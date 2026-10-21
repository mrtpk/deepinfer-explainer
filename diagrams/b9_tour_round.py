"""Diagram: one speculative decoding round for request "1" (tour spec-decode-round).

Used by: src/tours/spec-decode-round.html ("The picture")
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:697                    seqlen_k = num_tokens + inflight + seqlen_q
  deepinfer/model_executor/layers/sampler.py:225-251   _verification, then DFlash decode_forward
  deepinfer/model_executor/layers/tilelang_ops/get_kv_index.py:166-174  draft positions = accepted_pos + 1 ..
  csrc/engine/scheduler.hpp:955-999                accepted ids, append, commit_processed_tokens
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:98-107   SWA ring slot = state_id * 134 + pos % 134
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:78-91    compressed entry only where (pos + 1) % n == 0
  deepinfer/model_executor/models/mtp/dflash.py:204-209           DFlash main keys of rejected drafts are overwritten
  deepinfer/model_executor/layers/sampler.py:366-376              SO matcher tries the drafts, then rolls back
Token ids and confidences are illustrative.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, GRAY_MID, INK, LINE, MUTE, NEUTRAL, PINK, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
_box = d.box
d.box = lambda *a, **k: _box(*a, mono_size=12, **k)
W = d.W

d.header(
    "One speculative decoding round for request \"1\"",
    "Step N verifies d1…d5 and drafts e1…e5  ·  step N+1 verifies the new drafts  ·  values are illustrative",
    params="before step N: len 50, num_tokens 49   ·   after: len 53, num_tokens 52   ·   MTP pool slot 2",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 232
d.panel(y0, P1, 1, "What does the device do in step N? Forward, verify, then draft",
        "One forward pass on 6 tokens. The sampler keeps d1 and d2, rejects d3, and DFlash drafts from there.")
by = y0 + 72
bw, bh = 300, 132
xs = [46, 400, 754]
d.box(xs[0], by, bw, bh, "1. Forward (main model)", [
    "inputs  t  d1 d2 d3 d4 d5", "positions 49 … 54", "writes KV for 49 … 54", "writes DFlash main keys", "for 49 … 54",
    "hidden states: 6 rows"], col=BLUE)
d.box(xs[1], by, bw, bh, "2. Verification (sampler)", [
    "row 0: d1 accept", "row 1: d2 accept", "row 2: d3 reject → r", "rows 3-5: not used", "last_valid_offset = 2",
    "tokens out: d1 d2 r"], col=EMERALD)
d.box(xs[2], by, bw, bh, "3. DFlash drafts", [
    "accepted_pos = 49 + 2 = 51", "block: r + 4 noise tokens", "positions 52 … 56", "drafts e1 … e5 (53 … 57)",
    "confidences c1 … c5", "→ MTP pool slot 2"], col=PINK)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, BLUE)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, EMERALD)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
rows = [
    ("KV count (num_tokens)", "49 → 52: commit_processed_tokens(3) counts only kept tokens", "scheduler.hpp:999"),
    ("SWA ring, 134 slots", "slots of 52-54 hold rejected keys; step N+1 writes 52 … 57 over them", "v4.cpp:98-107"),
    ("Compressed KV", "an entry at a rejected position is written again for the real token", "v4.cpp:78-91"),
    ("DFlash cache", "main keys of 52-54 are overwritten by the draft keys of 52-56, in step N", "dflash.py:204-209"),
    ("MTP info pool slot 2", "d1 … d5 replaced by e1 … e5 (same slot)", "dflash.py:339-344"),
    ("SO grammar matcher", "tries the drafts to build masks, then rolls back", "sampler.py:366-376"),
]
P2 = 84 + len(rows) * 34 + 10
d.panel(y1, P2, 2, "What happens to the rejected d3, d4, d5? Nothing is copied back",
        "Every store is indexed by position. The next step writes the same positions again.")
ry = y1 + 74
d.text(46, ry, "object", 12.5, MUTE, "bold")
d.text(270, ry, "what happens", 12.5, MUTE, "bold")
d.text(880, ry, "source", 12.5, MUTE, "bold")
for i, (a, b, c) in enumerate(rows):
    yy = ry + 12 + i * 34
    d.rect(40, yy, 1020, 30, fill=WHITE if i % 2 else "#f3f4f6", stroke=None, rx=4)
    d.text(46, yy + 20, a, 13, TEAL[0], "bold")
    d.text(270, yy + 20, b, 12.5, INK)
    d.text(880, yy + 20, c, 12, MUTE, mono=True)

# ---------------------------------------------------------------- panel 3
y2 = y1 + P2 + 20
P3 = 226
d.panel(y2, P3, 3, "How long is the check in step N+1? 6 tokens, or fewer with DSpark",
        "Without DSpark the request sends r and all 5 drafts. With DSpark the confidences can cut the list.")
cy = y2 + 76
conf = [0.92, 0.80, 0.60, 0.30, 0.20]
cum, r = [], 1.0
for c in conf:
    r *= c
    cum.append(r)
d.text(46, cy + 22, "confidence", 12.5, MUTE, "bold")
d.text(46, cy + 56, "running product", 12.5, MUTE, "bold")
for j in range(5):
    x = 190 + j * 120
    d.text(x + 50, cy + 22, f"c{j + 1} {conf[j]:.2f}", 12.5, INK, anchor="middle", mono=True)
    d.rect(x, cy + 36, 100, 30, fill=EMERALD[1] if j < 3 else WHITE, stroke=EMERALD[0] if j < 3 else LINE, rx=6,
           sw=1.3, dash=None if j < 3 else "4 3")
    d.text(x + 50, cy + 56, f"{cum[j]:.3f}", 13, EMERALD[0] if j < 3 else INK, "bold", "middle", mono=True)
d.aside(800, cy + 22, ["Example: the batch budget", "keeps 3 drafts of this request."])

iy = cy + 96
d.text(46, iy + 20, "without DSpark", 13, INK, "bold")
d.text(190, iy + 20, "seqlen_q 6:  r(52) e1(53) e2(54) e3(55) e4(56) e5(57)", 13, BLUE[0], "bold", mono=True)
d.text(46, iy + 50, "with DSpark", 13, INK, "bold")
d.text(190, iy + 50, "seqlen_q 4:  r(52) e1(53) e2(54) e3(55)", 13, EMERALD[0], "bold", mono=True)

y = y2 + P3 + 24
d.legend(30, y, [(BLUE, "main model"), (EMERALD, "accepted / verified"), (PINK, "draft model"), (TEAL, "stored state")])
y += 36
y = d.footnotes(30, y, [
    "v4.cpp = csrc/engine/input_metadata/prepare_tensor_input_v4.cpp. 134 = 128 + 6 with default settings.",
    "The DSpark length comes from all requests of the batch together (concepts/dspark); the cut at 3 drafts is an example.",
])
d.save(height=y + 10)
