:authors: Jason Power


------------------------------
Some thoughts on this document
------------------------------

* Changes that need to happen before next stable release
   * Remove is_top_level

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
    #. Running tests
#. Advanced gem5 usage
    #. Full-system simulation
    #. Checkpoint creation and restoring
    #. ISA language
    #. Using m5ops
    #. Using traces
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

Todo list
~~~~~~~~~

.. todolist::
