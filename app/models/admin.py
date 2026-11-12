"""Admin & Moderation models — 4 tables."""
from datetime import datetime, timezone
from ..extensions import db


class UserReport(db.Model):
    __tablename__ = 'user_reports'
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default='pending')  # pending, reviewed, resolved
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='filed_reports')
    reported_user = db.relationship('User', foreign_keys=[reported_user_id], backref='reports_against')


class ModerationAction(db.Model):
    __tablename__ = 'moderation_actions'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # user, report, claim
    target_id = db.Column(db.Integer, nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # warn, suspend, delete, reinstate
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin = db.relationship('User', backref='moderation_actions')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='audit_logs')


class VerificationToken(db.Model):
    __tablename__ = 'verification_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(256), unique=True, nullable=False)
    token_type = db.Column(db.String(30), nullable=False)  # email_verify, password_reset
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='verification_tokens')
