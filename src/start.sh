#!/usr/bin/env bash
# script used to start the main.py file as sudo because Scapy requires sudo

cd "$(dirname "$0")" || exit

# Source the .env file from the parent directory
if [ -f "../.env" ]; then
    set -a
    source "../.env"
    set +a
fi

# check if sudo exists (doesn't exist on the container)
which sudo &> /dev/null

if [ $? -eq 0 ]; then
    sudo --preserve-env=KIBBLE_MODE,DOCKER_SECONDARY_COUNT,HARDWARE_IPS,EMAIL_PASSWD $(which python3) ./main.py
else
    $(which python3) ./main.py
fi
