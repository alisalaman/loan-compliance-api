import json
import re
from pathlib import Path

import pdfplumber

SECTIONS_TO_EXTRACT = {
    "5.2A": "Creditworthiness assessment",
    "2.10": "Mental capacity guidance",
    "7": "Arrears, default and recovery (including repossessions)",
}


def get_pdf_text_with_pages(pdf_path: Path, start_page: int = 40) -> list[dict]:
    """Extracts text from each page of a PDF and returns a list of dictionaries,
    where each dictionary contains the page number and the text of that page.
    Skips title pages and table of contents by starting from start_page."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"The file '{pdf_path}' was not found.")

    pages_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Skip title pages, TOC, and other preliminary content
            if page_num + 1 < start_page:
                continue
            pages_content.append(
                {
                    "page_number": page_num + 1,
                    "text": page.extract_text(x_tolerance=2, y_tolerance=3),
                }
            )
    return pages_content


def find_section_text_and_pages(
    pages_content: list[dict], section_number: str, section_title: str
) -> dict | None:
    """Finds the full text of a section and the pages it spans."""
    section_text_parts = []
    section_pages = []
    in_section = False

    # Special handling for section 7 - look for first subsection instead
    if section_number == "7":
        start_pattern = re.compile(
            r"^\s*7\.1\s+Application", re.IGNORECASE | re.MULTILINE
        )
    else:
        # A more precise pattern to find the start of the section
        start_pattern = re.compile(
            rf"^\s*{re.escape(section_number)}\s+{re.escape(section_title)}",
            re.IGNORECASE | re.MULTILINE,
        )
    # Pattern to identify actual section headers (not just clause numbers)
    # Look for section number followed by a title/description
    end_pattern = re.compile(
        r"^\s*(\d{1,2}(?:\.\d{1,2}[A-Z]?)?)\s+[A-Z][a-zA-Z\s]{10,}", re.MULTILINE
    )

    for _i, page in enumerate(pages_content):
        text = page["text"]
        if not text:  # Skip empty pages
            continue

        if not in_section:
            if start_pattern.search(text):
                in_section = True
                section_pages.append(page["page_number"])
                # Capture text after the section title on the starting page
                match = start_pattern.search(text)
                section_text_parts.append(text[match.end() :].strip())
        else:
            # Check if the current page starts with a new section.
            match = end_pattern.search(text)
            if match:
                next_section_num_prefix = match.group(1).split(".")[0]
                current_section_num_prefix = section_number.split(".")[0]

                # Check if this is actually a different section (not a subsection of current)
                next_section_full = match.group(1)

                # Special handling for section 7 - continue until we hit section 8
                if section_number == "7":
                    if next_section_num_prefix == "8":
                        # Our section ends here. Append text before the new section starts.
                        section_text_parts.append(text[: match.start()].strip())
                        break
                else:
                    # Stop if we hit a completely different main section (e.g., 6.x after 5.2A)
                    if next_section_num_prefix != current_section_num_prefix:
                        # Our section ends here. Append text before the new section starts.
                        section_text_parts.append(text[: match.start()].strip())
                        break

                    # Stop if we hit a sibling section (e.g., 5.3 after 5.2A, but not 5.2A.x after 5.2A)
                    if (
                        next_section_num_prefix == current_section_num_prefix
                        and not next_section_full.startswith(section_number + ".")
                    ):
                        # Our section ends here. Append text before the new section starts.
                        section_text_parts.append(text[: match.start()].strip())
                        break

            section_pages.append(page["page_number"])
            section_text_parts.append(text.strip())

    if not section_text_parts:
        return None

    return {"text": "\n".join(section_text_parts), "pages": section_pages}


def find_subsection_name(
    clause_id: str, pages_content: list[dict], section_pages: list[int]
) -> str:
    """Find the subsection name for a given clause by looking for section headers."""
    # First try to find the nearest subsection header before this clause
    current_subsection = ""

    # Look through the pages to find subsection headers
    for page_info in pages_content:
        if page_info["page_number"] in section_pages:
            text = page_info["text"]
            lines = text.split("\n")

            for _i, line in enumerate(lines):
                line = line.strip()

                # Check if this line contains our clause - if so, return the current subsection
                if clause_id in line and len(line) < 200:
                    return current_subsection

                # Check if this is a subsection header (standalone title line)
                # These are usually short, capitalized, and don't start with numbers
                if (
                    len(line) > 3
                    and len(line) < 50
                    and line[0].isupper()
                    and not line[0].isdigit()
                    and "www." not in line
                    and "Release" not in line
                    and "CONC" not in line
                    and "." not in line[:10]  # No clause numbers at start
                    and not line.startswith("(")  # Not a sub-point
                    and line.count(" ") < 8
                ):  # Not too many words

                    # Clean up the potential subsection name
                    cleaned = re.sub(
                        r"^[.\s]+|[.\s]+$", "", line
                    )  # Remove leading/trailing dots/spaces
                    if cleaned and len(cleaned) > 3:
                        current_subsection = cleaned

    return current_subsection


def find_main_section_name(
    clause_id: str, pages_content: list[dict], section_pages: list[int]
) -> str:
    """Find the main section name for a given clause (e.g., 'Application' for 7.1.x clauses)."""
    # Extract the main section (e.g., "7.1" from "7.1.2")
    parts = clause_id.split(".")
    if len(parts) >= 2:
        main_section = ".".join(parts[:2])  # e.g., "7.1", "5.2A"
    else:
        return ""

    # Look for main section headers like "7.1 Application"
    for page_info in pages_content:
        if page_info["page_number"] in section_pages:
            text = page_info["text"]
            lines = text.split("\n")

            for line in lines:
                line = line.strip()
                if line.startswith(main_section + " "):
                    title = line[len(main_section) :].strip()
                    # Clean up common patterns
                    title = re.sub(r"^\s*[.]{3,}.*", "", title)  # Remove dots
                    title = re.sub(r"\s+", " ", title)  # Normalize spaces
                    if (
                        len(title) > 2
                        and len(title) < 100
                        and not title.startswith("www")
                    ):
                        return title

    return ""


def extract_clauses_from_section_text(
    section_text: str,
    section_number: str,
    section_pages: list[int],
    pages_content: list[dict],
) -> list[dict]:
    """Extracts clauses from a section's text and assigns page numbers."""
    clauses = []

    # For section 7, we need to match all subsections (7.1.x, 7.2.x, etc.)
    if section_number == "7":
        clause_pattern = re.compile(
            r"^\s*(7\.\d+(?:\.\d+[A-Z]?)*)\s+([RG])\s+(.*?)(?=^\s*7\.\d+(?:\.\d+[A-Z]?)*\s+[RG]\s+|\Z)",
            re.DOTALL | re.MULTILINE,
        )
    else:
        # Original pattern for other sections
        clause_pattern = re.compile(
            rf"^\s*({re.escape(section_number)}(?:\.\d+[A-Z]?)*)\s+([RG])\s+(.*?)(?=^\s*{re.escape(section_number)}(?:\.\d+[A-Z]?)*\s+[RG]\s+|\Z)",
            re.DOTALL | re.MULTILINE,
        )

    for match in clause_pattern.finditer(section_text):
        clause_id = match.group(1).strip()
        clause_type = match.group(2).strip()  # R or G
        content = match.group(3).strip()

        # Clean up extra newlines and spaces within the content
        # Preserve internal newlines, but clean up leading/trailing whitespace on lines
        content = """
""".join(
            [
                line.strip()
                for line in content.split(
                    """
"""
                )
            ]
        ).strip()

        # Find the most accurate page number for the clause
        page_number = section_pages[0] if section_pages else -1
        for p_num in section_pages:
            # Find the page that contains this specific clause
            for page_info in pages_content:
                if page_info["page_number"] == p_num and clause_id in page_info["text"]:
                    page_number = p_num
                    break

        # Find the main section name and subsection name for this clause
        main_section_name = find_main_section_name(
            clause_id, pages_content, section_pages
        )
        subsection_name = find_subsection_name(clause_id, pages_content, section_pages)

        clauses.append(
            {
                "section": section_number,
                "clause_id": f"{clause_id} {clause_type}",
                "main_section_name": main_section_name,
                "subsection_name": subsection_name,
                "content": content,
                "page_number": page_number,
            }
        )
    return clauses


