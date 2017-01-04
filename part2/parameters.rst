:authors: Jason Lowe-Power

.. _parameters-chapter:

------------------------------------------------
Adding parameters to SimObjects and more events
------------------------------------------------

One of the most powerful parts of gem5's Python interface is the ability to pass parameters from Python to the C++ objects in gem5.
In this chapter, we will explore some of the kinds of parameters for SimObjects and how to use them building off of the simple ``HelloObject`` from the `previous chapters`_.

.. _previous chapters: events-chapter

Simple parameters
~~~~~~~~~~~~~~~~~

First, we will add parameters for the latency and number of times to fire the event in the ``HelloObject``.
To add a parameter, modify the ``HelloObject`` class in the SimObject Python file (``src/learning_gem5/HelloObject.py``).
Parameters are set by adding new statements to the Python class that include a ``Param`` type.

For instance, the following code as a parameter ``time_to_wait`` which is a "Latency" parameter and ``number_of_fires`` which is an integer parameter.

.. code-block:: python

    class HelloObject(SimObject):
        type = 'HelloObject'
        cxx_header = "learning_gem5/hello_object.hh"

        time_to_wait = Param.Latency("Time before firing the event")
        number_of_fires = Param.Int(1, "Number fo times to fire the event before "
                                       "goodbye")

``Param.<TypeName>`` declares a parameter of type ``TypeName``.
Common types are ``Int`` for integers, ``Float`` for floats, etc.
These types act like regular Python classes.

Each parameter declaration takes one or two parameters.
When given two parameters (like ``number_of_fires`` above), the first parameter is the *default value* for the parameter.
In this case, if you instantiate a ``HelloObject`` in your Python config file without specifying any value for number_of_fires, it will take the default value of 1.

The second parameter to the parameter declaration is a short description of the parameter.
This must be a Python string.
If you only specify a single parameter to the parameter declaration, it is the description (as for ``time_to_wait``).

gem5 also supports many complex parameter types that are not just builtin types.
For instance, ``time_to_wait`` is a ``Latency``.
``Latency`` takes a value as a time value as a string and converts it into simulator **ticks**.
For instance, with a default tick rate of 1 picosecond (10^12 ticks per second or 1 THz), ``"1ns"`` is automatically converted to 1000.
There are other convience parameters like ``Percent``, ``Cycles``, ``MemorySize`` and many more.

Once you have declared these paramaters in the SimObject file, you need to copy their values to your C++ class in its construtor.
The following code shows the changes to the ``HelloObject`` constructor.

.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        SimObject(params),
        event(*this),
        myName(params->name),
        latency(params->time_to_wait),
        timesLeft(params->number_of_fires)
    {
        DPRINTF(Hello, "Created the hello object with the name %s\n", myName);
    }

Here, we use the parameter's values for the default values of latency and timesLeft.
Additionally, we store the ``name`` from the parameter object to use it later in the member variable ``myName``.
Each ``params`` instantiation has a name which comes from the Python config file when it is instantiated.

When we run gem5 with the above, we get the following error:

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan  4 2017 14:46:36
    gem5 started Jan  4 2017 14:46:52
    gem5 executing on chinook, pid 3422
    command line: build/X86/gem5.opt --debug-flags=Hello configs/learning_gem5/part2/run_hello.py

    Global frequency set at 1000000000000 ticks per second
    fatal: hello.time_to_wait without default or user set value

This is because the ``time_to_wait`` parameter does not have a default value.
Therefore, we need to update the Python config file (``run_hello.py``) to specify this value.

.. code-block:: python

    root.hello = HelloObject(time_to_wait = '2us')

Or, we can specify ``time_to_wait`` as a member variable.
Either option is exactly the same because the C++ objects are not created until ``m5.instantiate()`` is called.

.. code-block:: python

    root.hello = HelloObject()
    root.hello.time_to_wait = '2us'

