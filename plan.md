# DeepInfer Explainer — Plan

Status: **APPROVED 2026-10-21. Phase 1 only, then stop for user review.**
Date: 2026-10-21
Source repo: `../DeepInfer` at commit `9bd9cf2` (github.com/deepseek-ai/DeepInfer)

---

## 1. Goal

Make a static website that teaches a beginner what happens in the DeepInfer codebase.
The reader clicks through the pages and learns step by step.
The site also works as a reference after the reader learns the basics.

## 2. Decisions (approved by the user)

| Topic | Decision |
|---|---|
| Reader | Knows Python. Knows little about ML. |
| Hosting | Local files for now. CDN libraries are permitted. The user will publish it later. |
| Depth | Concept pages + guided tours + a file index. Not one page for every file. |
| Location | `test-harness/deepinfer-explainer/`. The DeepInfer repo stays unchanged. |
| Site language | ASD-STE100 (Simplified Technical English) for all site text. |
| Checkpoint | Stop after Phase 1. The user reviews the sample pages before the full build. |
| Scope | Be generous. VL (vision) path and Engram get full pages, not short pages. |
| Name | "DeepInfer Explained". |
| Code version | Show the DeepInfer commit prominently (user request 2026-10-21): a version line under every page title, full SHA + date + message in the footer, and a home section `#code-version` with checkout commands and the 6 pinned vendor submodule commits. Commit: `9bd9cf243fc53ef9afbf8f04d391d989117d6ab9` (2026-10-21). |
| Depth of detail | The user studies with this site. Each page starts beginner-friendly, then gives full detail: exact tensor shapes, data layouts, algorithms, edge cases, env vars, and line-by-line code reading. |
| Look | **Changed 2026-10-21:** Page style is a light, readable article look like https://magazine.sebastianraschka.com/p/the-big-llm-architecture-comparison (white background, dark gray text, large body font, one centered column, few boxes). Always light by default; dark only by toggle. Diagrams still follow `instructions-svg.md`. |

## 3. Facts about the codebase (from the survey)

- About 342 files: 270 Python (~46k lines in `deepinfer/`), 33 C++ files (~6k lines in `csrc/`).
- One model: DeepSeek-V4.1-Flash. Two hardware types: NVIDIA SM100 and Huawei Ascend.
- Derived from vLLM. Some comments are in Chinese.
- Git history has only 4 commits. The site cannot teach "how the code changed". It teaches the code as it is.
- `vendor/` submodules (FlashMLA, DeepGEMM, DeepEP, DeepSelect) are not checked out. The site explains only how DeepInfer calls them.
- Good English sources: `doc/inference_deployment_qa.md`, `v4_modules/__init__.py`, `examples/README.md`, `eval/README.md`, `deepinfer/_C/engine.pyi`.
- Reusable images: `doc/images/architecture_overview.png` and 3 Pareto charts.

## 4. Site structure (about 100–120 pages)

```
deepinfer-explainer/
  index.html              Home: what DeepInfer is, "start here", learning paths, clickable map
  learn/                  PART 1 — Basics for a Python developer (~10 pages)
  concepts/               PART 2 — DeepInfer concepts (~25 pages)
  tours/                  PART 3 — Guided tours through real code (~6 tours)
  code/                   PART 4 — Code map: folder tree + one page per important module (~45 pages)
  reference/              PART 5 — Env vars, config classes, C++ API, glossary, FAQ
  assets/                 CSS, JS, images, search index
```

### Part 1 — Learn the basics (no DeepInfer code yet)
1. What an LLM does: text in, next token out
2. Tokens and tokenizers
3. Inside a transformer: embeddings, layers, attention, MLP, output head
4. Attention, step by step (with a small interactive example)
5. Prefill and decode: the two phases of generation
6. The KV cache: why we keep keys and values
7. Sampling: temperature, top-k, top-p
8. Batching: many requests on one GPU
9. GPUs, kernels, and why speed is hard
10. Parallelism basics: data, context, and expert parallelism
11. Mixture of Experts (MoE)
12. Number formats: BF16, FP8, FP4

