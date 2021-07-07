#!/bin/bash
# Perform a backup of bucket/current model into your MODELS directory.
# USAGE: ./local-copy.sh <model_backup_name>

MODELS=../models

if [ "$1" = "" ]; then
	echo "USAGE: $0 <model_backup_name>"
	printf "\nYou can edit MODELS directory path inside this script.\n\n"
	echo "Current $MODELS directory status:"
	ls $MODELS
else

	echo "Backup to $MODELS/$1"
	echo "..."

	mkdir $MODELS/$1

	cp data/robomaker/log/rl_coach_* $MODELS/$1/
	cp -R data/minio/bucket/current/model $MODELS/$1/
	cp data/minio/bucket/custom_files/reward.py $MODELS/$1/
	cp data/minio/bucket/current/model.tar.gz $MODELS/$1/$1.tar.gz

	echo "done"
fi

