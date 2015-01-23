:authors: Jason Power


------------------------------
Some thoughts on this document
------------------------------

* We want this document to be living.
   * We should have the source checked in somewhere (probably in a repo next to gem5).
   * We should force people to make updates when they break things.
   * We should have the source for the examples checked into the gem5 repo, and have tests that run them.

An outline:

#. Part I: Getting started
    #. Building gem5
    #. A simple gem5 configuration script
    #. A more complex gem5 configuration script
    #. Using the example configuration scripts
    #. Full system simulation
#. Part II: Developing with gem5
    #. Creating a new SimObject
    #. Debugging support in gem5
    #. Creating a new MemObject with master/slave ports
    #. Contributing back to gem5
#. Part III: Using Ruby cache coherence model
    #. Overview of Ruby
    #. Ruby's cache coherence protocols
    #. Ruby's network topologies
    #. Writing a new protocol
    #. Debugging a protocol
    #. Extending the SLICC language


Todo list
~~~~~~~~~

.. todolist::
