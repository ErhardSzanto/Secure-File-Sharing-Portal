from app.scanner import label_from_scan, scan_content


def test_scanner_redacts_sensitive_examples_and_counts_matches():
    payload = b"""
    Contact jane.doe@example.com or +1 (555) 123-9876.
    Test card 4111 1111 1111 1111 and ID: ID-ABC12345.
    """

    summary = scan_content("customer-export.txt", "text/plain", payload)

    assert summary["counts"]["emails"] >= 1
    assert summary["counts"]["phones"] >= 1
    assert summary["counts"]["credit_cards"] >= 1
    assert summary["counts"]["generic_ids"] >= 1

    first_email_example = summary["examples"]["emails"][0]
    assert "jane.doe@example.com" not in first_email_example
    assert "***" in first_email_example


def test_label_from_scan_internal_when_no_hits():
    summary = scan_content("note.txt", "text/plain", b"hello world")
    assert label_from_scan(summary) == "Internal"


def test_label_from_scan_highly_confidential_for_multiple_categories():
    payload = b"email one@example.com phone 555-123-4567"
    summary = scan_content("mixed.txt", "text/plain", payload)
    assert label_from_scan(summary) == "Highly Confidential"


def test_pdf_scan_is_limited_scope():
    summary = scan_content("sample.pdf", "application/pdf", b"/Type /Page jane@example.com")
    assert summary["scan_scope"] == "limited"
