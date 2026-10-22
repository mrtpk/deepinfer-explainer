#!/usr/bin/env python3
"""build.py - static site generator for a codebase explainer site ("<Project> Explained").

Standard library only. Run from the project folder:

    python3 build.py                  # build site/
    python3 build.py --strict         # warnings also fail the build
    python3 build.py --preview        # write site/ even when there are errors
    python3 build.py --force-diagrams # re-run every diagram script

All project-specific values (name, upstream repo, pinned commit, ...) are in explainer.json.

Input
  src/**/*.html          page sources: front matter + HTML fragment (see STYLE.md)
  src/nav/*.json         one nav file per section (sidebar order, planned pages)
  src/glossary/*.json    glossary entries, merged from all files
  diagrams/*.py          one script per diagram, writes build/diagrams/<name>.svg
  assets/                CSS, JS, images (copied to site/assets/); assets/viz/ = interactive visuals
  <repo_path>            the target repo checkout (explainer.json), READ ONLY, pinned to its sha

Output
  site/                  fully static, opens from disk (file://), relative links only
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "explainer.json"


def _load_config() -> dict:
    """Read explainer.json: the ONLY place for project-specific values."""
    if not CONFIG_FILE.is_file():
        sys.exit(f"ERROR   {CONFIG_FILE} not found. Copy it from the template and fill it in.")
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR   explainer.json: invalid JSON: {e}")
    missing = [k for k in ("project", "repo_path", "repo_url", "sha") if not cfg.get(k)]
    if missing:
        sys.exit(f"ERROR   explainer.json: missing {', '.join(missing)}")
    if not re.fullmatch(r"[0-9a-f]{40}", cfg["sha"]):
        sys.exit("ERROR   explainer.json: 'sha' must be the full 40-character commit id")
    return cfg


CFG = _load_config()
PROJECT = CFG["project"]
REPO = (ROOT / CFG["repo_path"]).resolve()
SHA = CFG["sha"]
SHORT_SHA = SHA[:7]
REPO_URL = CFG["repo_url"].rstrip("/")
REPO_HOST = CFG.get("repo_host", "github")          # github | gitlab | gitea
REPO_LABEL = CFG.get("repo_label") or "/".join(REPO_URL.split("/")[-2:])
HOST_NAME = {"github": "GitHub", "gitlab": "GitLab", "gitea": "Gitea"}.get(REPO_HOST, "the repo host")
SITE_NAME = CFG.get("site_name") or f"{PROJECT} Explained"
BRAND_MARK = CFG.get("brand_mark") or PROJECT[:2].upper()
COMMENT_LANGUAGE = CFG.get("comment_language", "")   # language of code comments that <x-tr> translates
STE_CHECK = CFG.get("language_style", "ste") == "ste"
STE_MAX_WORDS = int(CFG.get("ste_max_words", 25))

SRC = ROOT / "src"
SITE = ROOT / "site"
ASSETS = ROOT / "assets"
DIAGRAMS = ROOT / "diagrams"
DIAGRAM_OUT = ROOT / "build" / "diagrams"

PRISM = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0"
PRISM_COMPONENTS = CFG.get("prism_components") or [
    "prism-core", "prism-clike", "prism-c", "prism-cpp", "prism-python", "prism-bash", "prism-json"]

LEVELS = ("Beginner", "Intermediate", "Advanced")
SECTIONS_NEED_LEVEL = {"learn", "concepts", "tours"}
TEMPLATE_SECTIONS = {"learn", "concepts", "tours"}
FRONT_KEYS = {
    "title", "nav_title", "section", "level", "prerequisites", "related", "summary",
    "prev", "next", "nav_after", "checks", "scripts",
}
GENERATED = {"reference/glossary"}
VIZ_CSS = "viz/viz.css"          # loaded by pages that use <x-viz> or <x-img> (path inside assets/)
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
REPO_IMAGES: set[str] = set()    # repo files used by <x-img repo="...">; copied to site/assets/repo/
LANG_BY_EXT = {
    ".py": "python", ".pyi": "python", ".cpp": "cpp", ".hpp": "cpp", ".h": "cpp", ".cc": "cpp",
    ".cu": "cpp", ".cuh": "cpp", ".sh": "bash", ".json": "json",
}
LANG_BY_EXT.update(CFG.get("lang_by_ext") or {})


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"ERROR   {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        line = f"WARNING {where}: {msg}"
        if line not in self.warnings:
            self.warnings.append(line)


R = Report()


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def slugify(s: str) -> str:
    s = strip_tags(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def suggest(name: str, options) -> str:
    m = difflib.get_close_matches(name, list(options), n=3)
    return f" (did you mean {', '.join(repr(x) for x in m)}?)" if m else ""


ATTR_RE = re.compile(r'([a-zA-Z_][\w-]*)\s*=\s*"([^"]*)"')
# attribute list of a custom tag; quoted values may contain ">" (for example <code>)
ATTRS = r'((?:[^>"]|"[^"]*")*?)'


def parse_attrs(s: str) -> dict[str, str]:
    attrs = {k: html.unescape(v) for k, v in ATTR_RE.findall(s or "")}
    rest = ATTR_RE.sub("", s or "").strip().rstrip("/").strip()
    if rest:
        attrs["__bad__"] = rest
    return attrs


# ---------------------------------------------------------------------------
# Repo access (READ ONLY)
# ---------------------------------------------------------------------------
_file_cache: dict[str, list[str] | None] = {}


def repo_path(path: str) -> Path | None:
    p = (REPO / path).resolve()
    if p != REPO and REPO not in p.parents:
        return None
    return p


def repo_lines(path: str) -> list[str] | None:
    if path not in _file_cache:
        p = repo_path(path)
        if p is None or not p.is_file():
            _file_cache[path] = None
        else:
            _file_cache[path] = p.read_text(encoding="utf-8", errors="replace").split("\n")
            if _file_cache[path] and _file_cache[path][-1] == "":
                _file_cache[path].pop()
    return _file_cache[path]


def github_url(path: str, a: int | None = None, b: int | None = None, is_dir: bool = False) -> str:
    kind = "tree" if is_dir else "blob"
    if REPO_HOST == "gitlab":
        url = f"{REPO_URL}/-/{kind}/{SHA}/{path.rstrip('/')}"
        if a is not None:
            url += f"#L{a}" if (b is None or b == a) else f"#L{a}-{b}"
        return url
    if REPO_HOST == "gitea":
        url = f"{REPO_URL}/src/commit/{SHA}/{path.rstrip('/')}"
    else:
        url = f"{REPO_URL}/{kind}/{SHA}/{path.rstrip('/')}"
    if a is not None:
        url += f"#L{a}" if (b is None or b == a) else f"#L{a}-L{b}"
    return url


def tree_url() -> str:
    if REPO_HOST == "gitlab":
        return f"{REPO_URL}/-/tree/{SHA}"
    if REPO_HOST == "gitea":
        return f"{REPO_URL}/src/commit/{SHA}"
    return f"{REPO_URL}/tree/{SHA}"


def parse_range(s: str) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", s)
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return (a, b) if b >= a else None


def check_repo_sha() -> None:
    try:
        out = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e:
        R.warn("repo", f"cannot run git to check the commit: {e}")
        return
    head = out.stdout.strip()
    if out.returncode != 0:
        R.warn("repo", f"cannot read the repo commit: {out.stderr.strip()}")
    elif head != SHA:
        R.error("repo", f"{REPO} is at {head[:12]}, but the site is pinned to {SHORT_SHA}. Line numbers would be wrong.")


_COMMIT_INFO: dict | None = None


def commit_info() -> dict:
    """Date and subject of the pinned commit (from git; empty strings if git is not available)."""
    global _COMMIT_INFO
    if _COMMIT_INFO is None:
        info = {"date": "", "day": "", "subject": ""}
        try:
            out = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%ci%n%cs%n%s", SHA],
                                 capture_output=True, text=True, timeout=20)
            if out.returncode == 0:
                parts = out.stdout.strip().split("\n", 2)
                if len(parts) == 3:
                    info = {"date": parts[0], "day": parts[1], "subject": parts[2]}
        except (OSError, subprocess.TimeoutExpired):
            pass
        _COMMIT_INFO = info
    return _COMMIT_INFO


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class NavEntry:
    id: str
    title: str
    section: str
    group: str | None


@dataclass
class Section:
    key: str
    title: str
    order: int
    groups: list[tuple[str | None, list[NavEntry]]]
    file: str


@dataclass
class Page:
    id: str
    src: Path | None
    meta: dict[str, str]
    body: str
    body_line: int = 1
    html_body: str = ""
    headings: list[tuple[int, str, str]] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)
    output: str = ""
    has_code: bool = False
    has_deepdive: bool = False
    has_viz_css: bool = False
    words: int = 0
    words_main: int = 0

    @property
    def title(self) -> str:
        if self.id == "index" and not self.meta.get("title"):
            return SITE_NAME
        return self.meta.get("title", self.id)

    @property
    def section(self) -> str:
        return "home" if self.id == "index" else self.id.split("/")[0]

    @property
    def out_rel(self) -> str:
        return f"{self.id}.html"

    @property
    def where(self) -> str:
        return rel(self.src) if self.src else f"(generated {self.id})"

    def listify(self, key: str) -> list[str]:
        v = self.meta.get(key, "").strip()
        if not v or v.lower() == "none":
            return []
        return [x.strip() for x in v.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_sections() -> tuple[list[Section], dict[str, NavEntry]]:
    sections: list[Section] = []
    entries: dict[str, NavEntry] = {}
    for f in sorted((SRC / "nav").glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            R.error(rel(f), f"invalid JSON: {e}")
            continue
        key = data.get("section")
        if not key:
            R.error(rel(f), 'missing "section"')
            continue
        groups_raw = data.get("groups")
        if groups_raw is None:
            groups_raw = [{"title": None, "pages": data.get("pages", [])}]
        groups: list[tuple[str | None, list[NavEntry]]] = []
        for g in groups_raw:
            items = []
            for p in g.get("pages", []):
                pid, title = p.get("id"), p.get("title")
                if not pid or not title:
                    R.error(rel(f), f'nav entry needs "id" and "title": {p}')
                    continue
                if not pid.startswith(key + "/"):
                    R.error(rel(f), f"nav id {pid!r} must start with '{key}/'")
                    continue
                if pid in entries:
                    R.error(rel(f), f"nav id {pid!r} is listed twice")
                    continue
                e = NavEntry(pid, title, key, g.get("title"))
                entries[pid] = e
                items.append(e)
            groups.append((g.get("title"), items))
        if any(s.key == key for s in sections):
            R.error(rel(f), f"section {key!r} is defined in two nav files")
            continue
        sections.append(Section(key, data.get("title", key.title()), int(data.get("order", 99)), groups, rel(f)))
    sections.sort(key=lambda s: (s.order, s.key))
    return sections, entries


def load_glossary() -> dict[str, dict]:
    terms: dict[str, dict] = {}
    for f in sorted((SRC / "glossary").glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            R.error(rel(f), f"invalid JSON: {e}")
            continue
        for tid, entry in data.items():
            if tid.startswith("_"):
                continue  # comments
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tid):
                R.error(rel(f), f"glossary id {tid!r}: use lower-case letters, digits and '-'")
                continue
            if tid in terms:
                R.error(rel(f), f"glossary id {tid!r} is also defined in {terms[tid]['_file']}")
                continue
            if not entry.get("term") or not entry.get("short"):
                R.error(rel(f), f'glossary entry {tid!r} needs "term" and "short"')
                continue
            if len(entry["short"]) > 220:
                R.warn(rel(f), f"glossary {tid!r}: 'short' is {len(entry['short'])} chars; keep it under 220 for the tooltip")
            entry["_file"] = rel(f)
            terms[tid] = entry
    return terms


FRONT_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def load_pages() -> dict[str, Page]:
    pages: dict[str, Page] = {}
    for f in sorted(SRC.rglob("*.html")):
        relp = f.relative_to(SRC)
        if relp.parts[0] in ("nav", "glossary") or any(part.startswith("_") for part in relp.parts):
            continue
        pid = relp.with_suffix("").as_posix()
        text = f.read_text(encoding="utf-8")
        m = FRONT_RE.match(text)
        if not m:
            R.error(rel(f), "missing front matter (--- ... --- at the top)")
            continue
        meta: dict[str, str] = {}
        for i, line in enumerate(m.group(1).split("\n"), start=2):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                R.error(f"{rel(f)}:{i}", f"front matter line needs 'key: value': {line!r}")
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            if k not in FRONT_KEYS:
                R.error(f"{rel(f)}:{i}", f"unknown front matter key {k!r}{suggest(k, FRONT_KEYS)}")
                continue
            meta[k] = v.strip()
        body_line = text[: m.end()].count("\n") + 1
        page = Page(pid, f, meta, text[m.end():], body_line)
        if pid in GENERATED:
            R.error(rel(f), f"{pid} is generated by build.py; do not write it by hand")
            continue
        pages[pid] = page
    return pages


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------
def run_diagrams(force: bool) -> dict[str, Path]:
    DIAGRAM_OUT.mkdir(parents=True, exist_ok=True)
    lib = DIAGRAMS / "svglib.py"
    lib_bytes = lib.read_bytes() if lib.exists() else b""
    found: dict[str, Path] = {}
    ran = 0
    for script in sorted(DIAGRAMS.glob("*.py")):
        if script.name == "svglib.py" or script.name.startswith("_"):
            continue
        name = script.stem
        out = DIAGRAM_OUT / f"{name}.svg"
        # Content hash of script + svglib, not mtime: mtimes on /mnt/c are not reliable.
        stamp = DIAGRAM_OUT / f"{name}.hash"
        digest = hashlib.sha256(script.read_bytes() + b"\0" + lib_bytes).hexdigest()
        stale = force or not out.exists() or not stamp.exists() or stamp.read_text() != digest
        if stale:
            ran += 1
            proc = subprocess.run([sys.executable, str(script), str(out)], capture_output=True, text=True, cwd=str(DIAGRAMS),
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            if proc.returncode != 0:
                R.error(rel(script), "diagram script failed:\n" + (proc.stderr.strip() or proc.stdout.strip()))
                continue
            stamp.write_text(digest)
            for line in proc.stderr.strip().splitlines():
                R.warn(rel(script), line)
        if out.exists():
            head = out.read_text(encoding="utf-8")[:300]
            if 'width="1100"' not in head:
                R.warn(rel(out), "canvas width is not 1100 (STYLE.md section 10, readability rule)")
            found[name] = out
    print(f"diagrams: {len(found)} found, {ran} rebuilt")
    return found


# ---------------------------------------------------------------------------
# Rendering context
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, pages, entries, sections, glossary, diagrams):
        self.pages: dict[str, Page] = pages
        self.entries: dict[str, NavEntry] = entries
        self.sections: list[Section] = sections
        self.glossary: dict[str, dict] = glossary
        self.diagrams: dict[str, Path] = diagrams

    def known(self, pid: str) -> bool:
        return pid in self.pages or pid in self.entries or pid == "index"

    def live(self, pid: str) -> bool:
        return pid in self.pages

    def title_of(self, pid: str) -> str:
        if pid in self.pages:
            return self.pages[pid].title
        if pid in self.entries:
            return self.entries[pid].title
        return pid


def href(from_id: str, to_id: str, anchor: str | None = None) -> str:
    depth = from_id.count("/")
    target = "index.html" if to_id == "index" else f"{to_id}.html"
    return "../" * depth + target + (f"#{anchor}" if anchor else "")


def root_prefix(pid: str) -> str:
    return "../" * pid.count("/")


def line_of(page: Page, needle: str) -> str:
    """Best-effort source line of a tag, for error messages."""
    if page.src is None:
        return page.where
    idx = page.body.find(needle)
    if idx < 0:
        return page.where
    return f"{page.where}:{page.body_line + page.body[:idx].count(chr(10))}"


# ---------------------------------------------------------------------------
# Inline tags: {{cite ...}}, {{term ...}}, {{link ...}}
# ---------------------------------------------------------------------------
INLINE_RE = re.compile(r"\{\{\s*([a-z]+)\s+([^{}|]+?)\s*(?:\|\s*([^{}]*?)\s*)?\}\}")


def render_cite(ctx: Ctx, page: Page, arg: str, label: str | None, where: str) -> str:
    m = re.fullmatch(r"([^:\s]+)(?::([\d\s-]+))?", arg)
    if not m:
        R.error(where, f"bad citation {arg!r}; use path:line or path:start-end")
        return esc(arg)
    path, rng = m.group(1), m.group(2)
    p = repo_path(path)
    if p is None or not p.exists():
        R.error(where, f"citation: file {path!r} does not exist in the repo")
        return esc(arg)
    if rng is None:
        url = github_url(path, is_dir=p.is_dir())
        text = label if label else f"<code>{esc(path)}</code>"
        return f'<a class="cite" href="{esc(url)}" target="_blank" rel="noopener">{text}</a>'
    if p.is_dir():
        R.error(where, f"citation: {path!r} is a folder; line numbers need a file")
        return esc(arg)
    r = parse_range(rng)
    lines = repo_lines(path) or []
    if r is None:
        R.error(where, f"citation: bad line range {rng!r} in {arg!r}")
        return esc(arg)
    a, b = r
    if a < 1 or b > len(lines):
        R.error(where, f"citation: {path} has {len(lines)} lines; {a}-{b} is out of range")
        return esc(arg)
    url = github_url(path, a, b)
    shown = f"{path}:{a}" if a == b else f"{path}:{a}-{b}"
    text = label if label else f"<code>{esc(shown)}</code>"
    return f'<a class="cite" href="{esc(url)}" target="_blank" rel="noopener" title="{esc(shown)} at {SHORT_SHA}">{text}</a>'


def render_term(ctx: Ctx, page: Page, arg: str, label: str | None, where: str) -> str:
    tid = arg.strip()
    entry = ctx.glossary.get(tid)
    if entry is None:
        R.error(where, f"unknown glossary term {tid!r}{suggest(tid, ctx.glossary)}")
        return esc(label or tid)
    text = label if label else esc(entry["term"])
    url = href(page.id, "reference/glossary", f"term-{tid}")
    return (f'<a class="term" href="{esc(url)}" data-term="{esc(entry["term"])}" '
            f'data-def="{esc(entry["short"])}">{text}</a>')


def render_link(ctx: Ctx, page: Page, arg: str, label: str | None, where: str) -> str:
    pid, _, anchor = arg.strip().partition("#")
    if not ctx.known(pid):
        R.error(where, f"link to unknown page {pid!r}{suggest(pid, list(ctx.pages) + list(ctx.entries))}")
        return esc(label or pid)
    text = label if label else esc(ctx.title_of(pid))
    if not ctx.live(pid) and pid != "index":
        if page.src is not None:  # generated pages (glossary) link to planned pages on purpose
            R.warn(where, f"link to {pid!r}, which is not written yet (shown as 'coming soon')")
        return f'<span class="soon-link" title="Coming soon">{text}</span>'
    return f'<a href="{esc(href(page.id, pid, anchor or None))}">{text}</a>'


def render_project(ctx: Ctx, page: Page, arg: str, label: str | None, where: str) -> str:
    """{{project name|site|sha|short_sha|repo_url|date|subject}}: values from explainer.json and git."""
    ci = commit_info()
    values = {"name": PROJECT, "site": SITE_NAME, "sha": SHA, "short_sha": SHORT_SHA, "repo_url": REPO_URL,
              "date": ci["date"], "day": ci["day"], "subject": ci["subject"]}
    key = arg.strip()
    if key not in values:
        R.error(where, f"{{{{project {key}}}}}: use one of {', '.join(values)}")
        return ""
    return esc(values[key])


INLINE_KINDS = {"cite": render_cite, "term": render_term, "link": render_link, "project": render_project}


def submodule_pins() -> list[tuple[str, str, str]]:
    """(path, url, pinned sha) of every git submodule at SHA. Empty if there are none."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", SHA], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if out.returncode != 0:
        return []
    urls: dict[str, str] = {}
    gm = repo_lines(".gitmodules") or []
    cur = None
    for line in gm:
        m = re.match(r"\s*path\s*=\s*(\S+)", line)
        if m:
            cur = m.group(1)
        m = re.match(r"\s*url\s*=\s*(\S+)", line)
        if m and cur:
            urls[cur] = m.group(1)
    pins = []
    for line in out.stdout.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "commit":
            pins.append((path, urls.get(path, ""), parts[2]))
    return pins


