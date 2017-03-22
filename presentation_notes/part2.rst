:authors: Jason Lowe-Power

Part II: Modifying and extending gem5
=====================================

Setting up development environment
----------------------------------

* Use the style guide
* Install the style guide
* Use mercurial queues (or git or whatever)

--------------------------------------

Simple SimObject
----------------

* Slide on outline of making a SimObject

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Create new folder src/hpca_tutorial

Step 1: Create a Python class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Every SimOjbect needs a SimObject declaration file
* Create a file src/hpca_tutorial/HelloObject.py

.. code-block:: python

    from m5.params import *
    from m5.SimObject import SimObject

    class HelloObject(SimObject):
        type = 'HelloObject'
        cxx_header = "hpca_tutorial/hello_object.hh"

* Talk about what these things mean

Step 2: Implement your SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Declare C++ file. Edit src/hpca_tutorial/hello_object.hh

.. code-block:: c++

    #ifndef __HPCA_TUTORIAL_HELLO_OBJECT_HH__
    #define __HPCA_TUTORIAL_HELLO_OBJECT_HH__

    #include "params/HelloObject.hh"
    #include "sim/sim_object.hh"

    class HelloObject : public SimObject
    {
      public:
        HelloObject(HelloObjectParams *p);
    };

    #endif // __HPCA_TUTORIAL_HELLO_OBJECT_HH__

* Explain the header file.

* Define the SimObject functions

.. code-block:: c++

    #include "learning_gem5/hello_object.hh"

    #include <iostream>

    HelloObject::HelloObject(HelloObjectParams *params) : SimObject(params)
    {
        std::cout << "Hello World! From a SimObject!" << std::endl;
    }

* Every SimObject constructor takes a single parameter, the parameters.

* Define the Params create function

.. code-block:: python

    HelloObject*
    HelloObjectParams::create()
    {
        return new HelloObject(this);
    }

* This is what calls the constructor. This is called when m5.instantiate() happens in the run script.

Step 3: Register the SimObject and C++ files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Edit src/hpca_tutorial/SConscript

.. code-block:: python

    Import('*')

    SimObject('HelloObject.py')
    Source('hello_object.cc')

* Explain the SConscript file

Step 4: Recompile
~~~~~~~~~~~~~~~~~
* Recompile gem5

.. code-block:: sh

    scons -j5 build/X86/gem5.opt

Step 5: Write a run/config script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Edit configs/hpca_tutorial/hello_run.py

* Again, import all gem5 objects

.. code-block:: python

    import m5
    from m5.objects import *

* Create the root object

.. code-block:: python

    root = Root(full_system = False)

* instantiate the hello object

.. code-block:: python

    root.hello = HelloObject()

* instantiate gem5 objects in C++ and run the simulation

.. code-block:: python

    m5.instantiate()

    print "Beginning simulation!"
    exit_event = m5.simulate()
    print 'Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause())

* Run gem5!

.. code-block:: python

    build/X86/gem5.opt configs/hpca_tutorial/hello_run.py

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Go through the slides explaining these steps again.

--------------------------------------

Debugging gem5
--------------

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Using iostream is bad! Think of what would happen if every single object had lots of print statments? How about when you need to debug something and you have to add a million print statements?
* Solution: Debug flags!

* Let's look at a couple of examples:
* Debug flags go between the gem5 binary and the config script.

.. code-block:: sh

    build/X86/gem5.opt --debug-flags=DRAM configs/learning_gem5/part1/simple.py | head -n 50

* Debug statements show you the name of the SimObject (as defined in Python) and the tick it was printed on.

* You can use the following to see what Debug flags exist

.. code-block:: sh

    build/X86/gem5.opt --debug-help

* Other things you can do
    * Break at a certain tick
    * Start/stop debugging at certain ticks
    * Redirect to a file
    * Ignore certain SimObject's output

--------------------------------

* Declare a debug flag in src/hpca_tutorial/SConscript

.. code-block:: python

    DebugFlag('Hello')

* Add a debug statment in src/hpca_tutorial/hello_object.cc

.. code-block:: c++

    # include "debug/Hello.hh"

    ...

    DPRINTF(Hello, "Created the hello object\n");

* Build gem5 and run it with "hello" debug flag

.. code-block:: sh

    build/X86/gem5.opt --debug-flags=Hello configs/hpca_tutorial/hello_run.py

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Go over debugging slide

--------------------------------------

Event-driven programming
------------------------

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Add an event wrapper to the HelloObject from last chapter.
* Add a processEvent function

