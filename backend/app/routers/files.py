from datetime import datetime, timezone
import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, ExternalLink, FileRecord, InternalShare, User
from app.policy_engine import ACTION_EXTERNAL_LINK, ACTION_INTERNAL_SHARE, DECISION_BLOCK, evaluate_policy
from app.scanner import label_from_scan, scan_content
from app.schemas import ExternalLinkRequest, FileDetailsOut, FileOut, InternalShareRequest
from app.upload_validation import validate_upload_filename

router = APIRouter(prefix="/files", tags=["files"])


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


def _get_file_or_404(db: Session, file_id: int) -> FileRecord:
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id, FileRecord.is_deleted.is_(False)).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    return file_record


def _ensure_owner_or_admin(file_record: FileRecord, current_user: User) -> None:
    if current_user.role != "Admin" and file_record.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner or admin can manage this action")


def _can_access_file(db: Session, file_record: FileRecord, user: User) -> bool:
    if user.role == "Admin" or file_record.owner_user_id == user.id:
        return True

    share = (
        db.query(InternalShare)
        .filter(InternalShare.file_id == file_record.id, InternalShare.user_id == user.id)
        .first()
    )
    return share is not None


@router.post("/upload", response_model=FileOut)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileOut:
    filename = file.filename or "uploaded-file"

    if not validate_upload_filename(filename):
        raise HTTPException(status_code=400, detail="Only TXT, CSV, and PDF files are allowed")

    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    suffix = filename.rsplit(".", 1)[-1].lower()

    settings.upload_path.mkdir(parents=True, exist_ok=True)
    storage_name = "{}.{}".format(uuid.uuid4().hex, suffix)
    storage_path = settings.upload_path / storage_name
    storage_path.write_bytes(content)

    scan_summary = scan_content(filename=filename, content_type=content_type, data=content)
    label = label_from_scan(scan_summary)
    policy_result = evaluate_policy(label=label, action=ACTION_EXTERNAL_LINK)

    file_record = FileRecord(
        filename=filename,
        owner_user_id=current_user.id,
        size=len(content),
        content_type=content_type,
        label=label,
        scan_summary_json=scan_summary,
        policy_decision=policy_result.decision,
        decision_reason=policy_result.reason,
        storage_path=str(storage_path),
    )
    db.add(file_record)
    db.flush()

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="upload",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"filename": filename, "label": label},
    )
    add_audit(
        db,
        actor_user_id=current_user.id,
        action="policy_decision",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "action": ACTION_EXTERNAL_LINK,
            "decision": policy_result.decision,
            "reason": policy_result.reason,
            "required_fields": policy_result.required_fields,
        },
    )

    db.commit()
    db.refresh(file_record)
    return FileOut(**_serialize_file(file_record))


@router.get("", response_model=list[FileOut])
def list_files(
    scope: str = Query("mine", description="mine|shared|all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FileOut]:
    if scope == "all":
        if current_user.role != "Admin":
            raise HTTPException(status_code=403, detail="Admin role required for scope=all")
        files = db.query(FileRecord).filter(FileRecord.is_deleted.is_(False)).order_by(FileRecord.created_at.desc()).all()
    elif scope == "shared":
        file_ids_query = select(InternalShare.file_id).where(InternalShare.user_id == current_user.id)
        files = (
            db.query(FileRecord)
            .filter(FileRecord.id.in_(file_ids_query), FileRecord.is_deleted.is_(False))
            .order_by(FileRecord.created_at.desc())
            .all()
        )
    else:
        files = (
            db.query(FileRecord)
            .filter(FileRecord.owner_user_id == current_user.id, FileRecord.is_deleted.is_(False))
            .order_by(FileRecord.created_at.desc())
            .all()
        )

    return [FileOut(**_serialize_file(file_record)) for file_record in files]


@router.get("/activity")
def recent_activity(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if current_user.role != "Admin":
        query = query.filter(AuditLog.actor_user_id == current_user.id)
    rows = query.limit(limit).all()
    return rows


@router.get("/{file_id}", response_model=FileDetailsOut)
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileDetailsOut:
    file_record = _get_file_or_404(db, file_id)
    if not _can_access_file(db, file_record, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    shares = (
        db.query(InternalShare, User)
        .join(User, User.id == InternalShare.user_id)
        .filter(InternalShare.file_id == file_record.id)
        .all()
    )

    external_links = (
        db.query(ExternalLink)
        .filter(ExternalLink.file_id == file_record.id)
        .order_by(ExternalLink.created_at.desc())
        .all()
    )

    payload = _serialize_file(file_record)
    payload["internal_shares"] = [
        {
            "id": share.id,
            "user_id": user.id,
            "email": user.email,
            "permission": share.permission,
            "created_at": share.created_at,
        }
        for share, user in shares
    ]
    payload["external_links"] = [
        {
            "id": link.id,
            "token": link.token,
            "expires_at": link.expires_at,
            "status": link.status,
            "created_at": link.created_at,
            "justification": link.justification,
        }
        for link in external_links
    ]

    return FileDetailsOut(**payload)


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    if not _can_access_file(db, file_record, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    real_path = file_record.storage_path
    if not real_path:
        raise HTTPException(status_code=404, detail="Stored file not found")
    if not Path(real_path).exists():
        raise HTTPException(status_code=404, detail="Stored file not found")

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="download",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"filename": file_record.filename},
    )
    db.commit()

    return FileResponse(path=real_path, media_type=file_record.content_type, filename=file_record.filename)


@router.post("/{file_id}/share/internal")
def add_internal_share(
    file_id: int,
    payload: InternalShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    _ensure_owner_or_admin(file_record, current_user)

    target_user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    policy_result = evaluate_policy(label=file_record.label, action=ACTION_INTERNAL_SHARE)
    required_fields = set(policy_result.required_fields)
    if "target_user_email" in required_fields and not payload.email:
        raise HTTPException(status_code=400, detail="target_user_email is required by policy")

    share = (
        db.query(InternalShare)
        .filter(InternalShare.file_id == file_record.id, InternalShare.user_id == target_user.id)
        .first()
    )
    if share:
        return {"status": "exists", "share_id": share.id}

    share = InternalShare(file_id=file_record.id, user_id=target_user.id, permission="read")
    db.add(share)
    db.flush()

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="policy_decision",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "action": ACTION_INTERNAL_SHARE,
            "decision": policy_result.decision,
            "reason": policy_result.reason,
        },
    )
    add_audit(
        db,
        actor_user_id=current_user.id,
        action="internal_share_added",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"shared_with_user_id": target_user.id, "shared_with_email": target_user.email},
    )

    db.commit()
    return {
        "status": "created",
        "share_id": share.id,
        "policy_decision": policy_result.decision,
        "policy_reason": policy_result.reason,
    }


@router.delete("/{file_id}/share/internal/{share_id}")
def remove_internal_share(
    file_id: int,
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    _ensure_owner_or_admin(file_record, current_user)

    share = (
        db.query(InternalShare)
        .filter(InternalShare.id == share_id, InternalShare.file_id == file_record.id)
        .first()
    )
    if not share:
        raise HTTPException(status_code=404, detail="Share record not found")

    db.delete(share)

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="internal_share_removed",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"share_id": share_id, "removed_user_id": share.user_id},
    )
    db.commit()
    return {"status": "removed", "share_id": share_id}


