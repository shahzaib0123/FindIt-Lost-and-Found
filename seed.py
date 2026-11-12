"""Idempotent database seeding script for the FindIt Lost & Found platform."""
import hashlib
from datetime import date, datetime, time, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models.admin import AuditLog, ModerationAction, UserReport, VerificationToken
from app.models.auth import (
    Permission,
    Role,
    RolePermission,
    User,
    UserContact,
    UserProfile,
    UserRole,
)
from app.models.claims import (
    Claim,
    ClaimAnswer,
    ClaimEvidence,
    ClaimReview,
    HandoverAppointment,
    HandoverRecord,
    VerificationQuestion,
)
from app.models.classification import (
    Brand,
    Category,
    ItemCondition,
    ReportStatus,
    ReportType,
    Subcategory,
)
from app.models.communication import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)
from app.models.location import Building, CampusZone, Floor, Location, Room
from app.models.reporting import (
    ItemReport,
    ReportLocation,
    ReportStatusHistory,
)
from app.models.search import (
    ItemMatch,
    ReportTag,
    SavedSearch,
    SavedSearchFilter,
    Tag,
)
from app.models.security import (
    CustodyLog,
    IncidentReport,
    PatrolZone,
    SecurityStaff,
    Shift,
    StorageLocation,
)


def _get_or_create(model, defaults=None, **kwargs):
    """Return existing instance matching kwargs or create a new one."""
    instance = model.query.filter_by(**kwargs).first()
    if instance is not None:
        return instance, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def seed_auth():
    """Seed roles, permissions, role-permission mappings, and demo users."""
    roles_data = [
        ('user', 'Standard campus student or staff member'),
        ('security', 'Campus security officer managing custody, shifts, and handovers'),
        ('admin', 'System administrator with full moderation and configuration access'),
    ]
    roles = {}
    for role_name, desc in roles_data:
        role, _ = _get_or_create(Role, defaults={'description': desc}, role_name=role_name)
        roles[role_name] = role

    permissions_data = [
        ('create_report', 'Submit lost and found item reports'),
        ('edit_own_report', 'Edit or delete own item reports'),
        ('submit_claim', 'Submit ownership claims on reported items'),
        ('review_claim', 'Approve or reject ownership claims'),
        ('manage_custody', 'Log item custody and storage transfers'),
        ('manage_incidents', 'Create and manage security incident reports'),
        ('manage_shifts', 'Schedule and view security patrol shifts'),
        ('manage_users', 'Activate, deactivate, and inspect user accounts'),
        ('moderate_content', 'Review user complaints and apply moderation actions'),
        ('view_audit_logs', 'Inspect system-wide audit logs'),
    ]
    permissions = {}
    for perm_name, desc in permissions_data:
        perm, _ = _get_or_create(
            Permission, defaults={'description': desc}, permission_name=perm_name
        )
        permissions[perm_name] = perm

    role_perm_map = {
        'user': ['create_report', 'edit_own_report', 'submit_claim'],
        'security': [
            'create_report',
            'edit_own_report',
            'submit_claim',
            'review_claim',
            'manage_custody',
            'manage_incidents',
            'manage_shifts',
        ],
        'admin': list(permissions.keys()),
    }
    for role_name, perm_names in role_perm_map.items():
        role = roles[role_name]
        for perm_name in perm_names:
            _get_or_create(
                RolePermission,
                role_id=role.id,
                permission_id=permissions[perm_name].id,
            )

    demo_users_spec = [
        {
            'email': 'admin@findit.edu',
            'username': 'admin',
            'password': 'Admin@1234',
            'role': 'admin',
            'first_name': 'Elena',
            'last_name': 'Vance',
            'department': 'Campus IT & Operations',
            'reg_no': 'ADM-001',
            'bio': 'FindIt platform administrator overseeing campus lost-and-found operations.',
            'contact': ('phone', '+1-555-0100'),
        },
        {
            'email': 'security@findit.edu',
            'username': 'security_officer',
            'password': 'Security@1234',
            'role': 'security',
            'first_name': 'Marcus',
            'last_name': 'Reid',
            'department': 'Campus Safety & Security',
            'reg_no': 'SEC-104',
            'bio': 'Lead campus security officer at the Central Lost & Found Custody Desk.',
            'contact': ('phone', '+1-555-0199'),
        },
        {
            'email': 'student1@findit.edu',
            'username': 'alex_chen',
            'password': 'Student@1234',
            'role': 'user',
            'first_name': 'Alex',
            'last_name': 'Chen',
            'department': 'Computer Science',
            'reg_no': 'STU-2024-118',
            'bio': 'Junior CS undergraduate. Frequently studies in the Main Library.',
            'contact': ('whatsapp', '+1-555-0142'),
        },
        {
            'email': 'student2@findit.edu',
            'username': 'maya_patel',
            'password': 'Student@1234',
            'role': 'user',
            'first_name': 'Maya',
            'last_name': 'Patel',
            'department': 'Electrical Engineering',
            'reg_no': 'STU-2025-209',
            'bio': 'EE sophomore and robotics club member.',
            'contact': ('phone', '+1-555-0175'),
        },
    ]

    users = {}
    for spec in demo_users_spec:
        user = User.query.filter_by(email=spec['email']).first()
        if user is None:
            user = User(
                username=spec['username'],
                email=spec['email'],
                is_active=True,
                is_verified=True,
            )
            user.set_password(spec['password'])
            db.session.add(user)
            db.session.flush()

        _get_or_create(
            UserProfile,
            defaults={
                'first_name': spec['first_name'],
                'last_name': spec['last_name'],
                'department': spec['department'],
                'reg_no': spec['reg_no'],
                'bio': spec['bio'],
            },
            user_id=user.id,
        )
        _get_or_create(UserRole, user_id=user.id, role_id=roles[spec['role']].id)
        _get_or_create(
            UserContact,
            defaults={'is_primary': True},
            user_id=user.id,
            contact_type=spec['contact'][0],
            contact_value=spec['contact'][1],
        )
        users[spec['email']] = user

    token_hash = hashlib.sha256(b'seed-verified-student1-token').hexdigest()
    _get_or_create(
        VerificationToken,
        defaults={
            'user_id': users['student1@findit.edu'].id,
            'token_type': 'email_verify',
            'expires_at': datetime.now(timezone.utc) + timedelta(days=7),
            'used_at': datetime.now(timezone.utc),
        },
        token_hash=token_hash,
    )

    return users


