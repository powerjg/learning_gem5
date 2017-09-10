:authors: Jason Lowe-Power

.. _MSI-running-section:

------------------------------------------
Running the simple Ruby system
------------------------------------------

Now, we can run our system with the MSI protocol!

As something interesting, below is a simple multithreaded program (note: as of this writing there is a bug in gem5 preventing this code from executing).

.. code-block:: c++

    #include <iostream>
    #include <thread>

    using namespace std;

    /*
     * c = a + b
     */
    void array_add(int *a, int *b, int *c, int tid, int threads, int num_values)
    {
        for (int i = tid; i < num_values; i += threads) {
            c[i] = a[i] + b[i];
        }
    }


    int main(int argc, char *argv[])
    {
        unsigned num_values;
        if (argc == 1) {
            num_values = 100;
        } else if (argc == 2) {
            num_values = atoi(argv[1]);
            if (num_values <= 0) {
                cerr << "Usage: " << argv[0] << " [num_values]" << endl;
                return 1;
            }
        } else {
            cerr << "Usage: " << argv[0] << " [num_values]" << endl;
            return 1;
        }

        unsigned cpus = thread::hardware_concurrency();

        cout << "Running on " << cpus << " cores. ";
        cout << "with " << num_values << " values" << endl;

        int *a, *b, *c;
        a = new int[num_values];
        b = new int[num_values];
        c = new int[num_values];

        if (!(a && b && c)) {
            cerr << "Allocation error!" << endl;
            return 2;
        }

        for (int i = 0; i < num_values; i++) {
            a[i] = i;
            b[i] = num_values - i;
            c[i] = 0;
        }

        thread **threads = new thread*[cpus];

        // NOTE: -1 is required for this to work in SE mode.
        for (int i = 0; i < cpus - 1; i++) {
            threads[i] = new thread(array_add, a, b, c, i, cpus, num_values);
        }
        // Execute the last thread with this thread context to appease SE mode
        array_add(a, b, c, cpus - 1, cpus, num_values);

        cout << "Waiting for other threads to complete" << endl;

        for (int i = 0; i < cpus - 1; i++) {
            threads[i]->join();
        }

        delete[] threads;

        cout << "Validating..." << flush;

        int num_valid = 0;
        for (int i = 0; i < num_values; i++) {
            if (c[i] == num_values) {
                num_valid++;
            } else {
                cerr << "c[" << i << "] is wrong.";
                cerr << " Expected " << num_values;
                cerr << " Got " << c[i] << "." << endl;
            }
        }

        if (num_valid == num_values) {
            cout << "Success!" << endl;
            return 0;
        } else {
            return 2;
        }
    }


With the above code compiled as ``threads``, we can run gem5!

.. code-block:: sh

    build/MSI/gem5.opt configs/learning_gem5/part6/simple_ruby.py


The output should be something like the following.
Most of the warnings are unimplemented syscalls in SE mode due to using pthreads and can be safely ignored for this simple example.

::

    gem5 Simulator System.  http://gem5.org
    gem5 is copyrighted software; use the --copyright option for details.

    gem5 compiled Sep  7 2017 12:39:51
    gem5 started Sep 10 2017 20:56:35
    gem5 executing on fuggle, pid 6687
    command line: build/MSI/gem5.opt configs/learning_gem5/part6/simple_ruby.py

    Global frequency set at 1000000000000 ticks per second
    warn: DRAM device capacity (8192 Mbytes) does not match the address range assigned (512 Mbytes)
    0: system.remote_gdb.listener: listening for remote gdb #0 on port 7000
    0: system.remote_gdb.listener: listening for remote gdb #1 on port 7001
    Beginning simulation!
    info: Entering event queue @ 0.  Starting simulation...
    warn: Replacement policy updates recently became the responsibility of SLICC state machines. Make sure to setMRU() near callbacks in .sm files!
    warn: ignoring syscall access(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall access(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall mprotect(...)
    warn: ignoring syscall set_robust_list(...)
    warn: ignoring syscall rt_sigaction(...)
          (further warnings will be suppressed)
    warn: ignoring syscall rt_sigprocmask(...)
          (further warnings will be suppressed)
    info: Increasing stack size by one page.
    info: Increasing stack size by one page.
    Running on 2 cores. with 100 values
    warn: ignoring syscall mprotect(...)
    warn: ClockedObject: Already in the requested power state, request ignored
    warn: ignoring syscall set_robust_list(...)
    Waiting for other threads to complete
    warn: ignoring syscall madvise(...)
    Validating...Success!
    Exiting @ tick 9386342000 because exiting with last active thread context
