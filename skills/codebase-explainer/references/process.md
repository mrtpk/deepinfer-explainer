# Process: phases, supervisor role, batches, git

Read this before Phase 0 and again before the full build.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 7. Process

### 7.1 Phases

| Phase | Work | Who | Gate |
|---|---|---|---|
| 0a | Codebase survey | 1 survey subagent (template A) | supervisor reads it; claims are not trusted yet |
| 0b | Draft `plan.md` + `progress.md`; ask the questions of goal-and-questions.md | supervisor | **user approves the plan** |
| 1a | Foundation: copy `templates/`, fill in `explainer.json`, adapt `STYLE.md`, nav files with all planned pages, `core.json`, one reference sample page | 1 subagent (template B) | build 0 errors; supervisor checks screenshots |
| 1b | Sample set: home page + system map + code tree + one module page; one basics page + one visual + basics glossary; Tour 1; one generated reference page | 3-4 writer subagents in parallel | build 0 errors |
| 1c | Fact check of all sample pages; site check | fact-check subagents (template D) + supervisor | defects fixed |
| 1d | **STOP. Show the user the sample pages.** Apply look and depth feedback to the tooling and `STYLE.md` | supervisor | **user approves the full build** |
| 2 | Full build in batches and waves (7.3) | writer → fact checker → commit, per batch | each batch: build 0 errors, fact check done, committed |
| D | Diagram pass if a rule changed (for example convert Phase 1 diagrams to the 1100 canvas) | 1 subagent | build 0 errors |
| F | Final pass: consistency sweep (template E) + site check (template F) + README | 2 subagents + supervisor | definition of done (goal-and-questions.md) |

Phase 1 samples must cover each page type once: basics, concept, tour, module, reference, home.
Writers in Phase 2 copy these samples. Good samples make good batches.

In DeepInfer, the plan had a separate research phase (fact sheets before writing). Phase 1 showed that a
writer who reads the code for its own batch gives good pages. So the full build dropped the research
phase, and kept a separate fact check per batch. Do the same.

### 7.2 Supervisor role

The main session is the supervisor. It does **not** write pages.
- It delegates every long task to a subagent. It does short tasks itself (a CSS fix, a status update).
- It writes each subagent brief (subagent-prompts.md), checks the output, and sends bad work back with clear fixes.
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

## 9. Git and publishing rules

- Ask the user for the commit author identity before the first commit. Set it **repo-local**
  (`git config user.name`, `git config user.email`).
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
