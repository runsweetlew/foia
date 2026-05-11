"""HTML text extraction utilities."""

from __future__ import annotations

from bs4 import BeautifulSoup

# Tags whose entire subtree should be removed before extracting text
REMOVE_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "iframe"}


def extract_html_text(html: str) -> str:
    """Strip away non-content elements and return the visible text.

    Removes scripts, styles, navigation, headers, footers, and other
    non-content elements, then returns the remaining text with
    reasonable whitespace.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "lxml")

    # Remove non-content tags entirely
    for tag_name in REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove hidden elements
    for tag in soup.find_all(attrs={"style": True}):
        style = tag.get("style", "")
        if "display:none" in style.replace(" ", "") or "visibility:hidden" in style.replace(" ", ""):
            tag.decompose()

    # Extract text with newlines between block elements
    text = soup.get_text(separator="\n")

    # Clean up excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)
