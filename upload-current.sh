#!/usr/bin/env bash
#
# Upload trained model s3 in a format compatible with DeepRacer model import functionality.
# Example usage to upload the best model:
#     ./upload-current.sh aws-deepracer-XXX model1 -b
#

S3_BUCKET=$1
S3_PREFIX=$2

MODEL_DIR=data/minio/bucket/current/model/

echo "Uploading to model ==>  s3://$S3_BUCKET/$S3_PREFIX  <=="

USE_BEST=false
while getopts ":c:b" opt; do
case $opt in
    c) CHECKPOINT="$OPTARG"
       ;;
    b) USE_BEST=true
       ;;
    \?) echo "Invalid option -$OPTARG" >&2
        ;;
esac
done

CHECKPOINT_FILE=$MODEL_DIR"deepracer_checkpoints.json"
if [ ! -f ${CHECKPOINT_FILE} ]; then
  echo "Checkpoint file not found!"
  exit 1
fi
echo "found checkpoint index file "$CHECKPOINT_FILE

if [ -z "$CHECKPOINT" ]; then
  #echo "Checkpoint not supplied, checking for latest checkpoint"
  LAST_CHECKPOINT=`cat $CHECKPOINT_FILE |jq ".last_checkpoint.name" | sed s/\"//g`
  BEST_CHECKPOINT=`cat $CHECKPOINT_FILE |jq ".best_checkpoint.name" | sed s/\"//g`
  if $USE_BEST; then
     CHECKPOINT=$BEST_CHECKPOINT
     echo "Using best checkpoint ==>  $CHECKPOINT  <=="
  else
     CHECKPOINT=$LAST_CHECKPOINT
     echo "Using latest checkpoint ==>  $CHECKPOINT  <=="
  fi
else
  echo "Checkpoint supplied: ["${CHECKPOINT}"]"
fi

MODEL=`echo $CHECKPOINT |sed "s@^[^0-9]*\([0-9]\+\).*@\1@"`
rm -rf checkpoint
cp -a upload-template checkpoint
mkdir -p checkpoint/model
MODEL_FILE=$MODEL_DIR"model_"$MODEL".pb"
METADATA_FILE=$MODEL_DIR"model_metadata.json"

if test ! -f "$MODEL_FILE"; then
    echo "$MODEL_FILE doesn't exist"
    exit 1
fi

if test ! -f "$METADATA_FILE"; then
    echo "$METADATA_FILE doesn't exist"
    exit 1
fi

cp -v $MODEL_FILE checkpoint/model/
cp -v $METADATA_FILE checkpoint/model/

CHECKPOINT_FILES=$MODEL_DIR/${CHECKPOINT}*
#for i in $( find $MODEL_DIR -type f -name ${CHECKPOINT}\* ); do
for i in $CHECKPOINT_FILES
do
  cp -v $i checkpoint/model/
done

echo $CHECKPOINT > checkpoint/model/.coach_checkpoint
# File deepracer_checkpoints.json is optional.

# Cleanup upload destination
aws s3 rm --recursive s3://$S3_BUCKET/$S3_PREFIX/

# Upload files to s3
aws s3 sync checkpoint/ s3://$S3_BUCKET/$S3_PREFIX/

# Backup checkpoint
tar -czvf ${CHECKPOINT}.tar.gz checkpoint
rm -rf checkpoint

echo 'done uploading model!'
