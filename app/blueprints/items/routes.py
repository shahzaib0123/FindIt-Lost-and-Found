"""Routes for the items blueprint."""
import os
import uuid
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.admin import AuditLog
from app.models.classification import (
    Brand,
    Category,
    ItemCondition,
    ReportStatus,
    ReportType,
    Subcategory,
)
from app.models.location import Location
from app.models.reporting import (
    ItemImage,
    ItemReport,
    ReportLocation,
    ReportStatusHistory,
)
from app.models.search import ReportTag, Tag
from . import items_bp
from .forms import ImageUploadForm, ItemReportForm

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def _populate_report_form_choices(form):
    """Populate dropdown choices for ItemReportForm from database lookup tables."""
    form.category_id.choices = [(0, '-- Select Category --')] + [
        (c.id, c.category_name) for c in Category.query.order_by(Category.category_name).all()
    ]
    form.subcategory_id.choices = [(0, '-- Select Subcategory --')] + [
        (s.id, s.subcategory_name) for s in Subcategory.query.order_by(Subcategory.subcategory_name).all()
    ]
    form.brand_id.choices = [(0, '-- Select Brand --')] + [
        (b.id, b.brand_name) for b in Brand.query.order_by(Brand.brand_name).all()
    ]
    form.condition_id.choices = [(0, '-- Select Condition --')] + [
        (c.id, c.condition_name) for c in ItemCondition.query.order_by(ItemCondition.condition_name).all()
    ]
    form.report_type_id.choices = [(0, '-- Select Type --')] + [
        (t.id, t.type_name.title()) for t in ReportType.query.order_by(ReportType.id).all()
    ]
    form.location_id.choices = [(0, '-- Select Location --')] + [
        (loc.id, loc.location_name) for loc in Location.query.order_by(Location.location_name).all()
    ]


def _sync_report_tags(report, tags_raw):
    """Synchronize comma-separated tags for an ItemReport."""
    ReportTag.query.filter_by(report_id=report.id).delete()
    if not tags_raw:
        return

    seen = set()
    for part in tags_raw.split(','):
        tag_name = part.strip().lower()[:50]
        if not tag_name or tag_name in seen:
            continue
        seen.add(tag_name)
        tag = Tag.query.filter_by(tag_name=tag_name).first()
        if tag is None:
            tag = Tag(tag_name=tag_name)
            db.session.add(tag)
            db.session.flush()
        db.session.add(ReportTag(report_id=report.id, tag_id=tag.id))


def _save_item_image(file_storage, report_id, is_primary=False):
    """Validate extension, save image file to UPLOAD_FOLDER, and create ItemImage record."""
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    unique_name = f'{uuid.uuid4().hex}_{filename}'
    file_path = os.path.join(upload_folder, unique_name)
    file_storage.save(file_path)

    if is_primary:
        ItemImage.query.filter_by(report_id=report_id, is_primary=True).update({'is_primary': False})

    image = ItemImage(
        report_id=report_id,
        image_path=f'uploads/{unique_name}',
        is_primary=is_primary,
    )
    db.session.add(image)
    return image


def _get_or_create_default_status(status_name='open'):
    """Fetch a ReportStatus by name, creating it if missing."""
    status = ReportStatus.query.filter(func.lower(ReportStatus.status_name) == status_name.lower()).first()
    if status is None:
        status = ReportStatus(status_name=status_name, description=f'{status_name.title()} report status')
        db.session.add(status)
        db.session.flush()
    return status


@items_bp.route('/', methods=['GET'])
def index():
    """List all item reports with pagination."""
    page = request.args.get('page', 1, type=int)
    pagination = ItemReport.query.order_by(ItemReport.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    return render_template(
        'items/list.html',
        reports=pagination.items,
        pagination=pagination,
        report_type_filter=None,
        page_title='All Item Reports',
    )


@items_bp.route('/lost', methods=['GET'])
def lost():
    """List lost item reports."""
    page = request.args.get('page', 1, type=int)
    pagination = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'lost')
        .order_by(ItemReport.created_at.desc())
        .paginate(page=page, per_page=12, error_out=False)
    )
    return render_template(
        'items/list.html',
        reports=pagination.items,
        pagination=pagination,
        report_type_filter='lost',
        page_title='Lost Items',
    )


@items_bp.route('/found', methods=['GET'])
def found():
    """List found item reports."""
    page = request.args.get('page', 1, type=int)
    pagination = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'found')
        .order_by(ItemReport.created_at.desc())
        .paginate(page=page, per_page=12, error_out=False)
    )
    return render_template(
        'items/list.html',
        reports=pagination.items,
        pagination=pagination,
        report_type_filter='found',
        page_title='Found Items',
    )


