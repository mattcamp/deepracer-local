import os
import docker
import time
import threading
import logging
import redis
from datetime import datetime

from manager import app, current_job, db
from manager.models import LocalModel
from .log_watchers import tail_robomaker_logs, tail_sagemaker_logs, tail_metrics, start_sagemaker_log_tail

client = docker.from_env()


def main_loop():
    while True:
        # app.logger.debug("in main loop")
        if current_job.local_model is not None:
            try:
                local_model = LocalModel.query.get(current_job.local_model_id)
                db.session.refresh(local_model)
                app.logger.debug(
                    "Status: {} {}: {} / {}".format(local_model.name,
                                                    local_model.status,
                                                    current_job.status['episode_number'],
                                                    current_job.minutes_target))

                if local_model.status == "training":
                    if local_model.start_timestamp:
                        td = datetime.now() - local_model.start_timestamp
                        minutes = divmod(td.seconds, 60)[0]
                        app.logger.info("Minutes trained: {} / {}".format(minutes, local_model.minutes_target))

                        if minutes != local_model.minutes_trained:
                            local_model.minutes_trained = minutes
                            db.session.commit()
                    # else:
                    #     app.logger.warning("Timestamp is {}".format(local_model.start_timestamp))

                    if minutes >= local_model.minutes_target:
                        app.logger.info(
                            "Target {} minutes reached at episode {}".format(minutes,
                                                                             current_job.status['episode_number']))
                        local_model.status = "complete"
                        db.session.commit()

                        stop_all_containers()
                        start_next_job()
            except Exception as e:
                app.logger.error("ERROR in main_loop: {}".format(e))
        else:
            pass
            # app.logger.debug("no current job, waiting")
        time.sleep(2)


def init_redis():
    redis_found = False
    for container in client.containers.list():
        if "redis" in container.attrs['Name']:
            redis_found = True

    if not redis_found:
        app.logger.info("Starting redis")
        network = init_docker_network()
        cwd = os.getcwd()
        redis_data_dir = "%s/data/redis" % cwd

        if not os.path.exists(redis_data_dir):
            os.mkdir(redis_data_dir)

        redis_image_found = False
        for image in client.images.list():
            if "redis:latest" in image.attrs['RepoTags']:
                redis_image_found = True

        if not redis_image_found:
            app.logger.info("Pulling redis:latest docker image")
            client.images.pull("redis:latest")
            app.logger.info("Docker pull complete")
        else:
            app.logger.info("Redis docker image found")

        redis_container = client.containers.run("redis:latest",
                                                name="redis",
                                                network=network.id,
                                                ports={6379: 6379},
                                                command="redis-server --appendonly yes",
                                                volumes={redis_data_dir: {'bind': '/data', 'mode': 'rw'}},
                                                detach=True,
                                                remove=True)
        app.logger.info("Redis started")
    else:
        app.logger.info("Redis already running")


def init_docker_network():
    networks = client.networks.list(names=['sagemaker-local'])
    if len(networks):
        network = networks[0]
        app.logger.info("Found docker network %s" % network.id)
    else:
        app.logger.info("Creating docker network")
        network = client.networks.create("sagemaker-local", driver="bridge", scope="local")

    return network


def write_training_params(filename):
    app.logger.info("Writing training_params.yaml into bucket")
    f = open(filename, "w+")
    for key, value in current_job.training_params.items():
        f.write("%s: \"%s\"\n" % (key, value))
    f.close()


def setup_bucket():
    try:
        cwd = os.getcwd()
        bucket_path = "{}/data/minio/bucket/{}-{}".format(cwd, current_job.local_model_id, current_job.local_model.name)
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
        if os.path.islink(latest_path):
            try:
                os.system("sudo rm %s" % latest_path)
            except:
                pass

        os.symlink(bucket_path, latest_path)

        write_training_params("%s/training_params.yaml" % bucket_path)

        metric_file = "%s/data/minio/bucket/DeepRacer-Metrics/TrainingMetrics.json" % cwd
        if os.path.exists(metric_file):
            try:
                os.system("sudo rm %s" % metric_file)
            except:
                pass

        os.mkdir("{}/logs".format(bucket_path))

    except Exception as e:
        app.logger.error("Error setting up bucket: {}".format(e))
        return False

    return True


def start_next_job():
    next_job = LocalModel.query.filter_by(status="queued").first()
    if next_job:
        app.logger.info("Starting next queued job: {}".format(next_job.name))
        start_training_job(next_job)
    else:
        app.logger.info("No queued jobs found")


def start_training_job(job):
    current_job.__init__()
    current_job.configure_from_queued_job(job)

    if setup_bucket():
        r = redis.Redis()
        try:
            r.delete("metrics-{}".format(current_job.local_model_id))
        except:
            pass

        start_all_containers()
        current_job.local_model.status = "training"
        db.session.commit()
    else:
        # Reset current_job
        current_job.__init__()


