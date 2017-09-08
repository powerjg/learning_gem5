:authors: Jason Lowe-Power

.. _MSI-directory-section:

------------------------------------------
MSI Directory implementation
------------------------------------------

Implementing a directory controller is very similar to the L1 cache controller, except using a different state machine table.
The state machine fore the directory can be found in Table 8.2 in Sorin et al.
Since things are mostly similar to the L1 cache, this section mostly just discusses a few more SLICC details and a few differences between directory controllers and cache controllers.
Let's dive straight in and start modifying a new file ``MSI-dir.sm``.

.. code-block:: c++

    machine(MachineType:Directory, "Directory protocol")
    :
      DirectoryMemory * directory;
      Cycles toMemLatency := 1;

    MessageBuffer *forwardToCache, network="To", virtual_network="1",
          vnet_type="forward";
    MessageBuffer *responseToCache, network="To", virtual_network="2",
          vnet_type="response";

    MessageBuffer *requestFromCache, network="From", virtual_network="0",
          vnet_type="request";

    MessageBuffer *responseFromCache, network="From", virtual_network="2",
          vnet_type="response";

    MessageBuffer *responseFromMemory;

    {
    . . .
    }

First, there are two parameter to this directory controller, ``DirectoryMemroy`` and a ``toMemLatency``.
The ``DirectoryMemory`` is a little weird.
It is allocated at initialization time such that it can cover *all* of physical memory, like a complete directory *not a directory cache*.
I.e., there are pointers in the ``DirectoryMemory`` object for every 64-byte block in physical memory.
However, the actual entries (as defined below) are lazily created via ``getDirEntry()``.
We'll see more details about ``DirectoryMemory`` below.

Next, is the ``toMemLatency`` parameter.
This will be used in the ``enqueue`` function when enqueing requests to model the directory latency.
We didn't use a parameter for this in the L1 cache, but it is simple to make the controller latency parameterized.
This parameter defaults to 1 cycle.
It is not required to set a default here.
The default is propagated to the generated SimObject description file as the default to the SimObject parameter.

Next, we have the message buffers for the directory.
Importantly, *these need to have the same virtual network numbers* as the message buffers in the L1 cache.
These virtual network numbers are how the Ruby network directs messages between controllers.

There is also one more special message buffer: ``responseFromMemory``.
This is similar to the ``mandatoryQueue``, except instead of being a slave port for CPUs it is like a master port.
The ``responseFromMemory`` buffer will deliver response sent across the the memory port, as we will see below in the action section.

After the parameters and message buffers, we need to declare all of the states, events, and other local structures.

.. code-block:: c++

    state_declaration(State, desc="Directory states",
                      default="Directory_State_I") {
        // Stable states.
        // NOTE: Thise are "cache-centric" states like in Sorin et al.
        // However, The access permissions are memory-centric.
        I, AccessPermission:Read_Write,  desc="Invalid in the caches.";
        S, AccessPermission:Read_Only,   desc="At least one cache has the blk";
        M, AccessPermission:Invalid,     desc="A cache has the block in M";

        // Transient states
        S_D, AccessPermission:Busy,      desc="Moving to S, but need data";

        // Waiting for data from memory
        S_m, AccessPermission:Read_Write, desc="In S waiting for mem";
        M_m, AccessPermission:Read_Write, desc="Moving to M waiting for mem";

        // Waiting for write-ack from memory
        MI_m, AccessPermission:Busy,       desc="Moving to I waiting for ack";
        SS_m, AccessPermission:Busy,       desc="Moving to I waiting for ack";
    }

    enumeration(Event, desc="Directory events") {
        // Data requests from the cache
        GetS,         desc="Request for read-only data from cache";
        GetM,         desc="Request for read-write data from cache";

        // Writeback requests from the cache
        PutSNotLast,  desc="PutS and the block has other sharers";
        PutSLast,     desc="PutS and the block has no other sharers";
        PutMOwner,    desc="Dirty data writeback from the owner";
        PutMNonOwner, desc="Dirty data writeback from non-owner";

        // Cache responses
        Data,         desc="Response to fwd request with data";

        // From Memory
        MemData,      desc="Data from memory";
        MemAck,       desc="Ack from memory that write is complete";
    }

    structure(Entry, desc="...", interface="AbstractEntry") {
        State DirState,         desc="Directory state";
        NetDest Sharers,        desc="Sharers for this block";
        NetDest Owner,          desc="Owner of this block";
    }


