# Threat Model (DLP-lite)

## Assets
- Uploaded documents (potentially sensitive content).
- Metadata and policy decisions.
- Audit logs (compliance evidence).
- JWT credentials and user roles.

## Trust Boundaries
- Browser to API boundary (untrusted client input).
- API to filesystem boundary (file writes/reads).
- API to DB boundary (authorization and data integrity).

## Key Threats and Mitigations
1. Unauthorized data access.
- Mitigation: JWT auth + role checks + ownership/share ACL checks per file endpoint.

2. Sensitive data retention in logs/metadata.
- Mitigation: scanner stores only counts and redacted examples; no raw match values in DB.

3. Risky external sharing.
- Mitigation: policy engine enforces `allow|warn|block`, required fields, and explicit blocks for Highly Confidential links.

4. Undetected insider actions.
- Mitigation: audit logging for login/upload/download/share/link/override/policy/report actions.

5. Upload abuse via unsupported file types.
- Mitigation: strict extension allowlist (`TXT`, `CSV`, `PDF`) and controlled storage location.

## Known Limitations
- PDF scanning is intentionally limited in v1 (trivial text preview only).
- No antivirus/malware scanning in this iteration.
- JWT secret defaults are development-only and must be overridden in production.

## Future Hardening
- Add signed URL download flow and short-lived download tokens.
- Add brute-force rate limiting and account lockout.
- Add encryption-at-rest for blob storage.
- Add object-level ABAC and policy versioning.