def seed_classification():
    """Seed categories, subcategories, brands, conditions, report types, and statuses."""
    categories_spec = [
        ('Electronics', 'Phones, laptops, tablets, headphones, and chargers', 'bi-laptop',
         ['Laptop', 'Smartphone', 'Headphones', 'Charger / Adapter']),
        ('Bags & Backpacks', 'Backpacks, messenger bags, and laptop sleeves', 'bi-backpack',
         ['Backpack', 'Laptop Bag', 'Tote Bag']),
        ('Wallets & IDs', 'Wallets, student ID cards, and credit/debit cards', 'bi-wallet2',
         ['Wallet', 'Student ID Card', 'Cardholder']),
        ('Keys & Access Cards', 'Room keys, car fobs, and building keycards', 'bi-key',
         ['Keychain', 'Keycard / Fob']),
        ('Books & Stationery', 'Textbooks, notebooks, calculators, and pens', 'bi-book',
         ['Textbook', 'Notebook', 'Calculator']),
        ('Accessories', 'Glasses, watches, water bottles, and umbrellas', 'bi-watch',
         ['Eyeglasses', 'Water Bottle', 'Watch']),
    ]

    categories = {}
    subcategories = {}
    for cat_name, desc, icon, sub_names in categories_spec:
        cat, _ = _get_or_create(
            Category,
            defaults={'description': desc, 'icon': icon},
            category_name=cat_name,
        )
        categories[cat_name] = cat
        for sub_name in sub_names:
            sub, _ = _get_or_create(
                Subcategory,
                category_id=cat.id,
                subcategory_name=sub_name,
            )
            subcategories[sub_name] = sub

    brands_spec = [
        ('Apple', 'Consumer electronics and accessories'),
        ('Samsung', 'Smartphones, tablets, and electronics'),
        ('Dell', 'Laptops and computing peripherals'),
        ('Sony', 'Audio headphones and electronics'),
        ('Jansport', 'Campus backpacks and bags'),
        ('Hydro Flask', 'Insulated water bottles'),
        ('Casio', 'Scientific calculators and watches'),
        ('Generic / Unbranded', 'Items without a visible brand label'),
    ]
    brands = {}
    for brand_name, desc in brands_spec:
        brand, _ = _get_or_create(
            Brand, defaults={'description': desc}, brand_name=brand_name
        )
        brands[brand_name] = brand

    conditions_spec = [
        ('New', 'Brand new with minimal or no signs of use'),
        ('Good', 'Clean and fully functional with minor wear'),
        ('Fair', 'Visible scratches or wear from regular use'),
        ('Damaged', 'Cracked, torn, or partially non-functional'),
    ]
    conditions = {}
    for cond_name, desc in conditions_spec:
        cond, _ = _get_or_create(
            ItemCondition, defaults={'description': desc}, condition_name=cond_name
        )
        conditions[cond_name] = cond

    report_types = {}
    for type_name in ('lost', 'found'):
        rt, _ = _get_or_create(ReportType, type_name=type_name)
        report_types[type_name] = rt

    statuses_spec = [
        ('open', 'Active report awaiting match or claim'),
        ('matched', 'Potential lost/found match identified'),
        ('claimed', 'Ownership claim approved and awaiting/undergoing handover'),
        ('returned', 'Item verified and returned to its rightful owner'),
        ('closed', 'Report archived or resolved without handover'),
    ]
    statuses = {}
    for status_name, desc in statuses_spec:
        st, _ = _get_or_create(
            ReportStatus, defaults={'description': desc}, status_name=status_name
        )
        statuses[status_name] = st

    return {
        'categories': categories,
        'subcategories': subcategories,
        'brands': brands,
        'conditions': conditions,
        'report_types': report_types,
        'statuses': statuses,
    }


