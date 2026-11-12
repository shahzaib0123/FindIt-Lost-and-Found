"""Reporting models — 4 tables."""
from datetime import datetime, timezone
from ..extensions import db


class ItemReport(db.Model):
    __tablename__ = 'item_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=True)
    condition_id = db.Column(db.Integer, db.ForeignKey('item_conditions.id'), nullable=True)
    report_type_id = db.Column(db.Integer, db.ForeignKey('report_types.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('report_statuses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = db.relationship('Category', backref='item_reports')
    subcategory = db.relationship('Subcategory', backref='item_reports')
    brand = db.relationship('Brand', backref='item_reports')
    condition = db.relationship('ItemCondition', backref='item_reports')
    report_type = db.relationship('ReportType', backref='item_reports')
    status = db.relationship('ReportStatus', backref='item_reports')
    report_location = db.relationship('ReportLocation', backref='report', uselist=False, cascade='all, delete-orphan')
    images = db.relationship('ItemImage', backref='report', cascade='all, delete-orphan')
    status_history = db.relationship('ReportStatusHistory', backref='report', cascade='all, delete-orphan')
    tags = db.relationship('ReportTag', backref='report', cascade='all, delete-orphan')
    claims = db.relationship('Claim', backref='report', cascade='all, delete-orphan')
    verification_questions = db.relationship('VerificationQuestion', backref='report', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='report')

    def __repr__(self):
        return f'<ItemReport {self.title}>'


class ReportLocation(db.Model):
    __tablename__ = 'report_locations'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False, unique=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    specific_location = db.Column(db.String(200))


class ItemImage(db.Model):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    image_path = db.Column(db.String(256), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ReportStatusHistory(db.Model):
    __tablename__ = 'report_status_history'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    old_status_id = db.Column(db.Integer, db.ForeignKey('report_statuses.id'), nullable=True)
    new_status_id = db.Column(db.Integer, db.ForeignKey('report_statuses.id'), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    change_reason = db.Column(db.String(300))
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    changer = db.relationship('User', backref='status_changes')
    old_status = db.relationship('ReportStatus', foreign_keys=[old_status_id])
    new_status = db.relationship('ReportStatus', foreign_keys=[new_status_id])
