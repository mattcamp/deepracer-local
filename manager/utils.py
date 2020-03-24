import os
import shutil
import docker
import time
import threading
import re
import json
from pygtail import Pygtail
from manager import app, current_job, db
from manager.models import TrainingJob

client = docker.from_env()


def write_training_params(filename):
    app.logger.info("Writing training_params.yaml into bucket")
    f = open(filename, "w+")
    for key, value in current_job.training_params.items():
        f.write("%s: \"%s\"\n" % (key, value))
    f.close()


def setup_bucket():
    cwd = os.getcwd()
    bucket_path = "%s/data/minio/bucket/%s" % (cwd, current_job.training_job.name)
    if os.path.exists(bucket_path):
        app.logger.info("Path exists: %s" % bucket_path)
        old_bucket_path = "%s.old" % bucket_path
        if os.path.exists(old_bucket_path):
            app.logger.info("Old path exists, removing: %s" % old_bucket_path)
            os.system("sudo rm -rf %s" % old_bucket_path)
        os.rename(bucket_path, old_bucket_path)

    app.logger.info("Creating bucket directory: %s" % bucket_path)
    os.mkdir(bucket_path)

    latest_path = "%s/data/minio/bucket/latest" % cwd
    if os.path.exists(latest_path):
        os.remove(latest_path)

    os.symlink(bucket_path, latest_path)

    write_training_params("%s/training_params.yaml" % bucket_path)

    metric_file = "%s/data/minio/bucket/DeepRacer-Metrics/TrainingMetrics.json" % cwd
    os.system("sudo rm %s" % metric_file)


def start_training_job():
    current_job.__init__()
    first_job = TrainingJob.query.filter_by(status='queued').first()
    current_job.configure_from_queued_job(first_job)
    setup_bucket()
    start_all_containers()
    current_job.training_job.status = "training"
    db.session.commit()


def start_all_containers():
    cwd = os.getcwd()
    networks = client.networks.list(names=['sagemaker-local'])
    if len(networks):
        network = networks[0]
        app.logger.info("found network %s" % network.id)
    else:
        app.logger.info("Creating docker network")
        network = client.networks.create("sagemaker-local", driver="bridge", scope="local")

    if not current_job.minio_container:
        app.logger.info("Starting minio")
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

    app.logger.info("Waiting for minio to start")
    while current_job.minio_container.attrs['State']['Status'] != "running":
        current_job.minio_container.reload()
        # current_job.update_status()
        app.logger.info(current_job.minio_container.attrs['State']['Status'])
        time.sleep(1)

    if not current_job.coach_container:
        app.logger.info("Starting coach")
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
        coach_tail = threading.Thread(target=tail_sagemaker_logs, args=(current_job.coach_container,))
        coach_tail.start()

    if not current_job.robomaker_container:
        app.logger.info("Starting robomaker")
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
        robomaker_tail = threading.Thread(target=tail_robomaker_logs, args=(current_job.robomaker_container,))
        robomaker_tail.start()

        metrics_tail = threading.Thread(target=tail_metrics)
        metrics_tail.start()


def stop_all_containers(minio=False):
    current_job.update_status()
    current_job.training_job.status = "stopped"
    db.session.commit()

    if current_job.sagemaker_container:
        try:
            current_job.sagemaker_container.kill()
            # wait 10 seconds for model.tar.gz to be written
            time.sleep(10)
        except:
            pass

    if current_job.robomaker_container:
        try:
            current_job.robomaker_container.kill()
        except:
            pass
    if current_job.coach_container:
        try:
            current_job.coach_container.kill()
        except:
            pass
    if minio:
        if current_job.minio_container:
            try:
                current_job.minio_container.kill()
            except:
                pass




