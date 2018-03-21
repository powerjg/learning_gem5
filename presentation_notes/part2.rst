:authors: Jason Lowe-Power

Part II: Modifying and extending gem5
=====================================

Setting up development environment
----------------------------------

* Use the style guide
* Install the style guide
  * You'll get errors when you try to commit.
  * Can be overridden, if needed.
* Use git branches

--------------------------------------

Simple SimObject
----------------

* Slide on outline of making a SimObject

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* New branch: part2 (builds off of part1)
* Create new folder src/tutorial

Step 1: Create a Python class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Every SimObject needs a SimObject declaration file
* Create a file src/tutorial/Hello.py

.. code-block:: python

    from m5.params import *
    from m5.SimObject import SimObject

    class Hello(SimObject):
        type = 'Hello'
        cxx_header = "tutorial/hello.hh"

* Talk about what these things mean

Step 2: Implement your SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Declare C++ file. Edit src/tutorial/hello.hh

.. code-block:: c++

    #ifndef __TUTORIAL_HELLO_HH__
    #define __TUTORIAL_HELLO_HH__

    #include "params/Hello.hh"
    #include "sim/sim_object.hh"

    class Hello : public SimObject
    {
      public:
        Hello(HelloParams *p);
    };

    #endif // __TUTORIAL_HELLO_HH__

* Explain the header file.

* Define the SimObject functions

.. code-block:: c++

    #include "tutorial/hello.hh"

    #include <iostream>

    Hello::Hello(HelloParams *params) : SimObject(params)
    {
        std::cout << "Hello World! From a SimObject!" << std::endl;
    }

* Every SimObject constructor takes a single parameter, the parameters.

* Define the Params create function

.. code-block:: python

    Hello*
    HelloParams::create()
    {
        return new Hello(this);
    }

* This is what calls the constructor. This is called when m5.instantiate() happens in the run script.

Step 3: Register the SimObject and C++ files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Edit src/tutorial/SConscript

.. code-block:: python

    Import('*')

    SimObject('Hello.py')
    Source('hello.cc')

* Explain the SConscript file

Step 4: Recompile
~~~~~~~~~~~~~~~~~
* Recompile gem5

.. code-block:: sh

    scons -j5 build/X86/gem5.opt

Step 5: Write a run/config script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Edit configs/tutorial/hello_run.py

* Again, import all gem5 objects

.. code-block:: python

    import m5
    from m5.objects import *

* Create the root object

.. code-block:: python

    root = Root(full_system = False)

* instantiate the hello object

.. code-block:: python

    root.hello = Hello()

* instantiate gem5 objects in C++ and run the simulation

.. code-block:: python

    m5.instantiate()

    print "Beginning simulation!"
    exit_event = m5.simulate()
    print 'Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause())

* Run gem5!

.. code-block:: python

    build/X86/gem5.opt configs/tutorial/hello_run.py

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

* Using iostream is bad! Think of what would happen if every single object had lots of print statements? How about when you need to debug something and you have to add a million print statements?
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

* Declare a debug flag in src/tutorial/SConscript

.. code-block:: python

    DebugFlag('HelloDebug')

* Add a debug statement in src/tutorial/hello.cc

.. code-block:: c++

    #include "debug/HelloDebug.hh"

    ...

    DPRINTF(HelloDebug, "Created the hello object\n");

* Build gem5 and run it with "hello" debug flag

.. code-block:: sh

    build/X86/gem5.opt --debug-flags=HelloDebug configs/tutorial/hello_run.py

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Other debug flags

.. code-block:: sh

    build/X86/gem5.opt --debug-flags=DRAM configs/learning_gem5/part1/simple.py | head -n 50
    build/X86/gem5.opt --debug-flags=Exec configs/learning_gem5/part1/simple.py | head -n 50

* Go over debugging slide

--------------------------------------

Event-driven programming
------------------------

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Add an event wrapper to the Hello from last chapter.
* Add a processEvent function

hello.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

      private:
        void processEvent();

        EventWrapper<Hello, &Hello::processEvent> event;

* Initialize the event
* Implement the processEvent function

hello.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    Hello::Hello(HelloParams *params) :
        SimObject(params), event([this]{processEvent();}, name())

    void
    Hello::processEvent()
    {
        DPRINTF(HelloDebug, "Hello world! Processing the event!\n");
    }

* Add a startup function to the header
* Schedule an event

hello.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

    void startup();

hello.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::startup()
    {
        schedule(event, 100);
    }

* Recompile and run gem5

--------------------------------------

* Add two parameters to class: latency, timesLeft

hello.hh
~~~~~~~~~~~~~~~
.. code-block:: c++

        Tick latency;

        int timesLeft;

* Initialize these parameters

