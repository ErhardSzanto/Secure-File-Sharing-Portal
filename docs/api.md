# API Reference

Base URL: `http://localhost:8000`

## Auth
- `POST /auth/login`
  - Body: `{ "email": "...", "password": "..." }`
  - Response: `{ "access_token": "...", "token_type": "bearer" }`
- `GET /auth/me`
  - Header: `Authorization: Bearer <token>`

## Files
- `POST /files/upload`
  - Multipart: `file`
  - Allowed extensions: `.txt`, `.csv`, `.pdf`
- `GET /files?scope=mine|shared|all`
- `GET /files/{id}`
- `GET /files/{id}/download`
- `GET /files/{id}/audit`
- `POST /files/{id}/share/internal`
  - Body: `{ "email": "user@portal.local" }`
- `DELETE /files/{id}/share/internal/{share_id}`
- `POST /files/{id}/share/external-link`
  - Body: `{ "expires_at": "2026-02-20T10:00:00Z", "justification": "optional" }`
- `POST /files/{id}/share/external-link/{link_id}/revoke`
- `GET /files/activity`

## Admin
- `GET /admin/files`
- `POST /admin/files/{id}/label-override`
  - Body: `{ "label": "Confidential", "justification": "reason" }`
- `GET /admin/audit`
- `GET /admin/policy`

## Reports
- `GET /reports/audit.csv?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `GET /reports/files/{id}/audit.csv`

## Core Behavior Notes
- Label assignment after scan:
  - no matches -> `Internal`
  - any PII -> `Confidential`
  - multiple categories or high volume -> `Highly Confidential`
- External link policy:
  - `Public/Internal`: allow with expiry
  - `Confidential`: warn and require justification + expiry
  - `Highly Confidential`: block
