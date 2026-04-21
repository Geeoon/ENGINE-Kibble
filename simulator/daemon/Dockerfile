# ENGINE Capstone
# Daemon container.

FROM alpine:latest
WORKDIR /edge_node

RUN apk add python3 py3-pip

COPY ./edge_node .

RUN python3 -m pip install --break-system-packages -r requirements.txt

# read /dev/null forever, busy loop to prevent container from automatically stopping itself
CMD ["python3", "main.py"]
