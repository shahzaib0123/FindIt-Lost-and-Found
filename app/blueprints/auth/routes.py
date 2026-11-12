"""Routes for the auth blueprint."""
from urllib.parse import urlparse
from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from app.extensions import db
from app.models.admin import AuditLog
from app.models.auth import Role, User, UserProfile, UserRole
from app.models.claims import Claim
from app.models.reporting import ItemReport
from . import auth_bp
from .forms import LoginForm, ProfileForm, RegistrationForm


def _ensure_user_profile(user):
    """Ensure the given user has a UserProfile record."""
    if user.profile is None:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return user.profile


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account, create profile, and assign default 'user' role."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id)
        db.session.add(profile)

        default_role = Role.query.filter_by(role_name='user').first()
        if default_role is None:
            default_role = Role(role_name='user', description='Standard campus user')
            db.session.add(default_role)
            db.session.flush()

        db.session.add(UserRole(user_id=user.id, role_id=default_role.id))
        db.session.add(
            AuditLog(
                user_id=user.id,
                action='user_registered',
                entity_type='user',
                entity_id=user.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate and log in a user."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account is currently deactivated. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user, remember=form.remember_me.data)
            session['user_id'] = user.id
            session['username'] = user.username

            db.session.add(
                AuditLog(
                    user_id=user.id,
                    action='user_login',
                    entity_type='user',
                    entity_id=user.id,
                    ip_address=request.remote_addr,
                )
            )
            db.session.commit()

            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc == '' and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.index'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user and clear session metadata."""
    user_id = current_user.id
    db.session.add(
        AuditLog(
            user_id=user_id,
            action='user_logout',
            entity_type='user',
            entity_id=user_id,
            ip_address=request.remote_addr,
        )
    )
    db.session.commit()

    session.pop('user_id', None)
    session.pop('username', None)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and optionally update the current user's profile."""
    user_profile = _ensure_user_profile(current_user)
    form = ProfileForm(obj=user_profile)

    if form.validate_on_submit():
        user_profile.first_name = form.first_name.data.strip() if form.first_name.data else None
        user_profile.last_name = form.last_name.data.strip() if form.last_name.data else None
        user_profile.bio = form.bio.data.strip() if form.bio.data else None
        user_profile.department = form.department.data.strip() if form.department.data else None
        user_profile.reg_no = form.reg_no.data.strip() if form.reg_no.data else None
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    reports = (
        ItemReport.query.filter_by(user_id=current_user.id)
        .order_by(ItemReport.created_at.desc())
        .all()
    )
    claims = (
        Claim.query.filter_by(claimant_id=current_user.id)
        .order_by(Claim.submitted_at.desc())
        .all()
    )
    return render_template(
        'auth/profile.html',
        user=current_user,
        profile=user_profile,
        form=form,
        reports=reports,
        claims=claims,
        is_own_profile=True,
    )


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit the current user's profile information."""
    user_profile = _ensure_user_profile(current_user)
    form = ProfileForm(obj=user_profile)

    if form.validate_on_submit():
        user_profile.first_name = form.first_name.data.strip() if form.first_name.data else None
        user_profile.last_name = form.last_name.data.strip() if form.last_name.data else None
        user_profile.bio = form.bio.data.strip() if form.bio.data else None
        user_profile.department = form.department.data.strip() if form.department.data else None
        user_profile.reg_no = form.reg_no.data.strip() if form.reg_no.data else None
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html', form=form, profile=user_profile)


@auth_bp.route('/profile/<int:user_id>', methods=['GET'])
def public_profile(user_id):
    """Display a user's public profile and submitted item reports."""
    user = db.get_or_404(User, user_id)
    if not user.is_active and not (current_user.is_authenticated and current_user.has_role('admin')):
        abort(404)

    reports = (
        ItemReport.query.filter_by(user_id=user.id)
        .order_by(ItemReport.created_at.desc())
        .all()
    )
    is_own = current_user.is_authenticated and current_user.id == user.id
    return render_template(
        'auth/profile.html',
        user=user,
        profile=user.profile,
        form=None,
        reports=reports,
        claims=[],
        is_own_profile=is_own,
    )