def seed_locations():
    """Seed campus zones, buildings, floors, rooms, and locations."""
    zones_names = [
        'North Academic Zone',
        'Central Library Zone',
        'Student Union Zone',
        'Residence Halls Zone',
    ]
    zones = {}
    for zname in zones_names:
        zone, _ = _get_or_create(CampusZone, zone_name=zname)
        zones[zname] = zone

    buildings_spec = [
        ('Main Library', 'Central Library Zone'),
        ('Engineering Hall', 'North Academic Zone'),
        ('Student Union Center', 'Student Union Zone'),
        ('Campus Security Annex', 'Student Union Zone'),
        ('Oak Residence Hall', 'Residence Halls Zone'),
    ]
    buildings = {}
    for bname, zname in buildings_spec:
        bld, _ = _get_or_create(
            Building,
            building_name=bname,
            zone_id=zones[zname].id,
        )
        buildings[bname] = bld

    floors_spec = [
        ('Main Library', 1),
        ('Main Library', 2),
        ('Engineering Hall', 1),
        ('Engineering Hall', 3),
        ('Student Union Center', 1),
        ('Campus Security Annex', 1),
    ]
    floors = {}
    for bname, fnum in floors_spec:
        flr, _ = _get_or_create(
            Floor,
            building_id=buildings[bname].id,
            floor_number=fnum,
        )
        floors[(bname, fnum)] = flr

    rooms_spec = [
        (('Main Library', 2), '204-Reading'),
        (('Engineering Hall', 3), '302-Lab'),
        (('Student Union Center', 1), '110-FoodCourt'),
        (('Campus Security Annex', 1), '101-Desk'),
    ]
    rooms = {}
    for flr_key, rnum in rooms_spec:
        rm, _ = _get_or_create(
            Room,
            floor_id=floors[flr_key].id,
            room_number=rnum,
        )
        rooms[rnum] = rm

    locations_spec = [
        ('Main Library - 2nd Floor Quiet Study', 'Central Library Zone', 'Main Library', '204-Reading', 37.8719, -122.2595),
        ('Engineering Hall - Room 302 Computer Lab', 'North Academic Zone', 'Engineering Hall', '302-Lab', 37.8745, -122.2582),
        ('Student Union - Ground Floor Food Court', 'Student Union Zone', 'Student Union Center', '110-FoodCourt', 37.8692, -122.2598),
        ('Campus Security - Lost & Found Desk', 'Student Union Zone', 'Campus Security Annex', '101-Desk', 37.8696, -122.2604),
        ('Oak Residence Hall - Main Courtyard', 'Residence Halls Zone', 'Oak Residence Hall', None, 37.8668, -122.2621),
    ]
    locations = {}
    for lname, zname, bname, rnum, lat, lng in locations_spec:
        loc, _ = _get_or_create(
            Location,
            defaults={
                'zone_id': zones[zname].id,
                'building_id': buildings[bname].id,
                'room_id': rooms[rnum].id if rnum else None,
                'latitude': lat,
                'longitude': lng,
            },
            location_name=lname,
        )
        locations[lname] = loc

    return {
        'zones': zones,
        'buildings': buildings,
        'floors': floors,
        'rooms': rooms,
        'locations': locations,
    }


