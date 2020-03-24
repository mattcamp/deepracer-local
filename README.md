# DeepRacer local training (2020 version)

Heavily based off work by [Crr0004](https://github.com/crr0004), [AlexSchultz](https://github.com/alexschultz), [Richardfan1126](https://github.com/richardfan1126) and [LarsLL](https://github.com/larsll)

This is a very early upload of Matt's local training setup so that a few people can test. Lots of things probably won't work properly and lots of functionality is still missing. 

Very rough guide for use (details to come):

- install nvidia drivers and tools. 
- install docker and docker-compose
- set docker to use docker-nvidia2 as default runtime
- edit reward function and training params in `data/minio/bucket/custom_files`
- tweak any other settings you want in `config.env`
   - Modify `ENABLE_GPU_TRAINING` for SageMaker runtime: `true` (nvidia runtime) or `false` (CPU runtime). Default is GPU.
   - Set `ENABLE_LOCAL_DESKTOP` to `true` if you have a local X-windows install (desktop machine) and want to automatically start the stream viewer and tail sagemaker logs.
- run `./start-training.sh` to start training
- view docker logs to see if it's working.
- run `./stop-training.sh` to stop training.
- run `./delete_last_run.sh` to clear out the buckets for a fresh run. 

The first run will likely take quite a while to start as it needs to pull over 10GB of all the docker images.
You can avoid this delay by pulling the images in advance:

   - `docker pull awsdeepracercommunity/deepracer-sagemaker:<cpu or gpu>`
   - `docker pull awsdeepracercommunity/deepracer-robomaker:<cpu or gpu>`
   - `docker pull mattcamp/dr-coach`
   - `docker pull minio/minio`

## Kinesis video

Kinesis video currently only works via the real AWS Kinesis service. 

To use Kinesis:
- create a real AWS user (with programmatic access keys) which has a policy attached that allows Kinesis access. 
- Update the AWS keys in config.env (including the minio ones) to match the user you have created.
- Create a stream in Kinesis with a name to match the `KINESIS_VIDEO_STREAM_NAME` value (in config.vars) in region `eu-west-1`
- Set `ENABLE_KINESIS` to `true` in config.env

Kinesis video is a stream of approx 1.5Mbps so beware the impact on your AWS costs and your bandwidth. 

Once working the stream should be visible in the Kinesis console. 

TODO: Get Kinesis working with localstack for local video streams.

## Known issues:
- Sometimes sagemaker won't start claiming that `/opt/ml/input/config/resourceconfig.json` is missing. Still trying to work out why.
- Stopping training at the wrong time seems to cause a problem where sagemaker will crash next time when trying to load the 'best' model which may not exist properly. This only happens if you start a new training session without clearing out the bucket first. Yet to be seen if this will cause a problem when trying to use pretrained models.
- `training_params.yaml` must exist in the target bucket or robomaker will not start. The start-training.sh script will copy it over from custom_files if necessary.
- Scripts not currently included to handle pretrainined models or uploading to AWS Console or virtual league. 
- Current sagemaker and robomaker GPU images are built for nvidia GPU only. 
- The sagemaker and robomakers images are huge (~4.5GB)