### Part 2 — DeepInfer concepts
Each page connects a concept to the files that implement it. Groups:
- **Engine:** offline API and step loop · request/sequence lifecycle · scheduler (prefill vs decode, chunked prefill, preemption) · paged KV cache and block manager · input metadata (varlen batching) · CUDA graphs · zero-overhead (async) scheduling
- **Model (V4.1):** model map · MLA attention · sparse attention with an indexer · sliding-window attention · KV compression · cross-layer KV sharing · YOCO / SWA bounded replay · mHC residual mixing · MoE routing · mega-MoE · Engram n-gram memory · vision encoder (VL)
- **Decoding:** sampler · speculative decoding (draft, verify, accept/reject) · DSpark confidence-scheduled verification · structured outputs · determinism and batch invariance
- **Scale:** DP with step-type votes · context parallelism (mirror CP) · expert parallelism (dispatch/combine) · EPLB · hardware discovery (`deep_cluster`)
- **Platform:** hardware abstraction (NVIDIA vs Ascend) · TileLang kernels · the Python ↔ C++ boundary (pybind11) · low-precision formats · weight loading

### Part 3 — Guided tours (step-by-step, with real code excerpts)
1. **Life of a request** — from `llm.generate()` to output tokens (13 stops)
2. **Start-up** — launch, process groups, weight loading, memory profile, KV cache allocation, CUDA graph capture
3. **One engine step** — schedule → prepare inputs → forward → sample → post-process, and how ZOS overlaps them
4. **Inside one decoder layer** — mHC → attention (MLA + indexer + SWA) → MoE → mHC
5. **One speculative decoding round** — draft → verify → accept → next drafts and confidence
6. **One step on many GPUs** — DP vote, CP all-gather, EP dispatch/combine, EPLB rebalance

### Part 4 — Code map
- An interactive folder tree. Each folder has a short description, file counts, and line counts.
- One page for each important module (about 45). Each page has: purpose, key classes and functions, "who calls it", "what it calls", related concepts, links to the source on GitHub at commit `9bd9cf2`.
- Small files (`__init__.py`, most tests) appear in the tree only.

### Part 5 — Reference
- All `DEEPINFER_*` env vars (from `deepinfer/environ.py`), grouped, with defaults and where they are read
- Config classes (`ModelConfig`, `CacheConfig`, `ParallelConfig`, `SchedulerConfig`)
- C++ engine API (from `deepinfer/_C/engine.pyi`)
- Glossary (every term links to its concept page)
- FAQ, using `doc/inference_deployment_qa.md`

## 5. Page design (one template for all pages)

Each concept or tour page has these parts:
1. **Level badge** — Beginner / Intermediate / Advanced
2. **Before you read** — links to the prerequisite pages
3. **In one sentence** — the main idea
4. **The idea** — plain explanation with an everyday analogy
5. **Diagram** — SVG made by a Python script that follows `instructions-svg.md`; some pages have an interactive visual
6. **In the code** — real code excerpts with `file:line` and a GitHub link
7. **Deep dive** — full detail for study: exact shapes and dtypes, memory layouts, the algorithm step by step, edge cases, related env vars and config, design trade-offs, and numbers from `doc/`. Long code is read line by line.
8. **What can go wrong / why it matters**
9. **Check yourself** — 3–5 questions with hidden answers (some easy, some hard)
10. **Next / previous** buttons and related pages

All pages have: a left sidebar, breadcrumbs, a search box, glossary tooltips on terms, light and dark mode, and a mobile layout.

### Interactive visuals (vanilla JS, about 6–8)
- Clickable system map on the home page (each box opens its page)
- Attention toy: change a token and see the attention weights change
- KV cache block allocator: add requests, see blocks fill, see preemption
- Scheduler simulator: watch prefill and decode steps, chunked prefill
- Speculative decoding: draft tokens, verify, accept or reject
- MoE router: tokens go to experts; EPLB moves "hot" experts
- ZOS timeline: CPU and GPU work with and without overlap
- Life-of-a-request stepper (Tour 1)

## 6. Technology

- Plain static HTML, one shared CSS file, one shared JS file. No framework.
- A small Python generator `build.py` (standard library only):
  - Page content lives in `src/` as HTML fragments with a small header (title, level, prerequisites, next).
  - `build.py` adds the shared layout: sidebar, breadcrumbs, next/previous, glossary tooltips.
  - `build.py` takes code excerpts from the real repo by file and line range. Excerpts are always exact.
  - `build.py` makes the search index as a `.js` file. (A `.json` file does not load from `file://`.)
  - `build.py` fails if a link is broken or a cited line range does not exist.
