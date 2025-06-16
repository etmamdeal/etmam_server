import json # Added for EditProductForm
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, BooleanField, SelectField, IntegerField # Added IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional # Added Optional
from flask_login import current_user
from models import User, Product, ProductType
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

class PropertyForm(FlaskForm):
    title = StringField('Property Title', validators=[DataRequired(), Length(min=5, max=200)])
    type = SelectField('Property Type',
                       choices=[
                           ('', '-- Select Type --'),
                           ('Residential', 'Residential (e.g., Apartment, Villa)'),
                           ('Commercial', 'Commercial (e.g., Office, Shop)'),
                           ('Land', 'Land'),
                           ('Other', 'Other')
                       ],
                       validators=[DataRequired(message="Please select a property type.")])
    price = FloatField('Price (SAR)', validators=[DataRequired(), NumberRange(min=0)])
    area = FloatField('Area (sqm)', validators=[Optional(), NumberRange(min=0)]) # Optional
    rooms = IntegerField('Number of Rooms', validators=[Optional(), NumberRange(min=0)]) # Optional
    description = TextAreaField('Description / Notes', validators=[Optional(), Length(max=5000)])
    # Latitude and Longitude will be handled by hidden fields in the template, not part of this WTForm directly
    submit = SubmitField('Save Property')

    def validate_type(self, field):
        if not field.data: # Handles the default empty choice
            raise ValidationError("Please select a valid property type.")


DEAL_STAGES = [
    ('New Lead', 'New Lead'),
    ('Showing Scheduled', 'Showing Scheduled'),
    ('Negotiation', 'Negotiation'),
    ('Contract Signing', 'Contract Signing'),
    ('Pending - Finance/Inspection', 'Pending - Finance/Inspection'),
    ('Closed - Won', 'Closed - Won'),
    ('Closed - Lost', 'Closed - Lost'),
    ('On Hold', 'On Hold')
]

class DealForm(FlaskForm):
    property_id = SelectField('Associated Property', coerce=int, validators=[DataRequired(message="Please select a property.")])
    client_name = StringField('Client Name (Buyer/Renter)', validators=[DataRequired(), Length(min=2, max=120)])
    stage = SelectField('Deal Stage', choices=DEAL_STAGES, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Save Deal')
