# Pitfalls and lessons

Read this once before Phase 1. These are the real problems of the DeepInfer Explained project.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

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

**Contradictions in the original DeepInfer tooling**

The starter kit fixes the first five. The last two still apply to the kit.
- `instructions-svg.md` says canvas 1500 and minimum text 9.5. `STYLE.md` §10 and `build.py` say 1100
  and 11. The site rule is 1100 / 11.
- `svglib.py` has `W = 1500` as the default and says 1500 in its docstring; `_template.py` calls
  `Diagram()` with no width. The kit sets the default to 1100.
- `STYLE.md` §10 helper table says panels span `x = 20 … 1480` (true only for 1500). With 1100 it is
  `20 … 1080`.
- `STYLE.md` §11 lists the warning "width not 1500"; the build warns "canvas width is not 1100".
- `STYLE.md` §2 names glossary files by area (`basics.json`, `engine.json`); the project used per-batch
  files (`b1.json` ...). Per-batch files are better.
- `STYLE.md` §4.3 asks for `level` and a quiz on module pages, but `build.py` does not require them there.
  Keep the rule; optionally add `code` to `SECTIONS_NEED_LEVEL`.
- The STE check counts only the 25-word limit; the 20-word limit for instructions is not checked.

---
