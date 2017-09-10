:authors: Jason Lowe-Power

.. _MSI-in-ports-section:

------------------------------------------
In port code blocks
------------------------------------------

After declaring all of the structures we need in the state machine file, the first "functional" part of the file are the "in ports".
This section specifies what *events* to *trigger* on different incoming messages.

However, before we get to the in ports, we must declare our out ports.

.. code-block:: c++

    out_port(request_out, RequestMsg, requestToDir);
    out_port(response_out, ResponseMsg, responseToDirOrSibling);


This code essentially just renames ``requestToDir`` and ``responseToDirOrSibling`` to ``request_out`` and ``response_out``.
Later in the file, when we want to *enqueue* messages to these message buffers we will use the new names ``request_out`` and ``response_out``.
This also specifies the exact implementation of the messages that we will send across these ports.
We will look at the exact definition of these types below in the file ``MSI-msg.sm``.

Next, we create an *in port code block*.
In SLICC, there are many cases where there are code blocks that look similar to ``if`` blocks, but they encode specific information.
For instance, the code inside an ``in_port()`` block is put in a special generated file: ``L1Cache_Wakeup.cc``.

All of the ``in_port`` code blocks are executed in order (or based on the priority if it is specified).
On each active cycle for the controller, the first ``in_port`` code is executed.
If it is successful, it is re-executed to see if there are other messages that can be consumed on the port.
If there are no messages or no events are triggered, then the next ``in_port`` code block is executed.

There are three different kinds of *stalls* that can be generated when executing ``in_port`` code blocks.
First, there is a parameterized limit for the number of transitions per cycle at each controller.
If this limit is reached (i.e., there are more messages on the message buffers than the transition per cycle limit), then the ``in_port``s stop processing and wait to continue until the next cycle.
Second, there could be a *resource stall*.
This happens if some needed resource is unavailable.
For instance, if using the ``BankedArray`` bandwidth model, the needed bank of the cache may be currently occupied.
Third, there could be a *protocol stall*.
This is a special kind of action that causes the state machine to stall until the next cycle.

It is important to note that protocol stalls and resource stalls prevent **all** ``in_port`` blocks from executing.
For instance, if the first ``in_port`` block generates a protocol stall, none of the other ports will be executed, blocking all messages.
This is why it is important to use the correct number and ordering of virtual networks.

Below, is the full code for the ``in_port`` block for the highest priority messages to our L1 cache controller, the response from directory or other caches.
We will break the code block down to explain each section.

.. code-block:: c++

    in_port(response_in, ResponseMsg, responseFromDirOrSibling) {
        if (response_in.isReady(clockEdge())) {
            peek(response_in, ResponseMsg) {
                Entry cache_entry := getCacheEntry(in_msg.addr);
                TBE tbe := TBEs[in_msg.addr];
                assert(is_valid(tbe));

                if (machineIDToMachineType(in_msg.Sender) ==
                            MachineType:Directory) {
                    if (in_msg.Type != CoherenceResponseType:Data) {
                        error("Directory should only reply with data");
                    }
                    assert(in_msg.Acks + tbe.AcksOutstanding >= 0);
                    if (in_msg.Acks + tbe.AcksOutstanding == 0) {
                        trigger(Event:DataDirNoAcks, in_msg.addr, cache_entry,
                                tbe);
                    } else {
                        trigger(Event:DataDirAcks, in_msg.addr, cache_entry,
                                tbe);
                    }
                } else {
                    if (in_msg.Type == CoherenceResponseType:Data) {
                        trigger(Event:DataOwner, in_msg.addr, cache_entry,
                                tbe);
                    } else if (in_msg.Type == CoherenceResponseType:InvAck) {
                        DPRINTF(RubySlicc, "Got inv ack. %d left\n",
                                tbe.AcksOutstanding);
                        if (tbe.AcksOutstanding == 1) {
                            trigger(Event:LastInvAck, in_msg.addr, cache_entry,
                                    tbe);
                        } else {
                            trigger(Event:InvAck, in_msg.addr, cache_entry,
                                    tbe);
                        }
                    } else {
                        error("Unexpected response from other cache");
                    }
                }
            }
        }
    }


First, like the out_port above "response_in" is the name we'll use later when we refer to this port, and "ResponseMsg" is the type of message we expect on this port.
The first step in all ``in_port`` code blocks is to check the message buffer to see if there are any messages to be processsed.
If not, then this ``in_port`` code block is skipped and the next is executed.

.. code-block:: c++

    in_port(response_in, ResponseMsg, responseFromDirOrSibling) {
        if (response_in.isReady(clockEdge())) {
            . . .
        }
    }

