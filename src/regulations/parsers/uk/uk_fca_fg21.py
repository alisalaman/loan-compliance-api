import re
from pathlib import Path

import pdfplumber

from regulations.models import (
    DocumentMetadata,
    ParsedDocument,
    RegulationClause,
    REGULATION_COUNTRIES,
    RegulationCountry,
)
from regulations.parsers.base import BaseRegulationParser


class UKFCAFg21Parser(BaseRegulationParser):
    """Parser for UK FCA Finalised Guidance FG21/1 - Fair treatment of vulnerable customers."""

    VERSION = "1.0.0"

    # Chapters to extract from FG21/1
    SECTIONS_TO_EXTRACT = {
        "1": "Introduction",
        "2": "Understanding the needs of vulnerable consumers",
        "3": "Skills and capability of staff",
        "4": "Taking practical action",
        "5": "Monitoring and evaluation",
        "Appendix1": "GDPR and DPA 2018 considerations",
        "Appendix2": "Other obligations relevant to vulnerable consumers",
    }

    def get_default_file_path(self) -> str:
        """Get the default file path for UK FCA FG21-1 documents."""
        return "data/regulations/uk/fca/fg21-1.pdf"

    def get_supported_document_types(self) -> list[str]:
        """Return list of supported document types."""
        return ["UK_FCA_FG21"]

    def _validate_document(self, file_path: Path) -> bool:
        """Check if this is a valid FG21/1 PDF."""
        if not file_path.exists():
            return False

        if not file_path.suffix.lower() == ".pdf":
            return False

        # Additional validation: check if PDF contains FG21/1 content
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) < 10:  # FG21/1 should be a substantial document
                    return False

                # Check first few pages for FG21/1 indicators
                for page_num in range(min(5, len(pdf.pages))):
                    text = pdf.pages[page_num].extract_text()
                    if text and (
                        "FG21/1" in text
                        or "vulnerable customers" in text.lower()
                        or "Finalised Guidance" in text
                    ):
                        return True
        except Exception:
            return False

        return False

    def _parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse FG21/1 PDF and extract guidance clauses."""
        if not self._validate_document(file_path):
            raise ValueError(f"Invalid FG21/1 document: {file_path}")

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
            country=RegulationCountry.UK,
            additional_info={
                "start_page": self.config.pdf_start_page,
                "x_tolerance": self.config.pdf_x_tolerance,
                "y_tolerance": self.config.pdf_y_tolerance,
                "document_type": "FG21/1",
                "guidance_title": "Fair treatment of vulnerable customers",
            },
        )

        return ParsedDocument(
            document_type="UK_FCA_FG21",
            version=self.VERSION,
            country=RegulationCountry.UK,
            clauses=all_clauses,
            metadata=metadata,
        )

    def _extract_pdf_pages(self, pdf_path: Path) -> list[dict]:
        """Extract text from each page of a PDF, starting from page 3."""
        if not pdf_path.is_file():
            raise FileNotFoundError(f"The file '{pdf_path}' was not found.")

        pages_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Start from page 3 (skip cover page and table of contents)
                if page_num + 1 < 3:
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

            # Filter out headers (FG21/1 Financial Conduct Authority...)
            if (
                line.startswith("FG21/1 Financial Conduct Authority")
                or "Financial Conduct Authority" in line
                and "Chapter" in line
            ):
                continue

            # Filter out page numbers and simple footers
            if len(line) < 15 and (
                line.isdigit()
                or re.match(r"^Page \d+$", line)
                or line == "Pubref:007407"
            ):
                continue

            # Filter out URL fragments and release info
            if (
                "www.handbook.fca.org.uk" in line
                or line.startswith("Release")
                or line.startswith("n Release")
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

        # Handle different section patterns
        if section_number.startswith("Appendix"):
            # For appendices: "Appendix 1" or "Appendix 2"
            appendix_num = section_number.replace("Appendix", "")
            start_pattern = re.compile(
                rf"^Appendix\s+{appendix_num}", re.IGNORECASE | re.MULTILINE
            )
            # End at next appendix or end of document
            end_pattern = re.compile(r"^Appendix\s+\d+", re.IGNORECASE | re.MULTILINE)
        else:
            # For regular chapters: "Chapter 1", "1 Introduction", etc.
            start_pattern = re.compile(
                rf"^(Chapter\s+{section_number}|{section_number}\s+{re.escape(section_title)})",
                re.IGNORECASE | re.MULTILINE,
            )
            # End at next chapter
            next_chapter = (
                str(int(section_number) + 1) if section_number.isdigit() else "Appendix"
            )
            end_pattern = re.compile(
                rf"^(Chapter\s+{next_chapter}|{next_chapter}\s+|\bAppendix\b)",
                re.IGNORECASE | re.MULTILINE,
            )

        for page in pages_content:
            text = page["text"]
            if not text:
                continue

            if not in_section:
                match = start_pattern.search(text)
                if match:
                    in_section = True
                    section_pages.append(page["page_number"])
                    # Capture text after the section title
                    section_text_parts.append(text[match.end() :].strip())
            else:
                # Check if we've reached the next section
                match = end_pattern.search(text)
                if match:
                    # Section ends here, append text before the new section
                    section_text_parts.append(text[: match.start()].strip())
                    break
                else:
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

        # Pattern for numbered guidance paragraphs (e.g., "1.1", "2.5", "4.12")
        if section_number.startswith("Appendix"):
            # For appendices, extract content as single clauses
            clauses.append(
                self._create_appendix_clause(
                    section_number, section_text, section_pages, pages_content
                )
            )
        else:
            # For regular chapters, extract numbered guidance paragraphs
            clause_pattern = re.compile(
                rf"^({section_number}\.(\d+))\s+(.*?)(?=^{section_number}\.\d+\s+|^Chapter\s+\d+|^Appendix|\Z)",
                re.DOTALL | re.MULTILINE,
            )

            # Track current subsection name across clauses
            current_subsection_name = ""

            for match in clause_pattern.finditer(section_text):
                clause_id = match.group(1).strip()  # e.g., "1.1", "2.5"
                content = match.group(3).strip()

                # Clean up content
                content = self._clean_clause_content(content)

                # Check if there's a new subsection name before this clause
                new_subsection = self._find_subsection_name(
                    clause_id, section_text, match.start()
                )
                if new_subsection:
                    current_subsection_name = new_subsection

                # Find page number for this clause
                page_number = self._find_clause_page_number(
                    clause_id, section_pages, pages_content
                )

                # Determine clause type (all are guidance for FG21/1)
                clause_type = "G"

                # Extract any examples or case studies
                examples, case_studies = self._extract_examples_and_case_studies(
                    content
                )

                clause = RegulationClause(
                    section=section_number,
                    clause_id=f"{clause_id} {clause_type}",
                    main_section_name=self.SECTIONS_TO_EXTRACT.get(section_number, ""),
                    subsection_name=current_subsection_name,
                    content=content,
                    page_number=page_number,
                )
                clauses.append(clause)

        return clauses

    def _create_appendix_clause(
        self,
        section_number: str,
        section_text: str,
        section_pages: list[int],
        pages_content: list[dict],
    ) -> RegulationClause:
        """Create a single clause for appendix content."""
        # Clean up content
        content = self._clean_clause_content(section_text)

        page_number = section_pages[0] if section_pages else -1

        return RegulationClause(
            section=section_number,
            clause_id=f"{section_number} G",
            main_section_name=self.SECTIONS_TO_EXTRACT.get(section_number, ""),
            subsection_name="",
            content=content,
            page_number=page_number,
        )

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

    # Dictionary mapping last line of multi-line subsection names to their flattened form
    SUBSECTION_MAPPING = {
        "This Guidance": "This Guidance",
        "Our Principles for Businesses": "Our Principles for Businesses",
        "Treating Customers Fairly": "Treating Customers Fairly",
        "Monitoring firms’ treatment of vulnerable customers": "Monitoring firms’ treatment of vulnerable customers",
        "that exist in the firm’s target market and customer base": "Understanding the nature and scale of characteristics of vulnerability that exist in the firm’s target market and customer base",
        "consumer experience and outcomes": "Understanding the impact of vulnerability on the needs of consumers in their target market and customer base, by asking themselves what types of harm or disadvantage their customers may be vulnerable to, and how this might affect the consumer experience and outcomes",
        "Examples of harm and disadvantage that firms should be alert to": "Examples of harm and disadvantage that firms should be alert to",
        "Embedding the fair treatment of vulnerable consumers across": "Embedding the fair treatment of vulnerable consumers across the workforce",
        "recognise and respond to a range of characteristics of vulnerability": "Ensuring frontline staff have the necessary skills and capability to recognise and respond to a range of characteristics of vulnerability",
        "Encouraging disclosure": "Encouraging disclosure",
        "Recording and accessing information about consumers’ needs": "Recording and accessing information about consumers’ needs",
        "dealing with vulnerable consumers": "Offering practical and emotional support to frontline staff dealing with vulnerable consumers",
        "Product and service design": "Product and service design",
        "consumers": "Considering if features of products or services exploit vulnerable consumers",
        "inflexibility that could result in harmful impacts": "Designing products and services that meet evolving needs and avoiding inflexibility that could result in harmful impacts",
        "Designing sales processes that meet consumers’ needs": "Designing sales processes that meet consumers’ needs",
        "and service design process": "Taking vulnerable consumers into account at all stages of the product and service design process",
        "Idea generation": "Idea generation",
        "Development": "Development",
        "Testing": "Testing",
        "Launch": "Launch",
        "Review": "Review",
        "Products sold through intermediaries in distribution chains": "Products sold through intermediaries in distribution chains",
        "Customer service": "Customer service",
        "vulnerable consumers to disclose their needs": "Setting up systems and processes in ways that support and enable vulnerable consumers to disclose their needs",
        "needs of vulnerable consumers": "Delivering appropriate customer service that responds flexibly to the needs of vulnerable consumers",
        "Telling consumers about the support available to them": "Telling consumers about the support available to them",
        "Supporting decision-making and third party representation": "Supporting decision-making and third party representation",
        "Third party representation": "Third party representation",
        "Specialist Support": "Specialist Support",
        "good customer service": "Putting in place systems and processes that support the delivery of good customer service",
        "Communications": "Communications",
        "services are presented in ways that are understandable for consumers": "Ensuring all communications and information about products and services are presented in ways that are understandable for consumers",
        "account of their needs": "Considering how to communicate with vulnerable consumers, taking account of their needs",
        "needs of vulnerable consumers are not met": "Implementing appropriate processes to evaluate where the needs of vulnerable consumers are not met",
        "Management information": "Management information",
    }

    def _find_subsection_name(
        self, clause_id: str, section_text: str, clause_start_pos: int
    ) -> str:
        """Extract subsection name by checking previous lines for known subsection endings."""
        if clause_start_pos == 0:
            return ""

        # Look at text before the current clause
        text_before_clause = section_text[:clause_start_pos]
        lines_before = text_before_clause.split("\n")

        # Check the last few lines before this clause for subsection name endings
        for i in range(min(5, len(lines_before))):
            line = lines_before[-(i + 1)].strip()
            if not line:
                continue

            # Check if this line matches any known subsection ending
            for line_ending, full_subsection_name in self.SUBSECTION_MAPPING.items():
                if line.endswith(line_ending):
                    return full_subsection_name

        return ""

    def _extract_examples_and_case_studies(
        self, content: str
    ) -> tuple[list[str], list[str]]:
        """Extract examples and case studies from clause content."""
        examples = []
        case_studies = []

        # Find "Examples of how firms can put this into practice" sections
        example_pattern = re.compile(
            r"Examples of how firms can put this into practice:?\s*(.*?)(?=Case study:|$)",
            re.DOTALL | re.IGNORECASE,
        )

        for match in example_pattern.finditer(content):
            examples.append(match.group(1).strip())

        # Find case studies (both good and poor practice)
        case_study_pattern = re.compile(
            r"Case study:\s*(.*?)(?=Case study:|Examples of how|$)",
            re.DOTALL | re.IGNORECASE,
        )

        for match in case_study_pattern.finditer(content):
            case_studies.append(match.group(1).strip())

        return examples, case_studies
