# Blank container to serve as the monitoring computer.  Starts and does nothing

FROM redhat/ubi8:8.10

# install tools
WORKDIR /tmp

# netcat is nice for debugging
RUN dnf install -y nmap-ncat

# ping and python
RUN dnf install -y iputils python3.12

# tmux is nice to have
# RUN dnf install -y https://mirror.ghettoforge.net/distributions/gf/el/8/testing/x86_64/tmux-3.2a-3.gf.el8.x86_64.rpm

# mongodb shell install
# mongodb shell install - need newer Node.js for mongosh
# mongodb shell install - download binary directly (ARM64)
RUN dnf install -y curl tar gzip && \
    curl -O https://downloads.mongodb.com/compass/mongosh-2.6.0-linux-arm64.tgz && \
    tar -xzf mongosh-2.6.0-linux-arm64.tgz && \
    mv mongosh-2.6.0-linux-arm64/bin/mongosh /usr/local/bin/ && \
    rm -rf mongosh-2.6.0-linux-arm64 mongosh-2.6.0-linux-arm64.tgz && \
    dnf clean all

# install python dependencies
RUN python3 -m ensurepip --upgrade
COPY ./src/Kibble/requirements.txt .
RUN python3 -m pip install -r requirements.txt

# add source code to home directory
COPY ./src .

# read /dev/null forever, busy loop to prevent container from automatically
# stopping itself
# probably should replace this with the program start script
CMD ["tail", "-f", "/dev/null"]


