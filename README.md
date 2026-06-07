# ENGINE Kibble project
## Main Monitor Installation
### Linux
[TODO]
### Windows
[TODO]

## Configuration
### Database
[TODO]
### Command-Line Arguments
```
usage: main.py [-h] [--low-thresh LOW_THRESH] [--medium-thresh MEDIUM_THRESH] [--high-thresh HIGH_THRESH] [--monitor-id MONITOR_ID] [--community-string COMMUNITY_STRING] [--device-timeout DEVICE_TIMEOUT] [--scan-period SCAN_PERIOD] [--threads THREADS]
               [--sender-email SENDER_EMAIL] [--receiver-email RECEIVER_EMAIL] [--mongo-host MONGO_HOST] [--mongo-port MONGO_PORT] [--mongo-user MONGO_USER] [--mongo-pass MONGO_PASS]

options:
  -h, --help            show this help message and exit
  --low-thresh LOW_THRESH
  --medium-thresh MEDIUM_THRESH
  --high-thresh HIGH_THRESH
  --monitor-id MONITOR_ID
                        Unique integer ID for this monitoring node (lowest ID wins leader election)
  --community-string COMMUNITY_STRING
                        Community string for SNMP monitor
  --device-timeout DEVICE_TIMEOUT
                        Timeout for the device
  --scan-period SCAN_PERIOD
                        How often to scan the network. Should be at least double the device timeout
  --threads THREADS     The number of threads to launch to do simultaneous device scans. Should scale with the number of devices.
  --sender-email SENDER_EMAIL
                        The email account to send alerts from
  --receiver-email RECEIVER_EMAIL
                        The email accoutn to send alerts to
  --mongo-host MONGO_HOST
                        The MongoDB hostname
  --mongo-port MONGO_PORT
                        The MongoDB port
  --mongo-user MONGO_USER
                        The MongoDB username
  --mongo-pass MONGO_PASS
                        The MongoDB password
```


## Custom Daemon Installation
### Linux
[TODO]
### Windows
[TODO]