hello_object.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

      private:
        void processEvent();

        EventWrapper<HelloObject, &HelloObject::processEvent> event;

* Initialize the event
* Implement the processEvent function

hello_object.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        SimObject(params), event(*this)

    void
    HelloObject::processEvent()
    {
        DPRINTF(Hello, "Hello world! Processing the event!\n");
    }

* Add a startup function to the header
* Schedule an event

hello_object.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

    void startup();

hello_object.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::startup()
    {
        schedule(event, 100);
    }

* Recompile and run gem5

--------------------------------------

* Add two parameters to class: latency, timesLeft

hello_object.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

        Tick latency;

        int timesLeft;

* Initialize these parameters

hello_object.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        SimObject(params), event(*this), latency(100), timesLeft(10)

* update startup and process event

hello_object.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::startup()
    {
        schedule(event, latency);
    }

    void
    HelloObject::processEvent()
    {
        timesLeft--;
        DPRINTF(Hello, "Hello world! Processing the event! %d left\n", timesLeft);

        if (timesLeft <= 0) {
            DPRINTF(Hello, "Done firing!\n");
        } else {
            schedule(event, curTick() + latency);
        }
    }

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Go over slides related to the above.

--------------------------------------

Adding parameters
-----------------
.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Talk about simple parameters

HelloObject.py
~~~~~~~~~~~~~~
.. code-block:: python

    class HelloObject(SimObject):
        type = 'HelloObject'
        cxx_header = "learning_gem5/hello_object.hh"

        time_to_wait = Param.Latency("Time before firing the event")
        number_of_fires = Param.Int(1, "Number of times to fire the event before "
                                       "goodbye")

* Update the constructor

hello_object.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        SimObject(params),
        event(*this),
        myName(params->name),
        latency(params->time_to_wait),
        timesLeft(params->number_of_fires)
    {
        DPRINTF(Hello, "Created the hello object with the name %s\n", myName);
    }

* Run gem5 without updating the config file and get an error
* Fix the above error

run_hello.py
~~~~~~~~~~~~
.. code-block:: python

    root.hello = HelloObject(time_to_wait = '2us')

* or

.. code-block:: python

    root.hello = HelloObject()
    root.hello.time_to_wait = '2us'

* Run again
* Modify config to fire more than once

* Run again

.. code-block:: python

    root.hello.number_of_fires = 10

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Go over slides

----------------------------------------------

MemObjects
----------

* Show slides about master/slave and packets
* packets
  * Request (addr, requestor)
  * command (can change)
  * size
  * data (pointer)
* port interface

.. figure:: ../_static/figures/master_slave_1.png
    :width: 40 %

    Simple master-slave interaction when both can accept the request and the response.

.. figure:: ../_static/figures/master_slave_2.png
    :width: 40 %
    :alt: Slave busy interaction

    Simple master-slave interaction when the slave is busy

.. figure:: ../_static/figures/master_slave_3.png
   :width: 40 %
   :alt: Master busy interaction

   Simple master-slave interaction when the master is busy

--------------------------

* This is the system we're trying to create.
    * Explain how this is going to be blocking
    * Explain how we want to implement this.

.. figure:: ../_static/figures/simple_memobj.png
   :width: 40 %

   System

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Add parameters for the ports to connect the CPU and the membus.

HelloObject.py
~~~~~~~~~~~~~~~
.. code-block:: python

    ...
    from MemObject import MemObject

    class HelloObject(MemObject):
        ...

        inst_port = SlavePort("CPU side port, receives requests")
        data_port = SlavePort("CPU side port, receives requests")
        mem_side = MasterPort("Memory side port, sends requests")

* Define the header file
* Point out "public MemObject"

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    #include "mem/mem_object.hh"

    HelloObject : public MemObject

* Define the CPU-side slave port
* Talk about each of the functions below

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
      private:
        HelloObject *owner;

      public:
        CPUSidePort(const std::string& name, HelloObject *owner) :
            SlavePort(name, owner), owner(owner)
        { }

        AddrRangeList getAddrRanges() const override;

      protected:
        Tick recvAtomic(PacketPtr pkt) override { panic("recvAtomic unimpl."); }
        void recvFunctional(PacketPtr pkt) override;
        bool recvTimingReq(PacketPtr pkt) override;
        void recvRespRetry() override;
    };

* define the memory side master port
* Talk about each of the functions below

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class MemSidePort : public MasterPort
    {
      private:
        HelloObject *owner;

      public:
        MemSidePort(const std::string& name, HelloObject *owner) :
            MasterPort(name, owner), owner(owner)
        { }

      protected:
        bool recvTimingResp(PacketPtr pkt) override;
        void recvReqRetry() override;
        void recvRangeChange() override;
    };

