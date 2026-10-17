#!/usr/bin/env python3
import html
import re
import string
import urllib.parse
from pathlib import Path
from string.templatelib import Interpolation, Template

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

ROOT = Path(__file__).parent.resolve()

IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".avif"}

IMAGE_DEFAULT_PCT = "8.2"

# Page shell, a $-placeholder string.Template so the CSS and JS braces need no escaping
PAGE = string.Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Tier List">
    <meta name="viewport" content="width=device-width">
    <title>Tier List$title</title>
    <style>
        body {
            margin: 0;
            font-size: 0;
        }
        img {
            width: var(--pct, $pct%);
            aspect-ratio: 1;
            object-fit: cover;
            vertical-align: top;
            margin-left: 1px;
            margin-bottom: 1px;
        }
    </style>
</head>
<body>
    <button onclick="zoom(step)">Zoom In</button>
    <button onclick="zoom(-step)">Zoom Out</button>
    <button onclick="toggleRows()">Toggle Rows</button>
    <br>
$body
    <script>
        let imgPercent = $pct;
        const step = 0.5;

        function zoom(delta) {
            imgPercent = Math.max(step, imgPercent + delta);
            document.body.style.setProperty("--pct", imgPercent + "%");
        }

        function toggleRows() {
            document.querySelectorAll("section").forEach(section => {
                section.style.display = section.style.display == "inline" ? "block" : "inline";
            });
        }
    </script>
</body>
</html>
""")


def h(template: Template) -> str:
    """Render a t-string as HTML: values are escaped, nested t-strings are rendered as-is."""
    parts = []
    for part in template:
        if isinstance(part, Interpolation):
            part = h(part.value) if isinstance(part.value, Template) else html.escape(str(part.value))
        parts.append(part)
    return "".join(parts)


def natsort(p: Path) -> list[int | str]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name.casefold())]


def hidden(name: str) -> bool:
    return name.startswith(".")


def folders(folder: Path) -> list[Path]:
    return sorted((p for p in folder.iterdir() if p.info.is_dir() and not hidden(p.name)), key=natsort)


def images(folder: Path) -> list[Path]:
    return sorted(
        (p for p in folder.iterdir() if p.info.is_file() and not hidden(p.name) and p.suffix.lower() in IMAGE_EXTS),
        key=natsort,
    )


def url(*parts: str) -> str:
    return "/" + "/".join(urllib.parse.quote(p) for p in parts)


def img_tag(src: str, name: str) -> Template:
    return t'<img src="{src}" alt="{name}" loading="lazy">'


def render(title: str, body: list[str]) -> HTMLResponse:
    return HTMLResponse(PAGE.substitute(title=title, body="".join(body), pct=IMAGE_DEFAULT_PCT))


def index(request: Request) -> HTMLResponse:
    body = []
    for tierlist in folders(ROOT):
        if covers := images(tierlist):  # A tier list needs a cover image to be listed
            cover = img_tag(url(tierlist.name, covers[0].name), tierlist.name)
            body.append(h(t'<a href="{url(tierlist.name)}/" title="{tierlist.name}">{cover}</a>'))
    return render("", body)


def tierlist_page(tierlist: Path) -> HTMLResponse:
    body = []
    for tier in folders(tierlist):
        body.append("    <section>\n")
        for img in images(tier):
            src = url(tierlist.name, tier.name, img.name)
            tag = img_tag(src, img.name)
            if img.stem != "000":  # 000 is the tier label, not a link
                tag = t'<a href="{src}" title="/{tierlist.name}/{tier.name}/{img.name}">{tag}</a>'
            body.append(h(t"        {tag}\n"))
        body.append("    </section>\n")
    return render(h(t": {tierlist.name}"), body)


def custom_router(request: Request) -> Response:
    path = request.path_params["path"]
    target = (ROOT / path).resolve()

    # Stay inside ROOT, and hide dotfiles and dot-folders (e.g. .git/ and .DS_Store)
    if not target.is_relative_to(ROOT) or any(hidden(part) for part in target.relative_to(ROOT).parts):
        raise HTTPException(404)

    # Only top-level folders are tier lists. Enforce trailing slash on directory as per RFC 3986 §5.2
    if target.is_dir() and target.parent == ROOT:
        return tierlist_page(target) if path.endswith("/") else RedirectResponse(url(target.name) + "/")

    # Only serve images, never code, archives or other files. Block scripts embedded in SVGs from running on this site
    if target.is_file() and target.suffix.lower() in IMAGE_EXTS:
        return FileResponse(target, headers={"Content-Security-Policy": "script-src 'none'"})

    raise HTTPException(404)


app = Starlette(routes=[Route("/", index), Route("/{path:path}", custom_router)])
