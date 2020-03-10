import os
import shutil
import docker
import time
from manager import current_job
from manager.models import TrainingJob

client = docker.from_env()


def write_training_params(filename):
    print("Writing training_params.yaml into bucket")
    f = open(filename, "w+")
    for key, value in current_job.training_params.items():
        f.write("%s: \"%s\"\n" % (key, value))
    f.close()


def setup_bucket():
    cwd = os.getcwd()
    bucket_path = "%s/data/minio/bucket/%s" % (cwd, current_job.training_job.name)
    if os.path.exists(bucket_path):
        print("Path exists: %s" % bucket_path)
        old_bucket_path = "%s.old" % bucket_path
        if os.path.exists(old_bucket_path):
            print("Old path exists, removing: %s" % old_bucket_path)
            shutil.rmtree(old_bucket_path)
        os.rename(bucket_path, old_bucket_path)

    print("Creating bucket directory: %s" % bucket_path)
    os.mkdir(bucket_path)

    latest_path = "%s/data/minio/bucket/latest" % cwd
    if os.path.exists(latest_path):
        os.remove(latest_path)

    os.symlink(bucket_path, latest_path)

    write_training_params("%s/training_params.yaml" % bucket_path)


def start_training_job():
    current_job.__init__()
    first_job = TrainingJob.query.first()
    current_job.configure_from_queued_job(first_job)
    setup_bucket()
    start_all_containers()


def start_all_containers():
    cwd = os.getcwd()
    networks = client.networks.list(names=['sagemaker-local'])
    if len(networks):
        network = networks[0]
        print("found network %s" % network.id)
    else:
        print("Creating docker network")
        network = client.networks.create("sagemaker-local", driver="bridge", scope="local")

    if not current_job.minio_container:
        print("Starting minio")
        minio_data_dir = "%s/data/minio" % cwd
        current_job.minio_container = client.containers.run(current_job.minio_image,
                                                            name="minio",
                                                            network=network.id,
                                                            environment=current_job.docker_env,
                                                            ports={9000: 9000},
                                                            command="server /data",
                                                            volumes={minio_data_dir: {'bind': '/data', 'mode': 'rw'}},
                                                            detach=True,
                                                            remove=True)

    print("Waiting for minio to start")
    while current_job.minio_container.attrs['State']['Status'] != "running":
        current_job.minio_container.reload()
        # current_job.update_status()
        print(current_job.minio_container.attrs['State']['Status'])
        time.sleep(1)

    if not current_job.coach_container:
        print("Starting coach")
        coach_src_dir = "%s/src/rl_coach_2020_v2" % cwd
        coach_volumes = {'//var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'},
                         coach_src_dir: {'bind': '/deepracer/rl_coach', 'mode': 'rw'},
                         '/robo/container': {'bind': '/robo/container', 'mode': 'rw'}
                         }
        current_job.coach_container = client.containers.run(current_job.coach_image,
                                                            name="coach",
                                                            network=network.id,
                                                            environment=current_job.docker_env,
                                                            volumes=coach_volumes,
                                                            detach=True,
                                                            remove=True)

    if not current_job.robomaker_container:
        print("Starting robomaker")
        robomaker_data_dir = "%s/data/robomaker" % cwd
        current_job.robomaker_container = client.containers.run(current_job.robomaker_image,
                                                                name="robomaker",
                                                                network=network.id,
                                                                environment=current_job.docker_env,
                                                                ports={5900: 8000, 8080: 8080},
                                                                volumes={robomaker_data_dir: {'bind': '/root/.ros/',
                                                                                              'mode': 'rw'}},
                                                                detach=True,
                                                                remove=True)
