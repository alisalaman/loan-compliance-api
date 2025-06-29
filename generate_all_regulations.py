#!/usr/bin/env python3
"""
Utility script to generate JSON files for all available regulation parsers.

Usage:
    python generate_all_regulations.py [--output-dir OUTPUT_DIR]

Example:
    python generate_all_regulations.py --output-dir ./parsed_regulations
"""

import argparse
import json
import sys
from pathlib import Path

from src.regulations.services.parser_service import RegulationParserService


def generate_all_json_files(output_dir: str) -> None:
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
    output_path.mkdir(exist_ok=True, parents=True)

    # Get all supported jurisdictions
    jurisdictions = service.get_supported_jurisdictions()

    if not jurisdictions:
        print("❌ No jurisdictions found!")
        sys.exit(1)

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

                    # Convert to JSON and save (serialize datetime fields)
                    json_data = parsed_doc.model_dump(mode='json')
                    with open(filepath, "w", encoding="utf-8") as f:
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
                with open(filepath, "w", encoding="utf-8") as f:
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

    if total_generated == 0:
        print(
            "\n⚠️  No files were generated. Check that regulation PDF files exist in the data directory."
        )
        sys.exit(1)
    else:
        print(f"\n✨ Successfully generated {total_generated} regulation JSON files!")


def main():
    """Main entry point for the command-line utility."""
    parser = argparse.ArgumentParser(
        description="Generate JSON files for all available regulation parsers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_all_regulations.py
  python generate_all_regulations.py --output-dir ./parsed_regulations
  python generate_all_regulations.py -o /tmp/regulations
        """.strip(),
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="output",
        help="Directory to save the generated JSON files (default: output)",
    )

    args = parser.parse_args()

    try:
        generate_all_json_files(args.output_dir)
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
