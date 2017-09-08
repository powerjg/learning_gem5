:authors: Jason Lowe-Power

.. _MSI-in-ports-section:

------------------------------------------
In port code blocks
------------------------------------------

This defines the message types that will flow across the
output buffers as defined above. These must be "to" networks.
"request_out" is the name we'll use later to send requests.
"RequestMsg" is the message type we will send (see MSI-msg.sm)
"requestToDir" is the name of the MessageBuffer declared above that we are sending these requests out of.

.. code-block:: c++

    out_port(request_out, RequestMsg, requestToDir);
    out_port(response_out, ResponseMsg, responseToDirOrSibling);

Input ports.
The order here is/(can be) important. The code in each In this cache, the order is responses from other caches, forwards, then requests from the CPU.
in_port is executed in the order specified in this file (or by the rank parameter).
Thus, we must sort these based on the network priority.

Like the out_port above
"response_in" is the name we'll use later when we refer to this port
"ResponseMsg" is the type of message we expect on this port
"responseFromDirOrSibling" is the name of the buffer this in_port is connected to for responses from other caches and the directory.

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


NOTE: You have to check to make sure the message buffer has a valid message at the head. The code in in_port is executed either way.

.. code-block:: c++

    in_port(response_in, ResponseMsg, responseFromDirOrSibling) {
        if (response_in.isReady(clockEdge())) {
            . . .
        }
    }

Peek is a special function. Any code inside a peek statement has a special variable declared and populated: in_msg.
This contains the message (of type RequestMsg in this case) at the head.
"forward_in" is the port we want to peek into "RequestMsg" is the type of message we expect.

Grab the entry and tbe if they exist.
The TBE better exist since this is a response and we need to be able to check the remaining acks.

.. code-block:: c++

    peek(response_in, ResponseMsg) {
        Entry cache_entry := getCacheEntry(in_msg.addr);
        TBE tbe := TBEs[in_msg.addr];
        assert(is_valid(tbe));

        . . .
    }

.. code-block:: c++

    // If it's from the directory...
    if (machineIDToMachineType(in_msg.Sender) ==
                MachineType:Directory) {
        if (in_msg.Type != CoherenceResponseType:Data) {
            error("Directory should only reply with data");
        }
        // Take the in_msg acks and add (sub) the Acks we've seen.
        // The InvAck will decrement the acks we're waiting for in
        // tbe.AcksOutstanding to below 0 if we haven't gotten the
        // dir resp yet. So, if this is 0 we don't need to wait
        assert(in_msg.Acks + tbe.AcksOutstanding >= 0);
        if (in_msg.Acks + tbe.AcksOutstanding == 0) {
            trigger(Event:DataDirNoAcks, in_msg.addr, cache_entry,
                    tbe);
        } else {
            // If it's not 0, then we need to wait for more acks
            // and we'll trigger LastInvAck later.
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
