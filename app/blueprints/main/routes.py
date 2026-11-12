"""Routes for the main blueprint."""
from flask import render_template, session
from sqlalchemy import func
from app.models.auth import User
from app.models.claims import Claim
from app.models.classification import ReportStatus, ReportType
from app.models.reporting import ItemReport
from . import main_bp


@main_bp.route('/', methods=['GET'])
def index():
    """Render the homepage/dashboard with recent lost & found reports and platform statistics."""
    session['visit_count'] = session.get('visit_count', 0) + 1

    recent_lost = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'lost')
        .order_by(ItemReport.created_at.desc())
        .limit(6)
        .all()
    )
    recent_found = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'found')
        .order_by(ItemReport.created_at.desc())
        .limit(6)
        .all()
    )
    recent_reports = ItemReport.query.order_by(ItemReport.created_at.desc()).limit(8).all()

    lost_count = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'lost')
        .count()
    )
    found_count = (
        ItemReport.query.join(ReportType)
        .filter(func.lower(ReportType.type_name) == 'found')
        .count()
    )
    resolved_count = (
        ItemReport.query.join(ReportStatus)
        .filter(func.lower(ReportStatus.status_name).in_(['claimed', 'resolved', 'returned', 'closed']))
        .count()
    )

    stats = {
        'total_reports': ItemReport.query.count(),
        'lost_count': lost_count,
        'found_count': found_count,
        'resolved_count': resolved_count,
        'total_users': User.query.count(),
        'total_claims': Claim.query.count(),
    }

    return render_template(
        'main/index.html',
        recent_lost=recent_lost,
        recent_found=recent_found,
        recent_reports=recent_reports,
        stats=stats,
    )


@main_bp.route('/about', methods=['GET'])
def about():
    """Render the about page with overview information."""
    stats = {
        'total_reports': ItemReport.query.count(),
        'total_users': User.query.count(),
        'total_claims': Claim.query.count(),
    }
    return render_template('main/about.html', stats=stats)
