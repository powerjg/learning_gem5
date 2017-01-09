:authors: Jason Lowe-Power

.. _simplecache-chapter:

------------------------------------------
Creating a simple cache object
------------------------------------------

In this chapter, we will take the framework for a memory object we created in the :ref:`last chapter <memoryobject-chapter>` and add caching logic to it.

SimpleCache SimObject
~~~~~~~~~~~~~~~~~~~~~

After creating the SConscript file, that you can download :download:`here <../_static/scripts/part2/simplecache/Sconscript>`, we can create the SimObject Python file.

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

.. code-block:: c++

    void
    SimpleCache::insert(PacketPtr pkt)
    {
        if (cacheStore.size() > capacity) {
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

Adding statistics to the cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a good idea...
