:authors: Jason Lowe-Power

.. _MSI-transitions-section:

------------------------------------------
Transition code blocks
------------------------------------------

Finally, we've reached the final section of the state machine file!
This section contains the details for all of the transitions between states and what actions to execute during the transition.

So far in this chapter we have written the state machine top to bottom one section at a time.
However, in most cache coherence implementations you will find that you need to move around between sections.
For instance, when writing the transitions you will realize you forgot to add an action, or you notice that you actually need another transient state to implement the protocol.
This is the normal way to write protocols, but for simplicity this chapter goes through the file top to bottom.

Transition blocks consist of two parts, the begin state, event to transition on, and end state and all of the actions to execute.
For instance, a simple transition in the MSI protocol is transitioning out of Invalid on a Load.

.. code-block:: c++

    transition(I, Load, IS_D) {
        allocateCacheBlock;
        allocateTBE;
        sendGetS;
        popMandatoryQueue;
    }

First, you specify the transition as the "parameters" to the ``transition`` statement.
In this case, if the initial state is ``I`` and the event is ``Load`` then transition to ``IS_D`` (was invalid, going to shared, waiting for data).
This transition is straight out of table 8.2 in Sorin et al.

Then, inside the ``transition`` code block, all of the actions that will execute are listed in order.
For this transition first we allocate cache cache block.
Remember that in the ``allocateCacheBlock`` action the newly allocated entry is set to the entry that will be used in the rest of the actions.
After allocating the cache block, we also allocate a TBE.
This could be used if we need to wait for acks from other caches.
Next, we send a GetS request to the directory, and finally we pop the head entry off of the mandatory queue since we have fully handled it.

.. code-block:: c++

    transition(IS_D, {Load, Store, Replacement, Inv}) {
        stall;
    }

In this transition, we use slightly different syntax.
According to Table 8.2 from Sorin et al., we should stall if the cache is in IS_D on loads, stores, replacements, and invalidates.
We can specify a single transition statement for this by including multple events in curly brackets as above.
Additionally, the final state isn't required.
If the final state isn't specified, then the transition is executed and the state is not updated (i.e., the block stays in its beginning state.)
You can read the above transition as "If the cache block is in state IS_D and there is a load, store, replacement, or invalidate stall the protocol and do not transition out of the state."
You can also use curly brackets for beginning states, as shown in some of the transitions below.

Below is the rest of the transitions needed to implement the L1 cache from the MSI protocol.

.. code-block:: c++

    transition(IS_D, {DataDirNoAcks, DataOwner}, S) {
        writeDataToCache;
        deallocateTBE;
        externalLoadHit;
        popResponseQueue;
    }

    transition({IM_AD, IM_A}, {Load, Store, Replacement, FwdGetS, FwdGetM}) {
        stall;
    }

    transition({IM_AD, SM_AD}, {DataDirNoAcks, DataOwner}, M) {
        writeDataToCache;
        deallocateTBE;
        externalStoreHit;
        popResponseQueue;
    }

    transition(IM_AD, DataDirAcks, IM_A) {
        writeDataToCache;
        storeAcks;
        popResponseQueue;
    }

    transition({IM_AD, IM_A, SM_AD, SM_A}, InvAck) {
        decrAcks;
        popResponseQueue;
    }

    transition({IM_A, SM_A}, LastInvAck, M) {
        deallocateTBE;
        externalStoreHit;
        popResponseQueue;
    }

    transition({S, SM_AD, SM_A, M}, Load) {
        loadHit;
        popMandatoryQueue;
    }

    transition(S, Store, SM_AD) {
        allocateTBE;
        sendGetM;
        popMandatoryQueue;
    }

    transition(S, Replacement, SI_A) {
        sendPutS;
    }

    transition(S, Inv, I) {
        sendInvAcktoReq;
        deallocateCacheBlock;
        popForwardQueue;
    }

    transition({SM_AD, SM_A}, {Store, Replacement, FwdGetS, FwdGetM}) {
        stall;
    }

    transition(SM_AD, Inv, IM_AD) {
        sendInvAcktoReq;
        popForwardQueue;
    }

    transition(SM_AD, DataDirAcks, SM_A) {
        writeDataToCache;
        storeAcks;
        popResponseQueue;
    }

    transition(M, Store) {
        storeHit;
        popMandatoryQueue;
    }

    transition(M, Replacement, MI_A) {
        sendPutM;
    }

    transition(M, FwdGetS, S) {
        sendCacheDataToReq;
        sendCacheDataToDir;
        popForwardQueue;
    }

    transition(M, FwdGetM, I) {
        sendCacheDataToReq;
        deallocateCacheBlock;
        popForwardQueue;
    }

    transition({MI_A, SI_A, II_A}, {Load, Store, Replacement}) {
        stall;
    }

    transition(MI_A, FwdGetS, SI_A) {
        sendCacheDataToReq;
        sendCacheDataToDir;
        popForwardQueue;
    }

    transition(MI_A, FwdGetM, II_A) {
        sendCacheDataToReq;
        popForwardQueue;
    }

    transition({MI_A, SI_A, II_A}, PutAck, I) {
        deallocateCacheBlock;
        popForwardQueue;
    }

    transition(SI_A, Inv, II_A) {
        sendInvAcktoReq;
        popForwardQueue;
    }


You can download the complete ``MSI-cache.sm`` file  :download:`here <../../_static/scripts/part3/MSI_protocol/MSI-cache.sm>`.
