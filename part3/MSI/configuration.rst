:authors: Jason Lowe-Power

.. _MSI-config-section:

------------------------------------------
Configuring a simple Ruby system
------------------------------------------

First, create a new configuration directory in ``configs/``.
Just like all gem5 configuration files, we will have a configuration run script.
For the run script, we can start with ``simple.py`` from :ref:`simple-config-chapter`.
Copy this file to ``simple_ruby.py`` in your new directory.

We will make a couple of small changes to this file to use Ruby instead of directly connecting the CPU to the memory controllers.

First, so we can test our *coherence* protocol, let's use two CPUs.

.. code-block:: python

    system.cpu = [TimingSimpleCPU(), TimingSimpleCPU()]


Next, after the memory controllers have been instantiated, we are going to create the cache system and set up all of the caches.
Add the following lines *after the CPU interrupts have been created, but before instantiating the system*.

.. code-block:: python

    system.caches = MyCacheSystem()
    system.caches.setup(system, system.cpu, [system.mem_ctrl])


Like the classic cache example in :ref:`cache-config-chapter`, we are going to create a second file that contains the cache configuration code.
In this file we are going to have a class called ``MyCacheSystem`` and we will create a ``setup`` function that takes as parameters the CPUs in the system and the memory controllers.

You can download the complete run script :download:`here <../../_static/scripts/part3/configs/simple_ruby.py>`

Cache system configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, let's create a file ``msi_caches.py``.
In this file, we will create four classes ``MyCacheSystem`` which will inherit from ``RubySystem``, ``L1Cache`` and ``Directory`` which will inherit from the SimObjects created by SLICC from our two state machines, and ``MyNetwork`` which will inherit from ``SimpleNetwork``.

L1 Cache
========

Let's start with the ``L1Cache``.
First, we will inherit from ``L1Cache_Controller`` since we named our L1 cache "L1Cache" in the state machine file.
We also include a special class variable and class method for tracking the "version number".
For each SLICC state machine, you have to number them in ascending order from 0.
Each machine of the same type should have a unique version number.
This is used to differentiate the individual machines.
(Hopefully, in the future this requirement will be removed.)

.. code-block:: python

    class L1Cache(L1Cache_Controller):

        _version = 0
        @classmethod
        def versionCount(cls):
            cls._version += 1 # Use count for this particular type
            return cls._version - 1


Next, we implement the constructor for the class.

.. code-block:: python

    def __init__(self, system, ruby_system, cpu):
        super(L1Cache, self).__init__()

        self.version = self.versionCount()
        self.cacheMemory = RubyCache(size = '16kB',
                               assoc = 8,
                               start_index_bit = self.getBlockSizeBits(system))
        self.clk_domain = cpu.clk_domain
        self.send_evictions = self.sendEvicts(cpu)
        self.ruby_system = ruby_system
        self.connectQueues(ruby_system)

We need the CPUs in this function to grab the clock domain and system is needed for the cache block size.
Here, we set all of the parameters that we named in the state machine file (e.g., ``cacheMemory``).
We will set ``sequencer`` later.
We also hardcode the size an associativity of the cache.
You could add command line parameters for these options, if it is important to vary them at runtime.

Next, we implement a couple of helper functions.
First, we need to figure out how many bits of the address to use for indexing into the cache, which is a simple log operation.
We also need to decide whether to send eviction notices to the CPU.
Only if we are using the out-of-order CPU and using x86 or ARM ISA should we forward evictions.

.. code-block:: python

    def getBlockSizeBits(self, system):
        bits = int(math.log(system.cache_line_size, 2))
        if 2**bits != system.cache_line_size.value:
            panic("Cache line size not a power of 2!")
        return bits

    def sendEvicts(self, cpu):
        """True if the CPU model or ISA requires sending evictions from caches
           to the CPU. Two scenarios warrant forwarding evictions to the CPU:
           1. The O3 model must keep the LSQ coherent with the caches
           2. The x86 mwait instruction is built on top of coherence
           3. The local exclusive monitor in ARM systems
        """
        if type(cpu) is DerivO3CPU or \
           buildEnv['TARGET_ISA'] in ('x86', 'arm'):
            return True
        return False


