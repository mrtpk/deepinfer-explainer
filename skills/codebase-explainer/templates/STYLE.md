# <Project> Explained — Writer's guide

> Template note: replace `<Project>`, `<project>`, the sample page names, the vocabulary table (section 6)
> and the out-of-scope list (section 7, rule 5) for your project. Keep the rest.

This guide is for everyone who writes pages, glossary entries or diagrams for the site.
Read all of it before you write your first page. Then copy the sample page
`src/concepts/example-concept.html` (replace it with the Phase 1 reference page) — it uses every part of this guide.

Contents

1. Quick start
2. Files, folders and ownership (how parallel writers avoid conflicts)
3. Page source format (front matter)
4. Page templates (concept, basics, tour, code map, reference)
5. Tag reference (copy-paste syntax)
6. Writing rules (ASD-STE100)
7. Accuracy rules
8. Glossary
9. Navigation
10. Diagrams
11. Build errors and warnings
12. Checklist before you hand in

---

## 1. Quick start

```bash
cd <project>-explainer
python3 build.py                 # build site/ (runs stale diagram scripts first)
python3 build.py --strict        # also fail on warnings (use before hand-in)
python3 build.py --force-diagrams
python3 build.py --preview         # write site/ even if another writer's page has an error
python3 tools/gen_folder_tree.py   # update the code-map folder tree (src/code/index.html)
```

Open `site/index.html` with a double-click. The site works from disk (`file://`).

- Source repo (READ ONLY): `repo_path` in `explainer.json`, pinned to the commit `sha` in `explainer.json`.
  The build stops if the repo is at another commit.
- Python 3 standard library only. No `pip install`.
- Never edit `site/` or `build/`. The build deletes and rewrites `site/` on every run.

## 2. Files, folders and ownership

```
<project>-explainer/
  explainer.json         project name, target repo path and URL, pinned commit (owner: supervisor)
  build.py               the generator (owner: foundation; do not edit without asking the supervisor)
  STYLE.md               this guide
  instructions-svg.md    the binding colour, font and diagram guide
  assets/                site.css, site.js, favicon (owner: foundation)
    viz/                 interactive visuals: viz.css (shared viz styles) + one <name>.js per visual (section 10)
    img/                 images for <x-img src="img/..."> (section 5.10)
  diagrams/
    svglib.py            diagram helper library (owner: foundation)
    _template.py         copy this to start a diagram (files that start with _ are not run)
    <name>.py            ONE script per diagram, owned by the page writer
  src/
    index.html           home page
    nav/<section>.json   ONE nav file per section: learn, concepts, tours, code, reference
    glossary/<file>.json glossary entries; the build merges all files
    _templates/          concept.html and tour.html starter pages (not built)
    learn/<id>.html      Part 1 pages
    concepts/<id>.html   Part 2 pages
    tours/<id>.html      Part 3 pages
    code/<id>.html       Part 4 pages
    reference/<id>.html  Part 5 pages (reference/glossary is generated, do not write it)
  build/diagrams/        generated SVGs (do not edit)
  site/                  generated website (do not edit)
```

**How parallel writers avoid editing the same file**

- **Pages.** Each page is its own file. The page id is the path without `.html`
  (`src/concepts/request-flow.html` → id `concepts/request-flow`). Write only the pages you own.
- **Navigation.** All planned pages are already listed in `src/nav/*.json`, with fixed ids.
  When you create a file with a listed id, its sidebar entry becomes live. You do **not** need to edit
  the nav file. If you must add a page that is not listed, do not edit another writer's nav file:
  put `nav_after: <existing id>` in your page front matter (section 9).
- **Glossary.** The build merges every `src/glossary/*.json` file. Each writer owns one file, for
  example `src/glossary/b1.json`, `src/glossary/b3a.json` (one file per batch).
  `core.json` (general terms) already exists and belongs to the supervisor. Search all glossary files before you
  add a term. A duplicate id stops the build. If an existing definition is wrong, tell the supervisor;
  do not redefine it.
- **Diagrams.** One script per diagram, named after its page or topic (`diagrams/b3a_request_flow.py`).
  Use a prefix that belongs to you, so two writers never pick the same name.
- **Links to pages that do not exist yet** are allowed. They render as grey "coming soon" text and give
  a warning, not an error. So you can link to pages that another writer writes at the same time.

