:authors: Jason Lowe-Power

.. _full-system-config-chapter:

----------------------------------------
Full system configuration files
----------------------------------------

This chapter describes a set of simple configuration scripts for gem5 full system simulation mode.
These scripts are a simple set of working scripts that allow Linux to boot.
These scripts are not a complete set of scripts that are ready to be used for architecture research.
However, they are a good starting point for writing your own scripts.

Configuration scripts for full system mode are significantly more complicated than scripts for syscall emulation mode.
For full system simulation, you need to specify all of the information about the hardware system, including the BIOS, physical memory layout, interrupt controllers, I/O hardware, etc.
Thus, these scripts will be much more complicated than the scripts created in :ref:`simple-config-chapter`.

Additionally, since the configuration scripts for full system simulation are tightly coupled to the hardware you are simulating, they are architecture specific.
x86, ARM, SPARC, etc., will all have significantly different full system configuration scripts.
In this chapter, we will be focusing on x86, since it is one of the most popular ISAs used in gem5.
<full-system-arm-chapter> contains information on how to configure an ARM system.
For other ISAs, you can refer to the code in mainline gem5 in configs/common/FSConfig.py.

.. todo::

    Make sure there is a link to the gem5 source here

Before getting started, make sure you have the x86 version of gem5 built.
See :ref:`building-chapter`.
In this chapter, we assume you have built gem5 with the x86 ISA enabled.

Creating the system object
~~~~~~~~~~~~~~~~~~~~~~~~~~

Most of the complication in setting up full system simulation comes from creating the system object.
In full system mode, this system object contains all of the "system" object, from I/O to BIOS information.
Since this is going to be a complicated object, instead of setting each member one at a time, we are going to create a new Python object, based on the ``System`` SimObject.
Since we are simulating an x86 system, we will inherit from ``LinuxX86System``.

.. todo::

    Update all SimObjects to point to the gem5 source code.

Create a file called ``system.py`` to define the system object that we will use.

The first step is to define the constructor for our ``MySystem`` class.
This constructor will handle all of the initialization of the system.
It will create the memory system, the caches, and initialize everything that is required.
The constructor takes a single parameter, ``opts``, which will be passed on to the caches so they can be configured from the command line.
Using the ``SimpleOpts`` framework you can add any other options to the system.

.. code-block:: python

    class MySystem(LinuxX86System):

    def __init__(self, opts):
        super(MySystem, self).__init__()
        self._opts = opts


Next, just like in the first scripts we created, we need to define a system clock.
We put this in the same constructor function.
In this example, we are going to just define one clock domain for the entire system.
However, you can easily change this to have a domain for each subsystem (e.g., last-level cache, memory controllers, etc.).

We also define two memory ranges here.
First, we create a memory range that is the size of our physical memory (3 GB) in this example.
Second, we create a memory range for I/O devices.
This I/O space is required for x86 to enable PCI and other memory-mapped I/O devices, which we will get to shortly.

.. code-block:: python

        self.clk_domain = SrcClockDomain()
        self.clk_domain.clock = '3GHz'
        self.clk_domain.voltage_domain = VoltageDomain()

        mem_size = '3GB'
        self.mem_ranges = [AddrRange(mem_size),
                           AddrRange(0xC0000000, size=0x100000), # For I/0
                           ]


Next, again similar to the simple scripts, we create a memory bus.
However, this time, we also add a bad address responder and a default responder.
The ``badaddr_responder`` is a simple device (``BadAddr``) which is a fake device which returns a bad address error on any access.
We then set this simple error device to be the default port for addresses that don't have a  specific destination.
We also set the system port to this bus, as we did in syscall emulation mode.

.. todo::

    This bad addr thing could be made more clear.


.. code-block:: python

        self.membus = SystemXBar()
        self.membus.badaddr_responder = BadAddr()
        self.membus.default = self.membus.badaddr_responder.pio

        self.system_port = self.membus.slave


After creating the membus, we can initialize the x86 system.
For now, we will just call a function which does the magic for us.
The details of the function are in <architecture-specific-settings>.

.. code-block:: python

        x86.init_fs(self, self.membus)

After initializing the architecture-specific parts of the system, we now set up the kernel we are going to use.
The kernel can be a vanilla Linux kernel.
However, we usually remove a number of drivers from the kernel so the system boots faster, and these hardware blocks are not implemented in gem5.
Details on kernel configuration are in :ref:`kernel-chapter`.
For now, we will simply use the kernel that is supplied from gem5.org.
You can download the kernel (and the disk image used below) from gem5.org.
http://gem5.org/Download
We will use the 2.6.22.9 kernel provided.
You will need to change this line to point to the kernel you want to use.
Using a full path will work best, but you can also use a relative path from where you execute the run script.
Additionally, we set a few parameters that are passed to the kernel at boot time.


