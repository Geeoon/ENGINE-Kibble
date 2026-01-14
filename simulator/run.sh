#!/usr/bin/env bash
# start script for the simulated environment
# add the number of secondary "computers" to start as the first argument

# CONSTANTS
readonly DEFAULT_NUM_COMPUTERS=5
readonly MAIN_CONTAINER_NAME="kibble-main-container"

# FUNCTIONS
print_help() {
    echo "Usage: $0 [OPTION]... [COMPUTERS]"
    echo "Starts the simulated environment and enters the main PC"
    echo ""
    echo "Options"
    echo "  -h, --help    display this help message and exit"
    echo "  COMPUTERS     the number of secondary computers to start must be a"
    echo "                positive integer.  Defaults to $DEFAULT_NUM_COMPUTERS"
}

num_computers=$DEFAULT_NUM_COMPUTERS

# parse command line arguments
if [ $# -ge 1 ]; then
    if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        print_help
        exit 0
    elif ! [[ $1 =~ ^-?[0-9]+$ ]]; then
        echo "Number of computers must be a number"
        echo "Try '$0 --help' for more information."
        exit 1
    elif ! [ $1 -gt 0 ]; then
        echo "Number of computers must a positive number"
        echo "Try '$0 --help' for more information."
        exit 1
    fi
    num_computers=$1
fi

docker compose build
docker compose up --scale secondary=$num_computers -d
# command below will show IP addresses of running containers, useful for ping
docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q)
docker exec -it $MAIN_CONTAINER_NAME sh
docker compose down

# for future reference:
# kill containers using: docker kill <container name>
# ping using: ping <ip address>