## 3. Page source format

A page is an HTML fragment with a front matter block at the top:

```html
---
title: The request flow: from the API call to the result
nav_title: The request flow
level: Intermediate
prerequisites: learn/example-basics
related: tours/example-tour, code/engine
summary: One request goes through four parts of <Project>. This page shows each part and the file that implements it.
---
<x-sentence>...</x-sentence>
<h2>The idea</h2>
...
```

| Key | Required | Meaning |
|---|---|---|
| `title` | yes | Page title (h1 and browser tab: "Title · <Project> Explained"). |
| `summary` | yes | One or two sentences. Used by search, related-page cards and `<meta description>`. |
| `level` | learn, concepts, tours | `Beginner`, `Intermediate` or `Advanced`. Optional elsewhere. |
| `prerequisites` | template pages | Comma-separated page ids, or `none`. Makes the "Before you read" box. |
| `related` | no | Comma-separated page ids. Makes the "Related pages" list at the end. |
| `nav_title` | no | Shorter title for the sidebar and breadcrumbs. |
| `nav_after` | no | Only for pages that are not in a nav file: insert after this id. |
| `prev`, `next` | no | Override the previous/next buttons (page id or `none`). Normally they follow the nav order. |
| `checks` | no | `off` turns off the template warnings (use only with a reason). |
| `scripts` | no | Comma-separated JS files inside `assets/`, for example `viz/example_stepper.js`. Loaded with `defer` on this page only (section 5.9). |

One `key: value` per line. Values are one line. Unknown keys stop the build.

The build adds: the level badge, breadcrumbs, "Before you read", reading time, the "On this page"
table of contents (from `<h2>` and `<h3>`), related pages, previous/next buttons and the search entry.
**Do not write an `<h1>`.** Use `<h2>` for sections and `<h3>` for sub-sections. The build adds ids
to headings; write `id="..."` yourself only when you link to the heading.

## 4. Page templates

Starter files: `src/_templates/concept.html`, `src/_templates/tour.html`.

### 4.1 Concept and basics pages (sections `concepts`, `learn`)

Use these parts in this order. Use the `<h2>` texts exactly as shown, so every page looks the same.

| # | Part | How |
|---|---|---|
| 1 | Level badge | front matter `level:` (automatic) |
| 2 | Before you read | front matter `prerequisites:` (automatic) |
| 3 | In one sentence | `<x-sentence>` — max 25 words |
| 4 | **The idea** | `<h2>The idea</h2>` — plain explanation, then one everyday comparison (analogy). Say where the analogy stops being true. |
| 5 | **The picture** | `<h2>The picture</h2>` + `<x-diagram>` + 2-3 sentences on how to read it |
| 6 | **In the code** | `<h2>In the code</h2>` — `<h3>Step N: ...</h3>` sub-sections, each with real excerpts (`<x-code>`) and citations (`{{cite}}`). Basics pages (`learn/`) use `<h2>In <Project></h2>` instead: a short section at the end with 1–3 cited pointers into the code and links to concept pages. |
| 7 | **Deep dive** | `<h2>Deep dive</h2>` + one or more `<x-deepdive>` blocks. FULL detail (see below). |
| 8 | **What can go wrong** | `<h2>What can go wrong</h2>` — failure modes with citations, then **Why it matters.** |
| 9 | Check yourself | `<x-quiz>` with 3-5 questions: mix easy, medium and hard. The heading is automatic. |
| 10 | Related pages, next/previous | front matter `related:` (automatic) |

**What goes in a deep dive.** The reader studies with this site. A deep dive must give the full
technical detail, not a longer summary:

- exact shapes, types and sizes (for example `int32 [num_tokens, 4]`, or a struct layout), with a worked example with real numbers;
- memory layouts (row-major, packed, padded; who writes which byte);
- the algorithm step by step, as a numbered list;
- edge cases and error paths (what raises, what only warns);
- related environment variables and config fields, with defaults and the line that reads them;
- design trade-offs (why this way, what the alternative costs), only if the code or docs support it;
- numbers from `doc/` (cite the line);
- long code read line by line: show the excerpt, then a numbered list "Line 13. ...".

Split long detail into several `<x-deepdive>` blocks, one topic each, with a clear title. A deep dive
may contain code, tables, callouts and lists. Do not put a quiz inside a deep dive.