Finally, we need to implement ``connectQueues`` to connect all of the message buffers to the Ruby network.
First, we create a message buffer for the mandatory queue.
Since this is an L1 cache and it will have a sequencer, we need to instantiate this special message buffer.
Next, we instantiate a message buffer for each buffer in the controller.
All of the "to" buffers we must set the "master" to the network (i.e., the buffer will send messages into the network), and all of the "from" buffers we must set the "slave" to the network.
These *names* are the same as the gem5 ports, but *message buffers are not currently implemented as gem5 ports*.
In this protocol, we are assuming the message buffers are ordered for simplicity.

.. code-block:: python

    def connectQueues(self, ruby_system):
        self.mandatoryQueue = MessageBuffer()

        self.requestToDir = MessageBuffer(ordered = True)
        self.requestToDir.master = ruby_system.network.slave
        self.responseToDirOrSibling = MessageBuffer(ordered = True)
        self.responseToDirOrSibling.master = ruby_system.network.slave
        self.forwardFromDir = MessageBuffer(ordered = True)
        self.forwardFromDir.slave = ruby_system.network.master
        self.responseFromDirOrSibling = MessageBuffer(ordered = True)
        self.responseFromDirOrSibling.slave = ruby_system.network.master

Directory
===========


Now, we can similarly implement the directory.
There are three differences from the L1 cache.
First, we need to set the address ranges for the directory.
Since each directory corresponds to a particular memory controller for a subset of the address range (possibly), we need to make sure the ranges match.
The default address ranges for Ruby controllers is ``AllMemory``.

Next, we need to set the master port ``memory``.
This is the port that sends messages when ``queueMemoryRead/Write`` is called in the SLICC code.
We set it the to the memory controller port.
Similarly, in ``connectQueues`` we need to instantiate the special message buffer ``responseFromMemory`` like the ``mandatoryQueue`` in the L1 cache.

.. code-block:: python

    class DirController(Directory_Controller):

        _version = 0
        @classmethod
        def versionCount(cls):
            cls._version += 1 # Use count for this particular type
            return cls._version - 1

        def __init__(self, ruby_system, ranges, mem_ctrls):
            """ranges are the memory ranges assigned to this controller.
            """
            if len(mem_ctrls) > 1:
                panic("This cache system can only be connected to one mem ctrl")
            super(DirController, self).__init__()
            self.version = self.versionCount()
            self.addr_ranges = ranges
            self.ruby_system = ruby_system
            self.directory = RubyDirectoryMemory()
            # Connect this directory to the memory side.
            self.memory = mem_ctrls[0].port
            self.connectQueues(ruby_system)

        def connectQueues(self, ruby_system):
            self.requestFromCache = MessageBuffer(ordered = True)
            self.requestFromCache.slave = ruby_system.network.master
            self.responseFromCache = MessageBuffer(ordered = True)
            self.responseFromCache.slave = ruby_system.network.master

            self.responseToCache = MessageBuffer(ordered = True)
            self.responseToCache.master = ruby_system.network.slave
            self.forwardToCache = MessageBuffer(ordered = True)
            self.forwardToCache.master = ruby_system.network.slave

            self.responseFromMemory = MessageBuffer()


Ruby System
============

Now, we can implement the Ruby system object.
For this object, the constructor is simple.
It just checks the SCons variable ``PROTOCOL`` to be sure that we are using the right configuration file for the protocol that was compiled.
We cannot create the controllers in the constructor because they require a pointer to the this object.
If we were to create them in the constructor, there would be a circular dependence in the SimObject hierarchy which will cause infinite recursion in when the system in instantiated with ``m5.instantiate``.

.. code-block:: python

    class MyCacheSystem(RubySystem):

        def __init__(self):
            if buildEnv['PROTOCOL'] != 'MSI':
                fatal("This system assumes MSI from learning gem5!")

            super(MyCacheSystem, self).__init__()


Instead of create the controllers in the constructor, we create a new function to create all of the needed objects: ``setup``.
First, we create the network.
We will look at this object next.
With the network, we need to set the number of virtual networks in the system.