def start_all_containers():
    cwd = os.getcwd()
    network = init_docker_network()

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

        start_sagemaker_log_tail()

    if not current_job.robomaker_container:
        app.logger.info("Starting robomaker")
        robomaker_data_dir = "%s/data/robomaker" % cwd
        markov_dir = "%s/markov" % cwd
        current_job.robomaker_container = client.containers.run(current_job.robomaker_image,
                                                                name="robomaker",
                                                                network=network.id,
                                                                environment=current_job.docker_env,
                                                                ports={5900: 8000, 8080: 8080},
                                                                volumes={robomaker_data_dir: {'bind': '/root/.ros/',
                                                                                              'mode': 'rw'}
                                                                         # markov_dir: {
                                                                         #     'bind': '/opt/install/sagemaker_rl_agent/lib/python3.5/site-packages/markov/',
                                                                         #     'mode': 'rw'}
                                                                         },
                                                                detach=True,
                                                                remove=True)

        if current_job.robotail is None:
            current_job.robotail = threading.Thread(target=tail_robomaker_logs, args=(current_job.robomaker_container,))
            current_job.robotail.start()
        else:
            # robomaker tail thread exists, but is it alive?
            if not current_job.robotail.is_alive():
                current_job.robotail = threading.Thread(target=tail_robomaker_logs,
                                                        args=(current_job.robomaker_container,))
                current_job.robotail.start()

        if current_job.metricstail is None:
            current_job.metricstail = threading.Thread(target=tail_metrics)
            current_job.metricstail.start()
        else:
            if not current_job.metricstail.is_alive():
                current_job.metricstail = threading.Thread(target=tail_metrics)
                current_job.metricstail.start()


def stop_all_containers(minio=False):
    current_job.update_status()

    if current_job.local_model:
        current_job.local_model.status = "stopped"
        db.session.commit()
    else:
        app.logger.warning("No current_job.local_model")

    if current_job.sagemaker_container:
        try:
            app.logger.info("Stopping Sagemaker")
            current_job.sagemaker_container.kill()
            app.logger.info("Waiting for Sagemaker to exit")
            # wait 10 seconds for model.tar.gz to be written
            time.sleep(10)
        except:
            pass

    if current_job.robomaker_container:
        try:
            app.logger.info("Stopping Robomaker")
            current_job.robomaker_container.kill()
        except:
            pass
    if current_job.coach_container:
        try:
            app.logger.info("Stopping Coach")
            current_job.coach_container.kill()
        except:
            pass
    if minio:
        if current_job.minio_container:
            try:
                app.logger.info("Stopping Minio")
                current_job.minio_container.kill()
            except:
                pass


def check_if_already_running():
    app.logger.info("In check_if_already_running()")
    if not current_job:
        app.logger.warning("No current job")
        return 0

    current_job.update_status()

    if current_job.local_model is None:
        if current_job.robomaker_container and current_job.status['robomaker_status'] == "running":
            app.logger.info("Found running robomaker container")
        try:
            running_jobs = LocalModel.query.filter_by(status="training").all()
            print("Found {} jobs in training state".format(len(running_jobs)))
        except Exception as e:
            return 0

        if len(running_jobs) > 1:
            app.logger.error("Found {} jobs in training state! This should not happen!".format(len(running_jobs)))

        if len(running_jobs):
            current_job.configure_from_queued_job(running_jobs[0])

    if current_job.status['minio_status'] == "running" and current_job.status['coach_status'] == "running" and \
            current_job.status['robomaker_status'] == "running" and current_job.status['sagemaker_status'] == "running":
        app.logger.info("Found all running containers")

        if current_job.robotail is None:
            current_job.robotail = threading.Thread(target=tail_robomaker_logs, args=(current_job.robomaker_container,))
            current_job.robotail.start()
        else:
            if not current_job.robotail.is_alive():
                current_job.robotail = threading.Thread(target=tail_robomaker_logs,
                                                        args=(current_job.robomaker_container,))
                current_job.robotail.start()
            else:
                app.logger.info("Robomaker tail thread already running, not restarting")

        if current_job.metricstail is None:
            current_job.metricstail = threading.Thread(target=tail_metrics)
            current_job.metricstail.start()
        else:
            if not current_job.metricstail.is_alive():
                current_job.metricstail = threading.Thread(target=tail_metrics)
                current_job.metricstail.start()
            else:
                app.logger.info("Metrics tail thread already running, not restarting")

        start_sagemaker_log_tail()
        # if current_job.sagetail is None:
        #     app.logger.info("No sagemaker tail thread found, starting")
        #     current_job.sagetail = threading.Thread(target=tail_sagemaker_logs, args=(current_job.sagemaker_container,))
        #     current_job.sagetail.start()
        # else:
        #     if not current_job.sagetail.is_alive():
        #         app.logger.info("Sagetail thread found but not running, starting")
        #         current_job.sagetail = threading.Thread(target=tail_sagemaker_logs,
        #                                                 args=(current_job.sagemaker_container,))
        #         current_job.sagetail.start()
        #     else:
        #         app.logger.info("Sagemaker tail thread already running, not restarting")
    else:
        app.logger.info("Not all containers are running")
        app.logger.info("  Minio: {}".format(current_job.status['minio_status']))
        app.logger.info("  Robomaker: {}".format(current_job.status['robomaker_status']))
        app.logger.info("  Coach: {}".format(current_job.status['coach_status']))
        app.logger.info("  Sagemaker: {}".format(current_job.status['sagemaker_status']))
        jobs = LocalModel.query.filter_by(status="training").all()
        for job in jobs:
            app.logger.info("Setting previously training job {} as stopped".format(job.name))
            job.status = "stopped"
            db.session.commit()

    return 1
