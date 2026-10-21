"""Diagram: the free list inside Blocks: a doubly linked list stored in a std::vector.

Used by: src/code/block-manager-hpp.html
Sources (commit 9bd9cf2):
  csrc/engine/block_manager.hpp:27-35     constructor: links 1..n-1, head 1, tail n-1, size n-1
  csrc/engine/block_manager.hpp:39-52     _push_back: append at the tail
  csrc/engine/block_manager.hpp:54-71     _erase: unlink, set prev = next = 0
  csrc/engine/block_manager.hpp:82-86     allocate: pop the head, ref_count += 1
  csrc/engine/block_manager.hpp:88-93     pin_block: ref_count += 1 (block must be in use)
  csrc/engine/block_manager.hpp:95-103    free: ref_count -= 1; push back at 0
Toy size: Blocks(6), so entries 1..5 are usable.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, BORDER, EMERALD, GRAY_MID, INK, MUTE, NEUTRAL, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "The free list: a linked list inside a vector",
    "Blocks(6): one entry {ref_count, next, prev} per block  ·  0 means \"none\", so block 0 is never used",
    params="allocate() = pop head, ref_count+1    free(i) = ref_count-1, push to tail at 0    pin_block(i) = ref_count+1",
)

CW, CH, GAP = 108, 74, 10
X0 = 300


def entries(y, rows, hl=()):
    """rows: list of 6 tuples (ref_count, next, prev) or None for entry 0."""
    for i, r in enumerate(rows):
        x = X0 + i * (CW + GAP)
        if r is None:
            d.rect(x, y, CW, CH, fill=BORDER, stroke=GRAY_MID, rx=6, sw=1.2)
            d.text(x + CW / 2, y + 20, "[0]", 12.5, INK, "bold", "middle", mono=True)
            d.text(x + CW / 2, y + 44, "not used", 11.5, MUTE, anchor="middle")
            continue
        rc, nx, pv = r
        used = rc > 0
        col = AMBER if used else EMERALD
        sw = 2.4 if i in hl else 1.4
        d.rect(x, y, CW, CH, fill=col[1], stroke=col[0], rx=6, sw=sw)
        d.text(x + CW / 2, y + 18, f"[{i}]", 12.5, col[0], "bold", "middle", mono=True)
        d.text(x + 12, y + 38, f"rc   {rc}", 12, INK, mono=True)
        d.text(x + 12, y + 53, f"next {nx}", 12, INK if not used else MUTE, mono=True)
        d.text(x + 12, y + 68, f"prev {pv}", 12, INK if not used else MUTE, mono=True)


def state(y, num, title, sub, rows, order, hl=()):
    d.badge(46, y + 14, num, BLUE, r=11, size=12)
    d.text(66, y + 19, title, 13.5, INK, "bold")
    for k, s in enumerate(sub):
        d.text(66, y + 39 + k * 17, s, 12, MUTE)
    entries(y, rows, hl)
    d.text(X0, y + CH + 20, order, 12, INK, mono=True)


y0 = 112
P1_H = 412
d.panel(y0, P1_H, 1, "Allocate and free",
        "Used blocks (amber) are out of the list; their next and prev are 0. Free blocks (green) form the list.")
state(y0 + 64, 1, "Blocks(6)", ["constructor,", "lines 28-34"],
      [None, (0, 2, 0), (0, 3, 1), (0, 4, 2), (0, 5, 3), (0, 0, 4)],
      "head 1   tail 5   size 5     list: 1 -> 2 -> 3 -> 4 -> 5")
state(y0 + 180, 2, "allocate() x 2", ["takes 1, then 2", "from the head"],
      [None, (1, 0, 0), (1, 0, 0), (0, 4, 0), (0, 5, 3), (0, 0, 4)],
      "head 3   tail 5   size 3     list: 3 -> 4 -> 5", hl=(1, 2))
state(y0 + 296, 3, "free(1)", ["rc 1 -> 0: block 1", "goes to the tail"],
      [None, (0, 0, 5), (1, 0, 0), (0, 4, 0), (0, 5, 3), (0, 1, 4)],
      "head 3   tail 1   size 4     list: 3 -> 4 -> 5 -> 1", hl=(1, 5))

y1 = y0 + P1_H + 20
P2_H = 160
d.panel(y1, P2_H, 2, "Reference counts: a shared block",
        "pin_block adds an owner. free removes one. The block goes back to the list only at rc 0.")
steps = [
    ("pin_block(2)", "rc 1 -> 2", "a fork shares block 2", AMBER),
    ("free(2)", "rc 2 -> 1", "still in use: not in the list", AMBER),
    ("free(2)", "rc 1 -> 0", "push to tail: 3 -> 4 -> 5 -> 1 -> 2", EMERALD),
]
for i, (call, rc, note, col) in enumerate(steps):
    x = 46 + i * 342
    d.box(x, y1 + 70, 320, 70, call, [rc, note], col=col, mono_size=12)
    if i < 2:
        d.arrow(x + 322, y1 + 105, x + 340, y1 + 105, INK)

y = y1 + P2_H + 24
d.legend(30, y, [(EMERALD, "free: in the list"), (AMBER, "in use: rc > 0"), (NEUTRAL, "entry 0: the \"none\" value")])
y += 40
y = d.footnotes(30, y, [
    "A thick border marks the entries that the step changed. rc = ref_count.",
    "Every call checks its index: 0 < i < n. pin_block on a free block and free below rc 0 raise errors (lines 89-99).",
])
d.save(height=y + 14)
