"""Diagram: what DeepseekDecoderLayer builds, and which forward lines run for which kind of layer.

Used by: src/code/decoder-layer.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/decoder_layer.py:38-45     _build_mlp_and_layernorms
  deepinfer/model_executor/models/decoder_layer.py:48-90     DeepseekDecoderLayer.__init__
  deepinfer/model_executor/models/decoder_layer.py:97-175    DeepseekDecoderLayer.forward
  deepinfer/model_executor/models/decoder_layer.py:178-239   DFlashDecoderLayer
  deepinfer/model_executor/models/deepseek.py:126-128, 191-198   YOCO compaction only with mode "compact", in prefill
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, CELL_EMPTY, INK, LINE, MUTE, PINK, TEAL, VIOLET, Diagram, WHITE  # noqa: E402

d = Diagram(width=1100)
d.header(
    "decoder_layer.py: what one layer holds, and what runs",
    "DeepseekDecoderLayer (main model) and DFlashDecoderLayer (draft model)  ·  commit 9bd9cf2",
    params="in: hidden [T, H] + residual  ·  out: MoE output [T, H] + HCLazyPostData",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 14, y + 24, title, TS, col[0], "bold")
    yy = y + 24
    if sub:
        d.text(x + 14, y + 43, sub, 12, MUTE)
        yy = y + 43
    for i, s in enumerate(lines):
        d.text(x + 14, yy + 21 + i * 18, s, MS, INK, mono=True)


cw, gx = 310, 39
xs = [46, 46 + cw + gx, 46 + 2 * (cw + gx)]

# ============================================================================
# Panel 1: __init__
# ============================================================================
y0 = 112
P1_H = 224
d.panel(y0, P1_H, 1, "What does __init__ build from one MoeDecoderBlockHC?",
        "The block holds the HF weights. The layer wraps them in runtime modules and sets some flags.")
r1 = y0 + 72
ch = 130
card(xs[0], r1, cw, ch, "mHC parameters", [
    "HCLayerMixin.__init__(layer)",
    "hc_attn, hc_attn_fn, _scale",
    "hc_ffn,  hc_ffn_fn,  _scale",
    "hc_shifted, use_mega_mhc",
], TEAL, sub="decoder_layer.py:57-58")
card(xs[1], r1, cw, ch, "Sub-layers", [
    "self_attn = V4Attention",
    "mlp = DeepseekMoE",
    "attn_layernorm (fp8_attn)",
    "ffn_layernorm  (fp8_mlp)",
], VIOLET, sub="decoder_layer.py:85-87, 38-45")
card(xs[2], r1, cw, ch, "Flags and options", [
    "dflash_input_index (or None)",
    "yoco_captures_shared_hidden",
    "engram = Engram (some layers)",
    "timer group key",
], AMBER, sub="decoder_layer.py:64-90")

# ============================================================================
# Panel 2: which lines run
# ============================================================================
y0b = y0 + P1_H + 22
rows = [
    ("Engram hook (closure)", "111-118"),
    ("YOCO compaction", "134-142"),
    ("attn_norm_forward", "143"),
    ("DFlash feature store", "144-145"),
    ("YOCO shared hidden", "146-152"),
    ("self_attn", "155-161"),
    ("ffn_norm_forward", "162"),
    ("mlp", "169-173"),
]
cols = ["plain layer", "Engram layer", "DFlash target", "1st YOCO consumer", "DFlash draft"]
# Y = runs, P = prefill with compact mode only, N = does not run
grid = [
    "NYNNN",
    "NNNPN",
    "YYYYY",
    "NNYNN",
    "NNNYN",
    "YYYYY",
    "YYYYY",
    "YYYYY",
]
RH = 30
P2_H = 72 + 40 + RH * len(rows) + 22
d.panel(y0b, P2_H, 2, "Which lines of forward run for which kind of layer?",
        "Four calls run in every layer. The other blocks depend on the layer and the step.")
gx0 = 46
lab_w = 300
col_w = (1054 - gx0 - lab_w) / len(cols)
hy = y0b + 72
for j, c in enumerate(cols):
    d.text(gx0 + lab_w + col_w * j + col_w / 2, hy + 20, c, 12.5, INK, "bold", "middle")
for i, (name, ln) in enumerate(rows):
    ry = hy + 32 + i * RH
    fill = WHITE if i % 2 == 0 else CELL_EMPTY
    d.rect(gx0, ry, 1008, RH, fill=fill, stroke=LINE, rx=0, sw=0.8)
    d.text(gx0 + 12, ry + 20, name, 12.5, INK, mono=True)
    d.text(gx0 + lab_w - 12, ry + 20, ln, 12, MUTE, anchor="end", mono=True)
    for j, g in enumerate(grid[i]):
        cx = gx0 + lab_w + col_w * j + col_w / 2
        if g == "Y":
            d.circle(cx, ry + RH / 2, 6, TEAL[0])
        elif g == "P":
            d.circle(cx, ry + RH / 2, 6, WHITE, stroke=PINK[0], sw=2)
            d.text(cx + 12, ry + 20, "prefill", 11.5, PINK[0], mono=True)
        else:
            d.text(cx, ry + 20, "-", 12.5, MUTE, anchor="middle", mono=True)

y = y0b + P2_H + 24
d.legend(30, y, [(TEAL, "mHC (dot in panel 2 = the line runs)"), (VIOLET, "sub-layers"), (AMBER, "options"),
                 (PINK, "only in a compact-mode prefill")])
y += 40
y = d.footnotes(30, y, [
    "DFlash draft = DFlashDecoderLayer.forward_drafts (decoder_layer.py:224-239); it calls self_attn.forward_drafts.",
    "A layer can be of more than one kind. The YOCO shared hidden is kept in prefill and decode (decoder_layer.py:146),",
    "  but only when a consumer layer reads it (decoder_layer.py:76).",
    "Timers (cuda_timer, cuda_graph_timer) wrap both halves in every layer; they record only in a few layers.",
])
d.save(height=y + 10)