* ``earlyprintk=ttyS0``: This enable the kernel output to be directed to the serial terminal. We will discuss how to connect to the serial terminal <running-full-system>.
* ``console=ttyS0``: Direct all output that would be to the console to the serial terminal.
* ``lpj=7999923``: This is a serial output setting.
* ``root=/dev/hda1``: The partition and disk that holds the root directory (``/``).

You can add any other parameters that the Linux kernel understands in this list.
The list is then joined, so it is a single string with spaces between the parameters.

.. code-block:: python

        self.kernel = 'binaries/x86_64-vmlinux-2.6.22.9'

        boot_options = ['earlyprintk=ttyS0', 'console=ttyS0', 'lpj=7999923',
                        'root=/dev/hda1']
        self.boot_osflags = ' '.join(boot_options)

The rest of the constructor function calls a number of helper functions to finish the initialization of the system.
First, we set a disk image.
We are going to use the disk image distributed with gem5.
Again, using a full path will work best, but you can also use a relative path from where you execute the run script.
Finally, we are going to create the system's CPU, caches, memory controller, and interrupt controllers.
Below, each of these functions is described.

.. code-block:: python

        self.setDiskImage('disks/linux-x86.img')

        self.createCPU()

        self.createCacheHierarchy()

        self.createMemoryControllers()

        self.setupInterrupts()

First, ``setDiskImage`` creates a disk image object and sets the simulated IDE drive to point to the disk.
We need to create a COW (copy-on-write) disk image wrapper around gem5's disk emulation (see code below).
Then, we set the IDE drive's disk to the COW image and set up the disk.
The IDE bus can have up to two disks per channel, one master (required) and one slave (optional), and each bus has two channels.
In this script we have a single bus, with two channels, but we are only adding one master.
You can have up to four disks using this configuration by modifying the list of disks on the IDE bus.

.. code-block:: python

    def setDiskImage(self, img_path):
        """ Set the disk image
            @param img_path path on the host to the image file for the disk
        """
        disk0 = CowDisk(img_path)
        self.pc.south_bridge.ide.disks = [disk0]

In gem5, the disk image a a copy-on-write copy of the disk.
The following wrapper around the ``IdeDisk`` class creates a disk whose original image will be read-only.
All updates to this image will persist in a new file.
This allows you to have multiple simulations share the same base disk image.
You can put the following code at the bottom of the system.py file.

.. code-block:: python

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

After setting the disk image, next we have a function to create the CPU for the system.
You can easily change this function to use any of the CPU models in gem5 (e.g., TimingSimpleCPU, O3CPU, etc.).
Additionally, if you instead have a loop to create many CPUs, you will have a multicore system!
Here we also set the memory mode to be ``atomic``.
In atomic mode, all memory accesses happen atomically and do *not* affect the timing.
If you want to use this configuration for real simulation, you need to change this to a different CPU and memory model.

.. code-block:: python

    def createCPU(self):
        """ Create a CPU for the system """
        self.cpu = AtomicSimpleCPU()
        self.mem_mode = 'atomic'

After creating the disk image and the CPU, we next create the cache hierarchy.
For this configuration, we are going to use the simple two-level cache hierarchy from :ref:`cache-config-chapter`.
However, there is one important change when setting up the caches in full system mode compared to syscall emulation mode.
In full system, since we are actually modeling the real hardware, x86 and ARM architectures have hardware page table walkers that access memory.
Therefore, we need to connect these devices to a memory port.
It is also possible to add caches to these devices as well, but we omit that in this configuration file.
The code for the ``L1ICache`` and ``L1DCache`` can be downloaded :download:`here <../_static/scripts/part1/caches.py>` or in ``configs/learning_gem5/part1/caches.py``.
You can simply import that file to use those caches.

.. code-block:: python

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
        self.cpu.itb.walker.port = self.mmubus.slave
        self.cpu.dtb.walker.port = self.mmubus.slave

After creating the cache hierarchy, next we need to create the memory controllers.
In this configuration file, it is very simple.
We are going to create a single memory controller that is the backing store for our one memory range.
There are many other possible configurations here.
For instance, you can have multiple memory controllers with interleaved addresses, or if you have more than 3 GB of memory you may have more than one memory range.

.. code-block:: python

    def createMemoryControllers(self):
        """ Create the memory controller for the system """
        self.mem_cntrl = DDR3_1600_x64(range = self.mem_ranges[0],
                                       port = self.membus.master)

