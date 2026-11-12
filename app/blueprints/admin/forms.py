"""Forms for the admin blueprint."""
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class CategoryForm(FlaskForm):
    """Form for creating or editing item categories."""

    category_name = StringField(
        'Category Name',
        validators=[
            DataRequired(message='Category name is required.'),
            Length(min=2, max=80, message='Category name must be between 2 and 80 characters.'),
        ],
    )
    description = StringField(
        'Description',
        validators=[Optional(), Length(max=200, message='Description must be at most 200 characters.')],
    )
    icon = StringField(
        'Icon',
        validators=[Optional(), Length(max=50, message='Icon name must be at most 50 characters.')],
    )
    submit = SubmitField('Save Category')


class BrandForm(FlaskForm):
    """Form for creating item brands."""

    brand_name = StringField(
        'Brand Name',
        validators=[
            DataRequired(message='Brand name is required.'),
            Length(min=1, max=80, message='Brand name must be between 1 and 80 characters.'),
        ],
    )
    description = StringField(
        'Description',
        validators=[Optional(), Length(max=200, message='Description must be at most 200 characters.')],
    )
    submit = SubmitField('Save Brand')


class LocationForm(FlaskForm):
    """Form for creating campus locations."""

    location_name = StringField(
        'Location Name',
        validators=[
            DataRequired(message='Location name is required.'),
            Length(min=2, max=150, message='Location name must be between 2 and 150 characters.'),
        ],
    )
    zone_id = SelectField(
        'Campus Zone',
        coerce=int,
        validators=[DataRequired(message='Please select a campus zone.')],
    )
    building_id = SelectField('Building (Optional)', coerce=int, validators=[Optional()])
    room_id = SelectField('Room (Optional)', coerce=int, validators=[Optional()])
    latitude = FloatField(
        'Latitude',
        validators=[Optional(), NumberRange(min=-90.0, max=90.0, message='Latitude must be between -90 and 90.')],
    )
    longitude = FloatField(
        'Longitude',
        validators=[Optional(), NumberRange(min=-180.0, max=180.0, message='Longitude must be between -180 and 180.')],
    )
    submit = SubmitField('Save Location')

    def validate_zone_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid campus zone.')


class ModerationForm(FlaskForm):
    """Form for recording moderation actions."""

    target_type = SelectField(
        'Target Type',
        choices=[('user', 'User'), ('report', 'Item Report'), ('claim', 'Claim')],
        validators=[DataRequired(message='Target type is required.')],
    )
    target_id = IntegerField(
        'Target ID',
        validators=[
            DataRequired(message='Target ID is required.'),
            NumberRange(min=1, message='Target ID must be positive.'),
        ],
    )
    action_type = SelectField(
        'Action Type',
        choices=[
            ('warn', 'Warn'),
            ('suspend', 'Suspend'),
            ('delete', 'Delete'),
            ('reinstate', 'Reinstate'),
        ],
        validators=[DataRequired(message='Action type is required.')],
    )
    reason = TextAreaField(
        'Reason',
        validators=[
            DataRequired(message='Reason is required.'),
            Length(min=5, max=2000, message='Reason must be at least 5 characters.'),
        ],
    )
    submit = SubmitField('Apply Moderation Action')


class UserReportReviewForm(FlaskForm):
    """Form for reviewing user complaints/reports."""

    status = SelectField(
        'Status',
        choices=[
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
            ('resolved', 'Resolved'),
        ],
        validators=[DataRequired(message='Status is required.')],
    )
    action_type = SelectField(
        'Moderation Action (Optional)',
        choices=[
            ('', 'No Action'),
            ('warn', 'Warn User'),
            ('suspend', 'Suspend User'),
            ('reinstate', 'Reinstate User'),
        ],
        validators=[Optional()],
    )
    reason = TextAreaField(
        'Review / Action Notes',
        validators=[Optional(), Length(max=2000, message='Notes must be at most 2000 characters.')],
    )
    submit = SubmitField('Update User Report')
