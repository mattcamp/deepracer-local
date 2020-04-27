import os
import docker
import time
import threading
import re
import json
import logging
from manager import app, current_job, db
from manager.models import TrainingJob
import redis
from datetime import datetime

client = docker.from_env()

def tail_robomaker_logs(robomaker):
    app.robologger.info("IN TAIL_ROBOMAKER_LOGS")

    cwd = os.getcwd()
    logs_path = "%s/data/minio/bucket/%s/logs" % (cwd, current_job.training_job.name)
    if not os.path.exists(logs_path):
        app.logger.info("Creating logs directory: {}".format(logs_path))
        try:
            os.mkdir(logs_path)
        except Exception as e:
            app.logger.error("Failed to create logs dir: {}".format(e))

    log_file = "{}/robomaker.log".format(logs_path)
    handler = logging.FileHandler(log_file)
    app.robologger.addHandler(handler)

    line = ""
    generator = robomaker.logs(stream=True, follow=True)
    for line in generator:
        if line.decode('utf-8').strip('\n') != "":
            app.robologger.info("%s" % line.decode('utf-8').strip('\n'))

    app.robologger.info("tail_robomaker_logs() exiting")


def start_sagemaker_log_tail():
    app.sagelogger.info("in start_sagemaker_log_tail()")

    while not current_job.sagemaker_container:
        app.sagelogger.warning("No sagemaker yet... waiting")
        current_job.update_status()
        time.sleep(1)

    cwd = os.getcwd()
    logs_path = "%s/data/minio/bucket/%s/logs" % (cwd, current_job.training_job.name)
    if not os.path.exists(logs_path):
        app.logger.info("Creating logs directory: {}".format(logs_path))
        try:
            os.mkdir(logs_path)
        except Exception as e:
            app.logger.error("Failed to create logs dir: {}".format(e))

    log_file = "{}/sagemaker.log".format(logs_path)
    handler = logging.FileHandler(log_file)
    app.sagelogger.addHandler(handler)

    if current_job.sagetail is None:
        app.sagelogger.info("No sagetail found")
        current_job.sagetail = threading.Thread(target=tail_sagemaker_logs, args=(current_job.sagemaker_container,))
        current_job.sagetail.start()
    else:
        if not current_job.sagetail.is_alive():
            app.sagelogger.info("Sagetail found but not alive")
            current_job.sagetail = threading.Thread(target=tail_sagemaker_logs, args=(current_job.sagemaker_container,))
            current_job.sagetail.start()
        else:
            app.sagelogger.info("Sagetail OK")


def tail_sagemaker_logs(sagemaker):
    app.sagelogger.info("IN TAIL_SAGEMAKER_LOGS")

    generator = sagemaker.logs(stream=True, follow=True, tail=250)

    line = ""
    for char in generator:
        line = line + char.decode("utf-8")
        if char == b"\n":
            app.sagelogger.info("{}".format(line.strip()))

            # Training> Name=main_level/agent, Worker=0, Episode=1134, Total reward=13.07, Steps=18594, Training iteration=56

            # Policy training> Surrogate loss=-0.08529137820005417, KL divergence=0.290351539850235, Entropy=0.8986915946006775, training epoch=2, learning_rate=0.0003
            # Best checkpoint number: 47, Last checkpoint number: 55

            m = re.match(
                r"Training> Name=main_level/agent, Worker=(\d+), Episode=(\d+), Total reward=(\d+).\d+, Steps=(\d+), Training iteration=(\d+)",
                line)
            if m:
                # print("Matched sagemaker line")
                current_job.status['episode_number'] = int(m.groups(2)[1])
                current_job.status['iteration_number'] = int(m.groups(2)[4])
                if current_job.training_job:
                    tj = TrainingJob.query.get(current_job.training_job_id)
                    tj.episodes_trained = int(m.groups(2)[1])

                    app.logger.debug("start_timestamp: {}".format(tj.start_timestamp))
                    if not tj.start_timestamp:
                        app.logger.info("Setting start_timestamp to now")
                        tj.start_timestamp = datetime.now()

                    db.session.commit()
                else:
                    app.sagelogger.warning("no current_job found, not writing episode count")

            m = re.match(
                r"Policy training> Surrogate loss=(-?\d+\.\d+), KL divergence=(-?\d+\.\d+), Entropy=(-?\d+\.\d+), training epoch=(\d+), learning_rate=(\d+\.\d+)",
                line)
            if m:
                current_job.entropy_metrics.append({"iteration": current_job.status['iteration_number'],
                                                    "entropy": float(m.groups(2)[2]),
                                                    "epoch": int(m.groups(2)[3])
                                                    })
                app.logger.debug("POLICY TRAINING: Iteration {}\tEntropy: {}\tEpoch: {}".format(current_job.status['iteration_number'], float(m.groups(2)[2]), int(m.groups(2)[3])))

            m = re.match(r"Best checkpoint number: (\d+), Last checkpoint number: (\d+)", line)
            if m:
                current_job.status['best_checkpoint'] = int(m.groups(2)[0])
                app.logger.debug("Best checkpoint now {}".format(current_job.status['best_checkpoint']))

            line = ""

        # line = line + char.decode("utf-8")

    app.sagelogger.info("***EXIT*** tail_sagemaker_logs() exiting")


def tail_metrics():
    app.logger.info("IN tail_metrics()")
    r = redis.Redis()
    cwd = os.getcwd()
    logfile = "%s/data/minio/bucket/DeepRacer-Metrics/TrainingMetrics.json" % cwd

    while not os.path.exists(logfile):
        time.sleep(1)

    app.logger.info("Found metrics file")

    last_position = 0
    while True:
        try:
            with open(logfile) as f:
                f.seek(last_position)
                new_data = f.read()
                last_position = f.tell()

            if new_data != "":
                try:
                    metric = json.loads(new_data[:-2])

                    if metric["episode_status"] == "Lap complete":
                        job = TrainingJob.query.get(current_job.training_job_id)
                        db.session.refresh(job)
                        job.laps_complete += 1
                        if float(metric["elapsed_time_in_milliseconds"])/1000 > job.best_lap_time:
                            job.best_lap_time = float(metric["elapsed_time_in_milliseconds"])/1000
                        db.session.commit()

                    current_job.metrics.append(metric)
                    metric["job"] = current_job.training_job_id
                    key = "metrics-{}".format(current_job.training_job_id)

                    app.logger.debug("METRIC: %s" % metric)
                    r.rpush(key, json.dumps(metric))
                except Exception as e:
                    app.logger.error("Error decoding JSON metric: %s (This is OK during startup)" % e)
        except:
            pass

        time.sleep(1)
