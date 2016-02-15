:authors: Jason Lowe-Power


------------------------------
Some thoughts on this document
------------------------------

* We want this document to be living.
   * We should have the source checked in somewhere (probably in a repo next to gem5).
   * We should force people to make updates when they break things.
   * We should have the source for the examples checked into the gem5 repo, and have tests that run them.

An outline:

#. Part I: Getting started
    Done-ish
#. Developing with gem5
    #. Creating a new SimObject
    #. Debugging support in gem5
    #. Creating a new MemObject with master/slave ports
    #. Contributing back to gem5
        #. Style guidelines
        #. Mercurial queues
        #. Reviewboard
    #. Running tests
#. Full system simulation
    #. Introduction
    #. Simple FS config file
    #. Building a kernel for gem5
    #. Building a disk image for gem5
    #. ARM simulation
    #. More on X86 simulation
#. Advanced gem5 usage
    #. Checkpoint creation and restoring
    #. ISA language
    #. Using m5ops
    #. Using traces
#. An overview of common SimObjects
    #. CPUs
        #. CPU models
        #. Dynamically switching CPUs
    #. Classic memory system
        #. Random note: All controllers that issue coherent requests are required to have a cache attached to them. For instance, you have to have a cache on the IOBus or else there are weird errors.
    #. System
#. Using Ruby cache coherence model
    #. Overview of Ruby
    #. Ruby's cache coherence protocols
    #. Ruby's network topologies
    #. Writing a new protocol
    #. Debugging a protocol
    #. Extending the SLICC language
#. External projects and gem5
    #. Power models
    #. GPU models
    #. External simulation infrastructure

.. todo::

    Add information about address ranges and interleaved address ranges.

Todo list
~~~~~~~~~

.. todolist::
