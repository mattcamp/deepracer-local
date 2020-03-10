import docker
from flask import jsonify

client = docker.from_env()


class CurrentJob():
    def __init__(self):

        self.minio_image = "minio/minio"
        self.coach_image = "mattcamp/dr-coach"
        self.robomaker_image = "awsdeepracercommunity/deepracer-robomaker:matt"

        self.docker_env = {
            'ALTERNATE_DRIVING_DIRECTION': None,
            'APP_REGION': "us-east-1",
            'AWS_REGION': "us-east-1",
            'AWS_ACCESS_KEY_ID': "your_aws_access_key",
            'AWS_SECRET_ACCESS_KEY': "your_aws_secret_key",
            'CHANGE_START_POSITION': None,
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
            'ENABLE_KINESIS': "false",
            'ENABLE_GUI': "true"
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
            'NUMBER_OF_OBSTACLES': "3",
            'CHANGE_START_POSITION': "true",
            'OBSTACLE_TYPE': "BOX",
            'RANDOMIZE_OBSTACLE_LOCATIONS': "false"
        }

        self.training_job = None
        self.minio_container = None
        self.coach_container = None
        self.robomaker_container = None
        self.sagemaker_container = None

        self.status = {
            'coach_status': None,
            'robomaker_status': None,
            'sagemaker_status': None,
            'episode_number': None,
            'iteration_number': None,
            'best_checkpoint': None
        }
        self.update_status()

    def update_status(self):
        print("Updating current docker status")
        self.status['sagemaker_status'] = None
        self.status['robomaker_status'] = None
        self.status['coach_status'] = None
        self.status['minio_status'] = None

        for container in client.containers.list():
            container.reload()
            if "sagemaker" in container.attrs['Config']['Image']:
                self.status['sagemaker_status'] = container.attrs['State']['Status']
                if not self.sagemaker_container:
                    self.sagemaker_container = container

            if "robomaker" in container.attrs['Config']['Image']:
                self.status['robomaker_status'] = container.attrs['State']['Status']
                if not self.robomaker_container:
                    self.robomaker_container = container

            if "coach" in container.attrs['Config']['Image']:
                self.status['coach_status'] = container.attrs['State']['Status']
                if not self.coach_container:
                    self.coach_container = container

            if "minio" in container.attrs['Config']['Image']:
                self.status['minio_status'] = container.attrs['State']['Status']
                if not self.minio_container:
                    self.minio_container = container
                print(self.minio_container.attrs['State']['Status'])



    def configure_from_queued_job(self, job):
        self.training_job = job

        self.docker_env['WORLD_NAME'] = job.track
        self.docker_env['MODEL_S3_PREFIX'] = job.name
        self.docker_env['SAGEMAKER_SHARED_S3_PREFIX'] = job.name
        self.docker_env['REWARD_FILE_S3_KEY'] = "custom_files/%s" % job.reward_function_filename
        self.docker_env['MODEL_METADATA_FILE_S3_KEY'] = "custom_files/%s" % job.model_metadata_filename
        self.docker_env['ALTERNATE_DRIVING_DIRECTION'] = job.alternate_direction
        self.docker_env['CHANGE_START_POSITION'] = job.change_start_position
        self.docker_env['HP_BATCH_SIZE'] = job.batch_size
        self.docker_env['HP_ENTROPY'] = job.entropy
        self.docker_env['HP_DISCOUNT'] = job.discount_factor
        self.docker_env['HP_LOSS_TYPE'] = job.loss_type
        self.docker_env['HP_LEARNING_RATE'] = job.learning_rate
        self.docker_env['HP_EPISODES_BETWEEN_TRAINING'] = job.episodes_between_training
        self.docker_env['HP_EPOCHS'] = job.epochs
        self.docker_env['PRETRAINED_MODEL'] = job.pretrained_model

        self.training_params['WORLD_NAME'] = job.track
        self.training_params['SAGEMAKER_SHARED_S3_PREFIX'] = job.name
        self.training_params['CHANGE_START_POSITION'] = job.change_start_position
        self.training_params['ALTERNATE_DRIVING_DIRECTION'] = job.alternate_direction
        self.training_params['REWARD_FILE_S3_KEY'] = "custom_files/%s" % job.reward_function_filename
        self.training_params['MODEL_METADATA_FILE_S3_KEY'] = "custom_files/%s" % job.model_metadata_filename
        self.training_params['RACE_TYPE'] = job.race_type
        self.training_params['NUMBER_OF_OBSTACLES'] = job.number_of_obstacles
        self.training_params['OBSTACLE_TYPE'] = job.obstacle_type
        self.training_params['RANDOMIZE_OBSTACLE_LOCATIONS'] = job.randomize_obstacle_locations





