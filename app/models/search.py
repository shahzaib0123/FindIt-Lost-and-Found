"""Search & Matching models — 5 tables."""
from datetime import datetime, timezone
from ..extensions import db


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(50), unique=True, nullable=False)

    report_tags = db.relationship('ReportTag', backref='tag', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tag {self.tag_name}>'


class ReportTag(db.Model):
    __tablename__ = 'report_tags'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('report_id', 'tag_id'),)


class SavedSearch(db.Model):
    __tablename__ = 'saved_searches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_name = db.Column(db.String(100), nullable=False)
    keyword = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='saved_searches')
    filters = db.relationship('SavedSearchFilter', backref='saved_search', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SavedSearch {self.search_name}>'


class SavedSearchFilter(db.Model):
    __tablename__ = 'saved_search_filters'
    id = db.Column(db.Integer, primary_key=True)
    saved_search_id = db.Column(db.Integer, db.ForeignKey('saved_searches.id'), nullable=False)
    filter_name = db.Column(db.String(50), nullable=False)
    filter_value = db.Column(db.String(200), nullable=False)


class ItemMatch(db.Model):
    __tablename__ = 'item_matches'
    id = db.Column(db.Integer, primary_key=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    found_report_id = db.Column(db.Integer, db.ForeignKey('item_reports.id'), nullable=False)
    match_score = db.Column(db.Float, default=0.0)
    match_method = db.Column(db.String(50))  # 'auto', 'manual'
    match_status = db.Column(db.String(30), default='pending')  # pending, confirmed, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lost_report = db.relationship('ItemReport', foreign_keys=[lost_report_id], backref='lost_matches')
    found_report = db.relationship('ItemReport', foreign_keys=[found_report_id], backref='found_matches')

    def __repr__(self):
        return f'<ItemMatch lost={self.lost_report_id} found={self.found_report_id} score={self.match_score}>'