def render_code_version() -> str:
    """<x-version />: commit table, checkout commands, submodule pins, line-number note."""
    ci = commit_info()
    rows = [("Commit", f"<code>{SHA}</code> (short: <code>{SHORT_SHA}</code>)")]
    if ci["date"]:
        rows.append(("Date", esc(ci["date"])))
    if ci["subject"]:
        rows.append(("Subject", f"\u201c{esc(ci['subject'])}\u201d"))
    rows.append(("Browse", f'<a href="{esc(tree_url())}" target="_blank" rel="noopener">{esc(REPO_LABEL)} at {SHORT_SHA}</a>'))
    table = "<table><tbody>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</tbody></table>"
    pins = submodule_pins()
    clone = REPO_URL + ("" if REPO_URL.endswith(".git") else ".git")
    folder = REPO_URL.rstrip("/").split("/")[-1].removesuffix(".git")
    cmds = [f"git clone {clone}", f"cd {folder}", f"git checkout {SHA}"]
    if pins:
        cmds.append("git submodule update --init --recursive")
    out = ["<p>To get exactly this version of the code, run these commands:</p>",
           table,
           f'<pre><code class="language-bash">{esc(chr(10).join(cmds))}</code></pre>']
    if pins:
        trs = []
        for path, url, sha in pins:
            link = url[:-4] if url.endswith(".git") else url
            cell = (f'<a href="{esc(link)}/tree/{sha}" target="_blank" rel="noopener"><code>{sha}</code></a>'
                    if link.startswith("https://") else f"<code>{sha}</code>")
            trs.append(f"<tr><td><code>{esc(path)}</code></td><td>{cell}</td></tr>")
        out.append(f"<p>The repository pins {len(pins)} git submodule(s). This table shows the commit of each one:</p>"
                   "<table><thead><tr><th>Submodule</th><th>Pinned commit</th></tr></thead><tbody>"
                   + "".join(trs) + "</tbody></table>")
    out.append('<aside class="callout callout-note"><p class="callout-title">Line numbers belong to this commit</p>'
               f'<div class="callout-body"><p>Every code excerpt and every <code>file:line</code> link on this site points to commit '
               f'<code>{SHORT_SHA}</code>. In a newer version, the line numbers and the code can be different.</p></div></aside>')
    return "\n".join(out)


