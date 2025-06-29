#!/usr/bin/env python3
"""Development scripts for code quality, formatting, and testing."""

import json
import subprocess
import sys
from pathlib import Path


def lint() -> None:
    """Run all linting and code quality checks."""
    print("🔍 Running code quality checks...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    success = True

    # Run ruff for linting
    print("\n📋 Running ruff linting...")
    try:
        subprocess.run(["ruff", "check", "."], cwd=project_root, check=True)
        print("✅ Ruff linting passed")
    except subprocess.CalledProcessError:
        print("❌ Ruff linting failed")
        success = False

    # Run mypy for type checking
    print("\n🔍 Running mypy type checking...")
    try:
        subprocess.run(["mypy", "src/"], cwd=project_root, check=True)
        print("✅ MyPy type checking passed")
    except subprocess.CalledProcessError:
        print("❌ MyPy type checking failed")
        success = False
    except FileNotFoundError:
        print("⚠️  MyPy not found, skipping type checking")

    # Check import sorting
    print("\n📦 Checking import sorting...")
    try:
        subprocess.run(
            ["ruff", "check", "--select", "I", "."], cwd=project_root, check=True
        )
        print("✅ Import sorting is correct")
    except subprocess.CalledProcessError:
        print("❌ Import sorting issues found")
        success = False

    if success:
        print("\n🎉 All quality checks passed!")
        sys.exit(0)
    else:
        print("\n💥 Some quality checks failed!")
        sys.exit(1)


def format_code() -> None:
    """Format code using black and fix ruff issues."""
    print("🎨 Formatting code...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    # Run black formatter
    print("\n🖤 Running Black formatter...")
    try:
        subprocess.run(["black", "."], cwd=project_root, check=True)
        print("✅ Black formatting completed")
    except subprocess.CalledProcessError:
        print("❌ Black formatting failed")
        sys.exit(1)
    except FileNotFoundError:
        print("⚠️  Black not found, skipping formatting")

    # Run ruff with --fix to auto-fix issues
    print("\n🔧 Running ruff auto-fixes...")
    try:
        subprocess.run(["ruff", "check", "--fix", "."], cwd=project_root, check=True)
        print("✅ Ruff auto-fixes completed")
    except subprocess.CalledProcessError:
        print("❌ Some ruff issues couldn't be auto-fixed")
        sys.exit(1)

    print("\n🎉 Code formatting completed!")


def run_tests() -> None:
    """Run the full test suite with coverage."""
    print("🧪 Running test suite...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    # Run pytest with coverage
    print("\n📊 Running tests with coverage...")
    try:
        subprocess.run(
            ["pytest", "--verbose", "--tb=short", "tests/"],
            cwd=project_root,
            check=True,
        )
        print("✅ All tests passed!")
    except subprocess.CalledProcessError:
        print("❌ Some tests failed!")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ pytest not found!")
        sys.exit(1)


def check_security() -> None:
    """Run security checks using bandit and safety."""
    print("🔒 Running security checks...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    success = True

    # Run bandit for security issues
    print("\n🛡️  Running bandit security scan...")
    try:
        subprocess.run(
            ["bandit", "-r", "src/", "-f", "json", "-o", "bandit-report.json"],
            cwd=project_root,
            check=True,
        )
        print("✅ Bandit security scan passed")
    except subprocess.CalledProcessError:
        print("❌ Bandit found security issues")
        success = False
    except FileNotFoundError:
        print("⚠️  Bandit not found, skipping security scan")

    # Run safety to check dependencies
    print("\n🔐 Checking dependency vulnerabilities...")
    try:
        subprocess.run(["safety", "check"], cwd=project_root, check=True)
        print("✅ No known vulnerabilities in dependencies")
    except subprocess.CalledProcessError:
        print("❌ Vulnerabilities found in dependencies")
        success = False
    except FileNotFoundError:
        print("⚠️  Safety not found, skipping dependency check")

    if success:
        print("\n🎉 Security checks passed!")
        sys.exit(0)
    else:
        print("\n💥 Security issues found!")
        sys.exit(1)


def check_all() -> None:
    """Run all quality checks: linting, formatting check, tests, and security."""
    print("🚀 Running complete code quality pipeline...")

    # Run formatting check (don't auto-fix, just check)
    print("\n1️⃣  Checking code formatting...")
    project_root = Path(__file__).parent.parent

    try:
        subprocess.run(["black", "--check", "."], cwd=project_root, check=True)
        print("✅ Code formatting is correct")
    except subprocess.CalledProcessError:
        print("❌ Code needs formatting (run 'uv run format' to fix)")
        sys.exit(1)
    except FileNotFoundError:
        print("⚠️  Black not found, skipping format check")

    # Run linting
    print("\n2️⃣  Running linting...")
    lint()

    # Run tests
    print("\n3️⃣  Running tests...")
    run_tests()

    # Run security checks
    print("\n4️⃣  Running security checks...")
    check_security()

    print("\n🎉 All quality checks passed! Ready for deployment!")


def generate_all() -> None:
    """Generate JSON files for all available regulation parsers."""
    print("🚀 Generating JSON files for all parsers...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    try:
        # Add project root to Python path for imports
        sys.path.insert(0, str(project_root))
        # Import here to avoid circular imports
        from src.regulations.services.parser_service import RegulationParserService

        # Create service instance
        service = RegulationParserService()

        # Create output directory
        output_path = project_root / "output"
        output_path.mkdir(exist_ok=True)

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

                        # Convert to JSON and save
                        json_data = parsed_doc.model_dump(mode="json")
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

                    json_data = results.model_dump(mode="json")
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
            print(
                f"\n✨ Successfully generated {total_generated} regulation JSON files!"
            )

    except ImportError as e:
        print(f"❌ Failed to import regulation service: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Allow running scripts directly
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "lint":
            lint()
        elif command == "format":
            format_code()
        elif command == "test":
            run_tests()
        elif command == "security":
            check_security()
        elif command == "all":
            check_all()
        elif command == "generate-all":
            generate_all()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: lint, format, test, security, all, generate-all")
            sys.exit(1)
    else:
        print("Available commands: lint, format, test, security, all, generate-all")
