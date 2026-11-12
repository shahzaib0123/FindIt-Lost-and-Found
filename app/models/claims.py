"""Claims & Verification models — 7 tables."""
from datetime import datetime, timezone
from ..extensions import db


class Claim(db.Model):
    __tablename__ = 'claims'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    claim_description = db.Column(db.Text, nullable=False)
    claim_status = db.Column(db.String(30), default='pending')  # pending, approved, rejected
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    evidence = db.relationship('ClaimEvidence', backref='claim', cascade='all, delete-orphan')
    answers = db.relationship('ClaimAnswer', backref='claim', cascade='all, delete-orphan')
    reviews = db.relationship('ClaimReview', backref='claim', cascade='all, delete-orphan')
    appointment = db.relationship('HandoverAppointment', backref='claim', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Claim {self.id} for Report {self.report_id}>'


class ClaimEvidence(db.Model):
    __tablename__ = 'claim_evidence'
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    evidence_type = db.Column(db.String(30), nullable=False)  # photo, receipt, description
    evidence_path = db.Column(db.String(256))
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class VerificationQuestion(db.Model):
    __tablename__ = 'verification_questions'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)


class ClaimAnswer(db.Model):
    __tablename__ = 'claim_answers'
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('verification_questions.id'), nullable=False)
    answer = db.Column(db.Text, nullable=False)

    question = db.relationship('VerificationQuestion', backref='answers')


class ClaimReview(db.Model):
    __tablename__ = 'claim_reviews'
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    decision = db.Column(db.String(30), nullable=False)  # approved, rejected
    review_notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    reviewer = db.relationship('User', backref='claim_reviews')


class HandoverAppointment(db.Model):
    __tablename__ = 'handover_appointments'
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    appointment_status = db.Column(db.String(30), default='scheduled')  # scheduled, completed, cancelled

    location = db.relationship('Location', backref='appointments')
    record = db.relationship('HandoverRecord', backref='appointment', uselist=False, cascade='all, delete-orphan')


class HandoverRecord(db.Model):
    __tablename__ = 'handover_records'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('handover_appointments.id'), nullable=False, unique=True)
    handed_over_by = db.Column(db.Integer, db.ForeignKey('security_staff.id'), nullable=False)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    handover_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    id_checked = db.Column(db.Boolean, default=False)
    confirmation_status = db.Column(db.String(30), default='pending')  # pending, confirmed

    staff = db.relationship('SecurityStaff', backref='handover_records')
    receiver = db.relationship('User', backref='received_handovers')
