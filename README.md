# Newtonite Operations Management Platform — MVP

A full-stack, enterprise-grade internal operations management platform with role-based access control, optimistic concurrency control, atomic concurrent assignment protection, transaction-consistent audit logging, and server-side paginated filtering.

---

## Architecture & Technology Stack

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide Icons.
- **Backend**: Python 3.13, FastAPI, Pydantic v2, Argon2id (`argon2-cffi`), PyJWT.
- **Database & ORM**: PostgreSQL (SQLAlchemy 2.0 with `psycopg` binary driver) & Alembic migrations.
- **Automated Tests**: Pytest test suite covering all 4 reliability behaviours, authentication, RBAC, and pagination.

---

## Prerequisites

- **Node.js**: v18+ (tested on Node v24) & `npm`
- **Python**: 3.11+ (tested on Python 3.13)
- **PostgreSQL**: PostgreSQL 14+ (service running on default port 5432)

---

## Quick Start & Setup

### 1. Database Creation
In PostgreSQL, create the target database:
```sql
CREATE DATABASE newtonite_db;
```

### 2. Backend Setup
1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   # Copy example template
   cp .env.example .env
   ```
   Adjust `DATABASE_URL` in `.env` if your PostgreSQL username/password differs from the defaults:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/newtonite_db
   SECRET_KEY=dev-secret-key-for-newtonite-operations-jwt-auth-2026-safe-dev
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   ENVIRONMENT=development
   ```
5. Apply Alembic database migrations:
   ```bash
   alembic upgrade head
   ```
6. Seed initial test data (Admin, Manager, Member, sample teams, and work items):
   ```bash
   python -m app.seed
   ```
7. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - OpenAPI Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/api/health`

---

### 3. Frontend Setup
1. In a separate terminal, navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure environment variables:
   ```bash
   # Copy example template
   cp .env.example .env.local
   ```
   Ensure `NEXT_PUBLIC_API_URL` points to the backend:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. Build or run the development server:
   ```bash
   # Development mode
   npm run dev

   # Production build & start
   npm run build
   npm run start
   ```
5. Open your browser at `http://localhost:3000`.

---

## Default Seeded Accounts

The database seed creates 4 preconfigured persona accounts for testing:

| Role | Email | Password | Scope & Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@newtonite.io` | `AdminSecure123!` | Full global management (teams, memberships, all items, users). |
| **Manager** | `manager@newtonite.io` | `ManagerPass123!` | Team-scoped management (create, reassign, status change in team). |
| **Staff Member** | `member@newtonite.io` | `MemberPass123!` | Scoped execution (view team items, claim tasks, add comments). |
| **Dev Member** | `dev@newtonite.io` | `DevPass123!` | Secondary member in Security & Compliance team. |

*Tip: The `/login` page includes **Quick Persona Login** buttons to immediately test each role.*

---

## Automated Test Suite

Run the automated test suite with `pytest`:
```bash
cd backend
pytest -v
```

### Test Coverage Highlights
- **`test_auth.py`**: User registration, duplicate email rejection, Argon2 password verification, JWT issuance, `/me` profile endpoint, inactive account rejection.
- **`test_reliability.py`**:
  - **Behaviour A (Concurrent Assignment)**: Atomic conditional claim prevents dual claims; returns `HTTP 409 Conflict`.
  - **Behaviour B (Stale Updates)**: Optimistic Concurrency Control rejects stale version writes with `HTTP 409 Conflict`.
  - **Behaviour C (Authorization)**: Direct API calls from unauthorized members to create or delete items in other teams receive `HTTP 403 Forbidden`.
  - **Behaviour D (Duplicate Operations & Audit Trail)**: `Idempotency-Key` header prevents duplicate writes; valid status changes log audit events, while failed/illegal transitions roll back with zero phantom logs.
- **`test_teams.py`**: Admin-only team creation, member additions, and member removals.
- **`test_work_items.py`**: Full CRUD, server-side pagination, search queries, priority filters, and comments.

---

## Key Features

1. **Operations Dashboard (`/`)**:
   - Real-time KPI widgets: Total Work Items, Open & In Progress, Critical Priority, Assigned to Logged-in User, Awaiting Action / Blocked.
   - Status & Priority distribution progress bars.
   - Live activity audit feed showing recent state transitions across authorized items.

2. **Server-Side Paginated Work Item List (`/work-items`)**:
   - Displays Title, Type, Status, Priority, Assignee, Team, and Updated Date.
   - Live search by title or description.
   - Composable multi-dimensional filtering by Status, Priority, Team, and Assignee.
   - Server-side pagination with items range and page controls. Never downloads full table into browser.

3. **Work Item Detail & Workflow State Machine (`/work-items/[id]`)**:
   - Complete item specifications, version counter, and metadata.
   - Workflow state machine enforcing allowed status transitions (`OPEN` &rarr; `IN_PROGRESS`, `BLOCKED`, etc.).
   - Atomic **Claim Task** button for unassigned tasks.
   - Optimistic concurrency conflict alert banner with instant reload button.
   - Real-time threaded commenting.
   - Chronological visual audit timeline showing actor, action, previous value, new value, and timestamp.

4. **Team Administration (`/teams`)**:
   - View teams, leadership, and active members.
   - Admin-exclusive controls to create teams, add members, and revoke memberships.
   - Clear authorization badges for non-admin users.

---

## Troubleshooting

- **Database Connection Error**:
  - Verify PostgreSQL service is active (`Get-Service postgresql*` on Windows, `systemctl status postgresql` on Linux).
  - Ensure the database `newtonite_db` exists (`psql -U postgres -c "CREATE DATABASE newtonite_db;"`).
- **CORS Errors**:
  - In development mode (`ENVIRONMENT=development`), CORS permits all origins. For production, ensure `CORS_ORIGINS` in `.env` includes your frontend domain.
- **Stale Update (HTTP 409 Conflict)**:
  - If another user or browser tab updated the work item in the background, click the **Reload Latest Server Version** button to synchronize state.

---

## Known Limitations

- Hierarchical nested sub-teams are out of scope for this MVP.
- Real-time updates rely on optimistic client refresh rather than WebSockets.
- File attachment uploads to work items are omitted in favor of text specifications and comments.
