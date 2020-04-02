#!/bin/bash
#
#TMUX=$(which tmux)

if [ -z "$(which tmux)" ]
then
  echo "tmux not found in path, not starting log tails"
  exit 0
fi

tmux new-session -d bash
tmux split-window -h bash
tmux set pane-border-status;
tmux display-pane;
tmux select-pane -t 0:0.0 -T 'Robomaker logs'
tmux select-pane -t 0:0.1 -T 'Sagemaker logs'
tmux send -t 0:0.0 "docker logs -f robomaker" C-m
tmux send -t 0:0.1 "./tail-sagemaker-logs.sh" C-m
tmux select-pane -t 0:0.0
tmux -2 attach-session -d

