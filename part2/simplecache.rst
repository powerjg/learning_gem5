:authors: Jason Lowe-Power

.. _simplecache-chapter:

------------------------------------------
Creating a simple cache object
------------------------------------------

In this chapter, we will take the framework for a memory object we created in the :ref:`last chapter <memoryobject-chapter>` and add caching logic to it.

SimpleCache SimObject
~~~~~~~~~~~~~~~~~~~~~

After creating the SConscript file, that you can download :download:`here <../_static/scripts/part2/simplecache/SConscript>`, we can create the SimObject Python file.

.. code-block:: python

    from m5.params import *
    from m5.proxy import *
    from MemObject import MemObject

    class SimpleCache(MemObject):
        type = 'SimpleCache'
        cxx_header = "learning_gem5/simple_cache/simple_cache.hh"

        cpu_side = VectorSlavePort("CPU side port, receives requests")
        mem_side = MasterPort("Memory side port, sends requests")

        latency = Param.Cycles(1, "Cycles taken on a hit or to resolve a miss")

        size = Param.MemorySize('16kB', "The size of the cache")

        system = Param.System(Parent.any, "The system this cache is part of")

There are a couple of differences between this SimObject file and the one from the :ref:`previous chapter <memoryobject-chapter>`.
First, we have a couple of extra parameters.
Namely, a latency for cache accesses and the size of the cache.
:ref:`parameters-chapter` goes into more detail about these kinds of SimObject parameters.

Next, we include a ``System`` parameter, which is a pointer to the main system this cache is connected tol.
This is needed so we can get the cache block size from the system object when we are initializing the cache.
To reference the system object this cache is connected to, we use a special *proxy parameter*.
In this case, we use ``Parent.any``.

In the Python config file, when a ``SimpleCache`` is instantiated, his proxy parameter searches through all of the parents of the ``SimpleCache`` instance to find a SimObject that matches the ``System`` type.
Since we often use a ``System`` as the root SimObject, you will often see a ``system`` parameter resolved with this proxy parameter.

.. todo::

    Talk about other kind of proxy parameters somewhere.

The third and final difference between the ``SimpleCache`` and the ``SimpleMemobj`` is that instead of having two named CPU ports (``inst_port`` and ``data_port``), the ``SimpleCache`` use another special parameter: the ``VectorPort``.
``VectorPorts`` behave similarly to regular ports (e.g., they are resovled via ``getMasterPort`` and ``getSlavePort``), but they allow this object to connect to multiple peers.
Then, in the resolution functions the parameter we ignored before (``PortID idx``) is used to differentiate between the different ports.
By using a vector port, this cache can be connected into the system more flexibly than the ``SimpleMemobj``.

