from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import require_admin
from app.models import AuditLog, FileRecord, User
from app.policy_engine import ACTION_EXTERNAL_LINK, evaluate_policy
from app.schemas import FileOut, LabelOverrideRequest

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_LABELS = {"Public", "Internal", "Confidential", "Highly Confidential"}


def _serialize_file(file_record: FileRecord) -> dict:
    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "owner_user_id": file_record.owner_user_id,
        "created_at": file_record.created_at,
        "size": file_record.size,
        "content_type": file_record.content_type,
        "label": file_record.label,
        "scan_summary_json": file_record.scan_summary_json,
        "policy_decision": file_record.policy_decision,
        "decision_reason": file_record.decision_reason,
        "is_deleted": file_record.is_deleted,
    }


@router.get("/files", response_model=list[FileOut])
def list_all_files(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> list[FileOut]:
    _ = admin_user
    files = db.query(FileRecord).filter(FileRecord.is_deleted.is_(False)).order_by(FileRecord.created_at.desc()).all()
    return [FileOut(**_serialize_file(file_record)) for file_record in files]


@router.post("/files/{file_id}/label-override", response_model=FileOut)
def override_label(
    file_id: int,
    payload: LabelOverrideRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> FileOut:
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id, FileRecord.is_deleted.is_(False)).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    requested_label = payload.label.strip()
    if requested_label not in VALID_LABELS:
        raise HTTPException(status_code=400, detail=f"label must be one of: {sorted(VALID_LABELS)}")

    if not payload.justification.strip():
        raise HTTPException(status_code=400, detail="justification is required")

    previous_label = file_record.label
    file_record.label = requested_label

    policy_result = evaluate_policy(label=file_record.label, action=ACTION_EXTERNAL_LINK)
    file_record.policy_decision = policy_result.decision
    file_record.decision_reason = policy_result.reason

    add_audit(
        db,
        actor_user_id=admin_user.id,
        action="label_override",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "from": previous_label,
            "to": requested_label,
            "justification": payload.justification,
        },
    )

    add_audit(
        db,
        actor_user_id=admin_user.id,
        action="policy_decision",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "action": ACTION_EXTERNAL_LINK,
            "decision": policy_result.decision,
            "reason": policy_result.reason,
            "updated_by": "label_override",
        },
    )

    db.commit()
    db.refresh(file_record)
    return FileOut(**_serialize_file(file_record))


@router.get("/audit")
def list_audit_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    _ = admin_user
    rows = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return rows


@router.get("/policy")
def policy_summary(admin_user: User = Depends(require_admin)):
    _ = admin_user
    return {
        "rules": [
            {
                "label": "Public/Internal",
                "action": "INTERNAL_SHARE",
                "decision": "allow",
                "reason": "Internal sharing allowed.",
                "required_fields": [],
            },
            {
                "label": "Public/Internal",
                "action": "EXTERNAL_LINK",
                "decision": "allow",
                "reason": "Expiry is required.",
                "required_fields": ["expires_at"],
            },
            {
                "label": "Confidential",
                "action": "EXTERNAL_LINK",
                "decision": "warn",
                "reason": "Requires justification and expiry.",
                "required_fields": ["justification", "expires_at"],
            },
            {
                "label": "Highly Confidential",
                "action": "INTERNAL_SHARE",
                "decision": "allow",
                "reason": "Only explicit allowlist users.",
                "required_fields": ["target_user_email"],
            },
            {
                "label": "Highly Confidential",
                "action": "EXTERNAL_LINK",
                "decision": "block",
                "reason": "Blocked by policy.",
                "required_fields": [],
            },
        ]
    }
