#!/bin/bash

TMUX=$(which tmux)

if [ -z $TMUX ]
then
  echo "tmux not found in path"
  exit 0
fi

tmux new-session -d bash
tmux split-window -h bash
#sends keys to first and second terminals
tmux send -t 0:0.0 "docker logs -f robomaker" C-m
tmux send -t 0:0.1 "./tail-sagemaker-logs.sh" C-m
tmux -2 attach-session -d

