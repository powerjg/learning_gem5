:authors: Jason Lowe-Power

.. _hello-simobject-chapter:

------------------------------------------
Creating a *very* simple SimObject
------------------------------------------

Almost all objects in gem5 inherit from the base SimObject type.
SimObjects export the main interfaces to all objects in gem5.
SimObjects are wrapped ``C++`` objects that are accessible from the ``Python`` configuration scripts.

SimObjects can have many parameters, which are set via the ``Python`` configuration files.
In addition to simple parameters like integers and floating point numbers, they can also have other SimObjects as parameters.
This allows you to create complex system hierarchies, like real machines.

In this chapter, we will walk through creating a simple "HelloWorld" SimObject.
The goal is to introduce you to how SimObjects are created and the required boilerplate code for all SimObjects.
We will also create a simple ``Python`` configuration script which instantiates our SimObject.

In the next few chapters, we will take this simple SimObject and expand on it to include `debugging support`_, `dynamic events`_, and `parameters`_.

.. _debugging support: debugging-chapter

.. _dynamic events: events-chapter

.. _parameters: parameters-chapter

.. sidebar:: Using git branches

	It is common to use a new git branch for each new feature you add to gem5.

	The first step when adding a new feature or modifying something in gem5, is to create a new branch to store your changes.
	Details on git branches can be found in the `Git book`_.

	.. _Git book: https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell

	.. code-block:: sh

		git checkout -b hello-simobject


Step 1: Create a Python class for your new SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each SimObject has a Python class which is associated with it.
This Python class describes the parameters of your SimObject that can be controlled from the Python configuration files.
For our simple SimObject, we are just going to start out with no parameters.
Thus, we simply need to declare a new class for our SimObject and set it's name and the C++ header that will define the C++ class for the SimObject.

We can create a file, HelloObject.py, in ``src/learning_gem5``

.. code-block:: python

	from m5.params import *
	from m5.SimObject import SimObject

	class HelloObject(SimObject):
	    type = 'HelloObject'
	    cxx_header = "learning_gem5/hello_object.hh"

You can find the complete file :download:`here <../_static/scripts/part2/helloobject/HelloObject.py>`.

It is not required that the ``type`` be the same as the name of the class, but it is convention.
The ``type`` is the C++ class that you are wrapping with this Python SimObject.
Only in special circumstances should the ``type`` and the class name be different.

The ``cxx_header`` is the file that contains the declaration of the class used as the ``type`` parameter.
Again, the convention is to use the name of the SimObject with all lowercase and underscores, but this is only convention.
You can specify any header file here.

Step 2: Implement your SimObject in C++
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we need to create ``hello_object.hh`` and ``hello_object.cc`` which will implement the hello object.

We'll start with the header file for our ``C++`` object.
By convention, gem5 wraps all header files in ``#ifndef/#endif`` with the name of the file and the directory its in so there are no circular includes.

The only thing we need to do in the file is to declare our class.
Since ``HelloObject`` is a SimObject, it must inherit from the C++ SimObject class.
Most of the time, your SimObject's parent will be a subclass of SimObject, not SimObject itself.

The SimObject class specifies many virtual functions.
However, none of these functions are pure virtual, so in the simplest case, there is no need to implement any functions except for the constructor.

The constructor for all SimObjects assumes it will take a parameter object.
This parameter object is automatically created by the build system and is based on the ``Python`` class for the SimObject, like the one we created above.
The name for this parameter type is generated automatically from the name of your object.
For our "HelloObject" the parameter type's name is "HelloObject**Params**".

The code required for our simple header file is listed below.

.. code-block:: c++

	#ifndef __LEARNING_GEM5_HELLO_OBJECT_HH__
	#define __LEARNING_GEM5_HELLO_OBJECT_HH__

	#include "params/HelloObject.hh"
	#include "sim/sim_object.hh"

	class HelloObject : public SimObject
	{
	  public:
	    HelloObject(HelloObjectParams *p);
	};

	#endif // __LEARNING_GEM5_HELLO_OBJECT_HH__

You can find the complete file :download:`here <../_static/scripts/part2/helloobject/hello_object.hh>`.

Next, we need to implement *two* functions in the ``.cc`` file, not just one.
The first function, is the constructor for the ``HelloObject``.
Here we simply pass the parameter object to the SimObject parent and print "Hello world!"

*Normally, you would **never** use ``std::cout`` in gem5.*
Instead, you should use debug flags.
In the `next chapter`_, we will modify this to use debug flags instead.
However, for now, we'll simply use ``std::cout`` because it is simple.

.. _next chapter: debugging-chapter

.. code-block:: c++

	#include "learning_gem5/hello_object.hh"

	#include <iostream>

	HelloObject::HelloObject(HelloObjectParams *params) : SimObject(params)
	{
	    std::cout << "Hello World! From a SimObject!" << std::endl;
	}

