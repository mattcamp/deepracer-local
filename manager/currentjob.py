import docker
from flask import jsonify

client = docker.from_env()


class CurrentJob():
    def __init__(self):
        print("*** CurrentJob init")
        self.minio_image = "minio/minio"
        self.coach_image = "mattcamp/dr-coach"
        self.robomaker_image = "awsdeepracercommunity/deepracer-robomaker:2.0.3-cpu-avx2"

        self.docker_env = {
            'ALTERNATE_DRIVING_DIRECTION': None,
            'APP_REGION': "us-east-1",
            'AWS_REGION': "us-east-1",
            'AWS_ACCESS_KEY_ID': "your_aws_access_key",
            'AWS_SECRET_ACCESS_KEY': "your_aws_secret_key",
            'CHANGE_START_POSITION': True,
            'GPU_AVAILABLE': True,
            'KINESIS_VIDEO_STREAM_NAME': "dr-kvs-local",
            'LOCAL': True,
            'MINIO_ACCESS_KEY': "your_aws_access_key",
            'MINIO_SECRET_KEY': "your_aws_secret_key",
            'MODEL_METADATA_FILE_S3_KEY': "custom_files/model_metadata.json",
            'MODEL_S3_BUCKET': "bucket",
            'MODEL_S3_PREFIX': "current",
            'REWARD_FILE_S3_KEY': "custom_files/reward.py",
            'S3_ENDPOINT_URL': "http://minio:9000",
            'S3_YAML_NAME': "training_params.yaml",
            'SAGEMAKER_SHARED_S3_BUCKET': "bucket",
            'SAGEMAKER_SHARED_S3_PREFIX': "current",
            'WORLD_NAME': None,
            "LOCAL_MODEL_ID": None,
            'ENABLE_KINESIS': "false",
            'ENABLE_GUI': "false"
        }

        self.training_params = {
            'WORLD_NAME': None,
            'RACE_TYPE': "OBJECT_AVOIDANCE",
            'SAGEMAKER_SHARED_S3_PREFIX': "current",
            'CHANGE_START_POSITION': None,
            'METRICS_S3_OBJECT_KEY': "DeepRacer-Metrics/TrainingMetrics.json",
            'AWS_REGION': "us-east-1",
            'NUMBER_OF_EPISODES': "10",
            'CAR_NAME': "MyCar",
            'KINESIS_VIDEO_STREAM_NAME': "dr-kvs-local",
            'REWARD_FILE_S3_KEY': "custom_files/reward.py",
            'METRIC_NAMESPACE': "AWSDeepRacer",
            'ALTERNATE_DRIVING_DIRECTION': "false",
            'ROBOMAKER_SIMULATION_JOB_ACCOUNT_ID': "123456789012",
            'METRICS_S3_BUCKET': "bucket",
            'SAGEMAKER_SHARED_S3_BUCKET': "bucket",
            'JOB_TYPE': "TRAINING",
            'MODEL_METADATA_FILE_S3_KEY': "custom_files/model_metadata.json",
            'METRIC_NAME': "TrainingRewardScore",
            'CAR_COLOR': "Purple",
            'TARGET_REWARD_SCORE': "None",
            'NUMBER_OF_OBSTACLES': "0",
            'CHANGE_START_POSITION': "true",
            'OBSTACLE_TYPE': "BOX",
            'RANDOMIZE_OBSTACLE_LOCATIONS': "false"
        }

        self.metrics = []
        self.entropy_metrics = []

        self.local_model = None
        self.local_model_id = None
        self.minio_container = None
        self.coach_container = None
        self.robomaker_container = None
        self.sagemaker_container = None
        self.robotail = None
        self.sagetail = None
        self.metricstail = None

        self.desired_state = None
        self.target_episodes = 0

        self.status = {
            'status_id': None,
            'coach_status': None,
            'robomaker_status': None,
            'sagemaker_status': None,
            'episode_number': 0,
            'iteration_number': 0,
            'best_checkpoint': None,
            'episodes_per_iteration': 0
        }
        self.update_status()


    def update_status(self):
        # print("Updating current docker status")
        self.status['sagemaker_status'] = None
        self.status['robomaker_status'] = None
        self.status['coach_status'] = None
        self.status['minio_status'] = None

        for container in client.containers.list():
            try:
                container.reload()
            except:
                continue
            if "sagemaker" in container.attrs['Config']['Image']:
                self.status['sagemaker_status'] = container.attrs['State']['Status']
                if not self.sagemaker_container:
                    self.sagemaker_container = container

            if "robomaker" in container.attrs['Config']['Image']:
                self.status['robomaker_status'] = container.attrs['State']['Status']
                if not self.robomaker_container:
                    self.robomaker_container = container
                # print(container.attrs)

            if "coach" in container.attrs['Config']['Image']:
                self.status['coach_status'] = container.attrs['State']['Status']
                if not self.coach_container:
                    self.coach_container = container

            if "minio" in container.attrs['Config']['Image']:
                self.status['minio_status'] = container.attrs['State']['Status']
                if not self.minio_container:
                    self.minio_container = container






    def configure_from_queued_job(self, model):
        self.local_model = model
        self.local_model_id = model.id
        self.target_episodes = model.episodes_target
        self.status["model_id"] = model.id
        self.status["episodes_per_iteration"] = model.episodes_between_training

        print("Loading model: {}-{}".format(model.id, model.name))

        self.docker_env['WORLD_NAME'] = model.track
        self.docker_env['MODEL_S3_PREFIX'] = "{}-{}".format(model.id, model.name)
        self.docker_env['SAGEMAKER_SHARED_S3_PREFIX'] = "{}-{}".format(model.id, model.name)
        self.docker_env['REWARD_FILE_S3_KEY'] = "custom_files/%s" % model.reward_function_filename
        self.docker_env['MODEL_METADATA_FILE_S3_KEY'] = "custom_files/%s" % model.model_metadata_filename
        self.docker_env['ALTERNATE_DRIVING_DIRECTION'] = model.alternate_direction
        self.docker_env['CHANGE_START_POSITION'] = model.change_start_position
        self.docker_env['HP_BATCH_SIZE'] = model.batch_size
        self.docker_env['HP_ENTROPY'] = model.entropy
        self.docker_env['HP_DISCOUNT'] = model.discount_factor
        self.docker_env['HP_LOSS_TYPE'] = model.loss_type
        self.docker_env['HP_LEARNING_RATE'] = model.learning_rate
        self.docker_env['HP_EPISODES_BETWEEN_TRAINING'] = model.episodes_between_training
        self.docker_env['HP_EPOCHS'] = model.epochs
        self.docker_env['LOCAL_MODEL_ID'] = model.id

        if model.pretrained_model != "None":
            print("Adding pretrained model")
            self.docker_env['PRETRAINED_MODEL'] = model.pretrained_model
        else:
            print("No pretrained model")

        self.docker_env['ENABLE_KINESIS'] = "False"

        self.training_params['WORLD_NAME'] = model.track
        self.training_params['NUMBER_OF_EPISODES'] = model.episodes_target
        self.training_params['SAGEMAKER_SHARED_S3_PREFIX'] = "{}-{}".format(model.id, model.name)
        self.training_params['CHANGE_START_POSITION'] = model.change_start_position
        self.training_params['ALTERNATE_DRIVING_DIRECTION'] = model.alternate_direction
        self.training_params['REWARD_FILE_S3_KEY'] = "custom_files/%s" % model.reward_function_filename
        self.training_params['MODEL_METADATA_FILE_S3_KEY'] = "custom_files/%s" % model.model_metadata_filename
        self.training_params['RACE_TYPE'] = model.race_type
        self.training_params['NUMBER_OF_OBSTACLES'] = model.number_of_obstacles
        self.training_params['OBSTACLE_TYPE'] = model.obstacle_type
        self.training_params['RANDOMIZE_OBSTACLE_LOCATIONS'] = model.randomize_obstacle_locations





