import os
import sys
import logging
import threading
import redis
import click

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from manager.currentjob import CurrentJob


def setup_logger(name, log_file, level=os.environ.get("LOGLEVEL", "INFO"), plain=True, stdout=False):
    if plain:
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    handler = logging.FileHandler(log_file)
    stdout_handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    if stdout:
        logger.addHandler(stdout_handler)

    return logger


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), filename="manager/logs/manager.log")
app.logger = setup_logger('main_logger', 'manager/logs/manager.log', plain=False, stdout=True)
app.robologger = setup_logger('robomaker_logger', 'manager/logs/robomaker.log', plain=False)  # TODO: Change to True
app.sagelogger = setup_logger('sagemaker_logger', 'manager/logs/sagemaker.log', plain=False)  #  TODO: Change to True

app.config['SECRET_KEY'] = os.urandom(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'manager.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
db.init_app(app)


if click.get_current_context().command.name == "run":
    current_job = CurrentJob()

    from manager import routes, models
    from manager.utils import check_if_already_running, start_next_job, stop_all_containers, main_loop, init_redis

    # session = db.session()
    # print(session.expire_on_commit)
    # session.expire_on_commit=True

    models.BaseModel.set_session(db.session)

    init_redis()
    app.redis = redis.Redis()

    check_if_already_running()
    app.logger.info("Startup complete")

    last_status = None

    main_loop_thread = threading.Thread(target=main_loop)
    main_loop_thread.start()

