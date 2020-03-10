from manager import app
from flask import render_template, request, redirect, jsonify
from random import random
from manager.forms import NewJobForm
from manager.models import TrainingJob
from manager import db
from manager import current_job
from manager.utils import start_training_job
import json


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


@app.route('/')
@app.route('/index')
def index():
    form = NewJobForm()
    return render_template('index.html', form=form)


@app.route('/jobs', methods=["GET", "POST"])
def jobs():
    if request.method == "POST":
        form = NewJobForm()
        data = request.form.to_dict(flat=True)
        del data['csrf_token']
        print("Adding new job: %s" % data)
        if not data['name']:
            return ("Must provide name", 400)
        if not data['track']:
            return ("Must provide track", 400)
        if not data['model_metadata_filename']:
            return ("Must provide model metadata filename", 400)
        if not data['reward_function_filename']:
            return ("Must provide reward function filename", 400)

        newjob = TrainingJob(name=data['name'],
                             race_type=data['race_type'],
                             track=data['track'],
                             reward_function_filename=data['reward_function_filename'],
                             model_metadata_filename=data['model_metadata_filename'],
                             episodes=int(data['episodes']),
                             episodes_between_training=int(data['episodes_between_training']),
                             batch_size=int(data['batch_size']),
                             epochs=int(data['epochs']),
                             learning_rate=float(data['learning_rate']),
                             entropy=float(data['entropy']),
                             discount_factor=float(data['discount_factor']),
                             loss_type=data['loss_type'],
                             number_of_obstacles=data['number_of_obstacles'],
                             randomize_obstacle_locations=str2bool(data['randomize_obstacle_locations']),
                             change_start_position=str2bool(data['change_start_position']),
                             alternate_direction=str2bool(data['alternate_driving_direction']),
                             pretrained_model=data['pretrained_model']
                             )
        db.session.add(newjob)
        db.session.commit()

        if newjob:
            jobs = TrainingJob.query.all()
            print(jobs)
            return ("OK", 200)
        else:
            return ("Failed to save new job", 500)

    else:
        jobs = TrainingJob.query.all()
        jobs_array = []
        for job in jobs:
            jobs_array.append(job.as_dict())
            print(job.as_dict())
        return jsonify(jobs_array)


@app.route('/current_job', methods=["GET", "POST"])
def current_training_job():
    if request.method == "POST":
        request_data = request.json
        if request_data['action'] == "start_training":
            print("Starting training session")
            current_job.update_status()
            if not current_job.status['sagemaker_status'] and not current_job.status['robomaker_status']:
                print("ok to start")
                start_training_job()
            else:
                print("Not ok to start")
                return "not ready", 412

        return "OK"
    else:
        current_job.update_status()
        return jsonify(current_job.status)
