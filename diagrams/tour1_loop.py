"""Diagram: the step loop for one request (illustrative timeline), ZOS overlap, and one decode step.

Used by: src/tours/life-of-a-request.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:168-186           _run_engine(): step() until no unfinished request, then flush
  deepinfer/worker/worker.py:113-189             forward N, post-process N-1, sample N, defer post-process (ZOS)
  deepinfer/engine/llm_engine.py:706-713         prefill gives no drafts: placeholder drafts (vocab_size - 1)
  deepinfer/model_executor/layers/mtp_info_pool.py:9-11   placeholder draft id = vocab_size - 1
  csrc/engine/mtp_varlen.hpp:150-158             seqlen_q = 1 + number of drafts (no perf curve)
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:88-121  positions and input_ids of a decode step
  csrc/engine/scheduler.hpp:927-1000             optimistic advance, accepted drafts, commit_processed_tokens
  csrc/engine/outputs.hpp:199-294                one RequestOutput per emitted token; draft_tok / accept_tok
All token counts and acceptance results are illustrative.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram()
d.header(
    "The step loop: one prefill step, then many decode steps",
    "Request \"1\" alone, counted from its first prefill step, ZOS on, nextn 5  ·  all counts are illustrative  ·  commit 9bd9cf2",
    params="prompt 41 tokens   max_tokens 128   decode step: 1 token + 5 drafts = seqlen_q 6",
)

# ============================================================================
# Panel 1: steps that touch the request
# ============================================================================
y0 = 112
P1_H = 316
d.panel(y0, P1_H, 1, "Which engine steps touch request \"1\"?",
        "step() runs again and again. A decode step returns the tokens of the step before it (ZOS).")
steps = [
    ("step 1", "prefill", "q 41  k 41", "#1", "1 token", BLUE),
    ("step 2", "decode D1", "q 6  k 47", "-", "nothing yet", EMERALD),
    ("step 3", "decode D2", "q 6", "D1", "#2", EMERALD),
    ("step 4", "decode D3", "q 6", "D2", "#3-#6", EMERALD),
    ("...", "", "", "", "", NEUTRAL),
    ("step m+1", "decode", "q 6", "Dm", "... #128 end", EMERALD),
    ("step m+2", "free blocks", "D(m+1) dropped", "-", "nothing", NEUTRAL),
    ("flush", "flush_inflight", "", "", "", AMBER),
]
bx0, bw, gap = 46, 160, 18
by = y0 + 90
d.text(46, by - 12, "forward + sample on the device", 12.5, MUTE, "bold")
for i, (name, kind, qk, ret, toks, col) in enumerate(steps):
    x = bx0 + i * (bw + gap)
    if name == "...":
        d.text(x + bw / 2, by + 44, "...", 22, MUTE, "bold", "middle")
        continue
    d.rect(x, by, bw, 76, fill=col[1], stroke=col, sw=1.4)
    d.text(x + 12, by + 22, name, 14, INK, "bold")
    d.text(x + 12, by + 43, kind, 13, col, "bold")
    d.text(x + 12, by + 63, qk, 13, INK, mono=True)
    if i + 1 < len(steps):
        d.arrow(x + bw, by + 38, x + bw + gap - 2, by + 38, MUTE, sw=1.4)
ry = by + 76 + 46
d.text(46, ry + 48 + 22, "what step() returns to LLM._run_engine()  (one RequestOutput per token)", 12.5, MUTE, "bold")
for i, (name, kind, qk, ret, toks, col) in enumerate(steps):
    x = bx0 + i * (bw + gap)
    if name in ("...", "flush"):
        continue
    d.rect(x, ry, bw, 48, fill="#ffffff", stroke=col, sw=1.2, dash="4 3")
    d.text(x + 12, ry + 20, ("result of " + ret) if ret not in ("-", "#1") else ("result of step 1" if ret == "#1" else "no output"), 12, MUTE)
    d.text(x + 12, ry + 39, toks, 13, INK, "bold", mono=True)
    d.arrow(x + bw / 2, by + 76, x + bw / 2, ry - 2, col, sw=1.4, dash="5 4")
fx = bx0 + 7 * (bw + gap)
d.rect(fx, ry, bw, 48, fill="#ffffff", stroke=AMBER, sw=1.2, dash="4 3")
d.text(fx + 12, ry + 20, "last in-flight step", 12, MUTE)
d.text(fx + 12, ry + 39, "then break", 13, INK, "bold", mono=True)
d.arrow(fx + bw / 2, by + 76, fx + bw / 2, ry - 2, AMBER, sw=1.4, dash="5 4")

# ============================================================================
# Panel 2: ZOS overlap
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 282
d.panel(y1, P2_H, 2, "Why one step behind? The CPU post-processes step N-1 while the device runs forward N",
        "Worker.execute_model_step(): launch forward N, post-process N-1, launch sample N, keep N for the next step.")
lx = 46
cpu_y, dev_y = y1 + 92, y1 + 178
d.text(lx, cpu_y + 26, "CPU", 15, INK, "bold")
d.text(lx, cpu_y + 44, "driver thread", 12, MUTE)
d.text(lx, dev_y + 26, "device", 15, INK, "bold")
d.text(lx, dev_y + 44, "one stream", 12, MUTE)
x0 = 170
# CPU row: step N
cpu_boxes = [
    (x0, 190, "schedule N + prepare N", BLUE),
    (x0 + 196, 110, "launch fwd N", BLUE),
    (x0 + 312, 300, "post-process N-1 (outputs)", VIOLET),
    (x0 + 618, 120, "launch sample N", BLUE),
    (x0 + 744, 190, "schedule N+1 + prepare", BLUE),
    (x0 + 940, 120, "launch fwd N+1", BLUE),
    (x0 + 1066, 210, "post-process N", VIOLET),
]
for x, w, label, col in cpu_boxes:
    d.rect(x, cpu_y, w, 52, fill=col[1], stroke=col, sw=1.3)
    d.text(x + 10, cpu_y + 31, label, 12.5, INK, "bold")
dev_boxes = [
    (x0 + 200, 536, "forward N  (CUDA graph replay)", EMERALD),
    (x0 + 744, 150, "sample N", EMERALD),
    (x0 + 1066, 210, "forward N+1", EMERALD),
]
for x, w, label, col in dev_boxes:
    d.rect(x, dev_y, w, 52, fill=col[1], stroke=col, sw=1.3)
    d.text(x + 10, dev_y + 31, label, 12.5, INK, "bold")
# launch arrows
d.arrow(x0 + 196 + 55, cpu_y + 52, x0 + 196 + 55, dev_y - 2, EMERALD, sw=1.5)
mid = (cpu_y + 52 + dev_y) / 2
for sx_, tx_ in ((x0 + 618 + 60, x0 + 744 + 75), (x0 + 940 + 60, x0 + 1066 + 105)):
    d.path_arrow(f"M {sx_:.1f},{cpu_y + 52:.1f} L {sx_:.1f},{mid:.1f} L {tx_:.1f},{mid:.1f} L {tx_:.1f},{dev_y - 2:.1f}", EMERALD, sw=1.5)
d.text(x0 + 744 + 75 + 8, mid - 6, "queued on the stream", 11.5, EMERALD)
d.text(x0 + 312, y1 + 80, "overlaps with forward N", 12, VIOLET, "bold")
d.aside(x0 + 312 + 190, y1 + 80, ["(waits only on sample_end_evt of N-1)"])

# ============================================================================
# Panel 3: one decode step
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 330
d.panel(y2, P3_H, 3, "One decode step: 6 tokens in, 1 to 6 tokens out",
        "Input: the last token plus 5 drafts. The sampler accepts a prefix of the drafts and adds one token of its own.")
cw, cg = 120, 10
cx0 = 260
rows_y = [y2 + 92, y2 + 158, y2 + 224]
labels = ["position", "input_ids", "result"]
for j, lab in enumerate(labels):
    d.text(46, rows_y[j] + 30, lab, 14, INK, "bold")
d.text(46, rows_y[0] + 48, "(seqlen_k = 55)", 12, MUTE)
cells_in = ["x49  (last)", "d1  draft", "d2  draft", "d3  draft", "d4  draft", "d5  draft"]
results = [("verify d1", "accept", EMERALD), ("verify d2", "accept", EMERALD), ("verify d3", "reject", PINK),
           ("", "unused", NEUTRAL), ("", "unused", NEUTRAL), ("", "unused", NEUTRAL)]
for k in range(6):
    x = cx0 + k * (cw + cg)
    d.rect(x, rows_y[0], cw, 44, fill="#ffffff", stroke=MUTE, sw=1)
    d.text(x + cw / 2, rows_y[0] + 28, str(49 + k), 14, INK, "bold", "middle", mono=True)
    col = BLUE if k == 0 else AMBER
    d.rect(x, rows_y[1], cw, 44, fill=col[1], stroke=col, sw=1.3)
    d.text(x + cw / 2, rows_y[1] + 28, cells_in[k], 13, INK, anchor="middle", mono=True)
    top, word, rc = results[k]
    d.rect(x, rows_y[2], cw, 44, fill=rc[1], stroke=rc, sw=1.3)
    if top:
        d.text(x + cw / 2, rows_y[2] + 18, top, 11.5, MUTE, anchor="middle")
    d.text(x + cw / 2, rows_y[2] + 36 if top else rows_y[2] + 28, word, 13, rc, "bold", "middle", mono=True)
# outcome box
ox = cx0 + 6 * (cw + cg) + 30
ow = 1454 - ox
d.rect(ox, rows_y[0], ow, 176, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(ox + 16, rows_y[0] + 26, "process_outputs() appends 3 tokens", 14, VIOLET, "bold")
out_lines = [
    "d1, d2, then y (sampled at the d2 row)",
    "len 50 -> 53;  KV num_tokens 49 -> 52",
    "KV of d3 (position 52) is not counted",
    "3 RequestOutputs; the last one has",
    "draft_tok 6, accept_tok 3",
    "then 5 new drafts for the next step",
]
for i, s in enumerate(out_lines):
    d.text(ox + 16, rows_y[0] + 52 + i * 20, s, 13, INK, mono=True)
d.arrow(ox - 28, rows_y[2] + 22, ox - 2, rows_y[2] + 22, VIOLET, sw=1.6)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "CPU work / the real last token"), (EMERALD, "device work / accepted"),
                 (VIOLET, "post-process"), (AMBER, "draft token / flush"), (PINK, "rejected draft")])
y += 38
y = d.footnotes(30, y, [
    "Illustrative: the numbers of accepted drafts, m, and the positions are examples. The first decode step after prefill has placeholder drafts (id vocab_size - 1).",
    "Not shown: the empty decode steps before step 1. The model class of this release has a vision part, so the request becomes schedulable only after the multimodal worker answers (see stop 5).",
    "Simplified: with DEEPINFER_ENABLE_MTP_VARLEN=1 the scheduler can verify fewer than 5 drafts (seqlen_q between 1 and 6).",
])
d.save(height=y + 10)
