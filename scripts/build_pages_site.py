#!/usr/bin/env python3
#
# Copyright (c) 2024-2026, Ryan Galloway (ryan@rsgalloway.com)
#

"""Build a simple Jekyll-friendly docs site from repository markdown files."""

import argparse
import re
import shutil
from pathlib import Path

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def rewrite_links(content: str, page_kind: str) -> str:
    """Rewrite local markdown links for generated HTML output."""

    def replace(match: re.Match) -> str:
        label = match.group("label")
        target = match.group("target")

        if "://" in target or target.startswith("#") or target.startswith("mailto:"):
            return match.group(0)

        if not target.endswith(".md"):
            return match.group(0)

        if page_kind == "root":
            if target == "README.md":
                target = "docs/api/"
            elif target == "docs/index.md":
                target = "./"
            elif target.startswith("docs/"):
                target = target[:-3] + "/"
            else:
                target = "docs/" + target[:-3] + "/"
        else:
            if target == "README.md":
                target = "../docs/api/"
            elif target == "docs/index.md":
                target = "../"
            elif target.startswith("docs/"):
                target = target[len("docs/") : -3] + "/"
            else:
                target = target[:-3] + "/"

        return f"[{label}]({target})"

    return re.sub(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)", replace, content)


def rewrite_mermaid_blocks(content: str) -> str:
    """Convert fenced mermaid blocks into raw HTML containers for rendering."""

    def replace(match: re.Match) -> str:
        body = match.group(1).strip("\n")
        return '<div class="mermaid">\n' + body + "\n</div>"

    return MERMAID_BLOCK_RE.sub(replace, content)


def extract_title(content: str, fallback: str) -> str:
    """Extract the first markdown H1 title or use a fallback."""
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def wrap_markdown(content: str, title: str) -> str:
    """Add minimal Jekyll front matter to markdown content."""
    return f"---\nlayout: default\ntitle: {title}\n---\n\n{content}"


def write_markdown_page(src: Path, dst: Path, fallback_title: str, page_kind: str):
    """Copy a markdown file into the site tree with front matter and fixed links."""
    content = src.read_text(encoding="utf-8")
    title = extract_title(content, fallback_title)
    content = rewrite_links(content, page_kind=page_kind)
    content = rewrite_mermaid_blocks(content)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(wrap_markdown(content, title), encoding="utf-8")


def write_site_config(output_dir: Path):
    """Write a minimal Jekyll config file."""
    config = """title: envstack
description: Environment variable composition and activation layer
markdown: kramdown
permalink: pretty
"""
    (output_dir / "_config.yml").write_text(config, encoding="utf-8")


def write_layout(output_dir: Path):
    """Write a minimal dark layout for the generated docs site."""
    layout_dir = output_dir / "_layouts"
    layout_dir.mkdir(parents=True, exist_ok=True)
    template = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% if page.title %}{{ page.title }} | {% endif %}{{ site.title }}</title>
    <meta name="description" content="{{ site.description }}">
    <link rel="stylesheet" href="{{ '/assets/site.css' | relative_url }}">
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "dark" });
    </script>
  </head>
  <body>
    <div class="site-shell">
      <header class="site-header">
        <a class="site-brand" href="{{ '/' | relative_url }}">{{ site.title }}</a>
        <nav class="site-nav">
          <a href="{{ '/' | relative_url }}">Home</a>
          <a href="{{ '/docs/api/' | relative_url }}">API</a>
          <a href="{{ '/docs/design/' | relative_url }}">Design</a>
          <a href="{{ '/docs/examples/' | relative_url }}">Examples</a>
          <a href="{{ '/docs/secrets/' | relative_url }}">Secrets</a>
          <a href="{{ '/docs/faq/' | relative_url }}">FAQ</a>
          <a href="https://github.com/rsgalloway/envstack">GitHub</a>
          <a href="https://pypi.org/project/envstack/">PyPI</a>
        </nav>
      </header>
      <main class="site-main">
        {{ content }}
      </main>
    </div>
  </body>
