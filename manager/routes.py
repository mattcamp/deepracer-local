from manager import app, db, current_job, csrf
from flask import render_template, request, redirect, jsonify
from random import random
from manager.forms import NewJobForm
from manager.models import LocalModel
from manager.utils import start_training_job, stop_all_containers
from os import getcwd, listdir
import json
from os.path import isfile, isdir, join
import redis

track_choices = [
    ("July_2020", "July 2020"),
    ("Spain_track", "Circuit de Barcelona-Catalunya"),
    ("AmericasGeneratedInclStart", "Baadal"),
    ("LGSWide", "SOLA Speedway"),
    ("Bowtie_track", "Bowtie"),
    ("Canada_Training", "Toronto Turnpike"),
    ("China_track", "Shanghai Sudu"),
    ("Mexico_track", "Cumulo Carrera"),
    ("New_York_Track", "Empire City"),
    ("Oval_track", "Oval"),
    ("reInvent2019_track", "2019 Championship cup"),
    ("reInvent2019_wide_mirrored", "2019 Championship cup wide mirrored"),
    ("reInvent2019_wide", "2019 Championship cup wide"),
    ("reinvent_base", "re:Invent 2018"),
    ("Straight_track", "Straight"),
    ("Tokyo_Training_track", "Kumo Torakku"),
    ("Vegas_track", "AWS Summit Raceway"),
    ("Virtual_May19_Train_track", "London Loop")

]


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1", "y")


def listRewardFuncFiles():
    cwd = getcwd()
    bucketpath = "{}/data/minio/bucket".format(cwd)
    customfiles_dir = "{}/custom_files".format(bucketpath)
    reward_func_files = []

    for cf in listdir(customfiles_dir):
        if isfile(join(customfiles_dir, cf)):
            if ".py" in cf:
                reward_func_files.append((cf, cf))

    return reward_func_files


def listMetadataFiles():
    cwd = getcwd()
    bucketpath = "{}/data/minio/bucket".format(cwd)
    customfiles_dir = "{}/custom_files".format(bucketpath)
    metadata_files = []

    for cf in listdir(customfiles_dir):
        if isfile(join(customfiles_dir, cf)):
            if ".json" in cf:
                metadata_files.append((cf, cf))

    return metadata_files


def listModelDirs():
    cwd = getcwd()
    bucketpath = "{}/data/minio/bucket".format(cwd)
    modeldirs = [('None', '----')]
    exclude_dirs = ["DeepRacer-Metrics", "custom_files"]

    for f in listdir(bucketpath):
        if isdir(join(bucketpath, f)):
            if f not in exclude_dirs:
                modeldirs.append((f, f))

    queued_models = LocalModel.query.filter_by(status="queued").all()
    for qm in queued_models:
        modeldirs.append(("{}-{}".format(qm.id, qm.name), "{}-{}".format(qm.id, qm.name)))

    return modeldirs


@app.route('/')
@app.route('/index')
def index():
    tracks = [
        "AWS_track",
        "Bowtie_track",
        "Canada_Training",
        "China_track",
        "LGSWide",
        "Mexico_track",
        "New_York_Track",
        "Oval_track",
        "reInvent2019_track",
        "reInvent2019_wide_mirrored",
        "reInvent2019_wide",
        "reinvent_base_jeremiah",
        "reinvent_base",
        "reinvent_carpet",
        "reinvent_concrete",
        "reinvent_wood",
        "Straight_track",
        "Tokyo_Training_track",
        "Vegas_track",
        "Virtual_May19_Train_track",
        "AmericasGeneratedInclStart"
    ]

    form = NewJobForm()
    form.track.choices = track_choices
    form.pretrained_model.choices = listModelDirs()
    form.model_metadata_filename.choices = listMetadataFiles()
    form.reward_function_filename.choices = listRewardFuncFiles()
    print(form.change_start_position)
    return render_template('index.html', form=form)


