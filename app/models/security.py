"""Security & Custody models — 6 tables."""
from datetime import datetime, timezone
from ..extensions import db


class SecurityStaff(db.Model):
    __tablename__ = 'security_staff'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    badge_no = db.Column(db.String(30), unique=True, nullable=False)
    post = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('security_profile', uselist=False))
    shifts = db.relationship('Shift', backref='staff', cascade='all, delete-orphan')
    custody_logs = db.relationship('CustodyLog', backref='staff')

    def __repr__(self):
        return f'<SecurityStaff {self.badge_no}>'


class PatrolZone(db.Model):
    __tablename__ = 'patrol_zones'
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(80), unique=True, nullable=False)
    campus_zone_id = db.Column(db.Integer, db.ForeignKey('campus_zones.id'), nullable=False)

    shifts = db.relationship('Shift', backref='patrol_zone')

    def __repr__(self):
        return f'<PatrolZone {self.zone_name}>'


class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('security_staff.id'), nullable=False)
    patrol_zone_id = db.Column(db.Integer, db.ForeignKey('patrol_zones.id'), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)


class StorageLocation(db.Model):
    __tablename__ = 'storage_locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    capacity = db.Column(db.Integer, default=50)

    custody_logs = db.relationship('CustodyLog', backref='storage_location')

    def __repr__(self):
        return f'<StorageLocation {self.name}>'


class CustodyLog(db.Model):
    __tablename__ = 'custody_logs'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('security_staff.id'), nullable=False)
    storage_location_id = db.Column(db.Integer, db.ForeignKey('storage_locations.id'), nullable=False)
    action = db.Column(db.String(30), nullable=False)  # received, released, transferred
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    report = db.relationship('ItemReport', backref='custody_logs')


class IncidentReport(db.Model):
    __tablename__ = 'incident_reports'
    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('security_staff.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='low')  # low, medium, high, critical
    incident_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    reporter_user = db.relationship('User', backref='incident_reports')
    staff = db.relationship('SecurityStaff', backref='incident_reports')
    location = db.relationship('Location', backref='incidents')
    item_report = db.relationship('ItemReport', backref='incidents')
