#!/bin/bash
# create .tar.gz file uploadable to physical deepracer
# USAGE: ./mk-model.sh <model_path>
cd $1
echo $(pwd)

if [ "$1" = "" ]; then
	echo "USAGE: $0 <model_path>"
else

	NUM=`cut -d '_' -f 1 < model/.coach_checkpoint`

	mkdir -p output/agent

	cp "model/model_$NUM.pb" output/agent/model.pb
	cp model/model_metadata.json output/

	cd output
	tar -czvf ../output.tar.gz *

	echo "done"

fi

