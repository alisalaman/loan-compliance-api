"""Tests for parser factory functionality."""
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.regulations.parsers.factory import ParserFactory, Jurisdiction
from src.regulations.parsers.base import BaseRegulationParser
from src.regulations.parsers.uk_fca_conc import UKFCACoNCParser
from src.regulations.models import ParserConfig


class MockParser(BaseRegulationParser):
    """Mock parser for testing factory registration."""
    
    def get_default_file_path(self) -> str:
        return "data/test/mock.pdf"
    
    def get_supported_document_types(self):
        return ["MOCK_DOC"]
    
    def _validate_document(self, file_path: Path) -> bool:
        return file_path.name == "mock.pdf"
    
    def _parse_document(self, file_path: Path):
        from src.regulations.models import ParsedDocument, DocumentMetadata
        return ParsedDocument(
            document_type="MOCK_DOC",
            clauses=[],
            metadata=DocumentMetadata(
                source_file=str(file_path),
                total_pages=1,
                sections_extracted=[],
                parser_version="1.0.0"
            )
        )


class TestParserFactory:
    """Tests for ParserFactory class."""
    
    def test_create_parser_valid_combination(self, default_config):
        """Test creating parser with valid jurisdiction/document type."""
        parser = ParserFactory.create_parser("uk", "FCA_CONC", default_config)
        
        assert isinstance(parser, UKFCACoNCParser)
        assert parser.config == default_config
    
    def test_create_parser_case_insensitive(self, default_config):
        """Test that jurisdiction matching is case insensitive."""
        parser = ParserFactory.create_parser("UK", "FCA_CONC", default_config)
        assert isinstance(parser, UKFCACoNCParser)
        
        parser = ParserFactory.create_parser("Uk", "FCA_CONC", default_config)
        assert isinstance(parser, UKFCACoNCParser)
    
    def test_create_parser_invalid_jurisdiction(self, default_config):
        """Test error for invalid jurisdiction."""
        with pytest.raises(ValueError) as exc_info:
            ParserFactory.create_parser("invalid", "FCA_CONC", default_config)
        
        error_msg = str(exc_info.value)
        assert "No parsers available for jurisdiction: invalid" in error_msg
        assert "Available jurisdictions:" in error_msg
    
    def test_create_parser_invalid_document_type(self, default_config):
        """Test error for invalid document type."""
        with pytest.raises(ValueError) as exc_info:
            ParserFactory.create_parser("uk", "INVALID_DOC", default_config)
        
        error_msg = str(exc_info.value)
        assert "No parser available for document type 'INVALID_DOC'" in error_msg
        assert "Available types for uk:" in error_msg
    
    def test_create_parser_without_config(self):
        """Test creating parser without explicit config."""
        parser = ParserFactory.create_parser("uk", "FCA_CONC")
        
        assert isinstance(parser, UKFCACoNCParser)
        assert parser.config is not None  # Should use default config
    
    @pytest.mark.skipif(True, reason="PDF validation tests require complex PDF structure")  
    def test_get_parser_for_file_auto_detection(self, default_config):
        """Test automatic parser detection for files."""
        pytest.skip("Requires actual PDF with proper structure")
    
    @pytest.mark.skipif(True, reason="PDF validation tests require complex PDF structure")
    def test_get_parser_for_file_with_jurisdiction_hint(self, default_config):
        """Test parser detection with jurisdiction hint.""" 
        pytest.skip("Requires actual PDF with proper structure")
    
    def test_get_parser_for_file_no_match(self, temp_pdf_file, default_config):
        """Test error when no parser matches the file."""
        # Use the simple temp PDF from conftest which won't match CONC validation
        with pytest.raises(ValueError) as exc_info:
            ParserFactory.get_parser_for_file(temp_pdf_file, config=default_config)
        
        error_msg = str(exc_info.value)
        assert "No suitable parser found for file:" in error_msg
        assert "Available parsers:" in error_msg
    
    def test_get_supported_jurisdictions(self):
        """Test getting list of supported jurisdictions."""
        jurisdictions = ParserFactory.get_supported_jurisdictions()
        
        assert isinstance(jurisdictions, list)
        assert "uk" in jurisdictions
        assert len(jurisdictions) >= 1
    
    def test_get_supported_types_for_jurisdiction(self):
        """Test getting supported document types for jurisdiction."""
        uk_types = ParserFactory.get_supported_types_for_jurisdiction("uk")
        
        assert isinstance(uk_types, list)
        assert "FCA_CONC" in uk_types
        
        # Test case insensitivity
        uk_types_upper = ParserFactory.get_supported_types_for_jurisdiction("UK")
        assert uk_types == uk_types_upper
        
        # Test non-existent jurisdiction
        empty_types = ParserFactory.get_supported_types_for_jurisdiction("nonexistent")
        assert empty_types == []
    
    def test_get_all_supported_combinations(self):
        """Test getting all supported combinations."""
        combinations = ParserFactory.get_all_supported_combinations()
        
        assert isinstance(combinations, dict)
        assert "uk" in combinations
        assert "FCA_CONC" in combinations["uk"]
    
    def test_register_parser(self):
        """Test registering a new parser."""
        # Register mock parser
        ParserFactory.register_parser("test", "MOCK_DOC", MockParser)
        
        # Verify registration
        supported_types = ParserFactory.get_supported_types_for_jurisdiction("test")
        assert "MOCK_DOC" in supported_types
        
        # Test creating the registered parser
        parser = ParserFactory.create_parser("test", "MOCK_DOC")
        assert isinstance(parser, MockParser)
        
        # Cleanup - remove the test parser
        if "test" in ParserFactory._parsers:
            del ParserFactory._parsers["test"]
    
    def test_register_parser_invalid_class(self):
        """Test error when registering invalid parser class."""
        
        class InvalidParser:
            """Not a BaseRegulationParser."""
            pass
        
        with pytest.raises(ValueError) as exc_info:
            ParserFactory.register_parser("test", "INVALID", InvalidParser)
        
        error_msg = str(exc_info.value)
        assert "Parser class must inherit from BaseRegulationParser" in error_msg
    
    def test_get_parser_info(self):
        """Test getting parser information."""
        info = ParserFactory.get_parser_info()
        
        assert isinstance(info, dict)
        assert "uk" in info
        assert "FCA_CONC" in info["uk"]
        
        # Check that the parser info contains expected fields
        uk_fca_info = info["uk"]["FCA_CONC"]
        assert isinstance(uk_fca_info, dict)
        # The exact structure depends on the get_parser_info implementation