FROM learning-gem5/base

MAINTAINER Jason Lowe-Power <jason@lowepower.com>

WORKDIR /usr/local/src/gem5

RUN mkdir -p /usr/local/src/gem5/configs/learning/part2/ && \
    mkdir -p /usr/local/src/gem5/src/learning/

# Copy script
COPY _static/scripts/part2/helloobject/run_hello.py \
     /usr/local/src/gem5/configs/learning/part2/

# Copy code
COPY _static/scripts/part2/helloobject/HelloObject.py \
     _static/scripts/part2/debugging/SConscript \
     _static/scripts/part2/events/hello_object.cc \
     _static/scripts/part2/events/hello_object.hh \
     /usr/local/src/gem5/src/learning_gem5/

RUN scons build/X86/gem5.opt -j5

# Run with the script
CMD ["build/X86/gem5.opt", \
     "--debug-flags=Hello", \
     "configs/learning/part2/run_hello.py"]
