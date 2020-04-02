#!/usr/bin/env bash

if [ ! -e data/minio/bucket/current/training_params.yaml ]; then
    mkdir -p data/minio/bucket/current
    cp data/minio/bucket/custom_files/training_params.yaml data/minio/bucket/current
fi

export ROBOMAKER_COMMAND="./run.sh run distributed_training.launch"
export CURRENT_UID=$(id -u):$(id -g)

docker-compose -f ./docker-compose.yml up -d

if [ "$ENABLE_LOCAL_DESKTOP" = true ] ; then
    echo "Starting desktop mode... waiting 20s for Sagemaker container to start"
    sleep 20

    echo 'Attempting to pull up sagemaker logs...'
    SAGEMAKER_ID="$(docker ps | awk ' /sagemaker/ { print $1 }')"

    echo 'Attempting to open stream viewer and logs...'
    gnome-terminal -x sh -c "echo viewer;x-www-browser -new-window http://localhost:8888/stream_viewer?topic=/racecar/deepracer/kvs_stream;sleep 1;wmctrl -r kvs_stream -b remove,maximized_vert,maximized_horz;sleep 1;wmctrl -r kvs_stream -e 1,100,100,720,640"
    gnome-terminal -x sh -c "docker logs -f $SAGEMAKER_ID"
else
    echo "Started in headless server mode. Set ENABLE_LOCAL_DESKTOP to true in config.env for desktop mode."
    ./tmux-logs.sh
fi

