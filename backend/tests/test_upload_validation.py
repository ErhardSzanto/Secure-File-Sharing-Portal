from app.upload_validation import validate_upload_filename


def test_supported_file_extensions_are_allowed():
    assert validate_upload_filename("report.txt") is True
    assert validate_upload_filename("records.csv") is True
    assert validate_upload_filename("scan.PDF") is True


def test_unsupported_extensions_are_blocked():
    assert validate_upload_filename("archive.zip") is False
    assert validate_upload_filename("malware.exe") is False