def main():
    root_dir = Path(__file__).parent.parent.parent.parent
    uk_fca_conf_dir = root_dir / "data" / "regulations" / "uk" / "fca"
    pdf_path = uk_fca_conf_dir / "CONC.pdf"
    output_path = uk_fca_conf_dir / "regulations_uk_fca_conf_structured.json"
    all_extracted_clauses = []

    try:
        pages_content = get_pdf_text_with_pages(pdf_path)
        print(f"Successfully read {len(pages_content)} pages from the PDF.")

        for number, title in SECTIONS_TO_EXTRACT.items():
            print(f"Processing section {number}: {title}...")
            section_info = find_section_text_and_pages(pages_content, number, title)

            if section_info:
                print(f"Found section {number} on pages: {section_info['pages']}")
                clauses = extract_clauses_from_section_text(
                    section_info["text"], number, section_info["pages"], pages_content
                )

                if clauses:
                    all_extracted_clauses.extend(clauses)
                    print(f"Extracted {len(clauses)} clauses from section {number}.")
                else:
                    print(f"No clauses found for section {number}.")
            else:
                print(f"Section {number} not found or could not be fully extracted.")
                # Special handling for section 5.3 if it's deleted and not found by pattern
                if (
                    number == "5.3"
                    and "5.3 Conduct of business in relation to creditworthiness and affordability [deleted]"
                    in title
                ):
                    for page in pages_content:
                        if (
                            "5.3 Conduct of business in relation to creditworthiness and affordability [deleted]"
                            in page["text"]
                        ):
                            all_extracted_clauses.append(
                                {
                                    "section": "5.3",
                                    "clause_id": "5.3",
                                    "content": "[deleted]",
                                    "page_number": page["page_number"],
                                }
                            )
                            print("Added deleted section 5.3 entry.")
                            break

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_extracted_clauses, f, indent=4, ensure_ascii=False)

        print(
            f"\nExtraction complete. Saved {len(all_extracted_clauses)} clauses to {output_path}"
        )

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
