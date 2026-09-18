# Kampala University Online Voting System (KU-OVS)

A secure, role-based electronic voting platform for Kampala University student guild elections. Built with Python Flask, SQLAlchemy, Bootstrap 5, and Chart.js.

---

## Key Security Pillars

| Guarantee | How it works |
|---|---|
| **Absolute Ballot Secrecy** | Two decoupled tables — `voter_participation` (Table A) tracks *who* voted; `votes` (Table B) stores anonymous ballots with zero student identifier or join path |
| **Double-Vote Prevention** | A unique constraint on `(election_id, student_id)` in Table A prevents any student from submitting more than one ballot |
| **Registrar Verification** | Students must match their official Student ID and Reg No against the `university_records` table before a voter account is created |
| **Eligibility Rules Engine** | Each position carries rules (campus, faculty, course, year, gender); the engine filters the ballot so students only see positions they are qualified to elect |
| **EC Results Publishing Gate** | Vote tallies are visible only to administrators until the EC Chair explicitly clicks **Approve & Publish** |
| **Cryptographic Participation Receipt** | After voting, each student receives a unique `KU-XXXXXXXXXXXXXXXX` token they can verify on the public portal without revealing their choices |

---

## Default Credentials (after running `seed_data.py`)

### Administrators
| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@KU2026` | Super Administrator |
| `ec_chair` | `Chair@KU2026` | EC Chairperson (can publish results) |
| `commissioner1` | `Comm@KU2026` | Returning Officer |

### Test Students — all use password `Student@2026`
| Student ID | Name | Campus |
|---|---|---|
| `KU/2024/001` | Mukasa Denis | Ggaba (Main Campus) |
| `KU/2024/002` | Acheng Sarah | Ggaba (Main Campus) — Female |
| `KU/2024/020` | Namutebi Fatuma | Old Kampala Campus |
| `KU/2024/030` | Kavuma Isaac | Luweero Campus |
| `KU/2024/040` | Waiswa Kenneth | Jinja Campus |
| `KU/2024/050` | Ssenyonga Moses | Masaka Campus |

---

## Prerequisites

- Python 3.9 or higher
- pip
- MySQL 5.7+ / 8.0+ or MariaDB 10.3+ *(optional — SQLite fallback works out of the box)*

---

## Quick Start (SQLite — zero configuration)

```powershell
# 1. Clone / enter the project directory
cd "KU ONLINE VOTING"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # macOS/Linux

# 3. Install dependencies
pip install flask flask-sqlalchemy flask-login werkzeug python-dotenv pymysql

# 4. Copy the environment template
Copy-Item .env.example .env    # Windows
# cp .env.example .env          # macOS/Linux

# 5. Seed the database with demo data
python seed_data.py

# 6. Start the development server
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## MySQL Setup (Production / Full Deployment)

### 1. Create the database and user

```sql
CREATE DATABASE ku_voting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ku_app'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON ku_voting.* TO 'ku_app'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Import the schema

```powershell
mysql -u ku_app -p ku_voting < database/schema.sql
```

### 3. Configure the `.env` file

```ini
DB_USER=ku_app
DB_PASSWORD=StrongPassword123!
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ku_voting
```

### 4. Seed and run

```powershell
python seed_data.py
python app.py
```

---

## Project Structure

```
KU ONLINE VOTING/
├── app.py                        # Flask application factory
├── config.py                     # Configuration (MySQL/SQLite dual engine)
├── models.py                     # SQLAlchemy models (ballot secrecy architecture)
├── seed_data.py                  # Database seeder with demo data
├── .env                          # Local environment variables (not committed)
├── .env.example                  # Environment template
│
├── blueprints/
│   ├── auth.py                   # Student & admin login, register, logout
│   ├── voting.py                 # Ballot rendering, eligibility filter, vote submission
│   ├── admin.py                  # EC dashboard, election/candidate management
│   ├── results.py                # Live tabulation, EC publish gate, public results
│   └── main.py                   # Homepage, FAQ, announcements, receipt verify
│
├── services/
│   ├── election_service.py       # Eligibility engine, atomic ballot casting, tabulation
│   ├── audit_service.py          # Tamper-evident audit log writer
│   └── notification_service.py   # In-app notifications + email/SMS stubs
│
├── templates/
│   ├── base.html                 # Base layout (navbar, flash messages, footer)
│   ├── index.html                # Public homepage with election status
│   ├── auth/                     # login.html, register.html, admin_login.html
│   ├── voting/                   # ballot.html, confirmation.html, elections.html
│   ├── admin/                    # dashboard, elections, candidates, students, audit
│   ├── results/                  # index.html, view.html (Chart.js visualizations)
│   ├── main/                     # faq.html, announcements.html, verify_receipt.html
│   └── errors/                   # 403.html, 404.html, 500.html
│
├── static/
│   ├── css/custom.css            # KU brand theme (navy #092347, gold #f5a623)
│   ├── js/main.js                # Ballot interaction, countdown timers, alerts
│   └── js/charts.js              # Chart.js helpers (bar, donut charts)
│
├── database/
│   └── schema.sql                # Production MySQL DDL for all 11 tables
│
└── tests/
    └── test_voting_system.py     # Pytest suite (secrecy, eligibility, double-vote, etc.)