def expand_inline(ctx: Ctx, page: Page, s: str) -> str:
    def sub(m: re.Match) -> str:
        kind, arg, label = m.group(1), m.group(2), m.group(3)
        where = line_of(page, m.group(0))
        fn = INLINE_KINDS.get(kind)
        if fn is None:
            R.error(where, f"unknown inline tag {{{{{kind} ...}}}}{suggest(kind, INLINE_KINDS)}")
            return esc(m.group(0)).replace("{", "&#123;")
        return fn(ctx, page, arg, label if label else None, where)

    s = INLINE_RE.sub(sub, s)
    for m in re.finditer(r"\{\{[^}]{0,60}", s):
        R.error(line_of(page, m.group(0)), f"malformed inline tag near {m.group(0)!r}")
    return s


# ---------------------------------------------------------------------------
# Block tags
# ---------------------------------------------------------------------------
class Holder:
    """Keeps rendered fragments out of later passes (so code text is never re-processed)."""

    def __init__(self) -> None:
        self.items: list[str] = []

    def put(self, s: str) -> str:
        self.items.append(s)
        return f"\x00H{len(self.items) - 1}\x00"

    def restore(self, s: str) -> str:
        for _ in range(5):
            if "\x00H" not in s:
                break
            s = re.sub(r"\x00H(\d+)\x00", lambda m: self.items[int(m.group(1))], s)
        return s


CODE_RE = re.compile(r"<x-code\b" + ATTRS + r"(?:/>|>(.*?)</x-code>)", re.S)
TR_RE = re.compile(r"<x-tr\b" + ATTRS + r">(.*?)</x-tr>", re.S)


