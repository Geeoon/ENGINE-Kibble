# ENGINE Capstone
# Blank container to serve as the monitoring computer.  Starts and does nothing
# TODO: modify to contain the main app

FROM redhat/ubi8:latest

WORKDIR /tmp
# mongodb shell install
RUN dnf install -y wget iputils
RUN wget https://repo.mongodb.org/yum/redhat/8Server/mongodb-org/8.2/x86_64/RPMS/mongodb-mongosh-2.6.0.x86_64.rpm
RUN dnf install -y mongodb-mongosh-2.6.0.x86_64.rpm && rm mongodb-mongosh-2.6.0.x86_64.rpm

# read /dev/null forever, busy loop to prevent container from automatically
# stopping itself
# probably should replace this with the program start script
CMD ["tail", "-f", "/dev/null"]
