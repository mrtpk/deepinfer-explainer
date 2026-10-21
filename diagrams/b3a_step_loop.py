"""Diagram: the offline step loop (LLM.generate -> _run_engine -> step()), and what each call returns.

Used by: src/concepts/engine-step-loop.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:129-142       generate(): one _add_request per prompt, then _run_engine
  deepinfer/entrypoints/llm.py:168-195       _run_engine(): step() while unfinished, else flush; clone; sort by id
  deepinfer/engine/llm_engine.py:665-679     has_unfinished_requests(): all-reduce MAX over the DP group
  deepinfer/engine/llm_engine.py:860-959     step(): schedule, clone/zero, checks, multimodal fetch, execute
  deepinfer/worker/worker.py:113-189         forward N, post-process N-1, sample N, post-process N now or later
  deepinfer/worker/worker.py:274-283         flush_inflight_reqs(): post-process the kept step
  csrc/engine/scheduler.hpp:752-763          free_finished_seqs() at the next decode schedule
  csrc/engine/scheduler.hpp:905-915          process_outputs skips a sequence that is already finished
Panel 3 is a worked example derived from these lines (not a run): ZOS on, no draft accepted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "The offline step loop and what each call returns",
    "LLM.generate() adds every request, then calls step() until no request is left  ·  ZOS on (the default)  ·  commit 9bd9cf2",
    params="step() -> np.ndarray[np.uint64]  (handles of RequestOutput objects, valid until the next step)",
)

# ============================================================================
# Panel 1: the loop
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "What does LLM.generate() do?",
        "It adds all prompts first, then runs a loop of engine steps. The loop ends with one flush.")

bx, bw, bh = 46, 300, 78
r1 = y0 + 74
d.box(bx, r1, bw, bh, "LLM.generate(prompts)", ["for each prompt: _add_request()", "tokenize -> add_request()", "llm.py:129-142"], col=BLUE)
d.box(400, r1, bw, bh, "has_unfinished_requests()", ["queues not empty, or SO pending", "all-reduce MAX over DP ranks", "llm_engine.py:665-679"], col=VIOLET)
d.box(754, r1, bw, bh, "LLMEngine.step()", ["schedule one batch, run it", "returns RequestOutput handles", "llm_engine.py:860-959"], col=VIOLET)
d.arrow(bx + bw, r1 + bh / 2, 398, r1 + bh / 2, BLUE)
d.arrow(700, r1 + bh / 2, 752, r1 + bh / 2, VIOLET)
d.arrow_label(726, r1 + bh / 2, "yes", VIOLET)

r2 = r1 + bh + 52
d.box(754, r2, bw, 64, "clone each output", ["RequestOutput.clone(ptr)", "llm.py:179-184"], col=BLUE)
d.arrow(904, r1 + bh, 904, r2 - 2, VIOLET)
# loop back from clone to has_unfinished
d.path_arrow(f"M 754,{r2 + 32} L 640,{r2 + 32} L 640,{r1 + bh + 2}", BLUE)
d.text(650, r2 + 24, "loop", 11.5, BLUE, "bold")

d.box(400, r2, 210, 64, "flush_inflight_reqs()", ["last kept ZOS step", "llm.py:178"], col=AMBER)
d.path_arrow(f"M 470,{r1 + bh} L 470,{r2 - 2}", VIOLET)
d.text(478, r1 + bh + 28, "no", 11.5, VIOLET, "bold")
d.box(bx, r2, bw, 64, "return results", ["sort by int(request_id)", "decode text if decode_sequence"], col=BLUE)
d.arrow(400, r2 + 32, bx + bw + 2, r2 + 32, AMBER)
d.arrow_label(373, r2 + 32, "break", AMBER)

# ============================================================================
# Panel 2: one step, in order
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 236
d.panel(y1, P2_H, 2, "What happens inside one step()?",
        "The engine schedules on the CPU; the Worker runs the device work and calls back into the engine.")
cw, ch = 316, 140
cy = y1 + 72
cards = [
    (46, "1  LLMEngine (CPU)", VIOLET, ["Scheduler.schedule(pool)", " -> seq_metadata_list,", "    scheduler_outputs", "clone / zero (if asked)", "SO check · multimodal fetch()"]),
    (392, "2  Worker.execute_model_step", EMERALD, ["forward step N", "post-process step N-1", "sample step N", "pre_sampler_sync() callback", "worker.py:113-189"]),
    (738, "3  post-process (callback)", VIOLET, ["process_MTPInfo", "scheduler.process_outputs", "build_request_outputs", "prefill / ZOS off: step N now", "ZOS decode: step N later"]),
]
for x, title, col, lines in cards:
    d.rect(x, cy, cw, ch, fill=col[1], stroke=col, sw=1.4)
    d.rect(x, cy, 6, ch, fill=col[0], stroke=None, rx=3)
    d.text(x + 18, cy + 22, title, 13.5, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 18, cy + 44 + i * 18, s, 12, INK, mono=True)
d.arrow(46 + cw, cy + ch / 2, 390, cy + ch / 2, VIOLET)
d.arrow(392 + cw, cy + ch / 2, 736, cy + ch / 2, EMERALD)

# ============================================================================
# Panel 3: what each call returns (worked example)
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 404
d.panel(y2, P3_H, 3, "What does each call return?",
        "Two requests: A (max_tokens 3) and B (max_tokens 4). With ZOS, a decode step returns the tokens of the step before it.")
calls = [
    ("step 1", "prefill A, B", "A1, B1", VIOLET, "a prefill step post-processes at once"),
    ("step 2", "decode A, B", "(none)", VIOLET, "nothing kept yet; keeps step 2"),
    ("step 3", "decode A, B", "A2, B2", VIOLET, "tokens of step 2"),
    ("step 4", "decode A, B", "A3 (length), B3", VIOLET, "tokens of step 3; A is finished"),
    ("step 5", "decode B", "B4 (length)", VIOLET, "A left running; its step-4 token is dropped"),
    ("step 6", "empty decode", "(none)", MUTE, "B left running; its step-5 token is dropped"),
    ("flush", "flush_inflight_reqs()", "(none)", AMBER, "post-processes step 6, then break"),
]
gx, gy = 46, y2 + 86
rw, rh, rgap = W - 92, 30, 6
cols = [(gx + 16, "call"), (gx + 130, "batch scheduled in this call"), (gx + 400, "returned handles"), (gx + 640, "why")]
for cx, label in cols:
    d.text(cx, gy - 6, label, 11.5, MUTE, "bold")
for j, (name, batch, ret, col, note) in enumerate(calls):
    ry = gy + j * (rh + rgap)
    c = col if isinstance(col, tuple) else (col, WHITE, WHITE)
    d.rect(gx, ry, rw, rh, fill=c[1], stroke=c, sw=1.3, dash="5 4" if name in ("step 6", "flush") else None)
    d.rect(gx, ry, 6, rh, fill=c[0], stroke=None, rx=3)
    d.text(cols[0][0], ry + 20, name, 13, c[0], "bold")
    d.text(cols[1][0], ry + 20, batch, 12.5, INK, mono=True)
    d.text(cols[2][0], ry + 20, ret, 12.5, INK, "bold", mono=True)
    d.text(cols[3][0], ry + 20, note, 12, MUTE)
ty = gy + len(calls) * (rh + rgap) + 18
d.text(gx, ty, "One row = one call in LLM._run_engine. Step 6 runs because B still counts in running when the loop tests it.", 12, MUTE)
d.text(gx, ty + 18, "Derived from the code, not from a run. With accepted drafts, one call returns more than one output per request.", 12, MUTE)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "LLM (llm.py)"), (VIOLET, "LLMEngine and its C++ calls"), (EMERALD, "Worker, device work"), (AMBER, "end of the loop")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: data-parallel ranks (every rank runs the same number of steps), structured-output pumping, statistics.",
    "Prefill steps post-process at once (worker.py:183-185). Only ZOS decode steps keep their state for the next call.",
])
d.save(height=y + 14)
