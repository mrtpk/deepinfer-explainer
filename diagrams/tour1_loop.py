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
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram, text_width  # noqa: E402

d = Diagram(width=1100)
W = d.W
R = W - 46  # right edge of the panel content
d.header(
    "The step loop: one prefill step, then many decode steps",
    "Request \"1\" alone, counted from its first prefill step, ZOS on, nextn 5  ·  all counts are illustrative  ·  commit 9bd9cf2",
    params="prompt 41 tokens   max_tokens 128   decode step: 1 token + 5 drafts = seqlen_q 6",
)


def wrap(s, size, maxw, mono=False, indent="  "):
    """Break s at spaces so that each line is at most maxw wide."""
    out, cur = [], ""
    for w in s.split(" "):
        cand = w if not cur else cur + " " + w
        if cur and text_width(cand, size, mono) > maxw:
            out.append(cur)
            cur = indent + w
        else:
            cur = cand
    out.append(cur)
    return out


# ============================================================================
# Panel 1: steps that touch the request (one row per step, time runs down)
# ============================================================================
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
BOX_H, ROW_GAP, DOTS_H = 40, 14, 24
y0 = 112
by = y0 + 96
rows_h = sum((DOTS_H if s[0] == "..." else BOX_H) + ROW_GAP for s in steps) - ROW_GAP
P1_H = by - y0 + rows_h + 22
d.panel(y0, P1_H, 1, "Which engine steps touch request \"1\"?",
        "step() runs again and again. A decode step returns the tokens of the step before it (ZOS).")
sx, sw = 46, 430          # step column
rx, rw = 566, R - 566     # "what step() returns" column
d.text(sx, by - 12, "forward + sample on the device", 12.5, MUTE, "bold")
d.text(rx, by - 12, "what step() returns to LLM._run_engine()  (one RequestOutput per token)", 12.5, MUTE, "bold")
yy = by
prev_bottom = None
for i, (name, kind, qk, ret, toks, col) in enumerate(steps):
    if name == "...":
        d.text(sx + sw / 2, yy + 18, "...", 22, MUTE, "bold", "middle")
        if prev_bottom is not None:
            d.arrow(sx + sw / 2, prev_bottom, sx + sw / 2, yy - 2, MUTE, sw=1.4)
        prev_bottom = yy + DOTS_H
        yy += DOTS_H + ROW_GAP
        continue
    if prev_bottom is not None:
        d.arrow(sx + sw / 2, prev_bottom, sx + sw / 2, yy - 2, MUTE, sw=1.4)
    d.rect(sx, yy, sw, BOX_H, fill=col[1], stroke=col, sw=1.4)
    d.text(sx + 14, yy + 25, name, 14, INK, "bold")
    d.text(sx + 120, yy + 25, kind, 13, col, "bold")
    if qk:
        d.text(sx + 270, yy + 25, qk, 13, INK, mono=True)
    # what step() returns
    if name == "flush":
        rcol, label, value = AMBER, "last in-flight step", "then break"
    else:
        rcol = col
        label = ("result of " + ret) if ret not in ("-", "#1") else ("result of step 1" if ret == "#1" else "no output")
        value = toks
    d.rect(rx, yy, rw, BOX_H, fill="#ffffff", stroke=rcol, sw=1.2, dash="4 3")
    d.text(rx + 14, yy + 25, label, 12, MUTE)
    d.text(rx + 190, yy + 25, value, 13, INK, "bold", mono=True)
    d.arrow(sx + sw, yy + BOX_H / 2, rx - 2, yy + BOX_H / 2, rcol, sw=1.4, dash="5 4")
    prev_bottom = yy + BOX_H
    yy += BOX_H + ROW_GAP

# ============================================================================
# Panel 2: ZOS overlap
# ============================================================================
y1 = y0 + P1_H + 20
cpu_y, dev_y = y1 + 92, y1 + 196
P2_H = dev_y + 52 + 24 - y1
d.panel(y1, P2_H, 2, "Why one step behind? The CPU post-processes step N-1 while the device runs forward N",
        "Worker.execute_model_step(): launch forward N, post-process N-1, launch sample N, keep N for the next step.")
lx = 46
d.text(lx, cpu_y + 26, "CPU", 15, INK, "bold")
d.text(lx, cpu_y + 44, "driver thread", 12, MUTE)
d.text(lx, dev_y + 26, "device", 15, INK, "bold")
d.text(lx, dev_y + 44, "one stream", 12, MUTE)
x0 = 150
# CPU row (labels may take two lines)
cpu_boxes = [
    (x0, 130, ["schedule N", "+ prepare N"], BLUE),
    (x0 + 136, 78, ["launch", "fwd N"], BLUE),
    (x0 + 220, 206, ["post-process N-1 (outputs)"], VIOLET),
    (x0 + 432, 86, ["launch", "sample N"], BLUE),
    (x0 + 524, 130, ["schedule N+1", "+ prepare"], BLUE),
    (x0 + 660, 86, ["launch", "fwd N+1"], BLUE),
    (x0 + 752, 146, ["post-process N"], VIOLET),
]


