from enum import Enum
from pathlib import Path

from ..models import ParserConfig
from .base import BaseRegulationParser
from regulations.parsers.uk.uk_fca_conc import UKFCACoNCParser
from regulations.parsers.uk.uk_fca_fg21 import UKFCAFg21Parser
from regulations.parsers.eu.eu_eba_gl_2020_06 import EUEBAGl202006Parser


class Jurisdiction(str, Enum):
    """Supported regulatory jurisdictions."""

    UK = "uk"
    EU = "eu"
    US = "us"
    CANADA = "canada"
    AUSTRALIA = "australia"


class ParserFactory:
    """Factory for creating appropriate regulation parsers based on jurisdiction and document type."""

    # Structure: {jurisdiction: {document_type: parser_class}}
    _parsers: dict[str, dict[str, type[BaseRegulationParser]]] = {
        Jurisdiction.UK: {
            "FCA_CONC": UKFCACoNCParser,
            "FCA_FG21": UKFCAFg21Parser,
            # "FCA_PRIN": UKFCAPrinciplesParser,
            # "PRA_CRR": UKPRACRRParser,
        },
        Jurisdiction.EU: {
            "EBA_GL_2020_06": EUEBAGl202006Parser,
            # "ECB_REG": ECBRegulationParser,
        },
        # Future jurisdictions:
        # Jurisdiction.US: {
        #     "CFPB_REG": USCFPBRegulationParser,
        #     "OCC_BULL": USCCBulletinParser,
        # },
    }

    @classmethod
    def create_parser(
        cls, jurisdiction: str, document_type: str, config: ParserConfig | None = None
    ) -> BaseRegulationParser:
        """Create a parser for the specified jurisdiction and document type.

        Args:
            jurisdiction: The regulatory jurisdiction (e.g., 'uk', 'eu', 'us')
            document_type: The type of document to parse (e.g., 'FCA_CONC')
            config: Optional configuration for the parser

        Returns:
            BaseRegulationParser: Appropriate parser instance

        Raises:
            ValueError: If no parser is available for the jurisdiction/document type
        """
        jurisdiction = jurisdiction.lower()

        # Find the matching jurisdiction key (enum or string)
        jurisdiction_key = None
        for key in cls._parsers.keys():
            if (hasattr(key, "value") and str(key.value) == jurisdiction) or str(
                key
            ) == jurisdiction:
                jurisdiction_key = key
                break

        if jurisdiction_key is None:
            available_jurisdictions = ", ".join(
                [
                    str(k.value) if hasattr(k, "value") else str(k)
                    for k in cls._parsers.keys()
                ]
            )
            raise ValueError(
                f"No parsers available for jurisdiction: {jurisdiction}. "
                f"Available jurisdictions: {available_jurisdictions}"
            )

        jurisdiction_parsers = cls._parsers[jurisdiction_key]
        if document_type not in jurisdiction_parsers:
            available_types = ", ".join(jurisdiction_parsers.keys())
            raise ValueError(
                f"No parser available for document type '{document_type}' in jurisdiction '{jurisdiction}'. "
                f"Available types for {jurisdiction}: {available_types}"
            )

        parser_class = jurisdiction_parsers[document_type]
        return parser_class(config or ParserConfig.default())

    @classmethod
    def get_parser_for_file(
        cls,
        file_path: Path,
        jurisdiction: str | None = None,
        config: ParserConfig | None = None,
    ) -> tuple[BaseRegulationParser, str, str]:
        """Auto-detect and return appropriate parser for a file.

        Args:
            file_path: Path to the file to parse
            jurisdiction: Optional jurisdiction hint to narrow search
            config: Optional configuration for the parser

        Returns:
            Tuple of (parser_instance, detected_jurisdiction, detected_document_type)

        Raises:
            ValueError: If no suitable parser is found for the file
        """
        search_jurisdictions = (
            [jurisdiction.lower()] if jurisdiction else cls._parsers.keys()
        )

        for jur in search_jurisdictions:
            if jur not in cls._parsers:
                continue

            for doc_type, parser_class in cls._parsers[jur].items():
                parser = parser_class(config or ParserConfig.default())
                if parser.validate_document(file_path):
                    return parser, jur, doc_type

        available_info = []
        for jur, parsers in cls._parsers.items():
            for doc_type in parsers.keys():
                available_info.append(f"{jur}:{doc_type}")

        raise ValueError(
            f"No suitable parser found for file: {file_path}. "
            f"Available parsers: {', '.join(available_info)}"
        )

    @classmethod
    def get_supported_jurisdictions(cls) -> list[str]:
        """Get list of all supported jurisdictions.

        Returns:
            List of supported jurisdiction identifiers
        """
        # Convert enum keys to string values
        return [
            str(key.value) if hasattr(key, "value") else str(key)
            for key in cls._parsers.keys()
        ]

    @classmethod
    def get_supported_types_for_jurisdiction(cls, jurisdiction: str) -> list[str]:
        """Get list of supported document types for a specific jurisdiction.

        Args:
            jurisdiction: The jurisdiction to query

        Returns:
            List of supported document types for the jurisdiction
        """
        jurisdiction = jurisdiction.lower()

        # Find the matching jurisdiction key (enum or string)
        for key in cls._parsers.keys():
            if (hasattr(key, "value") and str(key.value) == jurisdiction) or str(
                key
            ) == jurisdiction:
                return list(cls._parsers[key].keys())

        return []

    @classmethod
    def get_all_supported_combinations(cls) -> dict[str, list[str]]:
        """Get all supported jurisdiction/document type combinations.

        Returns:
            Dictionary mapping jurisdictions to their supported document types
        """
        return {
            (
                str(jurisdiction.value)
                if hasattr(jurisdiction, "value")
                else str(jurisdiction)
            ): list(parsers.keys())
            for jurisdiction, parsers in cls._parsers.items()
        }

    @classmethod
    def register_parser(
        cls,
        jurisdiction: str,
        document_type: str,
        parser_class: type[BaseRegulationParser],
    ) -> None:
        """Register a new parser for a jurisdiction/document type combination.

        Args:
            jurisdiction: The jurisdiction identifier
            document_type: The document type identifier
            parser_class: The parser class to register

        Raises:
            ValueError: If the parser class doesn't inherit from BaseRegulationParser
        """
        if not issubclass(parser_class, BaseRegulationParser):
            raise ValueError(
                f"Parser class must inherit from BaseRegulationParser: {parser_class}"
            )

        jurisdiction = jurisdiction.lower()
        if jurisdiction not in cls._parsers:
            cls._parsers[jurisdiction] = {}

        cls._parsers[jurisdiction][document_type] = parser_class

    @classmethod
    def get_parser_info(cls) -> dict[str, dict[str, dict]]:
        """Get information about all registered parsers organized by jurisdiction.

        Returns:
            Nested dictionary with jurisdiction -> document_type -> parser_info
        """
        info: dict[str, dict[str, dict]] = {}
        for jurisdiction, parsers in cls._parsers.items():
            info[jurisdiction] = {}
            for doc_type, parser_class in parsers.items():
                # Create a temporary instance to get info
                temp_parser = parser_class(ParserConfig.default())
                info[jurisdiction][doc_type] = temp_parser.get_parser_info()

        return info