def render_code(ctx: Ctx, page: Page, m: re.Match, holder: Holder) -> str:
    where = line_of(page, m.group(0)[:80])
    a = parse_attrs(m.group(1))
    if "__bad__" in a:
        R.error(where, f"x-code: cannot parse attributes near {a['__bad__']!r} (use name=\"value\")")
    path = a.get("file", "")
    lines = repo_lines(path) if path else None
    if not path:
        R.error(where, 'x-code needs file="repo/relative/path"')
        return ""
    if lines is None:
        R.error(where, f"x-code: file {path!r} does not exist in the repo")
        return ""
    r = parse_range(a.get("lines", ""))
    if r is None:
        R.error(where, f'x-code: lines="start-end" is missing or bad ({a.get("lines")!r})')
        return ""
    start, end = r
    if start < 1 or end > len(lines):
        R.error(where, f"x-code: {path} has {len(lines)} lines; {start}-{end} is out of range")
        return ""
    if end - start + 1 > 120:
        R.warn(where, f"x-code: {end - start + 1} lines is long; split it or move it into a deep dive")
    hl: set[int] = set()
    for part in filter(None, (x.strip() for x in a.get("highlight", "").split(","))):
        hr = parse_range(part)
        if hr is None or hr[0] < start or hr[1] > end:
            R.error(where, f"x-code: highlight {part!r} is outside lines {start}-{end}")
            continue
        hl.update(range(hr[0], hr[1] + 1))
    ext = os.path.splitext(path)[1]
    lang = a.get("lang") or LANG_BY_EXT.get(ext, "none")
    code = "\n".join(lines[start - 1:end])
    shown = f"{path}:{start}-{end}" if end != start else f"{path}:{start}"
    url = github_url(path, start, end)
    gutter = "".join(
        f'<span class="ln{" hl" if n in hl else ""}">{n}</span>' for n in range(start, end + 1)
    )
    bars = "".join(
        f'<span class="hl-bar" style="top:calc({n - start} * var(--code-lh))"></span>' for n in sorted(hl)
    )
    caption = a.get("caption")
    cap_html = f'<figcaption class="code-caption">{expand_inline(ctx, page, caption)}</figcaption>' if caption else ""
    trs = ""
    inner = m.group(2) or ""
    if inner.strip():
        items = []
        for tm in TR_RE.finditer(inner):
            ta = parse_attrs(tm.group(1))
            ln = ta.get("line", "")
            lr = parse_range(ln)
            if lr is None or lr[0] < start or lr[1] > end:
                R.error(where, f"x-tr line={ln!r} is outside lines {start}-{end}")
            items.append(f'<li><span class="tr-line">{esc(ln)}</span> {expand_inline(ctx, page, tm.group(2).strip())}</li>')
        leftover = TR_RE.sub("", inner).strip()
        if leftover:
            R.error(where, "x-code may only contain <x-tr line=\"N\">...</x-tr> items")
        if items:
            trs = ('<div class="code-tr"><p class="code-tr-title">Translated comments{f" ({COMMENT_LANGUAGE} → English)" if COMMENT_LANGUAGE else ""}</p>'
                   f'<ul>{"".join(items)}</ul></div>')
    page.has_code = True
    title = a.get("title")
    title_html = f'<span class="code-title">{esc(title)}</span>' if title else ""
    out = (
        f'<figure class="code-excerpt" data-lang="{esc(lang)}">'
        f'<div class="code-head">{title_html}<a class="code-path" href="{esc(url)}" target="_blank" rel="noopener" '
        f'title="Open on {HOST_NAME} at commit {SHORT_SHA}">{esc(shown)}</a>'
        f'<span class="code-actions"><a class="code-gh" href="{esc(url)}" target="_blank" rel="noopener">{HOST_NAME} ↗</a>'
        f'<button type="button" class="code-copy" aria-label="Copy code">Copy</button></span></div>'
        f'<div class="code-body"><div class="code-gutter" aria-hidden="true">{gutter}</div>'
        f'<div class="code-scroll"><div class="code-inner">{bars}'
        f'<pre><code class="language-{esc(lang)}">{esc(code)}</code></pre></div></div></div>'
        f"{trs}{cap_html}</figure>"
    )
    return holder.put(out)


def svg_inline(name: str, path: Path) -> str:
    svg = path.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    prefix = f"dg-{name}-"
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', svg)
    svg = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{prefix}{m.group(1)})", svg)
    svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}{m.group(1)}"', svg)
    return svg


def render_diagram(ctx: Ctx, page: Page, attrs: dict, where: str, holder: Holder) -> str:
    name = attrs.get("name", "")
    if name not in ctx.diagrams:
        R.error(where, f"x-diagram: no diagram {name!r} (expected diagrams/{name}.py)"
                       f"{suggest(name, ctx.diagrams)}")
        return ""
    alt = attrs.get("alt", "")
    if not alt:
        R.error(where, f'x-diagram {name!r} needs alt="..." (a text description for screen readers)')
    svg = svg_inline(name, ctx.diagrams[name])
    svg = svg.replace("<svg ", f'<svg role="img" aria-label="{esc(alt)}" ', 1)
    full = root_prefix(page.id) + f"diagrams/{name}.svg"
    cap = attrs.get("caption", "")
    cap_html = f'<figcaption>{expand_inline(ctx, page, cap)}</figcaption>' if cap else ""
    return holder.put(
        f'<figure class="diagram" id="fig-{esc(name)}">'
        f'<div class="diagram-card"><button type="button" class="diagram-zoom" aria-label="Zoom diagram: {esc(alt)}">'
        f"{svg}</button></div>"
        f'<div class="diagram-meta">{cap_html}<a class="diagram-open" href="{esc(full)}" target="_blank">Open full size ↗</a></div>'
        f"</figure>"
    )


VIZ_RE = re.compile(r"<x-viz\b" + ATTRS + r"(?:/>|>(.*?)</x-viz>)", re.S)
IMG_RE = re.compile(r"<x-img\b" + ATTRS + r"/?>(?:</x-img>)?")
VIZ_FALLBACK = ("This interactive visual needs JavaScript. Turn on JavaScript in your browser to use it. "
                "The text on this page explains the same idea.")


