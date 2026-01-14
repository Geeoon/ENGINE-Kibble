# ENGINE Capstone
# Blank container to serve as a test machine.  Starts and does nothing.

FROM alpine:latest
WORKDIR /

# read /dev/null forever, busy loop to prevent container from automatically stopping itself
CMD ["tail", "-f", "/dev/null"]
