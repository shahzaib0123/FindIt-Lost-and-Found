"""Routes for the search blueprint."""
from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from app.extensions import db
from app.models.classification import Category, ReportType
from app.models.reporting import ItemReport
from app.models.search import ItemMatch, SavedSearch, SavedSearchFilter
from . import search_bp
from .forms import SaveSearchForm, SearchForm


def _populate_search_form(form):
    """Populate category and report type filter dropdowns."""
    form.category_id.choices = [(0, 'All Categories')] + [
        (c.id, c.category_name) for c in Category.query.order_by(Category.category_name).all()
    ]
    form.report_type_id.choices = [(0, 'All Types')] + [
        (t.id, t.type_name.title()) for t in ReportType.query.order_by(ReportType.id).all()
    ]


@search_bp.route('/', methods=['GET'])
def index():
    """Search item reports with keyword, category, and report type filters."""
    form = SearchForm(request.args, meta={'csrf': False})
    _populate_search_form(form)

    keyword = (request.args.get('keyword') or '').strip()
    category_id = request.args.get('category_id', type=int) or 0
    report_type_id = request.args.get('report_type_id', type=int) or 0

    query = ItemReport.query
    if keyword:
        pattern = f'%{keyword}%'
        query = query.filter(
            or_(
                ItemReport.title.ilike(pattern),
                ItemReport.description.ilike(pattern),
            )
        )
    if category_id > 0:
        query = query.filter(ItemReport.category_id == category_id)
    if report_type_id > 0:
        query = query.filter(ItemReport.report_type_id == report_type_id)

    results = query.order_by(ItemReport.created_at.desc()).all()

    session['last_search'] = {
        'keyword': keyword,
        'category_id': category_id,
        'report_type_id': report_type_id,
    }

    save_form = SaveSearchForm(
        keyword=keyword,
        category_id=str(category_id) if category_id else '',
        report_type_id=str(report_type_id) if report_type_id else '',
    )

    return render_template(
        'search/search.html',
        form=form,
        save_form=save_form,
        results=results,
        keyword=keyword,
        category_id=category_id,
        report_type_id=report_type_id,
    )


@search_bp.route('/save', methods=['POST'])
@login_required
def save():
    """Save current search filters to the user's saved searches."""
    form = SaveSearchForm()
    if form.validate_on_submit():
        last_search = session.get('last_search', {})
        keyword = (form.keyword.data or last_search.get('keyword') or '').strip()
        category_id = form.category_id.data or str(last_search.get('category_id') or '')
        report_type_id = form.report_type_id.data or str(last_search.get('report_type_id') or '')

        saved_search = SavedSearch(
            user_id=current_user.id,
            search_name=form.search_name.data.strip(),
            keyword=keyword or None,
        )
        db.session.add(saved_search)
        db.session.flush()

        if category_id and category_id != '0':
            db.session.add(
                SavedSearchFilter(
                    saved_search_id=saved_search.id,
                    filter_name='category_id',
                    filter_value=str(category_id),
                )
            )
        if report_type_id and report_type_id != '0':
            db.session.add(
                SavedSearchFilter(
                    saved_search_id=saved_search.id,
                    filter_name='report_type_id',
                    filter_value=str(report_type_id),
                )
            )

        db.session.commit()
        flash('Search saved successfully.', 'success')
        return redirect(url_for('search.saved'))

    flash('Please provide a valid name for your saved search.', 'danger')
    return redirect(url_for('search.index'))


@search_bp.route('/saved', methods=['GET'])
@login_required
def saved():
    """List all saved searches for the current user."""
    saved_searches = (
        SavedSearch.query.filter_by(user_id=current_user.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )
    return render_template('search/saved.html', saved_searches=saved_searches)


@search_bp.route('/saved/<int:id>/delete', methods=['POST'])
@login_required
def delete_saved(id):
    """Delete a saved search owned by the current user."""
    saved_search = db.get_or_404(SavedSearch, id)
    if saved_search.user_id != current_user.id:
        abort(403)

    db.session.delete(saved_search)
    db.session.commit()
    flash('Saved search deleted.', 'info')
    return redirect(url_for('search.saved'))


@search_bp.route('/matches', methods=['GET'])
@login_required
def matches():
    """View potential lost/found item matches for the current user's reports."""
    if current_user.has_role('admin') or current_user.has_role('security'):
        item_matches = ItemMatch.query.order_by(ItemMatch.match_score.desc(), ItemMatch.created_at.desc()).all()
    else:
        user_report_ids = [
            r.id for r in ItemReport.query.with_entities(ItemReport.id).filter_by(user_id=current_user.id).all()
        ]
        if user_report_ids:
            item_matches = (
                ItemMatch.query.filter(
                    or_(
                        ItemMatch.lost_report_id.in_(user_report_ids),
                        ItemMatch.found_report_id.in_(user_report_ids),
                    )
                )
                .order_by(ItemMatch.match_score.desc(), ItemMatch.created_at.desc())
                .all()
            )
        else:
            item_matches = []

    return render_template('search/matches.html', matches=item_matches)
