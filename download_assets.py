#!/usr/bin/env python3
"""Download all remote assets referenced in index.html into ./assets and rewrite paths."""

from __future__ import annotations

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
ASSETS_DIR = ROOT / "assets"

URL_RE = re.compile(r"https://[^\s\"')]+")


def local_name(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = unquote(parsed.path).lstrip("/")
    if not path or path.endswith("/"):
        path = path + "file"
    # Keep query image ids for unsplash
    if parsed.query:
        digest = hashlib.md5(parsed.query.encode("utf-8")).hexdigest()[:8]
        stem = Path(path).stem
        suffix = Path(path).suffix or ".jpg"
        path = f"{Path(path).parent.as_posix()}/{stem}-{digest}{suffix}".lstrip("./")
    # Flatten nested folders under assets/<host>/...
    safe = re.sub(r"[^a-zA-Z0-9._/-]+", "-", f"{host}/{path}")
    return safe


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"SKIP  {url}")
        return
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AdarshAssetMirror/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    print(f"OK    {url} -> {dest.relative_to(ROOT)}")


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    urls = sorted(set(URL_RE.findall(html)))
    # Only download image-like / asset URLs
    asset_urls = [
        u
        for u in urls
        if any(
            x in u.lower()
            for x in (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".gif",
                ".svg",
                "images.unsplash.com",
                "/assets/",
            )
        )
    ]

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}

    for url in asset_urls:
        rel = local_name(url)
        dest = ASSETS_DIR / rel
        try:
            download(url, dest)
            mapping[url] = "./assets/" + rel.replace("\\", "/")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {url} ({exc})")

    updated = html
    for remote, local in sorted(mapping.items(), key=lambda x: -len(x[0])):
        updated = updated.replace(remote, local)

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"\nDownloaded {len(mapping)}/{len(asset_urls)} assets into {ASSETS_DIR}")
    print("Updated index.html to use local paths.")


if __name__ == "__main__":
    main()
