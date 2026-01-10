#!/usr/bin/env python3
"""Build script to generate static site for GitHub Pages."""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
DRUGS_DIR = DOCS_DIR / "drugs"
NAMES_FILE = BASE_DIR / "page_names.json"


def sanitize_filename(name: str) -> str:
    """Convert drug name to a safe filename (must match generate_drug_images.py)."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.replace(" ", "_")
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def get_available_drugs() -> dict[str, str]:
    """Scan drugs directory for available HTML files and build entries."""
    if not DRUGS_DIR.exists():
        return {}

    # Get all HTML files
    html_files = {f.stem: f.name for f in DRUGS_DIR.glob("*.html")}
    return html_files


def load_page_names() -> dict[str, list[int]]:
    """Load page names from JSON file."""
    if NAMES_FILE.exists():
        with open(NAMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_html(entries: list[dict]) -> str:
    """Generate static HTML with responsive drug viewer using iframes."""
    entries_json = json.dumps(entries, ensure_ascii=False, indent=2)

    # Generate options HTML
    options_html = ""
    for i, entry in enumerate(entries):
        name = entry["name"]
        options_html += f'            <option value="{i}" data-name="{name.lower()}">{name}</option>\n'

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hướng dẫn hiệu chỉnh liều kháng sinh</title>
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
            background: #f5f5f5;
        }}

        .header {{
            padding: 0.75rem 1rem;
            background: #2e7d32;
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        .search-input {{
            flex: 1;
            min-width: 150px;
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            border: none;
            border-radius: 4px;
            background: rgba(255,255,255,0.9);
            color: #333;
            outline: none;
        }}

        .search-input::placeholder {{
            color: #666;
        }}

        .search-input:focus {{
            background: white;
            box-shadow: 0 0 0 2px rgba(255,255,255,0.5);
        }}

        .drug-select {{
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            min-width: 200px;
            border: none;
            border-radius: 4px;
            background: rgba(255,255,255,0.9);
            color: #333;
            cursor: pointer;
        }}

        .nav-buttons {{
            display: flex;
            gap: 0.25rem;
        }}

        .nav-btn {{
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            border: none;
            border-radius: 4px;
            background: rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .nav-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .nav-btn:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}

        .entry-info {{
            font-size: 0.85rem;
            color: rgba(255,255,255,0.9);
            white-space: nowrap;
        }}

        .viewer {{
            flex: 1;
            overflow: auto;
            background: #f5f5f5;
        }}

        .viewer iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}

        .loading, .no-results, .error {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            font-size: 1.1rem;
            color: #666;
        }}

        .error {{
            color: #c62828;
        }}

        /* Mobile adjustments */
        @media (max-width: 768px) {{
            .header {{
                padding: 0.5rem;
                gap: 0.5rem;
            }}

            .search-input {{
                min-width: 120px;
                font-size: 0.85rem;
                padding: 0.4rem 0.6rem;
            }}

            .drug-select {{
                min-width: 150px;
                font-size: 0.85rem;
                padding: 0.4rem 0.6rem;
            }}

            .nav-btn {{
                padding: 0.4rem 0.6rem;
                font-size: 0.85rem;
            }}

            .entry-info {{
                font-size: 0.8rem;
            }}
        }}

        @media (max-width: 480px) {{
            .header {{
                flex-direction: column;
                align-items: stretch;
            }}

            .search-input, .drug-select {{
                width: 100%;
                min-width: unset;
            }}

            .nav-buttons {{
                justify-content: center;
            }}

            .entry-info {{
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <input type="text" class="search-input" id="search" placeholder="Tìm kiếm thuốc...">
        <select class="drug-select" id="drugSelect">
{options_html}        </select>
        <div class="nav-buttons">
            <button class="nav-btn" id="prevBtn" title="Trước">&larr;</button>
            <button class="nav-btn" id="nextBtn" title="Sau">&rarr;</button>
        </div>
        <span class="entry-info" id="entryInfo"></span>
    </div>
    <div class="viewer" id="viewerContainer">
        <div class="loading">Đang tải...</div>
    </div>

    <script>
        const search = document.getElementById('search');
        const drugSelect = document.getElementById('drugSelect');
        const viewerContainer = document.getElementById('viewerContainer');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const entryInfo = document.getElementById('entryInfo');

        // Embedded entries data
        const allEntries = {entries_json};

        let currentEntries = [...allEntries];

        function updateEntryInfo() {{
            const currentIndex = drugSelect.selectedIndex;
            const total = drugSelect.options.length;
            if (total > 0) {{
                entryInfo.textContent = `${{currentIndex + 1}} / ${{total}}`;
            }} else {{
                entryInfo.textContent = '';
            }}
            prevBtn.disabled = currentIndex <= 0;
            nextBtn.disabled = currentIndex >= total - 1;
        }}

        function updateViewer() {{
            const selectedIdx = drugSelect.selectedIndex;
            if (selectedIdx < 0 || currentEntries.length === 0) {{
                viewerContainer.innerHTML = '<div class="no-results">Không tìm thấy kết quả</div>';
                updateEntryInfo();
                return;
            }}

            const entry = currentEntries[selectedIdx];
            const iframe = document.createElement('iframe');
            iframe.src = 'drugs/' + entry.file;
            iframe.title = entry.name;

            viewerContainer.innerHTML = '';
            viewerContainer.appendChild(iframe);

            updateEntryInfo();
        }}

        drugSelect.addEventListener('change', updateViewer);

        prevBtn.addEventListener('click', () => {{
            if (drugSelect.selectedIndex > 0) {{
                drugSelect.selectedIndex--;
                updateViewer();
            }}
        }});

        nextBtn.addEventListener('click', () => {{
            if (drugSelect.selectedIndex < drugSelect.options.length - 1) {{
                drugSelect.selectedIndex++;
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
            drugSelect.innerHTML = '';
            currentEntries.forEach((entry, idx) => {{
                const option = document.createElement('option');
                option.value = idx;
                option.dataset.name = entry.name.toLowerCase();
                option.textContent = entry.name;
                drugSelect.appendChild(option);
            }});

            updateViewer();
        }}, 150);

        search.addEventListener('input', handleSearch);

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.target === search) return;

            if (e.key === 'ArrowLeft') {{
                prevBtn.click();
            }} else if (e.key === 'ArrowRight') {{
                nextBtn.click();
            }}
        }});

        // Initialize
        updateViewer();
    </script>
</body>
</html>'''

    return html


def main() -> None:
    """Build the static site."""
    print("Building static site...")

    # 1. Check drugs directory exists
    if not DRUGS_DIR.exists():
        print(f"Error: {DRUGS_DIR} does not exist.")
        print("Run 'uv run python generate_drug_images.py' first to generate HTML files.")
        return

    # 2. Load page names to get drug order and names
    names = load_page_names()
    if not names:
        print("Error: No page_names.json found.")
        return

    # 3. Build entries list from page_names.json, matching to HTML files
    html_files = get_available_drugs()
    entries = []

    for name, pages in names.items():
        safe_name = sanitize_filename(name)
        if safe_name in html_files:
            entries.append({
                "name": name,
                "file": html_files[safe_name],
            })
        else:
            print(f"  Warning: No HTML found for '{name}' (expected {safe_name}.html)")

    # Sort by original page order
    name_to_pages = {name: pages[0] for name, pages in names.items()}
    entries.sort(key=lambda x: name_to_pages.get(x["name"], 999))

    print(f"  Found {len(entries)} drug HTML files in {DRUGS_DIR}/")

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
