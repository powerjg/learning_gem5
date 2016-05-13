:author: Jason Lowe-Power


Introduction
------------

This is an intro to this tutorial.
It says lots of interesting things.

The goal of this document is to give you, the reader, a thorough introduction on how to use gem5 and the gem5 codebase.
The purpose of this document is not to provide a detailed description of every feature in gem5.
After reading this document, you should feel comfortable using gem5 in the classroom and for computer architecture research.
Additionally, you should be able to modify and extend gem5 and then contribute your improvements to the main gem5 repository.

This document is colored by my personal experiences with gem5 over the past six years as a graduate student at the University of Wisconsin-Madison.
The examples presented are just one way to do it.
Unlike Python, whose mantra is "There should be one-- and preferably only one --obvious way to do it." (from The Zen of Python. See ``import this``), in gem5 there are a number of different ways to accomplish the same thing.
Thus, many of the examples presented in this book are my opinion of the best way to do things.

One important lesson I have learned (the hard way) is when using complex tools like gem5, it is important to actually understand how it works before using it.

.. todo::

  	Finish the previous paragraph about how it is a good idea to understand what your tools are actually doing.

.. todo::

	should add a list of terms.
	Things like "simulated system" vs "host system", etc.


You can find the source for this book on github at https://github.com/powerjg/learning_gem5.