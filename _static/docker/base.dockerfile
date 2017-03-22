FROM ubuntu:16.04

MAINTAINER Jason Lowe-Power <jason@lowepower.com>


# Install all of gem5's dependencies
RUN apt-get update -y && apt-get install -y \
        build-essential \
        python-dev \
        scons \
        swig \
        zlib1g-dev \
        m4 \
        libprotobuf-dev \
        python-protobuf \
        protobuf-compiler \
        libgoogle-perftools-dev
RUN apt-get install --no-install-recommends -y mercurial

# Download the gem5 source
WORKDIR /usr/local/src
RUN hg clone http://repo.gem5.org/gem5

# Build gem5
WORKDIR /usr/local/src/gem5
RUN scons build/X86/gem5.opt -j5
