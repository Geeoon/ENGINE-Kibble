# ENGINE Capstone
# Blank container to serve as the monitoring computer.  Starts and does nothing

FROM redhat/ubi8:latest

# install tools
WORKDIR /tmp
# ping
RUN dnf install -y iputils python3
# mongodb shell install
ADD https://repo.mongodb.org/yum/redhat/8Server/mongodb-org/8.2/x86_64/RPMS/mongodb-mongosh-2.6.0.x86_64.rpm .
RUN dnf install -y mongodb-mongosh-2.6.0.x86_64.rpm && rm mongodb-mongosh-2.6.0.x86_64.rpm

# add source code to home directory
WORKDIR /home
COPY ./src ./src

# read /dev/null forever, busy loop to prevent container from automatically
# stopping itself
# probably should replace this with the program start script
CMD ["tail", "-f", "/dev/null"]
