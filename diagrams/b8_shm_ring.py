"""Diagram: the shared-memory ring buffer of MessageQueue (layout, flag states, enqueue path).

Used by: src/code/shm-broadcast.html
Sources (commit 9bd9cf2):
  deepinfer/distributed/shm_broadcast.py:41-98    layout: data chunks then metadata; written flag + reader flags
  deepinfer/distributed/shm_broadcast.py:320-357  acquire_write: wait until written and all read; reset readers, then set written
  deepinfer/distributed/shm_broadcast.py:359-387  acquire_read: wait until written and not read by me; set my flag
  deepinfer/distributed/shm_broadcast.py:389-422  enqueue / dequeue: pickle, overflow byte, ZeroMQ for large objects
  deepinfer/model_executor/parallel_utils/parallel_state.py:123-124   1 << 20 bytes, 10 chunks
Example: CP group of 4 ranks -> 1 writer (cp_rank 0), 3 readers.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "MessageQueue: one writer, many readers, one shared buffer",
    "deepinfer/distributed/shm_broadcast.py  ·  example: CP group of 4 ranks = 1 writer + 3 readers  ·  commit 9bd9cf2",
    params="max_chunk_bytes = 1 << 20 (1 MiB)   max_chunks = 10   metadata = 1 + n_reader = 4 bytes per chunk",
)

# ---------------------------------------------------------------------------
# Panel 1: memory layout
# ---------------------------------------------------------------------------
y0 = 112
P1_H = 220
d.panel(y0, P1_H, 1, "What is in the shared memory?",
        "10 data chunks, then 10 small flag rows. Total (1 MiB + 4 B) x 10 = 10,485,800 bytes.")
by = y0 + 76
x = 46
CW = 76
for i in range(10):
    col = BLUE
    d.rect(x + i * (CW + 2), by, CW, 46, fill=col[1], stroke=col, rx=3, sw=1.2)
    d.text(x + i * (CW + 2) + CW / 2, by + 20, f"chunk {i}", 11.5, col[0], "bold", "middle", mono=True)
    d.text(x + i * (CW + 2) + CW / 2, by + 36, "1 MiB", 11, INK, anchor="middle", mono=True)
mx = x + 10 * (CW + 2) + 10
MW = 18
for i in range(10):
    d.rect(mx + i * (MW + 1), by, MW, 46, fill=VIOLET[1], stroke=VIOLET, rx=2, sw=1)
d.text(mx + 5 * (MW + 1), by + 64, "10 x 4 B", 11.5, VIOLET[0], "bold", "middle", mono=True)
d.text(x, by + 66, "data_offset = 0", 12, INK, mono=True)
d.text(mx - 10, by + 66, "metadata_offset = max_chunk_bytes x max_chunks ->", 12, INK, anchor="end", mono=True)
# one data chunk detail
dy = by + 84
d.rect(46, dy, 210, 30, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.2)
d.text(56, dy + 20, "byte 0: overflow flag", 12, AMBER[0], "bold", mono=True)
d.rect(258, dy, 420, 30, fill=BLUE[1], stroke=BLUE, rx=3, sw=1.2)
d.text(268, dy + 20, "bytes 1..: pickled object (if it fits)", 12, BLUE[0], "bold", mono=True)
d.rect(700, dy, 354, 30, fill=VIOLET[1], stroke=VIOLET, rx=3, sw=1.2)
d.text(710, dy + 20, "flags: [written, r0, r1, r2]", 12, VIOLET[0], "bold", mono=True)

# ---------------------------------------------------------------------------
# Panel 2: the flag states of one chunk
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
states = [
    ("0 ? ? ?", "not written", "write: yes   read: no", NEUTRAL),
    ("1 0 0 0", "just written", "write: no   read: yes", EMERALD),
    ("1 1 0 1", "read by r0, r2", "r1 may read; write: no", EMERALD),
    ("1 1 1 1", "read by all", "write: yes   read: no", NEUTRAL),
]
SW, SH, SG = 236, 92, 21
P2_H = 72 + SH + 92
d.panel(y1, P2_H, 2, "When may the writer and a reader use a chunk?",
        "Readers only set their own flag 0 -> 1. The writer resets the reader flags first, then sets written = 1.")
sy = y1 + 72
for i, (flags, name, rule, col) in enumerate(states):
    sx = 46 + i * (SW + SG)
    d.rect(sx, sy, SW, SH, fill=col[1], stroke=col, sw=1.5)
    d.text(sx + 14, sy + 26, flags, 17, INK, "bold", mono=True)
    d.text(sx + 14, sy + 50, name, 13, INK, "bold")
    d.text(sx + 14, sy + 72, rule, 12, INK, mono=True)
    if i < 3:
        d.arrow(sx + SW, sy + SH / 2, sx + SW + SG - 2, sy + SH / 2, INK)
d.path_arrow(f"M {46 + 3 * (SW + SG) + SW / 2:.1f},{sy + SH:.1f} L {46 + 3 * (SW + SG) + SW / 2:.1f},{sy + SH + 30:.1f} "
             f"L {46 + SW / 2:.1f},{sy + SH + 30:.1f} L {46 + SW / 2:.1f},{sy + SH + 2:.1f}", VIOLET, dash="5 4")
d.text(560, sy + SH + 52, "writer: written = 0, write data, readers = 0, written = 1, current_idx = (idx + 1) % 10",
       12, VIOLET[0], "bold", "middle", mono=True)

# ---------------------------------------------------------------------------
# Panel 3: enqueue path
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
CARD_H = 50
CARD_GAP = 12
steps = [
    ("enqueue(obj) on cp_rank 0", "pickle.dumps(obj, HIGHEST_PROTOCOL) -> n bytes", "line 392", BLUE),
    ("acquire_write: spin until chunk idx is free", "os.sched_yield(); debug log every 60 s; optional timeout", "lines 320-357", VIOLET),
    ("n < 1 MiB: byte 0 = 0, bytes 1..n = data", "else byte 0 = 1, and the data goes over a ZeroMQ PUB socket", "lines 396-402", AMBER),
    ("dequeue() on each follower", "acquire_read on its own idx; pickle.loads; set own flag", "lines 406-422", EMERALD),
]
P3_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y2, P3_H, 3, "What happens for one object?",
        "Small objects travel in shared memory. Large ones use the chunk only as a ticket.")
cy = y2 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    d.pill_auto(1054 - 10 - (len(cite) * 11 * 0.602 + 20), cy + 8, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "data"), (VIOLET, "flags / writer"), (AMBER, "overflow path"), (EMERALD, "readable chunk"),
                 (NEUTRAL, "writable chunk")])
y += 38
y = d.footnotes(30, y, [
    "Line numbers refer to shm_broadcast.py. Remote readers (another host) use only the ZeroMQ socket; the CP group has none.",
    "Simplified: the flag bytes are plain memory; the code relies on the write order shown in panel 2 (lines 80-85).",
])
d.save(height=y + 10)
