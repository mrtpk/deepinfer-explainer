"""Diagram: the two block managers and one worked example of allocate / append / free.

Used by: src/concepts/paged-kv-cache.html
Sources (commit 9bd9cf2):
  deepinfer/engine/llm_engine.py:265-266          one BlockManager for KV blocks, one for state slots
  deepinfer/worker/cache_engine.py:201-202        state slots = int(max_num_seqs * 1.2) + 1
  csrc/engine/block_manager.hpp:27-35             entry 0 is never given out; free list 1..n-1
  csrc/engine/block_manager.hpp:82-103            allocate pops the head; free pushes to the tail at ref_count 0
  csrc/engine/block_manager.hpp:128-136           can_allocate: NEVER / OK / LATER
  csrc/engine/block_manager.hpp:147-149           free_blocks frees the table in reverse order
  csrc/engine/scheduler.hpp:194-201               block check + state check
  csrc/engine/scheduler.hpp:817-828               _append_slot adds one block when get_num_blocks grows
  csrc/engine/scheduler.hpp:830-835               cache usage counts block 0 as used
  csrc/engine/sequence.hpp:291-293                get_num_blocks = ceil((len + inflight + drafts) / 128)
Toy pool: 10 KV blocks and max_num_seqs 4 (5 state slots). Request sizes are made up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, BORDER, GRAY_MID, INK, MUTE, NEUTRAL, PINK, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Two block managers, one worked example",
    "Toy pool: 10 KV blocks of 128 tokens, 5 state slots  ·  entry 0 of each pool is never used  ·  sizes are made up",
    params="A: prompt 300 tokens   B: prompt 1000 tokens   nextn 5   ZOS on (6 in-flight tokens)",
)

CELL = 34
GAP = 3


def strip(x, y, n, owner, label_idx=True):
    """owner: dict index -> colour tuple; index 0 is reserved."""
    for i in range(n):
        cx = x + i * (CELL + GAP)
        if i == 0:
            d.rect(cx, y, CELL, CELL, fill=BORDER, stroke=GRAY_MID, rx=3, sw=1.2)
        elif i in owner:
            col = owner[i]
            d.rect(cx, y, CELL, CELL, fill=col[1], stroke=col[0], rx=3, sw=1.6)
        else:
            d.rect(cx, y, CELL, CELL, fill=WHITE, stroke=GRAY_MID, rx=3, sw=1.0)
        if label_idx:
            d.text(cx + CELL / 2, y + CELL / 2 + 4.5, str(i), 12, INK if i in owner or i == 0 else MUTE,
                   "bold" if i in owner else "normal", "middle", mono=True)
    return x + n * (CELL + GAP)


# ============================================================================
# Panel 1: the two pools
# ============================================================================
y0 = 112
P1_H = 196
d.panel(y0, P1_H, 1, "Two pools, two managers",
        "The KV pool is paged: many blocks per sequence. The state pool gives each sequence exactly one slot.")
d.text(46, y0 + 84, "KV BlockManager", 13.5, INK, "bold")
d.text(46, y0 + 102, "num_gpu_blocks = 10", 12, MUTE, mono=True)
x_end = strip(250, y0 + 74, 10, {1: BLUE, 2: BLUE, 3: BLUE})
d.text(x_end + 14, y0 + 86, "A: block_table = [1, 2, 3]", 12, BLUE[0], "bold", mono=True)
d.text(x_end + 14, y0 + 103, "blocks 4-9 are free", 12, MUTE, mono=True)

d.text(46, y0 + 146, "state BlockManager", 13.5, INK, "bold")
d.text(46, y0 + 164, "int(4 × 1.2) + 1 = 5", 12, MUTE, mono=True)
x_end2 = strip(250, y0 + 136, 5, {1: BLUE})
d.text(x_end2 + 14, y0 + 148, "A: state_id = 1", 12, BLUE[0], "bold", mono=True)
d.text(x_end2 + 14, y0 + 165, "SWA ring + compression state", 12, MUTE)

# ============================================================================
# Panel 2: the timeline
# ============================================================================
y1 = y0 + P1_H + 20
ROW = 64
events = [
    ("1  start", "the free list holds 1 to 9 in order", {}, "free: 1 2 3 4 5 6 7 8 9"),
    ("2  A prefill: allocate_seq", "ceil(300 / 128) = 3 blocks, from the head", {1: BLUE, 2: BLUE, 3: BLUE},
     "free: 4 5 6 7 8 9"),
    ("3  B waits: LATER", "B needs ceil(1000 / 128) = 8; only 6 are free", {1: BLUE, 2: BLUE, 3: BLUE},
     "free: 4 5 6 7 8 9"),
    ("4  A decode: _append_slot", "len 380 + 6 in flight + 5 drafts = 391 > 384", {1: BLUE, 2: BLUE, 3: BLUE, 4: BLUE},
     "free: 5 6 7 8 9"),
    ("5  A ends: free in reverse", "4, 3, 2, 1 go to the TAIL of the list", {},
     "free: 5 6 7 8 9 4 3 2 1"),
    ("6  B prefill: allocate_seq", "8 blocks from the head; usage is now 9 / 10 = 0.9", {5: PINK, 6: PINK, 7: PINK, 8: PINK,
                                                                                 9: PINK, 4: PINK, 3: PINK, 2: PINK},
     "free: 1"),
]
P2_H = 66 + len(events) * ROW + 6
d.panel(y1, P2_H, 2, "One run, step by step",
        "allocate takes blocks from the head of the free list; free puts them at the tail. Block ids do not stay in order.")
for i, (title, sub, owner, free) in enumerate(events):
    yy = y1 + 70 + i * ROW
    d.text(46, yy + 14, title, 13, INK, "bold")
    d.text(46, yy + 33, sub, 12, MUTE)
    strip(420, yy, 10, owner)
    d.text(800, yy + 22, free, 12, INK, mono=True)
d.text(800, y1 + 70 + 5 * ROW + 48, "B: [5, 6, 7, 8, 9, 4, 3, 2]", 12, PINK[0], "bold", mono=True)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "sequence A"), (PINK, "sequence B"), (NEUTRAL, "entry 0: never used"),
                 ((GRAY_MID, WHITE, WHITE), "free")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: one data-parallel rank; no forked sequences, so every reference count is 0 or 1.",
    "After step 6 a new prefill is still allowed: the rule is usage <= 0.9, and block 0 counts as used.",
    "State slots follow the same rules: A frees slot 1 in step 5, slot 1 goes to the tail, and B gets slot 2.",
])
d.save(height=y + 14)
