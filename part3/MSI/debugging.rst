:authors: Jason Lowe-Power

.. _MSI-debugging-section:

Debugging SLICC Protocols
---------------------------

In this section, I present the steps that I took while debugging the MSI protocol implemented earlier in this chapter.
Learning to debug coherence protocols is a challenge.
The best way is by working with others who have written SLICC protocols in the past.
However, since you, the reader, cannot look over my shoulder while I am debugging a protocol, I am trying to present the next-best thing.

Here, I first present some high-level suggestions to tackling protocol errors.
Next, I discuss some details about deadlocks, and how to understand protocol traces that can be used to fix them.
Then, I present my experience debugging the MSI protocol in this chapter in a stream-of-consciousness style.
I will show the error that was generated, then the solution to the error, sometimes with some commentary of the different tactics I tried to solve the error.

General debugging tips
=======================

Ruby has many useful debug flags.
However, the most useful, by far, is ``ProtocolTrace``.
Below, you will see several examples of using the protocol trace to debug a protocol.
The protocol trace prints every transition for all controllers.
Thus, you can simply trace the entire execution of the cache system.

Other useful debug flags include:

RubyGenerated
    Prints a bunch of stuff from the ruby generated code.

RubyPort/RubySequencer
    See the details of sending/receiving messages into/out of ruby.

RubyNetwork
    Prints entire network messages including the sender/receiver and the data within the message for all messages.
    This flag is useful when there is a data mismatch.

The first step to debugging a Ruby protocol is to run it with the Ruby random tester.
The random tester issues semi-random requests into the Ruby system and checks to make sure the returned data is correct.
To make debugging faster, the random tester issues read requests from one controller for a block and a write request for the same cache block (but a different byte) from a different controller.
Thus, the Ruby random tester does a good job exercising the transient states and race conditions in the protocol.

.. todo::

    Add more details about the random tester.


Unfortunately, the random tester's configuration is slightly different than when using normal CPUs.
Thus, we need to use a different ``MyCacheSystem`` than before.
You can download this different cache system file :download:`here <../../_static/scripts/part3/configs/test_caches.py>` and you can download the modified run script :download:`here <../../_static/scripts/part3/configs/ruby_test.py>`.
The test run script is mostly the same as the simple run script, but creates the ``RubyRandomTester`` instead of CPUs.

It is often a good idea to first run the random tester with a single "CPU".
Then, increase the number of loads from the default of 100 to something that takes a few minutes to execute on your host system.
Next, if there are no errors, then increase the number of "CPUs" to two and reduce the number of loads to 100 again.
Then, start increasing the number of loads.
Finally, you can increase the number of CPUs to something reasonable for the system you are trying to simulate.
If you can run the random tester for 10-15 minutes, you can be slightly confident that the random tester isn't going to find any other bugs.

Once you have your protocol working with the random tester, you can move on to using real applications.
It is likely that real applications will expose even more bugs in the protocol.
If at all possible, it is much easier to debug your protocol with the random tester than with real applications!

Understanding Protocol Traces
=============================

Unfortunately, despite extensive effort to catch bugs in them, coherence protocols (even heavily tested ones) will have sometimes have bugs.
Sometimes these bugs are relatively simple fixes, while other times the bugs will be very insidious and difficult to track down.
In the worst case, the bugs will manifest themselves as deadlocks: bugs that literally prevent the application from making progress.
Another, similar problem is livelocks: where the program runs forever because there is a cycle somewhere in the system.
Whenever livelocks or deadlocks occur, the next thing to do is generate a protocol trace.
Traces print a running list of every transition that is happening in the memory system -- memory requests starting and completing, L1 and directory transitions, etc.
You can then use these traces to identify why the deadlock is occurring.
However, as we will discuss in more detail below, debugging deadlocks in protocol traces is often extremely challenging.

Here, we discuss what appears in the protocol trace to help explain what is happening.
To start with, lets look at a small snippet of a protocol trace (we will discuss the details of this trace further below):