- Diagrams: Python scripts in `diagrams/` use one shared helper `svglib.py` (from `instructions-svg.md` section 9). `build.py` runs them and puts the SVGs inline in the pages. No Mermaid, so all diagrams have one look.
- Site colors and fonts use the tokens in `instructions-svg.md` section 2 and 3. The site is light by default. In dark mode, diagrams stay on white cards.
- CDN libraries with pinned versions: Prism (code colors) only. Only cdnjs / jsDelivr / unpkg, so the site can be published as a claude.ai Artifact later.
- The output in `site/` opens from disk with a double-click on `site/index.html`.

## 7. Writing rules

- Short sentences. Explain each new term the first time, and link it to the glossary.
- Every claim about the code cites `file:line`. No claim without a source.
- Translate Chinese comments where they help.
- Do not explain the internals of `vendor/` libraries. Only explain how DeepInfer uses them.
- Mark simplifications clearly ("Simplified: ...").
- All site text is in ASD-STE100. Code, file names and technical names stay as they are.

## 8. How I will work (supervisor + subagents)

I am the supervisor. I write the brief for each subagent, check its output, and update `progress.md`.
Subagents write to separate folders, so they do not conflict. I run at most about 6 at the same time.

| Phase | Work | Who | Output |
|---|---|---|---|
| 0 | Plan approval | User | approved `plan.md` |
| 1 | Foundation: `build.py`, layout, CSS/JS, page template, 1 sample page of each type, style guide | 1 subagent | working skeleton |
| 2 | Research: read the code and write fact sheets with `file:line` citations | 6 subagents in parallel (engine+scheduler · worker+cache+ZOS · model architecture · MoE+parallelism · sampler+spec-decode+SO · platform+kernels+config+loading) | `notes/*.md` |
| 3 | Write pages from the fact sheets | 5–6 subagents in parallel (basics · concepts ×2 · tours · code map · reference) | `src/**` |
| 4 | Interactive visuals | 2 subagents | `assets/viz/*.js` |
| 5 | Verification | Fact-check subagents (each claim against the code), a beginner-reader review, `build.py` link and citation checks, browser screenshots (Playwright through `npx`, if it installs) | fixes and a review report |
| 6 | Polish: home page, learning paths, final check | supervisor + 1 subagent | final `site/` |

Rules for unattended work:
- After each phase, I update `progress.md` (done, open issues, next step). If the session restarts, `progress.md` tells where to continue.
- I check each subagent's output before the next phase starts. I send bad work back with clear fixes.
- I do not change the `DeepInfer/` repo. I do not push, publish, or send anything outside this machine.
- If a decision belongs to the user, I write it in `progress.md` under "Questions for the user" and continue with a safe default.

## 9. Definition of done

- All planned pages exist and `build.py` runs with zero errors (no broken links, no bad citations).
- Every concept and tour page has a diagram, code excerpts, and "Check yourself".
- Fact-check pass: no known false claims remain.
- Each interactive visual works in Chrome on desktop and phone width (screenshots checked).
- A beginner can follow the path Home → Basics → Tour 1 without a dead end.

## 10. Risks

| Risk | What I do |
|---|---|
| Wrong explanations (the code is complex) | Fact sheets first, citations always, a separate fact-check pass |
| Pages differ in style | One template, one style guide, sample pages from Phase 1 given to every writer |
| Vendor kernels are not in the repo | Explain the interface only, and say so on the page |
| The site is too large to finish | Order of priority: Basics → Tour 1 → core concepts → code map → reference |

## 11. Answers from the user (2026-10-21)

1. Site language: ASD-STE100.
2. Checkpoint: Stop after Phase 1 for review.
3. Scope: Be generous. Full pages for VL and Engram.
4. Name: "DeepInfer Explained". Look: `instructions-svg.md`.

## 12. Phase 1 in detail (the review package)

| Step | Work | Who |
|---|---|---|
| 1a | `build.py`, page layout, CSS, JS (search, sidebar, tooltips, quiz), `svglib.py`, `STYLE.md` for writers, and one reference sample page: concept "NVIDIA and Ascend" (includes "Is it AFD?") | 1 subagent |
| 1b | Three sample sets in parallel: (i) home page + clickable system map + code-map tree + module page `llm_engine.py`; (ii) basics page "The KV cache" + interactive block allocator + glossary; (iii) Tour 1 "Life of a request" + env-var reference | 3 subagents |
| 1c | Fact check of all sample pages against the code, build check, browser screenshots | 1 subagent + supervisor |
| 1d | Stop. Show the user the sample pages. | supervisor |
