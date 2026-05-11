"""PDF text extraction with OCR fallback."""

from __future__ import annotations

import structlog

log = structlog.get_logger()

# Minimum average characters per page to consider a PDF "digital" (not scanned)
MIN_CHARS_PER_PAGE = 50


def extract_pdf_text(pdf_path: str, skip_ocr: bool = False) -> tuple[str, bool]:
    """Extract text from a PDF file.

    First attempts extraction with pdfplumber (fast, works on digital PDFs).
    If the average characters per page is below the threshold and skip_ocr
    is False, falls back to Tesseract OCR via pytesseract + pdf2image.

    When skip_ocr is True (bulk scraping mode), scanned PDFs are left
    without text — they'll be OCR'd in a separate batch pass later.

    Returns:
        A tuple of (extracted_text, ocr_was_needed).
    """
    text, ocr_needed = _try_pdfplumber(pdf_path)

    if ocr_needed and not skip_ocr:
        log.info("pdf.ocr_fallback", path=pdf_path)
        text = _ocr_extract(pdf_path)
        return text, True
    elif ocr_needed:
        log.debug("pdf.ocr_skipped", path=pdf_path)
        return text, False

    return text, False


def _try_pdfplumber(pdf_path: str) -> tuple[str, bool]:
    """Attempt text extraction with pdfplumber.

    Returns (text, needs_ocr).  If the extracted text is too sparse the
    second element will be True.
    """
    import pdfplumber

    pages_text: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)
    except Exception:
        log.exception("pdf.pdfplumber_error", path=pdf_path)
        return "", True

    full_text = "\n\n".join(pages_text)
    num_pages = len(pages_text) or 1
    avg_chars = len(full_text.strip()) / num_pages

    if avg_chars < MIN_CHARS_PER_PAGE:
        log.info(
            "pdf.sparse_text",
            path=pdf_path,
            avg_chars_per_page=round(avg_chars, 1),
            threshold=MIN_CHARS_PER_PAGE,
        )
        return full_text, True

    return full_text, False


def _ocr_extract(pdf_path: str) -> str:
    """Run Tesseract OCR on each page of the PDF."""
    from pdf2image import convert_from_path
    import pytesseract

    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception:
        log.exception("pdf.pdf2image_error", path=pdf_path)
        return ""

    pages_text: list[str] = []
    for i, image in enumerate(images):
        try:
            page_text = pytesseract.image_to_string(image)
            pages_text.append(page_text)
        except Exception:
            log.exception("pdf.tesseract_error", path=pdf_path, page=i)
            pages_text.append("")

    return "\n\n".join(pages_text)


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF file."""
    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        log.exception("pdf.page_count_error", path=pdf_path)
        return 0
