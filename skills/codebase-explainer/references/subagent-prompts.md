# Subagent prompt templates

Copy a template, fill in the {...} parts, and send it as the subagent prompt.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

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
Read these files of the codebase-explainer skill first: {SKILL_PATH}/references/page-templates.md,
style-and-diagrams.md, writing-and-accuracy.md and tooling.md.
The starter kit ({SKILL_PATH}/templates/) is already copied into the explainer folder.

Do:
1. Fill in explainer.json (project, site name, brand mark, repo path and URL, host, full SHA, language
   style, comment language, Prism languages). Adapt STYLE.md (<Project>, vocabulary, out-of-scope list).
   Run tools/gen_folder_tree.py and add folder descriptions. Do not change build.py unless the build
   cannot handle the project; then report the change.
2. Write src/nav/*.json with every planned page from plan.md section 4 (fixed ids, groups).
3. Write src/glossary/core.json with the general terms of the domain (about 30).
4. Replace the example pages. Write one reference sample page: concepts/{SAMPLE_ID}. It must use every part of the concept template
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
