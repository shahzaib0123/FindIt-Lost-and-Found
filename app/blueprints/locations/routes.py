"""Routes for the locations blueprint."""
from flask import render_template, request
from app.extensions import db
from app.models.location import Building, CampusZone, Location
from app.models.reporting import ItemReport, ReportLocation
from . import locations_bp


@locations_bp.route('/', methods=['GET'])
def index():
    """List all campus locations with optional campus zone filtering."""
    zone_id = request.args.get('zone_id', type=int)
    query = Location.query
    if zone_id:
        query = query.filter_by(zone_id=zone_id)

    all_locations = query.order_by(Location.location_name).all()
    zones = CampusZone.query.order_by(CampusZone.zone_name).all()
    return render_template(
        'locations/list.html',
        locations=all_locations,
        zones=zones,
        selected_zone_id=zone_id,
    )


@locations_bp.route('/<int:id>', methods=['GET'])
def detail(id):
    """Display details for a campus location and item reports tied to it."""
    location = db.get_or_404(Location, id)
    reports = (
        ItemReport.query.join(ReportLocation)
        .filter(ReportLocation.location_id == location.id)
        .order_by(ItemReport.created_at.desc())
        .all()
    )
    return render_template('locations/detail.html', location=location, reports=reports)


@locations_bp.route('/zones', methods=['GET'])
def zones():
    """List all campus zones."""
    all_zones = CampusZone.query.order_by(CampusZone.zone_name).all()
    return render_template('locations/zones.html', zones=all_zones)


@locations_bp.route('/buildings', methods=['GET'])
def buildings():
    """List all campus buildings."""
    all_buildings = Building.query.order_by(Building.building_name).all()
    return render_template('locations/buildings.html', buildings=all_buildings)


@locations_bp.route('/buildings/<int:id>', methods=['GET'])
def building_detail(id):
    """Display building details, floors, rooms, and locations."""
    building = db.get_or_404(Building, id)
    return render_template('locations/building_detail.html', building=building)
