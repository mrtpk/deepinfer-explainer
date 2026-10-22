# Playbook: make an "Explained" study site for an open-source codebase

This file tells you how to make a static HTML site that teaches one open-source codebase to a beginner.
The same reader also studies the full detail. The model project is **DeepInfer Explained**
(this folder: 106 pages, 91 diagrams, 8 interactive visuals, 321 glossary terms, all fact-checked).

Readers of this file:
- **A new Claude Code session.** It acts as the supervisor. It delegates long work to subagents.
- **The user.** The user approves the plan, reviews Phase 1, and decides on publishing.

How to use this file:
1. Read all of it once.
2. Copy the tooling (section 6.1) into a new project folder.
3. Do the process in section 7, phase by phase. Use the prompt templates in section 7.6.
4. Use the checklists in section 12 at each gate.

Words in this file:
- **Target repo**: the open-source codebase that the site explains. It stays read-only.
- **Explainer repo**: the new folder with the site sources, the tooling and the build output.
- **Supervisor**: the main session. **Subagent**: an agent that the supervisor starts for one task.
- **Batch**: a group of 4-8 pages on one topic. One writer subagent writes one batch.
- `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`: fill in for your project.

---

## 1. Goal and outcome

**Goal.** Make a static website that teaches what happens in `{PROJECT}`. The reader clicks through
the pages and learns step by step. After the basics, the site also works as a reference.

**The outcome, when done:**
- A folder `site/` that opens from disk (`file://`) with a double-click on `site/index.html`. No server.
- Five parts: Learn the basics, Concepts, Guided tours, Code map, Reference (section 3).
- Every page starts beginner-friendly and then gives a full "Deep dive" for study.
- Every claim about the code has a citation to `file:line` at one pinned commit.
- Code excerpts are copied from the pinned checkout by the build, so they are always exact.
- One look: a light article page, SVG diagrams in one style, a few interactive visuals.
- Each batch of pages was checked by a separate fact-check subagent against the code.
- The build has 0 errors. A site check at 1280 px and 390 px found no layout or JS errors.
- Git history has one commit per stage.

**Definition of done** (copy into `plan.md`):
- All planned pages exist, or the user deferred them (they show as "soon" in the menu).
- `python3 build.py` gives 0 errors (no broken links, citations, anchors or glossary terms).
- Every concept and tour page has a diagram, code excerpts, a deep dive and "Check yourself".
- Fact checks are done for every batch. The FINAL-PASS TODO list is empty.
- Each interactive visual works at desktop and phone width, with mouse, keyboard and touch.
- A beginner can follow the path Home → Basics → Tour 1 with no dead end.

---

## 2. Questions to ask the user first

Ask these questions **before** you build. Write the answers into `plan.md` section "Decisions".
Do not start Phase 1 before the user approves `plan.md`.

| # | Question | Why it matters | Default for this user (Thomas Paul) |
|---|---|---|---|
| 1 | Who is the reader? What do they know already? | Sets the basics part and the level of each page. | Knows Python (or the main language of the repo). Knows little about the domain (for example ML). |
| 2 | Depth: only a beginner guide, or also full study detail? | Decides if every page gets a deep dive. | Both. "I use this to study. Beginner-friendly, but I need details as well." |
| 3 | Local files or published? Are CDN libraries OK? | Decides the link rules and the CDN list. | Local for now, publish later. CDN is OK (cdnjs, jsDelivr, unpkg, Google Fonts). |
| 4 | Site structure: concepts + tours + code map? One page per file? | Decides the page count. | Concepts + guided tours + a code map with one page per important module. Not one page per file. |
| 5 | Folder for the explainer repo? | Avoid edits to the target repo. | `test-harness/<project>-explainer/`, next to the target repo checkout. |
| 6 | Language style of the site text? | Writing rules (section 5). | ASD-STE100 Simplified Technical English. |
| 7 | Scope: which parts get full pages? What is out of scope? | Avoids surprises late. | Be generous. Vendor submodules: explain only the interface. |
| 8 | Name of the site? | Title on every page. | "`{PROJECT}` Explained". |
| 9 | Look? Show the sample look or a reference site. | Avoids a restyle (section 10). | Light article look like Sebastian Raschka's Substack (`magazine.sebastianraschka.com`). Never auto dark mode. |
| 10 | Which commit to pin? | All line numbers depend on it. | The newest commit on the default branch on the day you start. |
| 11 | Git: local commits per stage? Push? Which author identity? | Git rules (section 9). | Commit per stage. Push only when asked. Author `Thomas Paul <contact@thomaspaul.dev>`, repo-local. |
| 12 | Stop after Phase 1 for a review? | The user checks look and depth early. | Yes. Always stop after Phase 1. |

Before you ask, run the codebase survey (section 7.6, template A). Then you can propose a concrete
page list with the questions. The user answers faster when there is a draft.

---

## 3. Site organization and page types

### 3.1 The five parts

```
<project>-explainer/site/
  index.html     Home: what the project is, the system map, "Start here" paths, code version
  learn/         Part 1: Learn the basics (no project code yet), ~10-12 pages
  concepts/      Part 2: Concepts of this project, ~25-35 pages in groups
  tours/         Part 3: Guided tours through real code, ~6 tours
  code/          Part 4: Code map: folder tree + one page per important module, ~40-50 pages
  reference/     Part 5: generated tables (env vars, config, API), glossary, FAQ
  assets/        CSS, JS, visuals, search index
  diagrams/      the SVG files
```

DeepInfer had: learn 12, concepts 33 (+1 deferred), tours 6, code 49 (+1 deferred), reference 4 + the
generated glossary. About 106 pages in total.

**Part 1, Learn the basics.** Domain knowledge that the reader needs before the code. No project
code, except a short "In {PROJECT}" section at the end with 1-3 cited pointers. For an ML inference
engine: what an LLM does, tokens, transformer, attention, prefill/decode, KV cache, sampling,
batching, GPUs and kernels, parallelism, MoE, number formats.

**Part 2, Concepts.** Each page explains one idea and connects it to the files that implement it.
Group the pages in the sidebar (DeepInfer: Engine, Model, Decoding, Scale, Platform).

**Part 3, Guided tours.** Step-by-step walks through real code in execution order. Each stop names
the file and the function where the reader is. Good tours:
- "Life of a request" (the main data path, end to end; about 13 stops). Always write this one.
- "Start-up" (launch, process groups, loading, memory, warm-up).
- "One main-loop iteration" (DeepInfer: one engine step).
- "Inside one core unit" (DeepInfer: one decoder layer).
- One tour for the hardest feature (DeepInfer: one speculative decoding round).
- "One step on many machines/devices" if the project is distributed.

**Part 4, Code map.** `code/index` is a folder tree with a short description, file counts and line
counts for each folder. Then one page per important module. Small files (`__init__.py`, most tests)
appear in the tree only. Group module pages by folder.

