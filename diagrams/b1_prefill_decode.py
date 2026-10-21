"""Diagram: prefill vs decode, and why they stress the hardware in different ways.

Used by: src/learn/prefill-decode.html (section "The picture")
Sources (commit 9bd9cf2):
  csrc/engine/prepare_sample.cpp:61        "Mixed prefill and decode batches are unsupported."
  csrc/engine/prepare_sample.cpp:197-198   prefill: sample only the last token row of each sequence
  csrc/engine/mtp_varlen.hpp:153-157       decode: each sequence sends 1 + its draft tokens
  deepinfer/environ.py:129                 DEEPINFER_USE_NEXTN_DECODE default 5 (so up to 6 tokens)
  deepinfer/worker/model_runner.py:182     CUDA graphs only in decode steps
Token counts in panels 1-2 are a toy example.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("Prefill and decode",
         "Toy request: a prompt of 6 tokens  ·  one layer's KV cache shown  ·  no draft tokens in panels 1-2")

prompt = ["BOS", "The", "cat", "sat", "on", "the"]
cw, ch, gap = 56, 28, 5


def chips(x, y, toks, col, hl_last=False):
    for i, t in enumerate(toks):
        c = EMERALD if (hl_last and i == len(toks) - 1) else col
        d.rect(x, y, cw, ch, fill=c[1], stroke=c, rx=5, sw=1.2)
        d.text(x + cw / 2, y + 19, t, 12, INK, anchor="middle", mono=True)
        x += cw + gap
    return x


# ---- panel 1: prefill --------------------------------------------------------------
y0 = 92
P1 = 196
d.panel(y0, P1, 1, "What does a prefill step do?",
        "All prompt tokens go through the model at once. The step fills the KV cache and samples the first new token.")
ry = y0 + 82
d.text(46, ry - 6, "input: 6 tokens in one step", 12.5, MUTE)
x = chips(46, ry + 4, prompt, BLUE)
d.arrow(x + 6, ry + 18, x + 52, ry + 18, INK)
d.box(x + 56, ry - 10, 200, 56, "Model", ["6 rows at once"], col=VIOLET, tsize=14, mono_size=12.5)
mx = x + 56 + 200
d.arrow(mx, ry + 18, mx + 40, ry + 18, INK)
d.rect(mx + 44, ry + 4, cw, ch, fill=WHITE, stroke=EMERALD, rx=5, sw=2)
d.text(mx + 44 + cw / 2, ry + 23, "mat", 12, EMERALD[0], "bold", anchor="middle", mono=True)
ky = ry + 62
d.text(46, ky + 19, "KV cache", 12.5, AMBER[0], "bold")
for i in range(6):
    d.rect(130 + i * 30, ky, 26, 26, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.2)
d.text(130 + 6 * 30 + 10, ky + 19, "6 entries written in this step", 12.5, MUTE)

# ---- panel 2: decode -----------------------------------------------------------------
y1 = y0 + P1 + 20
steps = [("mat", 7, "."), (".", 8, "EOS")]
P2 = 78 + len(steps) * 48 + 30
d.panel(y1, P2, 2, "What does a decode step do?",
        "Each step sends only the newest token. It reads all cache entries and adds one.")
for k, (tin, n, tout) in enumerate(steps):
    yy = y1 + 76 + k * 48
    d.text(46, yy + 19, f"step {k + 2}", 12.5, MUTE, "bold", mono=True)
    d.rect(120, yy, cw, ch, fill=EMERALD[1], stroke=EMERALD, rx=5, sw=1.2)
    d.text(120 + cw / 2, yy + 19, tin, 12, INK, anchor="middle", mono=True)
    d.arrow(182, yy + 14, 214, yy + 14, INK)
    for i in range(n):
        new = i == n - 1
        d.rect(220 + i * 30, yy + 1, 26, 26, fill=AMBER[0] if new else AMBER[1], stroke=AMBER, rx=3, sw=1.2)
    ex = 220 + 8 * 30 + 8
    d.text(ex, yy + 19, f"reads {n - 1} old entries, writes 1", 12.5, MUTE)
    ax = ex + 226
    d.arrow(ax, yy + 14, ax + 36, yy + 14, INK)
    oc = AMBER if tout == "EOS" else EMERALD
    d.rect(ax + 40, yy, cw, ch, fill=WHITE, stroke=oc, rx=5, sw=2)
    d.text(ax + 40 + cw / 2, yy + 19, tout, 12, oc[0], "bold", anchor="middle", mono=True)
    d.text(ax + 40 + cw + 14, yy + 19, "goes back as the next input" if tout != "EOS" else "EOS: the request ends",
           12.5, MUTE)
d.text(46, y1 + 76 + len(steps) * 48 + 14, "Without a KV cache, each step would compute the keys and values of all earlier tokens again.",
       12, MUTE, italic=True)

# ---- panel 3: hardware view -------------------------------------------------------------
y2 = y1 + P2 + 20
P3 = 222
d.panel(y2, P3, 3, "Why do the two phases feel different to the hardware?",
        "Each step must read all model weights. Prefill uses each weight for many tokens; decode for very few.")
cards = [
    ("Prefill step", ["tokens per sequence: whole prompt", "math per weight read: high", "limit: compute  →  TTFT"], BLUE),
    ("Decode step", ["tokens per sequence: 1 (+ drafts)", "math per weight read: low", "limit: memory reads  →  TBT"],
     EMERALD),
    ("In DeepInfer", ["a step is prefill OR decode,", "never mixed; decode can", "replay a CUDA graph"], VIOLET),
]
for i, (t, lines, col) in enumerate(cards):
    bx = 46 + i * 354
    d.box(bx, y2 + 72, 300, 120, t, [], col=col, tsize=14)
    for j, s in enumerate(lines):
        d.text(bx + 18, y2 + 120 + j * 22, s, 12.5, INK)

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "prompt token"), (EMERALD, "new token"), (AMBER, "KV cache entry (dark: new)"),
                 (VIOLET, "model / engine")])
y += 36
y = d.footnotes(30, y, [
    "TTFT = time to first token. TBT = time between tokens. Both are latency targets for a serving system.",
    "DeepInfer: prepare_sample.cpp:61 rejects mixed batches; model_runner.py:182 uses CUDA graphs only for decode.",
    "With draft tokens (default 5), a DeepInfer decode step sends up to 1 + 5 = 6 tokens per sequence (mtp_varlen.hpp:153-157).",
])
d.save(height=y + 8)