The output of this simple script is the following when running the the ``Hello`` debug flag.

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan  4 2017 14:46:36
    gem5 started Jan  4 2017 14:50:08
    gem5 executing on chinook, pid 3455
    command line: build/X86/gem5.opt --debug-flags=Hello configs/learning_gem5/part2/run_hello.py

    Global frequency set at 1000000000000 ticks per second
          0: hello: Created the hello object with the name hello
    Beginning simulation!
    info: Entering event queue @ 0.  Starting simulation...
    2000000: hello: Hello world! Processing the event! 0 left
    2000000: hello: Done firing!
    Exiting @ tick 18446744073709551615 because simulate() limit reached

You can also modify the config script to fire the event multiple times.

Other SimObjects as parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also specify other SimObjects as parameters.
To demonstrate this, we are going to create a new SimObject, ``GoodbyeObject``.
This object is going to have a simple function that says "Goodbye" to another SimObject.
To make it a little more interesting, the ``GoodbyeObject`` is going to have a buffer to write the message, and a limited bandwidth to write the message.

First, declare the SimObject in the SConscript file:

.. code-block:: python

    Import('*')

    SimObject('HelloObject.py')
    Source('hello_object.cc')
    Source('goodbye_object.cc')

    DebugFlag('Hello')

The new SConscript file can be downloaded `here <../_static/scripts/part2/parameters/SConscript>`

Next, you need to declare the new SimObject in a SimObject Python file.
Since the ``GoodbyeObject`` is highly related to the ``HelloObject``, we will use the same file.
You can add the following code to ``HelloObject.py``.

This object has two parameters, both with default values.
The first parameter is the size of a buffer and is a ``MemorySize`` parameter.
Second is the ``write_bandwidth`` which specifies the speed to fill the buffer.
Once the buffer is full, the simulation will exit.

.. code-block:: python

    class GoodbyeObject(SimObject):
        type = 'GoodbyeObject'
        cxx_header = "learning_gem5/goodbye_object.hh"

        buffer_size = Param.MemorySize('1kB',
                                       "Size of buffer to fill with goodbye")
        write_bandwidth = Param.MemoryBandwidth('100MB/s', "Bandwidth to fill "
                                                "the buffer")

The updated ``HelloObject.py`` file can be downloaded `here <../_static/scripts/part2/parameters/HelloObject.py>`

Now, we need to implement the ``GoodbyeObject``.

.. code-block:: c++

    #ifndef __LEARNING_GEM5_GOODBYE_OBJECT_HH__
    #define __LEARNING_GEM5_GOODBYE_OBJECT_HH__

    #include <string>

    #include "params/GoodbyeObject.hh"
    #include "sim/sim_object.hh"

    class GoodbyeObject : public SimObject
    {
      private:
        void processEvent();

        /**
         * Fills the buffer for one iteration. If the buffer isn't full, this
         * function will enqueue another event to continue filling.
         */
        void fillBuffer();

        EventWrapper<GoodbyeObject, &GoodbyeObject::processEvent> event;

        /// The bytes processed per tick
        float bandwidth;

        /// The size of the buffer we are going to fill
        int bufferSize;

        /// The buffer we are putting our message in
        char *buffer;

        /// The message to put into the buffer.
        std::string message;

        /// The amount of the buffer we've used so far.
        int bufferUsed;

      public:
        GoodbyeObject(GoodbyeObjectParams *p);

        /**
         * Called by an outside object. Starts off the events to fill the buffer
         * with a goodbye message.
         *
         * @param name the name of the object we are saying goodbye to.
         */
        void sayGoodbye(std::string name);
    };

    #endif // __LEARNING_GEM5_GOODBYE_OBJECT_HH__

