# DeepInfer Explainer — Progress

Last update: 2026-10-21
Current phase: **Full build — wave 1** (plan section 13)

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 0 Plan approval | done | Approved 2026-10-21 with answers (plan section 11) |
| 1 Foundation | done | User reviewed and approved: "I like it. build for all. fact check it as well." |
| Full build (plan §13) | running | Batches B1–B11, D, F. Writer → fact check → commit per batch. |

## Full build — batch status

| Batch | Writer | Fact check | Committed |
|---|---|---|---|
| B1 Basics I | done | done (23 defects fixed) | yes |
| B2 Basics II | done | done (16 defects fixed) | yes |
| B3a Engine + scheduler | done | done (26 defects fixed) | yes |
| B3b API + cache | done | done (16 defects fixed) | yes |
| B4a Inputs + graphs | done | running | — |
| B4b Worker + ZOS | done | done (26 defects fixed) | yes |
| B5a Attention I | done | done (43 defects fixed) | yes |
| B5b Attention II | done | running | — |
| B6a Layer + mHC | done | running | — |
| B6b Engram + VL | done | done (36 defects fixed) | yes |
| B7 MoE + EP | done | done (40 defects fixed) | yes |
| B8 Scale | running | — | — |
| B9 Decoding | done | done (25 defects fixed) | yes |
| B10a SO + precision | running | — | — |
| B10b Kernels + loading | STOPPED (safety classifier on first page; glossary + 3 diagrams only) — waiting for user | — | — |
| B11 Start-up + reference | running | — | — |
| D Diagrams to 1100 | done | n/a | yes |
| F Final pass | later | — | — |

## RESUMED after the usage limit (was stopped 2026-10-21 18:21 Dubai)

Subagents were cut off. Their files on disk are partial and NOT committed.
Resume order after the reset:
1. B3b writer FINISHED (needs fact check; also: facts.md fork_seq + _preempt frees state and MTP slots; learn/kv-cache slot mapping is on device with ZOS; possible block leak for aborted chunked prompts). Resume (continue, not restart): writers B4a, B4b, B5b, B6a, B6b; fact checks B3a, B7, B9.
2. Then: fact checks for B3b, B4a, B4b, B5b, B6a, B6b; writers B8, B10a, B10b, B11; final pass F (TODOs below).
Committed so far: Phase 1, D, B1, B2, B5a.

## Done

- FINAL-PASS TODO: check every page that describes the DFlash hook position (Tour 1 stop 8/11, model-map, decoder-layer, dflash pages): it runs after the attention mHC pre + norm, before attention, and stores the mean of the trunk streams.

- DECISION 2026-10-21: doc QA ~274 "post-process(N−1) while device runs N" and the code (post-process N in the call that launches N+1) are the same overlap with shifted numbering — not a contradiction. Pages use the code's numbering.

- FINAL-PASS TODO: Tour 1 stop 5: item 6 sums full lengths (incl. outputs after recompute), not prompt lengths; the token limit when unset is 2**30; structured output stops on preempt only when status != 0. learn/kv-cache: with ZOS the decode slot mapping is computed on the device.

- FINAL-PASS TODO: code/llm-engine.html says no Python code calls fork_seq — examples/benchmark.py does (facts.md). Tour 1 simplification box: the fifth request starts at the next attempt point after a slot frees, not when another finishes.
- FINAL-PASS TODO (CSS): wide tables inside deep dives scroll sideways; add a wrapping table style.

- IDEA for B10a/final: interactive number-format converter (value → BF16 / E4M3 / E2M1 bits) for learn/number-formats and concepts/low-precision-formats.

- FINAL-PASS TODO: reference/env-vars.html: (a) DEEPINFER_FORCE_IMBALANCE_RATIO from the env never takes effect (model_runner.py ~509-512); (b) line ~494 says the shared expert runs "while combine runs" — the code shows only the launch order; overlap is decided inside DeepEP (see facts.md).

- FINAL-PASS TODO: learn/kv-cache.html (already fact-checked) may say ica_state is float32 state for ratio-2 layers and that the main KV entry is 528 B; per B5a, ica_state is None in practice and the loader default is FP4 (288 B). Check and fix in pass F.
- 2026-10-21: build.py --preview writes site/ even with errors (writers asked: one broken page blocked all previews).