**Part 5, Reference.**
- Tables that a tool generates from the code (DeepInfer: all `DEEPINFER_*` env vars, made by
  `tools/gen_env_vars.py`). Generate, do not hand-copy: hand-copied tables go wrong.
- Config classes, public API (DeepInfer: the C++ engine API from a `.pyi` stub).
- Glossary: generated by `build.py` from `src/glossary/*.json`. Do not write it by hand.
- FAQ: short answers with citations. Include "Where do docs and code disagree?" and
  "Known open questions". Use the project's own Q&A docs if they exist.

**Home page.** It has these sections:
1. One paragraph: what the project is (cite the README), and who the site is for.
2. A fact table: what it runs, hardware or platform, code size, how to run it.
3. **The system map** (`#system-map`): a clickable HTML/CSS map. Left column: the path of a request,
   numbered 1..7, each box links to its page and shows the file path. Right column: "Around every
   step" parts. Colour stripe = where the code runs (for example Python on the CPU, C++ on the CPU,
   work on the device), with a legend. A `<x-simplified>` box under it.
4. **Start here** (`#start-here`): 3 learning paths (A: new to the domain, B: knows the domain,
   C: studies one part).
5. **How to use this site** (`#how-to-use`): levels, two depths per page, quizzes, search with `/`,
   glossary tooltips, code links, translated comments, grey "soon" entries.
6. **What is not in this release** (`#not-in-this-release`), if the README says so.
7. **The code version this site explains** (`#code-version`): full SHA, date, subject, history size,
   browse link, checkout commands, a table of pinned submodule commits, and a note that line numbers
   belong to this commit.

### 3.2 Page anatomy (what the build makes around each page)

Every built page has, from top to bottom:
- Top bar: menu button (phones), brand mark and site name, search box ("Search ( / )"), light/dark toggle.
- Left sidebar: Home, then one collapsible group per part with a "live/total" count. Not-written pages
  show in grey with "soon". The current page is marked.
- Breadcrumbs: Home › Part › Group › Page.
- `<h1>` page title (the writer never writes an `<h1>`).
- Meta row: level (Beginner / Intermediate / Advanced, a small coloured dot), part name,
  "about N min read + M min deep dives", and "Open all deep dives".
- **Version line**: "Code version: {PROJECT} @ `{SHORT_SHA}` · date", linked to the tree at the commit.
- "Before you read" box from `prerequisites:` (or "You do not need to read other pages first").
- The page body (templates in 3.3).
- "Related pages" with the summary of each page.
- Previous / Next buttons in sidebar order (pages not written are skipped).
- Footer: full SHA, commit date and subject, link to `index.html#code-version`, source link, build date.
- "On this page" table of contents on the right, only at ≥ 1680 px width.
- Hidden: lightbox for diagrams, glossary tooltip element.

### 3.3 Page templates

Use the `<h2>` texts exactly, so all pages look the same. Starter files: `src/_templates/concept.html`
and `src/_templates/tour.html`. The model module page is a real page (DeepInfer: `src/code/llm-engine.html`).

**Concept page** (`concepts/`) and **basics page** (`learn/`):

| # | Part | Source |
|---|---|---|
| 1 | Level badge | front matter `level:` |
| 2 | Before you read | front matter `prerequisites:` |
| 3 | In one sentence | `<x-sentence>`, max 25 words |
| 4 | `<h2>The idea</h2>` | plain explanation, then one everyday comparison; say where the comparison stops being true |
| 5 | `<h2>The picture</h2>` | `<x-diagram>` + 2-3 sentences on how to read it; optional `<x-viz>` |
| 6 | `<h2>In the code</h2>` | `<h3>Step N: ...</h3>` parts with `<x-code>` and `{{cite}}`. Basics pages use `<h2>In {PROJECT}</h2>` at the end instead: 1-3 cited pointers and links to concept pages |
| 7 | `<h2>Deep dive</h2>` | one or more `<x-deepdive>` blocks, one topic each |
| 8 | `<h2>What can go wrong</h2>` | failure modes with citations, then **Why it matters.** |
| 9 | Check yourself | `<x-quiz>`, 3-5 questions, easy/medium/hard; at least one needs the deep dive |
| 10 | Related, prev/next | automatic |

**What goes in a deep dive** (the user studies with it; it is not a longer summary):
- exact shapes and types (`int32 [num_tokens, 4]`), with a worked example with real numbers;
- memory or data layouts (row-major, packed, padded; who writes which byte);
- the algorithm step by step, as a numbered list (pseudocode is good);
- edge cases and error paths (what raises, what only logs);
- related environment variables and config fields, with defaults and the line that reads them;
- design trade-offs, only when the code or the docs support them;
- numbers from the project docs, with citations;
- long code read line by line: the excerpt, then a numbered list "Line 13. ...".

**Tour page** (`tours/`): sentence, The idea, The picture (often 2 diagrams: a map split in two halves,
plus an optional stepper visual), then numbered stops, then "What can go wrong" and the quiz.

```html
<x-stop n="1" title="The user script starts the engine and calls generate()">
  <p>Where we are, and why this step exists.</p>
  <x-code file="pkg/entrypoints/llm.py" lines="100-120" highlight="110" />
  <p>What the excerpt does.</p>
  <x-deepdive title="Stop 1 in detail"> ... </x-deepdive>
</x-stop>
```

Stops run in code order. A final `<h2>` can show the loop ("many steps for one request").

**Module page** (`code/`). Front matter title: `<path>: <main thing>`. Parts in order:
1. `Purpose`: one sentence, then an "at a glance" table: File (lines, origin), Main class, Runs in
   (process / thread / device), Called by, Calls, Not in this file.
2. `Where it sits`: optional diagram, `<h3>Who calls it</h3>`, `<h3>What it calls</h3>`, all cited.
3. `Key classes and functions`: table of name | cited line | one-line role.
4. `Walk through the main methods`: one `<h3>` per method, `<x-code>` ≤ 40 lines, a numbered "Line N" list.
5. `Deep dive`: data flow (types and shapes table), processes and threads, interaction with other parts,
   a worked example, an error-path table, env vars (default, read-at line, effect).
6. `Related concepts`: list of links.
7. `<x-quiz>` with 3-5 questions. Module pages also get a `level`.
Small modules (under ~150 lines) can merge parts 3 and 4.

**Code map index** (`code/index`): Purpose, The folder tree (nested list with counts and links),
How the folders depend on each other, How the numbers were measured.

**Reference page**: free structure. Every row that states a default or a location has a citation.
A generated table sits between markers, for example
`<!-- BEGIN GENERATED env-tables --> ... <!-- END GENERATED env-tables -->`.

### 3.4 Interactive visuals

