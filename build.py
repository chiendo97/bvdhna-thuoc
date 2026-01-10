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


def get_available_drugs() -> list[dict]:
    """Scan drugs directory for available PNG files and build entries."""
    if not DRUGS_DIR.exists():
        return []

    # Get all PNG files
    png_files = {f.stem: f.name for f in DRUGS_DIR.glob("*.png")}
    return png_files


def load_page_names() -> dict[str, list[int]]:
    """Load page names from JSON file."""
    if NAMES_FILE.exists():
        with open(NAMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_html(entries: list[dict]) -> str:
    """Generate static HTML with PNG image viewer."""
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
            background: #525659;
        }}

        .header {{
            padding: 0.75rem 1rem;
            background: #323639;
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-input {{
            flex: 1;
            min-width: 200px;
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            border: none;
            border-radius: 4px;
            background: #525659;
            color: #fff;
            outline: none;
        }}

        .search-input::placeholder {{
            color: #aaa;
        }}

        .search-input:focus {{
            background: #626669;
        }}

        .drug-select {{
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            min-width: 250px;
            border: none;
            border-radius: 4px;
            background: #525659;
            color: #fff;
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
            background: #525659;
            color: #fff;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .nav-btn:hover {{
            background: #626669;
        }}

        .nav-btn:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}

        .entry-info {{
            font-size: 0.85rem;
            color: #aaa;
            white-space: nowrap;
        }}

        .zoom-controls {{
            display: flex;
            gap: 0.25rem;
            align-items: center;
        }}

        .zoom-btn {{
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            border: none;
            border-radius: 4px;
            background: #525659;
            color: #fff;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .zoom-btn:hover {{
            background: #626669;
        }}

        .zoom-level {{
            color: #aaa;
            font-size: 0.85rem;
            min-width: 50px;
            text-align: center;
        }}

        .viewer {{
            flex: 1;
            overflow: auto;
            display: flex;
            justify-content: center;
            padding: 20px;
            background: #525659;
        }}

        .viewer img {{
            max-width: 100%;
            height: auto;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
            background: white;
            transform-origin: top center;
        }}

        .loading {{
            color: #aaa;
            font-size: 1.2rem;
            padding: 2rem;
            text-align: center;
        }}

        .no-results {{
            color: #aaa;
            font-size: 1.2rem;
            padding: 2rem;
            text-align: center;
        }}

        .error {{
            color: #f88;
            font-size: 1.2rem;
            padding: 2rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <input type="text" class="search-input" id="search" placeholder="Tìm kiếm thuốc...">
        <select class="drug-select" id="drugSelect">
{options_html}        </select>
        <div class="nav-buttons">
            <button class="nav-btn" id="prevBtn" title="Trước">&larr; Trước</button>
            <button class="nav-btn" id="nextBtn" title="Sau">Sau &rarr;</button>
        </div>
        <div class="zoom-controls">
            <button class="zoom-btn" id="zoomOut" title="Thu nhỏ">-</button>
            <span class="zoom-level" id="zoomLevel">100%</span>
            <button class="zoom-btn" id="zoomIn" title="Phóng to">+</button>
            <button class="zoom-btn" id="zoomFit" title="Vừa màn hình">Fit</button>
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
        const zoomInBtn = document.getElementById('zoomIn');
        const zoomOutBtn = document.getElementById('zoomOut');
        const zoomFitBtn = document.getElementById('zoomFit');
        const zoomLevelSpan = document.getElementById('zoomLevel');

        // Embedded entries data
        const allEntries = {entries_json};

        let currentEntries = [...allEntries];
        let currentScale = 1.0;
        let currentImage = null;

        function updateZoomDisplay() {{
            zoomLevelSpan.textContent = Math.round(currentScale * 100) + '%';
        }}

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

        function applyZoom() {{
            if (currentImage) {{
                currentImage.style.transform = `scale(${{currentScale}})`;
            }}
        }}

        function updateViewer() {{
            const selectedIdx = drugSelect.selectedIndex;
            if (selectedIdx < 0 || currentEntries.length === 0) {{
                viewerContainer.innerHTML = '<div class="no-results">Không tìm thấy kết quả</div>';
                updateEntryInfo();
                return;
            }}

            viewerContainer.innerHTML = '<div class="loading">Đang tải...</div>';

            const entry = currentEntries[selectedIdx];
            const img = document.createElement('img');
            img.src = 'drugs/' + entry.file;
            img.alt = entry.name;

            img.onload = function() {{
                viewerContainer.innerHTML = '';
                viewerContainer.appendChild(img);
                currentImage = img;
                applyZoom();
            }};

            img.onerror = function() {{
                viewerContainer.innerHTML = '<div class="error">Không thể tải hình ảnh: ' + entry.file + '</div>';
                currentImage = null;
            }};

            updateEntryInfo();
        }}

        drugSelect.addEventListener('change', () => {{
            currentScale = 1.0;
            updateZoomDisplay();
            updateViewer();
        }});

        prevBtn.addEventListener('click', () => {{
            if (drugSelect.selectedIndex > 0) {{
                drugSelect.selectedIndex--;
                currentScale = 1.0;
                updateZoomDisplay();
                updateViewer();
            }}
        }});

        nextBtn.addEventListener('click', () => {{
            if (drugSelect.selectedIndex < drugSelect.options.length - 1) {{
                drugSelect.selectedIndex++;
                currentScale = 1.0;
                updateZoomDisplay();
                updateViewer();
            }}
        }});

        zoomInBtn.addEventListener('click', () => {{
            currentScale = Math.min(currentScale + 0.25, 4);
            updateZoomDisplay();
            applyZoom();
        }});

        zoomOutBtn.addEventListener('click', () => {{
            currentScale = Math.max(currentScale - 0.25, 0.25);
            updateZoomDisplay();
            applyZoom();
        }});

        zoomFitBtn.addEventListener('click', () => {{
            currentScale = 1.0;
            updateZoomDisplay();
            applyZoom();
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

            currentScale = 1.0;
            updateZoomDisplay();
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
            }} else if (e.key === '+' || e.key === '=') {{
                zoomInBtn.click();
            }} else if (e.key === '-') {{
                zoomOutBtn.click();
            }}
        }});

        // Initialize
        updateZoomDisplay();
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
        print("Run 'uv run python generate_drug_images.py' first to generate PNG images.")
        return

    # 2. Load page names to get drug order and names
    names = load_page_names()
    if not names:
        print("Error: No page_names.json found.")
        return

    # 3. Build entries list from page_names.json, matching to PNG files
    png_files = get_available_drugs()
    entries = []

    for name, pages in names.items():
        safe_name = sanitize_filename(name)
        if safe_name in png_files:
            entries.append({
                "name": name,
                "file": png_files[safe_name],
            })
        else:
            print(f"  Warning: No PNG found for '{name}' (expected {safe_name}.png)")

    # Sort by original page order
    name_to_pages = {name: pages[0] for name, pages in names.items()}
    entries.sort(key=lambda x: name_to_pages.get(x["name"], 999))

    print(f"  Found {len(entries)} drug images in {DRUGS_DIR}/")

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