```

---

## Running the Test Suite

```powershell
# Run all tests (uses in-memory SQLite — no database setup required)
python -m pytest tests/ -v

# Or with unittest directly
python -m unittest discover -s tests -p "test_*.py" -v
```

### What the tests cover

| Test | Description |
|---|---|
| `test_ballot_secrecy_decoupling` | Asserts `votes` table has no `student_id`, `voter_id`, `user_id`, or `receipt_token` columns |
| `test_eligibility_filtering` | Verifies campus-specific and gender-specific position filtering works correctly |
| `test_single_vote_and_double_vote_rejection` | Casts a ballot, checks the receipt token, then asserts a second submission is rejected |
| `test_election_closed_rejection` | Asserts ballots submitted to a closed election are refused |
| `test_ec_results_gate` | Asserts results are hidden from the public until the EC Chair publishes them |
| `test_registrar_verification_and_auth` | Validates password hashing and registrar record matching |

---

## Manual Verification Walkthrough

### Student Flow
1. Navigate to `http://127.0.0.1:5000`
2. Click **Verify & Register** → enter `KU/2024/030` and `24/KU/030/UG` to register as Kavuma Isaac (Luweero Campus)
3. Log in and observe the ballot — you will see **Guild President**, **Vice Guild President**, **Luweero Campus Representative**, but **NOT** the Ggaba Campus Representative (filtered by eligibility rule)
4. Cast your vote, copy the participation receipt token
5. Log out and try logging in again → the voting booth shows **You Have Voted** with double-vote lock active
6. Go to **Verify Receipt** and paste the token — the system confirms participation without revealing choices

### Admin Flow
1. Navigate to `/auth/admin/login`
2. Log in as `ec_chair` / `Chair@KU2026`
3. Open **Admin Cockpit** → view live turnout KPIs, candidate queue, audit trail
4. Go to **Elections** → click **Results** on the active election to view real-time tabulations
5. Click **Approve & Publish to Public** to release results to students
6. Log out and revisit the results page as an unauthenticated visitor — certified charts and winner badges are now visible

---

## Production Deployment (Gunicorn + Nginx)

### Install Gunicorn

```bash
pip install gunicorn
```

### Run with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
```

### Nginx reverse proxy snippet

```nginx
server {
    listen 80;
    server_name vote.ku.ac.ug;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/ku-ovs/static/;
        expires 7d;
    }
}
```

### Production `.env` checklist

```ini
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<64-character random hex string>
SESSION_COOKIE_SECURE=True          # Requires HTTPS
DATABASE_URL=mysql+pymysql://ku_app:StrongPassword@localhost/ku_voting
```

---

## Security Notes

- **Ballot secrecy** is enforced at the schema level — there is no foreign key, join path, or index between `votes` and `students`. Even a direct database query cannot link a vote to its author.
- **HTTPS / TLS** is mandatory in production. The `SESSION_COOKIE_SECURE=True` flag enforces this.
- **Werkzeug password hashing** (scrypt/pbkdf2) is used for all stored credentials. Plain-text passwords are never written to the database.
- **Audit logs** record every authentication and administrative event but deliberately never log vote selections.
- **Input validation** is performed on both client (JavaScript) and server (Python) sides. Invalid candidate IDs and out-of-eligibility position IDs are rejected before any database write.

---

## University Campuses Pre-loaded

- Ggaba (Main Campus)
- Old Kampala Campus
- Luweero Campus
- Jinja Campus
- Masaka Campus

## Faculties Pre-loaded

- Faculty of Computer Science and Information Technology
- Faculty of Business Administration & Management
- Faculty of Education
- Faculty of Arts & Social Sciences
- Faculty of Natural Sciences
- Faculty of Health Sciences

---

*Kampala University Electoral Commission — "In God We Trust, Knowledge is Power"*
