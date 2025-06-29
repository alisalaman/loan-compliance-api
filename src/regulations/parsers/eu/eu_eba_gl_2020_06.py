import re
from pathlib import Path

import pdfplumber

from regulations.models import DocumentMetadata, ParsedDocument, RegulationClause
from regulations.parsers.base import BaseRegulationParser


class EUEBAGl202006Parser(BaseRegulationParser):
    """Parser for EU EBA Guidelines 2020/06 - Guidelines on loan origination and monitoring."""

    VERSION = "1.0.0"

    # Only extract section 8 as requested
    SECTIONS_TO_EXTRACT = {
        "8": "Monitoring framework",
    }

    def get_default_file_path(self) -> str:
        """Get the default file path for EU EBA GL 2020/06 documents."""
        return "data/regulations/eu/eba/EBA GL 2020 06 Final Report on GL on loan origination and monitoring.pdf"

    def get_supported_document_types(self) -> list[str]:
        """Return list of supported document types."""
        return ["EU_EBA_GL_2020_06"]

    def _validate_document(self, file_path: Path) -> bool:
        """Check if this is a valid EBA GL 2020/06 PDF."""
        if not file_path.exists():
            return False

        if not file_path.suffix.lower() == ".pdf":
            return False

        # Additional validation: check if PDF contains EBA GL 2020/06 content
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) < 20:  # EBA GL should be a substantial document
                    return False

                # Check first few pages for EBA GL 2020/06 indicators
                for page_num in range(min(10, len(pdf.pages))):
                    text = pdf.pages[page_num].extract_text()
                    if text and (
                        "EBA/GL/2020/06" in text
                        or "loan origination and monitoring" in text.lower()
                        or "Guidelines" in text
                        or "European Banking Authority" in text
                    ):
                        return True
        except Exception:
            return False

        return False

    def _parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse EBA GL 2020/06 PDF and extract guidance clauses."""
        if not self._validate_document(file_path):
            raise ValueError(f"Invalid EBA GL 2020/06 document: {file_path}")

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
                "document_type": "EBA GL 2020/06",
                "guidance_title": "Guidelines on loan origination and monitoring",
            },
        )

        return ParsedDocument(
            document_type="EU_EBA_GL_2020_06",
            version=self.VERSION,
            clauses=all_clauses,
            metadata=metadata,
        )

    def _extract_pdf_pages(self, pdf_path: Path) -> list[dict]:
        """Extract text from each page of a PDF, starting from page 1."""
        if not pdf_path.is_file():
            raise FileNotFoundError(f"The file '{pdf_path}' was not found.")

        pages_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Start from page 1 for EBA documents (ignore default start_page config)
                if page_num + 1 < 1:
                    continue

                raw_text = page.extract_text(
                    x_tolerance=self.config.pdf_x_tolerance,
                    y_tolerance=self.config.pdf_y_tolerance,
                )

                # Clean headers and footers
                cleaned_text = self._clean_page_text(raw_text, page_num + 1)

                pages_content.append(
                    {
                        "page_number": page_num + 1,
                        "text": cleaned_text,
                    }
                )
        return pages_content

    def _clean_page_text(self, text: str, page_number: int) -> str:
        """Clean headers, footers, and other noise from page text."""
        if not text:
            return ""

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Filter out headers (EBA/GL/2020/06...)
            if (
                line.startswith("EBA/GL/2020/06")
                or "European Banking Authority" in line
                and len(line) < 50
            ):
                continue

            # Filter out page numbers and simple footers
            if len(line) < 15 and (
                line.isdigit()
                or re.match(r"^Page \d+$", line)
                or re.match(r"^\d+$", line)
            ):
                continue

            # Filter out URL fragments and release info
            if (
                "www.eba.europa.eu" in line
                or line.startswith("Publication")
                or "European Banking Authority" in line and len(line) < 50
            ):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _find_section_text_and_pages(
        self, pages_content: list[dict], section_number: str, section_title: str
    ) -> dict | None:
        """Find the full text of a section and the pages it spans."""
        section_text_parts = []
        section_pages = []
        in_section = False

        # For section 8: look for "8. Monitoring framework" pattern
        # We need to find the instance that contains paragraph 240, not the table of contents
        start_pattern = re.compile(
            rf"^{section_number}\.?\s+{re.escape(section_title)}",
            re.IGNORECASE | re.MULTILINE,
        )
        
        # End at next section (section 9) or end of document
        next_section = str(int(section_number) + 1) if section_number.isdigit() else None
        if next_section:
            end_pattern = re.compile(
                rf"^{next_section}\.?\s+",
                re.IGNORECASE | re.MULTILINE,
            )
        else:
            end_pattern = None

        for page in pages_content:
            text = page["text"]
            if not text:
                continue

            if not in_section:
                match = start_pattern.search(text)
                if match:
                    # Additional validation: ensure this section contains paragraph 240
                    # (the actual section 8 content, not table of contents)
                    if "240." in text or page["page_number"] >= 50:  # Section 8 starts around page 60
                        in_section = True
                        section_pages.append(page["page_number"])
                        # Capture text after the section title
                        section_text_parts.append(text[match.end() :].strip())
            else:
                # Check if we've reached the next section
                if end_pattern:
                    match = end_pattern.search(text)
                    if match:
                        # Section ends here, append text before the new section
                        section_text_parts.append(text[: match.start()].strip())
                        break
                
                section_pages.append(page["page_number"])
                section_text_parts.append(text.strip())

        if not section_text_parts:
            return None

        return {"text": "\n".join(section_text_parts), "pages": section_pages}

    def _extract_clauses_from_section(
        self, section_info: dict, section_number: str, pages_content: list[dict]
    ) -> list[RegulationClause]:
        """Extract guidance clauses from a section's text."""
        clauses = []
        section_text = section_info["text"]
        section_pages = section_info["pages"]

        # Pattern for numbered paragraphs (e.g., "240.", "241.", "242.")
        # EBA uses sequential paragraph numbering, not section.subsection format
        # Only match paragraphs that start with 2 or 3 digits (section 8 uses 240+)
        next_section_num = int(section_number) + 1
        clause_pattern = re.compile(
            rf"^(\d{{2,3}})\.\s+(.*?)(?=^\d{{2,3}}\.\s+|^Annex|^\d+\s+—|^{next_section_num}\.\s+|\Z)",
            re.DOTALL | re.MULTILINE,
        )

        # Track current subsection name across clauses
        current_subsection_name = ""
        
        for match in clause_pattern.finditer(section_text):
            clause_id = match.group(1).strip()  # e.g., "240", "241"
            content = match.group(2).strip()

            # Clean up content
            content = self._clean_clause_content(content)

            # Check if there's a new subsection name before this clause
            new_subsection = self._find_subsection_name(clause_id, section_text, match.start())
            if new_subsection:
                current_subsection_name = new_subsection

            # Find page number for this clause
            page_number = self._find_clause_page_number(
                clause_id, section_pages, pages_content
            )

            clause = RegulationClause(
                section=section_number,
                clause_id=clause_id,  # Just the number, no type suffix
                main_section_name=self.SECTIONS_TO_EXTRACT.get(section_number, ""),
                subsection_name=current_subsection_name,
                content=content,
                page_number=page_number,
                clause_type="R",  # Default to R - regulation
            )
            clauses.append(clause)

        return clauses

    def _clean_clause_content(self, content: str) -> str:
        """Clean up clause content by removing noise and formatting properly."""
        # Split into lines and clean each
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip lines that are just formatting artifacts
            if len(line) < 3 or line.isdigit() or re.match(r"^[.\-\s]+$", line):
                continue

            cleaned_lines.append(line)

        # Join lines back together
        cleaned_content = "\n".join(cleaned_lines)

        # Remove excessive whitespace
        cleaned_content = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned_content)

        return cleaned_content.strip()

    def _find_clause_page_number(
        self, clause_id: str, section_pages: list[int], pages_content: list[dict]
    ) -> int:
        """Find the page number where a specific clause appears."""
        for page_info in pages_content:
            if (
                page_info["page_number"] in section_pages
                and clause_id in page_info["text"]
            ):
                return int(page_info["page_number"])

        # Default to first page of section if not found
        return section_pages[0] if section_pages else -1

    # Dictionary mapping subsection ending phrases to their full names for EBA GL 2020/06
    SUBSECTION_MAPPING = {
        "credit risk monitoring framework": "General provisions for the credit risk monitoring framework",
        "monitoring framework": "General provisions for the credit risk monitoring framework",
        "exposures and borrowers": "Monitoring of credit exposures and borrowers",
        "credit exposures and borrowers": "Monitoring of credit exposures and borrowers",
        "review of borrowers": "Regular credit review of borrowers", 
        "credit review of borrowers": "Regular credit review of borrowers",
        "of covenants": "Monitoring of covenants",
        "monitoring of covenants": "Monitoring of covenants",
        "early warning indicators/watch lists in credit monitoring": "Use of early warning indicators/watch lists in credit monitoring",
        "watch lists in credit monitoring": "Use of early warning indicators/watch lists in credit monitoring",
        "escalation process on triggered EWIs": "Follow-up and escalation process on triggered EWIs",
        "process on triggered EWIs": "Follow-up and escalation process on triggered EWIs",
    }

    def _find_subsection_name(self, clause_id: str, section_text: str, clause_start_pos: int) -> str:
        """Extract subsection name by checking previous lines for known subsection endings."""
        if clause_start_pos == 0:
            return ""
        
        # Look at text before the current clause
        text_before_clause = section_text[:clause_start_pos]
        lines_before = text_before_clause.split('\n')
        
        # Check the last few lines before this clause for subsection name endings
        for i in range(min(10, len(lines_before))):
            line = lines_before[-(i+1)].strip()
            if not line:
                continue
                
            # Check if this line matches any known subsection ending
            for line_ending, full_subsection_name in self.SUBSECTION_MAPPING.items():
                if line.lower().endswith(line_ending.lower()):
                    return full_subsection_name
                    
        return ""