Make 6-8 visuals for the hardest ideas. Vanilla JS, one file each in `assets/viz/`. DeepInfer had:
attention toy, KV cache block allocator, scheduler simulator, ZOS (CPU/GPU overlap) timeline,
MoE router with load balancer, speculative decoding accept/reject, number-format converter,
"Life of a request" stepper. Good kinds: **simulators** (click "Add request", "Step"),
**steppers** (Next / a stop number), **converters** (value in, bits out), **toys** (change an input,
see the weights change).

Rules for a visual:
- Copy the real rules from the code, and list them with citations in the file header comment.
  List what the visual leaves out.
- Seeded random generator (mulberry32 with a fixed seed). A Reset button. Same result for every reader.
- No libraries, no network. Works from `file://`.
- IIFE scope; find mounts with `[data-viz="<id>"]`; prefix CSS classes (`kva-`).
- Colours from CSS custom properties (`var(--ink)`, `var(--blue)`, `--viz-c1..8`), so dark mode works.
- Real `<button>` elements, ≥ 40 px tall, Tab + Enter/Space, `aria-live="polite"` for results.
  No hover-only information.
- Works at 390 px width with no horizontal page scroll.
- Label it as a simplified model on the page, and say what the real code does differently.

The home system map is plain HTML/CSS (no JS). That is enough and it is easier to keep correct.

---

## 4. Look and diagram rules

### 4.1 Page look (user feedback; binding)

The first look was dark and busy: the site followed the OS dark mode, and it had many boxes,
borders and badges. The user said: *"I hate the color scheme... need light background, readable.
This is learning material."* A full restyle followed. Start with the final look:

- **Light background always.** Dark mode only through the toggle button. Never follow
  `prefers-color-scheme`. The toggle stores the choice in `localStorage`; a small inline script in
  `<head>` applies it before paint.
