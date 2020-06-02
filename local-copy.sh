#!/bin/bash

MODELS=../models

echo "Backup to $MODELS/$1"
echo "..."

mkdir $MODELS/$1

cp data/robomaker/log/rl_coach_* $MODELS/$1/
cp -R data/minio/bucket/current/model $MODELS/$1/
cp data/minio/bucket/current/source/* $MODELS/$1/

echo "done"

