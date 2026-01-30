#!/usr/bin/env bash
# script used to start the main.py file as sudo because Scapy requires sudo

# check if sudo exists (doesn't exist on the container)
which sudo &> /dev/null

if [ $? -eq 0 ]; then
    sudo $(which python3) ./main.py
else
    $(which python3) ./main.py
fi
