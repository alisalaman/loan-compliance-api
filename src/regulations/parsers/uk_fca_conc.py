import re
from pathlib import Path

import pdfplumber

from ..models import DocumentMetadata, ParsedDocument, RegulationClause
from .base import BaseRegulationParser


class UKFCACoNCParser(BaseRegulationParser):
    """Parser for UK FCA Consumer Credit Sourcebook (CONC) documents."""

    VERSION = "1.0.0"

    SECTIONS_TO_EXTRACT = {
        "5.2A": "Creditworthiness assessment",
        "2.10": "Mental capacity guidance",
        "7": "Arrears, default and recovery (including repossessions)",
    }

    def get_default_file_path(self) -> str:
        """Get the default file path for UK FCA CONC documents."""
        return "data/regulations/uk/fca/CONC.pdf"

    def get_supported_document_types(self) -> list[str]:
        """Return list of supported document types."""
        return ["UK_FCA_CONC"]

    def _validate_document(self, file_path: Path) -> bool:
        """Check if this is a valid CONC PDF."""
        if not file_path.exists():
            return False

        if not file_path.suffix.lower() == ".pdf":
            return False

        # Additional validation: check if PDF contains CONC content
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) < 10:  # CONC should be a substantial document
                    return False

                # Check first few pages for CONC indicators
                for page_num in range(min(5, len(pdf.pages))):
                    text = pdf.pages[page_num].extract_text()
                    if text and ("CONC" in text or "Consumer Credit" in text):
                        return True
        except Exception:
            return False

        return False

    def _parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse CONC PDF and extract regulation clauses."""
        if not self._validate_document(file_path):
            raise ValueError(f"Invalid CONC document: {file_path}")

        pages_content = self._extract_pdf_pages(file_path)
        all_clauses = []

        sections_to_extract = (
            self.config.sections_to_extract or self.SECTIONS_TO_EXTRACT
        )

        for section_number, section_title in sections_to_extract.items():
            section_info = self._find_section_text_and_pages(
                pages_content, section_number, section_title
            )

            if section_info:
                clauses = self._extract_clauses_from_section(
                    section_info, section_number, pages_content
                )
                all_clauses.extend(clauses)

        metadata = DocumentMetadata(
            source_file=str(file_path),
            total_pages=len(pages_content),
            sections_extracted=list(sections_to_extract.keys()),
            parser_version=self.VERSION,
            additional_info={
                "start_page": self.config.pdf_start_page,
                "x_tolerance": self.config.pdf_x_tolerance,
                "y_tolerance": self.config.pdf_y_tolerance,
            },
        )

        return ParsedDocument(
            document_type="UK_FCA_CONC", clauses=all_clauses, metadata=metadata
        )

    def _extract_pdf_pages(self, pdf_path: Path) -> list[dict]:
        """Extract text from each page of a PDF."""
        if not pdf_path.is_file():
            raise FileNotFoundError(f"The file '{pdf_path}' was not found.")

        pages_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Skip title pages, TOC, and other preliminary content
                if page_num + 1 < self.config.pdf_start_page:
                    continue
                pages_content.append(
                    {
                        "page_number": page_num + 1,
                        "text": page.extract_text(
                            x_tolerance=self.config.pdf_x_tolerance,
                            y_tolerance=self.config.pdf_y_tolerance,
                        ),
                    }
                )
        return pages_content

    def _find_section_text_and_pages(
        self, pages_content: list[dict], section_number: str, section_title: str
    ) -> dict | None:
        """Find the full text of a section and the pages it spans."""
        section_text_parts = []
        section_pages = []
        in_section = False

        # Special handling for section 7 - look for first subsection instead
        if section_number == "7":
            start_pattern = re.compile(
                r"^\s*7\.1\s+Application", re.IGNORECASE | re.MULTILINE
            )
        else:
            start_pattern = re.compile(
                rf"^\s*{re.escape(section_number)}\s+{re.escape(section_title)}",
                re.IGNORECASE | re.MULTILINE,
            )

        # Pattern to identify actual section headers (not just clause numbers)
        end_pattern = re.compile(
            r"^\s*(\d{1,2}(?:\.\d{1,2}[A-Z]?)?)\s+[A-Z][a-zA-Z\s]{10,}", re.MULTILINE
        )

        for _i, page in enumerate(pages_content):
            text = page["text"]
            if not text:  # Skip empty pages
                continue

            if not in_section:
                if start_pattern.search(text):
                    in_section = True
                    section_pages.append(page["page_number"])
                    # Capture text after the section title on the starting page
                    match = start_pattern.search(text)
                    section_text_parts.append(text[match.end() :].strip())
            else:
                # Check if the current page starts with a new section
                match = end_pattern.search(text)
                if match:
                    next_section_num_prefix = match.group(1).split(".")[0]
                    current_section_num_prefix = section_number.split(".")[0]
                    next_section_full = match.group(1)

                    # Special handling for section 7 - continue until we hit section 8
                    if section_number == "7":
                        if next_section_num_prefix == "8":
                            section_text_parts.append(text[: match.start()].strip())
                            break
                    else:
                        # Stop if we hit a completely different main section
                        if next_section_num_prefix != current_section_num_prefix:
                            section_text_parts.append(text[: match.start()].strip())
                            break

                        # Stop if we hit a sibling section
                        if (
                            next_section_num_prefix == current_section_num_prefix
                            and not next_section_full.startswith(section_number + ".")
                        ):
                            section_text_parts.append(text[: match.start()].strip())
                            break

                section_pages.append(page["page_number"])
                section_text_parts.append(text.strip())

        if not section_text_parts:
            return None

        return {"text": "\n".join(section_text_parts), "pages": section_pages}

    def _find_subsection_name(
        self, clause_id: str, pages_content: list[dict], section_pages: list[int]
    ) -> str:
        """Find the subsection name for a given clause."""
        current_subsection = ""

        for page_info in pages_content:
            if page_info["page_number"] in section_pages:
                text = page_info["text"]
                lines = text.split("\n")

                for _i, line in enumerate(lines):
                    line = line.strip()

                    # Check if this line contains our clause
                    if clause_id in line and len(line) < 200:
                        return current_subsection

                    # Check if this is a subsection header
                    if (
                        len(line) > 3
                        and len(line) < 50
                        and line[0].isupper()
                        and not line[0].isdigit()
                        and "www." not in line
                        and "Release" not in line
                        and "CONC" not in line
                        and "." not in line[:10]
                        and not line.startswith("(")
                        and line.count(" ") < 8
                    ):
                        cleaned = re.sub(r"^[.\s]+|[.\s]+$", "", line)
                        if cleaned and len(cleaned) > 3:
                            current_subsection = cleaned

        return current_subsection

    def _find_main_section_name(
        self, clause_id: str, pages_content: list[dict], section_pages: list[int]
    ) -> str:
        """Find the main section name for a given clause."""
        parts = clause_id.split(".")
        if len(parts) >= 2:
            main_section = ".".join(parts[:2])
        else:
            return ""

        for page_info in pages_content:
            if page_info["page_number"] in section_pages:
                text = page_info["text"]
                lines = text.split("\n")

                for line in lines:
                    line = line.strip()
                    if line.startswith(main_section + " "):
                        title = line[len(main_section) :].strip()
                        title = re.sub(r"^\s*[.]{3,}.*", "", title)
                        title = re.sub(r"\s+", " ", title)
                        if (
                            len(title) > 2
                            and len(title) < 100
                            and not title.startswith("www")
                        ):
                            return title

        return ""

    def _extract_clauses_from_section(
        self, section_info: dict, section_number: str, pages_content: list[dict]
    ) -> list[RegulationClause]:
        """Extract clauses from a section's text."""
        clauses = []
        section_text = section_info["text"]
        section_pages = section_info["pages"]

        # For section 7, we need to match all subsections (7.1.x, 7.2.x, etc.)
        if section_number == "7":
            clause_pattern = re.compile(
                r"^\s*(7\.\d+(?:\.\d+[A-Z]?)*)\s+([RG])\s+(.*?)(?=^\s*7\.\d+(?:\.\d+[A-Z]?)*\s+[RG]\s+|\Z)",
                re.DOTALL | re.MULTILINE,
            )
        else:
            clause_pattern = re.compile(
                rf"^\s*({re.escape(section_number)}(?:\.\d+[A-Z]?)*)\s+([RG])\s+(.*?)(?=^\s*{re.escape(section_number)}(?:\.\d+[A-Z]?)*\s+[RG]\s+|\Z)",
                re.DOTALL | re.MULTILINE,
            )

        for match in clause_pattern.finditer(section_text):
            clause_id = match.group(1).strip()
            clause_type = match.group(2).strip()
            content = match.group(3).strip()

            # Clean up content
            content = "\n".join([line.strip() for line in content.split("\n")]).strip()

            # Find page number
            page_number = section_pages[0] if section_pages else -1
            for p_num in section_pages:
                for page_info in pages_content:
                    if (
                        page_info["page_number"] == p_num
                        and clause_id in page_info["text"]
                    ):
                        page_number = p_num
                        break

            # Find section names
            main_section_name = self._find_main_section_name(
                clause_id, pages_content, section_pages
            )
            subsection_name = self._find_subsection_name(
                clause_id, pages_content, section_pages
            )

            clause = RegulationClause(
                section=section_number,
                clause_id=f"{clause_id} {clause_type}",
                main_section_name=main_section_name,
                subsection_name=subsection_name,
                content=content,
                page_number=page_number,
            )
            clauses.append(clause)

        return clauses
