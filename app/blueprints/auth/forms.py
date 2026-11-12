"""Forms for the auth blueprint."""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    Regexp,
    ValidationError,
)
from app.models.auth import User


class RegistrationForm(FlaskForm):
    """User registration form with server-side uniqueness and password validation."""

    username = StringField(
        'Username',
        validators=[
            DataRequired(message='Username is required.'),
            Length(min=3, max=80, message='Username must be between 3 and 80 characters.'),
            Regexp(
                r'^[A-Za-z0-9_.-]+$',
                message='Username may only contain letters, numbers, underscores, dots, and hyphens.',
            ),
        ],
    )
    email = EmailField(
        'Email',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.'),
            Length(max=120, message='Email must be at most 120 characters.'),
        ],
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=8, max=128, message='Password must be at least 8 characters long.'),
        ],
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords must match.'),
        ],
    )
    submit = SubmitField('Register')

    def validate_username(self, field):
        existing = User.query.filter_by(username=field.data.strip()).first()
        if existing:
            raise ValidationError('That username is already taken. Please choose another.')

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing:
            raise ValidationError('An account with that email already exists.')


class LoginForm(FlaskForm):
    """User login form."""

    email = EmailField(
        'Email',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.'),
        ],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message='Password is required.')],
    )
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ProfileForm(FlaskForm):
    """Form for editing user profile details."""

    first_name = StringField(
        'First Name',
        validators=[Optional(), Length(max=50, message='First name must be at most 50 characters.')],
    )
    last_name = StringField(
        'Last Name',
        validators=[Optional(), Length(max=50, message='Last name must be at most 50 characters.')],
    )
    bio = TextAreaField(
        'Bio',
        validators=[Optional(), Length(max=1000, message='Bio must be at most 1000 characters.')],
    )
    department = StringField(
        'Department',
        validators=[Optional(), Length(max=100, message='Department must be at most 100 characters.')],
    )
    reg_no = StringField(
        'Registration Number',
        validators=[Optional(), Length(max=50, message='Registration number must be at most 50 characters.')],
    )
    submit = SubmitField('Save Profile')
