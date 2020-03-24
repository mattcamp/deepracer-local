#!/usr/bin/env bash

docker-compose -f ./docker-compose.yml down

docker stop $(docker ps | awk ' /sagemaker/ { print $1 }')
docker rm $(docker ps -a | awk ' /sagemaker/ { print $1 }')

if [ "$ENABLE_LOCAL_DESKTOP" = true ] ; then
    wmctrl -c kvs_stream
fi