- Model: a long-form magazine article (Sebastian Raschka's Substack).
- Body: Inter (Google Fonts), **18 px / line height 1.7** (17 px / 1.68 on phones). Text colour dark
  gray `#292929`, headings `#141414`, on white.
- **Prose column ~720 px** (`--measure`). **Figures up to ~1100 px** (`--wide`). The article is a
  3-track CSS grid: prose in the middle track, `.diagram`, `.viz`, `.figure-img` span the full width.
- Figures nested in a deep dive, a tour stop or a callout break out to full width with a container query:
  `.article { container-type: inline-size; }` and
  `.article :is(.diagram,.viz,.figure-img):not(.article > *) { width: min(var(--wide), 100cqw); position: relative; left: 50%; transform: translateX(-50%); }`.
- Few boxes, borders and badges. Hairline rules. Pale tints only where they help.
  Role colours only as small dots, thin rules and short labels.
- One link colour (blue). Site colour roles: blue = link / note; amber = warning; teal = deep dive;
  emerald / violet / pink = level Beginner / Intermediate / Advanced.
- Code: GitHub-light token colours, Prism from cdnjs (pinned version), line-number gutter,
  highlighted lines, "GitHub ↗" and "Copy" buttons, path header linked to the pinned commit.
- Wide tables: cells wrap at spaces, code in cells breaks anywhere, tighter cells on phones.
  A table with many columns may scroll inside its own box; the page must never scroll sideways.
- Diagrams and images sit on a white card, also in dark mode.
- Mobile: sidebar becomes a drawer below 960 px; 16 px side padding; brand name hidden below 560 px.

### 4.2 Diagram rules

The full guide is `instructions-svg.md`. Read it. The project rules below **override** it where they differ
(see section 10, "contradictions").

- **One Python script per diagram** in `diagrams/<name>.py`, built on the shared `diagrams/svglib.py`.
  No Mermaid, no hand-drawn SVG, no images when a script can draw it. One look for all diagrams.
- **Canvas width 1100**: `d = Diagram(width=1100)`. The build warns if the width is not 1100.
  (A 1500 canvas showed text at 7-8 px on a 1280 screen. 1100 shows near 1:1.)
- **No text smaller than 11** on the canvas. Mono data lines 12-13. Box titles 14. No rotated text.
- **At most 3 boxes side by side. At most 3 panels per diagram.** If you need more, split the
  diagram into two (for example `tour1_map_a`, `tour1_map_b`).
- White background rect; height computed from content; inline attributes only (no CSS, no `<style>`,
  no gradients, shadows, filters or images).
- Sans (Inter stack) for prose; mono for every number, size, identifier and path.
- One colour = one meaning; 3-5 role accents per diagram, all in the legend; neutral gray for the rest.
  Arrow colour = the role of what flows. Dashed arrows for secondary paths. Arrows do not cross boxes.
- Numbered panels top to bottom; flow left to right in a panel. Each panel answers one question;
  its subtitle is the answer.
- Title says what the diagram explains; subtitle says the scope. Footnotes say what is simplified.
- Real values from the code. Sources (`file:line`) in the script docstring or on the drawing.
- **Captions start with "Figure: "** and say what the reader must see. `alt` text is required and
  describes the content panel by panel.
- "Open full size" is a help. The diagram must be readable in the page at 100 %.

---

## 5. Writing and accuracy rules

### 5.1 Language style (configurable)

The site language is a project choice (section 2, question 6). **Default for this user: ASD-STE100.**
If the user picks plain English, keep rules 3, 6, 7, 8 and 10 below and drop the word limits.

ASD-STE100 rules for site text (code, file names and technical names stay as they are):
1. Approved, simple words. One word for one meaning.
2. Max 20 words in an instruction sentence, max 25 in a descriptive sentence.
3. Active voice. Passive only when the actor is unknown or not important.
4. Simple tenses. No "-ing" forms as verbs.
5. One instruction per sentence; the instruction first.
6. Max 6 sentences per paragraph; one topic per paragraph.
7. Numbered lists for steps; bulleted lists for items with no order.
8. Warnings and cautions **before** the step they apply to.
9. Keep articles ("the", "a").
10. No idioms, jokes, slang or rhetorical questions (quiz questions are questions).

Word substitutions: utilize/leverage → use; perform → do; initiate/commence → start; terminate → stop;
obtain/retrieve → get; require → need, must; prior to → before; in order to → to; ensure → make sure;
approximately → about; numerous → many; via → through; due to → because of; delete "robust",
"seamless", "powerful", "harness" and say the fact.

**Fixed vocabulary.** Write a table in `STYLE.md` of the project's words: one word per thing, and the
words not to use for it. DeepInfer example: request (what a user sends) / sequence (the engine object);
step (one engine iteration), not tick or round; rank (one process) / device (one GPU or NPU);
block (KV cache block), not page or chunk; kernel (device program), not op.

**Technical terms.** Define each term at its first use on the page and link it with `{{term id}}`.
Link only the first use (and again in a far deep dive).

**Tone.** Short and calm. Say what the code does, then why. A concrete example with real numbers is
better than an abstract sentence.

### 5.2 Accuracy rules

1. **Every claim about the code has a source**: `{{cite path:line}}` or an `<x-code>` excerpt.
   No source, no claim.
2. **Read the code yourself.** Surveys, notes and `facts.md` are a guide only.
   (The DeepInfer survey named an empty `__init__.py` as the kernel dispatcher. The real one was `ops.py`.)
3. Cite the **narrowest** line range that proves the claim.
4. Mark every simplification with `<x-simplified>` and say what the full truth is.
5. **Open questions are written as open questions.** When the code does not answer a question, say so on
   the page (and in the FAQ "Known open questions"). Do not guess. "It probably ..." is not allowed.
6. When code and docs disagree, describe the code and mention the difference. Collect these in the FAQ.
   When a code comment is wrong, say so (DeepInfer: a comment said "shortest", the code picks the most
   output tokens).
7. Derived claims (for example "the first prefill runs in step 71") must say "earliest possible" or show
   the derivation. Mark them for a hard fact check.
8. Inferred values that are not in the repo (for example a size that comes from a checkpoint file) are
   marked "inferred".
9. Vendor libraries and submodules that are not checked out: explain only how the project calls them
   (arguments, shapes, when). Do not describe their inside.
10. Comments in other languages: translate when it helps, and mark them as translated (`<x-tr>`).
11. General knowledge that is not about this repo needs no citation, but it must be correct and short.
    If you are not sure, leave it out.
12. Line numbers are for the pinned commit. The build fails when the checkout is at another commit.

### 5.3 Quizzes, notes and warnings

- 3-5 questions per page; mix easy, medium and hard; at least one hard question needs the deep dive.
  Answers say *why* and cite the code.
- `<x-note>` for a useful extra fact; `<x-simplified>` for every simplification; `<x-warning>` for a real
  trap, placed before the text it is about.

---

## 6. Tooling

### 6.1 What to copy and what to change

Copy these files from the DeepInfer explainer into the new explainer repo:

| File | Copy as is? | What to change |
|---|---|---|
| `build.py` | adapt | `REPO`, `SHA`, `GITHUB`, `SITE_NAME`, `PRISM_COMPONENTS` and `LANG_BY_EXT` (languages of the target repo), the brand mark text `DI`, the version-line text "DeepInfer @", the footer source link, `localStorage` key `di-theme`, `window.DI_SEARCH_INDEX` (also in `site.js`), the `<x-tr>` label "Chinese → English", `STE_MAX_WORDS` (or turn `ste_check` off for plain English), `github_url()` if the host is not GitHub (GitLab uses `/-/blob/<sha>/path#L10-20`). Also the docstring. |
| `assets/site.css` | yes | only the header comment |
| `assets/site.js` | yes | the theme key and the search-index name (keep them equal to `build.py`) |
| `assets/viz/viz.css` | yes | header comment |
| `assets/favicon.svg` | adapt | the letters |
| `diagrams/svglib.py` | yes | change the default `W = 1500` to `1100` and fix the docstring |
| `diagrams/_template.py` | adapt | use `Diagram(width=1100)`; fix the commit in the docstring |
| `src/_templates/concept.html`, `tour.html` | yes | example paths |
| `STYLE.md` | adapt | project paths, vocabulary table, vendor list, example page, fix the stale 1500 values (section 10) |
| `instructions-svg.md` | yes | add one line at the top: "Site rules in STYLE.md §10 override: canvas 1100, min text 11" |
| `tools/gen_env_vars.py` | model only | rewrite for the new project's config source (section 6.7) |
| `assets/viz/*.js` | model only | use as examples of style and structure; write new visuals |
| `.gitignore` | yes | `__pycache__/`, `*.pyc`, `build/`, `screenshots/`, `.site-tmp-*/`, `.site-old-*/` |

Do not copy: `src/` pages, `src/nav/*.json`, `src/glossary/*.json`, `notes/facts.md`, `plan.md`,
`progress.md`, `diagrams/<name>.py`. Make new ones. Use them as format examples only.

### 6.2 Folder layout

```
parent/
  {PROJECT}/                   target repo checkout at {SHA}, READ ONLY
  {project}-explainer/
    build.py                   the generator (owner: foundation / supervisor)
    STYLE.md                   the writer's guide
    instructions-svg.md        the diagram style guide
    plan.md  progress.md       plan and progress log (section 8)
    README.md                  what the site is, code version, how to build
    notes/facts.md             shared verified facts (section 8.3)
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
- **Pinned-commit check.** Runs `git -C ../{PROJECT} rev-parse HEAD`. If HEAD is not `SHA`, it is an
  error: line numbers would be wrong.
- **Version line and footer.** Reads date and subject of `SHA` with `git log` and puts them on every page.
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

Generate every reference table that the code can give. Model: `tools/gen_env_vars.py`.
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

Use Playwright through `npx` (it installed in this environment with a workaround: keep the scripts in
the scratchpad, give each run its own output file name, because a shared fixed file name raced).
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

## 7. Process

### 7.1 Phases

| Phase | Work | Who | Gate |
|---|---|---|---|
| 0a | Codebase survey | 1 survey subagent (template A) | supervisor reads it; claims are not trusted yet |
| 0b | Draft `plan.md` + `progress.md`; ask the questions of section 2 | supervisor | **user approves the plan** |
| 1a | Foundation: copy and adapt tooling, `STYLE.md`, nav files with all planned pages, `core.json`, one reference sample page | 1 subagent (template B) | build 0 errors; supervisor checks screenshots |
| 1b | Sample set: home page + system map + code tree + one module page; one basics page + one visual + basics glossary; Tour 1; one generated reference page | 3-4 writer subagents in parallel | build 0 errors |
| 1c | Fact check of all sample pages; site check | fact-check subagents (template D) + supervisor | defects fixed |
| 1d | **STOP. Show the user the sample pages.** Apply look and depth feedback to the tooling and `STYLE.md` | supervisor | **user approves the full build** |
| 2 | Full build in batches and waves (7.3) | writer → fact checker → commit, per batch | each batch: build 0 errors, fact check done, committed |
| D | Diagram pass if a rule changed (for example convert Phase 1 diagrams to the 1100 canvas) | 1 subagent | build 0 errors |
| F | Final pass: consistency sweep (template E) + site check (template F) + README | 2 subagents + supervisor | definition of done (section 1) |

Phase 1 samples must cover each page type once: basics, concept, tour, module, reference, home.
Writers in Phase 2 copy these samples. Good samples make good batches.

In DeepInfer, the plan had a separate research phase (fact sheets before writing). Phase 1 showed that a
writer who reads the code for its own batch gives good pages. So the full build dropped the research
phase, and kept a separate fact check per batch. Do the same.

### 7.2 Supervisor role

The main session is the supervisor. It does **not** write pages.
- It delegates every long task to a subagent. It does short tasks itself (a CSS fix, a status update).
- It writes each subagent brief (section 7.6), checks the output, and sends bad work back with clear fixes.
- It keeps `progress.md` current after every event: batch started, finished, fact-checked, committed;
  user decisions; issues; resume notes.
- It runs the build, looks at screenshots, and commits each stage.
- It owns `build.py`, `assets/site.css`, `assets/site.js`, `core.json`, `notes/facts.md` merges and the
  FINAL-PASS TODO list. Writers report tooling needs; they do not edit shared files.
- It decides on its own only when a safe default exists; it writes the open question for the user in
  `progress.md` "Questions for the user" and continues.
- It does not change the target repo. It does not push or publish without a user request.

### 7.3 Batches and waves

- A batch = 4-8 pages on one topic, usually mixed types: concept pages + their module pages + maybe a
  tour + maybe one visual. One writer subagent per batch. Example: "B3a Engine + scheduler: concepts
  engine-step-loop, request-lifecycle, scheduler; code scheduler-hpp, sequence-hpp, sequence; visual
  scheduler simulator".
- Name batches B1, B2, B3a, B3b ... Use the batch name as the prefix for its diagram scripts
  (`b3a_sched_decide.py`) and as its glossary file (`b3a.json`).
- Put the batch table in `plan.md` (pages and visual per batch) and the wave list.
- **Waves.** Run 6-7 subagents at the same time at most. Wave 1 = batches with no dependency (basics,
  core engine, model core, the hardest feature). Wave 2 = batches that build on wave 1. Wave 3 = scale,
  platform, start-up tour, reference. Then F.
- **Order of priority** if time is short: Basics → Tour 1 → core concepts → code map → reference.
- **Pipeline per batch:** writer → `build.py` 0 errors (`--preview` while others are broken) →
  **separate** fact-check subagent (fixes in place) → build 0 errors → supervisor reviews → commit.
  Start the fact check as soon as the writer finishes. Do not wait for the wave.
- Fact checks are not optional. In DeepInfer, the fact checkers found and fixed about 480 defects in
  about 7,000 claims (about 7 %; 16 to 43 per batch). Most were citations (wrong lines), then wrong
  defaults, wrong call order, over-general claims, and claims that only the docs supported.
- The fact checker is **never** the agent that wrote the batch.

### 7.4 Ownership rules for parallel writers

- Each page is its own file; a writer edits only its own pages.
- Nav ids are fixed. Writers do not edit nav files; they use `nav_after:` if they must add a page.
- One glossary file per batch. Search all files before adding a term. Do not redefine; report errors.
- One diagram script per diagram, with the batch prefix.
- One visual per file in `assets/viz/`; shared visual styles only in `viz.css`. No edits to `site.css`.
- Links to pages that do not exist yet are allowed (warning, grey text).
- Writers do not edit `notes/facts.md`. They report new facts and wrong facts in their final report.
  The supervisor (or the fact checker) merges them.

### 7.5 Usage limits and stops

- Subagents can be cut off by a usage limit. Their files on disk are then partial and not committed.
  Write in `progress.md` at once: which batches were running, which files are partial, the resume order.
- After the reset, **continue** a cut-off subagent (send it a message, or start a new one with "resume:
  these files exist and are partial; finish them") instead of a restart from zero.
- If a safety classifier stops a writer on some topic (likely a false positive on a technical word),
  **do not retry**. Tell the user. Defer the page: it stays as "soon" in the nav. Save the ready material
  (diagram scripts, facts) and write in `plan.md` "Deferred pages" what exists. Continue the other pages.
- If the user gives an instruction about usage (for example "let the running agents finish, then build,
  commit, push and pause"), write it in `progress.md` as a USER INSTRUCTION with the date.

### 7.6 Subagent prompt templates

Fill in the `{...}` parts. Give every subagent the absolute paths. Tell every subagent to report back:
what it did, files changed, build result, facts found, open questions.

#### A. Codebase survey

```
You survey the codebase {TARGET_PATH} (git repo of {PROJECT}, {REPO_URL}) at commit {SHA}.
Do not change any file. Report in your final message only (no report files).

Give me:
1. Size: files and lines per language; top-level folder map with one line per folder.
2. What the project is and what it runs on (cite README lines).
3. The main data/request flow from the public entry point to the output, as numbered steps
   with file:function for each step.
4. The architecture: processes, threads, main classes, language boundaries (for example Python/C++).
5. About 30 concepts a learner must understand, grouped, each with the files that implement it.
6. About 20 central files with line counts and a one-line role.
7. Good existing docs in the repo (English and not), images that the site can reuse.
8. Configuration sources: env vars, config classes, CLI flags (where they are declared).
9. Git history size, submodules and whether they are checked out, code comments in other languages.
10. Anything unusual or surprising.
Mark each claim with file:line. Say "not checked" when you did not open the file.
```

#### B. Foundation (Phase 1a)

```
You set up the tooling for "{SITE_NAME}", a static study site about {PROJECT}.
Explainer folder: {EXPLAINER_PATH}. Target repo (READ ONLY): {TARGET_PATH} at {SHA}.
Read {EXPLAINER_PATH}/project-instructions.md sections 3, 4, 5 and 6 first.
The tooling files from the DeepInfer explainer are already copied in (list: ...).

Do:
1. Adapt build.py, site.js, svglib.py, _template.py, STYLE.md as section 6.1 says
   (SHA, repo path, GitHub URL, site name, brand mark, storage keys, languages, comment translation label).
2. Write src/nav/*.json with every planned page from plan.md section 4 (fixed ids, groups).
3. Write src/glossary/core.json with the general terms of the domain (about 30).
4. Write one reference sample page: concepts/{SAMPLE_ID}. It must use every part of the concept template
   and most tags (x-code with highlight, cite, term, link, diagram, note, simplified, warning, deepdive,
   quiz). Write one diagram for it with svglib at width 1100.
5. Update STYLE.md: project vocabulary table, vendor/out-of-scope list, the sample page name.
6. Run python3 build.py until it has 0 errors. Take screenshots at 1280 and 390 px if Playwright works.
Rules: site text in {LANGUAGE_STYLE}; light look always (dark only by toggle); Python standard library only.
Report: files changed, build output summary, problems, questions for the supervisor.
```

#### C. Batch writer (Phase 1b and Phase 2)

```
You write batch {BATCH} of "{SITE_NAME}".
Explainer folder: {EXPLAINER_PATH}. Target repo (READ ONLY, pinned): {TARGET_PATH} at {SHA}.

Read first, in this order:
1. {EXPLAINER_PATH}/STYLE.md (all of it; it is binding)
2. {EXPLAINER_PATH}/instructions-svg.md (STYLE.md §10 overrides it: canvas 1100, min text 11)
3. {EXPLAINER_PATH}/notes/facts.md (shared verified facts; still open the code and cite it yourself)
4. Sample pages to copy: {SAMPLE_PAGES, e.g. src/concepts/hardware-platforms.html, src/code/llm-engine.html, src/tours/life-of-a-request.html}

Your pages (ids are fixed in src/nav/*.json):
- {page id}: {one line of scope}
- ...
Interactive visual: {name and behaviour, or "none"}.
You own: these page files; src/glossary/{batch}.json; diagrams/{batch}_*.py; assets/viz/{name}.js.
Glossary terms you own in this wave: {list}. Other terms: search src/glossary/*.json and reuse.
Do not edit: build.py, assets/site.css, site.js, nav files, other glossary files, notes/facts.md,
other writers' pages. Other writers build at the same time: use `python3 build.py --preview` while
another page is broken; your own pages must have 0 errors and no template warnings.

Content rules:
- The reader knows {READER_KNOWS} and little about {DOMAIN}. Start simple; then a full Deep dive with
  shapes, layouts, algorithms, edge cases, env vars, worked examples with real numbers, line-by-line reading.
- Every claim about the code: {{cite}} or <x-code>. Open every cited line yourself. Narrowest range.
- No guesses. If the code does not answer a question, write it as an open question on the page and
  list it in your report.
- Mark simplifications with <x-simplified>. Translate useful foreign-language comments with <x-tr>.
- Vendor/submodule internals are out of scope; explain only the calls.
- Site text in {LANGUAGE_STYLE} (STYLE.md §6). Captions start with "Figure: ".
- Diagrams: Diagram(width=1100), max 3 boxes across, max 3 panels, no text below 11; split big diagrams.

Report at the end (final message, no report files):
1. Pages written, diagrams, visual, glossary ids added.
2. Build result (errors and warnings for your pages).
3. NEW FACTS for notes/facts.md (each with file:line).
4. FACTS IN facts.md THAT ARE WRONG (with proof).
5. Claims you are less sure of (for the fact checker to check hard).
6. Open questions and cross-page problems (other pages that may now be wrong).
```

#### D. Fact checker (one per batch; never the writer)

```
You fact-check batch {BATCH} of "{SITE_NAME}". You did not write it. Be adversarial.
Explainer folder: {EXPLAINER_PATH}. Target repo (READ ONLY): {TARGET_PATH} at {SHA}.
Pages: {page ids}. Also their diagrams (diagrams/{batch}_*.py), visual (assets/viz/{name}.js) and
glossary file (src/glossary/{batch}.json). Read STYLE.md §6-7 and notes/facts.md first.
Writer's notes on uncertain claims: {paste from the writer report}.

For every claim about the code (prose, tables, captions, alt text, diagram labels, quiz answers,
glossary text, the rules copied into the visual):
1. Open the cited lines. Does the code say exactly this? Is the citation the narrowest correct range?
2. Check numbers, defaults, types, shapes, call order, which process/thread runs it, conditions
   ("always" vs "only when").
3. Check claims with no citation. Add a citation or remove the claim.
4. Check derived claims step by step. Reword to "earliest possible" or similar if the derivation has gaps.
5. Check that general domain statements are correct.
Fix defects in place (pages, diagram scripts, glossary, visual). Keep the writer's structure and the
language rules. Run python3 build.py (or --preview) until your pages have 0 errors.

Report (final message only):
- Number of claims checked and number of defects fixed, by type (citation, value, logic, missing source, other).
- The most important corrections (one line each).
- Corrections for notes/facts.md (add / change, with file:line).
- Other pages that may repeat a wrong claim (for the FINAL-PASS TODO list).
- Anything you could not decide (for the supervisor).
```

#### E. Final consistency pass

```
You do the final consistency pass of "{SITE_NAME}".
Explainer folder: {EXPLAINER_PATH}. Target repo (READ ONLY): {TARGET_PATH} at {SHA}.
1. Fix every open line in the FINAL-PASS TODO list in progress.md (list: ...). Check each against the code.
2. Sweep all pages against notes/facts.md: grep for each fact's key words; fix pages that disagree with
   the code. Where facts.md itself is wrong, fix it and say so.
3. Check that the same thing has the same name, number and default on every page (glossary, reference
   tables, tours, concepts). Re-run tools/*.py generators with --check.
4. Check diagrams that show changed facts.
5. Run python3 build.py: 0 errors. Run python3 build.py --strict and list the remaining warnings.
Report: each TODO with its fix, other fixes, pages changed, build result.
```

#### F. Site check

```
You check the built site {EXPLAINER_PATH}/site/ in a browser. Do not change page text.
Use Playwright through npx (scripts in your scratchpad; one output file name per run).
For every page, at 1280 px and 390 px width, with all deep dives opened:
- page-level horizontal overflow; console errors and page errors;
- internal links, anchors and glossary term links;
- each interactive visual renders and reacts to a click (also with the keyboard);
- light mode and dark mode (toggle) on a sample of pages.
Fix layout problems in assets/site.css or markup problems in page sources (identifiers in <code>,
table wrapping). Then build again.
Report: numbers (pages, links, broken links, anchors, overflow before/after, JS errors), fixes made,
problems that remain (with page and width), and 5-10 screenshot paths for the supervisor.
```

#### G. Diagram conversion (only if a diagram rule changes)

```
Convert these diagrams to the current rules: {list}. Rules: STYLE.md §10 (width 1100, no text
below 11, max 3 boxes across, max 3 panels; split if needed; keep all facts and sources).
Update the <x-diagram> tags and captions on the pages if you split a diagram.
Run python3 build.py --force-diagrams until 0 errors and no svglib edge warnings.
```

---

## 8. Tracking files

### 8.1 `plan.md`

Sections:
1. Goal (3 sentences).
2. Decisions (approved by the user): a table Topic | Decision. Add the date when a decision changes
   ("**Changed 2026-10-21:** ...").
3. Facts about the codebase (from the survey): size, languages, what it runs on, history, submodules,
   good docs, reusable images.
4. Site structure: the five parts and every planned page id with a one-line scope.
5. Page design (the templates of section 3.3, short) and the list of interactive visuals.
6. Technology (section 6, short).
7. Writing rules (short; refer to `STYLE.md`).
8. How the supervisor works (phases, at most N subagents at a time, rules for unattended work).
9. Definition of done.
10. Risks and what to do about them.
11. Answers from the user (dated).
12. Phase 1 in detail (steps 1a-1d and who does them).
13. Full build: batch table (Batch | Pages | Interactive visual), waves, pipeline per batch.
14. Deferred pages (with the reason and the ready material).

Status line at the top: "Status: **APPROVED <date>. Phase 1 only, then stop for user review.**"

### 8.2 `progress.md`

This file is the memory of the project. A new session must be able to continue from it alone.

```markdown
# {PROJECT} Explainer — Progress

Last update: <date>
Current phase: **<phase>** — <one line: what runs now, what waits>

## Phase status
| Phase | Status | Notes |

## Full build — batch status
| Batch | Writer | Fact check | Committed |
| B1 Basics I | done | done (23 defects fixed) | yes |

## RESUME NOTES (only while something is interrupted)
Which subagents were cut off, which files are partial, resume order (continue, not restart).

## Done   (newest first; one dated line per event)
- <date>: USER FEEDBACK: "<quote>". Cause: ... Action: ...
- <date>: USER DECISION: ...
- <date>: DECISION: <supervisor decision and reason>
- FINAL-PASS TODO: <cross-page fix found late; which pages; source of truth>
- DONE (final pass) — FINAL-PASS TODO: ...   (change the line when it is fixed)
- IDEA: ...

## Next step
<one paragraph; keep it current — a stale "Next step" misleads a new session>

## Questions for the user
(none open)

## Issues log
- <date> (<batch> facts): code facts found, contradictions between comments/docs and code.
- TODO (supervisor, tooling): ...
- FACT-CHECK FOCUS: <claim that the next fact checker must check hard>

## Subagent log
| Date | Task | Result |
```

Rules:
- Update it after every subagent finishes and after every user message that decides something.
- Quote user feedback word for word when it is short.
- Keep the FINAL-PASS TODO lines until the final pass marks them DONE.
- Before a usage limit or a long wait, write the resume notes first.

### 8.3 `notes/facts.md`

Shared verified facts. Writers read it first, so pages agree with each other.

```markdown
# Verified facts (shared by all writers)

Line numbers here are approximate (~). Open the file and cite exact lines on your page.
If a fact here is wrong, do NOT edit this file: say so in your report.

## Version
- {PROJECT} commit {SHA} (<date>). Submodules: ... (checked out or not).

## <Topic>
- <fact>, with path:~line. Mark inferred values "INFERRED". Mark wrong comments/docs ("the comment
  at x.hpp ~557 says 'shortest'; the code takes the most").

## Added after B5a (<date>)
## Added after the B5a fact check (<date>)
```

Rules:
- Only the supervisor (or a fact checker, on the supervisor's order) edits it.
- Add a dated section after each writer and each fact check, from their reports.
- When two sources conflict, write both, the resolution and the reason (DeepInfer example: the docs say
  "post-process N−1 while the device runs N"; the code post-processes N in the call that launches N+1.
  Same overlap, shifted numbering; pages use the code's numbering).
- When a fact changes after pages were written, add a FINAL-PASS TODO line that names the affected pages.

### 8.4 `README.md` (of the explainer repo)

Sections: what the site is and for whom; status (pages, deferred pages); **Code version** (full SHA with
link, date, checkout commands incl. `git submodule update --init --recursive`; line numbers belong to this
commit); Read the site (open `site/index.html`; what needs the internet: the Inter font and Prism for code
colours); the five parts table; Build the site (requirements, folder layout next to the target repo,
commands); Repository layout; How the content is made (language, citations, fact checks, out-of-scope
parts); a line that the pages were written with Claude Code and reviewed against the code, and that the
site is not an official project of the upstream authors.

---

## 9. Git and publishing rules

- Ask the user for the commit author identity before the first commit. Set it **repo-local**
  (`git config user.name`, `git config user.email`). Default for this user:
  `Thomas Paul <contact@thomaspaul.dev>`.
- `git init` the explainer repo. The target repo stays unchanged: never commit, check out or edit there.
  (Exception: the user may ask you to check out the pinned commit.)
- **Commit per stage**, so the user can review each stage: plan; Phase 1a; 1b; 1c; each batch after its
  fact check ("B3a: engine step loop, request lifecycle, scheduler + 3 module pages (fact-checked)");
  diagram pass; tooling fixes; progress-only updates; final pass.
- Commit `site/` too if the user wants to publish from the repo or view it on GitHub (DeepInfer did).
  Do not commit `build/`, `screenshots/`, `.site-tmp-*`, `.site-old-*`.
- **Push only when the user asks.** Never push by default.
- **Never rewrite pushed history.** Before the first push, a rewrite is possible if the user asks (for
  example to change the author email); keep a backup ref. After a push, only add new commits.
- Credentials: on WSL with a Windows Git credential manager, this worked:
  `git -c credential.helper= -c credential.helper="/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe" push origin main`.
- Publishing later: the site uses only relative links and CDN files from cdnjs / jsDelivr / unpkg /
  Google Fonts, so it can go to GitHub Pages or a claude.ai Artifact without changes. Ask the user first.

---

## 10. Pitfalls and lessons

**Process**
- The survey is a guide, not a source. It named an empty `__init__.py` as a dispatcher. Writers must
  open every file they cite.
- Fact checking is not optional: about 7 % of claims were wrong after writing. The writer cannot find its
  own errors well; use a separate agent.
- Errors repeat across pages. A fact fixed in one batch can still be wrong in pages from earlier
  batches. Record it as a FINAL-PASS TODO with the page list, and sweep at the end.
- Plan the look **before** Phase 1 samples. A late restyle costs a full subagent run and a diagram pass.
  Show the user a reference site and get a yes.
- Diagram readability: a 1500 canvas in a ~950 px column gives 7-8 px text. Use 1100 from the start.
- Put every planned page in the nav files in Phase 1. Then links to future pages work and give only
  warnings, and parallel writers do not edit shared files.
- Keep page-local `<style>` blocks out of pages; put shared styles in `site.css`. (DeepInfer still has
  local styles in `src/index.html` and `src/code/index.html`; a TODO to move them was not done.)
- Keep "Next step" in `progress.md` current. A stale line misleads a new session.

**Tooling**
- Parallel builds clash (one build deletes `site/` while another reads it) → atomic swap of a temp folder.
  On `/mnt/c` the old folder is sometimes not deleted (`.site-old-<pid>` stays); ignore it in git and
  delete it by hand.
- One broken page blocked every writer's preview → `--preview`.
- `mtime` is unreliable on Windows mounts → content-hash stamps for diagrams. Without them, a diagram
  did not rebuild after a script edit.
- Glossary duplicate ids across parallel batches → merge-time error. Assign term ownership per batch.
- A `.json` search index does not load from `file://` → write it as a `.js` file that sets a global.
- Bool and int parsing in the target code can surprise (DeepInfer: `=off` turns a feature ON; an empty
  int raises). Generated reference tables catch these; hand-written ones do not.
- Docs and examples can disagree with code defaults (DeepInfer: README said 32, the code default is 0).
  Always cite the code for defaults.
- Headless browsers may lack CJK fonts; Chinese shows as boxes only in screenshots.

**Look (user feedback)**
- The user hates dark and busy pages for learning material. Light always, dark only by toggle.
- Few boxes, borders and badges. Long-form article layout. Large body text.

**People and limits**
- Usage limits cut subagents off mid-file. Write resume notes; continue, do not restart.
- A safety classifier may stop a writer on a harmless technical topic. Do not retry. Ask the user, defer
  the page, keep it as "soon".
- The user answers questions in short form. Ask concrete questions with a proposed default.

**Contradictions in the DeepInfer tooling to fix when you copy it**
- `instructions-svg.md` says canvas 1500 and minimum text 9.5. `STYLE.md` §10 and `build.py` say 1100
  and 11. The site rule is 1100 / 11.
- `svglib.py` has `W = 1500` as the default and says 1500 in its docstring; `_template.py` calls
  `Diagram()` with no width. Set the default to 1100.
- `STYLE.md` §10 helper table says panels span `x = 20 … 1480` (true only for 1500). With 1100 it is
  `20 … 1080`.
- `STYLE.md` §11 lists the warning "width not 1500"; the build warns "canvas width is not 1100".
- `STYLE.md` §2 names glossary files by area (`basics.json`, `engine.json`); the project used per-batch
  files (`b1.json` ...). Per-batch files are better.
- `STYLE.md` §4.3 asks for `level` and a quiz on module pages, but `build.py` does not require them there.
  Keep the rule; optionally add `code` to `SECTIONS_NEED_LEVEL`.
- The STE check counts only the 25-word limit; the 20-word limit for instructions is not checked.

---

## 11. Adapting to other kinds of projects

The process, tooling, look and rules stay the same. These parts change:

| Part | ML inference engine (DeepInfer) | Web framework / backend service | Compiler / language tool | Database / storage engine | CLI tool / library |
|---|---|---|---|---|---|
| Basics pages | LLM, tokens, attention, KV cache, sampling, GPUs, parallelism, number formats | HTTP, routing, middleware, ORM, async I/O, sessions, caching | lexing, parsing, AST, IR, passes, codegen, linking | pages, B-trees/LSM, WAL, transactions, MVCC, replication | the problem domain, the main data model, the main algorithm |
| Tour 1 | Life of a request (`generate()` → tokens) | Life of a request (socket → handler → response) | Life of a source file (text → binary) | Life of a query / a write | Life of one command (argv → output) |
| Other tours | start-up, one engine step, one layer, one spec-decode round, multi-GPU step | start-up, one middleware chain, one DB transaction | one optimisation pass, error reporting | recovery after a crash, compaction, one checkpoint | config loading, plugin loading |
| Visuals | allocator, scheduler, attention toy, router | request pipeline stepper, cache hit/miss sim | parser stepper, pass pipeline | B-tree insert/split, WAL replay, lock table | state machine stepper |
| Reference generators | env vars (`environ.py`), config classes, C++ API from `.pyi` | settings, routes, CLI flags, HTTP API (OpenAPI) | flags, IR ops table, diagnostics list | config keys, SQL functions, error codes | flags, public API from type stubs or docs |
| Code map pages | Python + C++ modules | packages / apps | compiler phases | storage, query, txn layers | modules |

For a **non-Python target repo**:
- Add its file extensions to `LANG_BY_EXT` and the Prism components to `PRISM_COMPONENTS`
  (for example `prism-rust`, `prism-go`, `prism-java`, `prism-typescript`). `lang="none"` works for any file.
- Write generators in Python (standard library) with regexes or the language's own tools run once into a
  JSON file in `notes/`. Keep `build.py` standard-library only.
- The "Line N" reading and the `<x-code>` rules stay the same.
- The tooling itself stays Python: it only reads text files from the checkout.

For a **non-GitHub host**: change `github_url()` (GitLab: `{base}/-/blob/{sha}/{path}#L{a}-{b}`;
Gitea: `{base}/src/commit/{sha}/{path}#L{a}-L{b}`) and the "GitHub ↗" label.

For a **repo with no comments in another language**: the `<x-tr>` tag stays unused. For comments in a
language other than Chinese, change the label in `build.py`.

For a **domain the reader already knows**: make the basics part short (3-5 pages) or merge it into the
first concept pages. Keep at least one page that explains the main data model.

For a **very large repo**: pin a subset in `plan.md` (for example one subsystem), say on the home page
what is out of scope, and keep the code map tree complete (it is cheap) while module pages cover only the
important modules.

---

## 12. Checklists

### 12.1 Before you ask the user to approve the plan
- [ ] Survey done; you read its report and spot-checked 3-5 claims in the code.
- [ ] `plan.md` has decisions, page list per part, page design, visuals, batches, waves, definition of done.
- [ ] `progress.md` exists with the phase table and "Questions for the user".
- [ ] The questions of section 2 are asked, each with a proposed default.
- [ ] The pinned commit (and submodule commits) are written down.

### 12.2 Before the Phase 1 review (stop here)
- [ ] Tooling adapted (section 6.1): SHA, repo path, URLs, names, keys, languages, canvas 1100.
- [ ] `python3 build.py` has 0 errors; `--strict` warnings are understood.
- [ ] Nav files list every planned page; the sidebar shows "soon" for the rest.
- [ ] One sample page of each type: home (with system map and code version section), basics (with a
      visual), concept, tour (Tour 1), module page, code tree, one generated reference page.
- [ ] Every sample page was fact-checked by a separate agent; defects fixed.
- [ ] Version line on every page; full SHA in the footer; `#code-version` on the home page.
- [ ] Light look by default; dark only by toggle; checked at 1280 and 390 px; diagrams readable at 100 %.
- [ ] `STYLE.md` updated with what Phase 1 taught (templates, vocabulary, module-page template).
- [ ] `progress.md` updated; Phase 1 committed.
- [ ] The user has the list of sample pages to open and the open questions.

### 12.3 Per batch
- [ ] Writer prompt lists pages, visual, owned files, owned glossary ids, samples to copy.
- [ ] Writer report has new facts, wrong facts, uncertain claims, open questions.
- [ ] Build 0 errors for the batch pages; no template warnings.
- [ ] Separate fact checker ran; defects counted and fixed; build 0 errors again.
- [ ] `notes/facts.md` updated from both reports (dated section).
- [ ] Cross-page problems added to the FINAL-PASS TODO list with page names.
- [ ] Supervisor looked at 1-2 pages in a browser (desktop and phone).
- [ ] `progress.md` batch row updated; committed with a message that names the pages.

### 12.4 Final
- [ ] All batches committed; deferred pages listed in `plan.md` and the README.
- [ ] FINAL-PASS TODO list all DONE (final consistency pass, template E).
- [ ] Generators run with `--check`; reference tables current.
- [ ] Site check (template F): 0 overflow at 1280 and 390 px, 0 JS errors, 0 broken links and anchors,
      0 missing glossary terms, every visual works with mouse, keyboard and touch.
- [ ] `python3 build.py` 0 errors; `--strict` warnings are only expected ones (for example links to
      deferred pages).
- [ ] README: status, code version, how to read, how to build, layout, how the content was made.
- [ ] `progress.md`: current phase "Done", "Next step" current, no stale running entries.
- [ ] Final commit. Push only if the user asks.