Assuming there is a valid message in the message buffer, next, we grab that message by using the special code block ``peek``.
Peek is a special function.
Any code inside a peek statement has a special variable declared and populated: ``in_msg``.
This contains the message (of type ResponseMsg in this case as specified by the second parameter of ``peek``) at the head.
``response_in`` is the port we want to peeking into.

Then, we need to grab the cache entry and the TBE for the incoming address.
(We will look at the other parameters in response message below.)
Above, we implemented getCacheEntry.
It will return either the valid matching entry for the address, or an invalid entry if there is not a matching cache block.

For the TBE, since this is a response to a request this cache controller initiated, there *must* be a valid TBE in the TBE table.
Hence, we see our first debug statement, an *assert*.
This is one of the ways to ease debugging of cache coherence protocols.
It is encouraged to use asserts liberally to make debugging easiers.

Grab the entry and tbe if they exist.
The TBE better exist since this is a response and we need to be able to check the remaining acks.

.. code-block:: c++

    peek(response_in, ResponseMsg) {
        Entry cache_entry := getCacheEntry(in_msg.addr);
        TBE tbe := TBEs[in_msg.addr];
        assert(is_valid(tbe));

        . . .
    }

Next, we need to decide what event to trigger based on the message.
For this, we first need to discuss what data response messages are carrying.

To declare a new message type, first create a new file for all of the message types: ``MSI-msg.sm``.
In this file, you can declare any structures that will be *globally* used across all of the SLICC files for your protocol.
We will include this file in all of the state machine definitions via the ``MSI.slicc`` file later.
This is similar to including global definitions in header files in C/C++.

In the ``MSI-msg.sm`` file, add the following code block:

.. code-block:: c++

    structure(ResponseMsg, desc="Used for Dir->Cache and Fwd message responses",
              interface="Message") {
        Addr addr,                   desc="Physical address for this response";
        CoherenceResponseType Type,  desc="Type of response";
        MachineID Sender,            desc="Node who is responding to the request";
        NetDest Destination,         desc="Multicast destination mask";
        DataBlock DataBlk,           desc="data for the cache line";
        MessageSizeType MessageSize, desc="size category of the message";
        int Acks,                    desc="Number of acks required from others";

        // This must be overridden here to support functional accesses
        bool functionalRead(Packet *pkt) {
            if (Type == CoherenceResponseType:Data) {
                return testAndRead(addr, DataBlk, pkt);
            }
            return false;
        }

        bool functionalWrite(Packet *pkt) {
            // No check on message type required since the protocol should read
            // data block from only those messages that contain valid data
            return testAndWrite(addr, DataBlk, pkt);
        }
    }


The message is just another SLICC structure similar to the structures we've defined before.
However, this time, we have a specific interface that it is implementing: ``Message``.
Within this message, we can add any members that we need for our protocol.
In this case, we first have the address.
Note, a common "gotcha" is that you *cannot* use "Addr" with a capitol "A" for the name of the member since it is the same name as the type!

Next, we have the type of response.
In our case, there are two types of response data and invalidation acks from other caches after they have invalidated their copy.
Thus, we need to define an *enumeration*, the ``CoherenceResponseType``, to use it in this message.
Add the following code *before* the ``ResponseMsg`` declaration in the same file.

.. code-block:: c++

    enumeration(CoherenceResponseType, desc="Types of response messages") {
        Data,       desc="Contains the most up-to-date data";
        InvAck,     desc="Message from another cache that they have inv. the blk";
    }

Next, in the response message type, we have the ``MachineID`` which sent the response.
``MachineID`` is the *specific machine* that sent the response.
For instance, it might be directory 0 or cache 12.
The ``MachineID`` contains both the ``MachineType`` (e.g., we have been creating an ``L1Cache`` as declared in the first ``machine()``) and the specific *version* of that machine type.
We will come back to machine version numbers when configuring the system.

.. index:: NetDest

Next, all messages need a *destination*, and a *size*.
The destination is specified as a ``NetDest``, which is a bitmap of all ``MachineID``s in the system.
This allows messages to be broadcast to a flexible set of receivers.
The message also has a size.
You can find the possible message sizes in ``src/mem/protocol/RubySlicc_Exports.sm``.

This message may also contain a data block and the number acks that are expected.
Thus, we can include these in the message definition as well.

Finally, we also have to define functional read and write functions.
These are used by Ruby to inspect in-flight messages on function reads and writes.
Note: This functionality currently is very brittle and if there are messages in-flight for an address that is functionally read or written the functional access may fail.

You can download the complete file ``MSI-msg.sm`` :download:`here <../../_static/scripts/part3/MSI_protocol/MSI-msg.sm>`.

Now that we have defined the data in the response message, we can look at how we choose the action to trigger in the ``in_port`` for response to the cache.