@router.post("/{file_id}/share/external-link")
def create_external_link(
    file_id: int,
    payload: ExternalLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    _ensure_owner_or_admin(file_record, current_user)

    policy_result = evaluate_policy(label=file_record.label, action=ACTION_EXTERNAL_LINK)
    if policy_result.decision == DECISION_BLOCK:
        add_audit(
            db,
            actor_user_id=current_user.id,
            action="policy_decision",
            target_type="file",
            target_id=str(file_record.id),
            metadata={
                "action": ACTION_EXTERNAL_LINK,
                "decision": policy_result.decision,
                "reason": policy_result.reason,
            },
        )
        db.commit()
        raise HTTPException(status_code=403, detail=policy_result.reason)

    required_fields = set(policy_result.required_fields)
    if "expires_at" in required_fields and not payload.expires_at:
        raise HTTPException(status_code=400, detail="expires_at is required")
    if "justification" in required_fields and not payload.justification:
        raise HTTPException(status_code=400, detail="justification is required")

    expires_at = payload.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="expires_at must be in the future")

    token = secrets.token_urlsafe(24)
    link = ExternalLink(
        file_id=file_record.id,
        token=token,
        expires_at=expires_at,
        created_by=current_user.id,
        status="active",
        justification=payload.justification,
    )

    db.add(link)
    db.flush()

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="policy_decision",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "action": ACTION_EXTERNAL_LINK,
            "decision": policy_result.decision,
            "reason": policy_result.reason,
            "required_fields": policy_result.required_fields,
        },
    )

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="external_link_created",
        target_type="file",
        target_id=str(file_record.id),
        metadata={
            "link_id": link.id,
            "expires_at": expires_at.isoformat(),
            "decision": policy_result.decision,
        },
    )

    db.commit()

    return {
        "status": "created",
        "link": {
            "id": link.id,
            "token": link.token,
            "expires_at": link.expires_at,
            "status": link.status,
            "justification": link.justification,
            "created_at": link.created_at,
        },
        "policy_decision": policy_result.decision,
        "policy_reason": policy_result.reason,
    }


@router.post("/{file_id}/share/external-link/{link_id}/revoke")
def revoke_external_link(
    file_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    _ensure_owner_or_admin(file_record, current_user)

    link = db.query(ExternalLink).filter(ExternalLink.id == link_id, ExternalLink.file_id == file_record.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="External link not found")

    link.status = "revoked"

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="external_link_revoked",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"link_id": link.id},
    )
    db.commit()
    return {"status": "revoked", "link_id": link.id}


@router.get("/{file_id}/audit")
def file_audit_timeline(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = _get_file_or_404(db, file_id)
    if not _can_access_file(db, file_record, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.target_type == "file", AuditLog.target_id == str(file_id))
        .order_by(AuditLog.timestamp.desc())
        .all()
    )
    return rows
