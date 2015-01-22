

:authors: Jason Power

.. _advanced-config-chapter:

------------------------------------------
Creating an advanced configuration script
------------------------------------------

Using the :ref:`previous configuration script as a starting point <simple-config-chapter>`, this chapter will walk through a more complex configuration.
We will add a cache heirarchy to the system and make the CPU model configurable as shown in :ref:`the figure below <advanced-config-fig>`.
Additionally, this chapter will cover understanding the gem5 statistics output and adding command line parameters to your scripts.

.. _advanced-config-fig:

.. figure:: ../_static/figures/advanced_config.png
   :width: 40 %
   :alt: Visual representation of the simple system to simulate

   A system configuration with a two-level cache heirarchy.


Creating cache objects
~~~~~~~~~~~~~~~~~~~~~~

We are going to use the classic caches, instead of :ref:`ruby`, since we are modeling a single CPU system and we don't care about modeling cache coherence.
We will extend the BaseCache SimObject and configure it for our system.
First, we must understand the parameters that are used to configure BaseCache objects.

BaseCache
**********************

The BaseCache SimObject declaration can be found in :file:`src/mem/cache/BaseCache.py`.
This Python file defines the parameters which you can set of the SimObject.
Under the hood, when the SimObject is instantiated these parameters are passed to the C++ imlpemenation of the object.

.. code-block:: python

    from m5.params import *
    from m5.proxy import *
    from MemObject import MemObject
    from Prefetcher import BasePrefetcher
    from Tags import *

    class BaseCache(MemObject):
        type = 'BaseCache'
        cxx_header = "mem/cache/base.hh"
        assoc = Param.Int("associativity")
        hit_latency = Param.Cycles("The hit latency for this cache")
        response_latency = Param.Cycles(
                "Additional cache latency for the return path to core on a miss");
        max_miss_count = Param.Counter(0,
            "number of misses to handle before calling exit")
        mshrs = Param.Int("number of MSHRs (max outstanding requests)")
        demand_mshr_reserve = Param.Int(1, "mshrs to reserve for demand access")
        size = Param.MemorySize("capacity in bytes")
        forward_snoops = Param.Bool(True,
            "forward snoops from mem side to cpu side")
        is_top_level = Param.Bool(False, "Is this cache at the top level (e.g. L1)")
        tgts_per_mshr = Param.Int("max number of accesses per MSHR")
        two_queue = Param.Bool(False,
            "whether the lifo should have two queue replacement")
        write_buffers = Param.Int(8, "number of write buffers")
        prefetch_on_access = Param.Bool(False,
            "notify the hardware prefetcher on every access (not just misses)")
        prefetcher = Param.BasePrefetcher(NULL,"Prefetcher attached to cache")
        cpu_side = SlavePort("Port on side closer to CPU")
        mem_side = MasterPort("Port on side closer to MEM")
        addr_ranges = VectorParam.AddrRange([AllMemory], "The address range for the CPU-side port")
        system = Param.System(Parent.any, "System we belong to")
        sequential_access = Param.Bool(False,
            "Whether to access tags and data sequentially")
        tags = Param.BaseTags(LRU(), "Tag Store for LRU caches")

Within the ``BaseCache`` class, there are a number of *parameters*.
For instance, ``assoc`` is an integer parameter.
Some parameters, like ``write_buffers`` have a default value, 8 in this case.
The default parameter is the first argument to ``Param.*``, unless the first argument is a string.
The string argument of each of the parameters is a description of what the parameter is (e.g., ``hit_latency = Param.Cycles("The hit latency for this cache")`` means that the hit_latency controls "The hit latency for this cache").

Many of these parameters do not have defaults, so we are required to set these parameters before calling ``m5.instantiate()``.

----------------------------------------------

Now, to create caches with specific parameters, we are first going to create a new file, ``caches.py``, in the same directory as simple.py, ``configs/tutorial``.
The first step is to import the SimObject(s) we are going to extend in this file.

.. code-block:: python

    from m5.objects import BaseCache

Next, we can treat the BaseCache object just like any other Python class and extend it.
We can name the new cache anything we want.
Let's start by making an L1 cache.

