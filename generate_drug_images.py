#!/usr/bin/env python3
"""Generate PNG images for each drug from DOCX source."""

import re
from html import escape
from pathlib import Path

from docx import Document
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
DOCX_FILE = BASE_DIR / "data.docx"
OUTPUT_DIR = BASE_DIR / "docs" / "drugs"

# Column widths in percentage (matching original PDF layout)
COLUMN_WIDTHS = [10, 22.5, 22.5, 22.5, 22.5]


def sanitize_filename(name: str) -> str:
    """Convert drug name to a safe filename."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.replace(' ', '_')
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def extract_nested_table_html(table: Table) -> str:
    """Convert a nested DOCX table to HTML."""
    html_parts = ['<table class="nested-table">']

    for row in table.rows:
        html_parts.append('<tr>')
        for cell in row.cells:
            cell_text = escape(cell.text.strip())
            # Handle line breaks within cells
            cell_text = cell_text.replace('\n', '<br>')
            html_parts.append(f'<td>{cell_text}</td>')
        html_parts.append('</tr>')

    html_parts.append('</table>')
    return ''.join(html_parts)


def extract_cell_html(cell: _Cell) -> str:
    """Convert cell content (paragraphs + nested tables) to HTML."""
    html_parts = []

    # Track which nested tables we've processed
    nested_tables = list(cell.tables)
    table_idx = 0

    # Process cell's XML to maintain order of paragraphs and tables
    for element in cell._tc:
        if element.tag.endswith('}p'):  # Paragraph
            # Find corresponding paragraph object
            for para in cell.paragraphs:
                if para._p == element:
                    text = para.text.strip()
                    if text:
                        # Escape HTML and handle formatting
                        text_html = escape(text)
                        # Handle bold text (check runs)
                        for run in para.runs:
                            if run.bold and run.text.strip():
                                run_text = escape(run.text)
                                text_html = text_html.replace(run_text, f'<strong>{run_text}</strong>', 1)

                        html_parts.append(f'<p>{text_html}</p>')
                    break
        elif element.tag.endswith('}tbl'):  # Table
            if table_idx < len(nested_tables):
                html_parts.append(extract_nested_table_html(nested_tables[table_idx]))
                table_idx += 1

    return ''.join(html_parts) if html_parts else '&nbsp;'


def generate_html_for_drug(drug_name: str, header_cells: list[str], drug_cells: list[str]) -> str:
    """Generate complete HTML document for a single drug."""
    # Build header row
    header_html = '<tr class="header-row">'
    for i, text in enumerate(header_cells):
        width = COLUMN_WIDTHS[i]
        header_html += f'<th style="width: {width}%">{escape(text)}</th>'
    header_html += '</tr>'

    # Build drug row
    drug_html = '<tr class="drug-row">'
    for i, cell_html in enumerate(drug_cells):
        width = COLUMN_WIDTHS[i]
        drug_html += f'<td style="width: {width}%">{cell_html}</td>'
    drug_html += '</tr>'

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 11px;
            line-height: 1.3;
            background: white;
            padding: 10px;
        }}

        .title {{
            text-align: center;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #1a5f1a;
        }}

        .main-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        .main-table th,
        .main-table td {{
            border: 1px solid #000;
            padding: 6px 8px;
            vertical-align: top;
            text-align: left;
        }}

        .header-row th {{
            background-color: #c5e0b4;
            font-weight: bold;
            text-align: center;
            font-size: 12px;
        }}

        .drug-row td:first-child {{
            font-weight: bold;
            background-color: #e8f5e9;
        }}

        .nested-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 5px 0;
            font-size: 10px;
        }}

        .nested-table td {{
            border: 1px solid #666;
            padding: 3px 5px;
            text-align: center;
        }}

        .nested-table tr:first-child td {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}

        p {{
            margin: 3px 0;
        }}

        strong {{
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="title">Hướng dẫn hiệu chỉnh liều kháng sinh, kháng nấm, kháng virus trên bệnh nhân người lớn suy giảm chức năng thận</div>
    <table class="main-table">
        {header_html}
        {drug_html}
    </table>
</body>
</html>'''
    return html


def render_html_to_png(html: str, output_path: Path, browser, scale: int = 3) -> None:
    """Render HTML to PNG using Playwright with high DPI scaling.

    Args:
        html: HTML content to render
        output_path: Output PNG file path
        browser: Playwright browser instance
        scale: Device scale factor for high-resolution output (default 3x)
    """
    # Create page with high DPI scaling for crisp text
    page = browser.new_page(
        viewport={"width": 1400, "height": 800},
        device_scale_factor=scale,  # 3x scale for high quality
    )
    page.set_content(html, wait_until="networkidle")

    # Take full page screenshot at high resolution
    page.screenshot(
        path=str(output_path),
        full_page=True,
        type="png",
    )
    page.close()


def main() -> None:
    """Generate PNG images for all drugs."""
    print("Generating drug images from DOCX...")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load DOCX
    doc = Document(DOCX_FILE)
    main_table = doc.tables[0]

    # Extract header row
    header_row = main_table.rows[0]
    header_cells = [cell.text.strip().replace('\n', ' ') for cell in header_row.cells]
    print(f"Header: {header_cells}")

    # Count drugs
    drug_count = len(main_table.rows) - 1
    print(f"Found {drug_count} drugs to process")

    # Start Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()

        success_count = 0
        for row_idx, row in enumerate(main_table.rows[1:], start=1):
            drug_name = row.cells[0].text.strip()
            print(f"\n[{row_idx}/{drug_count}] Processing: {drug_name}...")

            try:
                # Extract cell HTML for each column
                drug_cells = []
                for cell in row.cells:
                    cell_html = extract_cell_html(cell)
                    drug_cells.append(cell_html)

                # Generate HTML
                html = generate_html_for_drug(drug_name, header_cells, drug_cells)

                # Generate filename and render
                safe_name = sanitize_filename(drug_name)
                output_path = OUTPUT_DIR / f"{safe_name}.png"

                render_html_to_png(html, output_path, browser)
                print(f"  Created: {output_path.name}")
                success_count += 1

            except Exception as e:
                print(f"  Error: {e}")

        browser.close()

    print(f"\nDone! Created {success_count}/{drug_count} PNG images in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
