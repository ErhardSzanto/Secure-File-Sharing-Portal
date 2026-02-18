from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

    class Config:
        orm_mode = True


class FileOut(BaseModel):
    id: int
    filename: str
    owner_user_id: int
    created_at: datetime
    size: int
    content_type: str
    label: str
    scan_summary_json: Dict[str, Any]
    policy_decision: str
    decision_reason: str
    is_deleted: bool

    class Config:
        orm_mode = True


class InternalShareRequest(BaseModel):
    email: str


class ExternalLinkRequest(BaseModel):
    expires_at: datetime
    justification: Optional[str] = None


class LabelOverrideRequest(BaseModel):
    label: str
    justification: str


class AuditOut(BaseModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    target_type: str
    target_id: str
    timestamp: datetime
    metadata_json: Dict[str, Any]

    class Config:
        orm_mode = True


class ExternalLinkOut(BaseModel):
    id: int
    token: str
    expires_at: datetime
    status: str
    created_at: datetime
    justification: Optional[str]

    class Config:
        orm_mode = True


class FileDetailsOut(FileOut):
    internal_shares: List[Dict[str, Any]]
    external_links: List[ExternalLinkOut]


class PolicySummaryRule(BaseModel):
    label: str
    action: str
    decision: str
    reason: str
    required_fields: List[str]


class AuditReportQuery(BaseModel):
    from_date: date
    to_date: date