### 4.2 Tours (section `tours`)

Same front matter and the same first parts (sentence, idea, picture). Then numbered stops instead of
"In the code":

```html
<x-stop n="1" title="The user calls llm.generate()">
  <p>Where we are, and why this step exists.</p>
  <x-code file="pkg/api.py" lines="100-120" highlight="110" />
  <p>What the excerpt does.</p>
  <x-deepdive title="Stop 1 in detail"> ... </x-deepdive>
</x-stop>
```

Each stop is an `<h2>` in the table of contents. End with "What can go wrong" and `<x-quiz>`.
Stops run in code order. Each stop names the file and function where the reader is.

### 4.3 Code map pages (section `code`)

The model page is `src/code/llm-engine.html`. Copy its structure.

Front matter: `title: <path>: <main thing>`, `nav_title: <short path>`, `level`, `prerequisites`,
`related`, `summary`.

`<h2>` parts, in order:
1. **Purpose**: one sentence, then an "at a glance" table: File (lines, origin), Main class, Runs in
   (process / thread / device), Called by, Calls, Not in this file.
2. **Where it sits**: optional diagram, then `<h3>Who calls it</h3>` and `<h3>What it calls</h3>`, all cited.
3. **Key classes and functions**: table of name | `{{cite}}` line | one-line role.
4. **Walk through the main methods**: one `<h3>` per method, with `<x-code>` (40 lines or fewer) and a
   numbered "Line N" list. Put warnings before the step they concern.
5. **Deep dive**: `<x-deepdive>` blocks for data flow (types and shapes table), processes and threads,
   interaction with other subsystems, a worked example with numbers, an error-path table (raises or
   logs), and environment variables (default, read-at line, effect).
6. **Related concepts**: a list of links.
7. `<x-quiz>` with 3-5 questions. At least one question needs the deep dive.

Small modules (under ~150 lines) can merge parts 3 and 4.

### 4.4 Reference pages (section `reference`)

Free structure: tables, grouped lists. Every row that states a default or a location has a citation.

## 5. Tag reference

General rules for all custom tags:

- Attribute values use **double quotes**: `lines="10-20"`. A `>` inside quotes is fine
  (`caption="<code>x</code>"`). For a double quote inside a value, write `&quot;`.
- Self-closing tags end with `/>`. A tag with content needs its closing tag.
- Plain HTML is allowed everywhere: `<p>`, `<ul>`, `<ol>`, `<table>`, `<code>`, `<strong>`, `<em>`, `<pre>`.
- Inline tags (`{{...}}`) are not expanded inside `<pre>` blocks and code excerpts.
  To write a literal `{{`, write `\{{`.

### 5.1 Code excerpt — `<x-code>`

The build reads the REAL lines from the target repo checkout. Line numbers in the block match the file. The
header shows `path:start-end` and links to GitHub at the pinned commit.

```html
<x-code file="pkg/engine.py" lines="222-227" />
<x-code file="pkg/engine.py" lines="55-83" highlight="57-58,63,80-82" caption="Short note on what to look at." />
<x-code file="native/queue.hpp" lines="26-32" title="The queue" lang="cpp" />
```

| Attribute | Required | Meaning |
|---|---|---|
| `file` | yes | Repo-relative path. |
| `lines` | yes | `start-end` or a single line. Must exist. Keep excerpts under ~40 lines in the main text; longer ones go into a deep dive (warning above 120). |
| `highlight` | no | Lines or ranges inside `lines`, comma-separated. |
| `caption` | no | HTML; inline tags such as `{{cite}}` work here. |
| `title` | no | Short bold label before the path. |
| `lang` | no | Override the language (`python`, `cpp`, `bash`, `json`, `none`). Default from the file extension. |

**Comments in another language** (set `comment_language` in `explainer.json`). Add translations as children. They show under the code:

```html
<x-code file="pkg/__init__.py" lines="9-32" highlight="15">
  <x-tr line="24">No device found: use the CPU as the default.</x-tr>
  <x-tr line="28-29">Build outputs are stored per platform ...</x-tr>
</x-code>
```

For a single comment in running text, write: `Translated: <em>"..."</em> ({{cite path:line}})`.

