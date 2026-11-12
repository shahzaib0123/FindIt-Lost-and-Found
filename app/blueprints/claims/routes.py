"""Routes for the claims blueprint."""
import os
import uuid
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.admin import AuditLog
from app.models.claims import (
    Claim,
    ClaimAnswer,
    ClaimEvidence,
    ClaimReview,
    VerificationQuestion,
)
from app.models.classification import ReportStatus
from app.models.communication import Notification
from app.models.reporting import ItemReport, ReportStatusHistory
from . import claims_bp
from .forms import ClaimForm, ClaimReviewForm, VerificationQuestionForm


def _can_review_claim(claim, user):
    """Return True if user is the report owner, security staff, or admin."""
    return (
        claim.report.user_id == user.id
        or user.has_role('security')
        or user.has_role('admin')
    )


def _save_evidence_file(file_storage):
    """Save uploaded claim evidence file and return relative upload path."""
    if not file_storage or not file_storage.filename:
        return None
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    unique_name = f'claim_{uuid.uuid4().hex}_{filename}'
    file_storage.save(os.path.join(upload_folder, unique_name))
    return f'uploads/{unique_name}'


@claims_bp.route('/submit/<int:report_id>', methods=['GET', 'POST'])
@login_required
def submit(report_id):
    """Submit a claim for an item report, including verification question answers."""
    report = db.get_or_404(ItemReport, report_id)
    if report.user_id == current_user.id:
        flash('You cannot submit a claim on your own report.', 'warning')
        return redirect(url_for('items.detail', id=report.id))

    existing_claim = Claim.query.filter_by(
        report_id=report.id,
        claimant_id=current_user.id,
        claim_status='pending',
    ).first()
    if existing_claim:
        flash('You already have a pending claim for this item.', 'info')
        return redirect(url_for('claims.detail', id=existing_claim.id))

    questions = VerificationQuestion.query.filter_by(report_id=report.id).all()
    form = ClaimForm()

    if form.validate_on_submit():
        answers_payload = []
        missing_answers = False
        for question in questions:
            ans_text = request.form.get(f'answer_{question.id}', '').strip()
            if not ans_text:
                missing_answers = True
            answers_payload.append((question, ans_text))

        if missing_answers:
            flash('Please answer all verification questions before submitting your claim.', 'danger')
            return render_template('claims/submit.html', form=form, report=report, questions=questions)

        claim = Claim(
            report_id=report.id,
            claimant_id=current_user.id,
            claim_description=form.claim_description.data.strip(),
            claim_status='pending',
        )
        db.session.add(claim)
        db.session.flush()

        for question, ans_text in answers_payload:
            db.session.add(
                ClaimAnswer(
                    claim_id=claim.id,
                    question_id=question.id,
                    answer=ans_text,
                )
            )

        evidence_path = _save_evidence_file(form.evidence_file.data)
        if evidence_path or (form.evidence_description.data and form.evidence_description.data.strip()):
            db.session.add(
                ClaimEvidence(
                    claim_id=claim.id,
                    evidence_type=form.evidence_type.data or 'description',
                    evidence_path=evidence_path,
                    description=(
                        form.evidence_description.data.strip() if form.evidence_description.data else None
                    ),
                )
            )

        db.session.add(
            Notification(
                user_id=report.user_id,
                title='New Claim Submitted',
                message=f'{current_user.username} submitted a claim on your report "{report.title}".',
                notification_type='claim',
            )
        )
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action='submit_claim',
                entity_type='claim',
                entity_id=claim.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash('Your claim has been submitted for review.', 'success')
        return redirect(url_for('claims.detail', id=claim.id))

    return render_template('claims/submit.html', form=form, report=report, questions=questions)


@claims_bp.route('/<int:id>', methods=['GET'])
@login_required
def detail(id):
    """View details, verification answers, evidence, and reviews for a claim."""
    claim = db.get_or_404(Claim, id)
    if claim.claimant_id != current_user.id and not _can_review_claim(claim, current_user):
        abort(403)

    review_form = ClaimReviewForm()
    can_review = _can_review_claim(claim, current_user)
    return render_template(
        'claims/detail.html',
        claim=claim,
        review_form=review_form,
        can_review=can_review,
    )


@claims_bp.route('/<int:id>/review', methods=['GET', 'POST'])
@login_required
def review(id):
    """Review and approve/reject a submitted claim."""
    claim = db.get_or_404(Claim, id)
    if not _can_review_claim(claim, current_user):
        abort(403)

    form = ClaimReviewForm()
    if form.validate_on_submit():
        decision = form.decision.data
        notes = form.review_notes.data.strip()

        db.session.add(
            ClaimReview(
                claim_id=claim.id,
                reviewer_id=current_user.id,
                decision=decision,
                review_notes=notes,
            )
        )
        claim.claim_status = decision

        if decision == 'approved':
            claimed_status = ReportStatus.query.filter(
                func.lower(ReportStatus.status_name) == 'claimed'
            ).first()
            if claimed_status is None:
                claimed_status = ReportStatus(
                    status_name='claimed',
                    description='Item claim approved',
                )
                db.session.add(claimed_status)
                db.session.flush()

            if claim.report.status_id != claimed_status.id:
                old_status_id = claim.report.status_id
                claim.report.status_id = claimed_status.id
                db.session.add(
                    ReportStatusHistory(
                        report_id=claim.report.id,
                        old_status_id=old_status_id,
                        new_status_id=claimed_status.id,
                        changed_by=current_user.id,
                        change_reason=f'Claim #{claim.id} approved',
                    )
                )

        db.session.add(
            Notification(
                user_id=claim.claimant_id,
                title=f'Claim {decision.title()}',
                message=f'Your claim on "{claim.report.title}" was {decision}.',
                notification_type='claim',
            )
        )
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action=f'review_claim_{decision}',
                entity_type='claim',
                entity_id=claim.id,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
        flash(f'Claim has been {decision}.', 'success')
        return redirect(url_for('claims.detail', id=claim.id))

    return render_template('claims/review.html', claim=claim, form=form)


@claims_bp.route('/my-claims', methods=['GET'])
@login_required
def my_claims():
    """List claims submitted by the current user and claims received on their reports."""
    submitted_claims = (
        Claim.query.filter_by(claimant_id=current_user.id)
        .order_by(Claim.submitted_at.desc())
        .all()
    )
    received_claims = (
        Claim.query.join(ItemReport, Claim.report_id == ItemReport.id)
        .filter(ItemReport.user_id == current_user.id)
        .order_by(Claim.submitted_at.desc())
        .all()
    )
    return render_template(
        'claims/my_claims.html',
        submitted_claims=submitted_claims,
        received_claims=received_claims,
    )


@claims_bp.route('/questions/<int:report_id>', methods=['GET', 'POST'])
@login_required
def manage_questions(report_id):
    """Create verification questions for an item report."""
    report = db.get_or_404(ItemReport, report_id)
    if (
        report.user_id != current_user.id
        and not current_user.has_role('security')
        and not current_user.has_role('admin')
    ):
        abort(403)

    form = VerificationQuestionForm()
    if form.validate_on_submit():
        db.session.add(
            VerificationQuestion(
                report_id=report.id,
                question=form.question.data.strip(),
            )
        )
        db.session.commit()
        flash('Verification question added.', 'success')
        return redirect(url_for('claims.manage_questions', report_id=report.id))

    questions = VerificationQuestion.query.filter_by(report_id=report.id).all()
    return render_template('claims/questions.html', report=report, questions=questions, form=form)