::

    ...
    4541   0    L1Cache         Replacement   MI_A>MI_A   [0x4ac0, line 0x4ac0]
    4542   0    L1Cache              PutAck   MI_A>I      [0x4ac0, line 0x4ac0]
    4549   0  Directory              MemAck   MI_M>I      [0x4ac0, line 0x4ac0]
    4641   0        Seq               Begin       >       [0x4aec, line 0x4ac0] LD
    4652   0    L1Cache                Load      I>IS_D   [0x4ac0, line 0x4ac0]
    4657   0  Directory                GetS      I>S_M    [0x4ac0, line 0x4ac0]
    4669   0  Directory             MemData    S_M>S      [0x4ac0, line 0x4ac0]
    4674   0        Seq                Done       >       [0x4aec, line 0x4ac0] 33 cycles
    4674   0    L1Cache       DataDirNoAcks   IS_D>S      [0x4ac0, line 0x4ac0]
    5321   0        Seq               Begin       >       [0x4aec, line 0x4ac0] ST
    5322   0    L1Cache               Store      S>SM_AD  [0x4ac0, line 0x4ac0]
    5327   0  Directory                GetM      S>M_M    [0x4ac0, line 0x4ac0]

Every line in this trace has a set pattern in terms of what information appears on that line.  Specifically, the fields are:

#. Current Tick: the tick the print is occurs in
#. Machine Version: The number of the machine where this request is coming from.  For example, if there are  4 L1 caches, then the numbers would be 0-3.  Assuming you have 1 L1 Cache per core, you can think of this as representing the core the request is coming from.
#. Component: which part of the system is doing the print.  Generally, ``Seq`` is shorthand for Sequencer, ``L1Cache`` represents the L1 Cache, "Directory" represents the directory, and so on.  For L1 caches and the directory, this represents the name of the machine type (i.e., what is after "MachineType:" in the ``machine()`` definition).
#. Action: what the component is doing.  For example, "Begin" means the Sequencer has received a new request, "Done" means that the Sequencer is completing a previous request, and "DataDirNoAcks" means that our DataDirNoAcks event is being triggered.
#. Transition (e.g., MI_A>MI_A): what state transition this action is doing (format: "currentState>nextState").  If no transition is happening, this is denoted with ">".
#. Address (e.g., [0x4ac0, line 0x4ac0]): the physical address of the request (format: [wordAddress, lineAddress]).  This address will always be cache-block aligned except for requests from the ``Sequencer`` and ``mandatoryQueue``.
#. (Optional) Comments: optionally, there is one additional field to pass comments.  For example, the "LD" , "ST", and "33 cycles" lines use this extra field to pass additional information to the trace -- such as identifying the request as a load or store.  For SLICC transitions, ``APPEND_TRANSITION_COMMENT`` often use this, as we discussed :ref:`previously <MSI-actions-section>`.

Generally, spaces are used to separate each of these fields.  However, sometimes if a field is very long, there may be no spaces or the line may be shifted compared to other lines.

Thus, the above snippet is showing what was happening in the memory system between ticks 4541 and 5327.
In this snippet, all of the requests are coming from L1Cache-0 (core 0) and going to Directory-0 (the first bank of the directory).
During this time, we see several memory requests and state transitions for the cache line 0x4ac0, both at the L1 caches and the directory.
For example, in tick 5322, the core executes a store to 0x4ac0.
However, it currently does not have that line in Modified in its cache (it is in Shared after the core loaded it from ticks 4641-4674), so it needs to request ownership for that line from the directory (which receives this request in tick 5327).
While waiting for ownership, it transitions from S (Shared) to SM_AD (a transient state -- was in S, going to M, waiting for Ack and Data).

To add a print to the protocol trace, you will need to add a print with these fields with the ProtocolTrace flag.
For example, if you look at ``src/mem/ruby/system/Sequencer.cc``, you can see where the ``Seq               Begin`` and ``Seq                Done`` trace prints come from (search for ProtocolTrace).

Errors I ran into debugging MSI
================================


::

    gem5.opt: build/MSI/mem/ruby/system/Sequencer.cc:423: void Sequencer::readCallback(Addr, DataBlock&, bool, MachineType, Cycles, Cycles, Cycles): Assertion `m_readRequestTable.count(makeLineAddress(address))' failed.


I'm an idiot, it was that I called readCallback in externalStoreHit instead of writeCallback.
It's good to start simple!

::

    gem5.opt: build/MSI/mem/ruby/network/MessageBuffer.cc:220: Tick MessageBuffer::dequeue(Tick, bool): Assertion `isReady(current_time)' failed.


I ran gem5 in GDB to get more information.
Look at L1Cache_Controller::doTransitionWorker.
The current transition is:
event=L1Cache_Event_PutAck, state=L1Cache_State_MI_A, next_state=@0x7fffffffd0a0: L1Cache_State_FIRST
This is more simply MI_A->I on a PutAck
See it's in popResponseQueue.

The problem is that the PutAck is on the forward network, not the response network.