For example commands that are not in the repo, use a plain block:
`<pre><code class="language-bash">python3 examples/quickstart.py</code></pre>`.

### 5.2 Citation — `{{cite ...}}`

```html
{{cite pkg/engine.py:223}}                 → link "pkg/engine.py:223"
{{cite pkg/engine.py:222-227}}             → link to a line range
{{cite pkg/engine.py:222 | Engine.step()}} → custom link text
{{cite pkg/backends/}}                     → link to a folder (no line)
{{cite .gitmodules}}                          → link to a whole file
```

The build fails if the file does not exist or the lines are out of range. Put citations in
parentheses after the claim: `... uses a thread pool ({{cite pkg/engine.py:89}}).`

### 5.3 Glossary term — `{{term ...}}`

```html
{{term kv-store}}              → shows the glossary "term" text ("KV store"), with a tooltip
{{term kernel | kernels}}      → custom text (plural, other case)
```

The id must exist in `src/glossary/*.json` (the build suggests close matches). Link a term at its
**first use on the page** (and again in a deep dive if it is far away). Do not link every use.

### 5.4 Internal link — `{{link ...}}`

```html
{{link concepts/request-flow}}                  → link text = that page's title
{{link concepts/request-flow | the flow}}      → custom text
{{link concepts/request-flow#the-picture}}     → link to a heading id (checked)
```

Never write `<a href="../concepts/x.html">` by hand; `{{link}}` makes the right relative path.
(Hand-written relative links are still checked, so a typo fails the build.)

### 5.5 Diagram — `<x-diagram>`

```html
<x-diagram name="example_flow" alt="Text description for screen readers." caption="Figure: what the reader must see." />
```

`name` is the script name in `diagrams/` without `.py`. `alt` is required. The SVG is put inline on
a white card. Click opens it at full size; "Open full size" opens the SVG file.

### 5.6 Callouts

```html
<x-sentence>The main idea in one sentence.</x-sentence>

<x-note>Extra information that helps.</x-note>
<x-note title="Where the dispatch is"><p>...</p></x-note>

<x-simplified><p>What is simplified, and what the full truth is (or where to read it).</p></x-simplified>

<x-warning title="Set MYPROJECT_HOME before you start"><p>...</p></x-warning>

<x-deepdive title="Engine.__init__, line by line">
  <p>...</p>
</x-deepdive>
```

- `x-note` (blue): useful extra fact. `x-simplified` (dashed grey): you must use it for every
  simplification. `x-warning` (amber): a real trap. `x-deepdive` (teal): collapsible full detail;
  its title appears in the table of contents. Add `open="yes"` only for a very short deep dive.
- Write a warning **before** the step or text that it is about.

### 5.7 Quiz — `<x-quiz>`

```html
<x-quiz>
  <x-q level="easy">Which function starts the main loop?
    <x-a><p><code>Engine.run()</code> in <code>pkg/engine.py</code>.</p></x-a>
  </x-q>
  <x-q level="hard">Question that needs two facts from the code?
    <x-a><p>Answer, with citations.</p></x-a>
  </x-q>
</x-quiz>
```

`level` is `easy`, `medium` or `hard`. Each `x-q` has exactly one `x-a`. The heading "Check yourself"
is automatic; add `heading="none"` for a second quiz on the same page. Answers explain *why* and cite
the code. At least one question must need the deep dive.

### 5.8 Tour stop — `<x-stop>`

See 4.2. Attributes: `n` (number, required) and `title`.

### 5.9 Interactive visual — `<x-viz>`

A page loads its own scripts with the front matter key `scripts:`. The tag makes the card where a
script draws the visual.

```html
---
...
scripts: viz/example_stepper.js
---
<x-viz id="example-stepper" title="Step through the request flow" caption="Click <em>Next</em>, or press Tab and Enter." />

<x-viz id="example-stepper" title="...">
  <p>Optional fallback HTML. Shown when JavaScript is off. Inline tags work here.</p>
</x-viz>
```

| Attribute | Required | Meaning |
|---|---|---|
| `id` | yes | Lower-case name (`example-stepper`). The script finds its mount with `[data-viz="<id>"]`. One `id` per page. |
| `title` | yes | Short title in the card header and the accessible name of the region. |
| `caption` | no | HTML under the card; inline tags work. |

