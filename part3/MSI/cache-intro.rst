:authors: Jason Lowe-Power

.. _MSI-chapter:

.. _MSI-intro-section:

------------------------------------------
MSI example cache protocol
------------------------------------------

Before we implement a cache coherence protocol, it is important to have a solid understanding of cache coherence.
This section leans heavily on the great book *A Primer on Memory Consistency and Cache Coherence* by Daniel J. Sorin, Mark D. Hill, and David A. Wood which was published as part of the Synthesis Lectures on Computer Architecture in 2011 (DOI:`10.2200/S00346ED1V01Y201104CAC016 <https://doi.org/10.2200/S00346ED1V01Y201104CAC016>`_).
If you are unfamiliar with cache coherence, I strongly advise reading that book before continuing.

In this chapter, we will be implementing an MSI protocol.
(An MSI protocol has three stable states, modified with read-write permission, shared with read-only permission, and invalid with no permissions.)
We will implement this as a three-hop directory protocol (i.e., caches can send data directly to other caches without going through the directory).
Details for the protocol can be found in Section 8.2 of the *Primer on Memory Consistency and Cache Coherence* (pages 141-149).
It will be helpful to print out Section 8.2 to reference as you are implementing the protocol.

First steps to writing a protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's start by creating a new directory for our protocol: ``src/learning_gem5/MSI_protocol``.
In this directory, like in all gem5 source directories, we need to create a file for SCons to know what to compile.
However, this time, instead of creating a ``SConscript`` file, we are going to create a ``SConsopts`` file.
(The ``SConsopts`` files are processed before the ``SConscript`` files and we need to run the SLICC compiler before SCons executes.)

We need to create a ``SConsopts`` file with the following:

.. code-block:: python

    Import('*')

    all_protocols.extend([
    'MSI',
    ])

    protocol_dirs.append(str(Dir('.').abspath))


We do two things in this file.
First, we register the name of our protocol (``'MSI'``).
Since we have named our protocol MSI, SCons will assume that there is a file named ``MSI.slicc`` which specifies all of the state machine files and auxiliary files.
We will create that file after writing all of our state machine files.
Second, the ``SConsopts`` files tells the SCons to look in the current directory for files to pass to the SLICC compiler.

You can download the ``SConsopts`` file  :download:`here <../../_static/scripts/part3/MSI_protocol/SConsopts>`.


Writing a state machine file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The next step, and most of the effort in writing a protocol, is to create the state machine files.
State machine files generally follow the outline:

Parameters
    These are the parameters for the SimObject that will be generated from the SLICC code.

Declaring required structures and functions
    This section declares the states, events, and many other required structures for the state machine.

In port code blocks
    Contain code that looks at incoming messages from the  (``in_port``) message buffers and determines what events to trigger.

Actions
    These are simple one-effect code blocks (e.g., send a message) that are executed when going through a transition.

Transitions
    Specify actions to execute given a starting state and an event and the final state.
    This is the meat of the state machine definition.

.. todo::

    Talk about how state machine files are SimObjects and how they inherit from AbstractController
