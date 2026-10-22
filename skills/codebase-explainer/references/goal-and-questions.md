# Goal, outcome and the questions to ask first

Read this before you talk to the user about a new explainer project.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 1. Goal and outcome

**Goal.** Make a static website that teaches what happens in `{PROJECT}`. The reader clicks through
the pages and learns step by step. After the basics, the site also works as a reference.

**The outcome, when done:**
- A folder `site/` that opens from disk (`file://`) with a double-click on `site/index.html`. No server.
- Five parts: Learn the basics, Concepts, Guided tours, Code map, Reference (page-templates.md).
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

| # | Question | Why it matters | Suggested default (what the DeepInfer user chose) |
|---|---|---|---|
| 1 | Who is the reader? What do they know already? | Sets the basics part and the level of each page. | Knows Python (or the main language of the repo). Knows little about the domain (for example ML). |
| 2 | Depth: only a beginner guide, or also full study detail? | Decides if every page gets a deep dive. | Both. "I use this to study. Beginner-friendly, but I need details as well." |
| 3 | Local files or published? Are CDN libraries OK? | Decides the link rules and the CDN list. | Local for now, publish later. CDN is OK (cdnjs, jsDelivr, unpkg, Google Fonts). |
| 4 | Site structure: concepts + tours + code map? One page per file? | Decides the page count. | Concepts + guided tours + a code map with one page per important module. Not one page per file. |
| 5 | Folder for the explainer repo? | Avoid edits to the target repo. | `test-harness/<project>-explainer/`, next to the target repo checkout. |
| 6 | Language style of the site text? | Writing rules (writing-and-accuracy.md). | ASD-STE100 Simplified Technical English. |
| 7 | Scope: which parts get full pages? What is out of scope? | Avoids surprises late. | Be generous. Vendor submodules: explain only the interface. |
| 8 | Name of the site? | Title on every page. | "`{PROJECT}` Explained". |
| 9 | Look? Show the sample look or a reference site. | Avoids a restyle (pitfalls.md). | Light article look like Sebastian Raschka's Substack (`magazine.sebastianraschka.com`). Never auto dark mode. |
| 10 | Which commit to pin? | All line numbers depend on it. | The newest commit on the default branch on the day you start. |
| 11 | Git: local commits per stage? Push? Which author identity? | Git rules (process.md). | Commit per stage. Push only when asked. Ask for the author name and email; set them repo-local. |
| 12 | Stop after Phase 1 for a review? | The user checks look and depth early. | Yes. Always stop after Phase 1. |

Before you ask, run the codebase survey (subagent-prompts.md, template A). Then you can propose a concrete
page list with the questions. The user answers faster when there is a draft.

---