* Define the MemObject interface

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class HelloObject : public MemObject
    {
      private:

        <CPUSidePort declaration>
        <MemSidePort declaration>

        CPUSidePort instPort;
        CPUSidePort dataPort;

        MemSidePort memPort;

      public:
        HelloObject(HelloObjectParams *params);

        BaseMasterPort& getMasterPort(const std::string& if_name,
                                      PortID idx = InvalidPortID) override;

        BaseSlavePort& getSlavePort(const std::string& if_name,
                                    PortID idx = InvalidPortID) override;

    };

* Initialize things in construcutor

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        MemObject(params),
        instPort(params->name + ".inst_port", this),
        dataPort(params->name + ".data_port", this),
        memPort(params->name + ".mem_side", this),
    {
    }

* Implement getMasterPort

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    BaseMasterPort&
    HelloObject::getMasterPort(const std::string& if_name, PortID idx)
    {
        if (if_name == "mem_side") {
            return memPort;
        } else {
            return MemObject::getMasterPort(if_name, idx);
        }
    }

* Implement getSlavePort

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    BaseSlavePort&
    HelloObject::getSlavePort(const std::string& if_name, PortID idx)
    {
        if (if_name == "inst_port") {
            return instPort;
        } else if (if_name == "data_port") {
            return dataPort;
        } else {
            return MemObject::getSlavePort(if_name, idx);
        }
    }

* This shows how all of these functions relate. I really want to show this a little at a time as I go through this. Drawing on the board would be perfect...

.. figure:: ../_static/figures/memobj_api.png
   :width: 100 %

   System

* Pass through some of the functions for CPU side port

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    AddrRangeList
    HelloObject::CPUSidePort::getAddrRanges() const
    {
        return owner->getAddrRanges();
    }

    AddrRangeList
    HelloObject::getAddrRanges() const
    {
        DPRINTF(HelloObject, "Sending new ranges\n");
        return memPort.getAddrRanges();
    }

    void
    HelloObject::CPUSidePort::recvFunctional(PacketPtr pkt)
    {
        return owner->handleFunctional(pkt);
    }

    void
    HelloObject::handleFunctional(PacketPtr pkt)
    {
        memPort.sendFunctional(pkt);
    }

* Pass through some of the functions for Mem side port

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::MemSidePort::recvRangeChange()
    {
        owner->sendRangeChange();
    }

    void
    HelloObject::sendRangeChange()
    {
        instPort.sendRangeChange();
        dataPort.sendRangeChange();
    }

---------------------------------------------

* NOw the fun part. Implementing the send/receives
* Let's start with receive

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::CPUSidePort::recvTimingReq(PacketPtr pkt)
    {
        if (!owner->handleRequest(pkt)) {
            needRetry = true;
            return false;
        } else {
            return true;
        }
    }

* Add variable to remember when we need to send the CPU a retry

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
        bool needRetry;

* Now, we need to do handle request

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::handleRequest(PacketPtr pkt)
    {
        if (blocked) {
            return false;
        }
        DPRINTF(HelloObject, "Got request for addr %#x\n", pkt->getAddr());
        blocked = true;
        memPort.sendPacket(pkt);
        return true;
    }

