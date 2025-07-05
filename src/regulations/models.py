from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegulationCountry(str, Enum):
    EU = "EU"
    UK = "UK"
    US = "US"


REGULATION_COUNTRIES = {
    RegulationCountry.EU: "European Union",
    RegulationCountry.UK: "United Kingdom",
    RegulationCountry.US: "United States",
}


class ClauseType(str, Enum):
    """Enumeration for regulation clause types."""

    REGULATION = "R"
    GUIDANCE = "G"
    UNKNOWN = "UNKNOWN"


class RegulationClause(BaseModel):
    """Model representing a single regulation clause."""

    model_config = ConfigDict()

    section: str = Field(..., description="Main section number (e.g., '5.2A', '7')")
    clause_id: str = Field(
        ..., description="Full clause identifier with type (e.g., '5.2A.1 R')"
    )
    main_section_name: str | None = Field(None, description="Main section title")
    subsection_name: str | None = Field(None, description="Subsection name")
    content: str = Field(..., description="Complete clause content")
    page_number: int = Field(..., description="Source page number")
    clause_type: ClauseType = Field(
        default=ClauseType.UNKNOWN, description="Type of clause"
    )

    @model_validator(mode="after")
    def determine_clause_type(self) -> "RegulationClause":
        """Auto-determine clause type from clause_id if not provided."""
        # If explicitly set to something other than UNKNOWN, keep it
        if self.clause_type != ClauseType.UNKNOWN:
            return self

        # Auto-detect from clause_id
        if self.clause_id.endswith(" R"):
            self.clause_type = ClauseType.REGULATION
        elif self.clause_id.endswith(" G"):
            self.clause_type = ClauseType.GUIDANCE
        else:
            self.clause_type = ClauseType.UNKNOWN

        return self


class DocumentMetadata(BaseModel):
    """Metadata for a parsed regulation document."""

    source_file: str = Field(..., description="Path to source file")
    total_pages: int = Field(..., ge=1, description="Total number of pages in document")
    sections_extracted: list[str] = Field(
        default_factory=list, description="List of sections that were extracted"
    )
    parser_version: str | None = Field(None, description="Version of parser used")
    extraction_date: datetime = Field(
        default_factory=datetime.now, description="When the document was parsed"
    )
    country: RegulationCountry = Field(
        ..., description="Country of origin (e.g., 'UK')"
    )
    additional_info: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ParsedDocument(BaseModel):
    """Model representing a fully parsed regulation document."""

    document_type: str = Field(
        ..., description="Type of document (e.g., 'UK_FCA_CONC')"
    )
    version: str | None = Field(None, description="Document version")
    country: RegulationCountry = Field(
        ..., description="Country of origin (e.g., 'UK')"
    )
    clauses: list[RegulationClause] = Field(
        default_factory=list, description="Extracted regulation clauses"
    )
    metadata: DocumentMetadata = Field(..., description="Document metadata")

    @property
    def clause_count(self) -> int:
        """Return the total number of clauses."""
        return len(self.clauses)

    def get_clauses_by_section(self, section: str) -> list[RegulationClause]:
        """Get all clauses for a specific section."""
        return [clause for clause in self.clauses if clause.section == section]

    def get_sections(self) -> list[str]:
        """Get list of all unique sections in the document."""
        return list(set(clause.section for clause in self.clauses))


class ClauseDocument:
    """Simple wrapper for clause data for embeddings."""

    def __init__(self, clause: RegulationClause, document: "ParsedDocument"):
        self.content: str = clause.content
        self.section: str = clause.section
        self.clause_id: str = clause.clause_id
        self.document_type: str = document.document_type
        self.version: str | None = document.version
        self.country: RegulationCountry = document.country
        self.metadata: DocumentMetadata = document.metadata


class ClauseMetadata(BaseModel):
    """Metadata for a parsed regulation document."""

    source_file: str = Field(..., description="Path to source file")
    total_pages: int = Field(..., ge=1, description="Total number of pages in document")
    sections_extracted: list[str] = Field(
        default_factory=list, description="List of sections that were extracted"
    )
    document_type: str = Field(
        ..., description="Type of document (e.g., 'UK_FCA_CONC')"
    )
    clause: RegulationClause = Field(
        ..., description="Clause identifier (e.g., '5.2A.1 R')"
    )
    parser_version: str | None = Field(None, description="Version of parser used")
    extraction_date: datetime = Field(
        default_factory=datetime.now, description="When the document was parsed"
    )
    country: RegulationCountry = Field(
        ..., description="Country of origin (e.g., 'UK')"
    )
    additional_info: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ClauseQuestionDocument:
    """Simple wrapper for clause data for embeddings."""

    def __init__(
        self, question: str, clause: RegulationClause, metadata: "ClauseMetadata"
    ):
        self.question: str = question
        self.country: RegulationCountry = document.country
        self.metadata: ClauseMetadata = document.metadata


class ParserConfig(BaseModel):
    """Configuration model for regulation parsers."""

    # Document file settings
    document_file_path: str | None = Field(
        None, description="Path to the regulation document file"
    )

    # PDF parsing settings
    pdf_start_page: int = Field(40, ge=1, description="Page to start parsing from")
    pdf_x_tolerance: int = Field(
        2, ge=0, description="X tolerance for PDF text extraction"
    )
    pdf_y_tolerance: int = Field(
        3, ge=0, description="Y tolerance for PDF text extraction"
    )

    # Output settings
    output_format: str = Field("json", description="Output format for parsed data")
    include_metadata: bool = Field(
        True, description="Whether to include metadata in output"
    )

    # Section extraction settings
    sections_to_extract: dict[str, str] | None = Field(
        None, description="Specific sections to extract"
    )

    @classmethod
    def default(cls) -> "ParserConfig":
        """Create a ParserConfig with default values.

        This method is provided for type checker compatibility.
        """
        return cls()  # type: ignore[call-arg]
