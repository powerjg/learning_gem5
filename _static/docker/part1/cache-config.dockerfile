FROM learning-gem5/base

MAINTAINER Jason Lowe-Power <jason@lowepower.com>

WORKDIR /usr/local/src/gem5

RUN mkdir -p /usr/local/src/gem5/configs/learning/part1/

# Copy script
COPY _static/scripts/part1/caches.py \
     _static/scripts/part1/two_level.py \
     /usr/local/src/gem5/configs/learning/part1/

# Run with the script
CMD ["build/X86/gem5.opt", \
     "configs/learning/part1/two_level.py"]
