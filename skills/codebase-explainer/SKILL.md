---
name: codebase-explainer
description: Plan and build a static HTML study site ("<Project> Explained") that teaches an open-source codebase to a beginner and also gives full detail for study. The site has basics pages, concept pages, guided tours through real code, a code map, generated reference tables, SVG diagrams, interactive visuals, quizzes and a glossary. Every claim cites file:line at a pinned commit, and a separate fact-checker agent checks each batch. Use this skill whenever the user wants an explainer site, a learning site, a study guide, a walkthrough, a guided tour, onboarding docs or "explain this repo" material for a codebase or a GitHub/GitLab repository, even when they do not say "site" or "skill". Do not use it for API reference docs that a doc generator makes, or for a single README.
---

# Codebase explainer

This skill makes a static website that teaches one open-source codebase. The reader starts with no
knowledge of the code. Each page starts simple, then gives a full "Deep dive". The model project is
*DeepInfer Explained* (106 pages, 91 diagrams, 8 interactive visuals, 321 glossary terms; fact checkers
corrected about 7 % of about 7,000 claims).

You act as the **supervisor**. You plan, ask the user, delegate long work to subagents, review, track
progress and commit. You do not write the pages yourself.

## Files in this skill

| Path | Read it when |
|---|---|
| `references/goal-and-questions.md` | before you talk to the user: outcome, definition of done, the questions |
| `references/page-templates.md` | when you plan the page list, and before you review pages |
| `references/style-and-diagrams.md` | before you touch CSS or diagrams, or review screenshots |
| `references/writing-and-accuracy.md` | give it to every writer and fact checker |
| `references/tooling.md` | when you set up the folder, or when a build error is unclear |
| `references/process.md` | before Phase 0 and before the full build (phases, batches, git) |
| `references/subagent-prompts.md` | each time you start a subagent (templates A-G) |
| `references/tracking-files.md` | when you write `plan.md`, `progress.md`, `notes/facts.md`, `README.md` |
| `references/pitfalls.md` | once, before Phase 1 |
| `references/adapting.md` | when the repo is not ML, not Python, or not on GitHub |
| `references/checklists.md` | at each gate |
| `templates/` | the starter kit: copy it into the new explainer folder |

## Workflow

### Step 0: Survey the codebase

1. Get a local checkout of the target repo. Do not change it. Note the full HEAD commit id: this is the pin.
2. Start a survey subagent with template A (`references/subagent-prompts.md`). It reports the folder map,
   the main data flow, the architecture, about 30 concepts and about 20 central files.
3. Spot-check 3-5 survey claims in the code. Surveys are wrong sometimes (the DeepInfer survey named an
   empty `__init__.py` as the dispatcher). Treat the survey as a guide, not a source.

### Step 1: Ask the user, write the plan, get approval

Write a draft `plan.md` and `progress.md` from `templates/` with a concrete page list. Then ask the user
these questions, each with a proposed default (details in `references/goal-and-questions.md`):

1. Who is the reader, and what do they know already?
2. Only a beginner guide, or also full study detail? (Suggested: both; a deep dive on every page.)
3. Local files or published? Are CDN libraries OK?
4. Structure: basics + concepts + tours + code map + reference? One page per file? (Suggested: one page per important module only.)
5. Which folder for the explainer repo?
6. Language style of the site text? (Suggested: ASD-STE100 Simplified Technical English. This is a
   choice: set `language_style` to `ste` or `plain` in `explainer.json`.)
7. Scope: what gets full pages, what is out of scope (vendored code, submodules)?
8. Site name? (Suggested: "<Project> Explained".)
9. Look? (Suggested: a light article look, like a long-form magazine article; dark only by a toggle.)
10. Which commit to pin?
11. Git: commit per stage? Push? Which author name and email?
12. Stop after Phase 1 for a review? (Suggested: yes.)

**Stop point 1.** Do not build before the user approves `plan.md`. Write the answers into `plan.md`
section 2 with the date.

### Step 2: Phase 1, foundation and samples

1. Copy the starter kit: `cp -r <this skill>/templates/. <project>-explainer/`. Fill in
   `explainer.json`: it is the only file with project values (name, repo path and URL, host, full SHA,
   language style, Prism languages). `git init`; set the author repo-local.
2. Run `python3 tools/gen_folder_tree.py && python3 build.py`. The example pages must build with 0 errors
   before you change anything else.
3. Start the foundation subagent (template B): `STYLE.md` for this project, nav files with **every**
   planned page, core glossary, and one reference concept page.
4. Start 3-4 writer subagents in parallel (template C) for one sample of each page type: home page with
   the system map and `#code-version`; one basics page with a visual; Tour 1 "Life of a request"; one
   module page and the code tree; one generated reference page.