- 2026-10-21: User asked to change the commit email to contact@thomaspaul.dev; history rewritten (backup ref refs/backup/before-email-rewrite, not pushed). Repo-local user.email set.
- 2026-10-21: User pushed main to https://github.com/mrtpk/deepinfer-explainer (origin). RULE from now: never rewrite pushed history; only add new local commits; push only when the user asks (works with: git -c credential.helper= -c credential.helper="/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe" push origin main).

- 2026-10-21: D done: 12 diagrams at 1100 (in-page scale 0.86). Supervisor CSS fix: figures nested in deep dives/stops break out to full width (container query units).

- 2026-10-21: Codebase survey by a subagent (directory map, request flow, architecture, 30 concepts, 20 central files). Results are in `plan.md` section 3.
- 2026-10-21: User decisions: Python-level reader, local site with CDN, concepts + tours + file index, folder `deepinfer-explainer/`.
- 2026-10-21: `plan.md` draft written.

- 2026-10-21: Plan approved. Answers: STE site text; stop after Phase 1; generous scope; name "DeepInfer Explained"; look from `instructions-svg.md`.
- 2026-10-21: User added: "I use this to study. Beginner-friendly, but I need details as well." Added a "Deep dive" part to every page (plan section 5).

- 2026-10-21: Phase 1a done (build.py, STYLE.md, assets, svglib, sample page "NVIDIA and Ascend", 34 glossary terms).
- 2026-10-21: Supervisor fix: diagrams were too small in the 860 px column. Wider column at >= 1640 px screens; STYLE.md §10 readability rule (bigger fonts, max 3 boxes across, max 3 panels, split big diagrams).

- 2026-10-21: USER FEEDBACK: "I hate the color scheme... need light background, readable". Cause: site followed OS dark mode; also too many boxes, borders and badges. Restyle subagent started (model: Raschka Substack article). Plan section 2 updated.

