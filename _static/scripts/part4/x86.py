# -*- coding: utf-8 -*-
# Copyright (c) 2016 Jason Lowe-Power
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors: Jason Lowe-Power

import m5
from m5.objects import *

def init_fs(system, membus):
    system.pc = Pc()

    # Constants similar to x86_traits.hh
    IO_address_space_base = 0x8000000000000000
    pci_config_address_space_base = 0xc000000000000000
    interrupts_address_space_base = 0xa000000000000000
    APIC_range_size = 1 << 12;

    # North Bridge
    system.iobus = IOXBar()
    system.bridge = Bridge(delay='50ns')
    system.bridge.master = system.iobus.slave
    system.bridge.slave = membus.master
    # Allow the bridge to pass through:
    #  1) kernel configured PCI device memory map address: address range
    #     [0xC0000000, 0xFFFF0000). (The upper 64kB are reserved for m5ops.)
    #  2) the bridge to pass through the IO APIC (two pages, already contained in 1),
    #  3) everything in the IO address range up to the local APIC, and
    #  4) then the entire PCI address space and beyond.
    system.bridge.ranges = \
        [
        AddrRange(0xC0000000, 0xFFFF0000),
        AddrRange(IO_address_space_base,
                  interrupts_address_space_base - 1),
        AddrRange(pci_config_address_space_base,
                  Addr.max)
        ]

    # Create a bridge from the IO bus to the memory bus to allow access to
    # the local APIC (two pages)
    system.apicbridge = Bridge(delay='50ns')
    system.apicbridge.slave = system.iobus.master
    system.apicbridge.master = membus.slave
    # This should be expanded for multiple CPUs
    system.apicbridge.ranges = [AddrRange(interrupts_address_space_base,
                                           interrupts_address_space_base +
                                           1 * APIC_range_size
                                           - 1)]

    # connect the io bus
    system.pc.attachIO(system.iobus)

    # Add a tiny cache to the IO bus.
    # This cache is required for the classic memory model to mantain coherence
    system.iocache = Cache(assoc=8,
                        tag_latency = 50,
                        data_latency = 50,
                        response_latency = 50,
                        mshrs = 20,
                        size = '1kB',
                        tgts_per_mshr = 12,
                        addr_ranges = system.mem_ranges)
    system.iocache.cpu_side = system.iobus.master
    system.iocache.mem_side = system.membus.slave

    system.intrctrl = IntrControl()

    ###############################################

    # Add in a Bios information structure.
    system.smbios_table.structures = [X86SMBiosBiosInformation()]

    # Set up the Intel MP table
    base_entries = []
    ext_entries = []
    # This is the entry for the processor.
    # You need to make multiple of these if you have multiple processors
    # Note: Only one entry should have the flag bootstrap = True!
    bp = X86IntelMPProcessor(
            local_apic_id = 0,
            local_apic_version = 0x14,
            enable = True,
            bootstrap = True)
    base_entries.append(bp)
    # For multiple CPUs, change id to 1 + the final CPU id above (e.g., cpus)
    io_apic = X86IntelMPIOAPIC(
            id = 1,
            version = 0x11,
            enable = True,
            address = 0xfec00000)
    system.pc.south_bridge.io_apic.apic_id = io_apic.id
    base_entries.append(io_apic)
    pci_bus = X86IntelMPBus(bus_id = 0, bus_type='PCI')
    base_entries.append(pci_bus)
    isa_bus = X86IntelMPBus(bus_id = 1, bus_type='ISA')
    base_entries.append(isa_bus)
    connect_busses = X86IntelMPBusHierarchy(bus_id=1,
            subtractive_decode=True, parent_bus=0)
    ext_entries.append(connect_busses)
    pci_dev4_inta = X86IntelMPIOIntAssignment(
            interrupt_type = 'INT',
            polarity = 'ConformPolarity',
            trigger = 'ConformTrigger',
            source_bus_id = 0,
            source_bus_irq = 0 + (4 << 2),
            dest_io_apic_id = io_apic.id,
            dest_io_apic_intin = 16)
    base_entries.append(pci_dev4_inta)
    def assignISAInt(irq, apicPin):
        assign_8259_to_apic = X86IntelMPIOIntAssignment(
                interrupt_type = 'ExtInt',
                polarity = 'ConformPolarity',
                trigger = 'ConformTrigger',
                source_bus_id = 1,
                source_bus_irq = irq,
                dest_io_apic_id = io_apic.id,
                dest_io_apic_intin = 0)
        base_entries.append(assign_8259_to_apic)
        assign_to_apic = X86IntelMPIOIntAssignment(
                interrupt_type = 'INT',
                polarity = 'ConformPolarity',
                trigger = 'ConformTrigger',
                source_bus_id = 1,
                source_bus_irq = irq,
                dest_io_apic_id = io_apic.id,
                dest_io_apic_intin = apicPin)
        base_entries.append(assign_to_apic)
    assignISAInt(0, 2)
    assignISAInt(1, 1)
    for i in range(3, 15):
        assignISAInt(i, i)
    system.intel_mp_table.base_entries = base_entries
    system.intel_mp_table.ext_entries = ext_entries

    # This is setting up the physical memory layout
    # Each entry represents a physical address range
    # The last entry in this list is the main system memory
    # Note: If you are configuring your system to use more than 3 GB then you
    #       will need to make significant changes to this section
    entries = \
       [
        # Mark the first megabyte of memory as reserved
        X86E820Entry(addr = 0, size = '639kB', range_type = 1),
        X86E820Entry(addr = 0x9fc00, size = '385kB', range_type = 2),
        # Mark the rest of physical memory as available
        X86E820Entry(addr = 0x100000,
                size = '%dB' % (system.mem_ranges[0].size() - 0x100000),
                range_type = 1),
        ]
    # Mark [mem_size, 3GB) as reserved if memory less than 3GB, which force
    # IO devices to be mapped to [0xC0000000, 0xFFFF0000). Requests to this
    # specific range can pass though bridge to iobus.
    entries.append(X86E820Entry(addr = system.mem_ranges[0].size(),
        size='%dB' % (0xC0000000 - system.mem_ranges[0].size()),
        range_type=2))

    # Reserve the last 16kB of the 32-bit address space for the m5op interface
    entries.append(X86E820Entry(addr=0xFFFF0000, size='64kB', range_type=2))

    system.e820_table.entries = entries
