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
    """Generate static HTML with PDF.js viewer."""
    entries_json = json.dumps(entries, ensure_ascii=False, indent=2)

    # Generate options HTML
    options_html = ""
    for i, entry in enumerate(entries):
        name = entry["name"]
        pages_str = ", ".join(str(p) for p in entry["pages"])
        options_html += f'            <option value="{i}" data-name="{name.lower()}">{name} ({pages_str})</option>\n'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Viewer</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.mjs" type="module"></script>
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

        .page-select {{
            padding: 0.5rem 0.75rem;
            font-size: 0.9rem;
            min-width: 200px;
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

        .page-info {{
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
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            gap: 10px;
        }}

        .viewer canvas {{
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
            background: white;
        }}

        .loading {{
            color: #aaa;
            font-size: 1.2rem;
            padding: 2rem;
        }}

        .no-results {{
            color: #aaa;
            font-size: 1.2rem;
            padding: 2rem;
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
        <div class="zoom-controls">
            <button class="zoom-btn" id="zoomOut" title="Zoom out">-</button>
            <span class="zoom-level" id="zoomLevel">100%</span>
            <button class="zoom-btn" id="zoomIn" title="Zoom in">+</button>
            <button class="zoom-btn" id="zoomFit" title="Fit width">Fit</button>
        </div>
        <span class="page-info" id="pageInfo"></span>
    </div>
    <div class="viewer" id="viewerContainer">
        <div class="loading">Loading PDF...</div>
    </div>

    <script type="module">
        // Import PDF.js
        const pdfjsLib = await import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.mjs');
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.mjs';

        const search = document.getElementById('search');
        const pageSelect = document.getElementById('pageSelect');
        const viewerContainer = document.getElementById('viewerContainer');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageInfo = document.getElementById('pageInfo');
        const zoomIn = document.getElementById('zoomIn');
        const zoomOut = document.getElementById('zoomOut');
        const zoomFit = document.getElementById('zoomFit');
        const zoomLevel = document.getElementById('zoomLevel');

        // Embedded entries data
        const allEntries = {entries_json};

        let currentEntries = [...allEntries];
        let currentScale = 1.5;
        let loadedPdfs = [];

        function updateZoomDisplay() {{
            zoomLevel.textContent = Math.round(currentScale * 100 / 1.5) + '%';
        }}

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

        async function renderPage(pdf, pageNum, container) {{
            const page = await pdf.getPage(pageNum);
            const viewport = page.getViewport({{ scale: currentScale }});

            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            await page.render({{
                canvasContext: context,
                viewport: viewport
            }}).promise;

            container.appendChild(canvas);
        }}

        async function loadAndRenderPdf(url, container) {{
            try {{
                const pdf = await pdfjsLib.getDocument(url).promise;
                loadedPdfs.push(pdf);

                // Render all pages of this PDF
                for (let i = 1; i <= pdf.numPages; i++) {{
                    await renderPage(pdf, i, container);
                }}
            }} catch (error) {{
                console.error('Error loading PDF:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'no-results';
                errorDiv.textContent = 'Error loading PDF';
                container.appendChild(errorDiv);
            }}
        }}

        async function updateViewer() {{
            const selectedIdx = pageSelect.selectedIndex;
            if (selectedIdx < 0 || currentEntries.length === 0) {{
                viewerContainer.innerHTML = '<div class="no-results">No matching entries found</div>';
                updatePageInfo();
                return;
            }}

            viewerContainer.innerHTML = '<div class="loading">Loading PDF...</div>';
            loadedPdfs = [];

            const entry = currentEntries[selectedIdx];
            viewerContainer.innerHTML = '';

            // Load and render each PDF file
            for (const file of entry.files) {{
                await loadAndRenderPdf('pages/' + file, viewerContainer);
            }}

            updatePageInfo();
        }}

        async function rerender() {{
            const selectedIdx = pageSelect.selectedIndex;
            if (selectedIdx < 0 || currentEntries.length === 0) return;

            viewerContainer.innerHTML = '';

            for (const pdf of loadedPdfs) {{
                for (let i = 1; i <= pdf.numPages; i++) {{
                    await renderPage(pdf, i, viewerContainer);
                }}
            }}
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

        zoomIn.addEventListener('click', () => {{
            currentScale = Math.min(currentScale + 0.25, 4);
            updateZoomDisplay();
            rerender();
        }});

        zoomOut.addEventListener('click', () => {{
            currentScale = Math.max(currentScale - 0.25, 0.5);
            updateZoomDisplay();
            rerender();
        }});

        zoomFit.addEventListener('click', () => {{
            // Calculate scale to fit container width
            const containerWidth = viewerContainer.clientWidth - 40; // padding
            if (loadedPdfs.length > 0) {{
                loadedPdfs[0].getPage(1).then(page => {{
                    const viewport = page.getViewport({{ scale: 1 }});
                    currentScale = containerWidth / viewport.width;
                    updateZoomDisplay();
                    rerender();
                }});
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
            if (e.target === search) return;

            if (e.key === 'ArrowLeft') {{
                prevBtn.click();
            }} else if (e.key === 'ArrowRight') {{
                nextBtn.click();
            }} else if (e.key === '+' || e.key === '=') {{
                zoomIn.click();
            }} else if (e.key === '-') {{
                zoomOut.click();
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