@app.route('/models', methods=["GET", "POST"])
def models():
    if request.method == "POST":
        form = NewJobForm(request.form)
        form.track.choices = track_choices
        form.pretrained_model.choices = listModelDirs()
        form.model_metadata_filename.choices = listMetadataFiles()
        form.reward_function_filename.choices = listRewardFuncFiles()
        # form.nn_layers.choices = [(3,3), (5,5)]

        if form.validate_on_submit():
            app.logger.debug("/models POST form is valid: {}".format(form.data))
        else:
            app.logger.error("validation failed: {}".format(form.errors))
            return (jsonify(form.errors), 400)

        data = request.form.to_dict(flat=True)
        del data['csrf_token']
        app.logger.debug("Saving job: %s" % data)

        if data['id']:
            app.logger.debug("Editing job {}".format(data['id']))
            this_model = LocalModel.query.get(data['id'])

            if this_model.status != "queued":
                return "Cannot edit job once training has started", 400
        else:
            this_model = LocalModel()

        if not data['name']:
            return ("Must provide job name", 400)
        if not data['track']:
            return ("Must provide track", 400)
        if not data['model_metadata_filename']:
            return ("Must provide model metadata filename", 400)
        if not data['reward_function_filename']:
            return ("Must provide reward function filename", 400)

        if data['minutes_target'] != '' and int(data['minutes_target']) > 0:
            this_model.minutes_target = int(data['minutes_target'])
        else:
            return ("Must provide target minutes", 400)

        this_model.name = data['name']
        this_model.description = data['description']
        this_model.race_type = data['race_type']
        this_model.track = data['track']
        this_model.reward_function_filename = data['reward_function_filename']
        this_model.model_metadata_filename = data['model_metadata_filename']
        this_model.episodes_between_training = int(data['episodes_between_training'])
        this_model.batch_size = int(data['batch_size'])
        this_model.epochs = int(data['epochs'])
        this_model.learning_rate = float(data['learning_rate'])
        this_model.entropy = float(data['entropy'])
        this_model.discount_factor = float(data['discount_factor'])
        this_model.loss_type = data['loss_type']
        this_model.number_of_obstacles = data['number_of_obstacles']
        this_model.randomize_obstacle_locations = str2bool(data['randomize_obstacle_locations'])

        app.logger.debug(
            "change_start: {}={}".format(data['change_start_position'], str2bool(data['change_start_position'])))
        app.logger.debug("alternate_direction: {}={}".format(data['alternate_direction'],
                                                             str2bool(data['alternate_direction'])))

        this_model.change_start_position = str2bool(data['change_start_position'])
        this_model.alternate_direction = str2bool(data['alternate_direction'])
        this_model.pretrained_model = data['pretrained_model']

        db.session.add(this_model)
        db.session.commit()

        if this_model:
            # jobs = LocalModel.query.all()
            return ("OK", 200)
        else:
            return ("Failed to save new job", 500)

    else:
        all_models = LocalModel.query.all()
        models_array = []
        for this_model in all_models:
            models_array.append(this_model.as_dict())
        return jsonify(models_array)


@app.route('/model/<model_id>', methods=["GET", "POST", "DELETE"])
def model(model_id):
    if not model_id:
        return "Model not found", 404

    if request.method == "DELETE":
        app.logger.info("Got delete for model {}".format(model_id))
        model_to_delete = LocalModel.query.filter_by(id=model_id).first()
        if model_to_delete:
            app.logger.info("Found model: {}".format(model_to_delete))
            if current_job.local_model == model_to_delete:
                current_job.local_model = None
            db.session.delete(model_to_delete)
            db.session.commit()
            # TODO: Delete metrics
        return "OK", 200

    if request.method == "GET":
        this_model = LocalModel.query.get(model_id)
        return jsonify(this_model.as_dict())


