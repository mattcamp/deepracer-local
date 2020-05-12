from flask_wtf import FlaskForm, form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Optional
import wtforms


class NewJobForm(FlaskForm):
    name = StringField('Job name', validators=[DataRequired()])
    description = StringField('Description')
    race_type = SelectField('Race type', choices=[('TIME_TRIAL', "Time Trial"),
                                                  ('OBJECT_AVOIDANCE', 'Object Avoidance'),
                                                  ('HEAD_TO_BOT', "Head to Bot"),
                                                  ('HEAD_TO_MODEL', "Head to Model")])
    track = SelectField('Track', validators=[DataRequired()], default="LGSWide")
    reward_function_filename = SelectField('Reward Function filename', validators=[DataRequired()], default="reward.py")
    model_metadata_filename = SelectField('Action space filename', validators=[DataRequired()],
                                          default="model_metadata.json")
    # episodes = IntegerField('Episodes to train', validators=[Optional()])
    minutes_target = IntegerField('Minutes to train', validators=[DataRequired()])
    episodes_between_training = IntegerField('Episodes between training', default=20)
    batch_size = IntegerField('Batch Size', default=10)
    epochs = IntegerField('Epochs', default=10)
    learning_rate = FloatField('Learning Rate', default=0.0003)
    entropy = FloatField('Entropy', default=0.01)
    discount_factor = FloatField('Discount Factor', default=0.999)
    loss_type = SelectField('Loss Type', default="mean squared error",
                            choices=[('mean squared error', 'mean squared error'),
                                     ('huber', 'huber')])
    number_of_obstacles = IntegerField('Number of obstacles', default=0)
    randomize_obstacle_locations = BooleanField('Random obstacle locations')
    change_start_position = BooleanField('Change start position', default="checked")
    alternate_direction = BooleanField('Alternate driving direction')
    pretrained_model = SelectField('Pre-trained model', validators=[Optional()])

    # TODO: construct model_metadata dynamically
    # nn_layers = SelectField('NN Layers', choices=[(3,3), (5,5)])
    # sensor_stereo_cameras = BooleanField('Stereo cameras')
    # sensor_lidar = BooleanField('LIDAR')

    number_of_bot_cars = IntegerField('Number of bot cars', default=0)
    bot_car_speed = FloatField('Bot car speed', default=1.0)
    is_lane_change = BooleanField('Bot cars change lanes')
    upper_lane_change_time = IntegerField('Max lane change interval', default=5)
    lower_lane_change_time = IntegerField('Min lane change interval', default=5)
