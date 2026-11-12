"""Forms for the messaging blueprint."""
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class MessageForm(FlaskForm):
    """Form for sending a message inside a conversation."""

    message_text = TextAreaField(
        'Message',
        validators=[
            DataRequired(message='Message cannot be empty.'),
            Length(min=1, max=2000, message='Message must be at most 2000 characters.'),
        ],
    )
    submit = SubmitField('Send Message')
