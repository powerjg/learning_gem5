:authors: Jason Lowe-Power

.. _full-system-intro-chapter:

----------------------------
gem5 Full System Simulation
----------------------------

One of the most exciting features of gem5 is the ability to simulate the full system.
In syscall emulation mode, gem5 acts more like an emulator or hypervisor than a traditional simulator.
In full system mode, gem5 simulates all of the hardware from the CPU to the I/O devices.
This allows gem5 to execute binaries with no modifications.
Additionally, full system mode allows researchers to investigate the impacts of the operating system and other low-level details.

Why full system simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~

#. More realistic
#. Runs unmodified OS binaries
#. Less magic than syscall emulation mode
#. OS investigations
#. Devices are simulated


Main differences from SE mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a number of differences between syscall emulation mode and full system mode.
The most important is that in full system mode it is much harder to fake things.
For instance, in full system mode, as a user, you have to provide a compiled Linux kernel and a disk image.
Then, to run applications in gem5, you have to boot the operating system, then you can interact as if it is a running computer.

.. todo::

	Other differences between SE and FS mode...
