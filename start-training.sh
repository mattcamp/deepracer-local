#!/usr/bin/env bash

if [ ! -e data/minio/bucket/current/training_params.yaml ]; then
    mkdir -p data/minio/bucket/current
    cp data/minio/bucket/custom_files/training_params.yaml data/minio/bucket/current
fi

export ROBOMAKER_COMMAND="./run.sh run distributed_training.launch"
export CURRENT_UID=$(id -u):$(id -g)

docker-compose -f ./docker-compose.yml up -d

#sleep for 20 seconds to allow the containers to start
sleep 20

echo 'Attempting to pull up sagemaker logs...'
SAGEM_ID="$(docker ps | awk ' /sagemaker/ { print $1 }')"
gnome-terminal -x sh -c "docker logs -f $SAGEM_ID"
nohup docker logs -f $SAGEM_ID >data/robomaker/log/sagemaker_$(date +"%Y%m%d%H%M").log &
##gnome-terminal -x sh -c "docker logs -f $(docker ps | awk ' /sagemaker/ { print $1 }')"

source ./config.env
if [ "$ENABLE_ROS_BROWSER_WINDOW" = true ] ; then
    echo 'Attempting to open the viewer...'
    gnome-terminal -x sh -c "echo viewer;x-www-browser -new-window http://localhost:8888/stream_viewer?topic=/racecar/deepracer/kvs_stream;sleep 1;wmctrl -r kvs_stream -b remove,maximized_vert,maximized_horz;sleep 1;wmctrl -r kvs_stream -e 1,100,100,720,640"
fi

