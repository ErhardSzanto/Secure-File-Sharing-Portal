# Architecture

## Overview
Secure File Sharing Portal is split into an Angular SPA frontend and a FastAPI backend with SQLite metadata storage and local filesystem blob storage.

## Components
- Frontend (`/frontend`): Angular UI for login, upload, policy-aware sharing, audit views, admin actions.
- API (`/backend/app`): FastAPI routers for auth, files, admin, and reports.
- Policy Engine (`/backend/app/policy_engine.py`): deterministic label/action decision logic (`allow|warn|block`).
- Scanner (`/backend/app/scanner.py`): regex-based PII detector with redacted summaries only.
- Data Layer (`/backend/app/models.py`): SQLAlchemy models for users, files, ACL shares, external links, and audit log.
- Storage:
  - Metadata: SQLite (`DATABASE_URL`, default `sqlite:///./app.db`).
  - File blobs: local directory (`UPLOAD_DIR`, default `./uploads`).

## Request Flow
1. User authenticates via `/auth/login` and receives JWT.
2. File upload hits `/files/upload`.
3. Backend validates extension, stores file, scans content, assigns label, evaluates policy, writes metadata + audit.
4. Sharing operations call policy engine again before ACL/external-link state changes.
5. Every critical action appends an audit record.

## ASCII Diagram
```text
+----------------------------+               +-----------------------------------+
|        Angular SPA         |               |           FastAPI Backend         |
| http://localhost:4200      |  JWT + REST   | http://localhost:8000             |
| - Login                    +---------------> - /auth, /files, /admin, /reports|
| - Dashboard tabs           |               | - scanner.py (PII regex/redact)   |
| - Upload/share/admin flows |               | - policy_engine.py (allow/warn/block)
+-------------+--------------+               +------------+----------------------+
              |                                           |
              |                                           |
              |                                           |
              |                                +----------v-----------+
              |                                |      SQLite DB       |
              |                                | users/files/audit/...|
              |                                +----------------------+
              |
              |                                +----------------------+
              +------------------------------->|    Local File Store   |
                                               |       ./uploads       |
                                               +----------------------+
```

## Docker Readiness Notes
- Configuration is fully env-based for DB, CORS, upload path.
- Backend and frontend are cleanly separated with independent dependency manifests.
- The next step is adding `Dockerfile` + `docker-compose.yml` without changing app code.
