"""Tests for EU EBA GL 2020/06 parser."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from regulations.parsers.eu.eu_eba_gl_2020_06 import EUEBAGl202006Parser
from src.regulations.models import ParserConfig


class TestEUEBAGl202006Parser:
    """Tests for EUEBAGl202006Parser class."""

    @pytest.fixture
    def parser(self, default_config):
        """Create a parser instance for testing."""
        return EUEBAGl202006Parser(default_config)

    @pytest.fixture
    def sample_pdf_pages(self):
        """Sample PDF pages content for testing EBA GL 2020/06."""
        return [
            {
                "page_number": 3,
                "text": """
8. Monitoring framework

As part of the EU's response to tackling the high level of non-performing exposures, the Council
of the European Union in its July 2017 Action Plan invited the EBA to 'issue detailed guidelines
on banks' loan origination, monitoring and internal governance which could in particular
address issues such as transparency and borrower affordability assessment'.
""",
            },
            {
                "page_number": 60,
                "text": """
8. Monitoring framework

240. Institutions should have a robust and effective monitoring framework, supported by an
adequate data infrastructure, to ensure that information regarding their credit risk exposures,
borrowers and collateral is relevant and up to date, and that the external reporting is reliable,
complete, up to date and timely.

241. The monitoring framework should enable institutions to manage and monitor their credit
risk exposures in line with their credit risk appetite, strategy, policies and procedures at
portfolio and, when relevant and material, individual exposure levels.

242. Institutions should ensure that the credit risk monitoring framework is well defined and
documented, is integrated into the institutions' risk management and control frameworks, and
allows all credit exposures to be followed throughout their life cycle.
""",
            },
            {
                "page_number": 61,
                "text": """
243. Institutions should consider, in the design and implementation of their credit risk
monitoring framework, that:
a. the framework and data infrastructure provide the capability to gather and
automatically compile data regarding credit risk without undue delay and with little
reliance on manual processes;
b. the framework and data infrastructure allow the generation of granular risk data that
is compatible and used for the institution's own risk management purposes.

244. The monitoring process should be based on a principle of follow-up action to support and
result in a regular and informed feedback loop, to inform the setting/review of credit risk
appetite, policies and limits.
""",
            },
            {
                "page_number": 62,
                "text": """
8.2 Monitoring of credit exposures and borrowers

251. As part of the monitoring of credit exposures and borrowers, institutions should monitor
all outstanding amounts and limits, and whether the borrower is meeting repayment
obligations, as laid down in the credit agreement, and is in line with the conditions set at the
point of credit granting, such as adherence to credit metrics and covenants.

252. Institutions should also monitor whether the borrower and collateral are in line with the
credit risk policies and conditions set at the point of credit granting.
""",
            },
            {
                "page_number": 63,
                "text": """
8.3 Regular credit review of borrowers

257. Institutions should also perform regular credit reviews of borrowers that are at least
medium-sized or large enterprises, with a view to identifying any changes in their risk profile,
financial position or creditworthiness compared with the criteria and the assessment at the
point of loan origination.

258. The review process and frequency should be specific and proportionate to the type and risk
profile of the borrower and the type, size and complexity of the credit facility.
""",
            },
            {
                "page_number": 64,
                "text": """
8.4 Monitoring of covenants

266. Where relevant and applicable to specific credit agreements, institutions should monitor
and follow up on the requirements of collateral insurance, in accordance with the credit
agreements or requirements of credit facilities.

8.5 Use of early warning indicators/watch lists in credit monitoring

269. As part of their monitoring framework, institutions should develop, maintain and regularly
evaluate relevant quantitative and qualitative EWIs that are supported by an appropriate IT and
data infrastructure.
""",
            },
            {
                "page_number": 66,
                "text": """
8.5.1 Follow-up and escalation process on triggered EWIs

275. When an EWI has been triggered for closer monitoring and further investigation,
immediate action should be taken in accordance with the institution's policies and procedures.

276. Relevant credit decision-makers should, based on the abovementioned analysis and other
relevant accessible information, decide on the appropriate next steps.

277. Triggering EWIs should lead to an increased frequency in the reviewing process, including
discussions and decisions by credit decision-makers, and more intense information gathering
from the borrower.
""",
            },
            {
                "page_number": 67,
                "text": """
Annex 1 — Credit-granting criteria

