import re
from pathlib import Path
from typing import List, Dict, Tuple

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
MAX_ATTACHMENT_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

def is_valid_email(email: str) -> bool:
    """Checks if an email string is formatted correctly."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_attachments(base_dir: Path, attachment_config: dict) -> Tuple[List[Path], List[str]]:
    """
    Validates that configured attachment files exist and are within size limits.
    Returns: (list_of_valid_paths, list_of_errors)
    """
    valid_paths: List[Path] = []
    errors: List[str] = []

    directory_name = attachment_config.get("directory", "attachments")
    target_dir = base_dir / directory_name

    if not target_dir.exists():
        errors.append(f"Attachments folder does not exist: {target_dir}")
        return valid_paths, errors

    files = attachment_config.get("files", [])
    if not files:
        errors.append("No attachment files listed in config.yaml.")
        return valid_paths, errors

    for filename in files:
        file_path = target_dir / filename
        if not file_path.exists():
            errors.append(f"Attachment file not found: {file_path}")
            continue

        size = file_path.stat().st_size
        if size > MAX_ATTACHMENT_SIZE_BYTES:
            errors.append(f"File '{filename}' exceeds 15MB limit ({size / (1024*1024):.2f} MB).")
            continue

        if size == 0:
            errors.append(f"File '{filename}' is empty (0 bytes).")
            continue

        valid_paths.append(file_path)

    return valid_paths, errors
