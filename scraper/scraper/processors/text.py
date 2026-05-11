"""Text normalization utilities."""

from __future__ import annotations

import re
import unicodedata


# Control characters to strip (excluding common whitespace)
_CONTROL_CHAR_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)

# Collapse runs of whitespace (spaces/tabs) into a single space
_MULTI_SPACE_RE = re.compile(r"[^\S\n]+")

# Collapse runs of blank lines into at most two newlines
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalize extracted text for storage and indexing.

    Steps:
      1. Unicode NFC normalization
      2. Remove control characters (keep normal whitespace)
      3. Collapse horizontal whitespace runs into a single space
      4. Collapse vertical whitespace (3+ newlines -> 2)
      5. Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # 1. Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)

    # 2. Remove control characters
    text = _CONTROL_CHAR_RE.sub("", text)

    # 3. Collapse horizontal whitespace (preserve newlines)
    text = _MULTI_SPACE_RE.sub(" ", text)

    # 4. Collapse excessive blank lines
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)

    # 5. Strip
    text = text.strip()

    return text
