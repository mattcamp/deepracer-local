#!/usr/bin/env bash

source config.env

if [ -e data/minio/bucket/current/model/deepracer_checkpoints.json ] ; then
  echo "WARNING: Files were found in the current model directory data/minio/bucket/current/"
  echo "Please run ./delete_last_run.sh or relocate the current model dir before starting a new training session."
  echo "You cannot currently restart training of an existing model, instead you should move the current model dir to rl-deepracer-pretrained and enable pretrained in hyperparams.json"
  exit 1
fi

if [ ! -e data/minio/bucket/current/training_params.yaml ]; then
    mkdir -p data/minio/bucket/current
    cp data/minio/bucket/custom_files/training_params.yaml data/minio/bucket/current
fi

export ROBOMAKER_COMMAND="./run.sh run distributed_training.launch"
export CURRENT_UID=$(id -u):$(id -g)

docker-compose -f ./docker-compose.yml up -d

if [ "$ENABLE_LOCAL_DESKTOP" = true ] ; then
    echo "Starting desktop mode... waiting 30s for Sagemaker container to start"
    sleep 30

    echo 'Attempting to pull up sagemaker logs...'
    SAGEMAKER_ID="$(docker ps | awk ' /sagemaker/ { print $1 }')"

    echo 'Attempting to open stream viewer and logs...'
    gnome-terminal --tab -- sh -c "echo viewer;x-www-browser -new-window http://localhost:8888/stream_viewer?topic=/racecar/deepracer/kvs_stream;sleep 1;wmctrl -r kvs_stream -b remove,maximized_vert,maximized_horz;sleep 1;wmctrl -r kvs_stream -e 1,100,100,720,640"
    gnome-terminal --tab -- sh -c "docker logs -f $SAGEMAKER_ID"
    gnome-terminal --tab -- sh -c 'docker logs -f robomaker'
else
    echo "Started in headless server mode. Set ENABLE_LOCAL_DESKTOP to true in config.env for desktop mode."
    if [ "$ENABLE_TMUX" = true ] ; then
        ./tmux-logs.sh
    fi
fi

