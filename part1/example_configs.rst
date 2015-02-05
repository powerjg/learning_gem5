:authors: Jason Power

.. _gem5-provided-configs-chapter:

------------------------------------------
Using the default configuration scripts
------------------------------------------

In this chapter, we'll explore using the default configuration scripts that come with gem5.
gem5 ships with many configuration scripts that allow you to use gem5 very quickly.
However, a common pitfall is to use these scripts without fully understanding what is being simulated.
It is important when doing computer architecture research with gem5 to fully understand the system you are simulating.
This chapter will walk you through some important options and parts of the default configuration scripts.

In the last few chapters you have created your own configuration scripts from scratch.
This is very powerful, as it allows you to specify every single system parameter.
However, some systems are very complex to set up (e.g., a full-system ARM  or x86 machine).
Luckily, the gem5 developers have provided many scripts to bootstrap the process of building systems.

A tour of the directory structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All of gem5's configuration files can be found in ``configs/``.
The directory structure is shown below:

::

    configs/boot:
    ammp.rcS            halt.sh                micro_tlblat2.rcS              netperf-stream-udp-local.rcS
    ...

    configs/common:
    Benchmarks.py     cpu2000.py     Options.py   
    Caches.py         FSConfig.py    O3_ARM_v7a.py     SysPaths.py
    CacheConfig.py    CpuConfig.py   MemConfig.py      Simulation.py

    configs/dram:
    sweep.py

    configs/example:
    fs.py       read_config.py       ruby_mem_test.py      ruby_random_test.py
    memtest.py  ruby_direct_test.py  ruby_network_test.py  se.py

    configs/ruby:
    MESI_Three_Level.py  MI_example.py           MOESI_CMP_token.py  Network_test.py
    MESI_Two_Level.py    MOESI_CMP_directory.py  MOESI_hammer.py     Ruby.py

    configs/splash2:
    cluster.py  run.py

    configs/topologies:
    BaseTopology.py  Cluster.py  Crossbar.py  MeshDirCorners.py  Mesh.py  Pt2Pt.py  Torus.py

Each directory is briefly described below:

**boot/**
    These are rcS files which are used in full-system mode.
    These files are loaded by the simulator after Linux boots and are executed by the shell.
    Most of these are used to control benchmarks when running in full-system mode.
    Some are utility functions, like ``hack_back_ckpt.rcS``.
    These files are covered in more depth in the chapter on full-system simulation.

**common/**
    This directory contains a number of helper scripts and functions to create simulated systems.
    For instance, ``Caches.py`` is similar to the ``caches.py`` and ``caches_opts.py`` files created in previous chapters.

    ``Options.py`` contains a variety of options that can be set on the command line.
    Like the number of CPUs, system clock, and many, many more.
    This is a good place to look to see if the option you want to change already has a command line parameter.

    ``CacheConfig.py`` contains the options and functions for setting cache parameters for the classic memory system.

    ``MemConfig.py`` provides some helper functions for setting the memory system.

    ``FSConfig.py`` contains the necessary functions to set up full-system simulation for many different kinds of systems.
    Full-system simulation is discussed further in it's own chapter.

    ``Simulation.py`` contains many helper functions to set up and run gem5.
    A lot of the code contained in this file manages saving and restoring checkpoints.
    The example configuration files below in ``examples/`` use the functions in this file to execute the gem5 simulation.
    This file is quite complicated, but it also allows a lot of flexibility in how the simulation is run.

**dram/**
    Contains scripts to test DRAM.

**example/**
    This directory contains some example gem5 configuration scripts that can be used out-of-the-box to run gem5.
    Specifically, ``se.py`` and ``fs.py`` are quite useful.
    More on these files can be found in the next section.
    There are also some other utility configuration scripts in this directory.

**ruby/**
    This directory contains the configurations scripts for Ruby and its included cache coherence protocols.
    More details can be found in the chapter on Ruby.

**splash2/**
    This directory contains scripts to run the splash2 benchmark suite with a few options to configure the simulated system.

**topologies/**
    This directory contains the implementation of the topologies that can be used when creating the Ruby cache hierarchy.
    More details can be found in the chapter on Ruby.


Using ``se.py`` and ``fs.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this section, I'll discuss some of the common options that can be passed on the command line to ``se.py`` and ``fs.py``.
More details on how to run full-system simulation can be found in the full-system simulation chapter.
Here I'll discuss the options that are common to the two files.

Most of the options discussed in this section are found in Options.py and are registered in the function ``addCommonOptions``.
This section does not detail all of the options.
To see all of the options, run the configuration script with ``--help``, or read the script's source code.

First, let's simply run the hello world program without any parameters:

.. code-block:: sh
    
    build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello

And we get the following as output:

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan 14 2015 16:11:34
    gem5 started Feb  2 2015 15:22:24
    gem5 executing on mustardseed.cs.wisc.edu
    command line: build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello
    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    **** REAL SIMULATION ****
    info: Entering event queue @ 0.  Starting simulation...
    Hello world!
    Exiting @ tick 5942000 because target called exit()

However, this isn't a very interesting simulation at all!
By default, gem5 uses the atomic CPU and uses atomic memory accesses, so there's no real timing data reported!
To confirm this, you can look at m5out/config.ini.
The CPU is shown on line 46:

::

    [system.cpu]
    type=AtomicSimpleCPU
    children=apic_clk_domain dtb interrupts isa itb tracer workload
    branchPred=Null
    checker=Null
    clk_domain=system.cpu_clk_domain
    cpu_id=0
    do_checkpoint_insts=true
    do_quiesce=true
    do_statistics_insts=true

To actually run gem5 in timing mode, let's specify a CPU type.
While we're at it, we can also specify sizes for the L1 caches.

.. code-block:: sh
    
    build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello --cpu-type=TimingSimpleCPU --l1d_size=64kB --l1i_size=16kB

:: 

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan 14 2015 16:11:34
    gem5 started Feb  2 2015 15:26:57
    gem5 executing on mustardseed.cs.wisc.edu
    command line: build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello --cpu-type=TimingSimpleCPU --l1d_size=64kB --l1i_size=16kB
    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    **** REAL SIMULATION ****
    info: Entering event queue @ 0.  Starting simulation...
    Hello world!
    Exiting @ tick 344986500 because target called exit()

Now, let's check the config.ini file and make sure that these options propagated correctly to the final system.
If you search ``m5out/config.ini`` for "cache", you'll find that no caches were created!
Even though we specified the size of the caches, we didn't specify that the system should use caches, so they weren't created.
The correct command line should be:

.. code-block:: sh
    
    build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello --cpu-type=TimingSimpleCPU --l1d_size=64kB --l1i_size=16kB --caches

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan 14 2015 16:11:34
    gem5 started Feb  2 2015 15:29:20
    gem5 executing on mustardseed.cs.wisc.edu
    command line: build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/linux/hello --cpu-type=TimingSimpleCPU --l1d_size=64kB --l1i_size=16kB --caches
    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    **** REAL SIMULATION ****
    info: Entering event queue @ 0.  Starting simulation...
    Hello world!
    Exiting @ tick 29480500 because target called exit()

On the last line, we see that the total time went from 344986500 ticks to 29480500, much faster!
Looks like caches are probably enabled now.
But, it's always a good idea to double check the ``config.ini`` file.

::

    [system.cpu.dcache]
    type=BaseCache
    children=tags
    addr_ranges=0:18446744073709551615
    assoc=2
    clk_domain=system.cpu_clk_domain
    demand_mshr_reserve=1
    eventq_index=0
    forward_snoops=true
    hit_latency=2
    is_top_level=true
    max_miss_count=0
    mshrs=4
    prefetch_on_access=false
    prefetcher=Null
    response_latency=2
    sequential_access=false
    size=65536
    system=system
    tags=system.cpu.dcache.tags
    tgts_per_mshr=20
    two_queue=false
    write_buffers=8
    cpu_side=system.cpu.dcache_port
    mem_side=system.membus.slave[2]

Some common options ``se.py`` and ``fs.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All of the possible options are printed when you run:

.. code-block:: sh
    
    build/X86_MESI_Two_Level/gem5.opt configs/example/se.py --help

Below is a few important options from that list.

.. option:: --cpu-type=CPU_TYPE
    
    The type of cpu to run with.
    This is an important parameter to always set.
    The default is atomic, which doesn't perform a timing simulation.

.. option:: --sys-clock=SYS_CLOCK

    Top-level clock for blocks running at system speed.

.. option:: --cpu-clock=CPU_CLOCK

    Clock for blocks running at CPU speed.
    This is separate from the system clock above.

.. option:: --mem-type=MEM_TYPE

    Type of memory to use.
    Options include different DDR memories, and the ruby memory controller.

.. option:: --caches

    Perform the simulation with classic caches.

.. option:: --l2cache
    
    Perform the simulation with an L2 cache, if using classic caches.

.. option:: --ruby
    
    Use Ruby instead of the classic caches as the cache system simulation.

.. option:: -m TICKS, --abs-max-tick=TICKS

    Run to absolute simulated tick specified including ticks from a restored checkpoint.
    This is useful if you only want simulate for a certain amount of simulated time.

.. option:: -I MAXINSTS, --maxinsts=MAXINSTS

    Total number of instructions to simulate (default: run forever).
    This is useful if you want to stop simulation after a certain number of instructions has been executed.

.. option:: -c CMD, --cmd=CMD
    
    The binary to run in syscall emulation mode.

.. option:: -o OPTIONS, --options=OPTIONS

    The options to pass to the binary, use " " around the entire string.
    This is useful when you are running a command which takes options.
    You can pass both arguments and options (e.g., --whatever) through this variable.

.. option:: --output=OUTPUT
    
    Redirect stdout to a file.
    This is useful if you want to redirect the output of the simulated application to a file instead of printing to the screen.
    Note: to redirect gem5 output, you have to pass a parameter *before* the configuration script.

.. option:: --errout=ERROUT

    Redirect stderr to a file.
    Similar to above.