There is another function that we have to implement as well for the SimObject to be complete.
We must implement one function for the parameter type that is implicitly created from the SimObject ``Python`` declaration, namely, the ``create`` function.
This function simply returns a new instantiation of the SimObject.
Usually this function is very simple (as below).

.. code-block:: c++

	HelloObject*
	HelloObjectParams::create()
	{
	    return new HelloObject(this);
	}

You can find the complete file :download:`here <../_static/scripts/part2/helloobject/hello_object.cc>`.

If you forget to add the create function for your SimObject, you will get a linker error when you compile.
It will look something like the following.

::

	build/X86/python/m5/internal/param_HelloObject_wrap.o: In function `_wrap_HelloObjectParams_create':
	/local.chinook/gem5/gem5-tutorial/gem5/build/X86/python/m5/internal/param_HelloObject_wrap.cc:3096: undefined reference to `HelloObjectParams::create()'
	collect2: error: ld returned 1 exit status
	scons: *** [build/X86/gem5.opt] Error 1
	scons: building terminated because of errors.

This ``undefined reference to `HelloObjectParams::create()'`` means you need to implement the create function for your SimObject.


Step 3: Register the SimObject and C++ file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order for the ``C++`` file to be compiled and the ``Python`` file to be parsed we need to tell the build system about these files.
gem5 uses SCons as the build system, so you simply have to create a SConscript file in the directory with the code for the SimObject.
If there is already a SConscript file for that directory, simply add the following declarations to that file.

This file is simply a normal ``Python`` file, so you can write any ``Python`` code you want in this file.
Some of the scripting can become quite complicated.
gem5 leverages this to automatically create code for SimObjects and to compile the domain-specific languages like SLICC and the ISA language.

In the SConscript file, there are a number of functions automatically defined after you import them.
See the section on that...

.. todo:: make a section on the SConscript build system which discuss all of the functions.

To get your new SimObject to compile, you simply need to create a new file with the name "SConscript" in the ``src/learning_gem5`` directory.
In this file, you have to declare the SimObject and the ``.cc`` file.
Below is the required code.

.. code-block:: python

	Import('*')

	SimObject('HelloObject.py')
	Source('hello_object.cc')

You can find the complete file :download:`here <../_static/scripts/part2/helloobject/SConscript>`.

Step 4: (Re)-build gem5
~~~~~~~~~~~~~~~~~~~~~~~

To compile and link your new files you simply need to recompile gem5.
The below example assumes you are using the x86 ISA, but nothing in our object requires an ISA so, this will work with any of gem5's ISAs.

.. code-block:: sh

	scons build/X86/gem5.opt


Step 5: Create the config scripts to use your new SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have implemented a SimObject, and it has been compiled into gem5, you need to create or modify a ``Python`` config file to instantiate your object.
Since your object is very simple a system object is not required!
CPUs are not needed, or caches, or anything, except a ``Root`` object.
All gem5 instances require a ``Root`` object.

Walking through creating a *very* simple configuration script, first, import m5 and all of the objects you have compiled.

.. code-block:: python

	import m5
	from m5.objects import *

Next, you have to instantiate the ``Root`` object, as required by all gem5 instances.

.. code-block:: python

	root = Root(full_system = False)

Now, you can instantiate the ``HelloObject`` you created.
All you need to do is call the ``Python`` "constructor".
Later, we will look at how to specify parameters via the ``Python`` constructor.
In addition to creating an instantiation of your object, you need to make sure that it is a child of the root object.
Only SimObjects that are children of the ``Root`` object are instantiated in ``C++``.

.. code-block:: python

	root.hello = HelloObject()

Finally, you need to call ``instantiate`` on the ``m5`` module and actually run the simulation!

.. code-block:: python

	m5.instantiate()

	print "Beginning simulation!"
	exit_event = m5.simulate()
	print 'Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause())

You can find the complete file :download:`here <../_static/scripts/part2/helloobject/run_hello.py>`.

The output should look something like the following

::

	gem5 Simulator System.  http://gem5.org
	gem5 is copyrighted software; use the --copyright option for details.

	gem5 compiled May  4 2016 11:37:41
	gem5 started May  4 2016 11:44:28
	gem5 executing on mustardseed.cs.wisc.edu, pid 22480
	command line: build/X86/gem5.opt configs/learning_gem5/part2/run_hello.py

	Global frequency set at 1000000000000 ticks per second
	Hello World! From a SimObject!
	Beginning simulation!
	info: Entering event queue @ 0.  Starting simulation...
	Exiting @ tick 18446744073709551615 because simulate() limit reached

Congrats! You have written your first SimObject.
In the next chapters, we will extend this SimObject and explore what you can do with SimObjects.
