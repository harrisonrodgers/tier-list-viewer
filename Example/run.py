#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import pathlib
import webbrowser
import re

NATSORT = lambda p: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', p.name.casefold())]

ROOT = pathlib.Path(__file__).parent.resolve()

CTYPE_MAP = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".avif": "image/avif",
}

HTML = """
<!DOCTYPE html>
<html lang="en">
    <title>Tier List: """ + ROOT.name + """</title>
    <meta charset="UTF-8">
    <meta name="description" content="Tier List">
    <meta name="viewport" content="width=device-width">
    <head>
        <style>
            body {
                margin: 0;
            }
            section {
                display: block;
                font-size: 0;
            }
            img {
                display: inline-block;
                width: 150px;
                height: 150px;
                margin-left: 1px;
                margin-bottom: 1px;
            }
        </style>
    </head>
    <body>
"""
for subdir in sorted(ROOT.iterdir()):
    if subdir.is_dir() and not subdir.name.startswith("."):
        HTML += "        <section>\n"
        for img in sorted((img for ext in CTYPE_MAP.keys() for img in subdir.glob(f"*{ext}")), key=NATSORT):
            HTML += "            "
            if img.stem != "000":
                HTML += f'<a href="/{subdir.name}/{img.name}" title="/{subdir.name}/{img.name}"/>'
            HTML += f'<img src="/{subdir.name}/{img.name}"/>'
            if img.stem != "000":
                HTML += "</a>"
            HTML += "\n"
        HTML += "        </section>\n"
HTML += """     </body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        target = ROOT / self.path.lstrip("/")
        if target.is_file():
            self.send_response(200)
            self.send_header("Content-Type", CTYPE_MAP.get(target.suffix.lower(), "application/octet-stream"))
            self.end_headers()
            self.wfile.write(target.read_bytes())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            self.send_error(404)


print("Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...")
webbrowser.open("http://localhost:8000")
try:
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
except KeyboardInterrupt:
    ...