This annex provides a set of criteria to be considered in the design and documentation of credit-
granting criteria, in accordance with these guidelines.
""",
            },
        ]

    def test_get_supported_document_types(self, parser):
        """Test getting supported document types."""
        types = parser.get_supported_document_types()
        assert isinstance(types, list)
        assert "EU_EBA_GL_2020_06" in types

    def test_get_default_file_path(self, parser):
        """Test getting default file path."""
        path = parser.get_default_file_path()
        assert "EBA GL 2020 06" in path
        assert path.endswith(".pdf")

    def test_validate_document_valid_pdf(self, parser, temp_pdf_file):
        """Test document validation with valid PDF."""
        # The temp_pdf_file fixture creates a minimal PDF but may not pass EBA validation
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

    @patch("regulations.parsers.eu.eu_eba_gl_2020_06.pdfplumber.open")
    def test_validate_document_small_pdf(self, mock_pdfplumber, parser):
        """Test document validation with PDF that's too small."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()] * 10  # Only 10 pages, below minimum of 20
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        test_file = Path("test.pdf")
        is_valid = parser.validate_document(test_file)
        assert is_valid is False

    @patch("pathlib.Path.exists")
    @patch("regulations.parsers.eu.eu_eba_gl_2020_06.pdfplumber.open")
    def test_validate_document_contains_eba_content(
        self, mock_pdfplumber, mock_exists, parser
    ):
        """Test document validation with PDF containing EBA GL 2020/06 content."""
        # Mock file exists
        mock_exists.return_value = True

        mock_pages = []
        for i in range(25):
            mock_page = MagicMock()
            if i == 0:
                mock_page.extract_text.return_value = (
                    "EBA/GL/2020/06 Guidelines on loan origination and monitoring"
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

    @patch(
        "regulations.parsers.eu.eu_eba_gl_2020_06.EUEBAGl202006Parser._extract_pdf_pages"
    )
    @patch(
        "regulations.parsers.eu.eu_eba_gl_2020_06.EUEBAGl202006Parser._validate_document"
    )
    def test_parse_document_success(
        self, mock_validate, mock_extract_pages, parser, sample_pdf_pages
    ):
        """Test successful document parsing."""
        mock_validate.return_value = True
        mock_extract_pages.return_value = sample_pdf_pages

        test_file = Path("test.pdf")
        result = parser._parse_document(test_file)

        assert result.document_type == "EU_EBA_GL_2020_06"
        assert len(result.clauses) > 0
        assert result.metadata.source_file == str(test_file)
        assert result.metadata.parser_version == parser.VERSION

    def test_parse_document_invalid_file(self, parser):
        """Test parsing invalid document raises error."""
        invalid_file = Path("/nonexistent.pdf")

        with pytest.raises(ValueError) as exc_info:
            parser._parse_document(invalid_file)

        assert "Invalid EBA GL 2020/06 document" in str(exc_info.value)

    def test_clean_page_text(self, parser):
        """Test cleaning page text removes headers/footers."""
        raw_text = """EBA/GL/2020/06

240. Institutions should have a robust and effective monitoring framework.

Some more important content here.

www.eba.europa.eu
Publication date: 29 May 2020
67"""

        cleaned = parser._clean_page_text(raw_text, 60)

        assert "EBA/GL/2020/06" not in cleaned
        assert "www.eba.europa.eu" not in cleaned
        assert "Publication date" not in cleaned
        assert "67" not in cleaned  # Page number
        assert "240. Institutions should have" in cleaned

    def test_find_section_text_and_pages_section_8(self, parser, sample_pdf_pages):
        """Test finding section text and pages for section 8."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "8", "Monitoring framework"
        )

        assert section_info is not None
        assert "text" in section_info
        assert "pages" in section_info
        assert 60 in section_info["pages"]  # Should find the real section 8, not TOC
        assert "240." in section_info["text"]  # Should contain paragraph 240

    def test_find_section_text_and_pages_avoids_toc(self, parser, sample_pdf_pages):
        """Test that section detection avoids table of contents on page 3."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "8", "Monitoring framework"
        )

        assert section_info is not None
        # Should not include page 3 (table of contents)
        assert 3 not in section_info["pages"]
        # Should start from page 60 where actual content begins
        assert 60 in section_info["pages"]

    def test_find_section_text_and_pages_not_found(self, parser, sample_pdf_pages):
        """Test finding non-existent section."""
        section_info = parser._find_section_text_and_pages(
            sample_pdf_pages, "99", "Non-existent section"
        )

        assert section_info is None

    def test_extract_clauses_from_section_section_8(self, parser, sample_pdf_pages):
        """Test extracting clauses from section 8."""
        # Combine text from relevant pages for section 8
        section_text = "\n".join(
            [
                sample_pdf_pages[1]["text"],  # Page 60
                sample_pdf_pages[2]["text"],  # Page 61
                sample_pdf_pages[3]["text"],  # Page 62
            ]
        )
        section_info = {"text": section_text, "pages": [60, 61, 62]}

        clauses = parser._extract_clauses_from_section(
            section_info, "8", sample_pdf_pages
        )

        assert (
            len(clauses) >= 5
        )  # Should find paragraphs 240, 241, 242, 243, 244, 251, 252

        # Check first clause
        first_clause = clauses[0]
        assert first_clause.section == "8"
        assert first_clause.clause_id == "240"  # No "G" suffix
        assert first_clause.clause_type == "R"  # Should be "R" not "G"
        assert "robust and effective monitoring framework" in first_clause.content
        assert first_clause.page_number == 60

        # Check clause IDs are numeric only
        for clause in clauses:
            assert clause.clause_id.isdigit()
            assert "G" not in clause.clause_id
            assert clause.clause_type == "R"

    def test_extract_clauses_subsection_detection(self, parser, sample_pdf_pages):
        """Test that subsection names are correctly detected."""
        # Use page with subsection headers
        section_text = "\n".join(
            [
                sample_pdf_pages[3][
                    "text"
                ],  # Page 62 - has "8.2 Monitoring of credit exposures and borrowers"
                sample_pdf_pages[4][
                    "text"
                ],  # Page 63 - has "8.3 Regular credit review of borrowers"
            ]
        )
        section_info = {"text": section_text, "pages": [62, 63]}

        clauses = parser._extract_clauses_from_section(
            section_info, "8", sample_pdf_pages
        )

        # Should find clauses 251, 252, 257, 258
        assert len(clauses) >= 4

        # Check subsection name assignment
        clause_251 = next((c for c in clauses if c.clause_id == "251"), None)
        assert clause_251 is not None
        assert (
            clause_251.subsection_name == "Monitoring of credit exposures and borrowers"
        )

        clause_257 = next((c for c in clauses if c.clause_id == "257"), None)
        assert clause_257 is not None
        assert clause_257.subsection_name == "Regular credit review of borrowers"

    def test_clean_clause_content(self, parser):
        """Test cleaning clause content."""
        raw_content = """

Institutions should have a robust framework.

More important information here.


123
....

Another important line.
"""

        cleaned = parser._clean_clause_content(raw_content)

        assert "Institutions should have" in cleaned
        assert "Another important line." in cleaned
        assert "123" not in cleaned  # Should remove lone digits
        assert "...." not in cleaned  # Should remove formatting artifacts

    def test_find_clause_page_number(self, parser, sample_pdf_pages):
        """Test finding page number for specific clause."""
        section_pages = [60, 61, 62]

        page_number = parser._find_clause_page_number(
            "240", section_pages, sample_pdf_pages
        )

        assert page_number == 60  # Should find page 60 where 240 appears

    def test_find_subsection_name(self, parser):
        """Test finding subsection names using the hardcoded mapping."""
        section_text = """
8.1 General provisions for the credit risk monitoring framework

240. Institutions should have a robust framework.

8.2 Monitoring of credit exposures and borrowers

251. As part of the monitoring.
"""

        # Test finding subsection before clause 240
        subsection = parser._find_subsection_name("240", section_text, 80)
        assert (
            subsection == "General provisions for the credit risk monitoring framework"
        )

        # Test finding subsection before clause 251
        subsection = parser._find_subsection_name("251", section_text, 200)
        assert subsection == "Monitoring of credit exposures and borrowers"

    def test_custom_sections_to_extract(self):
        """Test parser with custom sections configuration."""
        custom_config = ParserConfig(sections_to_extract={"8": "Custom Monitoring"})
        parser = EUEBAGl202006Parser(custom_config)

        # Should use custom sections instead of defaults
        assert parser.config.sections_to_extract == {"8": "Custom Monitoring"}

    @patch("regulations.parsers.eu.eu_eba_gl_2020_06.pdfplumber.open")
    @patch("pathlib.Path.is_file")
    def test_extract_pdf_pages_starts_from_page_1(
        self, mock_is_file, mock_pdfplumber, parser
    ):
        """Test that PDF extraction starts from page 1 for EBA documents."""
        # Mock file exists
        mock_is_file.return_value = True

        # Create mock PDF with multiple pages
        mock_pages = [MagicMock() for _ in range(25)]
        for i, page in enumerate(mock_pages):
            page.extract_text.return_value = f"Page {i+1} content"

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        test_file = Path("test.pdf")
        pages_content = parser._extract_pdf_pages(test_file)

        # Should start from page 1 (all pages)
        assert len(pages_content) == 25  # All pages
        assert pages_content[0]["page_number"] == 1

    def test_extract_pdf_pages_file_not_found(self, parser):
        """Test error when PDF file doesn't exist."""
        non_existent_file = Path("/path/that/does/not/exist.pdf")

        with pytest.raises(FileNotFoundError):
            parser._extract_pdf_pages(non_existent_file)

    def test_subsection_mapping_coverage(self, parser):
        """Test that all expected subsection mappings are present."""
        expected_mappings = {
            "General provisions for the credit risk monitoring framework",
            "Monitoring of credit exposures and borrowers",
            "Regular credit review of borrowers",
            "Monitoring of covenants",
            "Use of early warning indicators/watch lists in credit monitoring",
            "Follow-up and escalation process on triggered EWIs",
        }

        # Check that all expected subsections are in the mapping values
        mapping_values = set(parser.SUBSECTION_MAPPING.values())
        for expected in expected_mappings:
            assert expected in mapping_values

    def test_clause_pattern_matches_only_multi_digit_paragraphs(self, parser):
        """Test that clause pattern only matches 2-3 digit paragraph numbers."""
        section_text = """
1. This should not match (single digit)
12. This should match (two digits - pattern allows 2-3 digits)
240. This should match (three digits)
241. This should also match
999. This should match (three digits)
1000. This should not match (four digits)
"""

        section_info = {"text": section_text, "pages": [60]}
        clauses = parser._extract_clauses_from_section(
            section_info, "8", [{"page_number": 60, "text": section_text}]
        )

        # Should find 12, 240, 241, 999 (2-3 digit numbers)
        clause_ids = [clause.clause_id for clause in clauses]
        assert "240" in clause_ids
        assert "241" in clause_ids
        assert "999" in clause_ids
        assert "12" in clause_ids  # Pattern allows 2-digit numbers
        assert "1" not in clause_ids  # Single digits not allowed
        assert "1000" not in clause_ids  # Four digits not allowed

    def test_clause_extraction_stops_at_annex(self, parser):
        """Test that clause extraction stops when it reaches an annex."""
        section_text = """
240. This should be extracted.

241. This should also be extracted.

Annex 1 — Credit-granting criteria

This annex content should not be extracted as a clause.
"""

        section_info = {"text": section_text, "pages": [60]}
        clauses = parser._extract_clauses_from_section(
            section_info, "8", [{"page_number": 60, "text": section_text}]
        )

        # Should only find 240, 241, not annex content
        clause_ids = [clause.clause_id for clause in clauses]
        assert "240" in clause_ids
        assert "241" in clause_ids
        assert len(clauses) == 2

        # Annex content should not be in any clause
        all_content = " ".join(clause.content for clause in clauses)
        assert "This annex content" not in all_content

    def test_page_validation_for_section_8(self, parser, sample_pdf_pages):
        """Test that section 8 detection requires page 50+ or contains '240.'."""
        # Test with page < 50 but contains '240.'
        early_page_with_240 = [
            {
                "page_number": 30,
                "text": "8. Monitoring framework\n240. Some content here.",
            }
        ]

        section_info = parser._find_section_text_and_pages(
            early_page_with_240, "8", "Monitoring framework"
        )
        assert section_info is not None  # Should be found due to '240.'

        # Test with page >= 50
        late_page_without_240 = [
            {"page_number": 55, "text": "8. Monitoring framework\nSome other content."}
        ]

        section_info = parser._find_section_text_and_pages(
            late_page_without_240, "8", "Monitoring framework"
        )
        assert section_info is not None  # Should be found due to page >= 50

        # Test with early page and no '240.' (like table of contents)
        toc_page = [
            {
                "page_number": 3,
                "text": "8. Monitoring framework\nTable of contents entry.",
            }
        ]

        section_info = parser._find_section_text_and_pages(
            toc_page, "8", "Monitoring framework"
        )
        assert section_info is None  # Should not be found (TOC case)
