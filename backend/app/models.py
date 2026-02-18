from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="User")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    size = Column(Integer, nullable=False)
    content_type = Column(String(128), nullable=False)
    label = Column(String(64), nullable=False)
    scan_summary_json = Column(JSON, nullable=False, default={})
    policy_decision = Column(String(16), nullable=False)
    decision_reason = Column(Text, nullable=False)
    storage_path = Column(String(500), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    owner = relationship("User")


class InternalShare(Base):
    __tablename__ = "internal_shares"
    __table_args__ = (UniqueConstraint("file_id", "user_id", name="uq_file_user_share"),)

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(String(32), nullable=False, default="read")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    file = relationship("FileRecord")
    user = relationship("User")


class ExternalLink(Base):
    __tablename__ = "external_links"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    justification = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    file = relationship("FileRecord")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata_json = Column(JSON, nullable=False, default={})

    actor = relationship("User")
