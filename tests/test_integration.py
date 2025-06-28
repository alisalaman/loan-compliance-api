"""Integration tests for the complete parsing pipeline."""
import pytest
from pathlib import Path

from src.regulations.services.parser_service import RegulationParserService
from src.regulations.parsers.factory import ParserFactory
from src.regulations.models import ParserConfig, ClauseType


class TestIntegration:
    """Integration tests for the complete regulation parsing system."""
    
    @pytest.fixture
    def service(self):
        """Service instance for integration testing."""
        return RegulationParserService()
    
    @pytest.fixture
    def custom_service(self):
        """Service with custom configuration."""
        config = ParserConfig(
            pdf_start_page=35,  # Different start page
            sections_to_extract={"7": "Arrears, default and recovery"}  # Only section 7
        )
        return RegulationParserService(config)
    
    @pytest.mark.skipif(
        not Path("data/regulations/uk/fca/CONC.pdf").exists(),
        reason="CONC.pdf not available for integration testing"
    )
    def test_end_to_end_conc_parsing(self, service):
        """Test complete end-to-end parsing of actual CONC document."""
        conc_path = Path("data/regulations/uk/fca/CONC.pdf")
        
        # Test auto-detection - jurisdiction is required, document type is auto-selected
        result = service.parse_document(jurisdiction="uk")
        
        # Verify document structure
        assert result.document_type == "UK_FCA_CONC"
        assert result.clause_count > 0
        assert len(result.clauses) > 100  # Should extract many clauses
        
        # Verify metadata
        assert "CONC.pdf" in result.metadata.source_file
        assert result.metadata.total_pages > 0
        assert "5.2A" in result.metadata.sections_extracted
        assert "2.10" in result.metadata.sections_extracted
        assert "7" in result.metadata.sections_extracted
        
        # Verify clause structure
        sample_clause = result.clauses[0]
        assert sample_clause.section is not None
        assert sample_clause.clause_id is not None
        assert sample_clause.content is not None
        assert sample_clause.page_number > 0
        assert sample_clause.clause_type in [ClauseType.RULE, ClauseType.GUIDANCE, ClauseType.UNKNOWN]
        
        # Verify we have clauses from different sections
        sections = {clause.section for clause in result.clauses}
        assert len(sections) > 1
        
        # Check parse history
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["success"] is True
        assert history[0]["clauses_extracted"] == result.clause_count
    
    @pytest.mark.skipif(
        not Path("data/regulations/uk/fca/CONC.pdf").exists(),
        reason="CONC.pdf not available for integration testing"
    )
    def test_end_to_end_with_explicit_params(self, service):
        """Test parsing with explicit jurisdiction and document type."""
        # Test with explicit parameters
        result = service.parse_document(
            jurisdiction="uk", 
            document_type="FCA_CONC"
        )
        
        assert result.document_type == "UK_FCA_CONC"
        assert result.clause_count > 0
        
        # Check history shows explicit parameters
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["jurisdiction"] == "uk"
        assert history[0]["document_type"] == "FCA_CONC"
    
    @pytest.mark.skipif(
        not Path("data/regulations/uk/fca/CONC.pdf").exists(),
        reason="CONC.pdf not available for integration testing"
    )
    def test_custom_configuration(self, custom_service):
        """Test parsing with custom configuration."""
        result = custom_service.parse_document(jurisdiction="uk")
        
        # Should only extract section 7 due to custom config
        assert result.metadata.sections_extracted == ["7"]
        
        # All clauses should be from section 7
        for clause in result.clauses:
            assert clause.section.startswith("7")
    
    def test_service_factory_integration(self, service):
        """Test integration between service and factory layers."""
        # Test getting supported combinations
        formats = service.get_supported_formats()
        assert isinstance(formats, dict)
        assert "uk" in formats
        assert "FCA_CONC" in formats["uk"]
        
        # Test getting jurisdictions
        jurisdictions = service.get_supported_jurisdictions()
        assert "uk" in jurisdictions
        
        # Test getting types for jurisdiction
        uk_types = service.get_supported_types_for_jurisdiction("uk")
        assert "FCA_CONC" in uk_types
        
        # Test parser info
        parser_info = service.get_parser_info()
        assert "uk" in parser_info
        assert "FCA_CONC" in parser_info["uk"]
    
    def test_validation_integration(self, service, temp_pdf_file):
        """Test document validation integration."""
        # Test validation of temp PDF (should be valid for CONC parser)
        is_valid, jurisdiction, doc_type = service.validate_document(temp_pdf_file)
        
        # Depending on the temp_pdf_file content, this might be valid or invalid
        assert isinstance(is_valid, bool)
        if is_valid:
            assert jurisdiction is not None
            assert doc_type is not None
        else:
            assert jurisdiction is None
            assert doc_type is None
    
    def test_error_handling_integration(self, service):
        """Test error handling across the complete pipeline."""
        # Test with invalid jurisdiction
        with pytest.raises(RuntimeError) as exc_info:
            service.parse_document(jurisdiction="invalid")
        
        assert "Failed to parse document" in str(exc_info.value)
        assert "No parsers available for jurisdiction: invalid" in str(exc_info.value)
        
        # Check error was logged
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["success"] is False
        
        # Test with invalid jurisdiction/type combination
        with pytest.raises(RuntimeError) as exc_info:
            service.parse_document(
                jurisdiction="uk",
                document_type="INVALID"
            )
        
        assert "Failed to parse document" in str(exc_info.value)
    
    def test_factory_registration_integration(self):
        """Test that factory registration works with service layer."""
        from src.regulations.parsers.base import BaseRegulationParser
        from src.regulations.models import ParsedDocument, DocumentMetadata
        
        class TestParser(BaseRegulationParser):
            def get_default_file_path(self):
                return "data/test/test.pdf"
                
            def get_supported_document_types(self):
                return ["TEST_DOC"]
            
            def _validate_document(self, file_path):
                return file_path.name == "test.pdf"
            
            def _parse_document(self, file_path):
                return ParsedDocument(
                    document_type="TEST_DOC",
                    clauses=[],
                    metadata=DocumentMetadata(
                        source_file=str(file_path),
                        total_pages=1,
                        sections_extracted=[],
                        parser_version="1.0.0"
                    )
                )
        
        # Register test parser
        ParserFactory.register_parser("test", "TEST_DOC", TestParser)
        
        try:
            # Test through service
            service = RegulationParserService()
            
            # Should be able to create parser
            parser = ParserFactory.create_parser("test", "TEST_DOC")
            assert isinstance(parser, TestParser)
            
            # Should appear in supported formats
            formats = service.get_supported_formats()
            assert "test" in formats
            assert "TEST_DOC" in formats["test"]
            
        finally:
            # Cleanup - remove test parser
            if "test" in ParserFactory._parsers:
                del ParserFactory._parsers["test"]
    
    def test_multiple_parsing_operations(self, service, temp_pdf_file):
        """Test multiple parsing operations and history tracking."""
        # Perform multiple validation operations (less likely to fail)
        for i in range(3):
            try:
                service.validate_document(temp_pdf_file)
            except Exception:
                pass  # Ignore validation failures for this test
        
        # History should track all operations that actually executed
        # Note: validate_document doesn't add to history, so we test parse operations
        history_before = len(service.get_parse_history())
        
        # Try parsing operations (these will be logged even if they fail)
        for i in range(2):
            try:
                service.parse_document(jurisdiction="uk", document_type="FCA_CONC")
            except Exception:
                pass  # Expected to fail, but should still log
        
        # Should have 2 more history entries
        history_after = service.get_parse_history()
        assert len(history_after) == history_before + 2
        
        # Test history management
        limited_history = service.get_parse_history(limit=1)
        assert len(limited_history) == 1
        
        service.clear_parse_history()
        assert len(service.get_parse_history()) == 0