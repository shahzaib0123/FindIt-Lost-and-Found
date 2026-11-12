"""Forms for the claims blueprint."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ClaimForm(FlaskForm):
    """Form for submitting an ownership claim on an item report."""

    claim_description = TextAreaField(
        'Claim Description',
        validators=[
            DataRequired(message='Please explain why this item belongs to you.'),
            Length(min=10, max=3000, message='Claim description must be at least 10 characters.'),
        ],
    )
    evidence_type = SelectField(
        'Evidence Type',
        choices=[
            ('description', 'Written Description'),
            ('receipt', 'Receipt / Proof of Purchase'),
            ('photo', 'Photo'),
        ],
        default='description',
        validators=[Optional()],
    )
    evidence_description = TextAreaField(
        'Evidence Notes',
        validators=[Optional(), Length(max=1000, message='Evidence notes must be at most 1000 characters.')],
    )
    evidence_file = FileField(
        'Supporting File (Optional)',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, or PDF files are allowed.'),
        ],
    )
    submit = SubmitField('Submit Claim')


class ClaimReviewForm(FlaskForm):
    """Form for reviewing and deciding on a claim."""

    decision = SelectField(
        'Decision',
        choices=[('approved', 'Approve'), ('rejected', 'Reject')],
        validators=[DataRequired(message='Please select a decision.')],
    )
    review_notes = TextAreaField(
        'Review Notes',
        validators=[
            DataRequired(message='Please provide notes explaining your decision.'),
            Length(min=5, max=2000, message='Review notes must be at least 5 characters.'),
        ],
    )
    submit = SubmitField('Submit Review')


class VerificationQuestionForm(FlaskForm):
    """Form for adding a verification question to an item report."""

    question = TextAreaField(
        'Verification Question',
        validators=[
            DataRequired(message='Question text is required.'),
            Length(min=5, max=500, message='Question must be between 5 and 500 characters.'),
        ],
    )
    submit = SubmitField('Add Question')
