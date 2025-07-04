"""Tests for regulation parser service layer."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.regulations.models import (
    DocumentMetadata,
    ParsedDocument,
    ParserConfig,
    RegulationClause,
)
from src.regulations.services.parser_service import RegulationParserService


class TestRegulationParserService:
    """Tests for RegulationParserService class."""

    @pytest.fixture
    def service(self, default_config):
        """Create a service instance for testing."""
        return RegulationParserService(default_config)

    @pytest.fixture
    def service_no_config(self):
        """Create a service instance without config."""
        return RegulationParserService()

    @pytest.fixture
    def mock_parsed_document(self):
        """Mock parsed document for testing."""
        return ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=[
                RegulationClause(
                    section="7.1",
                    clause_id="7.1.1 R",
                    content="Test clause content",
                    page_number=156,
                )
            ],
            metadata=DocumentMetadata(
                source_file="/test/path.pdf",
                total_pages=200,
                sections_extracted=["7"],
                parser_version="1.0.0",
            ),
        )

    def test_service_initialization_with_config(self, default_config):
        """Test service initialization with config."""
        service = RegulationParserService(default_config)

        assert service.config == default_config
        assert isinstance(service._parse_history, list)
        assert len(service._parse_history) == 0

    def test_service_initialization_without_config(self):
        """Test service initialization without config uses defaults."""
        service = RegulationParserService()

        assert service.config is not None
        assert isinstance(service.config, ParserConfig)

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_document_with_explicit_params(
        self, mock_create_parser, service, temp_pdf_file, mock_parsed_document
    ):
        """Test parsing document with explicit jurisdiction and document type."""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed_document
        mock_parser.get_file_path.return_value = temp_pdf_file
        mock_create_parser.return_value = mock_parser

        result = service.parse_document(jurisdiction="uk", document_type="FCA_CONC")

        assert result == mock_parsed_document
        mock_create_parser.assert_called_once_with("uk", "FCA_CONC", service.config)
        mock_parser.parse.assert_called_once()

        # Check that operation was logged
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["success"] is True
        assert history[0]["jurisdiction"] == "uk"
        assert history[0]["document_type"] == "FCA_CONC"

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_types_for_jurisdiction"
    )
    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_all_documents_for_jurisdiction(
        self,
        mock_create_parser,
        mock_get_types,
        service,
        temp_pdf_file,
        mock_parsed_document,
    ):
        """Test parsing all document types for a jurisdiction when document_type is None."""
        # Setup mock for multiple document types
        mock_get_types.return_value = ["FCA_CONC", "FCA_FG21"]

        # Create different mock documents for each type
        mock_conc_doc = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=[],
            metadata=DocumentMetadata(
                source_file="/test/conc.pdf",
                total_pages=100,
                sections_extracted=["5"],
                parser_version="1.0.0",
            ),
        )

        mock_fg21_doc = ParsedDocument(
            document_type="UK_FCA_FG21",
            clauses=[],
            metadata=DocumentMetadata(
                source_file="/test/fg21.pdf",
                total_pages=50,
                sections_extracted=["1", "2"],
                parser_version="1.0.0",
            ),
        )

        # Setup parsers to return different documents
        mock_parser_conc = MagicMock()
        mock_parser_conc.parse.return_value = mock_conc_doc
        mock_parser_conc.get_file_path.return_value = temp_pdf_file

        mock_parser_fg21 = MagicMock()
        mock_parser_fg21.parse.return_value = mock_fg21_doc
        mock_parser_fg21.get_file_path.return_value = temp_pdf_file

        # Configure create_parser to return different parsers for different document types
        def create_parser_side_effect(jurisdiction, doc_type, config):
            if doc_type == "FCA_CONC":
                return mock_parser_conc
            elif doc_type == "FCA_FG21":
                return mock_parser_fg21
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

        mock_create_parser.side_effect = create_parser_side_effect

        # Call parse_document with document_type=None
        result = service.parse_document(jurisdiction="uk", document_type=None)

        # Should return dict of parsed documents
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "FCA_CONC" in result
        assert "FCA_FG21" in result
        assert result["FCA_CONC"] == mock_conc_doc
        assert result["FCA_FG21"] == mock_fg21_doc

        # Check that both parsers were created and called
        assert mock_create_parser.call_count == 2
        mock_parser_conc.parse.assert_called_once()
        mock_parser_fg21.parse.assert_called_once()

        # Check that operations were logged
        history = service.get_parse_history()
        assert len(history) == 3  # 2 individual parses + 1 summary

        # Check summary operation
        summary_op = history[-1]
        assert summary_op["jurisdiction"] == "uk"
        assert summary_op["document_type"] == "ALL"
        assert summary_op["success"] is True
        assert summary_op["total_successful"] == 2
        assert summary_op["total_failed"] == 0

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_types_for_jurisdiction"
    )
    def test_parse_all_documents_no_parsers_available(self, mock_get_types, service):
        """Test parsing all documents when no parsers are available for jurisdiction."""
        mock_get_types.return_value = []

        with pytest.raises(ValueError) as exc_info:
            service.parse_document(jurisdiction="unknown")

        assert "No parsers available for jurisdiction: unknown" in str(exc_info.value)

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_types_for_jurisdiction"
    )
    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_all_documents_partial_failure(
        self, mock_create_parser, mock_get_types, service, temp_pdf_file
    ):
        """Test parsing all documents when some parsers fail."""
        mock_get_types.return_value = ["FCA_CONC", "FCA_FG21", "FCA_PRIN"]

        # Create successful parser for FCA_CONC
        mock_conc_doc = ParsedDocument(
            document_type="UK_FCA_CONC",
            clauses=[],
            metadata=DocumentMetadata(
                source_file="/test/conc.pdf",
                total_pages=100,
                sections_extracted=["5"],
                parser_version="1.0.0",
            ),
        )
        mock_parser_conc = MagicMock()
        mock_parser_conc.parse.return_value = mock_conc_doc
        mock_parser_conc.get_file_path.return_value = temp_pdf_file

        # Create failing parser for FCA_FG21
        mock_parser_fg21 = MagicMock()
        mock_parser_fg21.get_file_path.return_value = Path("/nonexistent.pdf")

        # Create parser that throws exception for FCA_PRIN
        mock_parser_prin = MagicMock()
        mock_parser_prin.parse.side_effect = ValueError("Parser error")
        mock_parser_prin.get_file_path.return_value = temp_pdf_file

        def create_parser_side_effect(jurisdiction, doc_type, config):
            if doc_type == "FCA_CONC":
                return mock_parser_conc
            elif doc_type == "FCA_FG21":
                return mock_parser_fg21
            elif doc_type == "FCA_PRIN":
                return mock_parser_prin
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

        mock_create_parser.side_effect = create_parser_side_effect

        # Should succeed with partial results
        result = service.parse_document(jurisdiction="uk", document_type=None)

        # Should return only successful parse
        assert isinstance(result, dict)
        assert len(result) == 1
        assert "FCA_CONC" in result
        assert result["FCA_CONC"] == mock_conc_doc

        # Check summary operation logs partial success
        history = service.get_parse_history()
        summary_op = history[-1]
        assert summary_op["success"] is True  # At least one succeeded
        assert summary_op["total_successful"] == 1
        assert summary_op["total_failed"] == 2

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_types_for_jurisdiction"
    )
    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_all_documents_complete_failure(
        self, mock_create_parser, mock_get_types, service
    ):
        """Test parsing all documents when all parsers fail."""
        mock_get_types.return_value = ["FCA_CONC", "FCA_FG21"]

        # Both parsers fail
        mock_parser_conc = MagicMock()
        mock_parser_conc.get_file_path.return_value = Path("/nonexistent1.pdf")

        mock_parser_fg21 = MagicMock()
        mock_parser_fg21.get_file_path.return_value = Path("/nonexistent2.pdf")

        def create_parser_side_effect(jurisdiction, doc_type, config):
            if doc_type == "FCA_CONC":
                return mock_parser_conc
            elif doc_type == "FCA_FG21":
                return mock_parser_fg21
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

        mock_create_parser.side_effect = create_parser_side_effect

        with pytest.raises(RuntimeError) as exc_info:
            service.parse_document(jurisdiction="uk", document_type=None)

        assert "Failed to parse any documents for jurisdiction 'uk'" in str(
            exc_info.value
        )

        # Check summary operation logs complete failure
        history = service.get_parse_history()
        summary_op = history[-1]
        assert summary_op["success"] is False
        assert summary_op["total_successful"] == 0
        assert summary_op["total_failed"] == 2

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_document_file_not_found(self, mock_create_parser, service):
        """Test parsing when file doesn't exist raises error."""
        non_existent = Path("/path/that/does/not/exist.pdf")
        mock_parser = MagicMock()
        mock_parser.get_file_path.return_value = non_existent
        mock_create_parser.return_value = mock_parser

        with pytest.raises(RuntimeError) as exc_info:
            service.parse_document(jurisdiction="uk", document_type="FCA_CONC")

        assert "Failed to parse document" in str(exc_info.value)
        assert "Regulation file not found" in str(exc_info.value)

        # Check that failed operation was logged
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["success"] is False

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_document_parser_error(
        self, mock_create_parser, service, temp_pdf_file
    ):
        """Test parsing when parser raises error."""
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = ValueError("Parser error")
        mock_parser.get_file_path.return_value = temp_pdf_file
        mock_create_parser.return_value = mock_parser

        with pytest.raises(RuntimeError) as exc_info:
            service.parse_document(jurisdiction="uk", document_type="FCA_CONC")

        assert "Failed to parse document" in str(exc_info.value)

        # Check that failed operation was logged
        history = service.get_parse_history()
        assert len(history) == 1
        assert history[0]["success"] is False
        assert "Parser error" in history[0]["error"]

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_all_supported_combinations"
    )
    def test_get_supported_formats(self, mock_get_combinations, service):
        """Test getting supported formats."""
        expected_formats = {"uk": ["FCA_CONC"], "eu": ["EBA_GL"]}
        mock_get_combinations.return_value = expected_formats

        result = service.get_supported_formats()

        assert result == expected_formats
        mock_get_combinations.assert_called_once()

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_jurisdictions"
    )
    def test_get_supported_jurisdictions(self, mock_get_jurisdictions, service):
        """Test getting supported jurisdictions."""
        expected_jurisdictions = ["uk", "eu", "us"]
        mock_get_jurisdictions.return_value = expected_jurisdictions

        result = service.get_supported_jurisdictions()

        assert result == expected_jurisdictions
        mock_get_jurisdictions.assert_called_once()

    @patch(
        "src.regulations.services.parser_service.ParserFactory.get_supported_types_for_jurisdiction"
    )
    def test_get_supported_types_for_jurisdiction(self, mock_get_types, service):
        """Test getting supported types for jurisdiction."""
        expected_types = ["FCA_CONC", "FCA_PRIN"]
        mock_get_types.return_value = expected_types

        result = service.get_supported_types_for_jurisdiction("uk")

        assert result == expected_types
        mock_get_types.assert_called_once_with("uk")

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_validate_document_with_params(
        self, mock_create_parser, service, temp_pdf_file
    ):
        """Test document validation with explicit parameters."""
        mock_parser = MagicMock()
        mock_parser.validate_document.return_value = True
        mock_create_parser.return_value = mock_parser

        is_valid, jurisdiction, doc_type = service.validate_document(
            temp_pdf_file, jurisdiction="uk", document_type="FCA_CONC"
        )

        assert is_valid is True
        assert jurisdiction == "uk"
        assert doc_type == "FCA_CONC"
        mock_create_parser.assert_called_once_with("uk", "FCA_CONC", service.config)
        mock_parser.validate_document.assert_called_once_with(temp_pdf_file)

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_validate_document_invalid(
        self, mock_create_parser, service, temp_pdf_file
    ):
        """Test document validation returns false for invalid document."""
        mock_parser = MagicMock()
        mock_parser.validate_document.return_value = False
        mock_create_parser.return_value = mock_parser

        is_valid, jurisdiction, doc_type = service.validate_document(
            temp_pdf_file, jurisdiction="uk", document_type="FCA_CONC"
        )

        assert is_valid is False
        assert jurisdiction is None
        assert doc_type is None

    @patch("src.regulations.services.parser_service.ParserFactory.get_parser_for_file")
    def test_validate_document_with_auto_detection(
        self, mock_get_parser, service, temp_pdf_file
    ):
        """Test document validation with auto-detection."""
        mock_parser = MagicMock()
        mock_get_parser.return_value = (mock_parser, "uk", "FCA_CONC")

        is_valid, jurisdiction, doc_type = service.validate_document(temp_pdf_file)

        assert is_valid is True
        assert jurisdiction == "uk"
        assert doc_type == "FCA_CONC"
        mock_get_parser.assert_called_once_with(temp_pdf_file, None, service.config)

    def test_validate_document_exception(self, service, temp_pdf_file):
        """Test document validation handles exceptions."""
        with patch(
            "src.regulations.services.parser_service.ParserFactory.create_parser"
        ) as mock_create:
            mock_create.side_effect = ValueError("Test error")

            is_valid, jurisdiction, doc_type = service.validate_document(
                temp_pdf_file, jurisdiction="uk", document_type="FCA_CONC"
            )

            assert is_valid is False
            assert jurisdiction is None
            assert doc_type is None

    @patch("src.regulations.services.parser_service.ParserFactory.get_parser_info")
    def test_get_parser_info(self, mock_get_info, service):
        """Test getting parser information."""
        expected_info = {"uk": {"FCA_CONC": {"version": "1.0.0"}}}
        mock_get_info.return_value = expected_info

        result = service.get_parser_info()

        assert result == expected_info
        mock_get_info.assert_called_once()

    def test_parse_history_management(self, service):
        """Test parse history management functions."""
        # Initially empty
        assert len(service.get_parse_history()) == 0

        # Add some history manually for testing
        service._log_parse_operation(
            {"file_path": "/test1.pdf", "success": True, "duration_seconds": 1.5}
        )
        service._log_parse_operation(
            {"file_path": "/test2.pdf", "success": False, "error": "Test error"}
        )

        # Check history
        history = service.get_parse_history()
        assert len(history) == 2
        assert history[0]["file_path"] == "/test1.pdf"
        assert history[1]["file_path"] == "/test2.pdf"

        # Test with limit
        limited_history = service.get_parse_history(limit=1)
        assert len(limited_history) == 1
        assert limited_history[0]["file_path"] == "/test2.pdf"  # Should be most recent

        # Clear history
        service.clear_parse_history()
        assert len(service.get_parse_history()) == 0

    def test_parse_history_size_limit(self, service):
        """Test that parse history maintains size limit."""
        # Add more than 1000 operations
        for i in range(1050):
            service._log_parse_operation(
                {"file_path": f"/test{i}.pdf", "success": True, "operation_id": i}
            )

        # Should only keep last 1000
        history = service.get_parse_history()
        assert len(history) == 1000
        assert history[0]["operation_id"] == 50  # First kept operation
        assert history[-1]["operation_id"] == 1049  # Last operation

    @patch("src.regulations.services.parser_service.ParserFactory.create_parser")
    def test_parse_timing_measurement(
        self, mock_create_parser, service, temp_pdf_file, mock_parsed_document
    ):
        """Test that parsing timing is properly measured."""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed_document
        mock_parser.get_file_path.return_value = temp_pdf_file
        mock_create_parser.return_value = mock_parser

        # Mock time to control duration
        with patch("src.regulations.services.parser_service.datetime") as mock_datetime:
            start_time = datetime(2023, 1, 1, 12, 0, 0)
            end_time = datetime(2023, 1, 1, 12, 0, 2)  # 2 seconds later
            mock_datetime.now.side_effect = [start_time, end_time]

            service.parse_document(jurisdiction="uk", document_type="FCA_CONC")

            history = service.get_parse_history()
            assert len(history) == 1
            assert history[0]["duration_seconds"] == 2.0
            assert history[0]["start_time"] == start_time
            assert history[0]["end_time"] == end_time
