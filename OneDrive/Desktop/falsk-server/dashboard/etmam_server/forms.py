import json # Added for EditProductForm
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, BooleanField, SelectField # Added TextAreaField, FloatField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange # Added NumberRange
from flask_login import current_user
from models import User, Product, ProductType # Added Product, ProductType
from werkzeug.security import check_password_hash


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Length(min=10, max=20)]) # Basic length validation
    submit_profile = SubmitField('Update Profile')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already taken by another account.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password',
                                        validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')])
    submit_password = SubmitField('Change Password')

    def validate_current_password(self, current_password):
        if not current_user.is_authenticated or not hasattr(current_user, 'password'): # Ensure current_user is valid and has password
            raise ValidationError('Authentication error.') # Or handle as appropriate
        if not check_password_hash(current_user.password, current_password.data):
            raise ValidationError('Incorrect current password.')

class EditProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price (SAR)', validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField('Product Active (visible in store)')
    script_parameters = TextAreaField('Script Parameters (JSON)',
                                     description="Edit parameters if this is a Script product. Must be valid JSON.",
                                     render_kw={"rows": 5})
    submit = SubmitField('Update Product')

    def validate_script_parameters(self, script_parameters):
        if script_parameters.data and script_parameters.data.strip():
            try:
                json.loads(script_parameters.data)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format for script parameters.')
