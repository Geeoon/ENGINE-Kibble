#!/usr/bin/env bash
# Installs Kibble Telemetry collection on linux
set -euo pipefail

# ensure ran as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be ran as root"
    exit 1
fi

cd "$(dirname "$0")" || exit 1

# create kibble system user if it doesn't exist

if ! id -u kibble &> /dev/null; then
    echo "Creating Kibble user"
    useradd --system --no-create-home --shell /sbin/nologin kibble
fi

echo "Creating log and app directories"
# create log and app directories
mkdir -p /var/log/kibble
chown kibble:kibble /var/log/kibble
mkdir -p /opt/kibble/edge_agent
# create venv
python3 -m venv /opt/kibble/edge_agent/.venv
chown -R kibble:kibble /opt/kibble

echo "Installing dependencies"
# install dependencies
/opt/kibble/edge_agent/.venv/bin/python3 -m pip install -r ./requirements.txt

# copy the collector script and modules
cp -r ../KibbleDaemon /opt/kibble/edge_agent
cp ../main.py /opt/kibble/edge_agent

# install and enable the systemd service
cp kibble-telemetry.service /etc/systemd/system/kibble-telemetry.service
systemctl daemon-reload
systemctl enable kibble-telemetry.service
systemctl start kibble-telemetry.service

echo "Kibble Telemetry Collection Installation Complete: Check status with: systemctl status kibble-telemetry.service"