hello.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    Hello::Hello(HelloParams *params) :
        SimObject(params),
    event([this]{processEvent();}, name()),
    latency(100), timesLeft(10)

* update startup and process event

hello.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::startup()
    {
        schedule(event, latency);
    }

    void
    Hello::processEvent()
    {
        timesLeft--;
        DPRINTF(HelloDebug, "Hello world! Processing the event! %d left\n",
                timesLeft);

        if (timesLeft <= 0) {
            DPRINTF(HelloDebug, "Done firing!\n");
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

Hello.py
~~~~~~~~~~~~~~
.. code-block:: python

    class Hello(SimObject):
        type = 'Hello'
        cxx_header = "tutorial/hello.hh"

        time_to_wait = Param.Latency("Time before firing the event")
        number_of_fires = Param.Int(1, "Number of times to fire the event before "
                                       "goodbye")

* Update the constructor

hello.cc
~~~~~~~~~~~~~~~
.. code-block:: c++

    Hello::Hello(HelloParams *params) :
        SimObject(params),
        event([this]{processEvent();}, name()),
        latency(params->time_to_wait),
        timesLeft(params->number_of_fires)


* Run gem5 without updating the config file and get an error
* Fix the above error

run_hello.py
~~~~~~~~~~~~
.. code-block:: python

    root.hello = Hello(time_to_wait = '2us')

* or

.. code-block:: python

    root.hello = Hello()
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

Hello.py
~~~~~~~~~~~~~~~
.. code-block:: python

    ...
    from MemObject import MemObject

    class Hello(MemObject):
        ...

        inst_port = SlavePort("CPU side port, receives requests")
        data_port = SlavePort("CPU side port, receives requests")
        mem_side = MasterPort("Memory side port, sends requests")

* Define the header file
* Point out "public MemObject"

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    #include "mem/mem_object.hh"

    Hello : public MemObject

* Define the CPU-side slave port
* Talk about each of the functions below

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
      private:
        Hello *owner;

      public:
        CPUSidePort(const std::string& name, Hello *owner) :
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

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class MemSidePort : public MasterPort
    {
      private:
        Hello *owner;

      public:
        MemSidePort(const std::string& name, Hello *owner) :
            MasterPort(name, owner), owner(owner)
        { }

      protected:
        bool recvTimingResp(PacketPtr pkt) override;
        void recvReqRetry() override;
        void recvRangeChange() override;
    };

* Define the MemObject interface

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class Hello : public MemObject
    {
      private:

        <CPUSidePort declaration>
        <MemSidePort declaration>

        CPUSidePort instPort;
        CPUSidePort dataPort;

        MemSidePort memPort;

      public:
        Hello(HelloParams *params);

        BaseMasterPort& getMasterPort(const std::string& if_name,
                                      PortID idx = InvalidPortID) override;

        BaseSlavePort& getSlavePort(const std::string& if_name,
                                    PortID idx = InvalidPortID) override;

    };

* Initialize things in construcutor

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    Hello::Hello(HelloParams *params) :
        MemObject(params),
        instPort(params->name + ".inst_port", this),
        dataPort(params->name + ".data_port", this),
        memPort(params->name + ".mem_side", this),
    {
    }

* Implement getMasterPort

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    BaseMasterPort&
    Hello::getMasterPort(const std::string& if_name, PortID idx)
    {
        if (if_name == "mem_side") {
            return memPort;
        } else {
            return MemObject::getMasterPort(if_name, idx);
        }
    }

* Implement getSlavePort

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    BaseSlavePort&
    Hello::getSlavePort(const std::string& if_name, PortID idx)
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

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    AddrRangeList
    Hello::CPUSidePort::getAddrRanges() const
    {
        return owner->getAddrRanges();
    }

    AddrRangeList
    Hello::getAddrRanges() const
    {
        DPRINTF(HelloDebug, "Sending new ranges\n");
        return memPort.getAddrRanges();
    }

    void
    Hello::CPUSidePort::recvFunctional(PacketPtr pkt)
    {
        return owner->handleFunctional(pkt);
    }

    void
    Hello::handleFunctional(PacketPtr pkt)
    {
        memPort.sendFunctional(pkt);
    }

* Pass through some of the functions for Mem side port

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::MemSidePort::recvRangeChange()
    {
        owner->sendRangeChange();
    }

    void
    Hello::sendRangeChange()
    {
        instPort.sendRangeChange();
        dataPort.sendRangeChange();
    }

hello.hh
~~~~~~~~
.. code-block:: c++

    AddrRangeList getAddrRanges() const;
    void handleFunctional(PacketPtr pkt);
    void sendRangeChange();

    bool handleRequest(PacketPtr pkt);
    bool handleResponse(PacketPtr pkt);


---------------------------------------------

* NOW the fun part. Implementing the send/receives
* Let's start with receive

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::CPUSidePort::recvTimingReq(PacketPtr pkt)
    {
        if (!owner->handleRequest(pkt)) {
            needRetry = true;
            return false;
        } else {
            return true;
        }
    }

* Add variable to remember when we need to send the CPU a retry

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
        bool needRetry;
        ...
        CPUSidePort(const std::string& name, Hello *owner) :
            SlavePort(name, owner), owner(owner), needRetry(false)

* Now, we need to do handle request

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::handleRequest(PacketPtr pkt)
    {
        if (blocked) {
            return false;
        }
        DPRINTF(HelloDebug, "Got request for addr %#x\n", pkt->getAddr());
        blocked = true;
        memPort.sendPacket(pkt);
        return true;
    }

hello.hh
~~~~~~~~~
.. code-block:: c++

    bool blocked;

hello.cc
~~~~~~~~
.. code-block:: c++

    <constructor>,
    blocked(false)


* Let's add a convenience function in the memside port

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::MemSidePort::sendPacket(PacketPtr pkt)
    {
        panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");
        if (!sendTimingReq(pkt)) {
            blockedPacket = pkt;
        }
    }

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class MemSidePort : public MasterPort {
        PacketPtr blockedPacket;
      public:
        void sendPacket(PacketPtr pkt);

* Implement code to handle retries

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::MemSidePort::recvReqRetry()
    {
        assert(blockedPacket != nullptr);

        PacketPtr pkt = blockedPacket;
        blockedPacket = nullptr;

        sendPacket(pkt);
    }

---------------------------------------------------------------

* Implement the code for receiving responses

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::MemSidePort::recvTimingResp(PacketPtr pkt)
    {
        return owner->handleResponse(pkt);
    }

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::handleResponse(PacketPtr pkt)
    {
        assert(blocked);
        DPRINTF(HelloDebug, "Got response for addr %#x\n", pkt->getAddr());

        blocked = false;

        // Simply forward to the memory port
        if (pkt->req->isInstFetch()) {
            instPort.sendPacket(pkt);
        } else {
            dataPort.sendPacket(pkt);
        }

        return true;
    }

* Now, we need the convenience function to send packets

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort
    {
        PacketPtr blockedPacket;
        // ADD TO THE CONSTRUCTOR!!!!
        , blockedPacket(nullptr)
      public:
        void sendPacket(PacketPtr pkt);

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::CPUSidePort::sendPacket(PacketPtr pkt)
    {
        panic_if(blockedPacket != nullptr, "Should never try to send if blocked!");

        if (!sendTimingResp(pkt)) {
            blockedPacket = pkt;
        }
    }

* Implement recvRespRetry

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::CPUSidePort::recvRespRetry()
    {
        assert(blockedPacket != nullptr);

        PacketPtr pkt = blockedPacket;
        blockedPacket = nullptr;

        sendPacket(pkt);
    }

* Implement trySendRetry

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    class CPUSidePort : public SlavePort {
      public:
        void trySendRetry();

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::CPUSidePort::trySendRetry()
    {
        if (needRetry && blockedPacket == nullptr) {
            needRetry = false;
            DPRINTF(HelloDebug, "Sending retry req for %d\n", id);
            sendRetryReq();
        }
    }


hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    Hello::handleResponse(PacketPtr pkt)
    {
        instPort.trySendRetry();
        dataPort.trySendRetry();

-----------------------------------

* Update simple config file SIMPLE CONFIG FILE

simple.py
~~~~~~~~~
.. code-block:: python

    system.cpu = TimingSimpleCPU()

    system.memobj = Hello()

    system.cpu.icache_port = system.memobj.inst_port
    system.cpu.dcache_port = system.memobj.data_port

    system.membus = SystemXBar()

    system.memobj.mem_side = system.membus.slave

* Run simple.py

---------------------------------------------

Making a cache
--------------

* Add parameters to memobj

Hello.py
~~~~~~~~~~~~~~~

* Remove the old parameters.

.. code-block:: python

    from m5.proxy import *

    latency = Param.Cycles(1, "Cycles taken on a hit or to resolve a miss")

    size = Param.MemorySize('16kB', "The size of the cache")

    system = Param.System(Parent.any, "The system this cache is part of")

* Talk about the parent.any proxy parameter

* Add latency/size/system to constructor

* Remove implementation of processEvent and startup.

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    #include "sim/system.hh"

    latency(params->latency),
    blockSize(params->system->cacheLineSize()),
    capacity(params->size / blockSize),

* Add latency, blockSize, and capacity to header.
* Remove timesLeft, event, and processEvent, startup

hello.hh
~~~~~~~~~

.. code-block:: c++

      private:

        Cycles latency; **** NOW CYCLE

        int blockSize;

        // Number of blocks in the cache
        uint32_t capacity;


* Implement new "handleRequest"

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::handleRequest(PacketPtr pkt, int port_id)
    {
        if (blocked) {
            return false;
        }
        DPRINTF(HelloDebug, "Got request for addr %#x\n", pkt->getAddr());

        blocked = true;

        schedule(new EventFunctionWrapper([this, pkt]{ accessTiming(pkt); },
                                          name() + ".access",
                                          true), // auto delete
                 clockEdge(latency));

        return true;
    }

* Talk about the clockEdge function and clocked-objects

* Implement the accessTiming function

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void accessTiming(PacketPtr pkt);

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            pkt->makeResponse();
            blocked = false;
            if (pkt->req->isInstFetch()) {
                instPort.sendPacket(pkt);
            } else {
                dataPort.sendPacket(pkt);
            }
            instPort.trySendRetry();
            dataPort.trySendRetry();
        } else {
            <miss handling>
        }
    }

* Note; It's a good idea to separate out functional from timing functions
* Miss handling is complicated by the block size

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::accessTiming(PacketPtr pkt)
    {
        bool hit = accessFunctional(pkt);
        if (hit) {
            <....>
        } else {
            Addr addr = pkt->getAddr();
            Addr block_addr = pkt->getBlockAddr(blockSize);
            unsigned size = pkt->getSize();

            DPRINTF(HelloDebug, "Upgrading packet to block size\n");
            panic_if(addr - block_addr + size > blockSize,
                     "Cannot handle accesses that span multiple cache lines");

            assert(pkt->needsResponse());
            MemCmd cmd;
            if (pkt->isWrite() || pkt->isRead()) {
                cmd = MemCmd::ReadReq;
            } else {
                panic("Unknown packet type in upgrade size");
            }
            // packet automatically aligned to block size!
            PacketPtr new_pkt = new Packet(pkt->req, cmd, blockSize);
            new_pkt->allocate();

            outstandingPacket = pkt; // Save original packet

            memPort.sendPacket(new_pkt);
        }
    }

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    PacketPtr outstandingPacket;

* Update handle response to be able to accept responses from the upgraded packets

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::handleResponse(PacketPtr pkt)
    {
        assert(blocked);
        DPRINTF(HelloDebug, "Got response for addr %#x\n", pkt->getAddr());
        insert(pkt);

        assert(outstandingPacket != nullptr);

        accessFunctional(outstandingPacket);
        outstandingPacket->makeResponse();
        delete pkt;
        pkt = outstandingPacket;
        outstandingPacket = nullptr;

        sendResponse(pkt);

        return true;
    }

-------------------------------------------------------

* Implementing the functional cache logic, now.

hello.hh
~~~~~~~~~~~~~~~~
.. code-block:: c++

    #include <unordered_map>

    void insert(PacketPtr pkt);
    bool accessFunctional(PacketPtr pkt);
    std::unordered_map<Addr, uint8_t*> cacheStore;

* Implement the access logic

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    bool
    Hello::accessFunctional(PacketPtr pkt)
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

hello.cc
~~~~~~~~~~~~~~~~
.. code-block:: c++

    void
    Hello::insert(PacketPtr pkt)
    {
        if (cacheStore.size() >= capacity) {
            auto block = cacheStore.begin(); // Replace the "first" element

            // WE don't track clean/dirty, so write back everything
            RequestPtr req = new Request(block->first, blockSize, 0, 0);
            PacketPtr new_pkt = new Packet(req, MemCmd::WritebackDirty, blockSize);
            new_pkt->dataDynamic(block->second); // This will be deleted later

            DPRINTF(HelloDebug, "Writing packet back %s\n", pkt->print());
            memPort.sendTimingReq(new_pkt);

            cacheStore.erase(block->first);
        }
        // Make the miss request.
        uint8_t *data = new uint8_t[blockSize];
        cacheStore[pkt->getAddr()] = data;

        pkt->writeDataToBlock(data, blockSize);
    }

* finally, need to make sure functional accesses work!

.. code-block:: c++

    void
    Hello::handleFunctional(PacketPtr pkt)
    {
        accessFunctional(pkt); // can ignore hit/miss
        memPort.sendFunctional(pkt);
    }

---------------------------------------------

* update the config file

simple.py
~~~~~~~~~
.. code-block:: python

    system.memobj = Hello(size='1kB')

* Run it!

* Show at 1KB vs 16KB the time is different.

* python3 -c "print(OLD/NEW)"

* Slides on things to remember from implementing the cache

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!
