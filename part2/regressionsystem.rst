
:authors: Matteo M. Fusi

.. _regression-system-chapther:


------------------------------------------
Extending the Regression System
------------------------------------------
Regression testing is an important techniques that allows to verify that modifications of the code don't break current functionalities of the software. The main idea is that you have you run a set of test-cases after a modification and you compare their output with a reference: if the result if a test-case is the same (or within a certain threshold), then your modification passed a test, otherwise not. In theory every modification you make should pass every test of the regression system, in practice this is not always true since the theory can be really far from the reality.
gem5 has a built-in system of regression testing based on SCons and it is very easy to modify if you know where you have to put hands on. In this chapter we will se how to modify the scripts in order to extend the built-in gem5 regression system. Following this chapter you will learn how to add categories and modes to the regression system.

Current organization
~~~~~~~~~~~~~~~~~~~~
gem5 stores everything about regression testing in the ``tests`` folder. This folder contains the following elements:

SConscript
   A SCons script which is called everytime you run the regression system
test-prog
   This folder contains the executables that will be used by the test cases. Everything is organized in a structured way.
quick/long
   These folders represents the categories of test-cases. Trivially, quick represent a categories of test-cases that should terminate relatively fast and long is the opposite. These are the default categories, but it is possible to add additional ones.
configs
   It contains the configuration scripts needed by the regression system.
diff-out
   It is a perl script that it is used after a test passes. It seeks and find differences between stats.txt of the reference and the executed test-case.
testing
   A folder that contains helper utilities for scanning folders, check the result of a test case. It is important for adding categories and modes.
run.py
   It is the python scripts that instantiate and invoke the execution of a test-case.

As you can see the regression system is self-contained. A nice feature of gem5 regression system is that you don't need to specify test-cases in a file: you just need to put some required files in the correct folder hierarchy. The con of this system is that ypu have to put these files in the correct locations **using the correct naming convention**.
You can run the regression tests using the script ``util/regression``. It tries to verify as more features as possible and you can modify its behaviour by passing options. As usual, pass it the ``--help`` flag to know more about it (or review its code).
Every reference of a test-cases identifies a runnable test. Reference of test-cases are organized and stored with the following structure:

::

    tests/<test category>/<mode>/<test name>/ref/<architecture>/<operating system>/<configuration>/

Adding a simple test-case
~~~~~~~~~~~~~~~~~~~~~~~~~

For example, a test for the classic hello world program in SE mode using a simple-timing configuration  is:

::

    tests/quick/se/00.hello/x86/linux/simple-timing

We put this test is the ``quick`` category since it doesn't require a lot of time to terminate. We run it in ``se`` mode on the ``x86`` architecture. Using `se`, `linux` is not really important, but it is required. ``simple-timing`` specify which configuration file load in the **previously specified** ``configuration`` folder.
In such a folder we must put the output of the execution of an hello world program that uses this configuration. It is possible to use gem5 and run the following commands:

::

    build/X86/gem5.opt -re configs/example/se.py --cmd=tests/test-progs/hello/bin/x86/hello
    mkdir -p tests/quick/00.hello/ref/x86/linux/simple-timing
    cp m5out/{config.ini,stats.txt,simout,simerr} tests/quick/00.hello/ref/x86/linux/simple-timing

The last thing we miss is a ``test.py`` that must be put into the folder ``tests/quick/00.hello/``. This file specifies additional parameters to the execution that are not stated in the configuration file. 
You can use the following piece of code:

.. code-block:: python 

    root.system.cpu[0].workload = Process(cmd = 'hello',
                                      executable = binpath('hello'))
    if root.system.cpu[0].checker != NULL:
        root.system.cpu[0].checker.workload = root.system.cpu[0].workload


To sum up, we ran the hello world, we copied the output in the right folder and we added some additional configuration with the ``test.py`` script... and that's it. Now the test we'll be run everytime we want to run regression test for quick category and SE mode.
After a modification you would like to run just one single test. It is possible to do it by running:

::

    scons build/X86/tests/opt/quick/00.hello

If you want to update the reference of a test-case using:

::

    scons --update-ref build/X86/tests/opt/quick/00.hello 

Adding a new category
~~~~~~~~~~~~~~~~~~~~~

Now we want to move our test named ``00.hello`` in a new category called ``misc`` because we realized that this test is not suitable for the ``quick`` category. What we have to do is to create a new directory called ``misc`` and move our test-case in it, and modify the ``tests/testing/tests.py`` file in order to helo SCons in finding the test-cases.

::

    mkdir tests/misc
    mv tests/quick/00.hello tests/misc/00.hello

Now we modify ``tests/testing/tests.py``: look for a variables colled ``all_categories``. It's a tuple that stores all the possible valid categories. You should add your new category ``misc`` to this tuple:

::

    all_categories = ("quick", "long", "misc")


Adding a new mode
~~~~~~~~~~~~~~~~~

The process is the same that we did while we were adding a new category, but it now we create a new folder at a different level (we change ``se`` instead of ``quick``) and we modify the variable ``all_modes`` in the file ``tests/testing/tests.py``.