@items_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new lost or found item report."""
    form = ItemReportForm()
    _populate_report_form_choices(form)

    if form.validate_on_submit():
        default_status = _get_or_create_default_status('open')
        report = ItemReport(
            user_id=current_user.id,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category_id=form.category_id.data if form.category_id.data else None,
            subcategory_id=form.subcategory_id.data if form.subcategory_id.data else None,
            brand_id=form.brand_id.data if form.brand_id.data else None,
            condition_id=form.condition_id.data if form.condition_id.data else None,
            report_type_id=form.report_type_id.data,
            status_id=default_status.id,
            event_date=form.event_date.data,
        )
        db.session.add(report)
        db.session.flush()

        if form.location_id.data and form.location_id.data > 0:
            db.session.add(
                ReportLocation(
                    report_id=report.id,
                    location_id=form.location_id.data,
                    specific_location=form.specific_location.data.strip() if form.specific_location.data else None,
                )
            )

        _sync_report_tags(report, form.tags.data)

        uploaded = request.files.get('image')
        if uploaded and uploaded.filename:
            saved_img = _save_item_image(uploaded, report.id, is_primary=True)
            if saved_img is None:
                flash('Invalid image format skipped. Allowed formats: jpg, jpeg, png, gif, webp.', 'warning')

        db.session.add(
            ReportStatusHistory(
                report_id=report.id,
                old_status_id=None,
                new_status_id=default_status.id,
                changed_by=current_user.id,
                change_reason='Initial report submission',
            )
        )
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='create_item_report',
                entity_type='item_report',
                entity_id=report.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()

        session['last_created_report_id'] = report.id
        flash('Item report created successfully!', 'success')
        return redirect(url_for('items.detail', id=report.id))

    return render_template('items/create.html', form=form)


@items_bp.route('/<int:id>', methods=['GET'])
def detail(id):
    """View details for a single item report."""
    report = db.get_or_404(ItemReport, id)

    recently_viewed = session.get('recently_viewed', [])
    if id in recently_viewed:
        recently_viewed.remove(id)
    recently_viewed.insert(0, id)
    session['recently_viewed'] = recently_viewed[:5]

    image_form = ImageUploadForm()
    return render_template('items/detail.html', report=report, image_form=image_form)


@items_bp.route('/<int:id>/upload-image', methods=['POST'])
@login_required
def upload_image(id):
    """Upload an image attachment for an existing item report."""
    report = db.get_or_404(ItemReport, id)
    if report.user_id != current_user.id and not current_user.has_role('admin'):
        abort(403)

    form = ImageUploadForm()
    if form.validate_on_submit():
        is_primary = form.is_primary.data or len(report.images) == 0
        saved = _save_item_image(form.image.data, report.id, is_primary=is_primary)
        if saved:
            db.session.commit()
            flash('Image uploaded successfully.', 'success')
        else:
            flash('Unable to save image. Please upload a valid image file.', 'danger')
    else:
        for errors in form.errors.values():
            for err in errors:
                flash(err, 'danger')

    return redirect(url_for('items.detail', id=report.id))


@items_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing item report and track status changes."""
    report = db.get_or_404(ItemReport, id)
    if report.user_id != current_user.id and not current_user.has_role('admin'):
        abort(403)

    form = ItemReportForm(obj=report)
    _populate_report_form_choices(form)
    statuses = ReportStatus.query.order_by(ReportStatus.id).all()

    if request.method == 'GET':
        if report.report_location:
            form.location_id.data = report.report_location.location_id
            form.specific_location.data = report.report_location.specific_location
        form.tags.data = ', '.join(rt.tag.tag_name for rt in report.tags if rt.tag)

    if form.validate_on_submit():
        report.title = form.title.data.strip()
        report.description = form.description.data.strip()
        report.category_id = form.category_id.data if form.category_id.data else None
        report.subcategory_id = form.subcategory_id.data if form.subcategory_id.data else None
        report.brand_id = form.brand_id.data if form.brand_id.data else None
        report.condition_id = form.condition_id.data if form.condition_id.data else None
        report.report_type_id = form.report_type_id.data
        report.event_date = form.event_date.data

        if form.location_id.data and form.location_id.data > 0:
            if report.report_location:
                report.report_location.location_id = form.location_id.data
                report.report_location.specific_location = (
                    form.specific_location.data.strip() if form.specific_location.data else None
                )
            else:
                db.session.add(
                    ReportLocation(
                        report_id=report.id,
                        location_id=form.location_id.data,
                        specific_location=(
                            form.specific_location.data.strip() if form.specific_location.data else None
                        ),
                    )
                )
        elif report.report_location:
            db.session.delete(report.report_location)

        _sync_report_tags(report, form.tags.data)

        new_status_id = request.form.get('status_id', type=int)
        if new_status_id and new_status_id != report.status_id:
            target_status = db.session.get(ReportStatus, new_status_id)
            if target_status:
                old_status_id = report.status_id
                report.status_id = target_status.id
                db.session.add(
                    ReportStatusHistory(
                        report_id=report.id,
                        old_status_id=old_status_id,
                        new_status_id=target_status.id,
                        changed_by=current_user.id,
                        change_reason=request.form.get('status_reason', 'Updated via report edit').strip()[:300],
                    )
                )

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='update_item_report',
                entity_type='item_report',
                entity_id=report.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Item report updated successfully.', 'success')
        return redirect(url_for('items.detail', id=report.id))

    return render_template('items/edit.html', form=form, report=report, statuses=statuses)


@items_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete an item report."""
    report = db.get_or_404(ItemReport, id)
    if report.user_id != current_user.id and not current_user.has_role('admin'):
        abort(403)

    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action='delete_item_report',
            entity_type='item_report',
            entity_id=report.id,
            ip_address=request.remote_addr,
        )
    )
    db.session.delete(report)
    db.session.commit()
    flash('Item report deleted.', 'info')
    return redirect(url_for('items.index'))
