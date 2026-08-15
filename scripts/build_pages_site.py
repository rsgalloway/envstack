#!/usr/bin/env python3
#
# Copyright (c) 2024-2026, Ryan Galloway (ryan@rsgalloway.com)
#

"""Build a simple Jekyll-friendly docs site from repository markdown files."""

import argparse
import re
import shutil
from pathlib import Path, PurePosixPath

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def source_doc_url(src_rel: PurePosixPath) -> str:
    """Return the canonical site URL for a markdown source path under docs/."""
    if src_rel == PurePosixPath("index.md"):
        return "/"
    if src_rel.name == "README.md":
        return "/" + str(PurePosixPath("docs") / src_rel.parent).strip("/") + "/"
    return "/" + str(PurePosixPath("docs") / src_rel.with_suffix("")).strip("/") + "/"


def source_to_output_path(src_rel: PurePosixPath) -> Path:
    """Map a markdown source path under docs/ to its generated site location."""
    if src_rel == PurePosixPath("index.md"):
        return Path("index.md")
    if src_rel.name == "README.md":
        return Path("docs") / src_rel.parent / "index.md"
    return Path("docs") / Path(str(src_rel))


def rewrite_links(content: str, src_rel: PurePosixPath) -> str:
    """Rewrite local markdown links for generated HTML output."""

    def replace(match: re.Match) -> str:
        label = match.group("label")
        target = match.group("target")

        if "://" in target or target.startswith("#") or target.startswith("mailto:"):
            return match.group(0)

        if not target.endswith(".md"):
            return match.group(0)

        target_rel = PurePosixPath(target)
        if target_rel.is_absolute():
            return match.group(0)

        if target.startswith("docs/"):
            resolved = PurePosixPath(target[len("docs/") :])
        else:
            resolved = src_rel.parent / target_rel

        normalized = PurePosixPath(*resolved.parts)
        return f"[{label}]({source_doc_url(normalized)})"

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


def write_markdown_page(src: Path, dst: Path, fallback_title: str, src_rel: PurePosixPath):
    """Copy a markdown file into the site tree with front matter and fixed links."""
    content = src.read_text(encoding="utf-8")
    title = extract_title(content, fallback_title)
    content = rewrite_links(content, src_rel=src_rel)
    content = rewrite_mermaid_blocks(content)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(wrap_markdown(content, title), encoding="utf-8")


def write_site_config(output_dir: Path):
    """Write a minimal Jekyll config file."""
    config = """title: envstack
description: Environment variable composition and activation layer
markdown: kramdown
permalink: pretty
highlighter: rouge
kramdown:
  input: GFM
  syntax_highlighter: rouge
  syntax_highlighter_opts:
    css_class: highlight
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
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="stylesheet" href="/assets/site.css">
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "dark" });
    </script>
    <script>
      document.addEventListener("DOMContentLoaded", () => {
        for (const heading of document.querySelectorAll(".site-main h2, .site-main h3")) {
          if (!heading.id || heading.querySelector(".header-anchor")) {
            continue;
          }

          const anchor = document.createElement("a");
          anchor.className = "header-anchor";
          anchor.href = `#${encodeURIComponent(heading.id)}`;
          anchor.setAttribute("aria-label", `Link to section: ${heading.textContent.trim()}`);
          anchor.textContent = "#";
          heading.appendChild(anchor);
        }
      });
    </script>
  </head>
  <body>
    <div class="site-shell">
      <header class="site-header">
        <a class="site-brand" href="/">{{ site.title }}</a>
        <nav class="site-nav">
          <a href="/">Home</a>
          <a href="/docs/api/">API</a>
          <a href="/docs/comparison/">Comparison</a>
          <a href="/docs/design/">Design</a>
          <a href="/docs/examples/">Examples</a>
          <a href="/docs/secrets/">Secrets</a>
          <a href="/docs/faq/">FAQ</a>
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

.site-main h2,
.site-main h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-anchor {
  color: var(--accent-2);
  font-weight: 500;
  opacity: 0;
  transition: opacity 120ms ease;
}

.site-main h2:hover .header-anchor,
.site-main h2:focus-within .header-anchor,
.site-main h3:hover .header-anchor,
.site-main h3:focus-within .header-anchor {
  opacity: 1;
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

.highlight {
  margin: 0;
}

.highlight pre,
pre.highlight {
  overflow-x: auto;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--code);
}

.highlight .hll { background: rgba(255,255,255,0.05); }
.highlight .c,
.highlight .cm,
.highlight .c1,
.highlight .cs { color: #7f8ea3; font-style: italic; }
.highlight .k,
.highlight .kd,
.highlight .kn,
.highlight .kp,
.highlight .kr,
.highlight .nt { color: #7cc7ff; }
.highlight .s,
.highlight .sa,
.highlight .sb,
.highlight .sc,
.highlight .dl,
.highlight .sd,
.highlight .s2 { color: #9be38c; }
.highlight .si,
.highlight .se,
.highlight .sh,
.highlight .sx { color: #ffd580; }
.highlight .m,
.highlight .mb,
.highlight .mf,
.highlight .mh,
.highlight .mi,
.highlight .mo { color: #ffb86b; }
.highlight .na,
.highlight .nb,
.highlight .bp,
.highlight .nc,
.highlight .nf,
.highlight .fm,
.highlight .ne,
.highlight .nn { color: #f7d774; }
.highlight .nv,
.highlight .vc,
.highlight .vg,
.highlight .vi { color: #ff9ecb; }
.highlight .o,
.highlight .ow { color: #ff8f70; }
.highlight .p,
.highlight .w { color: #d9e2f2; }

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
    for src in sorted(docs_dir.rglob("*.md")):
        src_rel = PurePosixPath(src.relative_to(docs_dir).as_posix())
        dst = output_dir / source_to_output_path(src_rel)
        fallback = (
            "envstack"
            if src_rel == PurePosixPath("index.md")
            else src.stem.replace("-", " ").title()
        )
        write_markdown_page(src, dst, fallback, src_rel=src_rel)

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
