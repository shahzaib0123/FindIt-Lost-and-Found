"""Forms for the items blueprint."""
from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DateField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class ItemReportForm(FlaskForm):
    """Form for creating and editing lost/found item reports."""

    title = StringField(
        'Title',
        validators=[
            DataRequired(message='Title is required.'),
            Length(min=3, max=200, message='Title must be between 3 and 200 characters.'),
        ],
    )
    description = TextAreaField(
        'Description',
        validators=[
            DataRequired(message='Description is required.'),
            Length(min=10, max=5000, message='Description must be at least 10 characters.'),
        ],
    )
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    subcategory_id = SelectField('Subcategory', coerce=int, validators=[Optional()])
    brand_id = SelectField('Brand', coerce=int, validators=[Optional()])
    condition_id = SelectField('Condition', coerce=int, validators=[Optional()])
    report_type_id = SelectField(
        'Report Type',
        coerce=int,
        validators=[DataRequired(message='Please select a report type.')],
    )
    location_id = SelectField('Campus Location', coerce=int, validators=[Optional()])
    specific_location = StringField(
        'Specific Location Details',
        validators=[Optional(), Length(max=200, message='Specific location must be at most 200 characters.')],
    )
    event_date = DateField(
        'Date Lost / Found',
        format='%Y-%m-%d',
        validators=[Optional()],
    )
    tags = StringField(
        'Tags (comma-separated)',
        validators=[Optional(), Length(max=300, message='Tags must be at most 300 characters.')],
    )
    submit = SubmitField('Submit Report')

    def validate_report_type_id(self, field):
        if not field.data or field.data <= 0:
            raise ValidationError('Please select a valid report type.')

    def validate_event_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Event date cannot be in the future.')


class ImageUploadForm(FlaskForm):
    """Form for uploading item report images."""

    image = FileField(
        'Item Image',
        validators=[
            FileRequired(message='Please select an image file to upload.'),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Only image files (jpg, png, gif, webp) are allowed.'),
        ],
    )
    is_primary = BooleanField('Set as Primary Image')
    submit = SubmitField('Upload Image')
