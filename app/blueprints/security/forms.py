"""Forms for the security blueprint."""
from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class CustodyLogForm(FlaskForm):
    """Form for logging item custody actions."""

    report_id = SelectField(
        'Item Report',
        coerce=int,
        validators=[DataRequired(message='Please select an item report.')],
    )
    storage_location_id = SelectField(
        'Storage Location',
        coerce=int,
        validators=[DataRequired(message='Please select a storage location.')],
    )
    action = SelectField(
        'Custody Action',
        choices=[
            ('received', 'Received into Custody'),
            ('released', 'Released to Owner'),
            ('transferred', 'Transferred'),
        ],
        validators=[DataRequired(message='Please select a custody action.')],
    )
    submit = SubmitField('Log Custody')

    def validate_report_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid item report.')

    def validate_storage_location_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid storage location.')


class IncidentReportForm(FlaskForm):
    """Form for filing a campus security incident report."""

    location_id = SelectField(
        'Location',
        coerce=int,
        validators=[DataRequired(message='Please select a location.')],
    )
    report_id = SelectField('Related Item Report (Optional)', coerce=int, validators=[Optional()])
    severity = SelectField(
        'Severity',
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='low',
        validators=[DataRequired(message='Please select severity.')],
    )
    description = TextAreaField(
        'Incident Description',
        validators=[
            DataRequired(message='Incident description is required.'),
            Length(min=10, max=3000, message='Description must be at least 10 characters.'),
        ],
    )
    submit = SubmitField('Submit Incident Report')

    def validate_location_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid location.')


class ShiftForm(FlaskForm):
    """Form for scheduling security staff patrol shifts."""

    staff_id = SelectField(
        'Security Staff',
        coerce=int,
        validators=[DataRequired(message='Please select a staff member.')],
    )
    patrol_zone_id = SelectField(
        'Patrol Zone',
        coerce=int,
        validators=[DataRequired(message='Please select a patrol zone.')],
    )
    shift_date = DateField(
        'Shift Date',
        format='%Y-%m-%d',
        validators=[DataRequired(message='Shift date is required.')],
    )
    start_time = TimeField(
        'Start Time',
        format='%H:%M',
        validators=[DataRequired(message='Start time is required.')],
    )
    end_time = TimeField(
        'End Time',
        format='%H:%M',
        validators=[DataRequired(message='End time is required.')],
    )
    submit = SubmitField('Schedule Shift')

    def validate_staff_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid security staff member.')

    def validate_patrol_zone_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid patrol zone.')

    def validate_end_time(self, field):
        if self.start_time.data and field.data and field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time.')


class StorageLocationForm(FlaskForm):
    """Form for creating a secure storage location."""

    name = StringField(
        'Storage Name',
        validators=[
            DataRequired(message='Storage name is required.'),
            Length(min=2, max=100, message='Name must be between 2 and 100 characters.'),
        ],
    )
    building_id = SelectField(
        'Building',
        coerce=int,
        validators=[DataRequired(message='Please select a building.')],
    )
    capacity = IntegerField(
        'Capacity',
        default=50,
        validators=[
            DataRequired(message='Capacity is required.'),
            NumberRange(min=1, max=10000, message='Capacity must be between 1 and 10000.'),
        ],
    )
    submit = SubmitField('Create Storage Location')

    def validate_building_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid building.')