Next, we instantiate all of the controllers.
Here, we use a single global list of the controllers to make it easier to connect them to the network later.
However, for more complicated cache topologies, it can make sense to use multiple lists of controllers.
We create one L1 cache for each CPU and one directory for the system.

Then, we instantiate all of the sequencers, one for each CPU.
Each sequencer needs a pointer to the instruction and data cache to simulate the correct latency when initially accessing the cache.
In more complicated systems, you also have to create sequencers for other objects like DMA controllers.

After creating the sequencers, we set the sequencer variable on each L1 cache controller.

Then, we connect all of the controllers to the network and call the ``setup_buffers`` function on the network.

We then have to set the "port proxy" for both the Ruby system and the ``system`` for making functional accesses (e.g., loading the binary in SE mode).

Finally, we connect all of the CPUs to the ruby system.
In this example, we assume that there are only CPU sequencers so the first CPU is connected to the first sequencer, and so on.
We also have to connect the TLBs and interrupt ports (if we are using x86).

.. code-block:: python

    def setup(self, system, cpus, mem_ctrls):
        self.network = MyNetwork(self)

        self.number_of_virtual_networks = 3
        self.network.number_of_virtual_networks = 3

        self.controllers = \
            [L1Cache(system, self, cpu) for cpu in cpus] + \
            [DirController(self, system.mem_ranges, mem_ctrls)]

        self.sequencers = [RubySequencer(version = i,
                                # I/D cache is combined and grab from ctrl
                                icache = self.controllers[i].cacheMemory,
                                dcache = self.controllers[i].cacheMemory,
                                clk_domain = self.controllers[i].clk_domain,
                                ) for i in range(len(cpus))]

        for i,c in enumerate(self.controllers[0:len(self.sequencers)]):
            c.sequencer = self.sequencers[i]

        self.num_of_sequencers = len(self.sequencers)

        self.network.connectControllers(self.controllers)
        self.network.setup_buffers()

        self.sys_port_proxy = RubyPortProxy()
        system.system_port = self.sys_port_proxy.slave

        for i,cpu in enumerate(cpus):
            cpu.icache_port = self.sequencers[i].slave
            cpu.dcache_port = self.sequencers[i].slave
            isa = buildEnv['TARGET_ISA']
            if isa == 'x86':
                cpu.interrupts[0].pio = self.sequencers[i].master
                cpu.interrupts[0].int_master = self.sequencers[i].slave
                cpu.interrupts[0].int_slave = self.sequencers[i].master
            if isa == 'x86' or isa == 'arm':
                cpu.itb.walker.port = self.sequencers[i].slave
                cpu.dtb.walker.port = self.sequencers[i].slave


Network
========

Finally, the last object we have to implement is the network.
The constructor is simple, but we need to declare an empty list for the list of network interfaces (``netifs``).

Most of the code is in ``connectControllers``.
This function implements a *very simple, unrealistic* point-to-point network.
In other words, every controller has a direct link to every other controller.

The Ruby network is made of three parts: routers that route data from one router to another or to external controllers, external links that link a controller to a router, and internal links that link two routers together.
First, we create a router for each controller.
Then, we create an external link from that router to the controller.
Finally, we add all of the "internal" links.
Each router is connected to all other routers to make the point-to-point network.

.. code-block:: python

    class MyNetwork(SimpleNetwork):

        def __init__(self, ruby_system):
            super(MyNetwork, self).__init__()
            self.netifs = []
            self.ruby_system = ruby_system

        def connectControllers(self, controllers):
            self.routers = [Switch(router_id = i) for i in range(len(controllers))]

            self.ext_links = [SimpleExtLink(link_id=i, ext_node=c,
                                            int_node=self.routers[i])
                              for i, c in enumerate(controllers)]

            link_count = 0
            self.int_links = []
            for ri in self.routers:
                for rj in self.routers:
                    if ri == rj: continue # Don't connect a router to itself!
                    link_count += 1
                    self.int_links.append(SimpleIntLink(link_id = link_count,
                                                        src_node = ri,
                                                        dst_node = rj))



You can download the complete ``msi_caches.py`` file :download:`here <../../_static/scripts/part3/configs/msi_caches.py>`.
