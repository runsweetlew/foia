"""Configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://foia:foia@localhost:5432/foia",
)

STORAGE_DIR = os.environ.get("STORAGE_DIR", "/data/pdfs")

# How far back to scrape by default (months)
DEFAULT_LOOKBACK_MONTHS = int(os.environ.get("LOOKBACK_MONTHS", "24"))

# HTTP request timeout in seconds
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))

# Maximum PDF file size to download (bytes) -- 100 MB default
MAX_PDF_SIZE = int(os.environ.get("MAX_PDF_SIZE", str(100 * 1024 * 1024)))
