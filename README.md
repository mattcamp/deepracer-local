# DeepRacer local training (2020 version)

Heavily based off work by [Crr0004](https://github.com/crr0004), [AlexSchultz](https://github.com/alexschultz), [Richardfan1126](https://github.com/richardfan1126) and [LarsLL](https://github.com/larsll)

This is a very early upload of Matt's local training setup so that a few people can test. Lots of things probably won't work properly and lots of functionality is still missing. 

Very rough guide for use (details to come):

- install nvidia cuda drivers and tools.
- install docker and docker-compose
- set docker-nvidia2 as default runtime in your `/etc/docker/daemon.json`
   
        {
         "default-runtime": "nvidia",
            "runtimes": {
                "nvidia": {
                    "path": "nvidia-container-runtime",
                    "runtimeArgs": []
                }
            }
        }


- edit reward function and training params in `data/minio/bucket/custom_files`. Note that the track name MUST be the same in both files!
- tweak any other settings you want in `config.env`
   - Modify `ENABLE_GPU_TRAINING` for SageMaker runtime: `true` (nvidia runtime) or `false` (CPU runtime). Default is GPU.
   - If you do not have an nvidia GPU then you will also need to change the tag of the robomaker image inside `docker-compose.yml`
   - Set `ENABLE_LOCAL_DESKTOP` to `true` if you have a local X-windows install (desktop machine) and want to automatically start the stream viewer and tail sagemaker logs.
   - Install tmux (`sudo apt install tmux` on Ubuntu Linux) if you want robomaker + sagemaker logs automatically tailed in your terminal session.
- run `./start-training.sh` to start training
- view docker logs to see if it's working (automatic if `tmux` is installed)
- run `./stop-training.sh` to stop training.
- run `./delete_last_run.sh` to clear out the buckets for a fresh run. 

The first run will likely take quite a while to start as it needs to pull over 10GB of all the docker images.
You can avoid this delay by pulling the images in advance:

   - `docker pull awsdeepracercommunity/deepracer-sagemaker:<cpu or gpu>`
   - `docker pull awsdeepracercommunity/deepracer-robomaker:<cpu or gpu>`
   - `docker pull mattcamp/dr-coach`
   - `docker pull minio/minio`

## Video stream

The video stream is available either via a web stream of via Kinesis. 

### Web stream:

The web video stream is exposed on port 8888. If you're running a local browser then you should be able to browse directly to `http://127.0.0.1:8888/stream_viewer?topic=/racecar/deepracer/kvs_stream` once Robomaker has started.

### Kinesis stream:

Kinesis video currently only works via the real AWS Kinesis service probably only makes sense if you are training on an EC2 instance.

To use Kinesis:
- create a real AWS user (with programmatic access keys) which has a policy attached that allows Kinesis access. 
- Update the AWS keys in config.env (including the minio ones) to match the user you have created.
- Create a stream in Kinesis with a name to match the `KINESIS_VIDEO_STREAM_NAME` value (in config.vars) in region `eu-west-1`
- Set `ENABLE_KINESIS` to `true` in config.env

Kinesis video is a stream of approx 1.5Mbps so beware the impact on your AWS costs and your bandwidth. 

Once working the stream should be visible in the Kinesis console. 

### VNC
You can enter runnning environment using a vncviewer at localhost:8080.

## Known issues:
- Sometimes sagemaker won't start claiming that `/opt/ml/input/config/resourceconfig.json` is missing. Still trying to work out why.
- Stopping training at the wrong time seems to cause a problem where sagemaker will crash next time when trying to load the 'best' model which may not exist properly. This only happens if you start a new training session without clearing out the bucket first. Yet to be seen if this will cause a problem when trying to use pretrained models.
- `training_params.yaml` must exist in the target bucket or robomaker will not start. The start-training.sh script will copy it over from custom_files if necessary.
- Scripts not currently included to handle pretrainined models or uploading to AWS Console or virtual league. 
- Current sagemaker and robomaker GPU images are built for nvidia GPU only. 
- The sagemaker and robomakers images are huge (~4.5GB)

## Getting help

Join `#dr-local-training-setup` on the AWS Machine Learning Community Slack at https://deepracing.io