def label_box(x, y, w, lines, col):
    d.rect(x, y, w, 52, fill=col[1], stroke=col, sw=1.3)
    if len(lines) == 1:
        d.text(x + 10, y + 31, lines[0], 12.5, INK, "bold")
    else:
        d.text(x + 10, y + 22, lines[0], 12.5, INK, "bold")
        d.text(x + 10, y + 40, lines[1], 12.5, INK, "bold")


for x, w, lines, col in cpu_boxes:
    label_box(x, cpu_y, w, lines, col)
dev_boxes = [
    (x0 + 140, 376, ["forward N  (CUDA graph replay)"], EMERALD),
    (x0 + 524, 106, ["sample N"], EMERALD),
    (x0 + 752, 146, ["forward N+1"], EMERALD),
]
for x, w, lines, col in dev_boxes:
    label_box(x, dev_y, w, lines, col)
# launch arrows
lf = x0 + 136 + 39
d.arrow(lf, cpu_y + 52, lf, dev_y - 2, EMERALD, sw=1.5)
mid = (cpu_y + 52 + dev_y) / 2
for sx_, tx_ in ((x0 + 432 + 43, x0 + 524 + 53), (x0 + 660 + 43, x0 + 752 + 73)):
    d.path_arrow(f"M {sx_:.1f},{cpu_y + 52:.1f} L {sx_:.1f},{mid:.1f} L {tx_:.1f},{mid:.1f} L {tx_:.1f},{dev_y - 2:.1f}", EMERALD, sw=1.5)
d.text(x0 + 432 + 43 - 10, mid + 4, "queued on the stream", 11.5, EMERALD, anchor="end")
d.text(x0 + 220, y1 + 80, "overlaps with forward N", 12, VIOLET, "bold")
d.aside(x0 + 220 + 160, y1 + 80, ["(waits only on sample_end_evt of N-1)"])

# ============================================================================
# Panel 3: one decode step
# ============================================================================
y2 = y1 + P2_H + 20
cw, cg = 128, 10
cx0 = 190
rows_y = [y2 + 80, y2 + 146, y2 + 212]
oy = rows_y[2] + 44 + 34          # outcome box top
OUT_H = 116
P3_H = oy + OUT_H + 22 - y2
d.panel(y2, P3_H, 3, "One decode step: 6 tokens in, 1 to 6 tokens out",
        "Input: the last token plus 5 drafts. The sampler accepts a prefix of the drafts and adds one token of its own.")
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
# outcome box, below the cells
ox, ow = cx0, 6 * cw + 5 * cg
d.rect(ox, oy, ow, OUT_H, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(ox + 16, oy + 26, "process_outputs() appends 3 tokens", 14, VIOLET, "bold")
out_lines = [
    "d1, d2, then y (sampled at the d2 row)",
    "len 50 -> 53;  KV num_tokens 49 -> 52",
    "KV of d3 (position 52) is not counted",
    "3 RequestOutputs; the last one has",
    "draft_tok 6, accept_tok 3",
    "then 5 new drafts for the next step",
]
for i, s in enumerate(out_lines):
    col_x = ox + 16 if i < 3 else ox + ow / 2 + 16
    d.text(col_x, oy + 52 + (i % 3) * 20, s, 13, INK, mono=True)
ax = cx0 + (cw + cg) + cw / 2      # below the "verify d2" cell: y is sampled there
d.arrow(ax, rows_y[2] + 44, ax, oy - 2, VIOLET, sw=1.6)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "CPU work / the real last token"), (EMERALD, "device work / accepted"),
                 (VIOLET, "post-process"), (AMBER, "draft token / flush"), (PINK, "rejected draft")])
y += 38
notes = [
    "Illustrative: the numbers of accepted drafts, m, and the positions are examples. The first decode step after prefill has placeholder drafts (id vocab_size - 1).",
    "Not shown: the empty decode steps before step 1. The model class of this release has a vision part, so the request becomes schedulable only after the multimodal worker answers (see stop 5).",
    "Simplified: with DEEPINFER_ENABLE_MTP_VARLEN=1 the scheduler can verify fewer than 5 drafts (seqlen_q between 1 and 6).",
]
y = d.footnotes(30, y, [ln for s in notes for ln in wrap(s, 12, W - 70)])
d.save(height=y + 10)