The build makes `<figure class="viz" id="viz-<id>">` with a header, the mount
`<div class="viz-mount" data-viz="<id>">`, and inside it a `.viz-fallback` text ("This interactive visual
needs JavaScript ..."). The script replaces the fallback. A page with `<x-viz>` also loads
`assets/viz/viz.css`. The build stops if the page has `<x-viz>` but no `scripts:`, or if a script file does
not exist. Section 10 tells how to write the script.

### 5.10 Image — `<x-img>`

Use an image only when a diagram script cannot show the same thing (for example a chart from the repo's docs).

```html
<x-img repo="docs/images/architecture.png" alt="Text description." caption="What it shows." width="900" />
<x-img src="img/my_picture.png" alt="Text description." />
```

| Attribute | Required | Meaning |
|---|---|---|
| `repo` *or* `src` | one of them | `repo`: a path in the target repo; the build copies the file to `site/assets/repo/<path>` and adds a "Source" link to the repo host. `src`: a path inside `assets/` (put your files in `assets/img/`). |
| `alt` | yes | Text description for screen readers. |
| `caption` | no | HTML; inline tags work. |
| `width` | no | Maximum display width in px. |

The image sits on a white card (also in dark mode) and opens at full size on click. Allowed types:
png, jpg, jpeg, gif, svg, webp.

### 5.11 Project values — `{{project ...}}`

```html
{{project name}}        → the project name from explainer.json
{{project short_sha}}   → the short pinned commit; also: sha, site, repo_url, date, day, subject
```

Use it instead of a hand-written commit id, so the text stays correct when the pin changes.
It does not work inside `<pre>` blocks.

### 5.12 Code version block — `<x-version />`

Only for the home page section `#code-version`. The build writes the commit table, the checkout commands,
the table of pinned git submodules (read with `git ls-tree` and `.gitmodules`) and a note that line
numbers belong to this commit.

## 6. Writing rules (ASD-STE100)

All site text uses ASD-STE100 Simplified Technical English. Code, file names, identifiers and
technical names stay as they are.

> Language style is a project choice (`language_style` in `explainer.json`: `ste` or `plain`).
> With `plain`, the build does not check sentence length. Keep rules 3, 6, 7, 8 and 10 anyway.

**Rules**

1. Use approved, simple words. Use one word for one meaning, and one meaning for one word.
2. Max **20 words** in an instruction sentence. Max **25 words** in a descriptive sentence.
3. Use the active voice ("The scheduler selects ...", not "... is selected by the scheduler").
   Passive is allowed only when the actor is unknown or not important.
4. Use simple tenses: present, simple past, future. Do not use "-ing" forms as verbs.
5. One instruction per sentence. Write the instruction first: "Set both variables to the same value."
6. Max **6 sentences** in a paragraph. One topic per paragraph.
7. Use a numbered list for steps, and a bulleted list for items that have no order.
8. Write warnings and cautions **before** the step they apply to.
9. Use articles ("the", "a") and do not drop words to make a sentence short.
10. No idioms, jokes, slang or rhetorical questions in descriptive text. (Quiz questions are questions.)

**Technical words.** Technical names and well-known terms of the domain are allowed, but you must
define each one at its first use on the page, and link it with `{{term}}`. Use the same word for the
same thing on every page. Fill in this table for your project (the rows are examples from an ML
inference engine; replace them):

| Use | Do not use (for this meaning) |
|---|---|
| request (what a user sends) / sequence (the engine object for it) | job, query, prompt (for the object) |
| step (one main-loop iteration) | iteration, tick, round |
| rank (one process) / device (one GPU) | worker, node, card (for these meanings) |
| block (one cache block) | page, chunk (for this meaning) |

**Word substitutions**

| Do not write | Write |
|---|---|
| utilize, leverage | use |
| perform, carry out | do |
| initiate, commence | start |
| terminate | stop, end |
| obtain, retrieve, fetch (in prose) | get |
| create (in prose) | make |
| require | need, must |
| prior to / subsequently | before / after, then |
| in order to | to |
| ensure | make sure |
| approximately | about |
| numerous | many |
| via | through, with |
| due to | because of |
| it is possible to | you can |
| harness, robust, seamless, powerful | (delete; say the fact) |

**Before and after**

| Before | After (STE) |
|---|---|
| The engine object is lazily instantiated upon first attribute access in order to ensure that initialization is deferred until the configuration has been loaded. | The package makes the engine object on first use. This happens after the configuration is loaded. |
| In order to leverage the fast path, the buffer should be pinned. | Pin the buffer. Pinned memory makes copies faster. |
| If you want to run the server you need to remember to export the home variable and also make sure the port variable matches. | Export `MYPROJECT_HOME`. Then set `MYPROJECT_PORT`. |
| Utilizing the queue, messages are being exchanged between workers. | The queue moves messages between workers. |
| It's kind of like a plug adapter, right? | Think of a travel plug adapter. |

**Tone.** Short and calm. Say what the code does, then why. Prefer a concrete example with real
numbers over an abstract sentence.

## 7. Accuracy rules

1. **Every claim about the code has a source**: a `{{cite path:line}}` or an `<x-code>` excerpt.
   No source, no claim. "It probably ..." is not allowed; leave it out or mark it as an open question
   for the supervisor.
2. Read the code yourself. Notes, surveys and fact sheets are only a guide. (Example: a survey said
   an `__init__.py` dispatches kernels. It was empty. Another file dispatched.)
3. Cite the **narrowest** line range that proves the claim.
4. Mark each simplification with `<x-simplified>` and say what the full truth is.
5. **Out-of-scope code** (list it here: vendored libraries, git submodules that are not checked out,
   third-party frameworks). Explain only how <Project> calls them (arguments, shapes, which
   function, when). Do not describe their insides.
6. Numbers from `doc/` and `README.md` are allowed; cite the line.
7. **Comments in another language**: translate them when they help. Always say they are translated
   (`<x-tr>` does this automatically).
8. General knowledge that is not about this repo (what CUDA is, what a CTA is) needs no citation,
   but must be correct and short. If you are not sure, leave it out.
9. When code and docs disagree, describe the code, and mention the difference.

## 8. Glossary

Files: `src/glossary/*.json`. One JSON object; keys are term ids.

```json
{
  "_about": "Who owns this file. Keys that start with _ are comments.",
  "kv-store": {
    "term": "KV store",
    "short": "A store that keeps values under keys. You put a value with a key, and get it back with the same key.",
    "long": "Optional extra HTML. Inline tags work: {{cite pkg/store.py:58}}.",
    "aliases": ["key-value store"],
    "page": "concepts/request-flow"
  }
}
```

- Ids: lower-case letters, digits and `-` (`kv-store`, `request-flow`).
- `term` and `short` are required. `short` is the tooltip: one or two STE sentences, under 220 characters.
- `page` (optional) links "Read more" to the page that explains the term. A planned page is fine.
- `aliases` help search.
- The glossary page `reference/glossary` is generated from these files.

## 9. Navigation

- `src/nav/<section>.json` lists the sections and the planned pages. Sections: `learn` (1),
  `concepts` (2), `tours` (3), `code` (4), `reference` (5).
- An entry whose page file does not exist shows as grey "soon". When the file exists, it is live.
- Page ids in the nav are fixed. Do not rename them: other writers link to them.
- To add a page that is not in the nav: create the file and put `nav_after: <id>` in its front
  matter. The page goes into the sidebar after that entry. Without `nav_after`, it goes to the end of
  its section with a warning.
- Previous/next buttons follow the sidebar order and skip pages that are not written.
- The code-map writer owns `src/nav/code.json`; its module list is a proposal and can change.

## 10. Diagrams

**Rules (summary of `instructions-svg.md` — read the full guide; it is binding):**

- Canvas width 1100 for site diagrams (see the readability rule below). White background rect. Height computed from content. No CSS, no `<style>`,
  no gradients, shadows, filters or images. Inline attributes only.
- Fonts: sans (Inter stack) for prose, mono for every number, size, identifier and path.
- One colour = one meaning. 3-5 role accents per diagram, each in the legend. Neutral grey for
  everything else. Arrow colour = the role of what flows. Dashed arrows for secondary paths.
- Numbered panels, read top to bottom; flow left to right inside a panel. Each panel answers one
  question; its subtitle is the answer.
- Title states what the diagram explains; subtitle states the scope. Footnotes say what is
  simplified or not shown.
- Show real values from the code, and put the source `file:line` on the drawing or in the docstring.
- No text smaller than 11 on the canvas. No rotated text. Arrows must not cross boxes.
- Diagrams stay on a white card in dark mode, so always design for a white background.
- **Readability in the page column (updated after the restyle).** Figures display up to 1100 px wide
  (about 950 px on a 1280 screen). So site diagrams use **`Diagram(width=1100)`** (the svglib default), and the
  font sizes from `instructions-svg.md` (no text below 11 on the canvas; mono data lines 12–13; box
  titles 14). Keep at most 3 boxes side by side and at most 3 panels per diagram. If a diagram needs
  more, split it into two diagrams. "Open full size" is a help, not the main way to read a diagram.
  Captions start with "Figure: " and say what the reader must see.

**How to add an interactive visual**

1. Write `assets/viz/<name>.js` (one file per visual, named after your page or topic; the writer of the
   page owns it). Add shared visual styles only in `assets/viz/viz.css`, or inject a `<style>` element once
   from your script. Do not edit `assets/site.css`.
2. Add `scripts: viz/<name>.js` to the page front matter and put `<x-viz id="..." title="..." />` in the
   page (section 5.9). Run `python3 build.py`.
3. Follow these rules:
   - **Vanilla JS only.** No libraries, no build step, no network (no `fetch`, no CDN). The page must work
     from `file://`.
   - **Scope.** Wrap the file in an IIFE: `(function () { ... })();`. Find mounts with
     `document.querySelectorAll('[data-viz="<id>"]')`. Put all DOM inside the mount. Prefix CSS classes
     (for example `kva-`) and scope selectors under `.viz-mount[data-viz="<id>"]`.
   - **Colours.** Use the CSS custom properties of `site.css` (`var(--ink)`, `var(--mute)`, `var(--line)`,
     `var(--surface)`, `var(--blue)` ...). Then dark mode works with no extra code. For a categorical
     series, use the 8 colours of `instructions-svg.md` section 2.3 (`viz.css` has them as `--viz-c1` ...
     `--viz-c8`, with lighter values for dark mode). Pair each colour with a label: colour alone carries
     no meaning.
   - **Fonts.** `var(--sans)` for text, `var(--mono)` for numbers and identifiers.
   - **Keyboard and touch.** Use real `<button>` elements (min. 40 px tall). Every action works with
     Tab + Enter/Space. Do not use hover-only information. Announce results in an `aria-live="polite"`
     element.
   - **Phone width.** The visual works at 390 px width without a horizontal page scroll. Grids wrap.
   - **Deterministic.** Use a seeded random generator (for example mulberry32 with a fixed seed), so every
     reader sees the same example. **Reset** returns to the start state.
   - **Honest.** Label the visual as a simplified model where it is one, and say on the page what the
     real code does differently (with citations).
4. Check the visual in a browser at 1280 px and 390 px width, in light and dark mode, with mouse, keyboard
   and touch.

**Site colour roles** (do not reuse these colours for other meanings on the page chrome):
blue = links / note; amber = warning; teal = deep dive; emerald / violet / pink = level
Beginner / Intermediate / Advanced. Inside a diagram, the legend defines the meaning.

**How to add a diagram**

1. Copy `diagrams/_template.py` to `diagrams/<name>.py`. Use a name that belongs to your pages.
2. List the sources (`file:line`) in the docstring.
3. Use the helpers in `diagrams/svglib.py`:

   | Helper | Use |
   |---|---|
   | `Diagram()` | one drawing; `d.save(height=...)` writes the file given as `argv[1]` |
   | `header(title, subtitle, params, scope)` | title block |
   | `panel(y, h, num, title, sub)` | numbered section card (x = 20 … 1080) |
   | `box(x, y, w, h, title, lines, col, align)` | tinted box with title + mono lines |
   | `step_card(x, y, w, h, num, title, col, tag, rows)` | step card with accent bar and keyed rows |
   | `lane(x, y, w, h, col, name, details)` | full-height column with a solid header band |
   | `chip`, `pill`, `pill_auto` | result chip / tag pill |
   | `arrow`, `path_arrow`, `arrow_label` | straight / orthogonal arrows (end 2 px short of the target) |
   | `badge`, `circle`, `line`, `rect`, `text` | primitives |
   | `legend(x, y, items)`, `callout(...)`, `footnotes(x, y, lines)`, `aside(x, y, lines)` | bottom matter |
   | colours | `BLUE, AMBER, VIOLET, TEAL, EMERALD, PINK` (strong, tint, pale), `NEUTRAL`, `INK, MUTE, LINE, BORDER, ...` |

4. Run it alone to test: `python3 diagrams/<name>.py /tmp/x.svg`. The library prints a warning if
   something passes the canvas edge.
5. Embed it: `<x-diagram name="<name>" alt="..." caption="..." />`. The build re-runs a script
   when the script or `svglib.py` changes.
6. Check the result in a browser at 100 % and with "Open full size". Use the checklist in
   `instructions-svg.md` section 11.

## 11. Build errors and warnings

The build prints every problem with `file:line` and stops on errors. Common messages:

| Message | Fix |
|---|---|
| `x-code: file '...' does not exist in the repo` | Check the path from the repo root (for example `pkg/...`). |
| `x-code: <file> has N lines; a-b is out of range` | Open the file and fix the range. |
| `x-code: highlight '...' is outside lines a-b` | Highlight lines must be inside `lines`. |
| `citation: ...` | Same as above, for `{{cite}}`. |
| `unknown glossary term 'x' (did you mean ...)` | Use an existing id, or add the term to your glossary file. |
| `glossary id 'x' is also defined in ...` | Use the existing entry; do not redefine it. |
| `link to unknown page 'x'` | Use an id from `src/nav/*.json` or an existing page. |
| `prerequisites: unknown page id` | Same. |
| `x-diagram: no diagram 'x'` | Create `diagrams/x.py`, or fix the name. |
| `diagram script failed` | Run the script alone and fix the Python error. |
| `unknown or unbalanced tag '<x-...'` | A custom tag is not closed, or the name is wrong. |
| `cannot parse attributes` | Use `name="value"` with double quotes. |
| `malformed inline tag` | A `{{` without a matching `}}`, or a typo inside it. Use `\{{` for a literal. |
| `broken link` / `broken anchor` | A hand-written link or `#id` that does not exist. Use `{{link}}`. |
| `unknown front matter key` | Use the keys in section 3. |
| `duplicate id(s) on the page` | Two headings or two quizzes make the same id. Add `id="..."` to one heading, or `heading="none"` to the second quiz. |
| `x-viz ...: the page has no 'scripts:'` / `scripts: assets/... does not exist` | Add `scripts: viz/<name>.js` to the front matter, and check the file in `assets/viz/`. |
| `x-img: ... does not exist` / `needs alt` | Fix the `repo=` or `src=` path; add `alt="..."`. |
| `repo is at ..., pinned to <sha>` | Do not change the repo checkout. Ask the supervisor. |

Warnings (the build still succeeds, `--strict` turns them into errors):

- links or prerequisites that point to pages that are not written yet (expected while writers work in parallel);
- missing template parts on learn/concepts/tours pages (no sentence, diagram, code, deep dive, or not 3-5 questions);
- `STE: sentence has N words (max 25)` on learn/concepts/tours pages (code, tables and citations are not counted). Split the sentence;
- a page that is not in a nav file;
- diagram warnings (content past the canvas edge, width not 1100).

## 12. Checklist before you hand in

- [ ] `python3 build.py` has 0 errors; your pages have no template warnings.
- [ ] Every claim about the code has a citation or an excerpt. You opened each cited line yourself.
- [ ] The page follows the template order and the exact `<h2>` names.
- [ ] Each new term is defined at first use and linked with `{{term}}`; new glossary ids are in your own file.
- [ ] STE: sentences ≤ 20 words (instructions) / ≤ 25 words (descriptions), active voice, paragraphs ≤ 6 sentences.
- [ ] Simplifications are marked with `<x-simplified>`. Comments in another language are translated and marked.
- [ ] No internals of out-of-scope code.
- [ ] Deep dives give shapes, dtypes, layouts, steps, edge cases, env vars — with numbers.
- [ ] 3-5 quiz questions, at least one easy and one hard; answers cite the code.
- [ ] Your diagram passes `instructions-svg.md` section 11, and has `alt` text.
- [ ] Interactive visuals: keyboard, touch, 390 px, light and dark mode checked; seeded; reset button.
- [ ] You looked at the page in a browser at desktop and phone width (or the supervisor did).
