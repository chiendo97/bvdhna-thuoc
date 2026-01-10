#!/usr/bin/env python3
"""Build script to generate static site for GitHub Pages."""

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
PAGES_DIR = DOCS_DIR / "pages"
SOURCE_PDF = BASE_DIR / "data.pdf"
NAMES_FILE = BASE_DIR / "page_names.json"


def split_pdf() -> int:
    """Split PDF into individual pages. Returns page count."""
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(SOURCE_PDF)

    for i, page in enumerate(reader.pages, 1):
        writer = PdfWriter()
        writer.add_page(page)
        with open(PAGES_DIR / f"page_{i}.pdf", "wb") as f:
            writer.write(f)

    return len(reader.pages)


def load_page_names() -> dict[str, list[int]]:
    """Load page names from JSON file."""
    if NAMES_FILE.exists():
        with open(NAMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_html(entries: list[dict]) -> str:
    """Generate static HTML with embedded entries data."""
    entries_json = json.dumps(entries, ensure_ascii=False, indent=2)

    # Generate options HTML
    options_html = ""
    for i, entry in enumerate(entries):
        name = entry["name"]
        pages_str = ", ".join(str(p) for p in entry["pages"])
        options_html += f'            <option value="{i}" data-name="{name.lower()}">{name} ({pages_str})</option>\n'

    # Generate initial embed
    if entries:
        first_file = entries[0]["files"][0]
        initial_embed = f'<embed src="pages/{first_file}" type="application/pdf">'
    else:
        initial_embed = '<div class="no-results">No PDF pages available</div>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: #f0f0f0;
        }}

        .header {{
            padding: 1rem;
            background: #ffffff;
            border-bottom: 1px solid #ddd;
            display: flex;
            gap: 1rem;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .search-input {{
            flex: 1;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 6px;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-input:focus {{
            border-color: #0066cc;
        }}

        .page-select {{
            padding: 0.75rem 1rem;
            font-size: 1rem;
            min-width: 250px;
            border: 1px solid #ccc;
            border-radius: 6px;
            background: white;
            cursor: pointer;
        }}

        .nav-buttons {{
            display: flex;
            gap: 0.5rem;
        }}

        .nav-btn {{
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .nav-btn:hover {{
            background: #f5f5f5;
        }}

        .nav-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .page-info {{
            font-size: 0.9rem;
            color: #666;
            white-space: nowrap;
        }}

        .viewer {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 4px;
            background: #333;
            overflow-y: auto;
        }}

        .viewer.single-page embed {{
            width: 100%;
            height: 100%;
            min-height: 100%;
            border: none;
        }}

        .viewer.dual-page embed {{
            width: 100%;
            height: 100vh;
            min-height: 100vh;
            border: none;
            flex-shrink: 0;
        }}

        .no-results {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 1.2rem;
            background: #333;
        }}
    </style>
</head>
<body>
    <div class="header">
        <input type="text" class="search-input" id="search" placeholder="Search by name...">
        <select class="page-select" id="pageSelect">
{options_html}        </select>
        <div class="nav-buttons">
            <button class="nav-btn" id="prevBtn" title="Previous">&larr; Prev</button>
            <button class="nav-btn" id="nextBtn" title="Next">Next &rarr;</button>
        </div>
        <span class="page-info" id="pageInfo"></span>
    </div>
    <div class="viewer single-page" id="viewerContainer">
        {initial_embed}
    </div>

    <script>
        const search = document.getElementById('search');
        const pageSelect = document.getElementById('pageSelect');
        const viewerContainer = document.getElementById('viewerContainer');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageInfo = document.getElementById('pageInfo');

        // Embedded entries data
        const allEntries = {entries_json};

        let currentEntries = [...allEntries];

        function updatePageInfo() {{
            const currentIndex = pageSelect.selectedIndex;
            const total = pageSelect.options.length;
            if (total > 0) {{
                pageInfo.textContent = `Entry ${{currentIndex + 1}} of ${{total}}`;
            }} else {{
                pageInfo.textContent = '';
            }}
            prevBtn.disabled = currentIndex <= 0;
            nextBtn.disabled = currentIndex >= total - 1;
        }}

        function updateViewer() {{
            const selectedIdx = pageSelect.selectedIndex;
            if (selectedIdx < 0 || currentEntries.length === 0) {{
                viewerContainer.innerHTML = '<div class="no-results">No matching entries found</div>';
                viewerContainer.className = 'viewer';
                updatePageInfo();
                return;
            }}

            const entry = currentEntries[selectedIdx];
            viewerContainer.innerHTML = '';

            // Set class based on page count
            viewerContainer.className = entry.files.length === 1 ? 'viewer single-page' : 'viewer dual-page';

            // Create embed for each page
            entry.files.forEach(file => {{
                const embed = document.createElement('embed');
                embed.src = 'pages/' + file;
                embed.type = 'application/pdf';
                viewerContainer.appendChild(embed);
            }});

            updatePageInfo();
        }}

        pageSelect.addEventListener('change', updateViewer);

        prevBtn.addEventListener('click', () => {{
            if (pageSelect.selectedIndex > 0) {{
                pageSelect.selectedIndex--;
                updateViewer();
            }}
        }});

        nextBtn.addEventListener('click', () => {{
            if (pageSelect.selectedIndex < pageSelect.options.length - 1) {{
                pageSelect.selectedIndex++;
                updateViewer();
            }}
        }});

        // Debounce function for search
        function debounce(func, wait) {{
            let timeout;
            return function executedFunction(...args) {{
                const later = () => {{
                    clearTimeout(timeout);
                    func(...args);
                }};
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            }};
        }}

        const handleSearch = debounce(() => {{
            const query = search.value.toLowerCase().trim();

            // Filter entries
            currentEntries = allEntries.filter(entry => entry.name.toLowerCase().includes(query));

            // Rebuild select
            pageSelect.innerHTML = '';
            currentEntries.forEach((entry, idx) => {{
                const option = document.createElement('option');
                option.value = idx;
                option.dataset.name = entry.name.toLowerCase();
                option.textContent = `${{entry.name}} (${{entry.pages.join(', ')}})`;
                pageSelect.appendChild(option);
            }});

            updateViewer();
        }}, 150);

        search.addEventListener('input', handleSearch);

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.target === search) return; // Don't interfere with search input

            if (e.key === 'ArrowLeft') {{
                prevBtn.click();
            }} else if (e.key === 'ArrowRight') {{
                nextBtn.click();
            }}
        }});

        // Initialize
        updatePageInfo();
    </script>
</body>
</html>'''

    return html


def main() -> None:
    """Build the static site."""
    print("Building static site...")

    # 1. Split PDF
    print(f"Splitting {SOURCE_PDF}...")
    page_count = split_pdf()
    print(f"  Created {page_count} page PDFs in {PAGES_DIR}/")

    # 2. Load page names (or generate defaults)
    names = load_page_names()
    if not names:
        print("No page_names.json found, generating defaults...")
        names = {f"Page {i}": [i] for i in range(1, page_count + 1)}

    # 3. Build entries list
    entries = [
        {"name": name, "pages": pages, "files": [f"page_{p}.pdf" for p in pages]}
        for name, pages in names.items()
    ]
    entries.sort(key=lambda x: x["pages"][0])
    print(f"  Loaded {len(entries)} entries from page_names.json")

    # 4. Generate index.html
    html = generate_html(entries)
    index_path = DOCS_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Generated {index_path}")

    print(f"\nDone! Static site built in {DOCS_DIR}/")
    print(f"To test locally: cd {DOCS_DIR} && python -m http.server 8000")


if __name__ == "__main__":
    main()
