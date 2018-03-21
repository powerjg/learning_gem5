:authors: Jason Lowe-Power

Part III: Ruby
======================================

**OPEN UP THE PDF OF THE PRIMER**

Overview
---------

* Slides on ruby overview

-------------------------------

* Start looking at a state machine file
* Slide on output

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Look at MSI-cache.sm
  * Show the top part with the parameters

* Build the protocol
* Note: May want to use a different build directory (e.g., X86_MSI)

.. code-block:: sh

    scons -j100 build/X86/gem5.opt PROTOCOL=MSI SLICC_HTML=True

    vi src/learning_gem5/part3/MSI-cache.sm

    ls build/X86/mem/protocol

    vi build/X86/mem/protocol/L1Cache_Controller.py


.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!


---------------------------------------

Parameters to state machines
-----------------------------

* Talk about the parts of the state machine file
* Talk about cachememory
* talk about message buffers


.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!


* Show the message buffers in the cache and the directory

.. code-block:: sh

    vi src/learning_gem5/part3/MSI-cache.sh
    vi src/learning_gem5/part3/MSI-dir.sh

* Talk about the mandatory event queue
* Talk about the memory buffer


-----------------------------------------

States and events and other function
-------------------------------------

* talk about states and show the MSI-cache.sm states

.. code-block:: sh

    vi src/learning_gem5/part3/MSI-cache.sh


* talk about events and show the MSI-cache events

* Show the other functions, etc.
  * Entry
  * TBE/table
  * Declarations
  * other functions

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

----------------------------------------

In/out ports
------------

* High-level out_port and in_port stuff

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* Look at MSI-cache.sm


.. code-block:: sh

    vi src/learning_gem5/part3/MSI-cache.sh


* Talk about the message types
* Talk about how message buffer above links to the ports
* Look at the message and make a decision
* THIS IS THE ONLY PLACE YOU're ALLOWED TO USE IF STATEMENTS

* Start with mandatory queue
* Talk about how peek automatically populates in_msg

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* go through slide.

------------------------------------------

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

Actions
-------

* Look at the actions in MSI-cache.sm

* talk about automatic variables and where they come from (passed in in in_port)
* talk about enqueue and out_msg
* nesting peek and enqueue
* NO IF STATEMENTS!

* Special z_stall.

.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* go through slide

-------------------------

Transitions
-----------

* go through slide.
* Show HTML table

--------------------------

Config scripts
--------------

* go through slides

* After slide on sequencers, let's look at the config scripts for MSI-cache


.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!

* The first file we'll look at is kind of like caches.py from our simple scripts.
  * We extend the L1Cache_Controller like we did Cache before. (And direcotry)
  * Construct the whole Ruby
  * Create sequencers
  * Connect everything up
* Also extend the network to have our point-to-point network

.. code-block:: sh

    vi configs/learning_gem5/part3/msi_caches.py


* Next, let's check out simple_ruby.py

* Talk about how there's two phases. Creating the cache system and setup. This is required because there is a circular dependence between RubySystem and RubyNetwork. :/
* Talk about creating something with multiple threads.

.. code-block:: sh

    vi configs/learning_gem5/part3/simple_ruby.py


.. figure:: ../_static/figures/switch.png
   :width: 20 %

   Switch!


-------------------------------------

Other ruby things
-----------------

See slides.


Things I'd like to add
----------------------

* Debugging
  * It would be cool to go through an example broken protocol.
  * If I ever do a multi-day tutorial, this would be good to have as an activity.
