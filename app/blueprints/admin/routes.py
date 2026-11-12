"""Routes for the admin blueprint."""
from functools import wraps
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from app.extensions import db
from app.models.admin import AuditLog, ModerationAction, UserReport
from app.models.auth import User
from app.models.claims import Claim
from app.models.classification import Brand, Category
from app.models.location import Building, CampusZone, Location, Room
from app.models.reporting import ItemReport
from . import admin_bp
from .forms import (
    BrandForm,
    CategoryForm,
    LocationForm,
    ModerationForm,
    UserReportReviewForm,
)


def admin_required(view_func):
    """Require authentication and the 'admin' role."""
    @wraps(view_func)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.has_role('admin'):
            abort(403)
        return view_func(*args, **kwargs)

    return decorated


def _populate_location_form(form):
    """Populate campus zone, building, and room choices for LocationForm."""
    form.zone_id.choices = [(0, '-- Select Campus Zone --')] + [
        (z.id, z.zone_name) for z in CampusZone.query.order_by(CampusZone.zone_name).all()
    ]
    form.building_id.choices = [(0, '-- None --')] + [
        (b.id, b.building_name) for b in Building.query.order_by(Building.building_name).all()
    ]
    form.room_id.choices = [(0, '-- None --')] + [
        (r.id, f'Room {r.room_number}') for r in Room.query.order_by(Room.room_number).all()
    ]


@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    """Render the admin control panel dashboard."""
    stats = {
        'users': User.query.count(),
        'reports': ItemReport.query.count(),
        'claims': Claim.query.count(),
        'pending_user_reports': UserReport.query.filter_by(status='pending').count(),
        'categories': Category.query.count(),
        'brands': Brand.query.count(),
        'locations': Location.query.count(),
    }
    recent_audit = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, recent_audit=recent_audit)


