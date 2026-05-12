#!/usr/bin/env bash
# Installs Kibble Telemetry collection on linux

cd "$(dirname "$0")" || exit

# create kibble system user if it doesn't exist
id -u kibble &> /dev/null
if [ $? -ne 0 ]; then
    useradd --system --no-create-home --shell /sbin/nologin kibble
fi

# create log and app directories
mkdir -p /var/log/kibble
chown kibble:kibble /var/log/kibble
mkdir -p /opt/kibble/edge_agent

# install dependencies
$(which python3) -m pip install -r requirements.txt

# copy the collector script and modules
cp ../telemetry_collector.py /opt/kibble/edge_agent/telemetry_collector.py
cp -r ../collectors/ /opt/kibble/edge_agent/collectors/

# install and enable the systemd service
cp kibble-telemetry.service /etc/systemd/system/kibble-telemetry.service
systemctl daemon-reload
systemctl enable kibble-telemetry.service
systemctl start kibble-telemetry.service

echo "Kibble Telemetry Collection Installation Complete: Check status with: systemctl status kibble-telemetry.service"
