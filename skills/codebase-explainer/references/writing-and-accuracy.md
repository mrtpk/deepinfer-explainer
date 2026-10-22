# Writing and accuracy rules

Read this before you write or fact-check text. Give it to every writer and fact checker.

Part of the `codebase-explainer` skill. The single-file version of this playbook is `project-instructions.md` in the DeepInfer explainer repo. Placeholders: `{PROJECT}`, `{SHA}`, `{SHORT_SHA}`, `{REPO_URL}`, `{SITE_NAME}`.

## 5. Writing and accuracy rules

### 5.1 Language style (configurable)

The site language is a project choice (goal-and-questions.md, question 6; `language_style` in
`explainer.json`). **Suggested default: ASD-STE100.** The DeepInfer user chose it.
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