def render_viz(ctx: Ctx, page: Page, m: re.Match, holder: Holder) -> str:
    where = line_of(page, m.group(0)[:80])
    a = parse_attrs(m.group(1))
    if "__bad__" in a:
        R.error(where, f"x-viz: cannot parse attributes near {a['__bad__']!r} (use name=\"value\")")
    vid = a.get("id", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", vid):
        R.error(where, f'x-viz needs id="lower-case-name" (got {vid!r})')
    title = a.get("title", "")
    if not title:
        R.error(where, f'x-viz {vid!r} needs title="..."')
    if not page.listify("scripts"):
        R.error(where, f"x-viz {vid!r}: the page has no 'scripts:' front matter, so nothing mounts here "
                       "(add for example 'scripts: viz/<name>.js')")
    page.has_viz_css = True
    cap = a.get("caption", "")
    cap_html = f'<figcaption class="viz-caption">{expand_inline(ctx, page, cap)}</figcaption>' if cap else ""
    inner = (m.group(2) or "").strip()
    head = holder.put(
        f'<figure class="viz" id="viz-{esc(vid)}">'
        f'<div class="viz-head"><span class="viz-badge">Interactive</span><span class="viz-title">{esc(title)}</span></div>'
        f'<div class="viz-mount" data-viz="{esc(vid)}" role="region" aria-label="{esc(title)}">'
        f'<div class="viz-fallback">'
    )
    tail = holder.put(f"</div></div>{cap_html}</figure>")
    return head + (inner or f"<p>{esc(VIZ_FALLBACK)}</p>") + tail


def render_img(ctx: Ctx, page: Page, m: re.Match, holder: Holder) -> str:
    where = line_of(page, m.group(0)[:80])
    a = parse_attrs(m.group(1))
    if "__bad__" in a:
        R.error(where, f"x-img: cannot parse attributes near {a['__bad__']!r} (use name=\"value\")")
    src, repo = a.get("src", ""), a.get("repo", "")
    if bool(src) == bool(repo):
        R.error(where, 'x-img needs exactly one of src="img/<file>" (from assets/) or repo="<repo path>"')
        return ""
    path = src or repo
    if ".." in Path(path).parts or path.startswith("/"):
        R.error(where, f"x-img: path {path!r} must be relative and must not contain '..'")
        return ""
    if Path(path).suffix.lower() not in IMG_EXT:
        R.error(where, f"x-img: {path!r} is not an image ({', '.join(sorted(IMG_EXT))})")
        return ""
    if src:
        if not (ASSETS / src).is_file():
            R.error(where, f"x-img: assets/{src} does not exist")
            return ""
        url = root_prefix(page.id) + "assets/" + src
    else:
        p = repo_path(repo)
        if p is None or not p.is_file():
            R.error(where, f"x-img: file {repo!r} does not exist in the repo")
            return ""
        REPO_IMAGES.add(repo)
        url = root_prefix(page.id) + "assets/repo/" + repo
    alt = a.get("alt", "")
    if not alt:
        R.error(where, f'x-img {path!r} needs alt="..." (a text description for screen readers)')
    page.has_viz_css = True
    cap = a.get("caption", "")
    src_note = ""
    if repo:
        src_note = (f' <span class="img-source">Source: <a class="cite" href="{esc(github_url(repo))}" target="_blank" '
                    f'rel="noopener"><code>{esc(repo)}</code></a></span>')
    cap_html = f'<figcaption>{expand_inline(ctx, page, cap)}{src_note}</figcaption>' if (cap or src_note) else ""
    width = a.get("width", "")
    style = f' style="max-width:{int(width)}px"' if width.isdigit() else ""
    return holder.put(
        f'<figure class="figure-img"><a class="figure-img-card" href="{esc(url)}" target="_blank" title="Open full size">'
        f'<img src="{esc(url)}" alt="{esc(alt)}" loading="lazy"{style}></a>{cap_html}</figure>'
    )


def block_tag(name: str) -> re.Pattern:
    return re.compile(rf"<{name}\b" + ATTRS + rf">((?:(?!<{name}\b).)*?)</{name}>", re.S)


CALLOUTS = {"x-note": "Note", "x-simplified": "Simplified", "x-warning": "Warning"}


def render_blocks(ctx: Ctx, page: Page, s: str, holder: Holder) -> str:
    # self-closing diagrams
    def dia(m: re.Match) -> str:
        return render_diagram(ctx, page, parse_attrs(m.group(1)), line_of(page, m.group(0)), holder)

    s = re.sub(r"<x-diagram\b" + ATTRS + r"/?>(?:</x-diagram>)?", dia, s)
    s = VIZ_RE.sub(lambda m: render_viz(ctx, page, m, holder), s)
    s = IMG_RE.sub(lambda m: render_img(ctx, page, m, holder), s)

    def sentence(m: re.Match) -> str:
        return (f'<div class="one-sentence"><p class="one-sentence-label">In one sentence</p>'
                f'<p class="one-sentence-text">{m.group(2).strip()}</p></div>')

    s = block_tag("x-sentence").sub(sentence, s)
    s = re.sub(r"<x-version\s*/>", lambda m: holder.put(render_code_version()), s)

    for tag, default in CALLOUTS.items():
        kind = tag[2:]

        def callout(m: re.Match, kind=kind, default=default) -> str:
            a = parse_attrs(m.group(1))
            title = esc(a.get("title", default))
            return (f'<aside class="callout callout-{kind}"><p class="callout-title">{title}</p>'
                    f'<div class="callout-body">{m.group(2).strip()}</div></aside>')

        s = block_tag(tag).sub(callout, s)

    def quiz(m: re.Match) -> str:
        where = line_of(page, m.group(0)[:60])
        a = parse_attrs(m.group(1))
        qs = []
        for i, qm in enumerate(block_tag("x-q").finditer(m.group(2)), start=1):
            qa = parse_attrs(qm.group(1))
            answers = block_tag("x-a").findall(qm.group(2))
            if len(answers) != 1:
                R.error(where, f"x-quiz question {i} needs exactly one <x-a>...</x-a>")
            question = block_tag("x-a").sub("", qm.group(2)).strip()
            answer = answers[0][1].strip() if answers else ""
            lvl = qa.get("level", "")
            if lvl and lvl not in ("easy", "medium", "hard"):
                R.error(where, f"x-q level={lvl!r}: use easy, medium or hard")
            lvl_html = f'<span class="q-level q-{esc(lvl)}">{esc(lvl)}</span>' if lvl else ""
            qs.append(
                f'<li class="q"><div class="q-text"><span class="q-num">{i}</span><div>{question}</div>{lvl_html}</div>'
                f'<details class="q-answer"><summary>Show answer</summary><div class="q-answer-body">{answer}</div></details></li>'
            )
        rest = block_tag("x-q").sub("", m.group(2)).strip()
        if rest:
            R.error(where, "x-quiz may only contain <x-q> items")
        page._quiz_count = getattr(page, "_quiz_count", 0) + len(qs)
        heading = "" if a.get("heading") == "none" else f'<h2 id="check-yourself">{esc(a.get("title", "Check yourself"))}</h2>'
        return (f'<section class="quiz">{heading}<ol class="q-list">{"".join(qs)}</ol>'
                f'<p class="quiz-tools"><button type="button" class="quiz-toggle">Show all answers</button></p></section>')

    s = block_tag("x-quiz").sub(quiz, s)

    def deepdive(m: re.Match) -> str:
        a = parse_attrs(m.group(1))
        title = a.get("title", "Details")
        page.has_deepdive = True
        open_attr = " open" if a.get("open") == "yes" else ""
        return (f'<details class="deepdive"{open_attr}><summary><span class="dd-label">Deep dive</span>'
                f'<h3 class="dd-title">{esc(title)}</h3></summary><div class="dd-body">{m.group(2).strip()}</div></details>')

    s = block_tag("x-deepdive").sub(deepdive, s)

    def stop(m: re.Match) -> str:
        where = line_of(page, m.group(0)[:60])
        a = parse_attrs(m.group(1))
        n = a.get("n", "")
        if not n.isdigit():
            R.error(where, 'x-stop needs n="<number>"')
        title = a.get("title", "")
        return (f'<section class="stop" id="stop-{esc(n)}"><h2 class="stop-title"><span class="stop-num">{esc(n)}</span>'
                f'{esc(title)}</h2>{m.group(2).strip()}</section>')

    s = block_tag("x-stop").sub(stop, s)

    for m in re.finditer(r"</?x-[a-z-]+", s):
        R.error(line_of(page, m.group(0)), f"unknown or unbalanced tag {m.group(0)!r}")
    return s


HEADING_RE = re.compile(r"<h([23])\b([^>]*)>(.*?)</h\1>", re.S)


def collect_headings(page: Page, s: str) -> str:
    used: set[str] = set(re.findall(r'\bid="([^"]+)"', s))
    heads: list[tuple[int, str, str]] = []

    def sub(m: re.Match) -> str:
        level, attrs, inner = int(m.group(1)), m.group(2), m.group(3)
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if idm:
            hid = idm.group(1)
        else:
            base = slugify(inner)
            hid, k = base, 2
            while hid in used:
                hid, k = f"{base}-{k}", k + 1
            used.add(hid)
            attrs = f' id="{hid}"' + attrs
        heads.append((level, hid, strip_tags(inner).strip()))
        if "dd-title" in attrs:  # deep-dive titles sit inside <summary>; a link there would fight the toggle
            return f"<h{level}{attrs}>{inner}</h{level}>"
        return f'<h{level}{attrs}>{inner}<a class="h-anchor" href="#{hid}" aria-label="Link to this section">#</a></h{level}>'

    s = HEADING_RE.sub(sub, s)
    page.headings = heads
    return s


def render_body(ctx: Ctx, page: Page) -> None:
    holder = Holder()
    s = page.body.replace("\\{{", "\x01LBRACE\x01")
    s = CODE_RE.sub(lambda m: render_code(ctx, page, m, holder), s)
    # protect hand-written <pre> blocks from tag expansion
    s = re.sub(r"<pre\b.*?</pre>", lambda m: holder.put(m.group(0)), s, flags=re.S)
    s = render_blocks(ctx, page, s, holder)
    s = expand_inline(ctx, page, s)
    s = holder.restore(s)
    s = collect_headings(page, s)
    s = s.replace("\x01LBRACE\x01", "{{")
    page.html_body = s
    no_code = re.sub(r"<pre\b.*?</pre>|<svg\b.*?</svg>", "", s, flags=re.S)
    page.words = len(re.findall(r"\w+", strip_tags(no_code)))
    no_dd = re.sub(r'<details class="deepdive".*?</details>', "", no_code, flags=re.S)
    page.words_main = len(re.findall(r"\w+", strip_tags(no_dd)))


# ---------------------------------------------------------------------------
# Glossary page (generated)
# ---------------------------------------------------------------------------
def glossary_page(ctx: Ctx) -> Page:
    page = Page("reference/glossary", None, {
        "title": "Glossary",
        "summary": "Short definitions of every technical term on this site, with links to the pages that explain them.",
    }, "")
    items = sorted(ctx.glossary.items(), key=lambda kv: kv[1]["term"].lower())
    parts = ['<p>This page lists every term that has a tooltip on this site. '
             'Each entry gives a short definition. Many entries link to a page with the full explanation.</p>']
    letters: dict[str, list] = {}
    for tid, e in items:
        ch = e["term"][0].upper()
        letters.setdefault(ch if ch.isalpha() else "#", []).append((tid, e))
    parts.append('<p class="glossary-jump">' + " ".join(
        f'<a href="#letter-{slugify(ch) if ch != "#" else "sym"}">{esc(ch)}</a>' for ch in letters) + "</p>")
    for ch, group in letters.items():
        lid = f"letter-{slugify(ch) if ch != '#' else 'sym'}"
        parts.append(f'<h2 id="{lid}">{esc(ch)}</h2><dl class="glossary">')
        for tid, e in group:
            aliases = e.get("aliases") or []
            alias_html = f'<span class="g-alias">also: {esc(", ".join(aliases))}</span>' if aliases else ""
            more = ""
            if e.get("page"):
                more = f'<p class="g-more">Read more: {{{{link {e["page"]}}}}}</p>'
            long = f'<p>{e["long"]}</p>' if e.get("long") else ""
            parts.append(f'<dt id="term-{tid}">{esc(e["term"])} {alias_html}</dt>'
                         f'<dd><p class="g-short">{esc(e["short"])}</p>{long}{more}</dd>')
        parts.append("</dl>")
    page.body = "\n".join(parts)
    return page


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def nav_order(ctx: Ctx) -> list[str]:
    order = ["index"]
    for sec in ctx.sections:
        for _, items in sec.groups:
            order.extend(e.id for e in items)
    return order


def insert_unlisted(ctx: Ctx) -> None:
    """Pages that exist but are not in a nav file are added to their section."""
    for pid, page in ctx.pages.items():
        if pid == "index" or pid in ctx.entries:
            continue
        sec = next((s for s in ctx.sections if s.key == page.section), None)
        if sec is None:
            R.error(page.where, f"section {page.section!r} has no nav file (src/nav/{page.section}.json)")
            continue
        entry = NavEntry(pid, page.meta.get("nav_title") or page.title, sec.key, None)
        after = page.meta.get("nav_after")
        placed = False
        if after:
            for gi, (gt, items) in enumerate(sec.groups):
                for i, e in enumerate(items):
                    if e.id == after:
                        entry.group = gt
                        items.insert(i + 1, entry)
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                R.error(page.where, f"nav_after: {after!r} is not in {sec.file}")
        if not placed:
            if not after:
                R.warn(page.where, f"page is not in {sec.file}; added at the end of the section (add it to the nav file or use nav_after)")
            sec.groups[-1][1].append(entry)
        ctx.entries[pid] = entry


def render_sidebar(ctx: Ctx, page: Page) -> str:
    out = [f'<a class="nav-home{" current" if page.id == "index" else ""}" href="{href(page.id, "index")}">Home</a>']
    for sec in ctx.sections:
        total = sum(len(items) for _, items in sec.groups)
        live = sum(1 for _, items in sec.groups for e in items if ctx.live(e.id))
        is_open = page.section == sec.key or (page.id == "index" and sec.order == min(s.order for s in ctx.sections))
        out.append(f'<details class="nav-sec"{" open" if is_open else ""}><summary>'
                   f'<span class="nav-sec-title">{esc(sec.title)}</span>'
                   f'<span class="nav-count" title="{live} of {total} pages written">{live}/{total}</span></summary>')
        for gtitle, items in sec.groups:
            if gtitle:
                out.append(f'<p class="nav-group">{esc(gtitle)}</p>')
            out.append("<ul>")
            for e in items:
                label = esc(ctx.pages[e.id].meta.get("nav_title") or e.title) if ctx.live(e.id) else esc(e.title)
                if ctx.live(e.id):
                    cur = ' class="current" aria-current="page"' if e.id == page.id else ""
                    out.append(f'<li><a{cur} href="{href(page.id, e.id)}">{label}</a></li>')
                else:
                    out.append(f'<li class="soon"><span>{label}</span><span class="soon-tag">soon</span></li>')
            out.append("</ul>")
        out.append("</details>")
    return "\n".join(out)


def render_toc(page: Page) -> str:
    heads = [h for h in page.headings if h[0] in (2, 3)]
    if len(heads) < 2:
        return ""
    items = []
    for level, hid, text in heads:
        items.append(f'<li class="toc-l{level}"><a href="#{hid}">{esc(text)}</a></li>')
    return f'<nav class="toc" aria-label="On this page"><p class="toc-title">On this page</p><ul>{"".join(items)}</ul></nav>'


def section_title(ctx: Ctx, key: str) -> str:
    sec = next((s for s in ctx.sections if s.key == key), None)
    return sec.title if sec else key.title()


def render_page(ctx: Ctx, page: Page, order: list[str]) -> str:
    pre = root_prefix(page.id)
    where = page.where
    # breadcrumbs
    crumbs = [f'<a href="{href(page.id, "index")}">Home</a>']
    if page.id != "index":
        sec_key = page.section
        sec = next((s for s in ctx.sections if s.key == sec_key), None)
        first_live = None
        if sec:
            for _, items in sec.groups:
                for e in items:
                    if ctx.live(e.id):
                        first_live = first_live or e.id
        crumbs.append(f"<span>{esc(section_title(ctx, sec_key))}</span>")
        entry = ctx.entries.get(page.id)
        if entry and entry.group:
            crumbs.append(f"<span>{esc(entry.group)}</span>")
        crumbs.append(f'<span aria-current="page">{esc(page.meta.get("nav_title") or page.title)}</span>')
    breadcrumbs = '<nav class="breadcrumbs" aria-label="Breadcrumbs">' + '<span class="sep">›</span>'.join(crumbs) + "</nav>"

    # level + meta row
    level = page.meta.get("level", "")
    meta_bits = []
    if level:
        meta_bits.append(f'<span class="level level-{level.lower()}" title="Level">{esc(level)}</span>')
    if page.id != "index":
        meta_bits.append(f'<span class="meta-sec">{esc(section_title(ctx, page.section))}</span>')
        mins = max(1, round(page.words_main / 200))
        dd = round((page.words - page.words_main) / 200)
        extra = f" + {dd} min deep dives" if dd >= 1 else ""
        meta_bits.append(f'<span class="meta-time">about {mins} min read{extra}</span>')
    if page.has_deepdive:
        meta_bits.append('<button type="button" class="dd-toggle-all">Open all deep dives</button>')
    meta_row = f'<div class="page-meta">{"".join(meta_bits)}</div>' if meta_bits else ""
    ci = commit_info()
    t_url = tree_url()
    version_line = (f'<p class="code-version">Code version: {esc(PROJECT)} @ <a href="{t_url}" target="_blank" rel="noopener" '
                    f'title="{SHA}"><code>{SHORT_SHA}</code></a>{" · " + esc(ci["day"]) if ci["day"] else ""}</p>')
    foot_commit = (f'Code version: <a href="{t_url}" target="_blank" rel="noopener"><code class="foot-sha">{SHA}</code></a>'
                   f'{" · " + esc(ci["date"]) if ci["date"] else ""}'
                   f'{" · “" + esc(ci["subject"]) + "”" if ci["subject"] else ""}'
                   f' · <a href="{href(page.id, "index")}#code-version">How to study this version</a>')

    # before you read
    prereq_html = ""
    prereqs = page.listify("prerequisites")
    if prereqs:
        lis = []
        for pid in prereqs:
            if not ctx.known(pid):
                R.error(where, f"prerequisites: unknown page id {pid!r}{suggest(pid, list(ctx.pages) + list(ctx.entries))}")
                continue
            if ctx.live(pid):
                lvl = ctx.pages[pid].meta.get("level", "")
                badge = f' <span class="level level-{lvl.lower()} level-sm">{esc(lvl)}</span>' if lvl else ""
                lis.append(f'<li><a href="{href(page.id, pid)}">{esc(ctx.title_of(pid))}</a>{badge}</li>')
            else:
                R.warn(where, f"prerequisite {pid!r} is not written yet")
                lis.append(f'<li><span class="soon-link">{esc(ctx.title_of(pid))}</span> <span class="soon-tag">soon</span></li>')
        prereq_html = ('<aside class="before-read"><p class="before-read-title">Before you read</p>'
                       f'<p>This page uses ideas from these pages:</p><ul>{"".join(lis)}</ul></aside>')
    elif page.meta.get("prerequisites", "").strip().lower() == "none":
        prereq_html = ('<aside class="before-read"><p class="before-read-title">Before you read</p>'
                       "<p>You do not need to read other pages first.</p></aside>")

    # related
    related_html = ""
    rel_ids = page.listify("related")
    if rel_ids:
        lis = []
        for pid in rel_ids:
            if not ctx.known(pid):
                R.error(where, f"related: unknown page id {pid!r}{suggest(pid, list(ctx.pages) + list(ctx.entries))}")
                continue
            if ctx.live(pid):
                summ = ctx.pages[pid].meta.get("summary", "")
                lis.append(f'<li><a href="{href(page.id, pid)}">{esc(ctx.title_of(pid))}</a>'
                           f'<span class="rel-sum">{esc(summ)}</span></li>')
            else:
                lis.append(f'<li><span class="soon-link">{esc(ctx.title_of(pid))}</span> <span class="soon-tag">soon</span></li>')
        related_html = f'<section class="related"><h2 id="related-pages">Related pages</h2><ul>{"".join(lis)}</ul></section>'
        page.headings.append((2, "related-pages", "Related pages"))

    # prev / next
    live_order = [p for p in order if ctx.live(p)]
    prev_id = next_id = None
    if page.id in live_order:
        i = live_order.index(page.id)
        prev_id = live_order[i - 1] if i > 0 else None
        next_id = live_order[i + 1] if i + 1 < len(live_order) else None
    for key in ("prev", "next"):
        v = page.meta.get(key)
        if v:
            if v.lower() == "none":
                prev_id = None if key == "prev" else prev_id
                next_id = None if key == "next" else next_id
            elif not ctx.live(v):
                R.error(where, f"{key}: {v!r} is not a written page")
            elif key == "prev":
                prev_id = v
            else:
                next_id = v
    pn = []
    if prev_id:
        pn.append(f'<a class="pn pn-prev" href="{href(page.id, prev_id)}"><span class="pn-dir">← Previous</span>'
                  f'<span class="pn-title">{esc(ctx.title_of(prev_id))}</span></a>')
    else:
        pn.append("<span></span>")
    if next_id:
        pn.append(f'<a class="pn pn-next" href="{href(page.id, next_id)}"><span class="pn-dir">Next →</span>'
                  f'<span class="pn-title">{esc(ctx.title_of(next_id))}</span></a>')
    prevnext = f'<nav class="prevnext" aria-label="Previous and next page">{"".join(pn)}</nav>'

    toc = render_toc(page)
    has_code = 'class="language-' in page.html_body
    prism = ""
    if has_code:
        prism = "\n".join(f'<script src="{PRISM}/components/{c}.min.js" defer></script>' for c in PRISM_COMPONENTS)
    page_css = f'\n<link rel="stylesheet" href="{pre}assets/{VIZ_CSS}">' if page.has_viz_css else ""
    page_js = ""
    for js in page.listify("scripts"):
        if not js.endswith(".js") or ".." in Path(js).parts or js.startswith("/"):
            R.error(where, f"scripts: {js!r} must be a .js path inside assets/, for example viz/kv_allocator.js")
        elif not (ASSETS / js).is_file():
            R.error(where, f"scripts: assets/{js} does not exist")
        else:
            page_js += f'\n<script src="{pre}assets/{esc(js)}" defer></script>'
    title_full = SITE_NAME if page.id == "index" else f"{page.title} · {SITE_NAME}"
    desc = page.meta.get("summary", "")
    built = time.strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title_full)}</title>
