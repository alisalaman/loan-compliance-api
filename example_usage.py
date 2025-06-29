"""Example usage of the refactored regulation parser service."""

import json
from pathlib import Path

from src.regulations.models import ParserConfig
from src.regulations.services.parser_service import RegulationParserService


def generate_all_json_files(output_dir: str = "output"):
    """
    Generate JSON files for all available parsers in all jurisdictions.

    Args:
        output_dir: Directory to save the JSON files
    """
    print("🚀 Generating JSON files for all parsers...")

    # Create service instance
    service = RegulationParserService()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get all supported jurisdictions
    jurisdictions = service.get_supported_jurisdictions()

    total_generated = 0
    total_failed = 0

    for jurisdiction in jurisdictions:
        print(f"\n📋 Processing jurisdiction: {jurisdiction}")

        try:
            # Parse all document types for this jurisdiction
            results = service.parse_document(jurisdiction)

            # Handle the case where results is a dict (multiple parsers)
            if isinstance(results, dict):
                for doc_type, parsed_doc in results.items():
                    filename = f"{jurisdiction}_{doc_type}_parsed.json"
                    filepath = output_path / filename

                    # Convert to JSON and save
                    json_data = parsed_doc.model_dump(mode='json')
                    with open(filepath, "w") as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)

                    print(
                        f"✅ Generated: {filename} ({parsed_doc.clause_count} clauses)"
                    )
                    total_generated += 1
            else:
                # Single parser result (backward compatibility)
                filename = f"{jurisdiction}_parsed.json"
                filepath = output_path / filename

                json_data = results.model_dump(mode='json')
                with open(filepath, "w") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)

                print(f"✅ Generated: {filename} ({results.clause_count} clauses)")
                total_generated += 1

        except Exception as e:
            print(f"❌ Failed to parse {jurisdiction}: {e}")
            total_failed += 1

    print("\n🎉 Summary:")
    print(f"   ✅ Generated: {total_generated} JSON files")
    print(f"   ❌ Failed: {total_failed} jurisdictions")
    print(f"   📁 Output directory: {output_path.absolute()}")


def main():
    # Create service instance
    service = RegulationParserService()

    # Example 1: Parse all documents in UK jurisdiction
    print("Example 1: Parse all documents in UK jurisdiction")
    try:
        results = service.parse_document("uk")
        if isinstance(results, dict):
            print(f"✅ Parsed {len(results)} document types from UK:")
            for doc_type, parsed_doc in results.items():
                print(f"   • {doc_type}: {parsed_doc.clause_count} clauses")
                print(f"     Source: {parsed_doc.metadata.source_file}")
        else:
            # Backward compatibility for single result
            print(f"✅ Parsed {results.clause_count} clauses from UK regulations")
            print(f"   Document type: {results.document_type}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n" + "=" * 50 + "\n")

    # Example 2: Parse specific UK FCA CONC document
    print("Example 2: Parse specific UK FCA CONC document")
    try:
        result = service.parse_document("uk", "FCA_CONC")
        print(f"✅ Parsed {result.clause_count} clauses from UK FCA CONC")
        sections = result.get_sections()
        print(f"   Sections found: {', '.join(sections)}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n" + "=" * 50 + "\n")

    # Example 2a: Generate all JSON files
    print("Example 2a: Generate JSON files for all parsers")
    try:
        generate_all_json_files("output")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n" + "=" * 50 + "\n")

    # Example 3: Use custom configuration
    print("Example 3: Parse with custom configuration")
    custom_config = ParserConfig(
        document_file_path="data/regulations/uk/fca/CONC.pdf",
        sections_to_extract={"7": "Arrears and default only"},
    )
    custom_service = RegulationParserService(custom_config)

    try:
        result = custom_service.parse_document("uk", "FCA_CONC")
        print(f"✅ Parsed {result.clause_count} clauses with custom config")
        print(f"   Sections extracted: {result.metadata.sections_extracted}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n" + "=" * 50 + "\n")

    # Example 4: Show supported jurisdictions and types
    print("Example 4: Available parsers")
    jurisdictions = service.get_supported_jurisdictions()
    print(f"Supported jurisdictions: {', '.join(jurisdictions)}")

    for jurisdiction in jurisdictions:
        types = service.get_supported_types_for_jurisdiction(jurisdiction)
        print(f"  {jurisdiction}: {', '.join(types)}")


if __name__ == "__main__":
    main()