.. code-block:: c++

    // If it's from the directory...
    if (machineIDToMachineType(in_msg.Sender) ==
                MachineType:Directory) {
        if (in_msg.Type != CoherenceResponseType:Data) {
            error("Directory should only reply with data");
        }
        assert(in_msg.Acks + tbe.AcksOutstanding >= 0);
        if (in_msg.Acks + tbe.AcksOutstanding == 0) {
            trigger(Event:DataDirNoAcks, in_msg.addr, cache_entry,
                    tbe);
        } else {
            trigger(Event:DataDirAcks, in_msg.addr, cache_entry,
                    tbe);
        }
    } else {
        // This is from another cache.
        if (in_msg.Type == CoherenceResponseType:Data) {
            trigger(Event:DataOwner, in_msg.addr, cache_entry,
                    tbe);
        } else if (in_msg.Type == CoherenceResponseType:InvAck) {
            DPRINTF(RubySlicc, "Got inv ack. %d left\n",
                    tbe.AcksOutstanding);
            if (tbe.AcksOutstanding == 1) {
                // If there is exactly one ack remaining then we
                // know it is the last ack.
                trigger(Event:LastInvAck, in_msg.addr, cache_entry,
                        tbe);
            } else {
                trigger(Event:InvAck, in_msg.addr, cache_entry,
                        tbe);
            }
        } else {
            error("Unexpected response from other cache");
        }
    }


First, we check to see if the message comes from the directory or another cache.
If it comes from the directory, we know that it *must* be a data response (the directory will never respond with an ack).

Here, we meet our second way to add debug information to protocols: the ``error`` function.
This function breaks simulation and prints out the string parameter similar to ``panic``.

Next, when we receive data from the directory, we expect that the number of acks we are waiting for will never be less than 0.
The number of acks we're waiting for is the current acks we have received (tbe.AcksOutstanding) and the number of acks the directory has told us to be waiting for.
We need to check it this way because it is possible that we have received acks from other caches before we get the message from the directory that we need to wait for acks.

There are two possibilities for the acks, either we have already received all of the acks and now we are getting the data (data from dir acks==0 in Table 8.3), or we need to wait for more acks.
Thus, we check this condition and trigger two different events, one for each possibility.

When triggering transitions, you need to pass four parameters.
The first parameter is the event to trigger.
These events were specified earlier in the ``Event`` declaration.
The next parameter is the (physical memory) address of the cache block to operate on.
Usually this is the same as the address of the ``in_msg``, but it may be different, for instance, on a replacement the address is for the block being replaced.
Next is the cache entry and the TBE for the block.
These may be invalid if there are no valid entries for the address in the cache or there is not a valid TBE in the TBE table.

When we implement actions below, we will see how these last three parameters are used.
They are passed into the actions as implicit variables: ``address``, ``cache_entry``, and ``tbe``.

If the ``trigger`` function is executed, after the transition is complete, the ``in_port`` logic is executed again, assuming there have been fewer transitions than that maximum transitions per cycle.
If there are other messages in the message buffer more transitions can be triggered.

If the response is from another cache instead of the directory, then other events are triggered, as shown in the code above.
These events come directly from Table 8.3 in Sorin et al.

Importantly, you should use the ``in_port`` logic to check all conditions.
After an event is triggered, it should only have a *single code path*.
I.e., there should be no ``if`` statements in any action blocks.
If you want to conditionally execute actions, you should use different states or different events in the ``in_port`` logic.

The reason for this constraint is the way Ruby checks resources before executing a transition.
In the generated code from the ``in_port`` blocks before the transition is actually executed all of the resources are checked.
In other words, transitions are atomic and either execute all of the actions or none.
Conditional statements inside the actions prevents the SLICC compiler from correctly tracking the resource usage and can lead to strange performance, deadlocks, and other bugs.

After specifying the ``in_port`` logic for the highest priority network, the response network, we need to add the ``in_port`` logic for the forward request network.
However, before specifying this logic, we need to define the ``RequestMsg`` type and the ``CoherenceRequestType`` which contains the types of requests.
These two definitions go in the ``MSI-msg.sm`` file *not in MSI-cache.sm* since they are global definitions.

It is possible to implement this as two different messages and request type enumerations, one for forward and one for normal requests, but it simplifies the code to use a single message and type.

.. code-block:: c++

    enumeration(CoherenceRequestType, desc="Types of request messages") {
        GetS,       desc="Request from cache for a block with read permission";
        GetM,       desc="Request from cache for a block with write permission";
        PutS,       desc="Sent to directory when evicting a block in S (clean WB)";
        PutM,       desc="Sent to directory when evicting a block in M";

        // "Requests" from the directory to the caches on the fwd network
        Inv,        desc="Probe the cache and invalidate any matching blocks";
        PutAck,     desc="The put request has been processed.";
    }

