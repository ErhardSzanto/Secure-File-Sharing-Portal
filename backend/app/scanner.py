import re
from typing import Iterable

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
GENERIC_ID_RE = re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|ID[:\s-]?[A-Za-z0-9]{6,14})\b", re.IGNORECASE)

HIGH_VOLUME_THRESHOLD = 5


def _redact(value: str) -> str:
    value = value.strip()
    if "@" in value:
        local, domain = value.split("@", 1)
        redacted_local = (local[:1] + "***") if local else "***"
        redacted_domain = domain[:1] + "***" if domain else "***"
        return f"{redacted_local}@{redacted_domain}"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


def _valid_luhn(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _extract_text(filename: str, content_type: str, data: bytes) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    lowered_name = filename.lower()

    if lowered_name.endswith(".pdf") or content_type == "application/pdf":
        # Minimal parsing only; avoid deep PDF extraction in the first iteration.
        preview = data[:16_384].decode("latin-1", errors="ignore")
        text = " ".join(re.findall(r"[A-Za-z0-9@._:\-+]{4,}", preview))
        notes.append("PDF scan is limited to filename and trivial text preview.")
        return text, "limited", notes

    text = data.decode("utf-8", errors="ignore")
    return text, "full", notes


def _capture(pattern: re.Pattern[str], text: str) -> list[str]:
    return [match.group(0) for match in pattern.finditer(text)]


def _summarize_examples(matches: Iterable[str]) -> list[str]:
    seen = set()
    redacted: list[str] = []
    for match in matches:
        masked = _redact(match)
        if masked in seen:
            continue
        seen.add(masked)
        redacted.append(masked)
        if len(redacted) >= 3:
            break
    return redacted


def scan_content(filename: str, content_type: str, data: bytes) -> dict:
    text, scan_scope, notes = _extract_text(filename, content_type, data)
    searchable_text = f"{filename} {text}"

    emails = _capture(EMAIL_RE, searchable_text)
    phones = _capture(PHONE_RE, searchable_text)
    cards = [match for match in _capture(CARD_RE, searchable_text) if _valid_luhn(match)]
    generic_ids = _capture(GENERIC_ID_RE, searchable_text)

    categories = {
        "emails": emails,
        "phones": phones,
        "credit_cards": cards,
        "generic_ids": generic_ids,
    }

    counts = {name: len(values) for name, values in categories.items()}
    detected = [name for name, count in counts.items() if count > 0]
    total_matches = sum(counts.values())

    return {
        "scan_scope": scan_scope,
        "counts": counts,
        "examples": {name: _summarize_examples(values) for name, values in categories.items()},
        "categories_detected": detected,
        "total_matches": total_matches,
        "notes": notes,
    }


def label_from_scan(summary: dict) -> str:
    total_matches = int(summary.get("total_matches", 0))
    categories_detected = summary.get("categories_detected", [])

    if total_matches == 0:
        return "Internal"

    if len(categories_detected) >= 2 or total_matches >= HIGH_VOLUME_THRESHOLD:
        return "Highly Confidential"

    return "Confidential"
