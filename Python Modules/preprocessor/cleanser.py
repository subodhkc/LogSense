# Cleanse log lines and normalize text
# preprocessor/cleanser.py

import chardet

def cleanse_log_lines(raw_bytes):
    """
    Decodes raw log bytes into clean, structured lines.

    Steps:
    1. Detect encoding using chardet.
    2. Decode using detected encoding (fallback to UTF-8).
    3. Strip lines, remove null bytes and discard empty/noisy lines.

    Args:
        raw_bytes (bytes): Raw content from log file.

    Returns:
        List[str]: Cleaned log lines.
    """
    # Detect encoding (fallback to utf-8 if unknown)
    detected = chardet.detect(raw_bytes)
    encoding = detected['encoding'] or 'utf-8'

    # Decode with replacement for bad bytes
    text = raw_bytes.decode(encoding, errors='replace')

    # Strip lines and remove null characters
    lines = text.splitlines()
    cleaned = [
        line.strip().replace('\x00', '')
        for line in lines
        if line.strip()  # Remove empty or whitespace-only lines
    ]
    return cleaned
