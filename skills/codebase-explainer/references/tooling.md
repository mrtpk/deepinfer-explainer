# Tooling: the starter kit, build.py, tags and generators

Read this when you set up the explainer repo, or when the build gives an error you do not understand.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 6. Tooling

### 6.1 The starter kit (`templates/`)

The skill folder has a generic starter kit in `templates/`. Copy all of it (with the hidden
`.gitignore`) into the new explainer folder:

```bash
cp -r <skill>/templates/. <project>-explainer/
```

Then fill in **one file**, `explainer.json`. It is the only place for project-specific values:

| Key | Meaning |
|---|---|
| `project` | Project name, used in the version line, `{{project name}}` and the default site name |
| `site_name` | Site title (default "`<project>` Explained") |
| `brand_mark` | 2-3 letters in the top bar and the generated favicon |
| `repo_path` | Path of the target repo checkout, relative to the explainer folder (or absolute) |
| `repo_url`, `repo_label`, `repo_host` | Code links; `repo_host` is `github`, `gitlab` or `gitea` |
| `sha` | Full 40-character pinned commit. The build fails if the checkout is at another commit |
| `language_style`, `ste_max_words` | `ste` (sentence-length check on) or `plain` |
| `comment_language` | Language of code comments that `<x-tr>` translates (label only) |
| `prism_components`, `lang_by_ext` | Code colours for the languages of the target repo |

What the kit contains:

| Path | What it is | What you change |
|---|---|---|
| `build.py` | the generator (section 6.3) | nothing, normally |
| `explainer.json` | project values | everything |
| `assets/site.css`, `assets/site.js` | the light article look, search, tooltips, quiz, lightbox | nothing, normally; add shared styles here, not in pages |
| `assets/viz/viz.css`, `assets/viz/example_stepper.js` | shared visual styles; ONE visual as a pattern | copy the pattern for each new visual |
| `diagrams/svglib.py`, `_template.py`, `example_flow.py` | diagram library (default width 1100), template, example | add one script per diagram; delete the example later |
| `tools/gen_folder_tree.py` | folder tree with file and line counts for `code/index`; pattern for all generators | folder descriptions in `DESCRIPTIONS` |
| `src/index.html` | home page skeleton, with `<x-version />` | all text; build the system map |
| `src/learn/example-basics.html`, `src/concepts/example-concept.html`, `src/tours/example-tour.html` | one example page per main type | replace them in Phase 1 |
| `src/code/index.html` | code-map page with generator markers | text around the markers |
| `src/_templates/` | starter pages (not built) | example paths |
| `src/nav/*.json`, `src/glossary/core.json` | nav and glossary examples | list every planned page; add core terms |
| `STYLE.md`, `instructions-svg.md` | writer's guide and diagram guide | `<Project>` names, vocabulary table, out-of-scope list |
| `plan.md`, `progress.md`, `notes/facts.md`, `README.md` | skeletons | fill in |

Test the kit after you fill in `explainer.json`:

```bash
python3 tools/gen_folder_tree.py && python3 build.py
```

The example pages cite `README.md` of the target repo, so the first build works on any repo that has a
`README.md` with at least 3 lines. Expected result: 0 errors and a few warnings for links to planned pages.

### 6.2 Folder layout

```
parent/
  {PROJECT}/                   target repo checkout at {SHA}, READ ONLY
  {project}-explainer/
    explainer.json             project name, target repo path and URL, pinned commit, language style
    build.py                   the generator (owner: foundation / supervisor)
    STYLE.md                   the writer's guide
    instructions-svg.md        the diagram style guide
    plan.md  progress.md       plan and progress log (tracking-files.md)
    README.md                  what the site is, code version, how to build
    notes/facts.md             shared verified facts (tracking-files.md)
    assets/                    site.css, site.js, favicon.svg
      viz/                     viz.css + one <name>.js per visual
      img/                     images for <x-img src="img/...">
    diagrams/                  svglib.py, _template.py, one <name>.py per diagram
    tools/                     generators (env vars, config tables, API tables)
    src/
      index.html               home page
      nav/<section>.json       one nav file per part: learn, concepts, tours, code, reference
      glossary/<file>.json     glossary entries; one file per owner; merged by the build
      _templates/              starter pages (not built: names that start with _ are skipped)
      learn/ concepts/ tours/ code/ reference/   page sources
    build/diagrams/            generated SVGs + .hash stamps (do not edit, not in git)
    site/                      generated site (do not edit)
```

### 6.3 `build.py` features

Python 3.11+, standard library only. Run from the explainer folder.

```bash
python3 build.py                   # build site/ (runs stale diagram scripts first)
python3 build.py --strict          # warnings also fail the build (use before hand-in)
python3 build.py --preview         # write site/ even with errors (one broken page must not block previews)
python3 build.py --force-diagrams  # run every diagram script again
```

What it does:
- **Config.** Reads `explainer.json`; stops with a clear message when a key is missing or the SHA is not 40 hex characters.
- **Pinned-commit check.** Runs `git -C <repo_path> rev-parse HEAD`. If HEAD is not `SHA`, it is an
  error: line numbers would be wrong.
