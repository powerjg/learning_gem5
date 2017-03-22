FROM learning-gem5/base

MAINTAINER Jason Lowe-Power <jason@lowepower.com>



WORKDIR /usr/local/src/gem5


# Run with no script. Default test with --help
CMD ["build/X86/gem5.opt", \
     "--help"]
