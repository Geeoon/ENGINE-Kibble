# ENGINE Capstone
# Blank container to serve as the monitoring computer.  Starts and does nothing

FROM redhat/ubi8:8.10-1770223225

# install tools
WORKDIR /tmp

# ping and python
RUN dnf install -y iputils python3.12

# mongodb shell install
RUN arch=$(uname -m) && dnf install -y https://repo.mongodb.org/yum/redhat/8Server/mongodb-org/8.2/${arch}/RPMS/mongodb-mongosh-2.6.0.${arch}.rpm
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


