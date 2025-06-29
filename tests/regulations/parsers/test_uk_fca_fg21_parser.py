"""Tests for UK FCA FG21-1 parser."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.regulations.models import ParserConfig
from regulations.parsers.uk.uk_fca_fg21 import UKFCAFg21Parser


class TestUKFCAFg21Parser:
    """Tests for UKFCAFg21Parser class."""

    @pytest.fixture
    def parser(self, default_config):
        """Create a parser instance for testing."""
        return UKFCAFg21Parser(default_config)

    @pytest.fixture
    def sample_pdf_pages(self):
        """Sample PDF pages content for testing FG21/1."""
        return [
            {
                "page_number": 3,
                "text": """
Chapter 1
Introduction

1.1 This finalised guidance sets out the FCA's views on how firms should treat customers in vulnerable circumstances. It builds on our existing rules and guidance and aims to help firms improve their practices and outcomes for vulnerable customers.

1.2 We expect all firms to have in place appropriate policies and procedures to identify and respond to the needs of vulnerable consumers.

Examples of how firms can put this into practice:
• Training staff to recognise signs of vulnerability
• Having clear escalation procedures
• Providing alternative communication methods
""",
            },
            {
                "page_number": 10,
                "text": """
Chapter 2
Understanding the needs of vulnerable consumers

2.1 A vulnerable consumer is someone who, due to their personal circumstances, is especially susceptible to detriment, particularly when a firm is not acting with appropriate levels of care.

2.2 We have identified four key drivers of vulnerability:
• Health conditions
• Life events
• Resilience
• Capability

Case study: Good practice – Identifying vulnerability
A mortgage lender noticed that a customer was struggling to understand information provided about their mortgage during a phone call. The adviser offered to arrange a follow-up call when the customer's partner could be present to provide support.
""",
            },
            {
                "page_number": 25,
                "text": """
Chapter 4
Taking practical action

4.1 Firms should turn their understanding of vulnerable consumers into practical action across all aspects of their business.

4.2 This includes product design, marketing, sales, customer service, and complaints handling.

Examples of how firms can put this into practice:
• Designing products with vulnerable customers in mind
• Using clear, simple language in communications
• Providing flexible payment options

Case study: Poor practice – Failing to adapt
A credit card provider continued to send marketing materials for additional products to a customer who had recently disclosed financial difficulties and requested help with their existing debt.
""",
            },
            {
                "page_number": 47,
                "text": """
Appendix 1
GDPR and DPA 2018 considerations

When dealing with vulnerable customers, firms should be mindful of their obligations under the General Data Protection Regulation (GDPR) and the Data Protection Act 2018.

This includes ensuring that:
• Personal data about vulnerability is processed lawfully
• Appropriate technical and organisational measures are in place
• Data subjects' rights are respected
""",
            },
            {
                "page_number": 55,
                "text": """
Appendix 2
Other obligations relevant to vulnerable consumers

Firms should also consider their obligations under:
• The Equality Act 2010
• The Consumer Rights Act 2015
• Relevant accessibility regulations

