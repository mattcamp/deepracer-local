# DeepRacer local training (2020 version)

Heavily based off work by [Crr0004](https://github.com/crr0004), [AlexSchultz](https://github.com/alexschultz), [Richardfan1126](https://github.com/richardfan1126) and [LarsLL](https://github.com/larsll)

## Prerequisites

This project is designed to run on a linux system, ideally with an nvidia GPU. CPU training is possible but will be very slow. AMD GPUs are not currently supported.
Ubuntu 18.04 has been extensively tested. 

1.  install nvidia cuda drivers and tools.
2.  install docker and docker-compose
3.  set docker-nvidia2 as default runtime in your `/etc/docker/daemon.json`
   
        {
         "default-runtime": "nvidia",
            "runtimes": {
                "nvidia": {
                    "path": "nvidia-container-runtime",
                    "runtimeArgs": []
                }
            }
        }

Visit the Community Knowledge Base for [a list of detailed resources and checks to confirm your prerequisites are set up properly.](https://wiki.deepracing.io/Local_Training#Prerequisites)

## Configure training session

1.  Edit the reward function in `data/minio/bucket/custom_files/reward.py`
2.  Edit the action space, CNN layers and sensors in `data/mini/bucket/custom_files/model_metadata.json`
3.  Edit the training params in `config.env` and `data/minio/bucket/custom_files/training_params.yaml`. Note that the track name MUST be the same in both files!

    Useful options include:
   
    | option | description |
    |--------|-------------|
    |ENABLE_GPU_TRAINING|Enables GPU for SageMaker runtime: `true` (nvidia runtime) or `false` (CPU runtime). Default is GPU|
    |ENABLE_LOCAL_DESKTOP|Set to `true` if you have a local X-windows install (desktop machine) and want to automatically start the stream viewer and tail sagemaker and robomaker logs.|
    |ENABLE_TMUX|Enables tmux for automatic log tails in your existing terminal session (good for remote servers)|
    |ENABLE_GUI|Enables gazebo client. Access via vnc on localhost:8080|
    |WORLD_NAME|The track name. Tracks are contained within the robomaker container image, built from the [deepracer-simapp community project](https://github.com/aws-deepracer-community/deepracer-simapp/tree/master/bundle/deepracer_simulation_environment/share/deepracer_simulation_environment/worlds) (excluding the .world suffix)
    
    Many other options are available.
    
4. Edit hyperparameters in `hyperparams.json` inside `src/rl_coach_2020_v2/hyperparams.json` - a symlink has been created in the root directory.
    
    More information on configuring local training can be found at https://wiki.deepracing.io/Customise_Local_Training

## Starting a training session
Run `./start-training.sh` to start training. 

The current model data dir (defaults to data/minio/bucket/current) must be empty. 

To use a pretrained model as a base for a new training session rename `data/minio/bucket/current` to `data/minio/bucket/rl-deepracer-pretrained` and set `"pretrained": "true"` in hyperparams.json

The first run will likely take quite a while to start as it needs to pull over 10GB of all the docker images.
You can avoid this delay by pulling the images in advance:

   - `docker pull awsdeepracercommunity/deepracer-sagemaker:<cpu or gpu>`
   - `docker pull awsdeepracercommunity/deepracer-robomaker:<cpu or gpu>`
   - `docker pull mattcamp/dr-coach`
   - `docker pull minio/minio`
   
   Note that different flavours of CPU image are available, see https://github.com/aws-deepracer-community/deepracer-simapp for details.
   `cpu-avx2` is the default.

## Monitoring training
- Docker logs should open automatically in new terminal tabs if running with `ENABLE_LOCAL_DESKTOP` enabled, or via tmux in your existing terminal session if `ENABLE_TMUX` is enabled.
- Logs can be manually viewed using `docker ps` and `docker logs robomaker` or `docker logs <sagemaker_container_id>`
- The web video stream is available by default on port 8888. If running in desktop mode a browser window should open automatically, otherwise you can try opening a url such as http://127.0.0.1:8888/stream_viewer?topic=/racecar/deepracer/kvs_stream
- Kinesis video stream can also be enabled. See below for more details, however usually the web video stream just works better.
- if `ENABLE_GUI` is enabled then you can connect a vncviewer on port 8080 to view the gazebo client directly.

## Stopping training
Run `./stop-training.sh` to stop training. 

If running, sagemaker will be stopped first and then after a 20s delay the rest of the containers will be stopped. This allows Robomaker to create a model.tar.gz file in the current model dir, ready to be loaded onto a physical DeepRacer car.
  
**NOTE: Sagemaker should not be stopped during the policy training phase or things might get weird and corrupt. You should only stop training while the video stream status is "Training" and not "Evaluating" (or verify via sagemaker logs that policy training has completed for the current iteration)**

## Model management
- run `./delete_last_run.sh` to clear out the buckets for a fresh run. For convenient version without sudo prompt check out `utilites/delete-last.c`.
- run `./local-copy.sh <model_backup_name>` to backup current model files into user specified MODEL directory.
- run `./mk-model.sh <model_path>` to create physical car uploadable .tar.gz file from your model. (Will be removed in a future update once file gets correctly generated after training)

### Kinesis video stream:

Kinesis video currently only works via the real AWS Kinesis service and probably only makes sense if you are training on an EC2 instance.

To use Kinesis:
- create a real AWS user (with programmatic access keys) which has a policy attached that allows Kinesis access. 
- Update the AWS keys in config.env (including the minio ones) to match the user you have created.
- Create a stream in Kinesis with a name to match the `KINESIS_VIDEO_STREAM_NAME` value (in config.vars) in region `eu-west-1`
- Set `ENABLE_KINESIS` to `true` in config.env

Kinesis video is a stream of approx 1.5Mbps so beware the impact on your AWS costs and your bandwidth. 

Once working the stream should be visible in the Kinesis console. 

## Known issues:
- Sometimes sagemaker won't start claiming that `/opt/ml/input/config/resourceconfig.json` is missing. Still trying to work out why.
- Stopping training at the wrong time seems to cause a problem where sagemaker will crash next time when trying to load the 'best' model which may not exist properly. This only happens if you start a new training session without clearing out the bucket first. Yet to be seen if this will cause a problem when trying to use pretrained models.
- `training_params.yaml` must exist in the target bucket or robomaker will not start. The start-training.sh script will copy it over from custom_files if necessary.
- Scripts not currently included to handle uploading to AWS Console or virtual league. 
- Current sagemaker and robomaker GPU images are built for nvidia GPU only. 
- The sagemaker and robomaker images are huge (~4.5GB)

## Getting help

Join `#dr-local-training-setup` on the AWS Machine Learning Community Slack at https://deepracing.io