</html>
"""
    (layout_dir / "default.html").write_text(template, encoding="utf-8")


def write_stylesheet(output_dir: Path):
    """Write a minimal dark stylesheet for the generated docs site."""
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    css = """:root {
  --bg: #0a0f19;
  --bg-elev: #111827;
  --panel: #131c2a;
  --border: #243244;
  --text: #ebf2ff;
  --muted: #aebbd1;
  --accent: #36c784;
  --accent-2: #2db7ff;
  --code: #0f1724;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background:
    radial-gradient(circle at top, rgba(45,183,255,0.10), transparent 30%),
    linear-gradient(180deg, #0a0f19 0%, #0b111b 100%);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.65;
}

a {
  color: var(--accent-2);
  text-decoration: none;
}

a:hover { color: #74d4ff; }

.site-shell {
  max-width: 980px;
  margin: 0 auto;
  padding: 32px 24px 72px;
}

.site-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 40px;
}

.site-brand {
  color: var(--text);
  font-size: 0.98rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.site-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.site-nav a {
  color: var(--muted);
  font-size: 0.9rem;
}

.site-nav a:hover { color: var(--text); }

.site-main h1:first-child,
.site-main p:first-child img {
  margin-top: 0;
}

h1, h2, h3 {
  color: var(--text);
  line-height: 1.15;
}

h1 {
  font-size: clamp(1.9rem, 5.4vw, 3.3rem);
  margin: 0 0 18px;
}

h2 {
  font-size: 1.6rem;
  margin-top: 46px;
  margin-bottom: 16px;
}

h3 {
  font-size: 1.08rem;
  margin-top: 28px;
  margin-bottom: 10px;
}

p, li {
  color: var(--muted);
  font-size: 0.98rem;
}

strong { color: var(--text); }

blockquote {
  margin: 24px 0;
  padding: 16px 20px;
  border-left: 4px solid var(--accent);
  background: rgba(19, 28, 42, 0.85);
  color: var(--text);
}

code, pre {
  font-family: "SFMono-Regular", SFMono-Regular, Consolas, "Liberation Mono", monospace;
}

code {
  padding: 0.15em 0.35em;
  border-radius: 0.35rem;
  background: rgba(255,255,255,0.06);
  color: var(--text);
}

pre {
  overflow-x: auto;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--code);
}

pre code {
  padding: 0;
  background: transparent;
}

hr {
  border: 0;
  border-top: 1px solid var(--border);
  margin: 40px 0;
}

img {
  max-width: 100%;
  height: auto;
}

.mermaid {
  margin: 24px 0;
  padding: 18px 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  background: rgba(19, 28, 42, 0.7);
}

th, td {
  border: 1px solid var(--border);
  padding: 12px 14px;
  text-align: left;
}

th {
  color: var(--text);
  background: rgba(255,255,255,0.04);
}

@media (max-width: 720px) {
  .site-shell {
    padding: 24px 18px 56px;
  }

  .site-header {
    margin-bottom: 28px;
  }
}
"""
    (assets_dir / "site.css").write_text(css, encoding="utf-8")


def copy_assets(src_dir: Path, dst_dir: Path):
    """Copy a directory tree into an existing destination on Python 3.8."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def build_site(args):
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output).resolve()

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_site_config(output_dir)
    write_layout(output_dir)
    write_stylesheet(output_dir)

    docs_dir = repo_root / "docs"
    for src in docs_dir.glob("*.md"):
        if src.name == "index.md":
            dst = output_dir / "index.md"
            fallback = "envstack"
            page_kind = "root"
        else:
            dst = output_dir / "docs" / src.name
            fallback = src.stem.replace("-", " ").title()
            page_kind = "docs"
        write_markdown_page(src, dst, fallback, page_kind=page_kind)

    if (docs_dir / "assets").exists():
        copy_assets(docs_dir / "assets", output_dir / "assets")
        copy_assets(docs_dir / "assets", output_dir / "docs" / "assets")

    cname = repo_root / "CNAME"
    if cname.exists():
        shutil.copy2(cname, output_dir / "CNAME")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build_site(args)


if __name__ == "__main__":
    main()
