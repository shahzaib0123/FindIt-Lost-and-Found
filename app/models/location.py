"""Campus Locations models — 5 tables."""
from ..extensions import db


class CampusZone(db.Model):
    __tablename__ = 'campus_zones'
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(80), unique=True, nullable=False)

    buildings = db.relationship('Building', backref='zone', cascade='all, delete-orphan')
    locations = db.relationship('Location', backref='zone')
    patrol_zones = db.relationship('PatrolZone', backref='campus_zone')

    def __repr__(self):
        return f'<CampusZone {self.zone_name}>'


class Building(db.Model):
    __tablename__ = 'buildings'
    id = db.Column(db.Integer, primary_key=True)
    building_name = db.Column(db.String(100), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('campus_zones.id'), nullable=False)

    floors = db.relationship('Floor', backref='building', cascade='all, delete-orphan')
    locations = db.relationship('Location', backref='building')
    storage_locations = db.relationship('StorageLocation', backref='building')

    def __repr__(self):
        return f'<Building {self.building_name}>'


class Floor(db.Model):
    __tablename__ = 'floors'
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    floor_number = db.Column(db.Integer, nullable=False)

    rooms = db.relationship('Room', backref='floor', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Floor {self.floor_number} of Building {self.building_id}>'


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id'), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)

    locations = db.relationship('Location', backref='room')

    def __repr__(self):
        return f'<Room {self.room_number}>'


class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(150), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('campus_zones.id'), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    report_locations = db.relationship('ReportLocation', backref='location')

    def __repr__(self):
        return f'<Location {self.location_name}>'
