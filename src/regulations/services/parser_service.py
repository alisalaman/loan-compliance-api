import logging
from datetime import datetime
from pathlib import Path

from ..models import ParsedDocument, ParserConfig
from ..parsers.factory import ParserFactory

logger = logging.getLogger(__name__)


class RegulationParserService:
    """Service layer for regulation parsing operations."""

    def __init__(self, config: ParserConfig | None = None):
        """Initialize the parser service with optional configuration.

        Args:
            config: Optional parser configuration
        """
        self.config = config or ParserConfig.default()
        self._parse_history: list[dict] = []

    def parse_document(
        self,
        jurisdiction: str,
        document_type: str | None = None,
    ) -> ParsedDocument:
        """Parse a regulation document.

        Args:
            jurisdiction: Jurisdiction identifier (e.g., 'uk', 'eu', 'us')
            document_type: Optional document type identifier (e.g., 'FCA_CONC').
                          If not provided, uses the first available parser for the jurisdiction.

        Returns:
            ParsedDocument: Structured representation of the parsed document

        Raises:
            ValueError: If no suitable parser is found
            RuntimeError: If parsing fails
        """
        start_time = datetime.now()

        try:
            # Determine document type if not provided
            if document_type is None:
                available_types = ParserFactory.get_supported_types_for_jurisdiction(
                    jurisdiction
                )
                if not available_types:
                    raise ValueError(
                        f"No parsers available for jurisdiction: {jurisdiction}"
                    )
                document_type = available_types[0]  # Use first available
                logger.info(
                    f"Auto-selected document type: {document_type} for jurisdiction: {jurisdiction}"
                )

            # Create parser for the specified jurisdiction and document type
            parser = ParserFactory.create_parser(
                jurisdiction, document_type, self.config
            )
            detected_jurisdiction = jurisdiction
            detected_document_type = document_type
            logger.info(f"Using parser: {jurisdiction}:{document_type}")

            # Get the file path from the parser configuration
            file_path = parser.get_file_path()

            # Validate file exists
            if not file_path.exists():
                raise FileNotFoundError(f"Regulation file not found: {file_path}")

            # Parse the document
            logger.info(f"Starting parse of {file_path}")
            result = parser.parse()

            end_time = datetime.now()
            parse_duration = (end_time - start_time).total_seconds()

            # Log the parsing operation
            self._log_parse_operation(
                {
                    "file_path": str(file_path),
                    "jurisdiction": detected_jurisdiction,
                    "document_type": detected_document_type,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_seconds": parse_duration,
                    "clauses_extracted": result.clause_count,
                    "success": True,
                }
            )

            logger.info(
                f"Successfully parsed {file_path}: {result.clause_count} clauses in {parse_duration:.2f}s"
            )

            return result

        except Exception as e:
            end_time = datetime.now()
            parse_duration = (end_time - start_time).total_seconds()

            # Try to get file path if available, otherwise use placeholder
            try:
                file_path_str = (
                    str(parser.get_file_path()) if "parser" in locals() else "unknown"
                )
            except Exception:
                file_path_str = "unknown"

            # Log the failed operation
            self._log_parse_operation(
                {
                    "file_path": file_path_str,
                    "jurisdiction": jurisdiction,
                    "document_type": document_type,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_seconds": parse_duration,
                    "success": False,
                    "error": str(e),
                }
            )

            logger.error(
                f"Failed to parse document for {jurisdiction}:{document_type}: {str(e)}"
            )
            raise RuntimeError(
                f"Failed to parse document for {jurisdiction}:{document_type}: {str(e)}"
            ) from e

    def get_supported_formats(self) -> dict[str, list[str]]:
        """Get list of supported document formats organized by jurisdiction.

        Returns:
            Dictionary mapping jurisdictions to their supported document types
        """
        return ParserFactory.get_all_supported_combinations()

    def get_supported_jurisdictions(self) -> list[str]:
        """Get list of supported jurisdictions.

        Returns:
            List of supported jurisdiction identifiers
        """
        return ParserFactory.get_supported_jurisdictions()

    def get_supported_types_for_jurisdiction(self, jurisdiction: str) -> list[str]:
        """Get supported document types for a specific jurisdiction.

        Args:
            jurisdiction: The jurisdiction to query

        Returns:
            List of supported document types
        """
        return ParserFactory.get_supported_types_for_jurisdiction(jurisdiction)

    def validate_document(
        self,
        file_path: Path,
        jurisdiction: str | None = None,
        document_type: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Validate if a document can be parsed.

        Args:
            file_path: Path to the document to validate
            jurisdiction: Optional jurisdiction hint
            document_type: Optional document type hint

        Returns:
            Tuple of (is_valid, detected_jurisdiction, detected_document_type)
        """
        try:
            if jurisdiction and document_type:
                parser = ParserFactory.create_parser(
                    jurisdiction, document_type, self.config
                )
                is_valid = parser.validate_document(file_path)
                return (
                    is_valid,
                    jurisdiction if is_valid else None,
                    document_type if is_valid else None,
                )
            else:
                parser, detected_jurisdiction, detected_document_type = (
                    ParserFactory.get_parser_for_file(
                        file_path, jurisdiction, self.config
                    )
                )
                return True, detected_jurisdiction, detected_document_type
        except Exception:
            return False, None, None

    def get_parser_info(self) -> dict:
        """Get information about all available parsers.

        Returns:
            Dictionary containing parser information organized by jurisdiction
        """
        return ParserFactory.get_parser_info()

    def get_parse_history(self, limit: int | None = None) -> list[dict]:
        """Get history of parsing operations.

        Args:
            limit: Optional limit on number of records to return

        Returns:
            List of parsing operation records
        """
        history = self._parse_history.copy()
        if limit:
            history = history[-limit:]
        return history

    def clear_parse_history(self) -> None:
        """Clear the parsing operation history."""
        self._parse_history.clear()
        logger.info("Parse history cleared")

    def _log_parse_operation(self, operation_info: dict) -> None:
        """Log a parsing operation to the internal history.

        Args:
            operation_info: Dictionary containing operation details
        """
        self._parse_history.append(operation_info)

        # Keep only last 1000 operations to prevent memory bloat
        if len(self._parse_history) > 1000:
            self._parse_history = self._parse_history[-1000:]
