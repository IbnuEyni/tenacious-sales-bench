#!/usr/bin/env python3
"""Convert memo.md to exactly 2-page PDF."""
import markdown
from weasyprint import HTML, CSS
from pathlib import Path
import re
import sys

# Accept optional input path
md_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("memo.md")
if not md_path.exists():
    # Try publication/ subfolder
    md_path = Path("publication/memo.md")

md_content = md_path.read_text()

# Fix image paths to absolute
reports_dir = md_path.parent.absolute()
md_content = re.sub(
    r'!\[([^\]]*)\]\(([^)]+\.png)\)',
    lambda m: f'![{m.group(1)}](file://{reports_dir}/{m.group(2)})',
    md_content
)

html_content = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'codehilite']
)

styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: A4;
            margin: 12mm 14mm 12mm 14mm;
        }}
        body {{
            font-family: Arial, sans-serif;
            font-size: 8.5pt;
            line-height: 1.35;
            margin: 0;
            padding: 0;
            color: #222;
        }}
        h1 {{
            font-size: 11pt;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 3px;
            margin: 0 0 6px 0;
        }}
        h2 {{
            font-size: 9.5pt;
            color: #34495e;
            border-bottom: 1px solid #aaa;
            padding-bottom: 2px;
            margin: 8px 0 4px 0;
        }}
        h3 {{
            font-size: 8.5pt;
            color: #555;
            margin: 6px 0 2px 0;
        }}
        p {{
            margin: 3px 0;
        }}
        ul, ol {{
            margin: 2px 0 2px 16px;
            padding: 0;
        }}
        li {{
            margin: 1px 0;
        }}
        code {{
            background: #f4f4f4;
            padding: 1px 3px;
            border-radius: 2px;
            font-family: monospace;
            font-size: 7.5pt;
        }}
        pre {{
            background: #f4f4f4;
            padding: 6px;
            border-radius: 3px;
            font-size: 7pt;
            margin: 4px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 4px 0;
            font-size: 7.5pt;
            table-layout: fixed;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 3px 5px;
            text-align: left;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        th {{
            background: #3498db;
            color: white;
            font-size: 7.5pt;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        blockquote {{
            border-left: 3px solid #3498db;
            padding-left: 8px;
            margin: 4px 0;
            color: #555;
            font-size: 8pt;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 6px 0;
        }}
        strong {{
            color: #2c3e50;
        }}
        /* Force page break between Page 1 and Page 2 */
        h2:contains("Page 2"),
        h2[id*="page-2"],
        h2[id*="skeptic"] {{
            page-break-before: always;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""

pdf_path = md_path.parent / "memo.pdf"
HTML(string=styled_html).write_pdf(str(pdf_path))

print(f"PDF generated: {pdf_path}")
print(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")
print("Note: Open the PDF and verify it is exactly 2 pages.")
print("If still >2 pages, reduce font-size in @page or trim memo content further.")
