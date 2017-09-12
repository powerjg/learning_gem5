:authors: Jason Lowe-Power

.. _simple-MI-chapter:

------------------------------------------
Configuring for a standard protocol
------------------------------------------

You can easily adapt the simple example configurations from this part to the other SLICC protocols in gem5.
In this chapter, we will briefly look at an example with ``MI_example``, though this can be easily extended to other protocols.

However, these simple configuration files will only work in syscall emulation mode.
Full system mode adds some complications such as DMA controllers.
These scripts can be extended to full system.

For ``MI_example``, we can use exactly the same runscript as before (``simple_ruby.py``), we just need to implement a different ``MyCacheSystem`` (and import that file in ``simple_ruby.py``).
Below, is the classes needed for ``MI_example``.
There are only a couple of changes from ``MSI``, mostly due to different naming schemes.
You can download the file :download:`here  <../_static/scripts/part3/configs/ruby_caches_MI_example.py>`

.. code-block:: python

    class MyCacheSystem(RubySystem):

        def __init__(self):
            if buildEnv['PROTOCOL'] != 'MI_example':
                fatal("This system assumes MI_example!")

            super(MyCacheSystem, self).__init__()

        def setup(self, system, cpus, mem_ctrls):
            """Set up the Ruby cache subsystem. Note: This can't be done in the
               constructor because many of these items require a pointer to the
               ruby system (self). This causes infinite recursion in initialize()
               if we do this in the __init__.
            """
            # Ruby's global network.
            self.network = MyNetwork(self)

            # MI example uses 5 virtual networks
            self.number_of_virtual_networks = 5
            self.network.number_of_virtual_networks = 5

            # There is a single global list of all of the controllers to make it
            # easier to connect everything to the global network. This can be
            # customized depending on the topology/network requirements.
            # Create one controller for each L1 cache (and the cache mem obj.)
            # Create a single directory controller (Really the memory cntrl)
            self.controllers = \
                [L1Cache(system, self, cpu) for cpu in cpus] + \
                [DirController(self, system.mem_ranges, mem_ctrls)]

            # Create one sequencer per CPU. In many systems this is more
            # complicated since you have to create sequencers for DMA controllers
            # and other controllers, too.
            self.sequencers = [RubySequencer(version = i,
                                    # I/D cache is combined and grab from ctrl
                                    icache = self.controllers[i].cacheMemory,
                                    dcache = self.controllers[i].cacheMemory,
                                    clk_domain = self.controllers[i].clk_domain,
                                    ) for i in range(len(cpus))]

            for i,c in enumerate(self.controllers[0:len(cpus)]):
                c.sequencer = self.sequencers[i]

            self.num_of_sequencers = len(self.sequencers)

            # Create the network and connect the controllers.
            # NOTE: This is quite different if using Garnet!
            self.network.connectControllers(self.controllers)
            self.network.setup_buffers()

            # Set up a proxy port for the system_port. Used for load binaries and
            # other functional-only things.
            self.sys_port_proxy = RubyPortProxy()
            system.system_port = self.sys_port_proxy.slave

            # Connect the cpu's cache, interrupt, and TLB ports to Ruby
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

    class L1Cache(L1Cache_Controller):

        _version = 0
        @classmethod
        def versionCount(cls):
            cls._version += 1 # Use count for this particular type
            return cls._version - 1

        def __init__(self, system, ruby_system, cpu):
            """CPUs are needed to grab the clock domain and system is needed for
               the cache block size.
            """
            super(L1Cache, self).__init__()

            self.version = self.versionCount()
            # This is the cache memory object that stores the cache data and tags
            self.cacheMemory = RubyCache(size = '16kB',
                                   assoc = 8,
                                   start_index_bit = self.getBlockSizeBits(system))
            self.clk_domain = cpu.clk_domain
            self.send_evictions = self.sendEvicts(cpu)
            self.ruby_system = ruby_system
            self.connectQueues(ruby_system)

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

        def connectQueues(self, ruby_system):
            """Connect all of the queues for this controller.
            """
            self.mandatoryQueue = MessageBuffer()
            self.requestFromCache = MessageBuffer(ordered = True)
            self.requestFromCache.master = ruby_system.network.slave
            self.responseFromCache = MessageBuffer(ordered = True)
            self.responseFromCache.master = ruby_system.network.slave
            self.forwardToCache = MessageBuffer(ordered = True)
            self.forwardToCache.slave = ruby_system.network.master
            self.responseToCache = MessageBuffer(ordered = True)
            self.responseToCache.slave = ruby_system.network.master

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
            self.requestToDir = MessageBuffer(ordered = True)
            self.requestToDir.slave = ruby_system.network.master
            self.dmaRequestToDir = MessageBuffer(ordered = True)
            self.dmaRequestToDir.slave = ruby_system.network.master

            self.responseFromDir = MessageBuffer()
            self.responseFromDir.master = ruby_system.network.slave
            self.dmaResponseFromDir = MessageBuffer(ordered = True)
            self.dmaResponseFromDir.master = ruby_system.network.slave
            self.forwardFromDir = MessageBuffer()
            self.forwardFromDir.master = ruby_system.network.slave
            self.responseFromMemory = MessageBuffer()

    class MyNetwork(SimpleNetwork):
        """A simple point-to-point network. This doesn't not use garnet.
        """

        def __init__(self, ruby_system):
            super(MyNetwork, self).__init__()
            self.netifs = []
            self.ruby_system = ruby_system

        def connectControllers(self, controllers):
            """Connect all of the controllers to routers and connect the routers
               together in a point-to-point network.
            """
            # Create one router/switch per controller in the system
            self.routers = [Switch(router_id = i) for i in range(len(controllers))]

            # Make a link from each controller to the router. The link goes
            # externally to the network.
            self.ext_links = [SimpleExtLink(link_id=i, ext_node=c,
                                            int_node=self.routers[i])
                              for i, c in enumerate(controllers)]

            # Make an "internal" link (internal to the network) between every pair
            # of routers.
            link_count = 0
            self.int_links = []
            for ri in self.routers:
                for rj in self.routers:
                    if ri == rj: continue # Don't connect a router to itself!
                    link_count += 1
                    self.int_links.append(SimpleIntLink(link_id = link_count,
                                                        src_node = ri,
                                                        dst_node = rj))