def seed_security(users, loc_data):
    """Seed security staff, patrol zones, shifts, and storage locations."""
    sec_user = users['security@findit.edu']
    staff, _ = _get_or_create(
        SecurityStaff,
        defaults={'badge_no': 'SEC-1040', 'post': 'Central Lost & Found Desk'},
        user_id=sec_user.id,
    )

    patrol_zones_spec = [
        ('Central Library Patrol', 'Central Library Zone'),
        ('North Academic Patrol', 'North Academic Zone'),
        ('Union & Plaza Patrol', 'Student Union Zone'),
    ]
    patrol_zones = {}
    for pz_name, cz_name in patrol_zones_spec:
        pz, _ = _get_or_create(
            PatrolZone,
            defaults={'campus_zone_id': loc_data['zones'][cz_name].id},
            zone_name=pz_name,
        )
        patrol_zones[pz_name] = pz

    today = date.today()
    shifts_spec = [
        (staff.id, patrol_zones['Central Library Patrol'].id, today, time(8, 0), time(16, 0)),
        (staff.id, patrol_zones['Union & Plaza Patrol'].id, today + timedelta(days=1), time(9, 0), time(17, 0)),
    ]
    for s_id, pz_id, s_date, t_start, t_end in shifts_spec:
        _get_or_create(
            Shift,
            staff_id=s_id,
            patrol_zone_id=pz_id,
            shift_date=s_date,
            start_time=t_start,
            end_time=t_end,
        )

    storage_spec = [
        ('Security Desk Vault A (Electronics)', 'Campus Security Annex', 40),
        ('Security Desk Shelf B (General Items)', 'Campus Security Annex', 80),
        ('Library Front Desk Lockbox', 'Main Library', 25),
    ]
    storage_locs = {}
    for sname, bname, cap in storage_spec:
        sl, _ = _get_or_create(
            StorageLocation,
            defaults={
                'building_id': loc_data['buildings'][bname].id,
                'capacity': cap,
            },
            name=sname,
        )
        storage_locs[sname] = sl

    return {
        'staff': staff,
        'patrol_zones': patrol_zones,
        'storage_locations': storage_locs,
    }


