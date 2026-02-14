# ENGINE Capstone
# Blank container to serve as the monitoring computer.  Starts and does nothing

FROM redhat/ubi8:8.10-1770223225

# install tools
WORKDIR /tmp

# ping and python
RUN dnf install -y iputils python3.12

# tmux is nice to have
RUN dnf install -y https://mirror.ghettoforge.net/distributions/gf/el/8/testing/x86_64/tmux-3.2a-3.gf.el8.x86_64.rpm

# mongodb shell install
RUN dnf install -y https://repo.mongodb.org/yum/redhat/8Server/mongodb-org/8.2/x86_64/RPMS/mongodb-mongosh-2.6.0.x86_64.rpm
WORKDIR /root/src

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