- 2026-10-21: USER REQUEST: show the DeepInfer commit id so students can go back to it. Sent to the restyle agent (version line on every page + footer) and fact-checker A (home section #code-version with checkout commands and vendor submodule commits).

- TODO (supervisor, before user review): diagram text is still ~7-8px at 1280 (1500 canvas shown at ~950px). Plan: one subagent converts all site diagrams so they display near 1:1 (narrower canvas ~1000-1100 or larger fonts), after fact checkers finish.

- 2026-10-21: Phase 1 fact checks done (A: 30 defects fixed, B: 36). Step-71 claim reworded to "earliest possible". Commits 966f05e, 92608af (local git, user asked; no push).
- 2026-10-21: User approved Phase 1 and asked for the full build with fact checks, and local git commits per stage.

## Next step

Wave 1 writers running. Start fact checks as batches finish. Then wave 2. Then supervisor: tooling TODOs, final build, screenshots check. Then 1d: ping the user for review.

## Questions for the user

(none open)

## Issues log

- 2026-10-21: Facts found by 1a: DEEPINFER_ACCELERATOR defaults to "nvidia" (environ.py:101), so Ascend users must export it; `_so/` folder name comes from scripts/build.sh, not setup.py; accelerator_kind()=="cpu" still gives PlatformGPU.
- 2026-10-21 (1b-i facts): _init_cache docstring says min block count over ranks, code uses the mean rounded down to even (worker/base.py:264-266). Engine and worker share one process; only CP ranks 1..cp-1 are spawned. With ZOS, step() returns the previous step's outputs as raw pointers (LLM must clone). llm_engine.py:800-858 are empty PD/KV-save hooks. Only architecture maps to DeepseekVLForCausalLM. Bad prompt token id: add_request returns None with an info log.
- 2026-10-21 (1b-ii facts): block size fixed at 128 (model_metadata_utils.py:133-135). ca_cache + ica_cache share one uint8 paged buffer; swa_cache is NOT paged (per-sequence ring of 134 tokens in the state buffer); state slots have a second BlockManager. 1 KV head, one 512-value entry per token (528 B fp8 / 288 B fp4), so the classic 2*heads*head_dim formula does not apply. Preemption picks the running seq with the MOST output tokens (comment at scheduler.hpp:557 says "shortest"). EngineArgs default = stop preempted request; offline LLM sets recompute.
- 2026-10-21 (1b-iii facts): tokenization in LLM._add_request (llm.py:156); BOS 0, EOS 1, vocab 129280. Model forward returns hidden states; sampler computes fp32 logits only for sampled rows. After prefill the draft list holds 5 placeholder ids, so a decode step sends 6 tokens. RequestOutput pool of 10000, released at next pre_sampler_sync.
- 2026-10-21 (1b-iv facts): bool env parsing treats only 0/empty/false/False as false (`=off` turns ON); empty int raises ValueError. 6 vars read at import time; SchedulerConfig reads prefill-interval vars as default args (rearm cannot fix). ZOS and multimodal pool default off in environ.py but EngineArgs turns them on. C++ reads DEEPINFER_USE_NEXTN_DECODE with getenv. examples/README.md:63 says extra experts default 32; code default 0.
- FACT-CHECK FOCUS: Tour 1 claims (derived, not run) that with a VL model the first prefill waits for the multimodal worker, and with the default attempt interval 70 the first prefill runs in step 71. Must be checked hard in 1c.
- TODO: CJK font missing in the headless browser (Chinese shows as boxes in screenshots only); shared pw/svgshot.sh writes a fixed wrap.html (race).
- TODO after 1b (supervisor, tooling): move page-local <style> blocks (home .sm-*, .paths; code tree .ct-*) to site.css; build.py does not rebuild a diagram after a script edit (needed --force-diagrams); concurrent builds delete site/ (race for screenshots); add module-page template to STYLE.md §4.3; decide level+quiz on module pages (yes); home image may be blank in screenshots due to loading=lazy — verify.
- Open (for user review): Inter font is not loaded (system fallback, no external stylesheet). Prism loads from cdnjs.
- 2026-10-21: The survey said `tilelang_ops/__init__.py` is the kernel dispatcher. That is wrong: the file is empty. The dispatcher is `tilelang_ops/ops.py`. Lesson: the survey is a guide only. Phase 2 fact sheets must check each claim in the code.
- 2026-10-21: User asked "Is it AFD?". Answer: no. One deployment uses one hardware type. Add an FAQ entry and a section on the hardware page (see the chat answer).

## Subagent log

| Date | Task | Result |
|---|---|---|
| 2026-10-21 | Survey DeepInfer codebase | Done. Report used for `plan.md`. |
| 2026-10-21 | Phase 1a: foundation (build.py, CSS/JS, svglib, STYLE.md, sample page "NVIDIA and Ascend") | Done. Build 0 errors. Playwright works with a workaround (scripts in scratchpad/pw/). Supervisor checked screenshots: good. |
| 2026-10-21 | Phase 1b (i): home page, clickable map, code-map tree, module page llm_engine.py | Done. 0 errors. Map = HTML/CSS grid (no JS). nav/code.json has 49 modules. Module-page template proposed (add to STYLE.md §4.3). |
| 2026-10-21 | Phase 1b (ii): basics "The KV cache", KV allocator viz, interactive-visual support in build.py | Done. New tags <x-viz>, <x-img>, front-matter `scripts:`. 20 basics glossary terms. Simulator copies DeepInfer's real allocation and preemption rules. |
| 2026-10-21 | Phase 1b (iii): Tour 1 "Life of a request" | Done. 13 stops (KV stop moved after forward), 4 diagrams, 18 glossary terms. No stepper viz yet (Phase 4). |
| 2026-10-21 | Phase 1b (iv): reference "Environment variables" | Done. 59 vars in 16 groups, generator tools/gen_env_vars.py (--check, --report). |
| 2026-10-21 | Restyle: light article look (user feedback) | Done. Always light (dark only by toggle), Inter 18px/1.7, 720px column, figures up to 1100px, version line on every page + footer. Supervisor checked screenshots: good. |
| 2026-10-21 | 1c Fact-check A: Tour 1, llm-engine module page, home | Running |
| 2026-10-21 | 1c Fact-check B: KV cache, platforms, env vars, folder tree | Running |
