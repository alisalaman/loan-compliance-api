from pathlib import Path
from typing import Dict, Type, List, Optional, Tuple
from enum import Enum

from .base import BaseRegulationParser
from .uk_fca_conc import UKFCACoNCParser
from ..models import ParserConfig


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
    _parsers: Dict[str, Dict[str, Type[BaseRegulationParser]]] = {
        Jurisdiction.UK: {
            "FCA_CONC": UKFCACoNCParser,
            # "FCA_PRIN": UKFCAPrinciplesParser,
            # "PRA_CRR": UKPRACRRParser,
        },
        # Future jurisdictions:
        # Jurisdiction.EU: {
        #     "EBA_GL": EUEBAGuidelinesParser,
        #     "ECB_REG": ECBRegulationParser,
        # },
        # Jurisdiction.US: {
        #     "CFPB_REG": USCFPBRegulationParser,
        #     "OCC_BULL": USCCBulletinParser,
        # },
    }
    
    @classmethod
    def create_parser(
        cls, 
        jurisdiction: str, 
        document_type: str, 
        config: Optional[ParserConfig] = None
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
        
        if jurisdiction not in cls._parsers:
            available_jurisdictions = ", ".join(cls._parsers.keys())
            raise ValueError(
                f"No parsers available for jurisdiction: {jurisdiction}. "
                f"Available jurisdictions: {available_jurisdictions}"
            )
        
        jurisdiction_parsers = cls._parsers[jurisdiction]
        if document_type not in jurisdiction_parsers:
            available_types = ", ".join(jurisdiction_parsers.keys())
            raise ValueError(
                f"No parser available for document type '{document_type}' in jurisdiction '{jurisdiction}'. "
                f"Available types for {jurisdiction}: {available_types}"
            )
        
        parser_class = jurisdiction_parsers[document_type]
        return parser_class(config)
    
    @classmethod
    def get_parser_for_file(
        cls, 
        file_path: Path, 
        jurisdiction: Optional[str] = None,
        config: Optional[ParserConfig] = None
    ) -> Tuple[BaseRegulationParser, str, str]:
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
        search_jurisdictions = [jurisdiction.lower()] if jurisdiction else cls._parsers.keys()
        
        for jur in search_jurisdictions:
            if jur not in cls._parsers:
                continue
                
            for doc_type, parser_class in cls._parsers[jur].items():
                parser = parser_class(config)
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
    def get_supported_jurisdictions(cls) -> List[str]:
        """Get list of all supported jurisdictions.
        
        Returns:
            List of supported jurisdiction identifiers
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def get_supported_types_for_jurisdiction(cls, jurisdiction: str) -> List[str]:
        """Get list of supported document types for a specific jurisdiction.
        
        Args:
            jurisdiction: The jurisdiction to query
            
        Returns:
            List of supported document types for the jurisdiction
        """
        jurisdiction = jurisdiction.lower()
        return list(cls._parsers.get(jurisdiction, {}).keys())
    
    @classmethod
    def get_all_supported_combinations(cls) -> Dict[str, List[str]]:
        """Get all supported jurisdiction/document type combinations.
        
        Returns:
            Dictionary mapping jurisdictions to their supported document types
        """
        return {
            jurisdiction: list(parsers.keys())
            for jurisdiction, parsers in cls._parsers.items()
        }
    
    @classmethod
    def register_parser(
        cls, 
        jurisdiction: str, 
        document_type: str, 
        parser_class: Type[BaseRegulationParser]
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
    def get_parser_info(cls) -> Dict[str, Dict[str, dict]]:
        """Get information about all registered parsers organized by jurisdiction.
        
        Returns:
            Nested dictionary with jurisdiction -> document_type -> parser_info
        """
        info = {}
        for jurisdiction, parsers in cls._parsers.items():
            info[jurisdiction] = {}
            for doc_type, parser_class in parsers.items():
                # Create a temporary instance to get info
                temp_parser = parser_class()
                info[jurisdiction][doc_type] = temp_parser.get_parser_info()
        
        return info