def seed_reports_and_workflows(users, cls_data, loc_data, sec_data):
    """Seed item reports, tags, matches, searches, claims, custody, incidents, and comms."""
    student1 = users['student1@findit.edu']
    student2 = users['student2@findit.edu']
    security_user = users['security@findit.edu']
    admin_user = users['admin@findit.edu']

    cats = cls_data['categories']
    subs = cls_data['subcategories']
    brands = cls_data['brands']
    conds = cls_data['conditions']
    rtypes = cls_data['report_types']
    statuses = cls_data['statuses']
    locs = loc_data['locations']

    today = date.today()

    reports_spec = [
        {
            'key': 'lost_airpods',
            'user': student1,
            'category': 'Electronics',
            'subcategory': 'Headphones',
            'brand': 'Apple',
            'condition': 'Good',
            'type': 'lost',
            'status': 'matched',
            'title': 'Apple AirPods Pro (2nd Gen) in White Case',
            'description': 'Lost white AirPods Pro charging case near the 2nd floor quiet study desks. Case has a small blue silicone lanyard attached.',
            'event_date': today - timedelta(days=3),
            'location': 'Main Library - 2nd Floor Quiet Study',
            'specific': 'Window desk #14 near east staircase',
            'tags': ['airpods', 'white', 'bluetooth', 'library'],
        },
        {
            'key': 'found_airpods',
            'user': student2,
            'category': 'Electronics',
            'subcategory': 'Headphones',
            'brand': 'Apple',
            'condition': 'Good',
            'type': 'found',
            'status': 'matched',
            'title': 'Found White Wireless Earbuds Case in Library',
            'description': 'Found an Apple wireless earbuds charging case on a study table on the 2nd floor of Main Library. Turned in to Security Desk.',
            'event_date': today - timedelta(days=2),
            'location': 'Main Library - 2nd Floor Quiet Study',
            'specific': 'East wing quiet study area',
            'tags': ['airpods', 'earbuds', 'library'],
        },
        {
            'key': 'found_backpack',
            'user': security_user,
            'category': 'Bags & Backpacks',
            'subcategory': 'Backpack',
            'brand': 'Jansport',
            'condition': 'Good',
            'type': 'found',
            'status': 'claimed',
            'title': 'Navy Blue JanSport Backpack with Engineering Notebook',
            'description': 'Found unattended navy backpack in Engineering Hall Lab 302. Contains a spiral notebook and USB-C cable.',
            'event_date': today - timedelta(days=4),
            'location': 'Engineering Hall - Room 302 Computer Lab',
            'specific': 'Back row workstation #8',
            'tags': ['backpack', 'navy', 'jansport', 'engineering'],
        },
        {
            'key': 'lost_calculator',
            'user': student2,
            'category': 'Books & Stationery',
            'subcategory': 'Calculator',
            'brand': 'Casio',
            'condition': 'Fair',
            'type': 'lost',
            'status': 'open',
            'title': 'Casio fx-991EX Scientific Calculator',
            'description': 'Left my black Casio scientific calculator after circuit analysis lab. Initials M.P. written lightly inside the slide cover.',
            'event_date': today - timedelta(days=1),
            'location': 'Engineering Hall - Room 302 Computer Lab',
            'specific': 'Front bench near oscilloscope station',
            'tags': ['calculator', 'casio', 'engineering'],
        },
        {
            'key': 'found_bottle',
            'user': security_user,
            'category': 'Accessories',
            'subcategory': 'Water Bottle',
            'brand': 'Hydro Flask',
            'condition': 'Good',
            'type': 'found',
            'status': 'open',
            'title': 'Teal Hydro Flask 32oz Insulated Bottle',
            'description': 'Teal stainless water bottle with two campus robotics stickers found near the Student Union food court seating.',
            'event_date': today - timedelta(days=1),
            'location': 'Student Union - Ground Floor Food Court',
            'specific': 'Table near coffee kiosk',
            'tags': ['water-bottle', 'hydro-flask', 'teal'],
        },
        {
            'key': 'lost_wallet',
            'user': student1,
            'category': 'Wallets & IDs',
            'subcategory': 'Wallet',
            'brand': 'Generic / Unbranded',
            'condition': 'Good',
            'type': 'lost',
            'status': 'returned',
            'title': 'Brown Leather Bifold Wallet with Student ID',
            'description': 'Misplaced brown leather wallet containing university ID card and transit pass near Oak Residence Hall courtyard.',
            'event_date': today - timedelta(days=7),
            'location': 'Oak Residence Hall - Main Courtyard',
            'specific': 'Benches outside north entrance',
            'tags': ['wallet', 'leather', 'student-id'],
        },
    ]

    reports = {}
    for spec in reports_spec:
        report, created = _get_or_create(
            ItemReport,
            defaults={
                'user_id': spec['user'].id,
                'category_id': cats[spec['category']].id,
                'subcategory_id': subs[spec['subcategory']].id,
                'brand_id': brands[spec['brand']].id,
                'condition_id': conds[spec['condition']].id,
                'report_type_id': rtypes[spec['type']].id,
                'status_id': statuses[spec['status']].id,
                'description': spec['description'],
                'event_date': spec['event_date'],
            },
            title=spec['title'],
        )
        reports[spec['key']] = report

        _get_or_create(
            ReportLocation,
            defaults={
                'location_id': locs[spec['location']].id,
                'specific_location': spec['specific'],
            },
            report_id=report.id,
        )

        if created:
            db.session.add(
                ReportStatusHistory(
                    report_id=report.id,
                    old_status_id=None,
                    new_status_id=statuses['open'].id,
                    changed_by=spec['user'].id,
                    change_reason='Initial report submission',
                )
            )
            if spec['status'] != 'open':
                db.session.add(
                    ReportStatusHistory(
                        report_id=report.id,
                        old_status_id=statuses['open'].id,
                        new_status_id=statuses[spec['status']].id,
                        changed_by=security_user.id,
                        change_reason=f'Status progressed to {spec["status"]}',
                    )
                )

        for tag_name in spec['tags']:
            tag, _ = _get_or_create(Tag, tag_name=tag_name)
            _get_or_create(ReportTag, report_id=report.id, tag_id=tag.id)

    # ItemMatch between lost_airpods and found_airpods
    _get_or_create(
        ItemMatch,
        defaults={
            'match_score': 0.92,
            'match_method': 'auto',
            'match_status': 'pending',
        },
        lost_report_id=reports['lost_airpods'].id,
        found_report_id=reports['found_airpods'].id,
    )

    # SavedSearch + SavedSearchFilter
    saved_search, _ = _get_or_create(
        SavedSearch,
        defaults={'keyword': 'AirPods'},
        user_id=student1.id,
        search_name='Library AirPods Watch',
    )
    _get_or_create(
        SavedSearchFilter,
        saved_search_id=saved_search.id,
        filter_name='category_id',
        filter_value=str(cats['Electronics'].id),
    )

    # Verification questions on found items
    vq_airpods, _ = _get_or_create(
        VerificationQuestion,
        report_id=reports['found_airpods'].id,
        question='What color accessory or lanyard is attached to the charging case?',
    )
    vq_backpack, _ = _get_or_create(
        VerificationQuestion,
        report_id=reports['found_backpack'].id,
        question='What items are inside the front zippered pocket of the backpack?',
    )

    # Claims (1 pending on found_airpods, 1 approved on found_backpack)
    claim_pending, _ = _get_or_create(
        Claim,
        defaults={
            'claim_description': 'These are my AirPods Pro. The case has a small blue silicone lanyard and my phone pairs with them as "Alex AirPods".',
            'claim_status': 'pending',
        },
        report_id=reports['found_airpods'].id,
        claimant_id=student1.id,
    )
    _get_or_create(
        ClaimAnswer,
        defaults={'answer': 'A small blue silicone lanyard attached to the side loop.'},
        claim_id=claim_pending.id,
        question_id=vq_airpods.id,
    )
    _get_or_create(
        ClaimEvidence,
        defaults={
            'evidence_path': None,
            'description': 'Serial number ending in L8K9 recorded in Apple Find My app.',
        },
        claim_id=claim_pending.id,
        evidence_type='description',
    )

    claim_approved, _ = _get_or_create(
        Claim,
        defaults={
            'claim_description': 'My navy JanSport backpack left in Lab 302 after afternoon circuits class.',
            'claim_status': 'approved',
        },
        report_id=reports['found_backpack'].id,
        claimant_id=student2.id,
    )
    _get_or_create(
        ClaimAnswer,
        defaults={'answer': 'A braided white USB-C cable and an engineering spiral notebook.'},
        claim_id=claim_approved.id,
        question_id=vq_backpack.id,
    )
    _get_or_create(
        ClaimReview,
        defaults={
            'decision': 'approved',
            'review_notes': 'Verified notebook name and pocket contents match stored item.',
        },
        claim_id=claim_approved.id,
        reviewer_id=security_user.id,
    )

    appointment, _ = _get_or_create(
        HandoverAppointment,
        defaults={
            'location_id': locs['Campus Security - Lost & Found Desk'].id,
            'appointment_date': datetime.now(timezone.utc) + timedelta(days=1),
            'appointment_status': 'scheduled',
        },
        claim_id=claim_approved.id,
    )
    _get_or_create(
        HandoverRecord,
        defaults={
            'handed_over_by': sec_data['staff'].id,
            'received_by': student2.id,
            'id_checked': True,
            'confirmation_status': 'pending',
        },
        appointment_id=appointment.id,
    )

    # Security CustodyLogs & IncidentReports
    _get_or_create(
        CustodyLog,
        report_id=reports['found_airpods'].id,
        staff_id=sec_data['staff'].id,
        storage_location_id=sec_data['storage_locations']['Security Desk Vault A (Electronics)'].id,
        action='received',
    )
    _get_or_create(
        CustodyLog,
        report_id=reports['found_backpack'].id,
        staff_id=sec_data['staff'].id,
        storage_location_id=sec_data['storage_locations']['Security Desk Shelf B (General Items)'].id,
        action='received',
    )
    _get_or_create(
        IncidentReport,
        defaults={
            'staff_id': sec_data['staff'].id,
            'report_id': reports['found_backpack'].id,
            'severity': 'low',
            'description': 'Unattended backpack reported in Engineering Lab 302 after hours; secured at Central Security Desk.',
        },
        reported_by=security_user.id,
        location_id=locs['Engineering Hall - Room 302 Computer Lab'].id,
    )

    # Messaging: Conversation, Participants, Messages, Notifications
    conv = Conversation.query.filter_by(report_id=reports['found_airpods'].id).first()
    if conv is None:
        conv = Conversation(report_id=reports['found_airpods'].id)
        db.session.add(conv)
        db.session.flush()

    _get_or_create(ConversationParticipant, conversation_id=conv.id, user_id=student1.id)
    _get_or_create(ConversationParticipant, conversation_id=conv.id, user_id=student2.id)

    if Message.query.filter_by(conversation_id=conv.id).count() == 0:
        db.session.add(
            Message(
                conversation_id=conv.id,
                sender_id=student1.id,
                message_text='Hi Maya! I saw your found earbuds report — does the case have a blue lanyard?',
                is_read=True,
            )
        )
        db.session.add(
            Message(
                conversation_id=conv.id,
                sender_id=student2.id,
                message_text='Yes it does! I turned it in at the Campus Security Desk, and I see your claim is pending review.',
                is_read=False,
            )
        )

    notifications_spec = [
        (
            student1.id,
            'Potential Item Match Found',
            'Your lost AirPods Pro report matched a newly submitted found report in Main Library.',
            'match',
            False,
        ),
        (
            student2.id,
            'Claim Approved',
            'Your claim for "Navy Blue JanSport Backpack" has been approved. Please visit the Security Desk for handover.',
            'claim',
            False,
        ),
    ]
    for uid, title, msg, ntype, is_read in notifications_spec:
        _get_or_create(
            Notification,
            defaults={'message': msg, 'notification_type': ntype, 'is_read': is_read},
            user_id=uid,
            title=title,
        )

    # Admin: UserReport, ModerationAction, AuditLog
    _get_or_create(
        UserReport,
        defaults={
            'description': 'Duplicate test inquiry flagged for verification.',
            'status': 'resolved',
        },
        reporter_id=student2.id,
        reported_user_id=student1.id,
        reason='Duplicate listing inquiry',
    )
    _get_or_create(
        ModerationAction,
        defaults={
            'reason': 'Reviewed inquiry and verified legitimate user report.',
        },
        admin_id=admin_user.id,
        target_type='report',
        target_id=reports['found_airpods'].id,
        action_type='reinstate',
    )

    audit_entries = [
        (admin_user.id, 'seed_database', 'system', 1),
        (student1.id, 'create_item_report', 'item_report', reports['lost_airpods'].id),
        (student2.id, 'create_item_report', 'item_report', reports['found_airpods'].id),
        (security_user.id, 'custody_received', 'custody_log', reports['found_backpack'].id),
        (security_user.id, 'review_claim_approved', 'claim', claim_approved.id),
    ]
    for uid, action, etype, eid in audit_entries:
        _get_or_create(
            AuditLog,
            defaults={'ip_address': '127.0.0.1'},
            user_id=uid,
            action=action,
            entity_type=etype,
            entity_id=eid,
        )


def seed_all():
    """Run all idempotent seeders inside an application context."""
    users = seed_auth()
    cls_data = seed_classification()
    loc_data = seed_locations()
    sec_data = seed_security(users, loc_data)
    seed_reports_and_workflows(users, cls_data, loc_data, sec_data)
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_all()
        print('FindIt database seeded successfully.')
