# ENGINE Kibble project
Kibble probes devices with different protocols, stores status events in MongoDB, detects latency thresholds, and raises alerts.

## Prerequisites

- **Python 3.12+**
- **Docker Desktop** (for the simulated environment and local MongoDB)
- **sudo** on Linux/macOS

Optional:

- **MongoDB Compass** - GUI for browsing the `kibble` database
- **mongosh** - MongoDB shell (included in the main simulator container)

## Quick start

```bash
git clone https://github.com/Geeoon/ENGINE-Kibble.git
cd ENGINE-Kibble

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r src/Kibble/requirements.txt

cd simulator
./run.sh
```

Inside the main container shell:

```bash
cd /tmp
./start.sh
```

In another terminal on your host, add a device:

```bash
cd ENGINE-Kibble/src
source ../.venv/bin/activate
python manage_devices.py add --asset-tag 1001 --type icmp --hostname simulator-secondary-1
```

Open MongoDB Compass with:

```
mongodb://root:password@localhost:27017
```
In MongoDB Compass devices and configurations can also be manually added/removed.

## Main Monitor Installation
### Linux

1. **Clone the repository**

   ```bash
   git clone https://github.com/Geeoon/ENGINE-Kibble.git
   cd ENGINE-Kibble
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r src/Kibble/requirements.txt
   ```
3. **Configure email alerts (optional)**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your Gmail app password:

   ```
   EMAIL_PASSWD=your_app_password_here
   ```

   Screen/Terminal alerts work without this step.

4. **Start MongoDB**

   Either run the full simulator:

   ```bash
   cd simulator
   ./run.sh
   ```

   Or start only the database container:

   ```bash
   cd simulator
   mkdir -p db && sudo chmod 777 db
   docker compose up database -d
   ```
5. **Run the monitor**

   **Inside the simulator container:**

   ```bash
   cd /tmp
   ./start.sh
   ```
  **On the host machine:**

   `src/main.py` defaults to `database.internal`. For host-side runs, either add `127.0.0.1 database.internal` to `/etc/hosts`, or change `mongo_host` in `src/main.py` to `'localhost'`.

   ```bash
   cd src
   source ../.venv/bin/activate
   ./start.sh
   ```

   `start.sh` loads `../.env` and runs `main.py` with `sudo` when available (needed for ICMP/Scapy).

   Press `Ctrl+C` to stop the monitor. Logs are written to `kibble.log` and `kibble_status.log`.

### Windows
1. **Clone the repository**

   ```powershell
   git clone https://github.com/Geeoon/ENGINE-Kibble.git
   cd ENGINE-Kibble
   ```

2. **Create a virtual environment and install dependencies**

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r src/Kibble/requirements.txt
   ```
3. **Configure email alerts (optional)**

   ```powershell
   copy .env.example .env
   ```

   Edit `.env` and set `EMAIL_PASSWD` to your Gmail app password.

4. **Start MongoDB with Docker Desktop**

   ```powershell
   cd simulator
   mkdir db
   docker compose up database -d
   ```

   To run the full simulator without bash, build and start manually:

   ```powershell
   docker compose build
   docker compose up --scale secondary=5 --scale scpi=5 -d
   docker exec -it kibble-main-container bash
   ```
5. **Run the monitor**

   **Inside the simulator container:**

   ```bash
   cd /tmp
   python main.py
   ```

   **On the host machine:**

   Change `mongo_host` in `src/main.py` to `'localhost'`, then:

   ```powershell
   cd src
   ..\.venv\Scripts\activate
   python main.py
   ```
## Simulated environment (for development)

The `simulator/` directory runs a full test network in Docker: a monitoring host, MongoDB, secondary machines, and SCPI instrument simulators.
### Start the stack

```bash
cd simulator
./run.sh          # starts 5 secondary + 5 SCPI devices (default)
./run.sh 3        # start 3 of each instead
```

`run.sh` will:

1. Build all container images
2. Start MongoDB and simulated devices
3. Open a shell inside `kibble-main-container`
4. Tear down the stack when you exit that shell (`docker compose down -v`)

To keep containers running in the background:

```bash
cd simulator
mkdir -p db && sudo chmod 777 db
docker compose build
docker compose up --scale secondary=5 --scale scpi=5 -d
```

The monitor connects to MongoDB at `database.internal:27017`, seeds test devices, and begins probing.

## Configuration
### Database
Kibble stores device configuration and monitoring events in MongoDB.

| Setting  | Simulator (inside Docker) | Host machine / Compass |
|----------|---------------------------|-------------------------|
| Host     | `database.internal`       | `localhost`             |
| Port     | `27017`                   | `27017`                 |
| Username | `root`                    | `root`                  |
| Password | `password`                | `password`              |
| Database | `kibble`                  | `kibble`                |

Connection string for Compass or `mongosh`:

```
mongodb://root:password@localhost:27017
```

> These credentials are simulator defaults for local development only.

Start the database container:

```bash
cd simulator && docker compose up database -d
```

#### Device configuration tool (`manage_devices.py`)

Use `src/manage_devices.py` to add or remove monitored devices in MongoDB from the terminal. The monitor reads device configuration from the database on each scan cycle.
> **MongoDB must be running** before using this tool.

**How device data is stored:**

| What you set in the CLI | Where it goes in MongoDB |
|-------------------------|--------------------------|
| `--asset-tag`           | `devices.asset_tag` |
| `--type`                | `devices.device_type_id` → `device_types` |
| `--ip`, `--hostname`, `--mac` | `interface_configurations` and `device_configurations` |

**Workflow:**

1. Start MongoDB
2. Add devices with `manage_devices.py`
3. Verify in Compass (see below)
4. Start the monitor
5. Watch `timeseries_events` for probe results

**Add a device**

Each device needs a unique `--asset-tag`, a device type (`--type` or `--type-name` with `--protocols`), and at least one of `--ip` or `--hostname`.

| `--type`  | Protocols 
|-----------|-----------
| `icmp`    | ICMP      
| `scpi`    | SCPI      
| `snmp`    | SNMP      
| `daemon`  | Daemon    

Examples:

```bash
# Ping a device by IP
python manage_devices.py add --asset-tag 1001 --type icmp --ip 192.168.1.10

# Ping a device by hostname
python manage_devices.py add --asset-tag 1002 --type icmp --hostname my-server.local

# Add an SCPI instrument in the simulator
python manage_devices.py add --asset-tag 2001 --type scpi --hostname simulator-scpi-1

# Custom device type
python manage_devices.py add --asset-tag 3001 --type-name "custom probe" --protocols ICMP --ip 10.0.0.5
```

Inside the main simulator container:

```bash
python manage_devices.py --mongo-host database.internal add \
  --asset-tag 1001 --type icmp --hostname simulator-secondary-1
```

Re-running `add` with the same `--asset-tag` updates the device. A new configuration snapshot is recorded only when IP, hostname, or MAC changes.

**Remove a device**

```bash
python manage_devices.py remove --asset-tag 1001
```

This deletes the device and its associated configuration records. Historical `timeseries_events` are not deleted.

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
