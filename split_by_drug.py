#!/usr/bin/env python3
"""Split PDF into individual drug files with header row included."""

import json
import re
from pathlib import Path
from typing import Annotated

import fitz  # PyMuPDF

BASE_DIR = Path(__file__).parent
SOURCE_PDF = BASE_DIR / "data.pdf"
NAMES_FILE = BASE_DIR / "page_names.json"
OUTPUT_DIR = BASE_DIR / "docs" / "drugs"

# Header row height (approximate, in points) - covers the table header
HEADER_HEIGHT = 55  # Will be refined based on actual PDF


def load_drug_pages() -> dict[str, list[int]]:
    """Load drug name to page mapping from page_names.json."""
    if NAMES_FILE.exists():
        with open(NAMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def sanitize_filename(name: str) -> str:
    """Convert drug name to a safe filename."""
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def format_pages_string(pages: list[int]) -> str:
    """Format page list as string for filename."""
    if len(pages) == 1:
        return f"p{pages[0]}"
    elif len(pages) == 2 and pages[1] == pages[0] + 1:
        return f"p{pages[0]}-{pages[1]}"
    else:
        return f"p{'-'.join(str(p) for p in pages)}"


def get_drug_order_on_page(doc: fitz.Document, page_num: int, drug_names: list[str]) -> list[tuple[str, float]]:
    """Get the y-positions of drug names on a specific page."""
    page = doc[page_num - 1]  # 0-indexed
    results = []

    for drug_name in drug_names:
        # Search for the drug name on the page
        text_instances = page.search_for(drug_name)
        if text_instances:
            # Get the first instance (should be in the first column)
            # Filter to instances in the left portion of the page (drug name column)
            page_width = page.rect.width
            left_instances = [inst for inst in text_instances if inst.x0 < page_width * 0.15]
            if left_instances:
                y_pos = left_instances[0].y0
                results.append((drug_name, y_pos))

    # Sort by y position
    results.sort(key=lambda x: x[1])
    return results


def find_drug_row_bounds(
    doc: fitz.Document,
    drug_name: str,
    pages: list[int],
    all_drugs: dict[str, list[int]],
) -> list[tuple[int, fitz.Rect]]:
    """Find the bounding rectangles for a drug's row across its pages.

    Returns list of (page_num, rect) tuples.
    """
    bounds = []

    for page_num in pages:
        page = doc[page_num - 1]  # 0-indexed
        page_rect = page.rect

        # Search for the drug name text
        text_instances = page.search_for(drug_name)
        if not text_instances:
            # If exact match not found, try partial match
            print(f"  Warning: '{drug_name}' not found on page {page_num}, using full page")
            bounds.append((page_num, page_rect))
            continue

        # Get instances in the drug name column (left side)
        page_width = page_rect.width
        left_instances = [inst for inst in text_instances if inst.x0 < page_width * 0.15]

        if not left_instances:
            # Fall back to any instance
            left_instances = text_instances

        drug_y_top = left_instances[0].y0 - 5  # Small padding above

        # Find the next drug's y position to determine row bottom
        # Get all drugs that appear on this page
        drugs_on_page = []
        for d_name, d_pages in all_drugs.items():
            if page_num in d_pages:
                drugs_on_page.append(d_name)

        # Get ordered list of drugs on this page by y position
        drug_positions = get_drug_order_on_page(doc, page_num, drugs_on_page)

        # Find our drug and the next one
        drug_y_bottom = page_rect.height  # Default to bottom of page
        found_current = False

        for i, (d_name, y_pos) in enumerate(drug_positions):
            if d_name == drug_name:
                found_current = True
                # Check if there's a next drug on this page
                if i + 1 < len(drug_positions):
                    next_drug_y = drug_positions[i + 1][1]
                    drug_y_bottom = next_drug_y - 2  # Small gap before next drug
                break

        if not found_current:
            # Drug not found in position list, use full page below header
            drug_y_top = HEADER_HEIGHT

        # Create the bounding rectangle
        row_rect = fitz.Rect(
            0,  # x0 - left edge
            drug_y_top,  # y0 - top
            page_rect.width,  # x1 - right edge
            drug_y_bottom,  # y1 - bottom
        )

        bounds.append((page_num, row_rect))

    return bounds


def extract_header_region(doc: fitz.Document) -> fitz.Rect:
    """Extract the header row region from page 1."""
    page = doc[0]
    page_rect = page.rect

    # The header consists of:
    # 1. Title row at the very top
    # 2. Column headers (Tên hoạt chất, Dược thư Quốc gia, etc.)

    # Search for "Tên hoạt chất" to find header position
    header_text = page.search_for("Tên")
    if header_text:
        header_bottom = header_text[0].y1 + 5  # Add small padding
    else:
        header_bottom = HEADER_HEIGHT

    # Search for "hoạt chất" to be more precise
    header_text2 = page.search_for("hoạt chất")
    if header_text2:
        header_bottom = max(header_bottom, header_text2[0].y1 + 5)

    return fitz.Rect(0, 0, page_rect.width, header_bottom)


def create_drug_pdf(
    doc: fitz.Document,
    drug_name: str,
    pages: list[int],
    header_rect: fitz.Rect,
    row_bounds: list[tuple[int, fitz.Rect]],
) -> Path:
    """Create a new PDF with header + drug row content."""
    new_doc = fitz.open()

    # Get source page dimensions
    source_page = doc[0]
    page_width = source_page.rect.width

    # Calculate total height needed
    total_height = header_rect.height
    for _, rect in row_bounds:
        total_height += rect.height

    # Create a single page with the combined content
    new_page = new_doc.new_page(width=page_width, height=total_height)

    current_y = 0

    # Copy header from page 1
    header_clip = fitz.Rect(0, 0, page_width, header_rect.height)
    new_page.show_pdf_page(
        header_clip,  # Where to place on new page
        doc,  # Source document
        0,  # Source page index (page 1)
        clip=header_rect,  # What to clip from source
    )
    current_y += header_rect.height

    # Copy each drug row section
    for page_num, row_rect in row_bounds:
        source_page_idx = page_num - 1
        row_height = row_rect.height

        # Destination rectangle on the new page
        dest_rect = fitz.Rect(0, current_y, page_width, current_y + row_height)

        new_page.show_pdf_page(
            dest_rect,
            doc,
            source_page_idx,
            clip=row_rect,
        )
        current_y += row_height

    # Generate filename
    safe_name = sanitize_filename(drug_name)
    pages_str = format_pages_string(pages)
    filename = f"{safe_name}_{pages_str}.pdf"
    output_path = OUTPUT_DIR / filename

    # Save the new PDF
    new_doc.save(output_path)
    new_doc.close()

    return output_path


def main() -> None:
    """Split PDF into individual drug files."""
    print("Splitting PDF by drug...")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load source PDF
    doc = fitz.open(SOURCE_PDF)
    print(f"Loaded {SOURCE_PDF} ({doc.page_count} pages)")

    # Load drug-to-page mapping
    drugs = load_drug_pages()
    if not drugs:
        print("Error: No drug mappings found in page_names.json")
        return

    print(f"Found {len(drugs)} drugs to extract")

    # Extract header region
    header_rect = extract_header_region(doc)
    print(f"Header region: height={header_rect.height:.1f}pt")

    # Process each drug
    success_count = 0
    for drug_name, pages in drugs.items():
        print(f"\nProcessing: {drug_name} (pages {pages})...")

        try:
            # Find row bounds
            row_bounds = find_drug_row_bounds(doc, drug_name, pages, drugs)

            # Create the drug PDF
            output_path = create_drug_pdf(doc, drug_name, pages, header_rect, row_bounds)
            print(f"  Created: {output_path.name}")
            success_count += 1
        except Exception as e:
            print(f"  Error: {e}")

    doc.close()
    print(f"\nDone! Created {success_count}/{len(drugs)} drug PDFs in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