::

    panic: Invalid transition
    system.caches.controllers0 time: 3594 addr: 3264 event: DataDirAcks state: IS_D


Hmm. I think this shouldn't have happened. The needed acks should always be 0 or you get data from the owner.
Ah. So I implemented sendDataToReq at the directory to always send the number of sharers.
If we get this response in IS_D we don't care whether or not there are sharers.
Thus, to make things more simple, I'm just going to transition to S on DataDirAcks.
This is a slight difference from the original implementation in Sorin et al.

Well, actually, I think it's that we send the request after we add ourselves to the sharer list.
The above is *incorrect*. Sorin et al. were not wrong!
Let's try not doing that!

So, I fixed this by checking to see if the requestor is the *owner* before sending the data to the requestor at the directory.
Only if the requestor is the owner do we include the number of sharers.
Otherwise, it doesn't matter at all and we just set the sharers to 0.

::
    panic: Invalid transition
    system.caches.controllers0 time: 5332 addr: 0x4ac0 event: Inv state: SM_AD


First, let's look at where Inv is triggered.
If you get an invalidate... only then.
Maybe it's that we are on the sharer list and shouldn't be?

We can use protocol trace and grep to find what's going on.

.. code-block:: sh

    build/MSI/gem5.opt --debug-flags=ProtocolTrace configs/learning_gem5/part6/ruby_test.py | grep 0x4ac0

::

    ...
    4541   0    L1Cache         Replacement   MI_A>MI_A   [0x4ac0, line 0x4ac0]
    4542   0    L1Cache              PutAck   MI_A>I      [0x4ac0, line 0x4ac0]
    4549   0  Directory              MemAck   MI_M>I      [0x4ac0, line 0x4ac0]
    4641   0        Seq               Begin       >       [0x4aec, line 0x4ac0] LD
    4652   0    L1Cache                Load      I>IS_D   [0x4ac0, line 0x4ac0]
    4657   0  Directory                GetS      I>S_M    [0x4ac0, line 0x4ac0]
    4669   0  Directory             MemData    S_M>S      [0x4ac0, line 0x4ac0]
    4674   0        Seq                Done       >       [0x4aec, line 0x4ac0] 33 cycles
    4674   0    L1Cache       DataDirNoAcks   IS_D>S      [0x4ac0, line 0x4ac0]
    5321   0        Seq               Begin       >       [0x4aec, line 0x4ac0] ST
    5322   0    L1Cache               Store      S>SM_AD  [0x4ac0, line 0x4ac0]
    5327   0  Directory                GetM      S>M_M    [0x4ac0, line 0x4ac0]


Maybe there is a sharer in the sharers list when there shouldn't be?
We can add a defensive assert in clearOwner and setOwner.

.. code-block:: c++

    action(setOwner, "sO", desc="Set the owner") {
        assert(getDirectoryEntry(address).Sharers.count() == 0);
        peek(request_in, RequestMsg) {
            getDirectoryEntry(address).Owner.add(in_msg.Requestor);
        }
    }

    action(clearOwner, "cO", desc="Clear the owner") {
        assert(getDirectoryEntry(address).Sharers.count() == 0);
        getDirectoryEntry(address).Owner.clear();
    }

Now, I get the following error:

::

    panic: Runtime Error at MSI-dir.sm:301: assert failure.


This is in setOwner. Well, actually this is OK since we need to have the sharers still set until we count them to send the ack count to the requestor.
Let's remove that assert and see what happens.
Nothing. That didn't help anything.

When are invalidations sent from the directory?
Only on S->M_M.
So, here, we need to remove ourselves from the invalidation list.
I think we need to keep ourselves in the sharer list since we subtract one when sending the number of acks.

Note: I'm coming back to this a little later.
It turns out that both of these asserts are wrong.
I found this out when running with more than one CPU below.
The sharers are set before clearing the Owner in M->S_D on a GetS.

So, onto the next problem!

::

    panic: Deadlock detected: current_time: 56091 last_progress_time: 6090 difference:  50001 processor: 0

Deadlocks are the worst kind of error.
Whatever caused the deadlock is ancient history (i.e., likely happened many cycles earlier), and often very hard to track down.

Looking at the tail of the protocol trace (note: sometimes you must put the protocol trace into a file because it grows *very* big) I see that there is an address that is trying to be replaced.
Let's start there.

::

          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]
          56091   0    L1Cache         Replacement   SM_A>SM_A   [0x5ac0, line 0x5ac0]

