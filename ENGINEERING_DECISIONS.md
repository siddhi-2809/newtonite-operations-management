# Newtonite Operations Management — Engineering Decisions Document

This document records the architectural and engineering decisions implemented for the Newtonite internal operations management MVP, outlining the approach, rationale, trade-offs, and boundaries for each core area.

---

## 1. Database Schema and Relationships

### Approach
We structured the schema around normalized relational entities in PostgreSQL using SQLAlchemy 2.0 and managed through Alembic migrations:
- **`users`**: Central identity entity storing `email` (unique index), Argon2-hashed password, `role` (`ADMIN`, `MANAGER`, `MEMBER`), and active flag.
- **`teams`**: Represents organizational divisions (e.g. Core Infrastructure, Security & Compliance).
- **`team_memberships`**: Join table enforcing unique user-to-team bindings with role (`LEAD` or `MEMBER`) and cascade deletion on team or user removal.
- **`work_items`**: Core transactional record with title, description, `item_type` (`TASK`, `BUG`, `FEATURE`, `INCIDENT`), `priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `status` (`OPEN`, `IN_PROGRESS`, `BLOCKED`, `RESOLVED`), `team_id` (foreign key), `assignee_id` (nullable foreign key), `reporter_id` (foreign key), `version` (optimistic concurrency integer), and composite index `(team_id, status, priority, assignee_id)`.
- **`comments`**: Direct relational child table linked to `work_items.id` with author metadata.
- **`activity_logs`**: Append-only transactional audit trail recording actor, action, previous value, new value, and timestamp.
- **`idempotency_records`**: Stores unique idempotency keys per user and endpoint with cached response status and payload.

### Why Chosen
- Eliminates anomalies by strictly maintaining referential integrity (foreign keys, cascading constraints where appropriate, restrict constraints on work items).
- Composite indexes on `work_items` accelerate the dominant read patterns (filtering by team, status, priority, and assignee).
- Explicit integer `version` field enables native Optimistic Concurrency Control (OCC).

### Trade-off & Limitations
- **Trade-off**: Relational joins require careful index design and eager loading (`joinedload`) to prevent N+1 queries.
- **Limitation**: Recursive organizational hierarchies (teams within sub-teams) are omitted in this MVP in favor of flat teams.

---

## 2. Authentication and Authorization Model

### Approach
- **Authentication**: Email and password credentials authenticated via HTTP endpoints (`/api/auth/login`, `/api/auth/register`, `/api/auth/me`). Passwords are encrypted with **Argon2id** (`argon2-cffi`), the OWASP gold standard for password storage due to memory-hard resistance to GPU attacks.
- **Session Tokens**: Cryptographically signed JSON Web Tokens (JWT, HS256) with 8-hour expiration returned in Bearer headers.
- **Role-Based Access Control (RBAC)**:
  - **`ADMIN`**: Global management privileges. Can create teams, assign and remove members, create and edit any work item, and manage users.
  - **`MANAGER`**: Team-scoped management privileges. Can manage work items, assign tasks, and transition statuses within teams they belong to.
  - **`MEMBER`**: Scoped execution privileges. Can view permitted work items within their teams, claim unassigned tasks, add comments, and transition the status of tasks assigned to them according to allowed workflow transitions.
- **Backend Enforcement**: Every private endpoint validates the authenticated `User` from the JWT token and enforces resource-level and team-level checks directly in Python code. The frontend never dictates user ID, role, or team membership.

### Why Chosen
- Token-based decoupled authentication allows independent scaling and clean separation between the Next.js frontend and FastAPI backend without cookie domain synchronization friction.
- Strict backend verification guarantees that direct API manipulation (e.g., via `curl` or Postman) cannot bypass permission rules.

### Trade-off & Limitations
- **Trade-off**: Stateless JWTs cannot be instantly invalidated server-side without a token blacklist table or Redis cache.
- **Limitation**: Advanced OAuth2/OIDC, SSO, and multi-factor authentication (MFA) were explicitly omitted to maintain assessment MVP scope.

---

## 3. Concurrent Assignment and Stale-Update Protection

### Approach

#### A. Concurrent Assignment Protection
To prevent two engineers from concurrently claiming the same unassigned work item:
- We employ an atomic conditional update at the database engine level:
  ```sql
  UPDATE work_items
  SET assignee_id = :user_id, version = version + 1, updated_at = :now
  WHERE id = :work_item_id AND assignee_id IS NULL AND version = :version;
  ```
- If rowcount is 0, the backend immediately inspects the refreshed record:
  - If `assignee_id` is already populated, it returns `HTTP 409 Conflict` ("Work item has already been claimed or assigned to another user").
  - If the version changed, it returns `HTTP 409 Conflict` ("Work item version mismatch").

#### B. Stale-Update Protection (Optimistic Concurrency Control)
- Every work item maintains a `version: int` column initialized to `1`.
- When the frontend loads a work item, it captures the current version.
- Any update request (`PUT /api/work-items/{id}`, `PATCH /api/work-items/{id}/status`, `PATCH /api/work-items/{id}/assign`) must supply the loaded `version`.
- If `item.version != request.version`, the backend rejects the update with `HTTP 409 Conflict` ("Work item has been modified by another user. Please refresh and try again").
- When a conflict occurs, the frontend displays a dedicated alert banner and provides an instant "Reload Latest Server Version" button.

### Why Chosen
- Atomic conditional SQL updates avoid heavyweight distributed locks or external lock managers (like Redis Redlock) while providing strict ACID isolation guarantees directly in PostgreSQL.
- Optimistic Concurrency Control avoids holding database table or row locks during human read-and-think time.

### Trade-off & Limitations
- **Trade-off**: Requires the client to handle 409 conflicts and refresh before reapplying changes.
- **Limitation**: In extremely high-contention burst write environments, optimistic retries can experience repeated retries, but for operational ticketing and task management, collision frequencies are low and OCC is optimal.

---

## 4. Activity History and Transaction Consistency

### Approach
- Every state-altering action (`CREATED`, `STATUS_CHANGE`, `ASSIGNED`, `PRIORITY_CHANGE`, `UPDATED`, `COMMENT_ADDED`) produces an `ActivityLog` record containing:
  - `work_item_id`: Reference to the parent item.
  - `actor_id`: Authenticated user who performed the operation.
  - `action`: Canonical action identifier.
  - `field_name`: Mutated attribute (e.g. `status`, `assignee_id`).
  - `previous_value`: Representation of previous state.
  - `new_value`: Representation of updated state.
  - `timestamp`: UTC datetime.
- **Transaction Consistency**: The activity log creation is executed inside the exact same database session transaction as the primary entity update:
  - If the update fails (e.g., validation failure, version mismatch, or network interruption), the session transaction is rolled back.
  - No phantom activity log is ever recorded for a failed update.
- **Status State Machine**:
  - Enforces valid operational transitions:
    - `OPEN` &rarr; `IN_PROGRESS`, `BLOCKED`
    - `IN_PROGRESS` &rarr; `BLOCKED`, `RESOLVED`, `OPEN`
    - `BLOCKED` &rarr; `OPEN`, `IN_PROGRESS`
    - `RESOLVED` &rarr; `OPEN`, `IN_PROGRESS`
  - Illegal jumps (e.g., `OPEN` directly to `RESOLVED` without progress) are rejected with `HTTP 400 Bad Request`.
- **Idempotency**:
  - Critical endpoints accept an `Idempotency-Key` header.
  - If a retry request arrives with the same key, the database returns the previously saved response body and status code without executing duplicate side effects or duplicate activity logs.

### Why Chosen
- Synchronous transactional auditing in the same DB transaction guarantees 100% audit log consistency without eventual-consistency gaps or risk of lost logs.

### Trade-off & Limitations
- **Trade-off**: Slightly increases transaction write latency by inserting both the entity update and the audit log row in the same transaction.
- **Limitation**: Audit logs are permanently stored in the primary operational table rather than offloaded to a cold OLAP data lake.

---

## 5. Pagination, Search, Scope Limitations, and Omitted Features

### Approach
- **Server-Side Pagination**:
  - Implemented on `GET /api/work-items` using SQL `COUNT(*)` for total count and `LIMIT :page_size OFFSET :offset` ordered by `updated_at DESC`.
  - The endpoint returns a typed metadata envelope:
    ```json
    {
      "items": [...],
      "total": 42,
      "page": 1,
      "page_size": 10,
      "total_pages": 5
    }
    ```
  - The frontend never downloads the full table, protecting browser memory and network bandwidth.
- **Search and Filtering**:
  - Search executes server-side across `title` and `description` via SQL `ILIKE` pattern matching.
  - Filters are composable (`status`, `priority`, `team_id`, `assignee_id`).
- **Omitted Features (Strict Scope Control)**:
  - Redis / Celery / background worker queues: Synchronous transactional execution is sufficient for MVP scale.
  - Third-party OAuth (Google, GitHub): Kept internal email/password with Argon2 to maintain self-contained assessment reproducibility.
  - WebSocket real-time broadcast: Replaced with clean polling / optimistic state refresh to keep the architecture robust and simple.
  - Rich-text markdown editor: Simplified to plain-text / multiline text areas to prevent XSS surface and excessive dependencies.

### Why Chosen
- Delivers a reliable, demonstrable internal operations dashboard that satisfies every requirement without scope creep or fragile external infrastructure.