Implementing the SimpleCache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most of the code for the ```SimpleCache`` is the same as the ``SimpleMemobj``.
There are a couple of changes in the constructor and the key memory object functions.

First, we need to create the CPU side ports dynamically in the constructor and initialize the extra member functions based on the SimObject parameters.

.. code-block:: c++

    SimpleCache::SimpleCache(SimpleCacheParams *params) :
        MemObject(params),
        latency(params->latency),
        blockSize(params->system->cacheLineSize()),
        capacity(params->size / blockSize),
        memPort(params->name + ".mem_side", this),
        blocked(false), outstandingPacket(nullptr), waitingPortId(-1)
    {
        for (int i = 0; i < params->port_cpu_side_connection_count; ++i) {
            cpuPorts.emplace_back(name() + csprintf(".cpu_side[%d]", i), i, this);
        }
    }

In this function, we use the ``cacheLineSize`` from the system parameters to set the ``blockSize`` for this cache.
We also initialize the capacity based on the block size and the parameter and initialize other member variables we will need below.
Finally, we must create a number of ``CPUSidePorts`` based on the number of connections to this object.
Since the ``cpu_side`` port was declared as a ``VectorSlavePort`` in the SimObject Python file, the parameter automatically has a variable ``port_cpu_side_connection_count``.
This is based on the Python name of the parameter.
For each of these connections we add a new ``CPUSidePort`` to a ``cpuPorts`` vector declared in the ``SimpleCache`` class.

We also add one extra member variable to the ``CPUSidePort`` to save its id, and we add this as a parameter to its constructor.

Next, we need to implement ``getMasterPort`` and ``getSlavePort``.
The ``getMasterPort`` is exactly the same as the ``SimpleMemobj``.
For ``getSlavePort``, we now need to return the port based on the id requested.

.. code-block:: c++

    BaseSlavePort&
    SimpleCache::getSlavePort(const std::string& if_name, PortID idx)
    {
        if (if_name == "cpu_side" && idx < cpuPorts.size()) {
            return cpuPorts[idx];
        } else {
            return MemObject::getSlavePort(if_name, idx);
        }
    }

The implemenation of the ``CPUSidePort`` and the ``MemSidePort`` is almost the same as in the ``SimpleMemobj``.
The only difference is we need to add an extra parameter to ``handleRequest`` that is the id of the port which the request originated.
Without this id, we would not be able to forward the response to the correct port.
The ``SimpleMemobj`` knew which port to send replies based on whether the original request was an instruction or data accesses.
However, this information is not useful to the ``SimpleCache`` since it uses a vector of ports and not named ports.

The new ``handleRequest`` function does two different things than the ``handleRequest`` function in the ``SimpleMemobj``.
First, it stores the port id of the request as discussed above.
Since the ``SimpleCache`` is blocking and only allows a single request outstanding at a time, we only need to save a single port id.

Second, it takes time to access a cache.
Therefore, we need to take into account the latency to access the cache tags and the cache data for a request.
We added an extra parameter to the cache object for this, and in ``handleRequest`` we now use an event to stall the request for the needed amount of time.
We schedule a new event for ``latency`` cycles in the future.
The ``clockEdge`` function returns the *tick* that the *nth* cycle in the future occurs on.

.. code-block:: c++

    bool
    SimpleCache::handleRequest(PacketPtr pkt, int port_id)
    {
        if (blocked) {
            return false;
        }
        DPRINTF(SimpleCache, "Got request for addr %#x\n", pkt->getAddr());

        blocked = true;
        waitingPortId = port_id;

        schedule(new AccessEvent(this, pkt), clockEdge(latency));

        return true;
    }

The ``AccessEvent`` is a little more complicated than the ``EventWrapper`` we used in :ref:`events-chapter`.
Instead of using an ``EventWrapper``, in the ``SimpleCache`` we will use a new class.
The reason we cannot use an ``EventWrapper``, is that we need to pass the packet (``pkt``) from ``handleRequest`` to the event handler function.
The following code is the ``AccessEvent`` class.
We only need to implement the ``process`` function, that calls the function we want to use as our event handler, in this case ``accessTming``.
We also pass the flag ``AutoDelete`` to the event constructor so we do not need to worry about freeing the memory for the dynamically created object.
The event code will automatically delete the object after the ``process`` function has executed.

.. code-block:: c++

    class AccessEvent : public Event
    {
      private:
        SimpleCache *cache;
        PacketPtr pkt;
      public:
        AccessEvent(SimpleCache *cache, PacketPtr pkt) :
            Event(Default_Pri, AutoDelete), cache(cache), pkt(pkt)
        { }
        void process() override {
            cache->accessTiming(pkt);
        }
    };

Now, we need to implement the event handler, ``accessTiming``.

.. code-block:: c++

    void
    SimpleCache::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            pkt->makeResponse();
            sendResponse(pkt);
        } else {
            <miss handling>
        }
    }

This function first *functionally* accesses the cache.
This function ``accessFunctional`` (described below) performs the functional access of the cache and either reads or writes the cache on a hit or returns that the access was a miss.

If the access is a hit, we simply need to respond to the packet.
To respond, you first must call the function ``makeResponse`` on the packet.
This converts the packet from a request packet to a response packet.
For instance, if the memory command in the packet was a ``ReadReq`` this gets converted into a ``ReadResp``.
Writes behave similarly.
Then, we can send the response back to the CPU.

The ``sendResponse`` function does the same things as the ``handleResponse`` function in the ``SimpleMemobj`` except that it uses the ``waitingPortId`` to send the packet to the right port.
In this function, we need to mark the ``SimpleCache`` unblocked before calling ``sendPacket`` in case the peer on the CPU side immediately calls ``sendTimingReq``.
Then, we try to send retries to the CPU side ports if the ``SimpleCache`` can now receive requests and the ports need to be sent retries.

.. code-block:: c++

    void SimpleCache::sendResponse(PacketPtr pkt)
    {
        int port = waitingPortId;

        blocked = false;
        waitingPortId = -1;

        cpuPorts[port].sendPacket(pkt);
        for (auto& port : cpuPorts) {
            port.trySendRetry();
        }
    }

------------------------------------------------------------------

Back to the ``accessTiming`` function, we now need to handle the cache miss case.
On a miss, we first have to check to see if the missing packet is to an entire cache block.
If the packet is aligned and the size of the request is the size of a cache block, then we can simply forward the request to memory, just like in the ``SimpleMemobj``.

However, if the packet is smaller than a cache block, then we need to create a new packet to read the entire cache block from memory.
Here, whether the packet is a read or a write request, we send a read request to memory to load the data for the cache block into the cache.
In the case of a write, it will occur in the cache after we have loaded the data from memory.

Then, we create a new packet, that is ``blockSize`` in size and we call the ``allocate`` function to allocate memory in the ``Packet`` object for the data that we will read from memory.
Note: this memory is freed when we free the packet.
We use the original request object in the packet so the memory-side objects know the original requestor and the original request type for statistics.

Finally, we save the original packet pointer (``pkt``) in a member variable ``outstandingPacket`` so we can recover it when the ``SimpleCache`` receives a response.
Then, we send the new packet across the memory side port.

.. code-block:: c++

    void
    SimpleCache::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            pkt->makeResponse();
            sendResponse(pkt);
        } else {
            Addr addr = pkt->getAddr();
            Addr block_addr = pkt->getBlockAddr(blockSize);
            unsigned size = pkt->getSize();
            if (addr == block_addr && size == blockSize) {
                DPRINTF(SimpleCache, "forwarding packet\n");
                memPort.sendPacket(pkt);
            } else {
                DPRINTF(SimpleCache, "Upgrading packet to block size\n");
                panic_if(addr - block_addr + size > blockSize,
                         "Cannot handle accesses that span multiple cache lines");

                assert(pkt->needsResponse());
                MemCmd cmd;
                if (pkt->isWrite() || pkt->isRead()) {
                    cmd = MemCmd::ReadReq;
                } else {
                    panic("Unknown packet type in upgrade size");
                }

                PacketPtr new_pkt = new Packet(pkt->req, cmd, blockSize);
                new_pkt->allocate();

                outstandingPacket = pkt;

                memPort.sendPacket(new_pkt);
            }
        }
    }

On a response from memory, we know that this was caused by a cache miss.
The first step is to insert the responding packet into the cache.

Then, either there is an ``outstandingPacket``, in which case we need to forward that packet to the original requestor, or there is no ``outstandingPacket`` which means we should forward the ``pkt`` in the response to the original requestor.

If the packet we are receiving as a response was an upgrade packet because the original request was smaller than a cache line, then we need to copy the new data to the outstandingPacket packet or write to the cache on a write.
Then, we need to delete the new packet that we made in the miss handling logic.

.. code-block:: c++

    bool
    SimpleCache::handleResponse(PacketPtr pkt)
    {
        assert(blocked);
        DPRINTF(SimpleCache, "Got response for addr %#x\n", pkt->getAddr());
        insert(pkt);

        if (outstandingPacket != nullptr) {
            accessFunctional(outstandingPacket);
            outstandingPacket->makeResponse();
            delete pkt;
            pkt = outstandingPacket;
            outstandingPacket = nullptr;
        } // else, pkt contains the data it needs

        sendResponse(pkt);

        return true;
    }

Functional cache logic
**********************

Now, we need to implement two more functions: ``accessFunctional`` and ``insert``.
These two functions make up the key components of the cache logic.

First, to functionally update the cache, we first need storage for the cache contents.
The simplest possible cache storage is a map (hashtable) that maps from addresses to data.
Thus, we will add the following member to the ``SimpleCache``.

.. code-block:: c++

    std::unordered_map<Addr, uint8_t*> cacheStore;

To access the cache, we first check to see if there is an entry in the map which matches the address in the packet.
We use the ``getBlockAddr`` function of the ``Packet`` type to get the block-aligned address.
Then, we simply search for that address in the map.
If we do not find the address, then this function returns ``false``, the data is not in the cache, and it is a miss.

Otherwise, if the packet is a write request, we need to update the data in the cache.
To do this, we write the data from the packet to the cache.
We use the ``writeDataToBlock`` function which writes the data in the packet to the write offset into a potentially larger block of data.
This function takes the cache block offset and the block size (as a parameter) and writes the correct offset into the pointer passed as the first parameter.

If the packet is a read request, we need to update the packet's data with the data from the cache.
The ``setDataFromBlock`` function performs the same offset calculation as the ``writeDataToBlock`` function, but writes the packet with the data from the pointer in the first parameter.

.. code-block:: c++

    bool
    SimpleCache::accessFunctional(PacketPtr pkt)
    {
        Addr block_addr = pkt->getBlockAddr(blockSize);
        auto it = cacheStore.find(block_addr);
        if (it != cacheStore.end()) {
            if (pkt->isWrite()) {
                pkt->writeDataToBlock(it->second, blockSize);
            } else if (pkt->isRead()) {
                pkt->setDataFromBlock(it->second, blockSize);
            } else {
                panic("Unknown packet type!");
            }
            return true;
        }
        return false;
    }

Finally, we also need to implement the ``insert`` function.
This function is called every time the memory side port responds to a request.

The first step is to check if the cache is currently full.
If the cache has more entries (blocks) than the capacity of the cache as set by the SimObject parameter, then we need to evict something.
The following code evicts a random entry by leveraging the hashtable implementation of the C++ ``unordered_map``.

On an eviction, we need to write the data back to the backing memory in case it has been updated.
For this, we create a new ``Request``-``Packet`` pair.
The packet uses a new memory command: ``MemCmd::WritebackDirty``.
Then, we send the packet across the memory side port (``memPort``) and erase the entry in the cache storage map.

Then, after a block has potentially been evicted, we add the new address to the cache.
For this we simply allocate space for the block and add an entry to the map.
Finally, we write the data from the response packet in to the newly allocated block.
This data is guaranteed to be the size of the cache block since we made sure to make a new packet in the cache miss logic if the packet was smaller than a cache block.

.. code-block:: c++

    void
    SimpleCache::insert(PacketPtr pkt)
    {
        if (cacheStore.size() >= capacity) {
            // Select random thing to evict. This is a little convoluted since we
            // are using a std::unordered_map. See http://bit.ly/2hrnLP2
            int bucket, bucket_size;
            do {
                bucket = random_mt.random(0, (int)cacheStore.bucket_count() - 1);
            } while ( (bucket_size = cacheStore.bucket_size(bucket)) == 0 );
            auto block = std::next(cacheStore.begin(bucket),
                                   random_mt.random(0, bucket_size - 1));

            RequestPtr req = new Request(block->first, blockSize, 0, 0);
            PacketPtr new_pkt = new Packet(req, MemCmd::WritebackDirty, blockSize);
            new_pkt->dataDynamic(block->second); // This will be deleted later

            DPRINTF(SimpleCache, "Writing packet back %s\n", pkt->print());
            memPort.sendTimingReq(new_pkt);

            cacheStore.erase(block->first);
        }
        uint8_t *data = new uint8_t[blockSize];
        cacheStore[pkt->getAddr()] = data;

        pkt->writeDataToBlock(data, blockSize);
    }

Creating a config file for the cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The last step in our implemenation is to create a new Python config script that uses our cache.
We can use the outline from the :ref:`last chapter <memoryobject-chapter>` as a starting point.
The only difference is we may want to set the parameters of this cache (e.g., set the size of the cache to ``1kB``) and instead of using the named ports (``data_port`` and ``inst_port``), we just use the ``cpu_side`` port twice.
Since ``cpu_side`` is a ``VectorPort``, it will automatically create multiple port connections.

.. code-block:: python

    import m5
    from m5.objects import *

    ...

    system.cache = SimpleCache(size='1kB')

    system.cpu.icache_port = system.cache.cpu_side
    system.cpu.dcache_port = system.cache.cpu_side

    system.membus = SystemXBar()

    system.cache.mem_side = system.membus.slave

    ...

The Python config file can be downloaded :download:`here <../_static/scripts/part2/simplecache/simple_cache.py>`

Running this script should produce the exepected output from the hello binary.

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan 10 2017 17:38:15
    gem5 started Jan 10 2017 17:40:03
    gem5 executing on chinook, pid 29031
    command line: build/X86/gem5.opt configs/learning_gem5/part2/simple_cache.py

    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    warn: CoherentXBar system.membus has no snooping ports attached!
    warn: ClockedObject: More than one power state change request encountered within the same simulation tick
    Beginning simulation!
    info: Entering event queue @ 0.  Starting simulation...
    Hello world!
    Exiting @ tick 56082000 because target called exit()

Modifying the size of the cache, for instance to 128 KB, should improve the performance of the system.

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan 10 2017 17:38:15
    gem5 started Jan 10 2017 17:41:10
    gem5 executing on chinook, pid 29037
    command line: build/X86/gem5.opt configs/learning_gem5/part2/simple_cache.py

    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    warn: CoherentXBar system.membus has no snooping ports attached!
    warn: ClockedObject: More than one power state change request encountered within the same simulation tick
    Beginning simulation!
    info: Entering event queue @ 0.  Starting simulation...
    Hello world!
    Exiting @ tick 32685000 because target called exit()


Adding statistics to the cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Knowing the overall execution time of the system is one important metric.
However, you may want to include other statistics as well, such as the hit and miss rates of the cache.
To do this, we need to add some statistics to the ``SimpleCache`` object.

First, we need to declare the statistics in the ``SimpleCache`` object.
They are part of the ``Stats`` namespace.
In this case, we'll make four statistics.
The number of ``hits`` and the number of ``misses`` are just simple ``Scalar`` counts.
We will also add a ``missLatency`` which is a histogram of the time it takes to satisfy a miss.
Finally, we'll add a special statistic called a ``Formula`` for the ``hitRatio`` that is a combination of other statistics (the number of hits and misses).

.. code-block:: c++

    class SimpleCache : public MemObject
    {
      private:
        ...

        Tick missTime; // To track the miss latency

        Stats::Scalar hits;
        Stats::Scalar misses;
        Stats::Histogram missLatency;
        Stats::Formula hitRatio;

      public:
        ...

        void regStats() override;
    };

Next, we have to define the function to override the ``regStats`` function so the statistics are registered with gem5's statistics infrastructure.
Here, for each statistic, we give it a name based on the "parent" SimObject name and a description.
For the histogram statistic, we also need to initialize it with how many buckets we want in the histogram.
Finally, for the formula, we simply need to write the formula down in code.

.. code-block:: c++

    void
    SimpleCache::regStats()
    {
        // If you don't do this you get errors about uninitialized stats.
        MemObject::regStats();

        hits.name(name() + ".hits")
            .desc("Number of hits")
            ;

        misses.name(name() + ".misses")
            .desc("Number of misses")
            ;

        missLatency.name(name() + ".missLatency")
            .desc("Ticks for misses to the cache")
            .init(16) // number of buckets
            ;

        hitRatio.name(name() + ".hitRatio")
            .desc("The ratio of hits to the total accesses to the cache")
            ;

        hitRatio = hits / (hits + misses);

    }

Finally, we need to use update the statistics in our code.
In the ``accessTiming`` class, we can increment the ``hits`` and ``misses`` on a hit and miss respectively.
Additionally, on a miss, we save the current time so we can measure the latency.

.. code-block:: c++

    void
    SimpleCache::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            hits++; // update stats
            pkt->makeResponse();
            sendResponse(pkt);
        } else {
            misses++; // update stats
            missTime = curTick();
            ...

Then, when we get a response, we need to add the measured latency to our histogram.
For this, we use the ``sample`` function.
This adds a single point to the histogram.
This histogram automaticaly resizes the buckets to fit the data it receives.

.. code-block:: c++

    bool
    SimpleCache::handleResponse(PacketPtr pkt)
    {
        insert(pkt);

        missLatency.sample(curTick() - missTime);
        ...

The complete code for the ``SimpleCache`` header file can be downloaded :download:`here <../_static/scripts/part2/simplecache/simple_cache.hh>`,
and the complete code for the implementation of the ``SimpleCache`` can be downloaded  :download:`here <../_static/scripts/part2/simplecache/simple_cache.cc>`.

Now, if we run the above config file, we can check on the statistics in the ``stats.txt`` file.
For the 1 KB case, we get the following statistics.
91% of the accesses are hits and the average miss latency is 53334 ticks (or 53 ns).

::

    system.cache.hits                                8431                       # Number of hits
    system.cache.misses                               877                       # Number of misses
    system.cache.missLatency::samples                 877                       # Ticks for misses to the cache
    system.cache.missLatency::mean           53334.093501                       # Ticks for misses to the cache
    system.cache.missLatency::gmean          44506.409356                       # Ticks for misses to the cache
    system.cache.missLatency::stdev          36749.446469                       # Ticks for misses to the cache
    system.cache.missLatency::0-32767                 305     34.78%     34.78% # Ticks for misses to the cache
    system.cache.missLatency::32768-65535             365     41.62%     76.40% # Ticks for misses to the cache
    system.cache.missLatency::65536-98303             164     18.70%     95.10% # Ticks for misses to the cache
    system.cache.missLatency::98304-131071             12      1.37%     96.47% # Ticks for misses to the cache
    system.cache.missLatency::131072-163839            17      1.94%     98.40% # Ticks for misses to the cache
    system.cache.missLatency::163840-196607             7      0.80%     99.20% # Ticks for misses to the cache
    system.cache.missLatency::196608-229375             0      0.00%     99.20% # Ticks for misses to the cache
    system.cache.missLatency::229376-262143             0      0.00%     99.20% # Ticks for misses to the cache
    system.cache.missLatency::262144-294911             2      0.23%     99.43% # Ticks for misses to the cache
    system.cache.missLatency::294912-327679             4      0.46%     99.89% # Ticks for misses to the cache
    system.cache.missLatency::327680-360447             1      0.11%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::360448-393215             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::393216-425983             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::425984-458751             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::458752-491519             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::491520-524287             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::total                   877                       # Ticks for misses to the cache
    system.cache.hitRatio                        0.905780                       # The ratio of hits to the total access


And when using a 128 KB cache, we get a slightly higher hit ratio. It seems like our cache is working as exepected!

::

    system.cache.hits                                8944                       # Number of hits
    system.cache.misses                               364                       # Number of misses
    system.cache.missLatency::samples                 364                       # Ticks for misses to the cache
    system.cache.missLatency::mean           64222.527473                       # Ticks for misses to the cache
    system.cache.missLatency::gmean          61837.584812                       # Ticks for misses to the cache
    system.cache.missLatency::stdev          27232.443748                       # Ticks for misses to the cache
    system.cache.missLatency::0-32767                   0      0.00%      0.00% # Ticks for misses to the cache
    system.cache.missLatency::32768-65535             254     69.78%     69.78% # Ticks for misses to the cache
    system.cache.missLatency::65536-98303             106     29.12%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::98304-131071              0      0.00%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::131072-163839             0      0.00%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::163840-196607             0      0.00%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::196608-229375             0      0.00%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::229376-262143             0      0.00%     98.90% # Ticks for misses to the cache
    system.cache.missLatency::262144-294911             2      0.55%     99.45% # Ticks for misses to the cache
    system.cache.missLatency::294912-327679             1      0.27%     99.73% # Ticks for misses to the cache
    system.cache.missLatency::327680-360447             1      0.27%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::360448-393215             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::393216-425983             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::425984-458751             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::458752-491519             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::491520-524287             0      0.00%    100.00% # Ticks for misses to the cache
    system.cache.missLatency::total                   364                       # Ticks for misses to the cache
    system.cache.hitRatio                        0.960894                       # The ratio of hits to the total access
