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
Thus, these scripts will be much more complicated than the scripts created in <simple-config-chapter>.

Additionally, since the configuration scripts for full system simulation are tightly coupled to the hardware you are simulating, they are architecture specific.
x86, ARM, SPARC, etc., will all have significantly different full system configuration scripts.
In this chapter, we will be focusing on x86, since it is one of the most popular ISAs used in gem5.
<full-system-arm-chapter> contains information on how to configure an ARM system.
For other ISAs, you can refer to the code in mainline gem5 in configs/common/FSConfig.py.

.. todo::

    Make sure there is a link to the gem5 source here

Before getting started, make sure you have the x86 version of gem5 built.

.. todo::

    Finish this paragraph about building gem5.

Creating the system object
~~~~~~~~~~~~~~~~~~~~~~~~~~

Most of the complication in setting up full system simulation comes from creating the system object.
In full system mode, this system object contains all of the "system" object, from I/O to BIOS information.
Since this is going to be a complicated object, instead of setting each member one at a time, we are going to create a new Python object, based on the ``System`` SimObject.
Since we are simulating an x86 system, we will inherit from ``LinuxX86System``.

.. todo::

    Update all SimObjects to point to the gem5 source code.

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
Details on kernel configuration are in <kernel-chapter>.
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

        self.kernel = '/p/multifacet/users/powerjg/gem5-tutorial/binaries/x86_64-vmlinux-2.6.22.9'

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

        self.setDiskImage('/p/multifacet/users/powerjg/gem5-tutorial/disks/linux-x86.img')

        self.createCPU()

        self.createCacheHierarchy()

        self.createMemoryControllers()

        self.setupInterrupts()

.. code-block:: python

    def setDiskImage(self, img_path):
        """ Set the disk image
            @param img_path path on the host to the image file for the disk
        """
        disk0 = CowDisk(img_path)
        self.pc.south_bridge.ide.disks = [disk0]

.. code-block:: python

    def createCPU(self):
        """ Create a CPU for the system """
        self.cpu = AtomicSimpleCPU()
        self.mem_mode = 'atomic'

.. code-block:: python

    def createCacheHierarchy(self):
        """ Create a simple cache heirarchy with the caches from part1 """

        # Create an L1 instruction and data caches and an MMU cache
        # The MMU cache caches accesses from the inst and data TLBs
        self.cpu.icache = L1ICache(self._opts)
        self.cpu.dcache = L1DCache(self._opts)
        self.cpu.itbcache = ITBCache()
        self.cpu.dtbcache = DTBCache()

        # Connect the instruction, data, and MMU caches to the CPU
        self.cpu.icache.connectCPU(self.cpu)
        self.cpu.dcache.connectCPU(self.cpu)
        self.cpu.itbcache.connectCPU(self.cpu)
        self.cpu.dtbcache.connectCPU(self.cpu)

        # Create a memory bus, a coherent crossbar, in this case
        self.l2bus = L2XBar()

        # Hook the CPU ports up to the l2bus
        self.cpu.icache.connectBus(self.l2bus)
        self.cpu.dcache.connectBus(self.l2bus)
        self.cpu.itbcache.connectBus(self.l2bus)
        self.cpu.dtbcache.connectBus(self.l2bus)

        # # Connect the CPU TLBs directly to the L2 bus.
        # # You could put a cache here.
        # self.cpu.itb.walker.port = self.l2bus.slave
        # self.cpu.dtb.walker.port = self.l2bus.slave

        # Create an L2 cache and connect it to the l2bus
        self.l2cache = L2Cache(self._opts)
        self.l2cache.connectCPUSideBus(self.l2bus)

        # Connect the L2 cache to the membus
        self.l2cache.connectMemSideBus(self.membus)

.. code-block:: python

    def createMemoryControllers(self):
        """ Create the memory controller for the system """
        self.mem_cntrl = DDR3_1600_x64(range = self.mem_ranges[0],
                                       port = self.membus.master)

.. code-block:: python

    def setupInterrupts(self):
        """ Create the interrupt controller for the CPU """
        self.cpu.createInterruptController()
        self.cpu.interrupts[0].pio = self.membus.master
        self.cpu.interrupts[0].int_master = self.membus.slave
        self.cpu.interrupts[0].int_slave = self.membus.master


.. _architecture-specific-settings:

Architecture-specific settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Creating a run script
~~~~~~~~~~~~~~~~~~~~~

.. _running-full-system

Running a full system simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~