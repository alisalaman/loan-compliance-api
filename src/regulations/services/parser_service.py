import logging
from datetime import datetime
from pathlib import Path

from regulations.models import ParsedDocument, ParserConfig
from regulations.parsers.factory import ParserFactory

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
    ) -> ParsedDocument | dict[str, ParsedDocument]:
        """Parse a regulation document.

        Args:
            jurisdiction: Jurisdiction identifier (e.g., 'uk', 'eu', 'us')
            document_type: Optional document type identifier (e.g., 'FCA_CONC').
                          If not provided, parses all available document types for the jurisdiction.

        Returns:
            ParsedDocument: If document_type is specified, returns a single parsed document
            dict[str, ParsedDocument]: If document_type is None, returns dict mapping document types to parsed documents

        Raises:
            ValueError: If no suitable parser is found
            RuntimeError: If parsing fails
        """
        # If document_type is None, parse all document types for the jurisdiction
        if document_type is None:
            return self._parse_all_documents_for_jurisdiction(jurisdiction)

        # Original single document parsing logic
        return self._parse_single_document(jurisdiction, document_type)

    def _parse_single_document(
        self,
        jurisdiction: str,
        document_type: str,
    ) -> ParsedDocument:
        """Parse a single regulation document.

        Args:
            jurisdiction: Jurisdiction identifier (e.g., 'uk', 'eu', 'us')
            document_type: Document type identifier (e.g., 'FCA_CONC')

        Returns:
            ParsedDocument: Structured representation of the parsed document

        Raises:
            ValueError: If no suitable parser is found
            RuntimeError: If parsing fails
        """
        start_time = datetime.now()

        try:
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

    def _parse_all_documents_for_jurisdiction(
        self,
        jurisdiction: str,
    ) -> dict[str, ParsedDocument]:
        """Parse all available document types for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction identifier (e.g., 'uk', 'eu', 'us')

        Returns:
            Dictionary mapping document types to their parsed documents

        Raises:
            ValueError: If no parsers are available for the jurisdiction
            RuntimeError: If all parsing attempts fail
        """
        start_time = datetime.now()

        # Get all available document types for the jurisdiction
        available_types = ParserFactory.get_supported_types_for_jurisdiction(
            jurisdiction
        )
        if not available_types:
            raise ValueError(f"No parsers available for jurisdiction: {jurisdiction}")

        logger.info(
            f"Parsing all document types for jurisdiction '{jurisdiction}': {', '.join(available_types)}"
        )

        parsed_documents = {}
        failed_parsers = []
        successful_parsers = []

        # Parse each document type
        for document_type in available_types:
            try:
                logger.info(f"Parsing document type: {document_type}")
                parsed_doc = self._parse_single_document(jurisdiction, document_type)
                parsed_documents[document_type] = parsed_doc
                successful_parsers.append(document_type)
                logger.info(f"Successfully parsed {document_type}")
            except Exception as e:
                logger.warning(f"Failed to parse {document_type}: {str(e)}")
                failed_parsers.append((document_type, str(e)))

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # Log summary operation
        self._log_parse_operation(
            {
                "file_path": "multiple",
                "jurisdiction": jurisdiction,
                "document_type": "ALL",
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": total_duration,
                "success": len(successful_parsers) > 0,
                "successful_parsers": successful_parsers,
                "failed_parsers": [doc_type for doc_type, _ in failed_parsers],
                "total_attempted": len(available_types),
                "total_successful": len(successful_parsers),
                "total_failed": len(failed_parsers),
            }
        )

        if not parsed_documents:
            # All parsers failed
            error_details = "; ".join(
                [f"{doc_type}: {error}" for doc_type, error in failed_parsers]
            )
            raise RuntimeError(
                f"Failed to parse any documents for jurisdiction '{jurisdiction}'. "
                f"Errors: {error_details}"
            )

        logger.info(
            f"Completed parsing for jurisdiction '{jurisdiction}': "
            f"{len(successful_parsers)} successful, {len(failed_parsers)} failed "
            f"in {total_duration:.2f}s"
        )

        return parsed_documents

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
