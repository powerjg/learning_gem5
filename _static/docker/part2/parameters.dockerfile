FROM learning-gem5/base

MAINTAINER Jason Lowe-Power <jason@lowepower.com>

WORKDIR /usr/local/src/gem5

RUN mkdir -p /usr/local/src/gem5/configs/learning/part2/ && \
    mkdir -p /usr/local/src/gem5/src/learning/

# Copy script
COPY _static/scripts/part2/parameters/hello_goodbye.py \
     /usr/local/src/gem5/configs/learning/part2/

# Copy code
COPY _static/scripts/part2/parameters/HelloObject.py \
     _static/scripts/part2/parameters/SConscript \
     _static/scripts/part2/parameters/hello_object.cc \
     _static/scripts/part2/parameters/hello_object.hh \
     _static/scripts/part2/parameters/goodbye_object.cc \
     _static/scripts/part2/parameters/goodbye_object.hh \
     /usr/local/src/gem5/src/learning_gem5/

RUN scons build/X86/gem5.opt -j5

# Run with the script
CMD ["build/X86/gem5.opt", \
     "--debug-flags=Hello", \
     "configs/learning/part2/hello_goodbye.py"]