@admin_bp.route('/users', methods=['GET'])
@admin_required
def users():
    """List all registered users."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:id>', methods=['GET'])
@admin_required
def user_detail(id):
    """View details and activity for a specific user."""
    user = db.get_or_404(User, id)
    reports = ItemReport.query.filter_by(user_id=user.id).order_by(ItemReport.created_at.desc()).all()
    claims = Claim.query.filter_by(claimant_id=user.id).order_by(Claim.submitted_at.desc()).all()
    mod_actions = (
        ModerationAction.query.filter_by(target_type='user', target_id=user.id)
        .order_by(ModerationAction.created_at.desc())
        .all()
    )
    return render_template(
        'admin/user_detail.html',
        user=user,
        reports=reports,
        claims=claims,
        mod_actions=mod_actions,
    )


@admin_bp.route('/users/<int:id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(id):
    """Activate or deactivate a user account."""
    user = db.get_or_404(User, id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.user_detail', id=user.id))

    user.is_active = not user.is_active
    action_type = 'reinstate' if user.is_active else 'suspend'
    db.session.add(
        ModerationAction(
            admin_id=current_user.id,
            target_type='user',
            target_id=user.id,
            action_type=action_type,
            reason=f'Account status toggled to {"active" if user.is_active else "inactive"}',
        )
    )
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action=f'user_{action_type}',
            entity_type='user',
            entity_id=user.id,
            ip_address=request.remote_addr,
        )
    )
    db.session.commit()
    flash(f'User {user.username} is now {"active" if user.is_active else "inactive"}.', 'success')
    return redirect(url_for('admin.user_detail', id=user.id))


@admin_bp.route('/reports', methods=['GET'])
@admin_required
def reports():
    """List user complaints / user reports."""
    user_reports = UserReport.query.order_by(UserReport.created_at.desc()).all()
    return render_template('admin/user_reports.html', user_reports=user_reports)


@admin_bp.route('/reports/<int:id>/review', methods=['GET', 'POST'])
@admin_required
def review_report(id):
    """Review a user complaint and optionally apply a moderation action."""
    user_report = db.get_or_404(UserReport, id)
    form = UserReportReviewForm(obj=user_report)

    if form.validate_on_submit():
        user_report.status = form.status.data
        action_type = form.action_type.data
        reason = form.reason.data.strip() if form.reason.data else f'User report #{user_report.id} reviewed'

        if action_type:
            db.session.add(
                ModerationAction(
                    admin_id=current_user.id,
                    target_type='user',
                    target_id=user_report.reported_user_id,
                    action_type=action_type,
                    reason=reason,
                )
            )
            if action_type == 'suspend':
                user_report.reported_user.is_active = False
            elif action_type == 'reinstate':
                user_report.reported_user.is_active = True

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='review_user_report',
                entity_type='user_report',
                entity_id=user_report.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('User report updated.', 'success')
        return redirect(url_for('admin.reports'))

    return render_template('admin/report_review.html', user_report=user_report, form=form)


@admin_bp.route('/moderation', methods=['GET', 'POST'])
@admin_required
def moderation():
    """View moderation history and apply moderation actions."""
    form = ModerationForm()
    if form.validate_on_submit():
        action = ModerationAction(
            admin_id=current_user.id,
            target_type=form.target_type.data,
            target_id=form.target_id.data,
            action_type=form.action_type.data,
            reason=form.reason.data.strip(),
        )
        db.session.add(action)
        db.session.flush()

        if form.target_type.data == 'user':
            target_user = db.session.get(User, form.target_id.data)
            if target_user and target_user.id != current_user.id:
                if form.action_type.data == 'suspend':
                    target_user.is_active = False
                elif form.action_type.data == 'reinstate':
                    target_user.is_active = True

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action=f'moderation_{form.action_type.data}',
                entity_type=form.target_type.data,
                entity_id=form.target_id.data,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Moderation action recorded.', 'success')
        return redirect(url_for('admin.moderation'))

    actions = ModerationAction.query.order_by(ModerationAction.created_at.desc()).all()
    return render_template('admin/moderation.html', actions=actions, form=form)


@admin_bp.route('/audit-log', methods=['GET'])
@admin_required
def audit_log():
    """View paginated system audit log."""
    page = request.args.get('page', 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('admin/audit_log.html', logs=pagination.items, pagination=pagination)


@admin_bp.route('/categories', methods=['GET'])
@admin_required
def categories():
    """List all item categories."""
    all_categories = Category.query.order_by(Category.category_name).all()
    return render_template('admin/categories.html', categories=all_categories)


@admin_bp.route('/categories/create', methods=['GET', 'POST'])
@admin_required
def create_category():
    """Create a new item category."""
    form = CategoryForm()
    if form.validate_on_submit():
        name = form.category_name.data.strip()
        existing = Category.query.filter(func.lower(Category.category_name) == name.lower()).first()
        if existing:
            flash('A category with that name already exists.', 'danger')
        else:
            category = Category(
                category_name=name,
                description=form.description.data.strip() if form.description.data else None,
                icon=form.icon.data.strip() if form.icon.data else None,
            )
            db.session.add(category)
            db.session.flush()
            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    action='create_category',
                    entity_type='category',
                    entity_id=category.id,
                    ip_address=request.remote_addr,
                )
            )
            db.session.commit()
            flash('Category created successfully.', 'success')
            return redirect(url_for('admin.categories'))

    return render_template('admin/category_form.html', form=form, category=None)


@admin_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(id):
    """Edit an existing item category."""
    category = db.get_or_404(Category, id)
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        name = form.category_name.data.strip()
        duplicate = Category.query.filter(
            func.lower(Category.category_name) == name.lower(),
            Category.id != category.id,
        ).first()
        if duplicate:
            flash('Another category with that name already exists.', 'danger')
        else:
            category.category_name = name
            category.description = form.description.data.strip() if form.description.data else None
            category.icon = form.icon.data.strip() if form.icon.data else None
            db.session.commit()
            flash('Category updated successfully.', 'success')
            return redirect(url_for('admin.categories'))

    return render_template('admin/category_form.html', form=form, category=category)


@admin_bp.route('/categories/<int:id>/delete', methods=['POST'])
@admin_required
def delete_category(id):
    """Delete an item category if unused by item reports."""
    category = db.get_or_404(Category, id)
    if ItemReport.query.filter_by(category_id=category.id).first():
        flash('Cannot delete category because it is referenced by existing reports.', 'warning')
        return redirect(url_for('admin.categories'))

    db.session.delete(category)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/brands', methods=['GET'])
@admin_required
def brands():
    """List all item brands."""
    all_brands = Brand.query.order_by(Brand.brand_name).all()
    return render_template('admin/brands.html', brands=all_brands)


@admin_bp.route('/brands/create', methods=['GET', 'POST'])
@admin_required
def create_brand():
    """Create a new item brand."""
    form = BrandForm()
    if form.validate_on_submit():
        name = form.brand_name.data.strip()
        existing = Brand.query.filter(func.lower(Brand.brand_name) == name.lower()).first()
        if existing:
            flash('A brand with that name already exists.', 'danger')
        else:
            brand = Brand(
                brand_name=name,
                description=form.description.data.strip() if form.description.data else None,
            )
            db.session.add(brand)
            db.session.flush()
            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    action='create_brand',
                    entity_type='brand',
                    entity_id=brand.id,
                    ip_address=request.remote_addr,
                )
            )
            db.session.commit()
            flash('Brand created successfully.', 'success')
            return redirect(url_for('admin.brands'))

    return render_template('admin/brand_form.html', form=form)


@admin_bp.route('/locations', methods=['GET'])
@admin_required
def locations():
    """List all campus locations."""
    all_locations = Location.query.order_by(Location.location_name).all()
    return render_template('admin/locations_manage.html', locations=all_locations)


@admin_bp.route('/locations/create', methods=['GET', 'POST'])
@admin_required
def create_location():
    """Create a new campus location."""
    form = LocationForm()
    _populate_location_form(form)

    if form.validate_on_submit():
        location = Location(
            location_name=form.location_name.data.strip(),
            zone_id=form.zone_id.data,
            building_id=form.building_id.data if form.building_id.data else None,
            room_id=form.room_id.data if form.room_id.data else None,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
        )
        db.session.add(location)
        db.session.flush()
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='create_location',
                entity_type='location',
                entity_id=location.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Location created successfully.', 'success')
        return redirect(url_for('admin.locations'))

    return render_template('admin/location_form.html', form=form)
