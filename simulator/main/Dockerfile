# ENGINE Capstone
# Blank container to serve as the monitoring computer.  Starts and does nothing
# TODO: modify to contain the main app

FROM alpine:latest
WORKDIR /

# read /dev/null forever, busy loop to prevent container from automatically
# stopping itself
# probably should replace this with the program start script
CMD ["tail", "-f", "/dev/null"]
