"""Item Classification models — 6 tables."""
from ..extensions import db


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50))

    subcategories = db.relationship('Subcategory', backref='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Category {self.category_name}>'


class Subcategory(db.Model):
    __tablename__ = 'subcategories'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    subcategory_name = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<Subcategory {self.subcategory_name}>'


class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Brand {self.brand_name}>'


class ItemCondition(db.Model):
    __tablename__ = 'item_conditions'
    id = db.Column(db.Integer, primary_key=True)
    condition_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<ItemCondition {self.condition_name}>'


class ReportType(db.Model):
    __tablename__ = 'report_types'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(20), unique=True, nullable=False)  # 'lost' or 'found'

    def __repr__(self):
        return f'<ReportType {self.type_name}>'


class ReportStatus(db.Model):
    __tablename__ = 'report_statuses'
    id = db.Column(db.Integer, primary_key=True)
    status_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<ReportStatus {self.status_name}>'