Before this replacement got stuck I see the following in the protocol trace.
Note: this is 50000 cycles in the past!

::

    ...
    5592   0    L1Cache               Store      S>SM_AD  [0x5ac0, line 0x5ac0]
    5597   0  Directory                GetM      S>M_M    [0x5ac0, line 0x5ac0]
    ...
    5641   0  Directory             MemData    M_M>M      [0x5ac0, line 0x5ac0]
    ...
    5646   0    L1Cache         DataDirAcks  SM_AD>SM_A   [0x5ac0, line 0x5ac0]

Ah! This clearly should not be DataDirAcks since we only have a single CPU!
So, we seem to not be subtracting properly.
Going back to the previous error, I was wrong about needing to keep ourselves in the list.
I forgot that we no longer had the -1 thing.
So, let's remove ourselves from the sharing list before sending the invalidations when we originally get the S->M request.

So! With those changes the Ruby tester completes with a single core.
Now, to make it harder we need to increase the number of loads we do and then the number of cores.

And, of course, when I increase it to 10,000 loads there is a deadlock. Fun!

What I'm seeing at the end of the protocol trace is the following.

::

    144684   0    L1Cache         Replacement   MI_A>MI_A   [0x5bc0, line 0x5bc0]
    ...
    144685   0  Directory                GetM   MI_M>MI_M   [0x54c0, line 0x54c0]
    ...
    144685   0    L1Cache         Replacement   MI_A>MI_A   [0x5bc0, line 0x5bc0]
    ...
    144686   0  Directory                GetM   MI_M>MI_M   [0x54c0, line 0x54c0]
    ...
    144686   0    L1Cache         Replacement   MI_A>MI_A   [0x5bc0, line 0x5bc0]
    ...
    144687   0  Directory                GetM   MI_M>MI_M   [0x54c0, line 0x54c0]
    ...

This is repeated for a long time.

It seems that there is a circular dependence or something like that causing this deadlock.

Well, it seems that I was correct.
The order of the in_ports really matters!
In the directory, I previously had the order: request, response, memory.
However, there was a memory packet that was blocked because the request queue was blocked, which caused the circular dependence and the deadlock.
The order *should* be memory, response, and request.
I believe the memory/response order doesn't matter since no responses depend on memory and vice versa.

Now, let's try with two CPUs.
First thing I run into is an assert failure.
I'm seeing the first assert in `setState` fail.

