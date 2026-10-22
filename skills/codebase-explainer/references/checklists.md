# Checklists

Use these at each gate: plan approval, Phase 1 review, each batch, the final pass.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 12. Checklists

### 12.1 Before you ask the user to approve the plan
- [ ] Survey done; you read its report and spot-checked 3-5 claims in the code.
- [ ] `plan.md` has decisions, page list per part, page design, visuals, batches, waves, definition of done.
- [ ] `progress.md` exists with the phase table and "Questions for the user".
- [ ] The questions of goal-and-questions.md are asked, each with a proposed default.
- [ ] The pinned commit (and submodule commits) are written down.

### 12.2 Before the Phase 1 review (stop here)
- [ ] `explainer.json` filled in (name, repo path, URL, host, full SHA, language style, Prism languages); example pages replaced.
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
