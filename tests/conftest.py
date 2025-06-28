"""Pytest configuration and minimal shared fixtures."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.regulations.models import ParserConfig


@pytest.fixture
def default_config():
    """Default parser configuration used across tests."""
    return ParserConfig()


@pytest.fixture
def temp_pdf_file():
    """Create a minimal temporary PDF file for testing."""
    with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        # Minimal PDF with CONC content for validation
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT/F1 12 Tf 100 700 Td(CONC Test Document)Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
299
%%EOF"""
        tmp.write(pdf_content)
        tmp.flush()

        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def conc_pdf_path():
    """Path to actual CONC PDF if available."""
    path = Path("data/regulations/uk/fca/CONC.pdf")
    return path if path.exists() else None
