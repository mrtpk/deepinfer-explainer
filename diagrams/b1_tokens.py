"""Diagram: from text to token ids; the BPE merge idea; DeepInfer's special ids.

Used by: src/learn/tokens.html (section "The picture")
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/tokenizer.py:25-30    release policy: BOS id 0, PAD id 2, 21 multimodal tokens at 129280-129300
  deepinfer/hugging_face/tokenizer.py:36-41    BOS must be id 0, EOS id 1, PAD id 2 (else ValueError)
  deepinfer/hugging_face/tokenizer.py:59-69    add_bos_token is turned on; encode("") must give [0]
  deepinfer/entrypoints/llm.py:156             LLM._add_request calls tokenizer.encode(prompt)
Panel 1 pieces and ids are illustrative (only BOS = 0 is real). Panel 2 is the textbook BPE example.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram, text_width  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("From text to token ids",
         "Panel 1 ids are illustrative (only BOS = 0 is real)  ·  panel 2 is a toy BPE run  ·  panel 3 is DeepInfer's real policy")

# ---- panel 1 -------------------------------------------------------------------
y0 = 92
P1 = 196
d.panel(y0, P1, 1, "How does text become ids?",
        "The tokenizer cuts the text into known pieces. Each piece has one integer id. DeepInfer puts BOS (id 0) first.")
d.rect(46, y0 + 72, 250, 40, fill=WHITE, stroke=INK, rx=8, sw=1.3)
d.text(171, y0 + 97, '"Tokenization isn\'t hard."', 13, INK, anchor="middle", mono=True)
d.arrow(298, y0 + 92, 334, y0 + 92, INK)
pieces = [("BOS", "0", AMBER), ("Token", "15400", BLUE), ("ization", "2860", BLUE), (" isn", "4568", BLUE),
          ("'t", "498", BLUE), (" hard", "3245", BLUE), (".", "16", BLUE)]
x = 338
for tok, tid, col in pieces:
    w = max(text_width(tok.replace(" ", "␣"), 13, mono=True), text_width(tid, 12.5, mono=True)) + 20
    d.rect(x, y0 + 72, w, 40, fill=col[1], stroke=col, rx=6, sw=1.3)
    d.text(x + w / 2, y0 + 97, tok.replace(" ", "␣"), 13, INK, anchor="middle", mono=True)
    d.text(x + w / 2, y0 + 134, tid, 12.5, col[0], "bold", anchor="middle", mono=True)
    x += w + 8
d.text(338, y0 + 162, "␣ = a space. A space usually belongs to the next piece. Common words are one piece; rare words are several.",
       12, MUTE, italic=True)

# ---- panel 2 -------------------------------------------------------------------
y1 = y0 + P1 + 20
steps = [
    ("start", "l o w ␣ l o w e r ␣ l o w e s t", "single characters"),
    ("merge 1", "lo w ␣ lo w e r ␣ lo w e s t", "pair (l, o) is most frequent: 3 times"),
    ("merge 2", "low ␣ low e r ␣ low e s t", "pair (lo, w): 3 times"),
    ("merge 3", "low ␣ lowe r ␣ lowe s t", "pair (low, e): 2 times"),
]
P2 = 74 + len(steps) * 34 + 16
d.panel(y1, P2, 2, "How does BPE learn its pieces?",
        "Training repeats one rule: merge the most frequent pair of neighbours into a new piece.")
for i, (k, v, note) in enumerate(steps):
    yy = y1 + 76 + i * 34
    d.text(46, yy + 16, k, 12.5, VIOLET[0] if i else MUTE, "bold", mono=True)
    d.rect(140, yy, 470, 26, fill=VIOLET[1] if i else WHITE, stroke=VIOLET if i else MUTE, rx=6, sw=1.2)
    d.text(152, yy + 18, v, 13, INK, mono=True)
    d.text(630, yy + 18, note, 12.5, MUTE)

# ---- panel 3 -------------------------------------------------------------------
y2 = y1 + P2 + 20
P3 = 196
d.panel(y2, P3, 3, "Which ids are special in DeepInfer?",
        "The default release policy checks these ids. If one is wrong, get_hf_tokenizer stops with ValueError.")
bw = 318
specials = [
    ("BOS  ·  id 0", ["<|begin▁of▁sentence|>", "added first by encode()"], AMBER),
    ("EOS  ·  id 1", ["<|end▁of▁sentence|>", "the model writes it to stop"], AMBER),
    ("PAD  ·  id 2", ["<|▁pad▁|>", "marks padding"], AMBER),
]
for i, (t, lines, col) in enumerate(specials):
    bx = 46 + i * (bw + 27)
    d.box(bx, y2 + 70, bw, 76, t, [], col=col, tsize=14)
    for j, s in enumerate(lines):
        d.text(bx + bw / 2, y2 + 112 + j * 19, s, 12.5 if j == 0 else 12, INK if j == 0 else MUTE,
               anchor="middle", mono=(j == 0))
d.text(46, y2 + 176, "Also reserved: 21 multimodal placeholder tokens at ids 129280-129300 (tokenizer.py:25-30, 48-56).",
       12.5, MUTE)

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "text piece"), (AMBER, "special token"), (VIOLET, "new piece from a BPE merge")])
y += 36
y = d.footnotes(30, y, [
    "Panel 1: the pieces and ids are made up to show the idea. A real tokenizer can cut the text in other places.",
    "Panel 2: a real byte-level BPE starts from bytes, learns many thousands of merges, and keeps the merge list in tokenizer.json.",
    "Panel 3: the real token names use the full-width bar U+FF5C, shown here as |.",
])
d.save(height=y + 8)
