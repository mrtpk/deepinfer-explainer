#!/usr/bin/env python3
"""Generate the folder tree of src/code/index.html from the target repo at the pinned commit.

PATTERN for every reference generator (env vars, config fields, CLI flags, API tables):
  1. read the facts from the code (here: `git ls-tree` at the pinned commit, and line counts);
  2. merge them with hand-written text (here: DESCRIPTIONS below, one short sentence per folder);
  3. write HTML between markers in a page source:
       <!-- BEGIN GENERATED folder-tree --> ... <!-- END GENERATED folder-tree -->
  4. --check: exit 1 if the page is out of date (run it in the final pass).

Python 3 standard library only. Reads explainer.json for the repo path and the commit.

Usage:
  python3 tools/gen_folder_tree.py             # write the page
  python3 tools/gen_folder_tree.py --check     # only check
  python3 tools/gen_folder_tree.py --depth 3   # show deeper folders (default 2)
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "explainer.json").read_text(encoding="utf-8"))
REPO = (ROOT / CFG["repo_path"]).resolve()
SHA = CFG["sha"]
PAGE = ROOT / "src" / "code" / "index.html"
BEGIN, END = "<!-- BEGIN GENERATED folder-tree -->", "<!-- END GENERATED folder-tree -->"

# Hand-written text: one short sentence per folder (site language rules apply).
# Optional page link: "folder": ("Description.", "code/page-id")
DESCRIPTIONS: dict[str, str | tuple[str, str]] = {
    "": "The repository root.",
}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", SHA],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        sys.exit(f"git ls-tree failed: {out.stderr.strip()}")
    return [p for p in out.stdout.splitlines() if (REPO / p).is_file()]


def line_count(path: str) -> int:
    data = (REPO / path).read_bytes()
    if b"\0" in data[:4096]:
        return 0  # binary
    return data.count(b"\n") + (0 if not data or data.endswith(b"\n") else 1)


def build_tree(files: list[str], depth: int) -> dict:
    tree: dict = {"files": 0, "lines": 0, "dirs": {}}
    for f in files:
        n = line_count(f)
        node = tree
        node["files"] += 1
        node["lines"] += n
        for part in f.split("/")[:-1][:depth]:
            node = node["dirs"].setdefault(part, {"files": 0, "lines": 0, "dirs": {}})
            node["files"] += 1
            node["lines"] += n
    return tree


def render(node: dict, prefix: str) -> str:
    items = []
    for name in sorted(node["dirs"]):
        sub = node["dirs"][name]
        path = f"{prefix}{name}/"
        desc = DESCRIPTIONS.get(path.rstrip("/"), "")
        link = ""
        if isinstance(desc, tuple):
            desc, page = desc
            link = f" {{{{link {page} | page}}}}"
        cite = f"{{{{cite {path} | {html.escape(path)}}}}}"
        text = f" {html.escape(desc)}" if desc else ""
        children = render(sub, path) if sub["dirs"] else ""
        items.append(f'<li>{cite} <span class="ct-n">{sub["files"]:,} files · {sub["lines"]:,} lines</span>'
                     f"{text}{link}{children}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--depth", type=int, default=2)
    args = ap.parse_args()
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != SHA:
        sys.exit(f"{REPO} is at {head[:12]}, but explainer.json pins {SHA[:12]}")
    tree = build_tree(tracked_files(), args.depth)
    body = (f'<p class="ct-total">{tree["files"]:,} tracked files, {tree["lines"]:,} lines '
            f"(text files only; counted with <code>git ls-tree</code> at the pinned commit).</p>\n"
            f'<div class="ct-tree">{render(tree, "")}</div>')
    page = PAGE.read_text(encoding="utf-8")
    if BEGIN not in page or END not in page:
        sys.exit(f"{PAGE}: markers {BEGIN} / {END} not found")
    start = page.index(BEGIN) + len(BEGIN)
    new = page[:start] + "\n" + body + "\n" + page[page.index(END):]
    if args.check:
        if new != page:
            print(f"{PAGE.relative_to(ROOT)} is out of date: run python3 tools/gen_folder_tree.py")
            return 1
        print("folder tree is up to date")
        return 0
    PAGE.write_text(new, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}: {tree['files']} files, {tree['lines']} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
