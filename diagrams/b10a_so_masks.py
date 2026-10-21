"""Diagram: one decode step of structured output with 5 drafts: masks per draft row, then rollback.

Used by: src/concepts/structured-outputs.html ("In the code", step 4)
Sources (commit 9bd9cf2):
  deepinfer/model_executor/layers/sampler.py:352-376   accept committed tokens, fill mask 0, accept drafts, fill mask k+1, rollback
  deepinfer/model_executor/layers/sampler.py:323-327   bitmasks_cpu: max_MTP_value + 1 pinned masks [n, ceil(V/32)] int32
  deepinfer/model_executor/layers/sampler.py:391-407   copy on so_copy_stream, so_mask_ready event
  deepinfer/model_executor/layers/sampler.py:433-437   apply_token_bitmask_by_step_inplace per step
  deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py:39-57   row = ftp[r] + step; bit 0 -> -inf
  deepinfer/structure_output/matcher.py:20             MAX_ROLLBACK_TOKENS = nextn + 2
Example tokens are invented (a JSON grammar after '{"color": ').
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, GRAY_MID, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W

d.header(
    "Structured outputs with drafts: one mask per draft row",
    "The CPU walks the matcher through the drafts, saves a mask after each one, then rolls the matcher back",
    params="nextn = 5  ·  masks: 6 × [num_seqs, ceil(V/32)] int32  ·  example: grammar wants a colour string",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 470
d.panel(y0, P1, 1, "What does the CPU do for one request? Accept, fill, try drafts, roll back",
        "Each mask k is the set of tokens that the grammar allows at draft row k. It is filled before the device samples.")

cx, cw, chh = 46, 612, 58
rows = [
    (1, "accept last step's tokens  (status 2)", BLUE, "matcher.accept_token(t) for t in accepted + [output]", "sampler.py:352-355"),
    (2, "fill mask 0  →  row 0", EMERALD, "state after  {\"color\": \"  → allows  red, green, blue (or a prefix)", "sampler.py:361-364"),
    (3, "accept d1 = red  →  fill mask 1  →  row 1", EMERALD, "allows  \"  only", "sampler.py:367-373"),
    (4, "accept d2 = \"  →  fill mask 2  →  row 2", EMERALD, "allows  ,  for example (the next legal JSON tokens)", "sampler.py:367-373"),
    (5, "d3 = !  is rejected by the grammar  →  stop", PINK, "rows 3, 4, 5 get no mask", "sampler.py:374-375"),
    (6, "rollback(2)", VIOLET, "matcher is back at the state of card 1", "sampler.py:376"),
]
yy = y0 + 70
for n, title, col, detail, cite in rows:
    d.step_card(cx, yy, cw, chh, n, title, col, rows=[(">", detail)], key_w=16)
    d.text(cx + cw - 10, yy + 22, cite, 11.5, MUTE, anchor="end", mono=True)
    yy += chh + 10

# right column: what is stored
rx = 690
d.box(rx, y0 + 70, 364, 122, "Stored on the CPU (pinned)", [
    "bitmasks_cpu[k]  k = 0 .. 5", "[num_seqs, ceil(V / 32)] int32", "bit j of word w = token 32w + j", "so_indices[k]: request rows", "sampler.py:323-329"],
    col=BLUE, align="start")
d.box(rx, y0 + 212, 364, 106, "Example for this request", [
    "mask 0, 1, 2 filled", "so_indices[0..2] contain it", "so_indices[3..5] do not", "drafts left unchecked: d4, d5"],
    col=EMERALD, align="start")
d.box(rx, y0 + 338, 364, 70, "Rollback depth", [
    "at most nextn = 5 drafts", "matcher history keeps nextn + 2 = 7"], col=VIOLET, align="start")

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 222
d.panel(y1, P2, 2, "What does the device do? Copy, wait, and set disallowed logits to −inf",
        "A side stream copies the masks. One TileLang kernel per step k changes row ftp[r] + k of each listed request.")

bw, bh = 300, 104
by = y1 + 74
d.box(46, by, bw, bh, "copy on so_copy_stream", [
    "pinned masks → device", "event so_mask_ready", "main stream waits for it", "sampler.py:391-407, 163-164"], col=BLUE)
d.box(400, by, bw, bh, "apply mask k (k = 0..5)", [
    "grid: ceil(V/8192) × requests", "row = ftp[r] + k", "bit = 0 → logit = −inf", "structure_output.py:39-57"], col=AMBER)
d.box(754, by, bw, bh, "verify and sample", [
    "row 2 checks d3 = !", "masked: q(!) = 0", "→ d3 rejected, resample", "from allowed tokens only"], col=EMERALD)
d.arrow(46 + bw, by + bh / 2, 398, by + bh / 2, BLUE)
d.arrow(400 + bw, by + bh / 2, 752, by + bh / 2, AMBER)

y = y1 + P2 + 22
d.legend(30, y, [(BLUE, "data movement"), (EMERALD, "mask filled / used"), (PINK, "grammar rejects"),
                 (VIOLET, "matcher state"), (AMBER, "device kernel")])
y += 36
y = d.footnotes(30, y, [
    "Simplified: tokens are shown as text; the matcher works on token ids. Row k of a request checks draft k + 1.",
    "The draft model does not see the grammar: an illegal draft is caught only at verification (masked logit = −inf).",
])
d.save(height=y + 10)