In the ``state_declaration`` we define a default.
For many things in SLICC you can specify a default.
However, this default must use the C++ name (mangled SLICC name).
For the state below you have to use the controller name and the name we use for states.
In this case, since the name of the machine is "Directory" the name for "I" is "Directory"+"State" (for the name of the structure)+"I".

Note that the permissions in the directory are "memory-centric".
Whereas, all of the states are cache centric as in Sorin et al.

In the ``Entry`` definition for the directory, we use a NetDest for both the sharers and the owner.
This makes sense for the sharers, since we want a full bitvector for all L1 caches that may be sharing the block.
The reason we also use a ``NetDest`` for the owner is to simply copy the structure into the message we send as a response as shown below.

In this implementation, we use a few more transient states than in Table 8.2 in Sorin et al. to deal with the fact that the memory latency in unknown.
In Sorin et al., the authors assume that the directory state and memory data is stored together in main-memory to simplify the protocol.
Similarly, we also include new actions: the responses from memory.

Next, we have the functions that need to overridden and declared.
The function ``getDirectoryEntry`` either returns the valid directory entry, or, if it hasn't been allocated yet, this allocates the entry.
Implementing it this way may save some host memory  since this is lazily populated.

.. code-block:: c++

    Tick clockEdge();

    Entry getDirectoryEntry(Addr addr), return_by_pointer = "yes" {
        Entry dir_entry := static_cast(Entry, "pointer", directory[addr]);
        if (is_invalid(dir_entry)) {
            // This first time we see this address allocate an entry for it.
            dir_entry := static_cast(Entry, "pointer",
                                     directory.allocate(addr, new Entry));
        }
        return dir_entry;
    }

    State getState(Addr addr) {
        if (directory.isPresent(addr)) {
            return getDirectoryEntry(addr).DirState;
        } else {
            return State:I;
        }
    }

    void setState(Addr addr, State state) {
        if (directory.isPresent(addr)) {
            if (state == State:M) {
                DPRINTF(RubySlicc, "Owner %s\n", getDirectoryEntry(addr).Owner);
                assert(getDirectoryEntry(addr).Owner.count() == 1);
                assert(getDirectoryEntry(addr).Sharers.count() == 0);
            }
            getDirectoryEntry(addr).DirState := state;
            if (state == State:I)  {
                assert(getDirectoryEntry(addr).Owner.count() == 0);
                assert(getDirectoryEntry(addr).Sharers.count() == 0);
            }
        }
    }

    AccessPermission getAccessPermission(Addr addr) {
        if (directory.isPresent(addr)) {
            Entry e := getDirectoryEntry(addr);
            return Directory_State_to_permission(e.DirState);
        } else  {
            return AccessPermission:NotPresent;
        }
    }
    void setAccessPermission(Addr addr, State state) {
        if (directory.isPresent(addr)) {
            Entry e := getDirectoryEntry(addr);
            e.changePermission(Directory_State_to_permission(state));
        }
    }

    void functionalRead(Addr addr, Packet *pkt) {
        functionalMemoryRead(pkt);
    }

    int functionalWrite(Addr addr, Packet *pkt) {
        if (functionalMemoryWrite(pkt)) {
            return 1;
        } else {
            return 0;
        }


Next, we need to implement the ports for the cache.
First we specify the ``out_port`` and then the ``in_port`` code blocks.
The only difference between the ``in_port`` in the directory and in the L1 cache is that the directory does not have a TBE or cache entry.
Thus, we do not pass either into the ``trigger`` function.

.. code-block:: c++

    out_port(forward_out, RequestMsg, forwardToCache);
    out_port(response_out, ResponseMsg, responseToCache);

    in_port(memQueue_in, MemoryMsg, responseFromMemory) {
        if (memQueue_in.isReady(clockEdge())) {
            peek(memQueue_in, MemoryMsg) {
                if (in_msg.Type == MemoryRequestType:MEMORY_READ) {
                    trigger(Event:MemData, in_msg.addr);
                } else if (in_msg.Type == MemoryRequestType:MEMORY_WB) {
                    trigger(Event:MemAck, in_msg.addr);
                } else {
                    error("Invalid message");
                }
            }
        }
    }

    in_port(response_in, ResponseMsg, responseFromCache) {
        if (response_in.isReady(clockEdge())) {
            peek(response_in, ResponseMsg) {
                if (in_msg.Type == CoherenceResponseType:Data) {
                    trigger(Event:Data, in_msg.addr);
                } else {
                    error("Unexpected message type.");
                }
            }
        }
    }

    in_port(request_in, RequestMsg, requestFromCache) {
        if (request_in.isReady(clockEdge())) {
            peek(request_in, RequestMsg) {
                Entry e := getDirectoryEntry(in_msg.addr);
                if (in_msg.Type == CoherenceRequestType:GetS) {

                    trigger(Event:GetS, in_msg.addr);
                } else if (in_msg.Type == CoherenceRequestType:GetM) {
                    trigger(Event:GetM, in_msg.addr);
                } else if (in_msg.Type == CoherenceRequestType:PutS) {
                    assert(is_valid(e));
                    // If there is only a single sharer (i.e., the requestor)
                    if (e.Sharers.count() == 1) {
                        assert(e.Sharers.isElement(in_msg.Requestor));
                        trigger(Event:PutSLast, in_msg.addr);
                    } else {
                        trigger(Event:PutSNotLast, in_msg.addr);
                    }
                } else if (in_msg.Type == CoherenceRequestType:PutM) {
                    assert(is_valid(e));
                    if (e.Owner.isElement(in_msg.Requestor)) {
                        trigger(Event:PutMOwner, in_msg.addr);
                    } else {
                        trigger(Event:PutMNonOwner, in_msg.addr);
                    }
                } else {
                    error("Unexpected message type.");
                }
            }
        }
    }


The next part of the state machine file is the actions.
First, we define actions for queuing memory reads and writes.
For this, we will use a special function define in the ``AbstractController``: ``queueMemoryRead``.
This function takes an address and converts it to a gem5 request and packet and sends it to across the port that is connected to this controller.
We will see how to connect this port in the :ref:`configuration section <MSI-config-section>`.
Note that we need two different actions to send data to memory for both requests and responses since there are two different message buffers (virtual networks) that data might arrive on.

.. code-block:: c++

    action(sendMemRead, "r", desc="Send a memory read request") {
        peek(request_in, RequestMsg) {
            queueMemoryRead(in_msg.Requestor, address, toMemLatency);
        }
    }

    action(sendDataToMem, "w", desc="Write data to memory") {
        peek(request_in, RequestMsg) {
            DPRINTF(RubySlicc, "Writing memory for %#x\n", address);
            DPRINTF(RubySlicc, "Writing %s\n", in_msg.DataBlk);
            queueMemoryWrite(in_msg.Requestor, address, toMemLatency,
                             in_msg.DataBlk);
        }
    }

    action(sendRespDataToMem, "rw", desc="Write data to memory from resp") {
        peek(response_in, ResponseMsg) {
            DPRINTF(RubySlicc, "Writing memory for %#x\n", address);
            DPRINTF(RubySlicc, "Writing %s\n", in_msg.DataBlk);
            queueMemoryWrite(in_msg.Sender, address, toMemLatency,
                             in_msg.DataBlk);
        }
    }


In this code, we also see the last way to add debug information to SLICC protocols: ``DPRINTF``.
This is exactly the same as a ``DPRINTF`` in gem5, except in SLICC only the ``RubySlicc`` debug flag is available.

Next, we specify actions to update the sharers and owner of a particular block.

.. code-block:: c++

    action(addReqToSharers, "aS", desc="Add requestor to sharer list") {
        peek(request_in, RequestMsg) {
            getDirectoryEntry(address).Sharers.add(in_msg.Requestor);
        }
    }

    action(setOwner, "sO", desc="Set the owner") {
        peek(request_in, RequestMsg) {
            getDirectoryEntry(address).Owner.add(in_msg.Requestor);
        }
    }

    action(addOwnerToSharers, "oS", desc="Add the owner to sharers") {
        Entry e := getDirectoryEntry(address);
        assert(e.Owner.count() == 1);
        e.Sharers.addNetDest(e.Owner);
    }

    action(removeReqFromSharers, "rS", desc="Remove requestor from sharers") {
        peek(request_in, RequestMsg) {
            getDirectoryEntry(address).Sharers.remove(in_msg.Requestor);
        }
    }

    action(clearSharers, "cS", desc="Clear the sharer list") {
        getDirectoryEntry(address).Sharers.clear();
    }

    action(clearOwner, "cO", desc="Clear the owner") {
        getDirectoryEntry(address).Owner.clear();
    }

The next set of actions send invalidates and forward requests to caches that the directory cannot deal with alone.

.. code-block:: c++

    action(sendInvToSharers, "i", desc="Send invalidate to all sharers") {
        peek(request_in, RequestMsg) {
            enqueue(forward_out, RequestMsg, 1) {
                out_msg.addr := address;
                out_msg.Type := CoherenceRequestType:Inv;
                out_msg.Requestor := in_msg.Requestor;
                out_msg.Destination := getDirectoryEntry(address).Sharers;
                out_msg.MessageSize := MessageSizeType:Control;
            }
        }
    }

    action(sendFwdGetS, "fS", desc="Send forward getS to owner") {
        assert(getDirectoryEntry(address).Owner.count() == 1);
        peek(request_in, RequestMsg) {
            enqueue(forward_out, RequestMsg, 1) {
                out_msg.addr := address;
                out_msg.Type := CoherenceRequestType:GetS;
                out_msg.Requestor := in_msg.Requestor;
                out_msg.Destination := getDirectoryEntry(address).Owner;
                out_msg.MessageSize := MessageSizeType:Control;
            }
        }
    }

    action(sendFwdGetM, "fM", desc="Send forward getM to owner") {
        assert(getDirectoryEntry(address).Owner.count() == 1);
        peek(request_in, RequestMsg) {
            enqueue(forward_out, RequestMsg, 1) {
                out_msg.addr := address;
                out_msg.Type := CoherenceRequestType:GetM;
                out_msg.Requestor := in_msg.Requestor;
                out_msg.Destination := getDirectoryEntry(address).Owner;
                out_msg.MessageSize := MessageSizeType:Control;
            }
        }
    }


Now we have responses from the directory.
Here we are peeking into the special buffer ``responseFromMemory``.
You can find the definition of ``MemoryMsg`` in ``src/mem/protocol/RubySlicc_MemControl.sm``.

.. code-block:: c++

    action(sendDataToReq, "d", desc="Send data from memory to requestor. May need to send sharer number, too") {
        peek(memQueue_in, MemoryMsg) {
            enqueue(response_out, ResponseMsg, 1) {
                out_msg.addr := address;
                out_msg.Type := CoherenceResponseType:Data;
                out_msg.Sender := machineID;
                out_msg.Destination.add(in_msg.OriginalRequestorMachId);
                out_msg.DataBlk := in_msg.DataBlk;
                out_msg.MessageSize := MessageSizeType:Data;
                Entry e := getDirectoryEntry(address);
                // Only need to include acks if we are the owner.
                if (e.Owner.isElement(in_msg.OriginalRequestorMachId)) {
                    out_msg.Acks := e.Sharers.count();
                } else {
                    out_msg.Acks := 0;
                }
                assert(out_msg.Acks >= 0);
            }
        }
    }

    action(sendPutAck, "a", desc="Send the put ack") {
        peek(request_in, RequestMsg) {
            enqueue(forward_out, RequestMsg, 1) {
                out_msg.addr := address;
                out_msg.Type := CoherenceRequestType:PutAck;
                out_msg.Requestor := machineID;
                out_msg.Destination.add(in_msg.Requestor);
                out_msg.MessageSize := MessageSizeType:Control;
            }
        }
    }

Then, we have the queue management and stall actions.

.. code-block:: c++

    action(popResponseQueue, "pR", desc="Pop the response queue") {
        response_in.dequeue(clockEdge());
    }

    action(popRequestQueue, "pQ", desc="Pop the request queue") {
        request_in.dequeue(clockEdge());
    }

    action(popMemQueue, "pM", desc="Pop the memory queue") {
        memQueue_in.dequeue(clockEdge());
    }

    action(stall, "z", desc="Stall the incoming request") {
        // Do nothing.
    }


Finally, we have the transistion section of the state machine file.
These mostly come from Table 8.2 in Sorin et al., but there are some extra transitions to deal with the unknown memory latency.

.. code-block:: c++

    transition({I, S}, GetS, S_m) {
        sendMemRead;
        addReqToSharers;
        popRequestQueue;
    }

    transition(I, {PutSNotLast, PutSLast, PutMNonOwner}) {
        sendPutAck;
        popRequestQueue;
    }

    transition(S_m, MemData, S) {
        sendDataToReq;
        popMemQueue;
    }

    transition(I, GetM, M_m) {
        sendMemRead;
        setOwner;
        popRequestQueue;
    }

    transition(M_m, MemData, M) {
        sendDataToReq;
        clearSharers; // NOTE: This isn't *required* in some cases.
        popMemQueue;
    }

    transition(S, GetM, M_m) {
        sendMemRead;
        removeReqFromSharers;
        sendInvToSharers;
        setOwner;
        popRequestQueue;
    }

    transition({S, S_D, SS_m, S_m}, {PutSNotLast, PutMNonOwner}) {
        removeReqFromSharers;
        sendPutAck;
        popRequestQueue;
    }

    transition(S, PutSLast, I) {
        removeReqFromSharers;
        sendPutAck;
        popRequestQueue;
    }

    transition(M, GetS, S_D) {
        sendFwdGetS;
        addReqToSharers;
        addOwnerToSharers;
        clearOwner;
        popRequestQueue;
    }

    transition(M, GetM) {
        sendFwdGetM;
        clearOwner;
        setOwner;
        popRequestQueue;
    }

    transition({M, M_m, MI_m}, {PutSNotLast, PutSLast, PutMNonOwner}) {
        sendPutAck;
        popRequestQueue;
    }

    transition(M, PutMOwner, MI_m) {
        sendDataToMem;
        clearOwner;
        sendPutAck;
        popRequestQueue;
    }

    transition(MI_m, MemAck, I) {
        popMemQueue;
    }

    transition(S_D, {GetS, GetM}) {
        stall;
    }

    transition(S_D, PutSLast) {
        removeReqFromSharers;
        sendPutAck;
        popRequestQueue;
    }

    transition(S_D, Data, SS_m) {
        sendRespDataToMem;
        popResponseQueue;
    }

    transition(SS_m, MemAck, S) {
        popMemQueue;
    }

    // If we get another request for a block that's waiting on memory,
    // stall that request.
    transition({MI_m, SS_m, S_m, M_m}, {GetS, GetM}) {
        stall;
    }


You can download the complete ``MSI-dir.sm`` file  :download:`here <../../_static/scripts/part3/MSI_protocol/MSI-dir.sm>`.
