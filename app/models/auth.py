"""Auth & Users models — 7 tables."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    user_roles = db.relationship('UserRole', backref='user', cascade='all, delete-orphan')
    contacts = db.relationship('UserContact', backref='user', cascade='all, delete-orphan')
    item_reports = db.relationship('ItemReport', backref='reporter', foreign_keys='ItemReport.user_id')
    claims = db.relationship('Claim', backref='claimant', foreign_keys='Claim.claimant_id')
    sent_messages = db.relationship('Message', backref='sender', foreign_keys='Message.sender_id')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(ur.role.role_name == role_name for ur in self.user_roles)

    def __repr__(self):
        return f'<User {self.username}>'


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    profile_picture = db.Column(db.String(256))
    bio = db.Column(db.Text)
    department = db.Column(db.String(100))
    reg_no = db.Column(db.String(50))

    def full_name(self):
        return f'{self.first_name or ""} {self.last_name or ""}'.strip() or self.user.username


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    role_permissions = db.relationship('RolePermission', backref='role', cascade='all, delete-orphan')
    user_roles = db.relationship('UserRole', backref='role', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Role {self.role_name}>'


class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    permission_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200))

    role_permissions = db.relationship('RolePermission', backref='permission', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Permission {self.permission_name}>'


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'role_id'),)


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id'),)


class UserContact(db.Model):
    __tablename__ = 'user_contacts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_type = db.Column(db.String(30), nullable=False)   # phone, whatsapp, etc.
    contact_value = db.Column(db.String(120), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
