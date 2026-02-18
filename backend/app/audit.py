from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def add_audit(
    db: Session,
    *,
    actor_user_id: Optional[int],
    action: str,
    target_type: str,
    target_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata or {},
    )
    db.add(entry)
    return entry