.. code-block:: python

    class L1Cache(BaseCache):
        assoc = 2
        hit_latency = 2
        response_latency = 2
        mshrs = 4
        tgts_per_mshr = 20
        is_top_level = True

Here, we are setting some of the parameters of the BaseCache that do not have default values.
To see all of the possible configuration options, and to find which are required and which are optional, you have to look at the source code of the SimObject.
In this case, we are using BaseCache.

We have extended ``BaseCache`` and set most of the parameters that do not have default values in the ``BaseCache`` SimObject.
Next, let's two more sub-classes of L1Cache, an L1DCache and L1ICache

.. code-block:: python

    class L1ICache(L1Cache):
        size = '16kB'

    class L1DCache(L1Cache):
        size = '64kB'

Let's also create an L2 cache with some reasonable parameters.

.. code-block:: python

    class L2Cache(BaseCache):
        size = '256kB'
        assoc = 8
        hit_latency = 20
        response_latency = 20
        mshrs = 20
        tgts_per_mshr = 12


Now that we have specified all of the necessary parameters required for ``BaseCache``, all we have to do is instantiate our sub-classes and connect the caches to the interconnect.
However, connecting lots of objects up to complex interconnects can make configuration files quickly grow and become unreadable.
Therefore, let's first add some helper functions to our sub-classes of ``BaseCache``.
Remember, these are just Python classes, so we can do anything with them that you can do with a Python class.

To the L1 cache let's add two functions, ``connectCPU`` to connect a CPU to the cache and ``connectBus`` to connect the cache to a bus.
We need to add the following code to the ``L1Cache`` class.

.. code-block:: python

    def connectCPU(self, cpu):
        # need to define this in a base class!
        raise NotImplementedError

    def connectBus(self, bus):
        self.mem_side = bus.slave

Next, we have to define a separate ``connectCPU`` function for the instruction and data caches, since the I-cache and D-cache ports have a different names.
Our ``L1ICache`` and ``L1DCache`` classes now become:

.. code-block:: python

    class L1ICache(L1Cache):
        size = '16kB'

        def connectCPU(self, cpu):
            self.cpu_side = cpu.icache_port

    class L1DCache(L1Cache):
        size = '64kB'

        def connectCPU(self, cpu):
            self.cpu_side = cpu.dcache_port

Finally, let's add functions to the ``L2Cache`` to connect to the memory-side and CPU-side bus, respectively.

.. code-block:: python

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.master

    def connectMemSideBus(self, bus):
        self.mem_side = bus.slave

The complete file can be downloaded :download:`here <../_static/scripts/caches.py>`.



Adding caches the simple config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, let's add the caches we just created to the configuration script we created in the :ref:`last chapter <simple-config-chapter>`.

First, let's copy the script to a new name.

.. code-block:: sh

    cp simple.py two-level.py

First, we need to import the names from the ``caches.py`` file into the namespace.
We can add the following to the top of the file, as you would with any Python source.

.. code-block:: python

    from caches import *

Now, after creating the CPU, let's create the L1 caches:

.. code-block:: python

    system.cpu.icache = L1ICache()
    system.cpu.dcache = L1DCache()

And connect the caches to the CPU ports with the helper function we created.

.. code-block:: python

    system.cpu.icache.connectCPU(system.cpu)
    system.cpu.dcache.connectCPU(system.cpu)

We can't directly connect the L1 caches to the L2 cache since the L2 cache only expects a single port to connect to it.
Therefore, we need to create an L2 bus to connect our L1 caches to the L2 cache.
The, we can use our helper function to connect the L1 caches to the L2 bus.

.. code-block:: python

    system.l2bus = CoherentXBar()

    system.cpu.icache.connectBus(system.l2bus)
    system.cpu.dcache.connectBus(system.l2bus)

Next, we can create out L2 cache and connect it to the L2 bus and the memory bus.

.. code-block:: python

    system.l2cache = L2Cache()
    system.l2cache.connectCPUSideBus(system.l2bus)

    system.l2cache.connectMemSideBus(system.membus)

Everything else in the file stays the same!
Now we have a complete configuration with a two-level cache heirarchy.
If you run the current file, ``hello`` should now finish in 54604000 ticks.
The full script can be found :download:`here <../_static/scripts/simple-caches.py>`.


