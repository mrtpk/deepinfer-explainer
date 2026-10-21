"""Diagram: how the C++ scheduler of a NORMAL engine chooses a prefill step or a decode step.

Used by: src/concepts/scheduler.html
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:80              GPU_CACHE_PREFILL_WATERMARK = 0.9
  csrc/engine/scheduler.hpp:273             _has_prefill_waiting(): front of waiting is schedulable
  csrc/engine/scheduler.hpp:295-341         attempt points, vote 1 (ALL/ANY), _schedule_prefill, vote 2
  csrc/engine/scheduler.hpp:169-182         _dp_allreduce (also with one DP rank)
  csrc/engine/scheduler.hpp:676-681         prefill step: decode_step = 0; decode step: decode_step += 1
  deepinfer/environ.py:174-178              DEEPINFER_PREFILL_ATTEMPT_INTERVAL = 70, ..._ANY_... = 100
  csrc/engine/scheduler.hpp:288-294         PROMPT engine: always prefill; COMPLETION engine: always decode
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Prefill step or decode step?",
    "Scheduler::_schedule for a NORMAL engine  ·  every DP rank runs the same votes in the same step  ·  commit 9bd9cf2",
    params="ALL interval 70   ANY interval 100   watermark 0.9   (defaults)",
)

# ============================================================================
# Panel 1: the decision
# ============================================================================
y0 = 112
cards = [
    ("Is decode_step an attempt point?", ["ALL point: decode_step % 70 == 0", "ANY point: decode_step != 0 and % 100 == 0"], "308-311", BLUE, "no"),
    ("Does this rank want a prefill?", ["want = cache usage <= 0.9 and waiting.front()", "   is schedulable (want = false still votes)"], "273, 313", BLUE, None),
    ("Vote 1: all-reduce MIN over the DP group", ["ALL point: prefill if EVERY rank wants", "ANY point: prefill if ONE rank wants"], "315-322", VIOLET, "no"),
    ("_schedule_prefill(), only if want", ["fills a prefill batch from waiting", "can come back empty (blocks, slots)"], "323-326", AMBER, None),
    ("Vote 2: did ANY rank schedule a prefill?", ["all-reduce MIN of (outputs ? 0 : 1)", "all ranks empty -> decode"], "328-335", VIOLET, "no"),
    ("Prefill step", ["this rank has a batch: return it", "else: an empty prefill step (placeholder)"], "336-340", AMBER, None),
]
ch, cg = 66, 18
P1_H = 70 + len(cards) * (ch + cg) + 6
d.panel(y0, P1_H, 1, "How does one step become prefill or decode?",
        "A prefill is tried only at an attempt point. Two votes keep the step type the same on every DP rank.")
cx, cw = 46, 640
lx, lw = 760, 294
top = y0 + 70
# decode lane on the right
lane_h = 5 * (ch + cg) - cg
d.rect(lx, top, lw, lane_h, fill=TEAL[1], stroke=TEAL, sw=1.5)
d.text(lx + lw / 2, top + 30, "Decode step", 15, TEAL[0], "bold", "middle")
for i, s in enumerate(["_schedule_decode()", "the running sequences", "1 + drafts tokens each", "scheduler.hpp:559-660", "", "then decode_step += 1"]):
    d.text(lx + lw / 2, top + 58 + i * 20, s, 12.5, INK, anchor="middle", mono=True)
for i, (title, lines, src, col, exit_) in enumerate(cards):
    y = top + i * (ch + cg)
    d.rect(cx, y, cw, ch, fill=col[1], stroke=col, sw=1.4)
    d.rect(cx, y, 6, ch, fill=col[0], stroke=None, rx=3)
    d.badge(cx + 24, y + 18, i + 1, col, r=10, size=11)
    d.text(cx + 42, y + 23, title, 13.5, INK, "bold")
    d.text(cx + cw - 10, y + 22, src, 12, MUTE, anchor="end", mono=True)
    for j, s in enumerate(lines):
        d.text(cx + 42, y + 42 + j * 16, s, 12, INK, mono=True)
    if i < len(cards) - 1:
        d.arrow(cx + 80, y + ch, cx + 80, y + ch + cg - 2, col)
        d.text(cx + 90, y + ch + 13, "yes" if exit_ else "", 11.5, col[0], "bold")
    if exit_:
        d.arrow(cx + cw, y + ch / 2, lx - 2, y + ch / 2, TEAL)
        d.arrow_label((cx + cw + lx) / 2, y + ch / 2, "no", TEAL)
# want=false path
d.text(lx, top + 5 * (ch + cg) + 24, "After a prefill step:", 12.5, AMBER[0], "bold")
d.text(lx, top + 5 * (ch + cg) + 44, "decode_step = 0", 12.5, INK, mono=True)

# ============================================================================
# Panel 2: attempt points over time
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 250
d.panel(y1, P2_H, 2, "When are the attempt points?",
        "decode_step counts decode steps since the last prefill step. Defaults: ALL every 70, ANY every 100.")
ax0, ax1 = 70, W - 150
ay = y1 + 128
maxv = 210
d.line(ax0, ay, ax1, ay, col=INK, sw=1.5)
def X(v):
    return ax0 + (ax1 - ax0) * v / maxv
for v in range(0, maxv + 1, 10):
    d.line(X(v), ay - 4, X(v), ay + 4, col=MUTE, sw=1)
d.text(ax1 + 14, ay + 4, "decode_step", 12, MUTE, mono=True)
for v in (0, 70, 140, 210):
    d.rect(X(v) - 7, ay - 30, 14, 14, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.4)
    d.text(X(v), ay - 38, "ALL " + str(v), 12, AMBER[0], "bold", "middle", mono=True)
for v in (100, 200):
    d.rect(X(v) - 7, ay + 16, 14, 14, fill=VIOLET[1], stroke=VIOLET, rx=3, sw=1.4)
    d.text(X(v), ay + 46, "ANY " + str(v), 12, VIOLET[0], "bold", "middle", mono=True)
for v in (50, 150):
    d.text(X(v), ay + 22, str(v), 11.5, MUTE, anchor="middle", mono=True)
d.text(46, ay + 74, "decode_step 0 is an ALL point, so right after a prefill step the scheduler tries again: prefill steps come back to back", 12, INK)
d.text(46, ay + 92, "while every rank has work. With one DP rank, up to 69 more decode steps can run after a request becomes schedulable (if blocks and slots are free).", 12, INK)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "local test"), (VIOLET, "DP vote, ANY point"), (AMBER, "prefill, ALL point"), (TEAL, "decode")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: a PROMPT engine always runs _schedule_prefill; a COMPLETION engine always runs _schedule_decode (scheduler.hpp:288-294).",
    "With one DP rank the votes still run as all-reduce calls on a group of size 1 (scheduler.hpp:169-182).",
])
d.save(height=y + 14)