5. Start a **separate** fact-check subagent (template D) for each sample set. Then do a site check (template F).
6. Commit Phase 1.

**Stop point 2.** Show the user the sample pages (paths in `site/`) and ask for feedback on look,
depth and language. Change the tooling and `STYLE.md` from the feedback. Get approval for the full build.
A late restyle is expensive: settle the look here.

### Step 3: Full build in batches

1. Put a batch table in `plan.md`: batches of 4-8 pages on one topic (concepts + their module pages +
   maybe a tour + maybe one visual), and waves of at most 6-7 parallel subagents.
2. For each batch, run this loop:
   - **Writer** subagent (template C). It owns its pages, `src/glossary/<batch>.json`,
     `diagrams/<batch>_*.py` and one visual. It reports new facts, wrong facts, uncertain claims and open questions.
   - Build: 0 errors for its pages (`--preview` while other writers have broken pages).
   - **Fact checker** subagent (template D). It is never the writer. It checks every claim against the
     code, fixes in place and counts defects.
   - Supervisor: merge both reports into `notes/facts.md`; add cross-page fixes to the FINAL-PASS TODO
     list in `progress.md`; look at 1-2 pages in a browser; update `progress.md`; commit the batch.
3. Start a fact check as soon as its writer finishes. Do not wait for the whole wave.

Why a separate fact checker: a writer does not find its own errors well. In DeepInfer each batch had 16-43
defects after writing, mostly wrong line numbers, wrong defaults and over-general claims.

### Step 4: Final pass

1. Consistency subagent (template E): fix every FINAL-PASS TODO, sweep all pages against `notes/facts.md`,
   run every generator with `--check`.
2. Site check subagent (template F): every page at 1280 and 390 px, deep dives open; no page overflow,
   no JS errors, no broken links or anchors, every visual works.
3. Write `README.md` from the template. Mark `progress.md` as done. Commit.

**Stop point 3.** Push or publish only when the user asks.

## Rules that matter most

- **Every claim about the code has a citation** (`{{cite path:line}}` or `<x-code>`) at the pinned commit.
  The build reads excerpts from the checkout and fails on a bad path, line range, link or glossary id,
  or when the checkout is at another commit.
- **No guesses.** When the code does not answer a question, write it on the page as an open question.
- **Mark simplifications** with `<x-simplified>`. Out-of-scope code: explain only how the project calls it.
- **Every page has two depths:** a beginner start (one sentence, the idea, a diagram) and a full deep
  dive (shapes and types, layouts, algorithm steps, edge cases, env vars, a worked example with numbers).
- **Look:** light background always; dark only by the toggle; Inter 18 px / 1.7; prose column about
  720 px; figures up to 1100 px; few boxes and badges. The DeepInfer user strongly disliked a dark, busy
  first version ("This is learning material").
- **Diagrams:** one Python script per diagram with `svglib.py`; canvas width 1100; no text below 11;
  at most 3 boxes across and 3 panels; split big diagrams; captions start with "Figure: ".
- **Generate reference tables** from the code (env vars, config, CLI flags, folder tree). Hand-copied
  tables go wrong.
- **Parallel writers never edit shared files.** All page ids are in the nav files from Phase 1; each
  batch owns its own glossary file and diagram prefix; only the supervisor edits `build.py`, `site.css`,
  `core.json` and `notes/facts.md`.

## Keep the project resumable

- `progress.md` is the memory of the project. Update it after every subagent and every user decision.
  Keep "Next step" current.
- Usage limits can stop subagents in the middle of a file. Write resume notes at once, then continue the
  work after the reset instead of a restart.
- If a safety classifier stops a writer on a harmless technical topic, do not retry. Ask the user, and
  defer the page (it stays "soon" in the menu).
- Git: commit per stage; never rewrite pushed history; push only on request.

## Starter kit quick reference

```bash
python3 tools/gen_folder_tree.py   # fill the code-map tree (src/code/index.html)
python3 build.py                   # build site/ (0 errors needed)
python3 build.py --strict          # warnings also fail
python3 build.py --preview         # write site/ even with errors
python3 build.py --force-diagrams  # re-run all diagram scripts
```

Page tags: `<x-sentence>`, `<x-code file lines highlight caption>`, `<x-tr line>`, `{{cite}}`,
`{{term}}`, `{{link}}`, `{{project name|short_sha|...}}`, `<x-diagram name alt caption>`, `<x-note>`,
`<x-simplified>`, `<x-warning>`, `<x-deepdive title>`, `<x-quiz>`/`<x-q level>`/`<x-a>`,
`<x-stop n title>`, `<x-viz id title>`, `<x-img>`, `<x-version />`. Full reference: `templates/STYLE.md`
section 5 and `references/tooling.md`.
