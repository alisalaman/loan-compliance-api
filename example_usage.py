"""Example usage of the refactored regulation parser service."""

from src.regulations.services.parser_service import RegulationParserService
from src.regulations.models import ParserConfig

def main():
    # Create service instance
    service = RegulationParserService()
    
    # Example 1: Parse UK regulations (auto-selects FCA_CONC)
    print("Example 1: Parse UK regulations with auto-detection")
    try:
        result = service.parse_document("uk")
        print(f"✅ Parsed {result.clause_count} clauses from UK regulations")
        print(f"   Document type: {result.document_type}")
        print(f"   Source: {result.metadata.source_file}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Parse specific UK FCA CONC document
    print("Example 2: Parse specific UK FCA CONC document")
    try:
        result = service.parse_document("uk", "FCA_CONC")
        print(f"✅ Parsed {result.clause_count} clauses from UK FCA CONC")
        sections = result.get_sections()
        print(f"   Sections found: {', '.join(sections)}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Use custom configuration
    print("Example 3: Parse with custom configuration")
    custom_config = ParserConfig(
        document_file_path="data/regulations/uk/fca/CONC.pdf",
        sections_to_extract={"7": "Arrears and default only"}
    )
    custom_service = RegulationParserService(custom_config)
    
    try:
        result = custom_service.parse_document("uk", "FCA_CONC")
        print(f"✅ Parsed {result.clause_count} clauses with custom config")
        print(f"   Sections extracted: {result.metadata.sections_extracted}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 4: Show supported jurisdictions and types
    print("Example 4: Available parsers")
    jurisdictions = service.get_supported_jurisdictions()
    print(f"Supported jurisdictions: {', '.join(jurisdictions)}")
    
    for jurisdiction in jurisdictions:
        types = service.get_supported_types_for_jurisdiction(jurisdiction)
        print(f"  {jurisdiction}: {', '.join(types)}")

if __name__ == "__main__":
    main()