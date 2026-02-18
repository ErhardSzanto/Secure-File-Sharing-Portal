from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".csv", ".pdf"}


def validate_upload_filename(filename: str) -> bool:
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS
