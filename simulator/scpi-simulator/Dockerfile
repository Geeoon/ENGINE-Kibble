# ENGINE Capstone
# Starts the SCPI simulator as a power supply

FROM alpine:latest
WORKDIR /scpi-sim

# add python3
RUN apk add python3 py3-pip

COPY . .

RUN python3 -m pip install --break-system-packages -r requirements.txt

CMD ["python3", "-m", "SCPISimulator", "-d", "power_supply", "-c", "example.toml", "-a", "0.0.0.0"]
