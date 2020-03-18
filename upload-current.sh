#!/usr/bin/env bash

S3_BUCKET=$1
S3_PREFIX=$2

MODEL_DIR=data/minio/bucket/current/model/

while getopts ":c:" opt; do
case $opt in
c) CHECKPOINT="$OPTARG"
;;
\?) echo "Invalid option -$OPTARG" >&2
;;
esac
done

CHECKPOINT_FILE=$MODEL_DIR"deepracer_checkpoints.json"
if [ ! -f ${CHECKPOINT_FILE} ]; then
  echo "Checkpoint file not found!"
  exit 1
else
  echo "found checkpoint index file "$CHECKPOINT_FILE
fi;

if [ -z "$CHECKPOINT" ]; then
  echo "Checkpoint not supplied, checking for latest checkpoint"

  LAST_CHECKPOINT=`cat $CHECKPOINT_FILE |jq ".last_checkpoint.name"`
  BEST_CHECKPOINT=`cat $CHECKPOINT_FILE |jq ".best_checkpoint.name"`
  
  CHECKPOINT=$LAST_CHECKPOINT

  echo "latest checkpoint = "$CHECKPOINT
else
  echo "Checkpoint supplied: ["${CHECKPOINT}"]"
fi

MODEL=`echo $CHECKPOINT |sed "s@^[^0-9]*\([0-9]\+\).*@\1@"`
mkdir -p checkpoint
MODEL_FILE=$MODEL_DIR"model_"$MODEL".pb"
METADATA_FILE=$MODEL_DIR"model_metadata.json"


if test ! -f "$MODEL_FILE"; then
    echo "$MODEL_FILE doesn't exist"
    exit 1
else
  cp $MODEL_FILE checkpoint/  
fi

if test ! -f "$METADATA_FILE"; then
    echo "$METADATA_FILE doesn't exist"
    exit 1
else
  cp $METADATA_FILE checkpoint/  
fi

CHECKPOINT_FILES=`echo $CHECKPOINT* |sed "s/\"//g"`
for i in $( find $MODEL_DIR -type f -name $CHECKPOINT_FILES ); do
  cp $i checkpoint/  
done

VAR1=`cat $CHECKPOINT_FILE |jq ".last_checkpoint = .best_checkpoint"`
VAR2=`echo $VAR1 |jq ".last_checkpoint.name = $CHECKPOINT"`
VAR3=`echo $VAR2 |jq ".best_checkpoint.name = $CHECKPOINT"`
echo $VAR3 >checkpoint/deepracer_checkpoints.json

# upload files to s3
for filename in checkpoint/*; do
  aws s3 cp $filename s3://$S3_BUCKET/$S3_PREFIX/model/
done

tar -czvf ${CHECKPOINT}-checkpoint.tar.gz checkpoint/*

rm -rf checkpoint
echo 'done uploading model!'