.. code-block:: c++

    structure(RequestMsg, desc="Used for Cache->Dir and Fwd messages",  interface="Message") {
        Addr addr,                   desc="Physical address for this request";
        CoherenceRequestType Type,   desc="Type of request";
        MachineID Requestor,         desc="Node who initiated the request";
        NetDest Destination,         desc="Multicast destination mask";
        DataBlock DataBlk,           desc="data for the cache line";
        MessageSizeType MessageSize, desc="size category of the message";

        bool functionalRead(Packet *pkt) {
            // Requests should never have the only copy of the most up-to-date data
            return false;
        }

        bool functionalWrite(Packet *pkt) {
            // No check on message type required since the protocol should read
            // data block from only those messages that contain valid data
            return testAndWrite(addr, DataBlk, pkt);
        }
    }


You can download the complete file ``MSI-msg.sm`` :download:`here <../../_static/scripts/part3/MSI_protocol/MSI-msg.sm>`.

Now, we can specify the logic for the forward network ``in_port``.
This logic is straightforward and triggers a different event for each request type.

.. code-block:: c++

    in_port(forward_in, RequestMsg, forwardFromDir) {
        if (forward_in.isReady(clockEdge())) {
            peek(forward_in, RequestMsg) {
                // Grab the entry and tbe if they exist.
                Entry cache_entry := getCacheEntry(in_msg.addr);
                TBE tbe := TBEs[in_msg.addr];

                if (in_msg.Type == CoherenceRequestType:GetS) {
                    trigger(Event:FwdGetS, in_msg.addr, cache_entry, tbe);
                } else if (in_msg.Type == CoherenceRequestType:GetM) {
                    trigger(Event:FwdGetM, in_msg.addr, cache_entry, tbe);
                } else if (in_msg.Type == CoherenceRequestType:Inv) {
                    trigger(Event:Inv, in_msg.addr, cache_entry, tbe);
                } else if (in_msg.Type == CoherenceRequestType:PutAck) {
                    trigger(Event:PutAck, in_msg.addr, cache_entry, tbe);
                } else {
                    error("Unexpected forward message!");
                }
            }
        }
    }


The final ``in_port`` is for the mandatory queue.
This is the lowest priority queue, so it must be lowest in the state machine file.
The mandatory queue has a special message type: ``RubyRequest``.
This type is specified in ``src/mem/protocol/RubySlicc_Types.sm``
It contains two different addresses, the ``LineAddress`` which is cache-block aligned and the ``PhysicalAddress`` which holds the original request's address and may not be cache-block aligned.
It also has other members that may be useful in some protcols.
However, for this simple protocol we only need the ``LineAddress``.

.. code-block:: c++

    in_port(mandatory_in, RubyRequest, mandatoryQueue) {
        if (mandatory_in.isReady(clockEdge())) {
            peek(mandatory_in, RubyRequest, block_on="LineAddress") {
                Entry cache_entry := getCacheEntry(in_msg.LineAddress);
                TBE tbe := TBEs[in_msg.LineAddress];

                if (is_invalid(cache_entry) &&
                        cacheMemory.cacheAvail(in_msg.LineAddress) == false ) {
                    Addr addr := cacheMemory.cacheProbe(in_msg.LineAddress);
                    Entry victim_entry := getCacheEntry(addr);
                    TBE victim_tbe := TBEs[addr];
                    trigger(Event:Replacement, addr, victim_entry, victim_tbe);
                } else {
                    if (in_msg.Type == RubyRequestType:LD ||
                            in_msg.Type == RubyRequestType:IFETCH) {
                        trigger(Event:Load, in_msg.LineAddress, cache_entry,
                                tbe);
                    } else if (in_msg.Type == RubyRequestType:ST) {
                        trigger(Event:Store, in_msg.LineAddress, cache_entry,
                                tbe);
                    } else {
                        error("Unexected type from processor");
                    }
                }
            }
        }
    }

There are a couple of new concepts shown in this code block.
First, we use ``block_on="LineAddress"`` in the peek function.
What this does is ensure that any other requests to the same cache line will be blocked until the current request is complete.

Next, we check if the cache entry for this line is valid.
If not, and there are no more entries available in the set, then we need to evict another entry.
To get the victim address, we can use the ``cacheProbe`` function on the ``CacheMemory`` object.
This function uses the parameterized replacement policy and returns the physical (line) address of the victim.

Importantly, when we trigger the ``Replacement`` event *we use the address of the victim block* and the victim cache entry and tbe.
Thus, when we take actions in the replacement transitions we will be acting on the victim block, not the requesting block.
Additionally, we need to remember to *not* remove the requesting message from the mandatory queue (pop) until it has been satisfied.
The message should not be popped after the replacement is complete.

If the cache block was found to be valid, then we simply trigger the ``Load`` or ``Store`` event.
