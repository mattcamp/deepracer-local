from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired


class NewJobForm(FlaskForm):
    name = StringField('Job name', validators=[DataRequired()])
    race_type = SelectField('Race type', choices=[('TIME_TRIAL', "Time Trial"),
                                                  ('OBJECT_AVOIDANCE', 'Object Avoidance'),
                                                  ('HEAD_TO_BOT', "Head to Bot"),
                                                  ('HEAD_TO_MODEL', "Head to Model")])
    track = SelectField('Track', validators=[DataRequired()], default="LGSWide")
    reward_function_filename = SelectField('Reward Function filename', validators=[DataRequired()], default="reward.py")
    model_metadata_filename = SelectField('Model Metadata filename', validators=[DataRequired()],
                                          default="model_metadata.json")
    episodes = IntegerField('Episodes to train', default=1000)
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
    randomize_obstacle_locations = BooleanField('Random obstacle locations', false_values=(False, 'False', 'false', ''))
    change_start_position = BooleanField('Change start position', default=True, false_values=(False, 'False', 'false', ''))
    alternate_driving_direction = BooleanField('Alternate driving direction', default=False, false_values=(False, 'False', 'false', ''))
    pretrained_model = SelectField('Pre-trained model')
