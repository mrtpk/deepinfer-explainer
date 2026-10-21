"""Diagram: how the scheduler fills a prefill batch and a decode batch (worked example with real sizes).

Used by: src/concepts/scheduler.html
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:360-546    _schedule_prefill: queue order, limits, chunk, side effects
  csrc/engine/scheduler.hpp:470-475    chunk = rest of the token budget (rounded to cp_align)
  csrc/engine/scheduler.hpp:518-520    blocks for the whole prompt at the first chunk
  csrc/engine/scheduler.hpp:543-545    a chunk is the last sequence of a NORMAL prefill batch
  csrc/engine/scheduler.hpp:940-1020   after the step: full prefill -> running; chunk -> front of waiting
  csrc/engine/scheduler.hpp:622-645    _schedule_decode: sort by output length, serve from the end, preempt the front
  csrc/engine/sequence.hpp:291-293     get_num_blocks = ceil((len + inflight + drafts) / block_size)
Settings of examples/offline_inference.py:52-56 and examples/_config.py:120 (chunked prefill on):
max_num_batched_tokens 32768, max_num_seqs 4, block size 128. Request sizes are made up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, SERIES, TEAL, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "How the scheduler fills one batch",
    "Worked example with the offline example settings  ·  all requests already schedulable  ·  sizes are made up",
    params="token budget 32768   max_num_seqs 4   block 128 tokens   chunked_prefill on   nextn 5",
)

COL = {"full": BLUE[0], "chunk": AMBER[0]}

def bar(y, segs, total, x0=46, x1=None, h=34):
    x1 = x1 or (W - 46)
    d.rect(x0, y, x1 - x0, h, fill=WHITE, stroke=INK, rx=4, sw=1.2)
    x = x0
    for name, n, label in segs:
        w = (x1 - x0) * n / total
        col = BLUE if name == "full" else AMBER
        d.rect(x, y, w, h, fill=col[1], stroke=col, rx=0, sw=1.2)
        if w > 40:
            d.text(x + w / 2, y + 23, label, 12, INK, "bold", "middle", mono=True)
        x += w
    return x

# ============================================================================
# Panel 1: prefill step 1
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "Prefill step 1: who gets into the batch?",
        "The scheduler takes requests from the front of waiting until the budget, the blocks or max_num_seqs stop it.")
d.text(46, y0 + 80, "waiting before:  A 41   B 20000   C 15000   D 300   E 50   (prompt tokens)", 12.5, INK, mono=True)
bar(y0 + 96, [("full", 41, ""), ("full", 20000, "B 20000"), ("chunk", 12727, "C chunk 12727")], 32768)
d.text(46, y0 + 150, "A 41 at the left edge (too thin to label)  ·  sum = 32768 = the token budget", 11.5, MUTE, italic=True)
rows = [
    ("A", "41 tokens fit", "1 block", "RUNNING after the step"),
    ("B", "20000 fit (32727 left)", "157 blocks", "RUNNING after the step"),
    ("C", "15000 > 12727 left: chunk", "118 blocks (whole prompt)", "back to the FRONT of waiting"),
    ("D, E", "not looked at", "-", "a chunk ends the batch (543-545)"),
]
for i, (n, a, b, c) in enumerate(rows):
    yy = y0 + 180 + i * 22
    d.text(46, yy, n, 12.5, INK, "bold", mono=True)
    d.text(110, yy, a, 12, INK, mono=True)
    d.text(420, yy, b, 12, INK, mono=True)
    d.text(680, yy, c, 12, INK)
d.text(46, y0 + 282, "waiting after:  C (2273 left)   D 300   E 50        running: A, B (1 output token each)", 12.5, INK, mono=True)

# ============================================================================
# Panel 2: prefill step 2
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 170
d.panel(y1, P2_H, 2, "Prefill step 2: decode_step is 0 again, so the scheduler tries again",
        "C finishes its prompt, D fits, E must wait: A, B, C and D now fill max_num_seqs = 4.")
bar(y1 + 70, [("chunk", 2273, "C 2273"), ("full", 300, "")], 32768)
d.text(46, y1 + 126, "C 2273 + D 300 = 2573 of 32768 tokens. Step 3 tries again, finds no room for E (4 slots used), and the second vote makes it a decode step.", 12, INK)
d.text(46, y1 + 146, "E waits for a free slot AND an attempt point: decode_step 70 (ALL) or 100 (ANY).", 12, INK)

# ============================================================================
# Panel 3: a decode step that preempts
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 300
d.panel(y2, P3_H, 3, "A decode step with no free block: who is preempted?",
        "running is sorted by output length, most first. The loop serves from the END and preempts from the FRONT.")
hdr = y2 + 80
cols = [(46, "running[i]"), (150, "sequence"), (290, "output tokens"), (450, "what the loop does"), (850, "order")]
for x, t in cols:
    d.text(x, hdr, t, 11.5, MUTE, "bold")
lines = [
    ("0", "B", "900", "preempted first: no free block, 4 left in the loop", "1st", PINK),
    ("1", "A", "300", "served: _append_slot, 6 query tokens", "4th", EMERALD),
    ("2", "D", "120", "served", "3rd", EMERALD),
    ("3", "C", "40", "served first (end of the list)", "2nd", EMERALD),
]
for i, (idx, name, out, act, order, col) in enumerate(lines):
    yy = hdr + 14 + i * 36
    d.rect(46, yy, W - 92, 28, fill=col[1], stroke=col, sw=1.2)
    d.text(60, yy + 19, idx, 12.5, INK, mono=True)
    d.text(150, yy + 19, name, 13, INK, "bold", mono=True)
    d.text(290, yy + 19, out, 12.5, INK, mono=True)
    d.text(450, yy + 19, act, 12, INK)
    d.text(850, yy + 19, order, 12.5, col[0], "bold", mono=True)
fy = hdr + 14 + 4 * 36 + 18
d.text(46, fy, "Order of events: the loop takes C (end); no block is free, so it preempts B (front). Then C, D, A get their slot.", 12, INK)
d.text(46, fy + 18, "B frees about 164 blocks. LLM default: B goes to the front of waiting and is recomputed; EngineArgs default: B stops.", 12, INK)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "whole prompt in one step"), (AMBER, "prefill chunk"), (EMERALD, "decode: served"), (PINK, "decode: preempted")])
y += 36
y = d.footnotes(30, y, [
    "Blocks: ceil(41/128) = 1, ceil(20000/128) = 157, ceil(15000/128) = 118 (sequence.hpp:291-293; no drafts before the first decode).",
    "Each decode sequence sends 1 + 5 drafts = 6 query tokens (mtp_varlen.hpp:153-157). Panel 3 is a later step with other lengths.",
])
d.save(height=y + 14)