Finally, we we create the interrupt controllers for the CPU.
Again, this is the same as when we were using syscall emulation mode and is straightforward.

.. code-block:: python

    def setupInterrupts(self):
        """ Create the interrupt controller for the CPU """
        self.cpu.createInterruptController()
        self.cpu.interrupts[0].pio = self.membus.master
        self.cpu.interrupts[0].int_master = self.membus.slave
        self.cpu.interrupts[0].int_slave = self.membus.master

You can find the complete file :download:`here <../_static/scripts/part3/system.py>`.

.. _architecture-specific-settings:

Architecture-specific settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One thing we skipped over in the previous section was the function ``x86.init_fs``.
This function encapsulates most of the architecture-specific setup that is required for an x86 system.
You can download the file :download:`here <../_static/scripts/part3/x86.py>` and the code is listed below.
Next we will go through some of the highlights of this code.
For the details, see the Intel x86 architecture manual and the gem5 source code.

.. code-block:: python

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
                            hit_latency = 50,
                            response_latency = 50,
                            mshrs = 20,
                            size = '1kB',
                            tgts_per_mshr = 12,
                            forward_snoops = False,
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

First, we set up the I/O and APIC address space.
Then, we create the north bridge and attach the PCI device addresses.
Next, we create the APIC bridge and the I/O bridge.

After setting up the I/O addresses and ports, we then set up the BIOS.
There are a number of important BIOS tables, but we will only talk about a couple of them here.
First, you must add a ``X86IntelMPProcessor`` for each processor in the system.
Since we are only simulating one processor in this configuration, we just create one.
Also, when creating the ``X86IntelMPProcessor`` entries, exactly one should be set as the bootstrap processor.
Similarly, after creating the ``X86IntelMPProcessor`` entries, you must create the APIC entries for each CPU (one in this case).
This will also have to be change for multiple CPUs.

Next, we create the PCI and ICA buses, and a number of other I/O devices.

Finally, we create a number of ``X86E820Entry`` objects.
The BIOS communicates the physical memory layout to the operation system through these entries.
The first couple of entries are for specific OS or BIOS functions, then the third entry is the main entry for physical memory.
This third entry uses the same memory range that we created in the system object.
There are another two entries created at the top of the address range to support the I/O devices for x86.
If you want to use more than 3 GB a physical memory or add more memory ranges, you will need to modify these entries.

Creating a run script
~~~~~~~~~~~~~~~~~~~~~

Now that we have created a full x86 system, we can write a simple script to run gem5.
Create a file called ``run.py``.
First, in this file, we are going to import the m5 object and our system object.
We will also add an option to pass in a script, which we will talk about in the next section: :ref:`running-full-system`.

.. code-block:: python

    import sys

    import m5
    from m5.objects import *

    sys.path.append('configs/common/') # For the next line...
    import SimpleOpts

    from system import MySystem

    SimpleOpts.add_option("--script", default='',
                          help="Script to execute in the simulated system")

Now, the meat of this file is going to simply create our system object, set the script, and then run gem5!
This is the same as the simple scripts in :ref:`simple-config-chapter`.

.. code-block:: python

    if __name__ == "__m5_main__":
        (opts, args) = SimpleOpts.parse_args()

        # create the system we are going to simulate
        system = MySystem(opts)

        # Read in the script file passed in via an option.
        # This file gets read and executed by the simulated system after boot.
        # Note: The disk image needs to be configured to do this.
        system.readfile = opts.script

        # set up the root SimObject and start the simulation
        root = Root(full_system = True, system = system)

        # instantiate all of the objects we've created above
        m5.instantiate()

        # Keep running until we are done.
        print "Running the simulation"
        exit_event = m5.simulate()
        print 'Exiting @ tick %i because %s' % (m5.curTick(),
                                                exit_event.getCause())


Now we can run our simulation!

You can download ``run.py`` from :download:`here <../_static/scripts/part3/run.py>`

.. _running-full-system

Running a full system simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest way to run the simulation is just call the ``run.py`` script.
This will start gem5, and begin booting Linux.

.. code-block:: sh

    build/X86/gem5.opt configs/full_system/run.py

When running gem5, your output should look something like below.

::
    
    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Feb 12 2016 16:27:24
    gem5 started Feb 12 2016 17:30:43
    gem5 executing on mustardseed.cs.wisc.edu, pid 2994
    command line: build/X86/gem5.opt configs/learning_gem5/part3/run.py

    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (4096 Mbytes)
    info: kernel located at: binaries/x86_64-vmlinux-2.6.22.9
    Listening for com_1 connection on port 3457
          0: rtc: Real-time clock set to Sun Jan  1 00:00:00 2012
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    warn: Reading current count from inactive timer.
    Running the simulation
    info: Entering event queue @ 0.  Starting simulation...
    warn: Don't know what interrupt to clear for console.

