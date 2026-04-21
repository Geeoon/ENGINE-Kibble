# ENGINE Capstone
# Daemon container.

FROM alpine:latest
WORKDIR /

# add traffic control for tests
RUN apk add iproute2-tc

COPY ./edge_node .

# read /dev/null forever, busy loop to prevent container from automatically stopping itself
CMD ["tail", "-f", "/dev/null"]
