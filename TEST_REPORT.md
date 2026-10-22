# KU Online Voting — Verification & Fix Report

Date: 2026-10-07

## Results

- Python compilation: PASS
- Jinja template compilation: PASS (22 templates)
- Application route registration: PASS (28 routes)
- Database table inspection: PASS for core election/voting tables
- Admin workflow unit tests: PASS (4/4)
- Voting/security unit tests: PASS (7/7)
- CSRF & End-to-End Integration tests: PASS (4/4)
- Total automated tests: PASS (15/15)
- HTTP smoke test: PASS (26+ requests, 0 HTTP 500 responses)

## Tested System Flows

1. **Voter Authentication & Profile Creation**:
   - Authoritative university registrar verification during self-registration
   - Student ID & password credential validation
   - Session establishment and role-based route dispatching
2. **Electoral Commission Admin Portal**:
   - Dedicated EC official login (`/auth/admin/login`)
   - Election creation, schedule management, and dynamic state transitions
   - Contested position creation, prioritization, and quota settings
   - Eligibility rule builder (filtering by campus, faculty, course, year, and gender)
   - Candidate screening, vetting, image uploads, approval, and disqualification
   - Chronological immutable audit logging
3. **Ballot Casting & Cryptographic Ballot Secrecy**:
   - Double-voting lock enforcement
   - Dynamic voter ballot generation showing only student-eligible offices
   - Strict decoupled ballot architecture: Table A (`voter_participation`) stores participation receipt token, Table B (`votes`) stores anonymous selections with zero identity correlation
   - Automatic shuffled batch commit
   - Cryptographic receipt token generation (`KU-...`) and simulated email confirmation
4. **Public Audit & Results Portal**:
   - Public receipt verification ledger (`/verify-receipt`) supporting both direct GET query links (`?token=KU-...`) and form POST submissions
   - Certified election results view with turnout analytics (campus and faculty donuts, candidate vote distribution bar charts)
   - Administrative real-time tabulation monitor with official publication gate

## Key Bugs Identified & Resolved

1. **CSRF Token Leakage & Form Submission Failures**:
   - **Root Cause**: All HTML forms previously rendered bare `{{ csrf_token() }}` without an HTML tag. In Flask-WTF, `csrf_token()` returns a raw signed string token (e.g. `IjEzMTA1ZmI3YzQxZGU2ZjFlYzgx...`), which Jinja rendered verbatim as visible text on the page (observed in the screenshot above the Student ID input). Crucially, the forms lacked an `<input type="hidden" name="csrf_token">`, which caused any subsequent POST request to be rejected with `HTTP 400 Bad Request (The CSRF token is missing)`.
   - **Fix**: Updated all 13 POST forms across 9 templates (`login.html`, `admin_login.html`, `register.html`, `ballot.html`, `verify_receipt.html`, `view.html`, `candidates.html`, `elections.html`, `election_detail.html`) to use `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. Added `<meta name="csrf-token" content="{{ csrf_token() }}">` to `base.html`.
2. **One-Click Receipt Ledger Verification**:
   - **Root Cause**: When students clicked "Verify on Public Ledger" on the ballot confirmation page, the URL passed `?token=KU-...` via GET, but `/verify-receipt` only evaluated tokens on POST requests, forcing the voter to copy and paste manually.
   - **Fix**: Updated `blueprints/main.py`'s `verify_receipt` route to read `request.values.get('token')`, automatically validating and rendering the authentic participation card upon landing.
3. **Template Block Nesting in Candidate Admin View**:
   - **Root Cause**: `templates/admin/candidates.html` incorrectly nested `{% block scripts %}` inside `{% block content %}`, preventing proper script placement.
   - **Fix**: Unnested and properly closed the blocks.
4. **Broadcast Notification Category for Active Status**:
   - **Root Cause**: `NotificationService.send_election_broadcast` only handled status `'opened'` for election start, causing admin updates to `'active'` to fall into generic announcements.
   - **Fix**: Added support for `'active'` to correctly generate official poll opening notices.
5. **Active Election Seed Window**:
   - Extended the active voting window in `seed_data.py` to 14 days and re-seeded the local database so the voting booths and ballots remain live and testable.
