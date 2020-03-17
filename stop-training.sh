#!/usr/bin/env bash

docker-compose -f ./docker-compose.yml down

docker stop $(docker ps | awk ' /sagemaker/ { print $1 }')
docker rm $(docker ps -a | awk ' /sagemaker/ { print $1 }')

source ./config.env
if [ "$ENABLE_ROS_BROWSER_WINDOW" = true ] ; then
    wmctrl -c kvs_stream
fi

