#!/usr/bin/env bash
# start script for the simulated environment
set -e

# CONSTANTS
readonly DEFAULT_NUM_COMPUTERS=5
readonly MAIN_CONTAINER_NAME="kibble-main-container"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Flag to control cleaning 
cleanup_needed=false

# FUNCTIONS

# Flag to control cleanup
cleanup_needed=false

cleanup() {
    if $cleanup_needed; then
        (cd "$SCRIPT_DIR" && docker compose down -v >/dev/null 2>&1 || true)
    fi
}
trap cleanup EXIT

print_help() {
    echo "Usage: $0 [OPTION]..."
    echo "Starts the demo environment based on .env configuration"
    echo ""
    echo "Options"
    echo "  -h, --help    display this help message and exit"
    echo ""
    echo "Environment variables (.env)"
    echo "  KIBBLE_MODE             docker | hardware | hybrid (default: docker)"
    echo "  DOCKER_SECONDARY_COUNT  positive integer (default: $DEFAULT_NUM_COMPUTERS)"
    echo "  HARDWARE_IPS             comma-separated IPs (default: empty)"
}


# parse command line options
if [ $# -gt 0 ]; then
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        print_help
        exit 0
    else
        echo "Unknown option: $1"
        echo "Try '$0 --help' for more information."
        exit 1
    fi
fi

# load environment
if [ -f "$REPO_DIR/.env" ]; then
    set -a
    source "$REPO_DIR/.env"
    set +a
fi

# determine mode
mode="$KIBBLE_MODE"

# convert mode to lowercase
mode=$(echo "$mode" | tr '[:upper:]' '[:lower:]')

# determine number of computers
num_computers="$DOCKER_SECONDARY_COUNT"
if [ -z "$num_computers" ]; then
    num_computers="$DEFAULT_NUM_COMPUTERS"
fi

hardware_ips="$HARDWARE_IPS"

# create db dir with correct perms
mkdir -p "$SCRIPT_DIR/db"
chmod 777 "$SCRIPT_DIR/db"

cd "$SCRIPT_DIR"

# docker or hybrid mode
if [ "$mode" = "docker" ] || [ "$mode" = "hybrid" ]; then
    cleanup_needed=true

    docker compose build
    docker compose up --scale secondary="$num_computers" -d

    # show container IPs
    docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q)

    docker exec -it \
        -e KIBBLE_MODE="$mode" \
        -e DOCKER_SECONDARY_COUNT="$num_computers" \
        -e HARDWARE_IPS="$hardware_ips" \
        -e EMAIL_PASSWD="$EMAIL_PASSWD" \
        "$MAIN_CONTAINER_NAME" bash

# hardware mode
elif [ "$mode" = "hardware" ]; then
    cleanup_needed=true

    docker compose up -d database

    export KIBBLE_MODE="hardware"
    export DOCKER_SECONDARY_COUNT="$num_computers"
    export HARDWARE_IPS="$hardware_ips"


    "$REPO_DIR/src/start.sh"

else
    echo "Invalid KIBBLE_MODE: $mode"
    exit 1
fi

# for future reference:
# kill containers using: docker kill <container name>
# ping using: ping <ip address>
# prune docker: docker system prune --volumes
# connect to db using `mongosh $CONN_STR`
# use kibble 
# db['events'].deleteMany({})
# db['events'].find({})
# add artificial delay with `tc qdisc add dev eth0 root netem delay 500ms`