.. code-block:: c++

    #include "learning_gem5/goodbye_object.hh"

    #include "debug/Hello.hh"
    #include "sim/sim_exit.hh"

    GoodbyeObject::GoodbyeObject(GoodbyeObjectParams *params) :
        SimObject(params), event(*this), bandwidth(params->write_bandwidth),
        bufferSize(params->buffer_size), buffer(nullptr), bufferUsed(0)
    {
        buffer = new char[bufferSize];
        DPRINTF(Hello, "Created the goodbye object\n");
    }

    void
    GoodbyeObject::processEvent()
    {
        DPRINTF(Hello, "Processing the event!\n");
        fillBuffer();
    }

    void
    GoodbyeObject::sayGoodbye(std::string other_name)
    {
        DPRINTF(Hello, "Saying goodbye to %s\n", other_name);

        message = "Goodbye " + other_name + "!! ";

        fillBuffer();
    }

    void
    GoodbyeObject::fillBuffer()
    {
        // There better be a message
        assert(message.length() > 0);

        // Copy from the message to the buffer per byte.
        int bytes_copied = 0;
        for (auto it = message.begin();
             it < message.end() && bufferUsed < bufferSize - 1;
             it++, bufferUsed++, bytes_copied++) {
            // Copy the character into the buffer
            buffer[bufferUsed] = *it;
        }

        if (bufferUsed < bufferSize - 1) {
            // Wait for the next copy for as long as it would have taken
            DPRINTF(Hello, "Scheduling another fillBuffer in %d ticks\n",
                    bandwidth * bytes_copied);
            schedule(event, curTick() + bandwidth * bytes_copied);
        } else {
            DPRINTF(Hello, "Goodbye done copying!\n");
            // Be sure to take into account the time for the last bytes
            exitSimLoop(buffer, 0, curTick() + bandwidth * bytes_copied);
        }
    }

    GoodbyeObject*
    GoodbyeObjectParams::create()
    {
        return new GoodbyeObject(this);
    }

The header file can be downloaded `here <../_static/scripts/part2/parameters/goodbye_object.hh>` and the implemenation can be downloaded `here <../_static/scripts/part2/parameters/goodbye_object.cc>`

The interface to this ``GoodbyeObject`` is simple a function ``sayGoodbye`` which takes a string as a parameter.
When this function is called, the simulator builds the message and saves it in a member variable.
Then, we begin filling the buffer.

To model the limited bandwidth, each time we write the message to the buffer, we pause for the latency it takes to write the message.
We use a simple event to model this pause.

Since we used a ``MemoryBandwidth`` parameter in the SimObject declaration, the ``bandwidth`` variable is automatically converted into bytes per tick, so calculating the latency is simply the bandwidth times the bytes we want to write the buffer.

Finally, when the buffer is full, we call the function ``exitSimLoop``, which will exit the simulation.
This function takes three parameters, the first is the message to return to the Python config script (``exit_event.getCause()``), the second is the exit code, and the third is when to exit.

Adding the GoodbyeObject as a parameter to the HelloObject
##########################################################

First, we will also add a ``GoodbyeObject`` as a parameter to the ``HelloObject``.
To do this, you simply specify the SimObject class name as the ``TypeName`` of the ``Param``.
You can have a default, or not, just like a normal parameter.

.. code-block:: python

    class HelloObject(SimObject):
        type = 'HelloObject'
        cxx_header = "learning_gem5/hello_object.hh"

        time_to_wait = Param.Latency("Time before firing the event")
        number_of_fires = Param.Int(1, "Number fo times to fire the event before "
                                       "goodbye")

        goodbye_object = Param.GoodbyeObject("A goodbye object")

The updated ``HelloObject.py`` file can be downloaded `here <../_static/scripts/part2/parameters/HelloObject.py>`

Second, we will add a reference to a ``GoodbyeObject`` to the ``HelloObject`` class.

.. code-block:: c++

    class HelloObject : public SimObject
    {
      private:
        void processEvent();

        EventWrapper<HelloObject, &HelloObject::processEvent> event;

        /// Pointer to the corresponding GoodbyeObject. Set via Python
        GoodbyeObject& goodbye;

        /// The name of this object in the Python config file
        std::string myName;

        /// Latency between calling the event (in ticks)
        Tick latency;

        /// Number of times left to fire the event before goodbye
        int timesLeft;

      public:
        HelloObject(HelloObjectParams *p);

        void startup();
    };

