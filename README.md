# FindIt — Smart Lost and Found Platform

**FindIt** is a campus-wide Lost & Found management web application built with **Flask**, **SQLAlchemy**, **Flask-Login**, **Flask-WTF**, and **Bootstrap 5**. It streamlines reporting lost or found items, matching reports, verifying ownership claims, coordinating campus security custody and handovers, and facilitating direct user-to-user messaging.

---

## Key Features

- **Role-Based Access Control (RBAC)**: Supports `user`, `security`, and `admin` roles with granular permissions.
- **Lost & Found Item Reporting**: Structured item reporting with categories, subcategories, brands, conditions, campus locations, image uploads, tags, and status history tracking (`open`, `matched`, `claimed`, `returned`, `closed`).
- **Search & Potential Matching**: Keyword, category, and report-type filtering, saved searches, and lost/found match tracking (`ItemMatch`).
- **Claims & Ownership Verification**: Claim submission with custom verification questions, evidence attachments, claim reviews, and scheduled handover appointments.
- **Security Operations Desk**: Dedicated portal for campus security staff to log item custody (`received`, `released`, `transferred`), manage storage locations, file incident reports, and schedule patrol shifts.
- **Messaging & Notifications**: Report-linked conversations between users and real-time in-app notifications for claims, matches, and messages.
- **Admin Control Panel**: User management (activate/deactivate), complaint review, moderation actions, taxonomy management (categories, brands, locations), and full system audit logs.

---

## Architecture & Directory Structure

FindIt uses the **Flask Application Factory** pattern (`create_app()` in `app/__init__.py`) paired with **9 modular Blueprints** and a **48-table normalized SQLAlchemy schema** organized across 9 domain modules.

```text
findit/
├── app/
│   ├── __init__.py              # Application factory & blueprint registration
│   ├── config.py                # Development, Production, and Testing configs
│   ├── extensions.py            # SQLAlchemy, LoginManager, and CSRFProtect instances
│   ├── blueprints/              # 9 feature blueprints (routes & WTForms)
│   │   ├── admin/               # /admin/* — user, taxonomy, moderation, audit log
│   │   ├── auth/                # /register, /login, /logout, /profile
│   │   ├── claims/              # /claims/* — submit, review, verification questions
│   │   ├── items/               # /items/* — lost/found CRUD & image uploads
│   │   ├── locations/           # /locations/* — campus zones, buildings, locations
│   │   ├── main/                # /, /about — homepage dashboard & stats
│   │   ├── messaging/           # /messaging/* — conversations & notifications
│   │   ├── search/              # /search/* — filtering, saved searches, matches
│   │   └── security/            # /security/* — custody, incidents, shifts, storage
│   ├── models/                  # 48 SQLAlchemy models across 9 domain modules
│   │   ├── admin.py             # 4 tables
│   │   ├── auth.py              # 7 tables
│   │   ├── claims.py            # 7 tables
│   │   ├── classification.py    # 6 tables
│   │   ├── communication.py     # 4 tables
│   │   ├── location.py          # 5 tables
│   │   ├── reporting.py         # 4 tables
│   │   ├── search.py            # 5 tables
│   │   └── security.py          # 6 tables
│   ├── static/
│   │   ├── css/style.css        # Custom Bootstrap 5 enhancements
│   │   ├── js/main.js           # Progressive UI enhancements
│   │   └── uploads/             # Uploaded item & claim evidence files
│   └── templates/               # Jinja2 templates extending base.html
├── requirements.txt             # Python package dependencies
├── run.py                       # Application entry point
├── seed.py                      # Idempotent database seeding script
└── README.md                    # Project documentation
```

---

## 48-Table Database Schema Breakdown

| Module | File | Tables (Count) | Table Names |
| :--- | :--- | :---: | :--- |
| **Auth & Users** | `app/models/auth.py` | 7 | `users`, `user_profiles`, `roles`, `permissions`, `user_roles`, `role_permissions`, `user_contacts` |
| **Item Classification** | `app/models/classification.py` | 6 | `categories`, `subcategories`, `brands`, `item_conditions`, `report_types`, `report_statuses` |
| **Campus Locations** | `app/models/location.py` | 5 | `campus_zones`, `buildings`, `floors`, `rooms`, `locations` |
| **Reporting** | `app/models/reporting.py` | 4 | `item_reports`, `report_locations`, `item_images`, `report_status_history` |
| **Search & Matching** | `app/models/search.py` | 5 | `tags`, `report_tags`, `saved_searches`, `saved_search_filters`, `item_matches` |
| **Claims & Verification** | `app/models/claims.py` | 7 | `claims`, `claim_evidence`, `verification_questions`, `claim_answers`, `claim_reviews`, `handover_appointments`, `handover_records` |
| **Security & Custody** | `app/models/security.py` | 6 | `security_staff`, `patrol_zones`, `shifts`, `storage_locations`, `custody_logs`, `incident_reports` |
| **Communication** | `app/models/communication.py` | 4 | `conversations`, `conversation_participants`, `messages`, `notifications` |
| **Admin & Moderation** | `app/models/admin.py` | 4 | `user_reports`, `moderation_actions`, `audit_logs`, `verification_tokens` |
| **Total** | **9 modules** | **48** | — |

---

## Setup & Installation

### 1. Create and Activate a Virtual Environment

```bash
python -m venv venv
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

All configuration values have sensible defaults for local development in `app/config.py`. Set the following environment variables as needed:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `FLASK_CONFIG` | Configuration profile (`development`, `production`, `testing`) | `development` |
| `SECRET_KEY` | Flask session & CSRF secret key (override in production) | `findit-super-secret-key-change-in-production` |
| `DATABASE_URL` | SQLAlchemy database connection URI | `sqlite:///findit.db` |

**Example (PowerShell):**
```powershell
$env:FLASK_CONFIG="development"
$env:SECRET_KEY="replace-with-a-strong-random-secret"
$env:DATABASE_URL="sqlite:///findit.db"
```

**Example (Linux / macOS):**
```bash
export FLASK_CONFIG=development
export SECRET_KEY="replace-with-a-strong-random-secret"
export DATABASE_URL="sqlite:///findit.db"
```

---

## Database Seeding & Demo Credentials

Run the standalone, idempotent seeding script to initialize all 48 tables and populate realistic sample data (safe to run multiple times without creating duplicates):

```bash
python seed.py
```

### Demo User Accounts

| Role | Email | Username | Password | Access Level |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin@findit.edu` | `admin` | `Admin@1234` | Full platform, user, taxonomy, moderation, and audit access |
| **Security** | `security@findit.edu` | `security_officer` | `Security@1234` | Security desk, custody logs, storage, shifts, and incidents |
| **Student 1** | `student1@findit.edu` | `alex_chen` | `Student@1234` | Standard user (lost/found reports, claims, messaging) |
| **Student 2** | `student2@findit.edu` | `maya_patel` | `Student@1234` | Standard user (lost/found reports, claims, messaging) |

---

## Running the Application

Start the Flask development server on port `5000`:

```bash
python run.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Running Tests

To run the automated test suite (using `TestingConfig` with `sqlite:///test.db` or `FLASK_CONFIG=testing`):

```bash
# Using pytest (if installed in your environment)
pytest

# Or using Python's built-in unittest discovery
python -m unittest discover
```

To run a quick application & database seed sanity check:

```bash
python -c "from app import create_app; app = create_app('testing'); print('Registered routes:', len(list(app.url_map.iter_rules())))"
```
