#!/bin/bash
# create .tar.gz file uploadable to physical deepracer.
# This should not be necessary if sagemaker is stopped before robomaker as the model.tar.gz will automatically be created.
# USAGE: ./mk-model.sh <model_path>

if [ "$1" = "" ]; then
	echo "USAGE: $0 <model_path>"
	echo 'MODEL_PATH should contain "model" directory'
	echo 'model.pb is chosen using .coach_checkpoint iteration number'
else
	cd $1
	echo $(pwd)

	NUM=`cut -d '_' -f 1 < model/.coach_checkpoint`

	mkdir -p output/agent

	cp "model/model_$NUM.pb" output/agent/model.pb
	cp model/model_metadata.json output/

	cd output
	tar -czvf ../output.tar.gz *

	echo "done"

fi

