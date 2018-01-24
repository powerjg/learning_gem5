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
from m5.util import convert

import x86

from caches import *

class MySystem(LinuxX86System):

    def __init__(self, opts):
        super(MySystem, self).__init__()
        self._opts = opts

        # Set up the clock domain and the voltage domain
        self.clk_domain = SrcClockDomain()
        self.clk_domain.clock = '3GHz'
        self.clk_domain.voltage_domain = VoltageDomain()

        # For x86, there is an I/O gap from 3GB to 4GB.
        # We can have at most 3GB of memory unless we do something special
        # to account for this I/O gap. For simplicity, this is omitted.
        mem_size = '512MB'
        self.mem_ranges = [AddrRange(mem_size),
                           AddrRange(0xC0000000, size=0x100000), # For I/0
                           ]

        # Create the main memory bus
        # This connects to main memory
        self.membus = SystemXBar()
        self.membus.badaddr_responder = BadAddr()
        self.membus.default = self.membus.badaddr_responder.pio

        # Set up the system port for functional access from the simulator
        self.system_port = self.membus.slave

        # This will initialize most of the x86-specific system parameters
        # This includes things like the I/O, multiprocessor support, BIOS...
        x86.init_fs(self, self.membus)

        # Change this path to point to the kernel you want to use
        # Kernel from http://www.m5sim.org/dist/current/x86/x86-system.tar.bz2
        self.kernel = 'binaries/x86_64-vmlinux-2.6.22.9'

        # Options specified on the kernel command line
        boot_options = ['earlyprintk=ttyS0', 'console=ttyS0', 'lpj=7999923',
                        'root=/dev/hda1']
        self.boot_osflags = ' '.join(boot_options)

        # Replace these paths with the path to your disk images.
        # The first disk is the root disk. The second could be used for swap
        # or anything else.
        # Disks from http://www.m5sim.org/dist/current/x86/x86-system.tar.bz2
        self.setDiskImage('disks/linux-x86.img')

        # Create the CPU for our system.
        self.createCPU()

        # Create the cache heirarchy for the system.
        self.createCacheHierarchy()

        # Create the memory controller for the sytem
        self.createMemoryControllers()

        # Set up the interrupt controllers for the system (x86 specific)
        self.setupInterrupts()

    def createCPU(self):
        """ Create a CPU for the system """
        # This defaults to one simple atomic CPU. Using other CPU models
        # and using timing memory is possible as well.
        # Also, changing this to using multiple CPUs is also possible
        # Note: If you use multiple CPUs, then the BIOS config needs to be
        #       updated as well.

        self.cpu = AtomicSimpleCPU()
        self.mem_mode = 'atomic'
        self.cpu.createThreads()

    def setDiskImage(self, img_path):
        """ Set the disk image
            @param img_path path on the host to the image file for the disk
        """
        # Can have up to two master disk images.
        # This can be enabled with up to 4 images if using master-slave pairs
        disk0 = CowDisk(img_path)
        self.pc.south_bridge.ide.disks = [disk0]

    def createCacheHierarchy(self):
        """ Create a simple cache heirarchy with the caches from part1 """

        # Create an L1 instruction and data caches and an MMU cache
        # The MMU cache caches accesses from the inst and data TLBs
        self.cpu.icache = L1ICache(self._opts)
        self.cpu.dcache = L1DCache(self._opts)

        # Connect the instruction, data, and MMU caches to the CPU
        self.cpu.icache.connectCPU(self.cpu)
        self.cpu.dcache.connectCPU(self.cpu)

        # Hook the CPU ports up to the membus
        self.cpu.icache.connectBus(self.membus)
        self.cpu.dcache.connectBus(self.membus)

        # Connect the CPU TLBs directly to the mem.
        self.cpu.itb.walker.port = self.membus.slave
        self.cpu.dtb.walker.port = self.membus.slave

    def createMemoryControllers(self):
        """ Create the memory controller for the system """

        # Just create a controller for the first range, assuming the memory
        # size is < 3GB this will work. If it's > 3GB or if you want to use
        # mulitple or interleaved memory controllers then this should be
        # updated accordingly
        self.mem_cntrl = DDR3_1600_8x8(range = self.mem_ranges[0],
                                       port = self.membus.master)

    def setupInterrupts(self):
        """ Create the interrupt controller for the CPU """

        # create the interrupt controller for the CPU, connect to the membus
        self.cpu.createInterruptController()

        # For x86 only, make sure the interrupts are connected to the memory
        # Note: these are directly connected to the memory bus, not cached
        self.cpu.interrupts[0].pio = self.membus.master
        self.cpu.interrupts[0].int_master = self.membus.slave
        self.cpu.interrupts[0].int_slave = self.membus.master

class CowDisk(IdeDisk):
    """ Wrapper class around IdeDisk to make a simple copy-on-write disk
        for gem5. Creates an IDE disk with a COW read/write disk image.
        Any data written to the disk in gem5 is saved as a COW layer and
        thrown away on the simulator exit.
    """

    def __init__(self, filename):
        """ Initialize the disk with a path to the image file.
            @param filename path to the image file to use for the disk.
        """
        super(CowDisk, self).__init__()
        self.driveID = 'master'
        self.image = CowDiskImage(child=RawDiskImage(read_only=True),
                                  read_only=False)
        self.image.child.image_file = filename
