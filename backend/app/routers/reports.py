import csv
from datetime import date, datetime, time, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import AuditLog, FileRecord, InternalShare, User

router = APIRouter(prefix="/reports", tags=["reports"])


def _csv_response(filename: str, content: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit.csv")
def export_audit_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="'to' must be greater than or equal to 'from'")

    start_dt = datetime.combine(from_date, time.min)
    end_dt = datetime.combine(to_date + timedelta(days=1), time.min)

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.timestamp >= start_dt, AuditLog.timestamp < end_dt)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "timestamp", "actor_user_id", "action", "target_type", "target_id", "metadata_json"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.timestamp.isoformat(),
                row.actor_user_id,
                row.action,
                row.target_type,
                row.target_id,
                row.metadata_json,
            ]
        )

    add_audit(
        db,
        actor_user_id=admin_user.id,
        action="report_export",
        target_type="report",
        target_id="audit_csv",
        metadata={"from": from_date.isoformat(), "to": to_date.isoformat(), "rows": len(rows)},
    )
    db.commit()

    return _csv_response("audit-report.csv", buffer.getvalue())


@router.get("/files/{file_id}/audit.csv")
def export_file_audit_timeline_csv(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id, FileRecord.is_deleted.is_(False)).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    has_access = current_user.role == "Admin" or current_user.id == file_record.owner_user_id
    if not has_access:
        share = (
            db.query(InternalShare)
            .filter(InternalShare.file_id == file_record.id, InternalShare.user_id == current_user.id)
            .first()
        )
        has_access = share is not None

    if not has_access:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.target_type == "file", AuditLog.target_id == str(file_record.id))
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "timestamp", "actor_user_id", "action", "target_type", "target_id", "metadata_json"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.timestamp.isoformat(),
                row.actor_user_id,
                row.action,
                row.target_type,
                row.target_id,
                row.metadata_json,
            ]
        )

    add_audit(
        db,
        actor_user_id=current_user.id,
        action="report_export",
        target_type="file",
        target_id=str(file_record.id),
        metadata={"report": "file_audit_timeline", "rows": len(rows)},
    )
    db.commit()

    return _csv_response(f"file-{file_id}-audit.csv", buffer.getvalue())
