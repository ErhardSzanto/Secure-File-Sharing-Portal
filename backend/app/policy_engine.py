from dataclasses import dataclass
from typing import Any, Dict, Optional

ACTION_INTERNAL_SHARE = "INTERNAL_SHARE"
ACTION_EXTERNAL_LINK = "EXTERNAL_LINK"

DECISION_ALLOW = "allow"
DECISION_WARN = "warn"
DECISION_BLOCK = "block"


@dataclass
class PolicyResult:
    decision: str
    reason: str
    required_fields: list[str]


def evaluate_policy(label: str, action: str, context: Optional[Dict[str, Any]] = None) -> PolicyResult:
    context = context or {}
    normalized_label = label.strip().lower()

    if action == ACTION_INTERNAL_SHARE:
        if normalized_label == "highly confidential":
            return PolicyResult(
                decision=DECISION_ALLOW,
                reason="Highly Confidential files can only be shared to explicit allowlisted users.",
                required_fields=["target_user_email"],
            )
        return PolicyResult(
            decision=DECISION_ALLOW,
            reason="Internal sharing is allowed for this classification.",
            required_fields=[],
        )

    if action == ACTION_EXTERNAL_LINK:
        if normalized_label in {"public", "internal"}:
            return PolicyResult(
                decision=DECISION_ALLOW,
                reason="External links allowed with an explicit expiry.",
                required_fields=["expires_at"],
            )

        if normalized_label == "confidential":
            return PolicyResult(
                decision=DECISION_WARN,
                reason="Confidential data needs a business justification and expiry before external sharing.",
                required_fields=["justification", "expires_at"],
            )

        if normalized_label == "highly confidential":
            return PolicyResult(
                decision=DECISION_BLOCK,
                reason="Highly Confidential data cannot be shared through external links.",
                required_fields=[],
            )

    return PolicyResult(
        decision=DECISION_WARN,
        reason="Policy fallback triggered. Manual review is recommended.",
        required_fields=list(context.keys()),
    )
