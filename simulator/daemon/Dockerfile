# ENGINE Capstone
# Daemon container.

FROM alpine:latest
WORKDIR /edge_node

RUN apk add python3 py3-pip

COPY ./edge_node .

RUN python3 -m pip install --break-system-packages -r requirements.txt

CMD ["python3", "main.py"]

# for debugging
# CMD ["tail", "-f", "/dev/null"]
