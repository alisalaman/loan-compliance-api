"""Tests for Pydantic models in the regulations package."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.regulations.models import (
    RegulationClause,
    ParsedDocument,
    DocumentMetadata,
    ParserConfig,
    ClauseType
)


class TestRegulationClause:
    """Tests for RegulationClause model."""
    
    @pytest.fixture
    def valid_clause_data(self):
        """Valid clause data for testing."""
        return {
            "section": "7.1",
            "clause_id": "7.1.1 R",
            "main_section_name": "Application",
            "subsection_name": "General requirements",
            "content": "A firm must establish and maintain arrangements.",
            "page_number": 156
        }
    
    def test_valid_clause_creation(self, valid_clause_data):
        """Test creating a valid regulation clause."""
        clause = RegulationClause(**valid_clause_data)
        
        assert clause.section == "7.1"
        assert clause.clause_id == "7.1.1 R"
        assert clause.clause_type == ClauseType.RULE  # Auto-detected from 'R'
        assert clause.content == "A firm must establish and maintain arrangements."
        assert clause.page_number == 156
    
    def test_clause_type_detection(self):
        """Test automatic clause type detection."""
        rule_clause = RegulationClause(
            section="7.1", clause_id="7.1.1 R", content="Rule content", page_number=1
        )
        assert rule_clause.clause_type == ClauseType.RULE
        
        guidance_clause = RegulationClause(
            section="7.1", clause_id="7.1.1 G", content="Guidance content", page_number=1
        )
        assert guidance_clause.clause_type == ClauseType.GUIDANCE
        
        unknown_clause = RegulationClause(
            section="7.1", clause_id="7.1.1", content="Unknown content", page_number=1
        )
        assert unknown_clause.clause_type == ClauseType.UNKNOWN
    
    def test_invalid_clause_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            RegulationClause(section="7.1")  # Missing required fields
        
        errors = exc_info.value.errors()
        required_fields = {"clause_id", "content", "page_number"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)
    
    def test_negative_page_number(self):
        """Test that negative page numbers are allowed (for unknown pages)."""
        clause = RegulationClause(
            section="7.1",
            clause_id="7.1.1 R", 
            content="Content",
            page_number=-1
        )
        assert clause.page_number == -1


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""
    
    @pytest.fixture
    def valid_metadata(self):
        """Valid metadata for testing."""
        return {
            "source_file": "/path/to/test.pdf",
            "total_pages": 200,
            "sections_extracted": ["5.2A", "2.10", "7"],
            "parser_version": "1.0.0"
        }
    
    def test_valid_metadata_creation(self, valid_metadata):
        """Test creating valid document metadata."""
        metadata = DocumentMetadata(**valid_metadata)
        
        assert metadata.source_file == "/path/to/test.pdf"
        assert metadata.total_pages == 200
        assert metadata.sections_extracted == ["5.2A", "2.10", "7"]
        assert metadata.parser_version == "1.0.0"
        assert isinstance(metadata.extraction_date, datetime)
    
    def test_metadata_with_additional_info(self, valid_metadata):
        """Test metadata with additional info."""
        valid_metadata["additional_info"] = {"start_page": 40, "tolerance": 2}
        metadata = DocumentMetadata(**valid_metadata)
        
        assert metadata.additional_info["start_page"] == 40
        assert metadata.additional_info["tolerance"] == 2
    
    def test_invalid_total_pages(self, valid_metadata):
        """Test validation fails for negative total pages."""
        valid_metadata["total_pages"] = -1
        
        with pytest.raises(ValidationError):
            DocumentMetadata(**valid_metadata)


class TestParsedDocument:
    """Tests for ParsedDocument model."""
    
    @pytest.fixture
    def sample_clauses(self):
        """Sample clauses for testing."""
        return [
            RegulationClause(
                section="7.1", clause_id="7.1.1 R", content="Rule 1", page_number=156
            ),
            RegulationClause(
                section="7.1", clause_id="7.1.2 G", content="Guidance 1", page_number=156
            ),
            RegulationClause(
                section="7.2", clause_id="7.2.1 R", content="Rule 2", page_number=158
            )
        ]
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return DocumentMetadata(
            source_file="/test.pdf",
            total_pages=200,
            sections_extracted=["7"],
            parser_version="1.0.0"
        )
    
    def test_valid_document_creation(self, sample_clauses, sample_metadata):
        """Test creating a valid parsed document."""
        document = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=sample_clauses,
            metadata=sample_metadata
        )
        
        assert document.document_type == "UK_FCA_CONC"
        assert len(document.clauses) == 3
        assert document.clause_count == 3
        assert document.metadata.source_file == "/test.pdf"
    
    def test_clause_count_property(self, sample_clauses, sample_metadata):
        """Test clause_count property calculation."""
        document = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=sample_clauses,
            metadata=sample_metadata
        )
        
        assert document.clause_count == len(sample_clauses)
    
    def test_empty_clauses_list(self, sample_metadata):
        """Test document with empty clauses list."""
        document = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=[],
            metadata=sample_metadata
        )
        
        assert document.clause_count == 0
        assert document.clauses == []
    
    def test_get_clauses_by_section(self, sample_clauses, sample_metadata):
        """Test filtering clauses by section."""
        document = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=sample_clauses,
            metadata=sample_metadata
        )
        
        section_7_1_clauses = document.get_clauses_by_section("7.1")
        assert len(section_7_1_clauses) == 2
        assert all(clause.section == "7.1" for clause in section_7_1_clauses)
        
        section_7_2_clauses = document.get_clauses_by_section("7.2")
        assert len(section_7_2_clauses) == 1
        assert section_7_2_clauses[0].section == "7.2"
        
        non_existent_clauses = document.get_clauses_by_section("99")
        assert len(non_existent_clauses) == 0


class TestParserConfig:
    """Tests for ParserConfig model."""
    
    def test_default_config(self):
        """Test default parser configuration."""
        config = ParserConfig()
        
        assert config.pdf_start_page == 40
        assert config.pdf_x_tolerance == 2
        assert config.pdf_y_tolerance == 3
        assert config.sections_to_extract is None
    
    def test_custom_config(self):
        """Test custom parser configuration."""
        custom_sections = {"5.2A": "Test section"}
        config = ParserConfig(
            pdf_start_page=50,
            pdf_x_tolerance=3,
            pdf_y_tolerance=3,
            sections_to_extract=custom_sections
        )
        
        assert config.pdf_start_page == 50
        assert config.pdf_x_tolerance == 3
        assert config.pdf_y_tolerance == 3
        assert config.sections_to_extract == custom_sections
    
    def test_invalid_start_page(self):
        """Test validation fails for invalid start page."""
        with pytest.raises(ValidationError):
            ParserConfig(pdf_start_page=0)
        
        with pytest.raises(ValidationError):
            ParserConfig(pdf_start_page=-1)
    
    def test_invalid_tolerance_values(self):
        """Test validation fails for invalid tolerance values."""
        with pytest.raises(ValidationError):
            ParserConfig(pdf_x_tolerance=-1)
        
        with pytest.raises(ValidationError):
            ParserConfig(pdf_y_tolerance=-1)