- **Version line and footer.** Reads date and subject of `SHA` with `git log` and puts them on every page.
- **Code-version block.** `<x-version />` writes the commit table, checkout commands, the submodule pins
  (from `git ls-tree` and `.gitmodules`) and a line-number note. `{{project ...}}` inserts project values.
- **Favicon.** Generated from `brand_mark`.
- **Page loading.** `src/**/*.html` with front matter. Unknown front matter keys are errors.
  Checks `title`, `summary`, `level` (required for learn/concepts/tours), and the section.
- **Navigation.** `src/nav/*.json` lists all planned pages with fixed ids. A listed page with no file
  shows as grey "soon". `nav_after:` inserts an unlisted page. Previous/next follow the sidebar order.
- **Code excerpts.** `<x-code>` reads the real lines from the checkout. It checks the file, the range, the
  highlight lines and the `<x-tr>` lines. Warns above 120 lines. Each excerpt links to GitHub at `SHA`.
- **Citations.** `{{cite path:line}}`, ranges, folders, whole files. Fails on a bad path or range.
- **Glossary.** Merges `src/glossary/*.json`. A duplicate id is an error (with the file that has it).
  Ids must be lower-case. Warns when `short` is over 220 characters. Unknown `{{term}}` ids are errors,
  with close-match suggestions. Generates `reference/glossary` (A-Z, aliases, "Read more" links).
- **Diagrams.** Runs `diagrams/*.py` (not `svglib.py`, not names with `_`) only when stale.
  Staleness = **SHA-256 content hash** of the script + `svglib.py`, stored as `build/diagrams/<name>.hash`
  (mtime is not reliable on Windows mounts such as `/mnt/c`). Puts the SVG inline, with ids prefixed per
  diagram so two diagrams on a page do not clash. Warns if the width is not 1100 and passes on svglib
  edge warnings.
- **Visuals and images.** `<x-viz>` needs `scripts:` in the front matter, and the script must exist.
  `<x-img repo=...>` copies a repo image into `site/assets/repo/` with a source link.
- **Template checks** (warnings) on learn/concepts/tours: no sentence, no diagram, no code (concepts,
  tours), no deep dive, not 3-5 quiz questions, no `prerequisites:`. `checks: off` turns them off.
- **STE check** (warning): descriptive sentences over 25 words, outside code, tables and citations.
- **Link check** on the rendered HTML: every relative `href`/`src`, every `#anchor`, links that leave the
  site folder, `http:` links (warning). Duplicate ids on a page are errors.
- **Search index** as `assets/search-index.js` (a `.json` file does not load from `file://`):
  pages (title, summary, part, level, headings) and glossary terms (with aliases).
- **Atomic site swap.** Writes into `.site-tmp-<pid>/`, then renames it over `site/` with retries.
  Parallel builds by several writers do not delete each other's output.
- **Reading time** for the main text and for the deep dives, separately.
- Exit code 1 on errors (also with `--preview`, after it writes the site).

### 6.4 Front matter

```html
---
title: Hardware platforms: NVIDIA and Ascend
nav_title: NVIDIA and Ascend
level: Intermediate
prerequisites: learn/gpus-kernels, learn/parallelism
related: concepts/tilelang-kernels, code/platform
summary: One or two sentences. Used by search, related-page cards and <meta description>.
scripts: viz/kv_allocator.js
---
```

Keys: `title` (required), `summary` (required), `level` (learn/concepts/tours), `prerequisites`
(ids or `none`), `related`, `nav_title`, `nav_after`, `prev`, `next` (id or `none`), `checks` (`off`),
`scripts` (JS paths inside `assets/`), `section` (must match the folder). One `key: value` per line.
The page id is the path without `.html` (`src/concepts/scheduler.html` → `concepts/scheduler`).
Do not write an `<h1>`. Use `<h2>` and `<h3>`; the build adds ids and the table of contents.

### 6.5 Custom tag reference

Attribute values use double quotes. Self-closing tags end with `/>`. Plain HTML works everywhere.
Inline tags are not expanded inside `<pre>` and excerpts. Write `\{{` for a literal `{{`.

