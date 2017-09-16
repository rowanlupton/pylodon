from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField, SelectField
from wtforms.validators import DataRequired

class userLogin(FlaskForm):
  handle = StringField('handle', validators=[DataRequired()])
  password = PasswordField('password', validators=[DataRequired()])

class userRegister(FlaskForm):
  handle = StringField('handle', validators=[DataRequired()])
  displayName = StringField('display name', validators=[DataRequired()])
  email = StringField('email', validators=[DataRequired()])
  password = PasswordField('password', validators=[DataRequired()])
  passwordConfirm = PasswordField('passwordConfirm', validators=[DataRequired()])



class composePost(FlaskForm):
  text = TextAreaField('post body', validators=[DataRequired()])
  to = TextAreaField('to')