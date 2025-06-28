from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ClauseType(str, Enum):
    """Enumeration for regulation clause types."""
    RULE = "R"
    GUIDANCE = "G"
    UNKNOWN = "UNKNOWN"


class RegulationClause(BaseModel):
    """Model representing a single regulation clause."""
    
    model_config = ConfigDict()
    
    section: str = Field(..., description="Main section number (e.g., '5.2A', '7')")
    clause_id: str = Field(..., description="Full clause identifier with type (e.g., '5.2A.1 R')")
    main_section_name: Optional[str] = Field(None, description="Main section title")
    subsection_name: Optional[str] = Field(None, description="Subsection name")
    content: str = Field(..., description="Complete clause content")
    page_number: int = Field(..., description="Source page number")
    clause_type: ClauseType = Field(default=ClauseType.UNKNOWN, description="Type of clause")
    
    @model_validator(mode='after')
    def determine_clause_type(self):
        """Auto-determine clause type from clause_id if not provided."""
        # If explicitly set to something other than UNKNOWN, keep it
        if self.clause_type != ClauseType.UNKNOWN:
            return self
        
        # Auto-detect from clause_id
        if self.clause_id.endswith(' R'):
            self.clause_type = ClauseType.RULE
        elif self.clause_id.endswith(' G'):
            self.clause_type = ClauseType.GUIDANCE
        else:
            self.clause_type = ClauseType.UNKNOWN
        
        return self


class DocumentMetadata(BaseModel):
    """Metadata for a parsed regulation document."""
    
    source_file: str = Field(..., description="Path to source file")
    total_pages: int = Field(..., ge=1, description="Total number of pages in document")
    sections_extracted: List[str] = Field(default_factory=list, description="List of sections that were extracted")
    parser_version: Optional[str] = Field(None, description="Version of parser used")
    extraction_date: datetime = Field(default_factory=datetime.now, description="When the document was parsed")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ParsedDocument(BaseModel):
    """Model representing a fully parsed regulation document."""
    
    document_type: str = Field(..., description="Type of document (e.g., 'UK_FCA_CONC')")
    version: Optional[str] = Field(None, description="Document version")
    clauses: List[RegulationClause] = Field(default_factory=list, description="Extracted regulation clauses")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    
    @property
    def clause_count(self) -> int:
        """Return the total number of clauses."""
        return len(self.clauses)
    
    def get_clauses_by_section(self, section: str) -> List[RegulationClause]:
        """Get all clauses for a specific section."""
        return [clause for clause in self.clauses if clause.section == section]
    
    def get_sections(self) -> List[str]:
        """Get list of all unique sections in the document."""
        return list(set(clause.section for clause in self.clauses))


class ParserConfig(BaseModel):
    """Configuration model for regulation parsers."""
    
    # Document file settings
    document_file_path: Optional[str] = Field(None, description="Path to the regulation document file")
    
    # PDF parsing settings
    pdf_start_page: int = Field(40, ge=1, description="Page to start parsing from")
    pdf_x_tolerance: int = Field(2, ge=0, description="X tolerance for PDF text extraction")
    pdf_y_tolerance: int = Field(3, ge=0, description="Y tolerance for PDF text extraction")
    
    # Output settings
    output_format: str = Field("json", description="Output format for parsed data")
    include_metadata: bool = Field(True, description="Whether to include metadata in output")
    
    # Section extraction settings
    sections_to_extract: Optional[Dict[str, str]] = Field(None, description="Specific sections to extract")