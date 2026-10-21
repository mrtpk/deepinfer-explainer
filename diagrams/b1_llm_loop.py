"""Diagram: an LLM writes text one token per step (generic, illustrative values).

Used by: src/learn/what-an-llm-does.html (section "The picture")
Sources (commit 9bd9cf2) for the DeepInfer notes in the footnotes:
  deepinfer/hugging_face/tokenizer.py:36-39     BOS id 0, EOS id 1
  csrc/engine/scheduler.hpp:1035-1051           stop at EOS, at max_model_len, or at max_tokens
  deepinfer/model_executor/layers/sampler_utils.py:20-28   logits = hidden states x LM head weight
All token ids and probabilities are illustrative (not real model output).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("How an LLM writes text: one token per step",
         "Illustrative ids and probabilities  ·  not real model output  ·  the loop is the same for every LLM")

# ---- panel 1: one step ------------------------------------------------------
y0 = 92
P1 = 246
d.panel(y0, P1, 1, "What happens in one step?",
        "The model reads all tokens so far. It gives a probability to every token in the vocabulary.")

bx_y = y0 + 74
bw, bh = 300, 150
xs = [46, 400, 754]
d.box(xs[0], bx_y, bw, bh, "1  Tokenizer", [], col=BLUE, tsize=14)
lines1 = ['"The cat sat on"', "↓", "[0, 671, 8214, 3923, 377]", "BOS, The, cat, sat, on"]
for i, s in enumerate(lines1):
    d.text(xs[0] + bw / 2, bx_y + 52 + i * 21, s, 13 if i != 3 else 12, INK if i != 3 else MUTE,
           anchor="middle", mono=True)

d.box(xs[1], bx_y, bw, bh, "2  Model (transformer)", [], col=VIOLET, tsize=14)
lines2 = ["in:  5 token ids", "out: 1 score (logit) for", "     each vocabulary token", "softmax → probabilities"]
for i, s in enumerate(lines2):
    d.text(xs[1] + 22, bx_y + 52 + i * 21, s, 13, INK, mono=True)

d.box(xs[2], bx_y, bw, bh, "3  Sampler", [], col=EMERALD, tsize=14)
probs = [("the", 0.41), ("a", 0.22), ("his", 0.09), ("top", 0.05)]
for i, (tok, p) in enumerate(probs):
    yy = bx_y + 44 + i * 19
    d.text(xs[2] + 22, yy + 11, f"{tok:<4}", 12.5, INK, mono=True)
    d.rect(xs[2] + 70, yy, 160 * p / 0.41, 13, fill=EMERALD[0] if i == 0 else EMERALD[1],
           stroke=EMERALD, rx=2, sw=1)
    d.text(xs[2] + 76 + 160 * p / 0.41, yy + 11, f"{p:.2f}", 12, MUTE, mono=True)
d.text(xs[2] + 22, bx_y + 136, "picks one id → \"the\"", 13, EMERALD[0], "bold", mono=True)

for i in range(2):
    x1 = xs[i] + bw
    d.arrow(x1, bx_y + bh / 2, xs[i + 1] - 2, bx_y + bh / 2, INK)
d.arrow_label((xs[0] + bw + xs[1]) / 2, bx_y + bh / 2, "ids", INK)
d.arrow_label((xs[1] + bw + xs[2]) / 2, bx_y + bh / 2, "probs", INK)

# ---- panel 2: the loop --------------------------------------------------------
y1 = y0 + P1 + 20
rows = [
    (["BOS", "The", "cat", "sat", "on"], "the", "prefill: reads 5 tokens"),
    (["BOS", "The", "cat", "sat", "on", "the"], "mat", "decode step 1"),
    (["BOS", "The", "cat", "sat", "on", "the", "mat"], ".", "decode step 2"),
    (["BOS", "The", "cat", "sat", "on", "the", "mat", "."], "EOS", "decode step 3: stop"),
]
row_h = 44
P2 = 78 + len(rows) * row_h + 14
d.panel(y1, P2, 2, "How does a whole answer come out?",
        "The new token goes back into the input. The loop stops at EOS or at max_tokens.")
cw, gap = 62, 6
for r, (toks, out, label) in enumerate(rows):
    yy = y1 + 74 + r * row_h
    x = 46
    for j, t in enumerate(toks):
        col = EMERALD if j >= 5 else BLUE
        d.rect(x, yy, cw, 30, fill=col[1], stroke=col, rx=6, sw=1.2)
        d.text(x + cw / 2, yy + 20, t, 12.5, INK, anchor="middle", mono=True)
        x += cw + gap
    ax = 46 + 8 * (cw + gap) + 6
    d.arrow(ax, yy + 15, ax + 40, yy + 15, INK)
    oc = AMBER if out == "EOS" else EMERALD
    d.rect(ax + 44, yy, cw, 30, fill=WHITE, stroke=oc, rx=6, sw=2)
    d.text(ax + 44 + cw / 2, yy + 20, out, 12.5, oc[0], "bold", anchor="middle", mono=True)
    d.text(ax + 44 + cw + 14, yy + 20, label, 12.5, MUTE)

y = y1 + P2 + 22
d.legend(30, y, [(BLUE, "input tokens"), (EMERALD, "token made by the model"), (AMBER, "stop token (EOS)"),
                 (VIOLET, "model")])
y += 36
y = d.footnotes(30, y, [
    "Ids are made up, except BOS = 0 and EOS = 1, which DeepInfer's tokenizer checks (hugging_face/tokenizer.py:36-39).",
    "DeepInfer also stops a request at max_tokens or at the maximum model length (csrc/engine/scheduler.hpp:1035-1051).",
    "Not shown: the KV cache, which keeps the work of earlier tokens, and draft tokens (speculative decoding).",
])
d.save(height=y + 8)
