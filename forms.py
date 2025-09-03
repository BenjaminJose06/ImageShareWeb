
# Image Upload Form
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField  
from wtforms.validators import DataRequired, Length, ValidationError 
import re
from models import User

class UploadImageForm(FlaskForm):
    name = StringField('Image Name', validators=[DataRequired(), Length(min=1, max=100)])
    image = FileField('Image File', validators=[FileRequired(), FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!')])
    submit = SubmitField('Upload')

# Custom email validation function
def validate_email(form, field):
    """
    Ensures the email follows a valid email format using regex.
    Raises a ValidationError if the email format is invalid.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, field.data):
        raise ValidationError("Invalid email format. Please enter a valid email address.")

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), validate_email])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("Username already taken. Please choose another.")
    
    def validate_email(self, email):
        existing_user = User.query.filter_by(email=email.data).first()
        if existing_user:
            raise ValidationError("Email is already registered. Please use a different email.")


# Login Form
class LoginForm(FlaskForm):
    """
    Form for user login.
    Allows login with either email or username.
    """
    email_or_username = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

# Password Reset Request Form
class RequestResetForm(FlaskForm):
    """
    Form to request a password reset.
    Requires the user to enter their registered email.
    """
    email = StringField('Email', validators=[DataRequired(), validate_email]) 
    submit = SubmitField('Request Password Reset')

# Password Reset Form
class ResetPasswordForm(FlaskForm):
    """
    Form to reset the user's password.
    Includes password confirmation for security.
    """
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')

# Change Email Form
class ChangeEmailForm(FlaskForm):
    """
    Form to allow users to change their email address.
    """
    new_email = StringField('New Email', validators=[DataRequired(), validate_email])
    submit = SubmitField('Change Email')

# Change Password Form
class ChangePasswordForm(FlaskForm):
    """
    Form to allow users to change their password.
    Requires entering the current password and a new password.
    """
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Change Password')
