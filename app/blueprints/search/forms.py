"""Forms for the search blueprint."""
from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class SearchForm(FlaskForm):
    """Form for searching item reports with filters."""

    keyword = StringField(
        'Keyword',
        validators=[Optional(), Length(max=200, message='Keyword must be at most 200 characters.')],
    )
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    report_type_id = SelectField('Report Type', coerce=int, validators=[Optional()])
    submit = SubmitField('Search')


class SaveSearchForm(FlaskForm):
    """Form for saving search criteria for quick access."""

    search_name = StringField(
        'Search Name',
        validators=[
            DataRequired(message='Please give this saved search a name.'),
            Length(min=2, max=100, message='Search name must be between 2 and 100 characters.'),
        ],
    )
    keyword = HiddenField()
    category_id = HiddenField()
    report_type_id = HiddenField()
    submit = SubmitField('Save Search')
