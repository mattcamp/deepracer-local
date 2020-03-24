import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from manager.current_job import CurrentJob


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

app.config['SECRET_KEY'] = os.urandom(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'manager.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
db.init_app(app)


current_job = CurrentJob()

from manager import routes, models
from manager.utils import check_if_already_running

models.BaseModel.set_session(db.session)

check_if_already_running()
app.logger.info("Startup complete")