.. code-block:: c++

        void setState(Addr addr, State state) {
            if (directory.isPresent(addr)) {
                if (state == State:M) {
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

To track this problem down, let's add a debug statement (DPRINTF) and run with protocol trace.
First I added the following line just before the assert.
Note that you are required to use the RubySlicc debug flag.
This is the only debug flag included in the generated SLICC files.

.. code-block:: c++

    DPRINTF(RubySlicc, "Owner %s\n", getDirectoryEntry(addr).Owner);

Then, I see the following output when running with ProtocolTrace and RubySlicc.

::

    118   0  Directory             MemData    M_M>M      [0x400, line 0x400]
    118: system.caches.controllers2: MSI-dir.sm:160: Owner [NetDest (16) 1 0  -  -  - 0  -  -  -  -  -  -  -  -  -  -  -  -  - ]
    118   0  Directory                GetM      M>M      [0x400, line 0x400]
    118: system.caches.controllers2: MSI-dir.sm:160: Owner [NetDest (16) 1 1  -  -  - 0  -  -  -  -  -  -  -  -  -  -  -  -  - ]

It looks like when we process the GetM when in state M we need to first clear the owner before adding the new owner.
The other options is in `setOwner` we could have Set the Owner specifically instead of adding it to the NetDest.

Oooo! This is a new error!

::

    panic: Runtime Error at MSI-dir.sm:229: Unexpected message type..


What is this message that fails?
Let's use the RubyNetwork debug flag to try to track down what message is causing this error.
A few lines above the error I see the following message whose destination is the directory.

The destination is a NetDest which is a bitvector of MachineIDs.
These are split into multiple sections.
I know I'm running with two CPUs, so the first two 0's are for the CPUs, and the other 1 must be fore the directory.

::

    2285: PerfectSwitch-2: Message: [ResponseMsg: addr = [0x8c0, line 0x8c0] Type = InvAck Sender = L1Cache-1 Destination = [NetDest (16) 0 0  -  -  - 1  -  -  -  -  -  -  -  -  -  -  -  -  - ] DataBlk = [ 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0xb1 0xb2 0xb3 0xb4 0xca 0xcb 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 ] MessageSize = Control Acks = 0 ]

This message has the type InvAck, which is clearly wrong!
It seems that we are setting the requestor wrong when we send the invalidate (Inv) message to the L1 caches from the directory.

Yes. This is the problem.
We need to make the requestor the original requestor.
This was already correct for the FwdGetS/M, but I missed the invalidate somehow.
On to the next error!

::

    panic: Invalid transition
    system.caches.controllers0 time: 2287 addr: 0x8c0 event: LastInvAck state: SM_AD

This seems to be that I am not counting the acks correctly.
It could also be that the directory is much slower than the other caches at responding since it has to get the data from memory.

If it's the latter (which I should be sure to verify), what we could do is include an ack requirement for the directory, too.
Then, when the directory sends the data (and the owner, too) decrement the needed acks and trigger the event based on the new ack count.

Actually, that first hypothesis was not quite right.
I printed out the number of acks whenever we receive an InvAck and what's happening is that the other cache is responding with an InvAck before the directory has told it how many acks to expect.

So, what we need to do is something like what I was talking about above.
First of all, we will need to let the acks drop below 0 and add the total acks to it from the directory message.
Then, we are going to have to complicate the logic for triggering last ack, etc.

Ok. So now we're letting the tbe.Acks drop below 0 and then adding the directory acks whenever they show up.

Next error: This is a tough one.
The error is now that the data doesn't match as it should.
Kind of like the deadlock, the data could have been corrupted in the ancient past.
I believe the address is the last one in the protocol trace.

::
    panic: Action/check failure: proc: 0 address: 19688 data: 0x779e6d0 byte_number: 0 m_value+byte_number: 53 byte: 0 [19688, value: 53, status: Check_Pending, initiating node: 0, store_count: 4]Time: 5843

So, it could be something to do with ack counts, though I don't think this is the issue.
Either way, it's a good idea to annotate the protocol trace with the ack information.
To do this, we can add comments to the transition with `APPEND_TRANSITION_COMMENT`.

.. code-block:: c++

    action(decrAcks, "da", desc="Decrement the number of acks") {
        assert(is_valid(tbe));
        tbe.Acks := tbe.Acks - 1;
        APPEND_TRANSITION_COMMENT("Acks: ");
        APPEND_TRANSITION_COMMENT(tbe.Acks);
    }

::

    5737   1    L1Cache              InvAck  SM_AD>SM_AD  [0x400, line 0x400] Acks: -1

For these data issues, the debug flag RubyNetwork is useful because it prints the value of the data blocks at every point it is in the network.
For instance, for the address in question above, it looks like the data block is all 0's after loading from main-memory.
I believe this should have valid data.
In fact, if we go back in time some we see that there was some non-zero elements.

::

              5382   1    L1Cache                 Inv      S>I      [0x4cc0, line 0x4cc0]
   5383: PerfectSwitch-1: Message: [ResponseMsg: addr = [0x4cc0, line 0x4cc0] Type = InvAck Sender = L1Cache-1 Destination = [NetDest (16) 1 0  -  -  - 0  -  -  -  -  -  -  -  -  -  -  -  -  - ] DataBlk = [ 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x35 0x36 0x37 0x61 0x6d 0x6e 0x6f 0x70 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 ] MessageSize = Control Acks = 0 ]
   ...
   ...
   ...
              5389   0  Directory             MemData    M_M>M      [0x4cc0, line 0x4cc0]
   5390: PerfectSwitch-2: incoming: 0
   5390: PerfectSwitch-2: Message: [ResponseMsg: addr = [0x4cc0, line 0x4cc0] Type = Data Sender = Directory-0 Destination = [NetDest (16) 1 0  -  -  - 0  -  -  -  -  -  -  -  -  -  -  -  -  - ] DataBlk = [ 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 ] MessageSize = Data Acks = 1 ]


It seems that memory is not being updated correctly on the M->S transition.
After lots of digging and using the MemoryAccess debug flag to see exactly what was being read and written to main memory, I found that in sendDataToMem I was using the request_in.
This is right for PutM, but not right for Data.
We need to have another action to send data from response queue!

::

    panic: Invalid transition
    system.caches.controllers0 time: 44381 addr: 0x7c0 event: Inv state: SM_AD

Invalid transition is my personal favorite kind of SLICC error.
For this error, you know exactly what address caused it, and it's very easy to trace through the protocol trace to find what went wrong.
However, in this case, nothing went wrong, I just forgot to put this transition in!
Easy fix!
