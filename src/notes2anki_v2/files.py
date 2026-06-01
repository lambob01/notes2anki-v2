from __future__ import annotations

import time
from pathlib import Path


SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".pptx"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def wait_for_file_stability(
    path: Path,
    check_interval: float = 0.5,
    stable_period: float = 2.0,
    timeout: float = 30.0,
) -> bool:
    start = time.monotonic()
    try:
        last_size = path.stat().st_size
    except OSError:
        return False

    stable_since = time.monotonic()
    while True:
        time.sleep(check_interval)
        try:
            current_size = path.stat().st_size
        except OSError:
            return False

        if current_size != last_size:
            last_size = current_size
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= stable_period:
            return True

        if time.monotonic() - start >= timeout:
            return False

