:authors: Jason Lowe-Power

.. _MSI-building-section:

------------------------------------------
Compiling a SLICC protocol
------------------------------------------

The SLICC file
~~~~~~~~~~~~~~

Now that we have finished implementing the protocol, we need to compile it.
You can download the complete SLICC files below:

- :download:`MSI-cache.sm <../../_static/scripts/part3/MSI_protocol/MSI-cache.sm>`
- :download:`MSI-dir.sm <../../_static/scripts/part3/MSI_protocol/MSI-dir.sm>`
- :download:`MSI-msg.sm <../../_static/scripts/part3/MSI_protocol/MSI-msg.sm>`

Before building the protocol, we need to create one more file: ``MSI.slicc``.
This file tells the SLICC compiler which state machine files to compile for this protocol.
The first line contains the name of our protocol.
Then, the file has a number of ``include`` statements.
Each ``include`` statement has a file name.
This filename can come from any of the ``protocol_dirs`` directories.
We declared the current directory as part of the ``protocol_dirs`` in the SConsopts file (``protocol_dirs.append(str(Dir('.').abspath))``).
The other directory is ``src/mem/protocol/``.
These files are included like C++h header files.
Effectively, all of the files are processed as one large SLICC file.
Thus, any files that declare types that are used in other files must come before the files they are used in (e.g., ``MSI-msg.sm`` must come before ``MSI-cache.sm`` since ``MSI-cache.sm`` uses the ``RequestMsg`` type).

.. code-block:: c++

    protocol "MSI";
    include "RubySlicc_interfaces.slicc";
    include "MSI-msg.sm";
    include "MSI-cache.sm";
    include "MSI-dir.sm";

You can download the fill file :download:`here <../../_static/scripts/part3/MSI_protocol/MSI.slicc>`

Compiling a protocol with SCons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most SCons defaults (found in ``build_opts/``) specify the protocol as ``MI_example``, an example, but poor performing protocol.
Therefore, we cannot simply use a default build name (e.g., ``X86`` or ``ARM``).
We have to specify the SCons options on the command line.
The command line below will build our new protocol with the X86 ISA.

.. code-block:: sh

    scons build/X86_MSI/gem5.opt --default=X86 PROTOCOL=MSI SLICC_HTML=True


This command will build ``gem5.opt`` in the directory ``build/X86_MSI``.
You can specify *any* directory here.
This command line has two new parameters: ``--default`` and ``PROTOCOL``.
First, ``--default`` specifies which file to use in ``build_opts`` for defaults for all of the SCons variables (e.g., ``ISA``, ``CPU_MODELS``).
Next, ``PROTOCOL`` *overrides* any default for the ``PROTOCOL`` SCons variable in the default specified.
Thus, we are telling SCons to specifically compile our new protocol, not whichever protocol was specified in ``build_opts/X86``.

There is one more variable on this command line to build gem5: ``SLICC_HTML=True``.
When you specify this on the building command line, SLICC will generate the HTML tables for your protocol.
You can find the HTML tables in ``<build directory>/mem/protocol/html``.
By default, the SLICC compiler skips building the HTML tables because it impacts the performance of compiling gem5, especially when compiling on a network file system.

After gem5 finishes compiling, you will have a gem5 binary with your new protocol!
If you want to build another protocol into gem5, you have to change the ``PROTOCOL`` SCons variable.
Thus, it is a good idea to use a different build directory for each protocol, especially if you will be comparing protocols.

When building your protocol, you will likely encounter errors in your SLICC code reported by the SLICC compiler.
Most errors include the file and line number of the error.
Sometimes, this line number is the line *after* the error occurs.
In fact, the line number can be far below the actual error.
For instance, if the curly brackets do not match correctly, the error will report the last line in the file as the location.
