# ENGINE Capstone
# Blank container to serve as a test machine.  Starts and does nothing.

FROM alpine:latest
WORKDIR /

# add traffic control for tests
RUN apk add iproute2-tc

# read /dev/null forever, busy loop to prevent container from automatically stopping itself
CMD ["tail", "-f", "/dev/null"]