* Let's add a convienency function in the memside port

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::MemSidePort::sendPacket(PacketPtr pkt)
    {
        panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");
        if (!sendTimingReq(pkt)) {
            blockedPacket = pkt;
        }
    }

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class MemSidePort : public MasterPort {
        PacketPtr blockedPacket;
      public:
        void sendPacket(PacketPtr pkt);

* Implement code to handle retries

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::MemSidePort::recvReqRetry()
    {
        assert(blockedPacket != nullptr);

        PacketPtr pkt = blockedPacket;
        blockedPacket = nullptr;

        sendPacket(pkt);
    }

---------------------------------------------------------------

* Implement the code for receiving responses

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::MemSidePort::recvTimingResp(PacketPtr pkt)
    {
        return owner->handleResponse(pkt);
    }

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::handleResponse(PacketPtr pkt)
    {
        assert(blocked);
        DPRINTF(HelloObject, "Got response for addr %#x\n", pkt->getAddr());

        blocked = false;

        // Simply forward to the memory port
        if (pkt->req->isInstFetch()) {
            instPort.sendPacket(pkt);
        } else {
            dataPort.sendPacket(pkt);
        }

        return true;
    }

* Now, we need the convience function to send packets

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
        PacketPtr blockedPacket;
      public:
        void sendPacket(PacketPtr pkt);

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::CPUSidePort::sendPacket(PacketPtr pkt)
    {
        panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");

        if (!sendTimingResp(pkt)) {
            blockedPacket = pkt;
        }
    }

* Implement recvRespRetry

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::CPUSidePort::recvRespRetry()
    {
        assert(blockedPacket != nullptr);

        PacketPtr pkt = blockedPacket;
        blockedPacket = nullptr;

        sendPacket(pkt);
    }

* Implement trySendRetry

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort {
        void trySendRetry();

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::CPUSidePort::trySendRetry()
    {
        if (needRetry && blockedPacket == nullptr) {
            needRetry = false;
            DPRINTF(HelloObject, "Sending retry req for %d\n", id);
            sendRetryReq();
        }
    }


hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    HelloObject::handleResponse(PacketPtr pkt)
    {
        instPort.trySendRetry();
        dataPort.trySendRetry();

-----------------------------------

* Update simple config file

simple.py
~~~~~~~~~
.. code-block:: python

    system.cpu = TimingSimpleCPU()

    system.memobj = HelloObject()

    system.cpu.icache_port = system.memobj.inst_port
    system.cpu.dcache_port = system.memobj.data_port

    system.membus = SystemXBar()

    system.memobj.mem_side = system.membus.slave

* Run simple.py

---------------------------------------------

Making a cache
--------------

* Add parameters to memobj

HelloObject.py
~~~~~~~~~~~~~~~
.. code-block:: python

    latency = Param.Cycles(1, "Cycles taken on a hit or to resolve a miss")

    size = Param.MemorySize('16kB', "The size of the cache")

    system = Param.System(Parent.any, "The system this cache is part of")

* Talk about the parent.any proxy parameter

* Add latency/size/system to constructor

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    latency(params->latency),
    blockSize(params->system->cacheLineSize()),
    capacity(params->size / blockSize),

* Implement new "handleRequest"

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::handleRequest(PacketPtr pkt, int port_id)
    {
        if (blocked) {
            return false;
        }
        DPRINTF(HelloObject, "Got request for addr %#x\n", pkt->getAddr());

        blocked = true;
        waitingPortId = port_id;

        schedule(new AccessEvent(this, pkt), clockEdge(latency));

        return true;
    }

* Talk about the clockEdge function and clocked-objects

* Implement the access event

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class AccessEvent : public Event
    {
      private:
        HelloObject *cache;
        PacketPtr pkt;
      public:
        AccessEvent(HelloObject *cache, PacketPtr pkt) :
            Event(Default_Pri, AutoDelete), cache(cache), pkt(pkt)
        { }
        void process() override {
            cache->accessTiming(pkt);
        }
    };

* Implement the accessTiming function

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void accessTiming(PacketPtr pkt);

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            pkt->makeResponse();
            sendResponse(pkt);
        } else {
            <miss handling>
        }
    }

* Note; It's a good idea to separate out functional from timing functions
* Miss handling is complicated by the block size

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::accessTiming(PacketPtr pkt)
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
                DPRINTF(HelloObject, "forwarding packet\n");
                memPort.sendPacket(pkt);
            } else {
                DPRINTF(HelloObject, "Upgrading packet to block size\n");
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

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    PacketPtr outstandingPacket;

* Update handle response to be able to accept responses from the upgraded packets

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::handleResponse(PacketPtr pkt)
    {
        assert(blocked);
        DPRINTF(HelloObject, "Got response for addr %#x\n", pkt->getAddr());
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

-------------------------------------------------------

* Implementing the functional cache logic, now.

hello_object.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void insert(PacketPtr pkt);
    bool accessFunctional(PacketPtr pkt);
    std::unordered_map<Addr, uint8_t*> cacheStore;

* Implement the access logic

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    HelloObject::accessFunctional(PacketPtr pkt)
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

* Implement the insert logic

hello_object.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    HelloObject::insert(PacketPtr pkt)
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

            DPRINTF(HelloObject, "Writing packet back %s\n", pkt->print());
            memPort.sendTimingReq(new_pkt);

            cacheStore.erase(block->first);
        }
        uint8_t *data = new uint8_t[blockSize];
        cacheStore[pkt->getAddr()] = data;

        pkt->writeDataToBlock(data, blockSize);
    }

---------------------------------------------

* update the config file

simple.py
~~~~~~~~~
.. code-block:: python

    system.memobj = HelloObject(size='1kB')

* Run it!
