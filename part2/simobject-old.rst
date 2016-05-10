
:authors: Jason Power

.. _simple-simobject-chapter:

------------------------------------------
Creating your first SimObject
------------------------------------------

.. Note:: This chapter is out of date! There have been significant changes in the cache models which renders the below code wrong. This chapter has been mostly subsumed by :ref:`hello-simobject-chapter`.

In this chapter we will walk though how to create a simple SimObject.
As an example, we are going to create a new cache replacement policy, specifically, NMRU, not most recently used.
After this chapter you should be able to create new SimObjects, instantiate them in configuration files, and run simulations with your new objects.

Step 1: Create a new patch for your changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first step when adding a new feature or modifying something in gem5, is to create a new patch to store your changes.
Details on Mercurial patch queues can be found in the `Mercurial book`_.

.. _Mercurial book: http://hgbook.red-bean.com/read/managing-change-with-mercurial-queues.html

.. code-block:: sh

	hg qnew nmru-patch -m "Mem: adds a new cache tag for NMRU replacement"

Step 2: Create a Python class for your new SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each SimObject has a Python class which is associated with it.
This Python class describes the parameters of your SimObject that can be controlled from the Python configuration files.
For our NMRU cache tags, we are just going to inherit all of the parameters from the BaseSetAssoc tags.
Thus, we simply need to declare a new class for our SimObject and set it's name and the C++ header that will define the C++ class for the SimObject.

We can create a file, NMRU.py, in ``src/mem/cache/tags/``

.. code-block:: python

	from Tags import BaseSetAssoc

	class NMRU(BaseSetAssoc):
	    type = 'NMRU'
	    cxx_header = "mem/cache/tags/nmru.hh"


Step 3: Implement your SimObject in C++
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we need to create ``nmru.hh`` and ``nmru.cc`` which will implement our NMRU replacement policy.
Importantly, every SimObject must inherit from the C++ SimObject class.
Most of the time, your SimObject's parent will be a subclass of SimObject, not SimObject itself.

For ``nmru.hh``, we can mostly copy the code from other similar replacement policies, say LRU.
In the Python file for NMRU, we used BaseSetAssoc as our parent, which we will mirror in C++.
Below is the contents of ``nmru.hh``.

.. code-block:: c++

	#ifndef __MEM_CACHE_TAGS_NMRU_HH__
	#define __MEM_CACHE_TAGS_NMRU_HH__

	#include "mem/cache/tags/base_set_assoc.hh"
	#include "params/NMRU.hh"

	class NMRU : public BaseSetAssoc
	{
	  public:
	    /** Convenience typedef. */
	    typedef NMRUParams Params;

	    /**
	     * Construct and initialize this tag store.
	     */
	    NMRU(const Params *p);

	    /**
	     * Destructor
	     */
	    ~NMRU() {}

	    /**
	     * Required functions for this subclass to implement
	     */
	    BlkType* accessBlock(Addr addr, bool is_secure, Cycles &lat,
	                         int context_src);
	    BlkType* findVictim(Addr addr) const;
	    void insertBlock(PacketPtr pkt, BlkType *blk);
	    void invalidate(BlkType *blk);
	};

	#endif // __MEM_CACHE_TAGS_NMRU_HH__

Again, for the implementation we can use similar code to LRU and Random replacement policies.
The basic implementation is that we track the most recently used block by moving the last accessed block to the head of the MRU queue.
On a replacement, we select a random block that is not the most recently used block. 
Below is the implementation in ``nrmu.cc``:

.. todo::

	Explain params etc.
	Overall, the tag store is not a great example for this, but we'll leave it for now.

