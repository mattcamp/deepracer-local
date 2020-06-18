#!/bin/bash
# USAGE: ./local-copy.sh <model_backup_name>

MODELS=../models

echo "Backup to $MODELS/$1"
echo "..."

mkdir $MODELS/$1

cp data/robomaker/log/rl_coach_* $MODELS/$1/
cp -R data/minio/bucket/current/model $MODELS/$1/
cp data/minio/bucket/custom_files/reward.py $MODELS/$1/

echo "done"

