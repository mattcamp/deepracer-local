#!/usr/bin/env bash

source config.env

export ROBOMAKER_COMMAND=""

SAGEMAKER_ID=$(docker ps | awk ' /sagemaker/ { print $1 }')
if [ ! -z "${SAGEMAKER_ID}" ]; then
  echo "Stopping sagemaker and waiting 20s while model.tar.gz is created"
  docker stop ${SAGEMAKER_ID}
  sleep 20
  docker rm ${SAGEMAKER_ID}
fi

docker-compose -f ./docker-compose.yml down

if [ "$ENABLE_LOCAL_DESKTOP" = true ] ; then
    if [ -n  "$(which wmctrl)" ] ; then
      wmctrl -c kvs_stream
    fi
fi

if [ "$ENABLE_TMUX" = true ] ; then
  tmux kill-session
fi


