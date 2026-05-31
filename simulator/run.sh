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
    echo "  -h, --help      display this help message and exit"
    echo "  -n, --no-build  do not build the image(s)"
    echo "  COMPUTERS       the number of secondary computers to start must be a"
    echo "                  positive integer.  Defaults to $DEFAULT_NUM_COMPUTERS"
}

num_computers=$DEFAULT_NUM_COMPUTERS
build=1
# parse command line arguments
while [ $# -ge 1 ]; do
    if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        print_help
        exit 0
    elif [ "$1" == "--no-build" ] || [ "$1" == "-n" ]; then
        build=2
        shift
        continue
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
    shift
done

# create db dir with correct perms
mkdir -p db
sudo chmod 777 db

if [ "$build" -ne 2 ]; then
    docker compose build
fi

# stop if there is an error building
if [ $? -ne 0 ]; then
    echo Unable to build containers
    exit 1
fi

docker compose up --scale secondary=$num_computers --scale scpi=$num_computers -d --scale daemon=$num_computers
# command below will show IP addresses of running containers, useful for ping
docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q)
docker exec -it $MAIN_CONTAINER_NAME bash
docker compose down -v

# for future reference:
# kill containers using: docker kill <container name>
# ping using: ping <ip address>
# prune docker: docker system prune --volumes
# connect to db using `mongosh $CONN_STR`
# use kibble 
# db['events'].deleteMany({})
# db['events'].find({})
# add artificial delay with `tc qdisc add dev eth0 root netem delay 500ms`