Unlike in syscall emulation mode, standard output is not automatically redirected to the console.
Since we are simulating an entire system, if you want to connect to the simulated system you need to connect via a serial terminal.
Luckily, the gem5 developers have included one in the gem5 source distribution.

To build the terminal application, go to ``util/term`` and type make.
Then you will have the ``m5term`` application.

.. code-block:: sh

    cd util/term
    make

Now, after starting gem5 (and giving it a moment to start the simulation), you can connect to the simulated system.
The parameters to this application are the host that gem5 is running on (localhost if it is running on your current computer) and the port that gem5 is listening on.

.. code-block:: sh

    util/term/m5term localhost 3456

You can determine which port gem5 is listening from the gem5 output after you start the simulator.
You should see a line like the one below.
You may have a slightly different port number, if port 3456 is taken for some reason.

::

    Listening for com_1 connection on port 3456

After connecting, you can begin the slow process of watching Linux boot!
Using the atomic CPU and a relatively recent host computer, it should take around 5 minutes to boot to a command prompt.
At this point, you can run any application that is installed on the disk image that you used to boot Linux.

Using a runscript
*****************

Another way to run gem5 in full system mode instead of connecting via a terminal and running your application manually, is to use a runscript.
Our ``run.py`` script takes a single option, a script to pass to gem5.
This script is passed via ``system.script`` to the simulated system.

When gem5 boots Linux, the first thing it does is try to read the script from the host into the simulator.
This is configured within the default disk image from gem5.
We cover how to do this with your own disk image in :ref:`disk-image-chapter`.
See `<http://www.lowepower.com/jason/creating-disk-images-for-gem5.html>` for some details.

Runscripts are simply bash scripts that are automatically executed after Linux boots.
For instance, below is a simple runscript that executes ``ls``, then exits.

.. code-block:: sh

    ls

    /sbin/m5 exit

If you save this script as ``test.rcS`` then run gem5 as below, gem5 will run to completion then exit.

.. code-block: sh

    build/X86/gem5.opt configs/learning_gem5/part3/run.py --script=test.rcS

You can view m5out/system.pc.com_1.terminal to see the output of the simulated system.
It should look like the output below.

::

    Linux version 2.6.22.9 (blackga@nacho) (gcc version 4.1.2 (Gentoo 4.1.2)) #2 Mon Oct 8 13:13:00 PDT 2007
    Command line: earlyprintk=ttyS0 console=ttyS0 lpj=7999923 root=/dev/hda1
    BIOS-provided physical RAM map:
     BIOS-e820: 0000000000000000 - 000000000009fc00 (usable)
     BIOS-e820: 000000000009fc00 - 0000000000100000 (reserved)
     BIOS-e820: 0000000000100000 - 00000000c0000000 (usable)
     BIOS-e820: 00000000ffff0000 - 0000000100000000 (reserved)
    end_pfn_map = 1048576
    kernel direct mapping tables up to 100000000 @ 8000-d000
    DMI 2.5 present.
    Zone PFN ranges:
      DMA             0 ->     4096
      DMA32        4096 ->  1048576
      Normal    1048576 ->  1048576
    early_node_map[2] active PFN ranges
        0:        0 ->      159
        0:      256 ->   786432

    ....

    TCP cubic registered
    NET: Registered protocol family 1
    NET: Registered protocol family 10
    IPv6 over IPv4 tunneling driver
    NET: Registered protocol family 17
    EXT2-fs warning: mounting unchecked fs, running e2fsck is recommended
    VFS: Mounted root (ext2 filesystem).
    Freeing unused kernel memory: 232k freed
    ^MINIT: version 2.86 booting^M
    mounting filesystems...
    loading script...
    bin   dev  home  lib32  lost+found  opt   root  sys  usr
    boot  etc  lib   lib64  mnt         proc  sbin  tmp  var

This simple run script also ran an application ``/sbin/m5`` on the simulated machine.
This application allows you to comminucate from the simulated system to the simulator on the host system.
By running ``/sbin/m5 exit`` we are asking the simulator to exit.
There are other options to the ``m5`` program as well.
You can run ``/sbin/m5 --help`` to see all the options.

This ``m5`` program was built with the source in ``util/m5``.
You can also use the code in that directory to change applications to talk to the simulator.
For instance, you can add region-of-interest markers that allow gem5 to reset its stats at the beginning of the region-of-interest and stop simulation at the end.
See :ref:<m5-op-chapter> for more details.