def tail_robomaker_logs(robomaker):
    app.logger.info("IN TAIL_ROBOMAKER_LOGS")
    line = ""
    generator = robomaker.logs(stream=True, follow=True)
    for line in generator:
        if line != "":
            pass
            # app.logger.info("ROBOMAKER: %s" % line.decode('utf-8').strip('\n'))

    app.logger.info("tail_robomaker_logs() exiting")


def tail_sagemaker_logs(sagemaker):
    app.logger.info("IN TAIL_SAGEMAKER_LOGS")
    line = ""
    generator = sagemaker.logs(stream=True, follow=True, tail=250)
    # for line in generator:
    #     app.logger.info("SAGEMAKER: %s" % line.decode('utf-8').strip('\n'))

    line = ""
    for char in generator:
        # print(char.decode("utf-8"))
        if char == b"\n":
            # print(char.decode("utf-8"))
            # print("===========")
            # app.logger.info("SAGEMAKER: %s" % line.strip())

            # Training> Name=main_level/agent, Worker=0, Episode=1134, Total reward=13.07, Steps=18594, Training iteration=56
            # Policy training> Surrogate loss=-0.08529137820005417, KL divergence=0.290351539850235, Entropy=0.8986915946006775, training epoch=2, learning_rate=0.0003
            # Best checkpoint number: 47, Last checkpoint number: 55

            m = re.match(
                r"Training> Name=main_level/agent, Worker=(\d+), Episode=(\d+), Total reward=(\d+).\d+, Steps=(\d+), Training iteration=(\d+)",
                line)
            if m:
                current_job.status['episode_number'] = int(m.groups(2)[1])
                current_job.status['iteration_number'] = int(m.groups(2)[4])
                current_job.training_job.episodes_trained = current_job.status['episode_number']
                db.session.commit()

            m = re.match(
                r"Policy training> Surrogate loss=(-?\d+\.\d+), KL divergence=(-?\d+\.\d+), Entropy=(-?\d+\.\d+), training epoch=(\d+), learning_rate=(\d+\.\d+)",
                line)
            if m:
                current_job.entropy_metrics.append({"iteration": current_job.status['iteration_number'],
                                                    "entropy": float(m.groups(2)[2]),
                                                    "epoch": int(m.groups(2)[3])
                                                    })

            m = re.match(r"Best checkpoint number: (\d+), Last checkpoint number: (\d+)", line)
            if m:
                current_job.status['best_checkpoint'] = int(m.groups(2)[0])

            line = ""
        else:
            line = line + char.decode("utf-8")

    app.logger.info("tail_sagemaker_logs() exiting")


def tail_metrics():
    app.logger.info("IN tail_metrics()")
    cwd = os.getcwd()
    logfile = "%s/data/minio/bucket/DeepRacer-Metrics/TrainingMetrics.json" % cwd

    while not os.path.exists(logfile):
        time.sleep(1)

    app.logger.info("Found metrics file")

    last_position = 0
    while True:
        with open(logfile) as f:
            f.seek(last_position)
            new_data = f.read()
            last_position = f.tell()

        if new_data != "":
            try:
                metric = json.loads(new_data[:-2])
                current_job.metrics.append(metric)
                app.logger.info("METRIC: %s" % metric)
            except Exception as e:
                app.logger.info("ERROR Json decoding metric: %s" % e)

        time.sleep(1)


def check_if_already_running():
    current_job.update_status()
    if current_job.status['minio_status'] == "running" and current_job.status['coach_status'] == "running" and \
            current_job.status['robomaker_status'] == "running" and current_job.status['sagemaker_status'] == "running":
        app.logger.info("Found all running containers")

        robomaker_tail = threading.Thread(target=tail_robomaker_logs, args=(current_job.robomaker_container,))
        robomaker_tail.start()

        metrics_tail = threading.Thread(target=tail_metrics)
        metrics_tail.start()

        sagemaker_tail = threading.Thread(target=tail_sagemaker_logs, args=(current_job.sagemaker_container,))
        sagemaker_tail.start()

    return 1