Then, we need to update the constructor and the process event function of the ``HelloObject``.

.. code-block:: c++

    HelloObject::HelloObject(HelloObjectParams *params) :
        SimObject(params),
        event(*this),
        goodbye(*params->goodbye_object),
        myName(params->name),
        latency(params->time_to_wait),
        timesLeft(params->number_of_fires)
    {
        DPRINTF(Hello, "Created the hello object\n");
    }

Once we have processed the number of event specified by the parameter, we should call the ``sayGoodbye`` function in the ``GoodbyeObject``.

.. code-block:: c++

    void
    HelloObject::processEvent()
    {
        timesLeft--;
        DPRINTF(Hello, "Hello world! Processing the event! %d left\n", timesLeft);

        if (timesLeft <= 0) {
            DPRINTF(Hello, "Done firing!\n");
            goodbye.sayGoodbye(myName);
        } else {
            schedule(event, curTick() + latency);
        }
    }

You can find the updated header file `here <../_static/scripts/part2/parameters/hello_object.hh>` and the implemenation file `here <../_static/scripts/part2/parameters/hello_object.cc>`.

Updating the config script
##########################

Lastly, we need to add the ``GoodbyeObject`` to the config script.
Create a new config script, ``hello_goodbye.py`` and instantiate both the hello and the goodbye objects.
For instance, one possible script is the following.

.. code-block:: python

    import m5
    from m5.objects import *

    root = Root(full_system = False)

    root.hello = HelloObject(time_to_wait = '2us', number_of_fires = 5)
    root.hello.goodbye_object = GoodbyeObject(buffer_size='100B')

    m5.instantiate()

    print "Beginning simulation!"
    exit_event = m5.simulate()
    print 'Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause())

You can download this script `here <../_static/scripts/part2/parameters/hello_goodbye.py>`

Running this script generates the following output.

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Jan  4 2017 15:17:14
    gem5 started Jan  4 2017 15:18:41
    gem5 executing on chinook, pid 3838
    command line: build/X86/gem5.opt --debug-flags=Hello configs/learning_gem5/part2/hello_goodbye.py

    Global frequency set at 1000000000000 ticks per second
          0: hello.goodbye_object: Created the goodbye object
          0: hello: Created the hello object
    Beginning simulation!
    info: Entering event queue @ 0.  Starting simulation...
    2000000: hello: Hello world! Processing the event! 4 left
    4000000: hello: Hello world! Processing the event! 3 left
    6000000: hello: Hello world! Processing the event! 2 left
    8000000: hello: Hello world! Processing the event! 1 left
    10000000: hello: Hello world! Processing the event! 0 left
    10000000: hello: Done firing!
    10000000: hello.goodbye_object: Saying goodbye to hello
    10000000: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10152592: hello.goodbye_object: Processing the event!
    10152592: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10305184: hello.goodbye_object: Processing the event!
    10305184: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10457776: hello.goodbye_object: Processing the event!
    10457776: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10610368: hello.goodbye_object: Processing the event!
    10610368: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10762960: hello.goodbye_object: Processing the event!
    10762960: hello.goodbye_object: Scheduling another fillBuffer in 152592 ticks
    10915552: hello.goodbye_object: Processing the event!
    10915552: hello.goodbye_object: Goodbye done copying!
    Exiting @ tick 10944163 because Goodbye hello!! Goodbye hello!! Goodbye hello!! Goodbye hello!! Goodbye hello!! Goodbye hello!! Goo

You can modify the parameters to these two SimObjects and see how the overall execution time (Exiting @ tick **10944163**) changes.
To run these tests, you may want to remove the debug flag so there is less output to the terminal.

In the next chapters, we will create a more complex and more useful SimObject, culminating with a simple blocking uniprocessor cache implemenation.
