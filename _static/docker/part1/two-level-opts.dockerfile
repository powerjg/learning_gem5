FROM learning-gem5/base

MAINTAINER Jason Lowe-Power <jason@lowepower.com>

WORKDIR /usr/local/src/gem5

RUN mkdir -p /usr/local/src/gem5/configs/learning/part1/

# Copy script
COPY _static/scripts/part1/caches_opts.py \
     _static/scripts/part1/two_level_opts.py \
     /usr/local/src/gem5/configs/learning/part1/

# Run with the script
CMD ["build/X86/gem5.opt", \
     "configs/learning/part1/two_level_opts.py", \
     "--l2_size=1MB", "--l1d_size=128kB"]
