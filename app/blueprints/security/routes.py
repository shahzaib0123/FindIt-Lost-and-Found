"""Routes for the security blueprint."""
from functools import wraps
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models.admin import AuditLog
from app.models.location import Building, Location
from app.models.reporting import ItemReport
from app.models.security import (
    CustodyLog,
    IncidentReport,
    PatrolZone,
    SecurityStaff,
    Shift,
    StorageLocation,
)
from . import security_bp
from .forms import CustodyLogForm, IncidentReportForm, ShiftForm, StorageLocationForm


def security_required(view_func):
    """Require authentication and either 'security' or 'admin' role."""
    @wraps(view_func)
    @login_required
    def decorated(*args, **kwargs):
        if not (current_user.has_role('security') or current_user.has_role('admin')):
            abort(403)
        return view_func(*args, **kwargs)

    return decorated


def _get_or_create_staff_profile(user):
    """Return the SecurityStaff record for user, creating one if absent."""
    staff = SecurityStaff.query.filter_by(user_id=user.id).first()
    if staff is None:
        staff = SecurityStaff(
            user_id=user.id,
            badge_no=f'SEC-{user.id:04d}',
            post='Campus Security Desk',
        )
        db.session.add(staff)
        db.session.flush()
    return staff


@security_bp.route('/dashboard', methods=['GET'])
@security_required
def dashboard():
    """Render the security operations dashboard."""
    stats = {
        'custody_logs': CustodyLog.query.count(),
        'incidents': IncidentReport.query.count(),
        'shifts': Shift.query.count(),
        'storage_locations': StorageLocation.query.count(),
    }
    recent_custody = CustodyLog.query.order_by(CustodyLog.logged_at.desc()).limit(5).all()
    recent_incidents = IncidentReport.query.order_by(IncidentReport.incident_date.desc()).limit(5).all()
    upcoming_shifts = Shift.query.order_by(Shift.shift_date.desc(), Shift.start_time.asc()).limit(5).all()
    return render_template(
        'security/dashboard.html',
        stats=stats,
        recent_custody=recent_custody,
        recent_incidents=recent_incidents,
        upcoming_shifts=upcoming_shifts,
    )


@security_bp.route('/custody', methods=['GET'])
@security_required
def custody():
    """List all item custody logs."""
    logs = CustodyLog.query.order_by(CustodyLog.logged_at.desc()).all()
    return render_template('security/custody.html', logs=logs)


@security_bp.route('/custody/log', methods=['GET', 'POST'])
@security_required
def log_custody():
    """Log custody receipt, release, or transfer of a reported item."""
    form = CustodyLogForm()
    form.report_id.choices = [(0, '-- Select Item Report --')] + [
        (r.id, f'#{r.id} - {r.title}') for r in ItemReport.query.order_by(ItemReport.created_at.desc()).all()
    ]
    form.storage_location_id.choices = [(0, '-- Select Storage Location --')] + [
        (s.id, s.name) for s in StorageLocation.query.order_by(StorageLocation.name).all()
    ]

    if form.validate_on_submit():
        staff = _get_or_create_staff_profile(current_user)
        entry = CustodyLog(
            report_id=form.report_id.data,
            staff_id=staff.id,
            storage_location_id=form.storage_location_id.data,
            action=form.action.data,
        )
        db.session.add(entry)
        db.session.flush()
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action=f'custody_{form.action.data}',
                entity_type='custody_log',
                entity_id=entry.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Custody action logged successfully.', 'success')
        return redirect(url_for('security.custody'))

    return render_template('security/custody_form.html', form=form)


@security_bp.route('/incidents', methods=['GET'])
@security_required
def incidents():
    """List all security incident reports."""
    all_incidents = IncidentReport.query.order_by(IncidentReport.incident_date.desc()).all()
    return render_template('security/incidents.html', incidents=all_incidents)


@security_bp.route('/incidents/create', methods=['GET', 'POST'])
@security_required
def create_incident():
    """Create a new security incident report."""
    form = IncidentReportForm()
    form.location_id.choices = [(0, '-- Select Location --')] + [
        (loc.id, loc.location_name) for loc in Location.query.order_by(Location.location_name).all()
    ]
    form.report_id.choices = [(0, '-- None --')] + [
        (r.id, f'#{r.id} - {r.title}') for r in ItemReport.query.order_by(ItemReport.created_at.desc()).all()
    ]

    if form.validate_on_submit():
        staff = _get_or_create_staff_profile(current_user)
        incident = IncidentReport(
            reported_by=current_user.id,
            staff_id=staff.id,
            location_id=form.location_id.data,
            report_id=form.report_id.data if form.report_id.data else None,
            severity=form.severity.data,
            description=form.description.data.strip(),
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='create_incident_report',
                entity_type='incident_report',
                entity_id=incident.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Incident report filed.', 'success')
        return redirect(url_for('security.incidents'))

    return render_template('security/incident_form.html', form=form)


@security_bp.route('/incidents/<int:id>', methods=['GET'])
@security_required
def incident_detail(id):
    """View details of a security incident report."""
    incident = db.get_or_404(IncidentReport, id)
    return render_template('security/incident_detail.html', incident=incident)


@security_bp.route('/shifts', methods=['GET'])
@security_required
def shifts():
    """List scheduled security patrol shifts."""
    all_shifts = Shift.query.order_by(Shift.shift_date.desc(), Shift.start_time.asc()).all()
    return render_template('security/shifts.html', shifts=all_shifts)


@security_bp.route('/shifts/create', methods=['GET', 'POST'])
@security_required
def create_shift():
    """Schedule a new security patrol shift."""
    form = ShiftForm()
    form.staff_id.choices = [(0, '-- Select Staff --')] + [
        (s.id, f'{s.badge_no} ({s.user.username})') for s in SecurityStaff.query.all()
    ]
    form.patrol_zone_id.choices = [(0, '-- Select Patrol Zone --')] + [
        (pz.id, pz.zone_name) for pz in PatrolZone.query.order_by(PatrolZone.zone_name).all()
    ]

    if form.validate_on_submit():
        shift = Shift(
            staff_id=form.staff_id.data,
            patrol_zone_id=form.patrol_zone_id.data,
            shift_date=form.shift_date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
        )
        db.session.add(shift)
        db.session.commit()
        flash('Security shift scheduled.', 'success')
        return redirect(url_for('security.shifts'))

    return render_template('security/shift_form.html', form=form)


@security_bp.route('/storage', methods=['GET'])
@security_required
def storage():
    """List all secure storage locations."""
    locations = StorageLocation.query.order_by(StorageLocation.name).all()
    return render_template('security/storage.html', storage_locations=locations)


@security_bp.route('/storage/create', methods=['GET', 'POST'])
@security_required
def create_storage():
    """Create a new secure storage location."""
    form = StorageLocationForm()
    form.building_id.choices = [(0, '-- Select Building --')] + [
        (b.id, b.building_name) for b in Building.query.order_by(Building.building_name).all()
    ]

    if form.validate_on_submit():
        storage_loc = StorageLocation(
            name=form.name.data.strip(),
            building_id=form.building_id.data,
            capacity=form.capacity.data,
        )
        db.session.add(storage_loc)
        db.session.commit()
        flash('Storage location created.', 'success')
        return redirect(url_for('security.storage'))

    return render_template('security/storage_form.html', form=form)