| Tag | Syntax | Result |
|---|---|---|
| Code excerpt | `<x-code file="pkg/x.py" lines="55-83" highlight="57-58,63" caption="..." title="..." lang="cpp" />` | exact lines from the checkout, line numbers, highlights, GitHub link, copy button |
| Translated comment | `<x-code ...><x-tr line="24">English text.</x-tr></x-code>` | "Translated comments" list under the code |
| Citation | `{{cite pkg/x.py:223}}`, `{{cite pkg/x.py:222-227}}`, `{{cite pkg/x.py:222 \| get_platform()}}`, `{{cite pkg/dir/}}`, `{{cite .gitmodules}}` | link to GitHub at `SHA`; checked |
| Glossary term | `{{term nccl}}`, `{{term kernel \| kernels}}` | dotted underline + tooltip; checked |
| Internal link | `{{link concepts/scheduler}}`, `{{link concepts/x \| text}}`, `{{link concepts/x#anchor}}` | relative link with the page title; checked; grey "coming soon" if not written |
| Diagram | `<x-diagram name="platform_select" alt="..." caption="Figure: ..." />` | inline SVG on a white card; click = lightbox; "Open full size" |
| Sentence | `<x-sentence>...</x-sentence>` | "In one sentence" block |
| Note | `<x-note title="...">...</x-note>` | blue callout |
| Simplified | `<x-simplified>...</x-simplified>` | dashed gray callout |
| Warning | `<x-warning title="...">...</x-warning>` | amber callout |
| Deep dive | `<x-deepdive title="..." open="yes">...</x-deepdive>` | collapsible teal block; title in the TOC |
| Quiz | `<x-quiz heading="none"><x-q level="easy">Q?<x-a><p>A.</p></x-a></x-q></x-quiz>` | "Check yourself" list with "Show answer" and "Show all answers" |
| Tour stop | `<x-stop n="1" title="...">...</x-stop>` | numbered `<h2>` section with id `stop-1` |
| Visual | `<x-viz id="kv-allocator" title="..." caption="..." />` (optional fallback HTML inside) | card with mount `div[data-viz="kv-allocator"]`; loads `viz.css` |
| Image | `<x-img repo="doc/images/a.png" alt="..." caption="..." width="900" />` or `src="img/x.png"` | image on a white card; repo images get a source link |
| Project value | `{{project name}}`, `{{project short_sha}}` (also `sha`, `site`, `repo_url`, `date`, `day`, `subject`) | text from `explainer.json` and git; not inside `<pre>` |
| Code version | `<x-version />` (home page only) | commit table, checkout commands, submodule pins, line-number note |

### 6.6 Nav and glossary files

`src/nav/concepts.json`:
```json
{
  "_owner": "Concept writers. Page ids are fixed; create src/concepts/<id>.html to make an entry live.",
  "section": "concepts",
  "title": "{PROJECT} concepts",
  "order": 2,
  "groups": [
    {"title": "Engine", "pages": [
      {"id": "concepts/engine-step-loop", "title": "Offline API and the step loop"}
    ]}
  ]
}
```
A part with no groups uses `"pages": [...]` directly. Ids start with the section name. Keys that start
with `_` are comments. **Write all nav files in Phase 1 with every planned page.** Then writers link to
pages that do not exist yet, and nobody edits another writer's nav file.

`src/glossary/<owner>.json`:
```json
{
  "_about": "Owner: batch B3a. Search all glossary files before you add a term.",
  "nccl": {
    "term": "NCCL",
    "short": "One or two sentences, under 220 characters. This is the tooltip.",
    "long": "Optional HTML. Inline tags work: {{cite pkg/platform.py:58}}.",
    "aliases": ["nccl backend"],
    "page": "concepts/hardware-platforms"
  }
}
```
**Glossary ownership.** `core.json` has general terms and belongs to the supervisor. Each batch owns one
file (`b1.json`, `b3a.json`, ...). A writer adds terms only to its own file. Duplicate ids are a build
error. When two batches run in parallel, they can both add the same term: the second build fails at merge
time. Fix: before a wave starts, give each term to one batch in the writer prompt, and tell writers to
search all glossary files before they add a term.

### 6.7 Reference generators

Generate every reference table that the code can give. The kit includes `tools/gen_folder_tree.py`
(the `code/index` tree); copy its pattern. The DeepInfer project also had `tools/gen_env_vars.py`
(all env vars, parsed with `ast`), which works like this:
- Parse the source with `ast` (Python) or a regex (C/C++ `getenv`, other languages).
  Get name, group, line, type and default.
- Scan the repo for every read site. Mark reads at import time (module body, class body, default arguments).
- Merge with a hand-written dict of STE text per item (`does`, `cites`, `page`).
- Check: every declared item has text; every cited line exists; warn if a cited range does not contain
  the name.
- Write HTML between `<!-- BEGIN GENERATED ... -->` markers in the page source.
- Flags: `--check` (exit 1 if the page is out of date), `--report` (print all use sites for review).

Other generators to consider: config dataclass fields and defaults; CLI flags (`argparse` calls); public
API from stubs (`.pyi`) or headers; registry tables (model architectures, plugins); folder tree counts
for `code/index` (files and lines per folder; say on the page how you counted).

### 6.8 Site check (browser)

Use Playwright (`npm install playwright-core` in a scratch folder, plus a Chromium build). If Chromium
fails with a missing shared library (for example `libnspr4.so` on WSL), extract the library packages into
a scratch folder and set `LD_LIBRARY_PATH`. Keep the check scripts in the scratchpad, and give each run
its own output file name (a shared fixed file name raced between parallel runs).
For every page, at 1280 px and 390 px width, with all deep dives open:
- horizontal page overflow (`document.documentElement.scrollWidth > window.innerWidth`);
- console errors and page errors;
- all internal links and anchors resolve;
- every glossary term link has an entry;
- each visual renders and reacts to a click;
- screenshots of a sample (light and dark) for the supervisor to look at.
Known false alarms: a headless browser may lack a CJK font (Chinese shows as boxes in screenshots only);
`loading="lazy"` images may be blank in full-page screenshots.

---