@app.route('/current_job', methods=["GET", "POST"])
def current_training_job():
    if request.method == "POST":
        request_data = request.json
        if request_data['action'] == "start_training":
            app.logger.info("Starting training session")
            current_job.desired_state = "running"
            current_job.update_status()
            if not current_job.status['sagemaker_status'] and not current_job.status['robomaker_status']:
                app.logger.info("ok to start")
                first_model = LocalModel.query.filter_by(status='queued').first()
                if first_model:
                    start_training_job(first_model)
                else:
                    app.logger.warning("Start button clicked but no models in queued state")
                    return "No queued models", 400
            else:
                app.logger.info("Not ok to start")
                return "not ready", 412

        if request_data['action'] == "stop_training":
            app.logger.info("Stop training requested")
            current_job.desired_state = "stopped"
            try:
                local_model = LocalModel.query.get(current_job.local_model_id)
                db.session.refresh(local_model)
                local_model.status = "stopped"
                db.session.commit()
            except Exception as e:
                app.logger.error("Error while stopping: {}".format(e))

            stop_all_containers()

        return "OK"
    else:
        current_job.update_status()
        return jsonify(current_job.status)


# @app.route('/metrics', methods=["GET"])
# def get_metrics():
#     from_episode = request.args.get('from_episode', -1)
#     metrics_to_return = []
#     for metric in current_job.metrics:
#         if metric['phase'] == "training" and metric['episode'] > int(from_episode):
#             metrics_to_return.append(metric)
#             print(metric)
#
#         if metric['phase'] == "evaluation" and metric['episode'] >= int(from_episode):
#             metrics_to_return.append(metric)
#             print(metric)
#
#     return jsonify(metrics_to_return)


@app.route('/metrics/<model_id>', methods=["GET"])
def get_metrics(model_id):
    from_episode = request.args.get('from_episode', -1)
    metrics_to_return = []
    r = redis.Redis()

    key = "metrics-{}".format(model_id)
    for i in range(0, r.llen(key)):
        metric = json.loads(r.lindex(key, i).decode("utf-8"))

        if metric['phase'] == "training" and metric['episode'] > int(from_episode):
            metrics_to_return.append(metric)
            # print(metric)

        if metric['phase'] == "evaluation" and metric['episode'] >= int(from_episode):
            metrics_to_return.append(metric)
            # print(metric)

    return jsonify(metrics_to_return)


# TODO: Calculate and store averaged metrics server-side?
# @app.route('/metrics_averaged/<model_id>', methods=["GET"])
# def get_metrics_averaged(model_id):
#     from_episode = request.args.get('from_episode', -1)
#     metrics_to_return = []
#     r = redis.Redis()
#
#     key = "metrics-{}".format(model_id)
#     for i in range(0, r.llen(key)):
#         metric = json.loads(r.lindex(key, i).decode("utf-8"))
#
#         if metric['phase'] == "training" and metric['episode'] > int(from_episode):
#             metrics_to_return.append(metric)
#             # print(metric)
#
#         if metric['phase'] == "evaluation" and metric['episode'] >= int(from_episode):
#             metrics_to_return.append(metric)
#             # print(metric)
#
#     return jsonify(metrics_to_return)


@app.route('/pretrained_dirs', methods=["GET"])
def pretrained_dirs():
    cwd = getcwd()
    bucketpath = "{}/data/minio/bucket".format(cwd)
    modeldirs = [('None', '----')]
    exclude_dirs = ["DeepRacer-Metrics", "custom_files"]

    for f in listdir(bucketpath):
        if isdir(join(bucketpath, f)):
            if f not in exclude_dirs:
                modeldirs.append({"value": f, "text": f})

    queued_models = LocalModel.query.filter_by(status="queued").all()
    for qm in queued_models:
        modeldirs.append({"value": "{}-{}".format(qm.id, qm.name), "text": "{}-{}".format(qm.id, qm.name)})

    return jsonify(modeldirs)
