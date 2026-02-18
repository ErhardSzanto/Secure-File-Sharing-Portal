from app.policy_engine import (
    ACTION_EXTERNAL_LINK,
    ACTION_INTERNAL_SHARE,
    DECISION_ALLOW,
    DECISION_BLOCK,
    DECISION_WARN,
    evaluate_policy,
)


def test_public_external_link_is_allow_with_expiry_requirement():
    result = evaluate_policy("Public", ACTION_EXTERNAL_LINK)
    assert result.decision == DECISION_ALLOW
    assert "expires_at" in result.required_fields


def test_confidential_external_link_is_warn_with_justification_and_expiry():
    result = evaluate_policy("Confidential", ACTION_EXTERNAL_LINK)
    assert result.decision == DECISION_WARN
    assert set(result.required_fields) == {"justification", "expires_at"}


def test_highly_confidential_external_link_is_blocked():
    result = evaluate_policy("Highly Confidential", ACTION_EXTERNAL_LINK)
    assert result.decision == DECISION_BLOCK
    assert result.required_fields == []


def test_highly_confidential_internal_share_is_allow_with_allowlist_requirement():
    result = evaluate_policy("Highly Confidential", ACTION_INTERNAL_SHARE)
    assert result.decision == DECISION_ALLOW
    assert result.required_fields == ["target_user_email"]