<meta name="description" content="{esc(desc)}">
<script>try{{var t=localStorage.getItem("explainer-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}}catch(e){{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400..700;1,14..32,400..700&amp;display=swap">
<link rel="stylesheet" href="{pre}assets/site.css">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">{page_css}
</head>
<body data-root="{pre}" data-page="{esc(page.id)}">
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <button type="button" class="menu-btn" aria-label="Open navigation" aria-controls="sidebar" aria-expanded="false"><span></span><span></span><span></span></button>
  <a class="brand" href="{href(page.id, "index")}"><span class="brand-mark" aria-hidden="true">{esc(BRAND_MARK)}</span><span class="brand-name">{SITE_NAME}</span></a>
  <div class="search" role="search">
    <input type="search" id="search-input" placeholder="Search  ( / )" aria-label="Search the site" autocomplete="off" spellcheck="false">
    <div class="search-results" id="search-results" role="listbox" hidden></div>
  </div>
  <button type="button" class="theme-btn" aria-label="Switch between light and dark mode" title="Light / dark mode">
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" fill="currentColor"/></svg>
  </button>
</header>
<div class="layout">
<aside class="sidebar" id="sidebar" aria-label="Site navigation">
<nav>
{render_sidebar(ctx, page)}
</nav>
</aside>
<div class="scrim" hidden></div>
<main id="main" class="main">
<article class="article">
{breadcrumbs}
<h1 class="page-title">{esc(page.title)}</h1>
{meta_row}
{version_line}
{prereq_html}
{page.html_body}
{related_html}
{prevnext}
<footer class="page-foot"><p class="foot-commit">{foot_commit}</p><p>Source: <a href="{REPO_URL}" target="_blank" rel="noopener">{esc(REPO_LABEL)}</a> · Built {built} · Code excerpts are copied from the repo at this commit by the build.</p></footer>
</article>
{toc}
</main>
</div>
<div class="lightbox" hidden><div class="lightbox-bar"><span class="lightbox-hint">Scroll to pan. Press Esc to close.</span><button type="button" class="lightbox-close">Close ✕</button></div><div class="lightbox-body"></div></div>
<div class="tooltip" role="tooltip" id="term-tooltip" hidden></div>
<script src="{pre}assets/search-index.js" defer></script>
<script src="{pre}assets/site.js" defer></script>{page_js}
{prism}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def template_checks(page: Page) -> None:
    if page.section not in TEMPLATE_SECTIONS or page.meta.get("checks", "").lower() == "off":
        return
    b = page.body
    w = page.where
    if page.section in ("learn", "concepts") and "<x-sentence" not in b:
        R.warn(w, "template: no <x-sentence> ('In one sentence')")
    if "<x-diagram" not in b:
        R.warn(w, "template: no <x-diagram>")
    if page.section in ("concepts", "tours") and "<x-code" not in b:
        R.warn(w, "template: no <x-code> excerpt")
    if "<x-deepdive" not in b:
        R.warn(w, "template: no <x-deepdive>")
    n = getattr(page, "_quiz_count", 0)
    if not 3 <= n <= 5:
        R.warn(w, f"template: 'Check yourself' has {n} questions; use 3 to 5")
    if not page.meta.get("prerequisites"):
        R.warn(w, "template: no 'prerequisites:' (write 'prerequisites: none' if there are none)")


def ste_check(page: Page) -> None:
    """Warn about sentences longer than the ASD-STE100 limit (STYLE.md section 6)."""
    if not STE_CHECK or page.src is None or page.section not in TEMPLATE_SECTIONS or page.meta.get("checks", "").lower() == "off":
        return
    t = page.body
    t = re.sub(r"<x-code\b.*?(?:/>|</x-code>)", " ", t, flags=re.S)
    t = re.sub(r"<pre\b.*?</pre>|<table\b.*?</table>", " ", t, flags=re.S)
    t = re.sub(r"<x-diagram\b.*?/>", " ", t, flags=re.S)
    t = re.sub(r"<x-(?:viz|img)\b" + ATTRS + r"/?>", " ", t)
    t = re.sub(r"\{\{\s*cite[^}]*\}\}", " ", t)
    t = re.sub(r"\{\{\s*\w+\s+[^}|]*\|\s*([^}]*)\}\}", r"\1", t)
    t = re.sub(r"\{\{\s*\w+\s+([^}|]*)\}\}", r"\1", t)
    t = re.sub(r"<code>(.*?)</code>", lambda m: m.group(1).replace(" ", "_"), t, flags=re.S)
    t = re.sub(r"</(?:p|li|h2|h3|h4|dt|dd|x-sentence|x-q|x-a)>|<br\s*/?>|<(?:ul|ol)\b", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    for block in t.split("\n"):
        for sent in re.split(r"(?<=[.!?])\s+", " ".join(block.split())):
            n = len(re.findall(r"[\w'’-]+", sent))
            if n > STE_MAX_WORDS:
                R.warn(page.where, f"STE: sentence has {n} words (max {STE_MAX_WORDS}): {sent[:90]!r}...")


def check_links(rendered: dict[str, str], ids: dict[str, set[str]], extra_files: set[str]) -> None:
    for out_rel, doc in rendered.items():
        base = Path(out_rel).parent
        for m in re.finditer(r'\b(?:href|src)="([^"]+)"', doc):
            url = html.unescape(m.group(1))
            if re.match(r"^(https?:|mailto:|data:|javascript:)", url):
                if url.startswith("http:"):
                    R.warn(f"site/{out_rel}", f"insecure link {url}")
                continue
            path, _, anchor = url.partition("#")
            if not path:
                target = out_rel
            else:
                target = os.path.normpath((base / path).as_posix()).replace("\\", "/")
            if target.startswith(".."):
                R.error(f"site/{out_rel}", f"link leaves the site folder: {url}")
                continue
            if target not in rendered and target not in extra_files:
                R.error(f"site/{out_rel}", f"broken link: {url}")
                continue
            if anchor and target in ids and anchor not in ids[target]:
                R.error(f"site/{out_rel}", f"broken anchor: {url} (no id={anchor!r} in {target})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--force-diagrams", action="store_true", help="re-run all diagram scripts")
    ap.add_argument("--preview", action="store_true",
                    help="write site/ even when there are errors (to preview your pages while another page is broken)")
    args = ap.parse_args()
    t0 = time.time()

    if not REPO.is_dir():
        print(f"ERROR   repo not found at {REPO}")
        return 1
    check_repo_sha()
    diagrams = run_diagrams(args.force_diagrams)
    sections, entries = load_sections()
    glossary = load_glossary()
    pages = load_pages()
    ctx = Ctx(pages, entries, sections, glossary, diagrams)
    if "index" not in pages:
        R.error("src/index.html", "the home page is missing")

    # generated pages
    gp = glossary_page(ctx)
    pages[gp.id] = gp
    for pid in list(pages):
        p = pages[pid]
        if pid != "index" and pid not in GENERATED:
            if not p.meta.get("title"):
                R.error(p.where, "front matter needs 'title:'")
            if not p.meta.get("summary"):
                R.error(p.where, "front matter needs 'summary:' (one sentence, used for search and cards)")
            lvl = p.meta.get("level", "")
            if p.section in SECTIONS_NEED_LEVEL and lvl not in LEVELS:
                R.error(p.where, f"front matter needs 'level:' Beginner, Intermediate or Advanced (got {lvl!r})")
            elif lvl and lvl not in LEVELS:
                R.error(p.where, f"level {lvl!r}: use Beginner, Intermediate or Advanced")
            if p.meta.get("section") and p.meta["section"] != p.section:
                R.error(p.where, f"section: {p.meta['section']!r} does not match the folder {p.section!r}")
    insert_unlisted(ctx)

    for p in pages.values():
        render_body(ctx, p)
        template_checks(p)
        ste_check(p)

    order = nav_order(ctx)
    rendered: dict[str, str] = {}
    ids: dict[str, set[str]] = {}
    for p in pages.values():
        doc = render_page(ctx, p, order)
        rendered[p.out_rel] = doc
        all_ids = re.findall(r'\bid="([^"]+)"', re.sub(r"<svg\b.*?</svg>", "", doc, flags=re.S))
        dups = sorted({i for i in all_ids if all_ids.count(i) > 1})
        if dups:
            R.error(p.where, f"duplicate id(s) on the page: {', '.join(dups)} (give headings or quizzes unique ids)")
        ids[p.out_rel] = set(re.findall(r'\bid="([^"]+)"', doc))

    # files that will exist next to the pages
    extra: set[str] = set()
    for f in ASSETS.rglob("*"):
        if f.is_file():
            extra.add("assets/" + f.relative_to(ASSETS).as_posix())
    extra.add("assets/search-index.js")
    extra.add("assets/favicon.svg")
    for img in REPO_IMAGES:
        extra.add("assets/repo/" + img)
    for name in diagrams:
        extra.add(f"diagrams/{name}.svg")
    check_links(rendered, ids, extra)

    # search index
    index = []
    for p in pages.values():
        index.append({
            "k": "page", "t": p.title, "u": p.out_rel, "s": p.meta.get("summary", ""),
            "sec": section_title(ctx, p.section) if p.id != "index" else "Home",
            "lvl": p.meta.get("level", ""), "h": [h[2] for h in p.headings][:60],
        })
    for tid, e in sorted(glossary.items()):
        index.append({"k": "term", "t": e["term"], "u": f"reference/glossary.html#term-{tid}",
                      "s": e["short"], "a": e.get("aliases", [])})

    strict_fail = args.strict and R.warnings
    if R.errors or strict_fail:
        for w in R.warnings:
            print(w)
        for e in R.errors:
            print(e)
        print(f"\nBUILD FAILED: {len(R.errors)} error(s), {len(R.warnings)} warning(s)."
              + (" (--strict: warnings count as errors)" if strict_fail and not R.errors else ""))
        if not args.preview:
            return 1
        print("--preview: writing site/ anyway. Do not hand in work while the build has errors.")

    # write into a private temp folder, then swap it in, so that parallel builds do not clash
    out = ROOT / f".site-tmp-{os.getpid()}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(ASSETS, out / "assets")
    for img in sorted(REPO_IMAGES):
        dest = out / "assets" / "repo" / img
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / img, dest)
    (out / "diagrams").mkdir()
    for name, path in diagrams.items():
        shutil.copy2(path, out / "diagrams" / f"{name}.svg")
    for out_rel, doc in rendered.items():
        dest = out / out_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(doc, encoding="utf-8")
    (out / "assets" / "search-index.js").write_text(
        "window.EXPLAINER_SEARCH_INDEX = " + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (out / "assets" / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#1a5fb4"/>'
        '<text x="16" y="21" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="13" font-weight="bold" '
        f'fill="#ffffff" text-anchor="middle">{esc(BRAND_MARK[:3])}</text></svg>\n', encoding="utf-8")
    swap_in_site(out)

    for w in R.warnings:
        print(w)
    planned = sum(1 for e in ctx.entries.values() if not ctx.live(e.id))
    print(f"\nBuilt {len(rendered)} pages ({planned} planned pages shown as 'coming soon'), "
          f"{len(glossary)} glossary terms, {len(diagrams)} diagrams in {time.time() - t0:.1f}s.")
    if R.errors:
        print(f"PREVIEW ONLY: {len(R.errors)} error(s). Open site/index.html in a browser.")
        return 1
    print(f"{len(R.warnings)} warning(s), 0 errors. Open site/index.html in a browser.")
    return 0


def swap_in_site(new: Path) -> None:
    """Replace site/ with `new`. Retries, because another build can swap at the same time."""
    old = ROOT / f".site-old-{os.getpid()}"
    for attempt in range(20):
        try:
            if SITE.exists():
                os.replace(SITE, old)
            os.replace(new, SITE)
            break
        except OSError:
            time.sleep(0.25 * (attempt + 1))
    else:
        # last resort (e.g. a file in site/ is locked): copy over the old folder
        shutil.copytree(new, SITE, dirs_exist_ok=True)
        shutil.rmtree(new, ignore_errors=True)
    shutil.rmtree(old, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
