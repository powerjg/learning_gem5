:authors: Jason Lowe-Power

Part I: Getting started with gem5
=================================

Building gem5
-------------

* Download gem5 source

.. code-block:: sh

    hg clone http://repo.gem5.org/gem5
    git clone https://gem5.googlesource.com/public/gem5

* Build gem5...

.. code-block:: sh

    scons -j5 build/X86/gem5.opt

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Slide on scons command
* Slide on SimObjects
* Slide on discrete event simulation

--------------------------------------

Configuration scripts
---------------------

* Slide on gem5 interface
* slide showing system we're going to build
    * If possible, draw this on the board, or leave it up.

* This script is the simplest system you can create.
    * We'll discuss some of what we're doing now
    * We'll go into more details on most of this later
* Make new folder: configs/hpca_tutorial
* Create new file: configs/hpca_tutorial/simple.py

* Import all compiled objects

.. code-block:: python

    import m5
    from m5.objects import *

* Instantiate a System

.. code-block:: python

    system = System()

* Set default clock domain and voltage domain

.. code-block:: python

    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = '1GHz'
    system.clk_domain.voltage_domain = VoltageDomain()

* Set memory mode to timing and default address range

.. code-block:: python

    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('512MB')]

* Create a CPU

.. code-block:: python

    system.cpu = TimingSimpleCPU()

* Create the membus

.. code-block:: python

    system.membus = SystemXBar()

* Connect the CPU ports to the membus

.. code-block:: python

    system.cpu.icache_port = system.membus.slave
    system.cpu.dcache_port = system.membus.slave

* Create the interrupt controllers (note: x86 only)

.. code-block:: python

    system.cpu.createInterruptController()
    system.cpu.interrupts[0].pio = system.membus.master
    system.cpu.interrupts[0].int_master = system.membus.slave
    system.cpu.interrupts[0].int_slave = system.membus.master

    system.system_port = system.membus.slave

* Create a memory controller
* Set the memory controller's range
* Connect the membus to the memory controller

.. code-block:: python

    system.mem_ctrl = DDR3_1600_x64()
    system.mem_ctrl.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.master

--------------------------------------

* Now, done with the "System"
* next step: Set up the workload
* Note: We're using SE mode

* Create a process
* Set the binary
* Set the CPU to use the process
* Create the threads

.. code-block:: python

    process = LiveProcess()
    process.cmd = ['tests/test-progs/hello/bin/x86/linux/hello']
    system.cpu.workload = process
    system.cpu.createThreads()

* Create the "root".
* All scripts *must* have a root
* Instantiate the system
    * This is where all the C++ objects are created

.. code-block:: python

    root = Root(full_system = False, system = system)
    m5.instantiate()

* Now, we can simulate.
* Remember, this is just Python

.. code-block:: python

    print "Beginning simulation!"
    exit_event = m5.simulate()

    print 'Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause())

* Run gem5!

.. code-block:: python

    build/X86/gem5.opt configs/hpca_tutorial/simple.py

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Slide on running
* Slide on ports
    * More details to come!
* slide on SE vs FS mode

--------------------------------------

Adding caches
-------------

* Quick overview of what you can do in python

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Look at src/mem/cache/Cache.py
* Look at configs/learning_gem5/part1/cache.py
* Loot at configs/learning_gem5/part1/two_level.py

* Run two_level.py

.. code-block:: sh

    build/X86/gem5.opt configs/learning_gem5/part1/two_level.py

* Run -h and show that you can add command-line parameters

.. code-block:: sh

    build/X86/gem5.opt configs/learning_gem5/part1/two_level.py -h

* Run with two different cache sizes and show there are different outputs

.. code-block:: sh

    build/X86/gem5.opt configs/learning_gem5/part1/two_level.py --l1d_size=2kB

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

--------------------------------------

Understanding gem5's output
--------------------------

* Slide on output generated

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Look at config.ini
* Look at stats.txt

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Slide talking about stats.txt
