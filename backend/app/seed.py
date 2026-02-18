import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session
from app.audit import add_audit

from app.audit import add_audit
from app.models import FileRecord, User
from app.policy_engine import ACTION_EXTERNAL_LINK, evaluate_policy
from app.scanner import label_from_scan, scan_content
from app.security import hash_password


DEMO_USERS = [
    {"email": "admin@portal.local", "password": "Admin123!", "role": "Admin"},
    {"email": "user@portal.local", "password": "User123!", "role": "User"},
    {"email": "analyst@portal.local", "password": "Analyst123!", "role": "User"},
]


DEMO_FILES = [
    "public-announcement.txt",
    "internal-roster.csv",
    "customer-export.txt",
]


def _ensure_users(db: Session) -> dict:
    users_by_email = {user.email: user for user in db.query(User).all()}

    for demo_user in DEMO_USERS:
        if demo_user["email"] in users_by_email:
            continue

        user = User(
            email=demo_user["email"],
            password_hash=hash_password(demo_user["password"]),
            role=demo_user["role"],
        )
        db.add(user)
        db.flush()
        users_by_email[user.email] = user
        add_audit(
            db,
            actor_user_id=None,
            action="seed_user_created",
            target_type="user",
            target_id=str(user.id),
            metadata={"email": user.email, "role": user.role},
        )

    return users_by_email


def _already_seeded(db: Session) -> bool:
    return db.query(FileRecord).count() > 0


def seed_demo_data(db: Session, demo_data_dir: Path, upload_dir: Path) -> None:
    users = _ensure_users(db)

    if _already_seeded(db):
        db.commit()
        return

    owner = users.get("user@portal.local")
    if not owner:
        db.commit()
        return

    upload_dir.mkdir(parents=True, exist_ok=True)

    for file_name in DEMO_FILES:
        source_path = demo_data_dir / file_name
        if not source_path.exists():
            continue

        content = source_path.read_bytes()
        scan_summary = scan_content(file_name, "text/plain", content)
        label = label_from_scan(scan_summary)
        policy = evaluate_policy(label=label, action=ACTION_EXTERNAL_LINK)

        generated_name = f"{uuid.uuid4().hex}_{file_name}"
        destination = upload_dir / generated_name
        shutil.copy2(source_path, destination)

        file_record = FileRecord(
            filename=file_name,
            owner_user_id=owner.id,
            size=len(content),
            content_type="text/plain",
            label=label,
            scan_summary_json=scan_summary,
            policy_decision=policy.decision,
            decision_reason=policy.reason,
            storage_path=str(destination),
        )
        db.add(file_record)
        db.flush()

        add_audit(
            db,
            actor_user_id=owner.id,
            action="upload",
            target_type="file",
            target_id=str(file_record.id),
            metadata={"seeded": True, "label": label},
        )

    db.commit()
