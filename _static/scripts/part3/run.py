import sys

import m5
from m5.objects import *

sys.path.append('configs/common/') # For the next line...
import SimpleOpts

from system import MySystem

SimpleOpts.add_option("--script", default='',
                      help="Script to execute in the simulated system")

if __name__ == "__m5_main__":
    (opts, args) = SimpleOpts.parse_args()

    # create the system we are going to simulate
    system = MySystem(opts)

    # Read in the script file passed in via an option.
    # This file gets read and executed by the simulated system after boot.
    # Note: The disk image needs to be configured to do this.
    system.readfile = opts.script

    # set up the root SimObject and start the simulation
    root = Root(full_system = True, system = system)

    # instantiate all of the objects we've created above
    m5.instantiate()

    # Keep running until we are done.
    print "Running the simulation"
    exit_event = m5.simulate()
    print 'Exiting @ tick %i because %s' % (m5.curTick(),
                                            exit_event.getCause())
