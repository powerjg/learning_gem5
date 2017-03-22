

:authors: Jason Lowe-Power

.. _development-environment-chapter:

------------------------------------------
Setting up your development environment
------------------------------------------

This is going to talk about getting started developing gem5.

gem5-style guidelines
~~~~~~~~~~~~~~~~~~~~~~

When modifying any open source project, it is important to follow the project's style guidelines.
Details on gem5 style can be found on the gem5 `wiki page`_.

.. _wiki page: http://gem5.org/Coding_Style

To help you conform to the style guidelines, gem5 includes a script which runs whenever you finalize anything in mercurial (i.e. commit a changeset or refresh a patch).
This script should be automatically added to your .hg/hgrc file by SCons the first time you build gem5.
If you see the following error, you may need to install the mercurial python library.

::

	Mercurial libraries cannot be found, ignoring style hook.  If
	you are a gem5 developer, please fix this and run the style
	hook. It is important.

The key takeaways from the style guide are:

# Use 4 spaces, not tabs
# Sort the includes
# Use capitalized camel case for class names, camel case for member variables, and underscores for local variables.
# Document your code

Mercurial patch queues
~~~~~~~~~~~~~~~~~~~~~~~

Most people developing with gem5 use the patch queue feature of mercurial to track their changes.
This makes it quite simple to commit your changes back to gem5.
Additionally, using patch queues can make it easier to update gem5 with new changes that other people make while keeping your own changes separate.
The `Mercurial book`_ has a great chapter_ describing the details of how to use Mercurial patch queues.

.. _Mercuial book: http://hgbook.red-bean.com/

.. _chapter: http://hgbook.red-bean.com/read/managing-change-with-mercurial-queues.html