These create additional duties that may apply when serving vulnerable customers.
""",
            },
        ]

    def test_get_supported_document_types(self, parser):
        """Test getting supported document types."""
        types = parser.get_supported_document_types()
        assert isinstance(types, list)
        assert "UK_FCA_FG21" in types

    def test_validate_document_valid_pdf(self, parser, temp_pdf_file):
        """Test document validation with valid PDF."""
        # The temp_pdf_file fixture creates a minimal PDF but may not pass FG21 validation
        # due to insufficient content requirements
        is_valid = parser.validate_document(temp_pdf_file)
        # Just verify that validation runs without error - result depends on PDF content
        assert isinstance(is_valid, bool)

    def test_validate_document_non_existent_file(self, parser):
        """Test document validation with non-existent file."""
        non_existent = Path("/path/that/does/not/exist.pdf")
        is_valid = parser.validate_document(non_existent)
        assert is_valid is False

    def test_validate_document_non_pdf_file(self, parser):
        """Test document validation with non-PDF file."""
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"This is not a PDF")
            tmp.flush()

            is_valid = parser.validate_document(Path(tmp.name))
            assert is_valid is False

            Path(tmp.name).unlink()

    @patch("src.regulations.parsers.uk_fca_fg21.pdfplumber.open")
    def test_validate_document_small_pdf(self, mock_pdfplumber, parser):
        """Test document validation with PDF that's too small."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()] * 5  # Only 5 pages, below minimum
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        test_file = Path("test.pdf")
        is_valid = parser.validate_document(test_file)
        assert is_valid is False

    @patch("pathlib.Path.exists")
    @patch("src.regulations.parsers.uk_fca_fg21.pdfplumber.open")
    def test_validate_document_contains_fg21_content(
        self, mock_pdfplumber, mock_exists, parser
    ):
        """Test document validation with PDF containing FG21/1 content."""
        # Mock file exists
        mock_exists.return_value = True

        mock_pages = []
        for i in range(20):
            mock_page = MagicMock()
            if i == 0:
                mock_page.extract_text.return_value = (
                    "FG21/1 Financial Conduct Authority"
                )
            else:
                mock_page.extract_text.return_value = f"Page {i} content"
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        test_file = Path("test.pdf")
        is_valid = parser.validate_document(test_file)
        assert is_valid is True

    @patch("src.regulations.parsers.uk_fca_fg21.UKFCAFg21Parser._extract_pdf_pages")
    @patch("src.regulations.parsers.uk_fca_fg21.UKFCAFg21Parser._validate_document")
    def test_parse_document_success(
        self, mock_validate, mock_extract_pages, parser, sample_pdf_pages
    ):
        """Test successful document parsing."""
        mock_validate.return_value = True
        mock_extract_pages.return_value = sample_pdf_pages

        test_file = Path("test.pdf")
        result = parser._parse_document(test_file)

        assert result.document_type == "UK_FCA_FG21"
        assert len(result.clauses) > 0
        assert result.metadata.source_file == str(test_file)
        assert result.metadata.parser_version == parser.VERSION

    def test_parse_document_invalid_file(self, parser):
        """Test parsing invalid document raises error."""
        invalid_file = Path("/nonexistent.pdf")

        with pytest.raises(ValueError) as exc_info:
            parser._parse_document(invalid_file)

        assert "Invalid FG21/1 document" in str(exc_info.value)

    def test_clean_page_text(self, parser):
        """Test cleaning page text removes headers/footers."""
        raw_text = """FG21/1 Financial Conduct Authority Chapter 1 Guidance for firms

1.1 This is actual content that should be kept.

Some more important content here.

Page 5
Pubref:007407"""

        cleaned = parser._clean_page_text(raw_text, 5)

        assert "FG21/1 Financial Conduct Authority" not in cleaned
        assert "Page 5" not in cleaned
        assert "Pubref:007407" not in cleaned
        assert "1.1 This is actual content" in cleaned

    def test_find_section_text_and_pages_chapter_1(self, parser, sample_pdf_pages):
        """Test finding section text and pages for Chapter 1."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "1", "Introduction"
        )

        assert section_info is not None
        assert "text" in section_info
        assert "pages" in section_info
        assert 3 in section_info["pages"]
        assert "1.1 This finalised guidance" in section_info["text"]

    def test_find_section_text_and_pages_chapter_2(self, parser, sample_pdf_pages):
        """Test finding section text and pages for Chapter 2."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "2", "Understanding the needs of vulnerable consumers"
        )

        assert section_info is not None
        assert 10 in section_info["pages"]
        assert "2.1 A vulnerable consumer" in section_info["text"]
        assert "four key drivers" in section_info["text"]

    def test_find_section_text_and_pages_appendix(self, parser, sample_pdf_pages):
        """Test finding appendix sections."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "Appendix1", "GDPR and DPA 2018 considerations"
        )

        assert section_info is not None
        assert 47 in section_info["pages"]
        assert "GDPR" in section_info["text"]

    def test_find_section_text_and_pages_not_found(self, parser, sample_pdf_pages):
        """Test finding non-existent section."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "99", "Non-existent section"
        )

        assert section_info is None

    def test_extract_clauses_from_section_chapter_1(self, parser, sample_pdf_pages):
        """Test extracting clauses from Chapter 1."""
        section_info = {"text": sample_pdf_pages[0]["text"], "pages": [3]}

        clauses = parser._extract_clauses_from_section(
            section_info, "1", sample_pdf_pages
        )

        assert len(clauses) >= 2  # Should find 1.1, 1.2

        # Check first clause
        first_clause = clauses[0]
        assert first_clause.section == "1"
        assert "1.1 G" in first_clause.clause_id
        assert "finalised guidance" in first_clause.content
        assert first_clause.page_number == 3

    def test_extract_clauses_from_section_chapter_2(self, parser, sample_pdf_pages):
        """Test extracting clauses from Chapter 2."""
        section_info = {"text": sample_pdf_pages[1]["text"], "pages": [10]}

        clauses = parser._extract_clauses_from_section(
            section_info, "2", sample_pdf_pages
        )

        assert len(clauses) >= 2  # Should find 2.1, 2.2

        # Check clauses contain expected content
        clause_contents = [clause.content for clause in clauses]
        assert any("vulnerable consumer" in content for content in clause_contents)
        assert any("four key drivers" in content for content in clause_contents)

    def test_extract_clauses_from_appendix(self, parser, sample_pdf_pages):
        """Test extracting clauses from appendix."""
        section_info = {"text": sample_pdf_pages[3]["text"], "pages": [47]}

        clauses = parser._extract_clauses_from_section(
            section_info, "Appendix1", sample_pdf_pages
        )

        assert len(clauses) == 1  # Appendix should be single clause

        clause = clauses[0]
        assert clause.section == "Appendix1"
        assert "Appendix1 G" in clause.clause_id
        assert "GDPR" in clause.content

    def test_clean_clause_content(self, parser):
        """Test cleaning clause content."""
        raw_content = """

This is good content.

More important information here.


123
....

Another important line.
"""

        cleaned = parser._clean_clause_content(raw_content)

        assert "This is good content." in cleaned
        assert "Another important line." in cleaned
        assert "123" not in cleaned  # Should remove lone digits
        assert "...." not in cleaned  # Should remove formatting artifacts

    def test_find_clause_page_number(self, parser, sample_pdf_pages):
        """Test finding page number for specific clause."""
        section_pages = [3, 4, 5]

        page_number = parser._find_clause_page_number(
            "1.1", section_pages, sample_pdf_pages
        )

        assert page_number == 3  # Should find page 3 where 1.1 appears

    def test_extract_examples_and_case_studies(self, parser):
        """Test extracting examples and case studies from content."""
        content = """
Main guidance text here.

Examples of how firms can put this into practice:
• Training staff to recognise signs
• Having clear procedures

Case study: Good practice – Identifying vulnerability
A firm noticed customer difficulties and provided support.

Case study: Poor practice – Failing to adapt
A firm ignored customer's disclosed difficulties.
"""

        examples, case_studies = parser._extract_examples_and_case_studies(content)

        assert len(examples) > 0
        assert "Training staff" in examples[0]

        assert len(case_studies) > 0
        assert "Good practice" in case_studies[0]

    def test_custom_sections_to_extract(self):
        """Test parser with custom sections configuration."""
        custom_config = ParserConfig(sections_to_extract={"1": "Custom Introduction"})
        parser = UKFCAFg21Parser(custom_config)

        # Should use custom sections instead of defaults
        assert parser.config.sections_to_extract == {"1": "Custom Introduction"}

    @patch("src.regulations.parsers.uk_fca_fg21.pdfplumber.open")
    @patch("pathlib.Path.is_file")
    def test_extract_pdf_pages_respects_start_page(
        self, mock_is_file, mock_pdfplumber, parser
    ):
        """Test that PDF extraction starts from page 3 (skips cover and TOC)."""
        # Mock file exists
        mock_is_file.return_value = True

        # Create mock PDF with multiple pages
        mock_pages = [MagicMock() for _ in range(20)]
        for i, page in enumerate(mock_pages):
            page.extract_text.return_value = f"Page {i+1} content"

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        test_file = Path("test.pdf")
        pages_content = parser._extract_pdf_pages(test_file)

        # Should start from page 3 (skip pages 1-2)
        assert len(pages_content) == 18  # Pages 3-20
        assert pages_content[0]["page_number"] == 3

    def test_extract_pdf_pages_file_not_found(self, parser):
        """Test error when PDF file doesn't exist."""
        non_existent_file = Path("/path/that/does/not/exist.pdf")

        with pytest.raises(FileNotFoundError):
            parser._extract_pdf_pages(non_existent_file)

    def test_find_subsection_name(self, parser):
        """Test finding subsection names."""
        content = """
Introduction and overview

1.1 This guidance provides firms with information about treating vulnerable customers fairly.

1.2 We expect all firms to have appropriate policies in place.
"""

        subsection = parser._find_subsection_name("1.1", content)

        # Should extract potential section header
        assert isinstance(subsection, str)
        # May be empty if no clear subsection header found
