from abc import ABC, abstractmethod
from pathlib import Path

from ..models import ParsedDocument, ParserConfig


class BaseRegulationParser(ABC):
    """Abstract base class for all regulation parsers."""

    def __init__(self, config: ParserConfig | None = None):
        """Initialize the parser with optional configuration."""
        self.config = config or ParserConfig.default()

    @abstractmethod
    def get_default_file_path(self) -> str:
        """Get the default file path for this parser's documents.

        Returns:
            Default file path for this parser's regulation documents
        """
        pass

    def get_file_path(self) -> Path:
        """Get the file path to parse (from config or default).

        Returns:
            Path to the document file
        """
        file_path = self.config.document_file_path or self.get_default_file_path()
        return Path(file_path)

    def parse(self, file_path: Path | None = None) -> ParsedDocument:
        """Parse a regulation document and return structured data.

        Args:
            file_path: Optional path to the document to parse. If not provided,
                      uses the configured or default path.

        Returns:
            ParsedDocument: Structured representation of the document

        Raises:
            ValueError: If the document is invalid or unsupported
            RuntimeError: If parsing fails
        """
        if file_path is None:
            file_path = self.get_file_path()
        return self._parse_document(file_path)

    @abstractmethod
    def _parse_document(self, file_path: Path) -> ParsedDocument:
        """Internal method to parse a specific document file.

        Args:
            file_path: Path to the document to parse

        Returns:
            ParsedDocument: Structured representation of the document
        """
        pass

    @abstractmethod
    def get_supported_document_types(self) -> list[str]:
        """Return list of document types this parser supports.

        Returns:
            List of supported document type identifiers
        """
        pass

    def validate_document(self, file_path: Path | None = None) -> bool:
        """Validate if this parser can handle the given document.

        Args:
            file_path: Optional path to the document to validate. If not provided,
                      uses the configured or default path.

        Returns:
            True if this parser can handle the document, False otherwise
        """
        if file_path is None:
            file_path = self.get_file_path()
        return self._validate_document(file_path)

    @abstractmethod
    def _validate_document(self, file_path: Path) -> bool:
        """Internal method to validate a specific document file.

        Args:
            file_path: Path to the document to validate

        Returns:
            True if this parser can handle the document, False otherwise
        """
        pass

    def get_parser_info(self) -> dict:
        """Get information about this parser.

        Returns:
            Dictionary containing parser metadata
        """
        return {
            "parser_class": self.__class__.__name__,
            "supported_types": self.get_supported_document_types(),
            "version": getattr(self, "VERSION", "unknown"),
        }