.. code-block:: c++

	/**
	 * @file
	 * Definitions of a NMRU tag store.
	 */

	#include "mem/cache/tags/nmru.hh"

	#include "base/random.hh"
	#include "debug/CacheRepl.hh"
	#include "mem/cache/base.hh"

	NMRU::NMRU(const Params *p)
	    : BaseSetAssoc(p)
	{
	}

	BaseSetAssoc::BlkType*
	NMRU::accessBlock(Addr addr, bool is_secure, Cycles &lat, int master_id)
	{
	    // Accesses are based on parent class, no need to do anything special
	    BlkType *blk = BaseSetAssoc::accessBlock(addr, is_secure, lat, master_id);

	    if (blk != NULL) {
	        // move this block to head of the MRU list
	        sets[blk->set].moveToHead(blk);
	        DPRINTF(CacheRepl, "set %x: moving blk %x (%s) to MRU\n",
	                blk->set, regenerateBlkAddr(blk->tag, blk->set),
	                is_secure ? "s" : "ns");
	    }

	    return blk;
	}

	BaseSetAssoc::BlkType*
	NMRU::findVictim(Addr addr) const
	{
	    BlkType *blk = BaseSetAssoc::findVictim(addr);

	    // if all blocks are valid, pick a replacement that is not MRU at random
	    if (blk->isValid()) {
	        // find a random index within the bounds of the set
	        int idx = random_mt.random<int>(1, assoc - 1);
	        assert(idx < assoc);
	        assert(idx >= 0);
	        blk = sets[extractSet(addr)].blks[idx];

	        DPRINTF(CacheRepl, "set %x: selecting blk %x for replacement\n",
	                blk->set, regenerateBlkAddr(blk->tag, blk->set));
	    }

	    return blk;
	}

	void
	NMRU::insertBlock(PacketPtr pkt, BlkType *blk)
	{
	    BaseSetAssoc::insertBlock(pkt, blk);

	    int set = extractSet(pkt->getAddr());
	    sets[set].moveToHead(blk);
	}

	void
	NMRU::invalidate(BlkType *blk)
	{
	    BaseSetAssoc::invalidate(blk);

	    // should be evicted before valid blocks
	    int set = blk->set;
	    sets[set].moveToTail(blk);
	}

	NMRU*
	NMRUParams::create()
	{
	    return new NMRU(this);
	}

Step 4: Register the SimObject and C++ file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each SimObject must be registered with SCons so that its Params object and Python wrapper is created.
Additionally, we also have to tell SCons which C++ files to compile.
To do this, modify the ``SConscipt`` file in the directory that your SimObject is in.
For each SimObject, add a call to ``SimObject`` and for each source file add a call to ``Source``.
In this example, you need to add the following to src/mem/cache/tags/SConscript:

.. code-block:: python

	SimObject('NMRU.py')

	Source('nmru.cc')

Step 5: Other things for tags, because their weird
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Tags in the gem5 classic cache are a little weird with how we need to create them.
Usually, you specify a ``create`` function like below:

.. code-block:: c++

	NMRUParams::create()
	{
	    return new NMRU(this);
	}

However, since the cache tags are tied very closely to the cache, instead you need to modify ``src/mem/cache/base.cc`` at the bottom of the file:

.. code-block:: c++

	BaseCache *
	BaseCacheParams::create()
	{
	    unsigned numSets = size / (assoc * system->cacheLineSize());

	    assert(tags);

	    if (dynamic_cast<FALRU*>(tags)) {
	        if (numSets != 1)
	            fatal("Got FALRU tags with more than one set\n");
	        return new Cache<FALRU>(this);
	    } else if (dynamic_cast<LRU*>(tags)) {
	        if (numSets == 1)
	            warn("Consider using FALRU tags for a fully associative cache\n");
	        return new Cache<LRU>(this);
	    } else if (dynamic_cast<RandomRepl*>(tags)) {
	        return new Cache<RandomRepl>(this);
	    } else if (dynamic_cast<NMRU*>(tags)) {
	        return new Cache<NMRU>(this);
	    } else {
	        fatal("No suitable tags selected\n");
	    }
	}

And modify ``cache.cc`` by adding a Cache templatized with NMRU:

.. code-block:: c++

	template class Cache<NMRU>;


Now, you should be able to compile gem5 and use your new cache tag!

Step 6: Modify the config scripts to use your new SimObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, you need to create your SimObject in the config scripts.
If you're using the simple config scripts created in previous chapters, you can simply change the L1D cache as below:

.. code-block:: python

	class L1DCache(L1Cache):
	    """Simple L1 data cache with default values"""

	    # Set the default size
	    size = '32kB'
	    tags = NMRU()

The changeset to add all of the NMRU code can be found :download:`here <../_static/patches/nmru-tags>`.
You can apply this patch by using ``hg qimport``.