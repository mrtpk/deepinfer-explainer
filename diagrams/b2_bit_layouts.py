"""Diagram: bit layouts of FP32, BF16, FP16, FP8 (E4M3, E5M2), FP4 (E2M1) and UE8M0, and 0.3 in each format.

Used by: src/learn/number-formats.html
Generic format facts (IEEE 754, OCP FP8/MX). DeepInfer-specific facts (commit 9bd9cf2):
  deepinfer/model_executor/layers/tilelang_ops/common.py:24-27   FLOAT4_E2M1_MAX = 6, FLOAT8E4M3_MAX = 448, min positive 2^-9
  deepinfer/hugging_face/weights.py:163-167                        UE8M0 value = 2 ** (bits - 127)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, PINK, TEAL, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header("Floating-point formats, bit by bit",
         "value = (−1)^sign × 1.mantissa × 2^(exponent − bias)  ·  exponent field 0 = subnormal (0.mantissa × 2^(1 − bias))",
         params="more exponent bits → more range        more mantissa bits → more precision        fewer bits → less memory")

SIGN, EXP, MAN = PINK, BLUE, AMBER

# ============================================================================
# Panel 1: layouts
# ============================================================================
y0 = 112
rows = [
    ("FP32", 1, 8, 23, "127", "3.4e38", "2^-23"),
    ("BF16", 1, 8, 7, "127", "3.4e38", "2^-7 = 0.0078"),
    ("FP16", 1, 5, 10, "15", "65,504", "2^-10"),
    ("FP8 E4M3", 1, 4, 3, "7", "448 (no inf)", "0.125"),
    ("FP8 E5M2", 1, 5, 2, "15", "57,344", "0.25"),
    ("FP4 E2M1", 1, 2, 1, "1", "6", "all: 0 .5 1 1.5 2 3 4 6"),
    ("UE8M0 scale", 0, 8, 0, "127", "2^127", "powers of 2 only"),
]
RH = 34
P1_H = 86 + len(rows) * RH + 16
d.panel(y0, P1_H, 1, "How are the bits used?",
        "Every format splits its bits into sign, exponent and mantissa. Only the split differs.")
CW = 14.6
sx = 170
for i, (name, s, e, m, bias, mx, step) in enumerate(rows):
    ry = y0 + 76 + i * RH
    d.text(46, ry + 17, name, 13.5, INK, "bold")
    x = sx
    for role, n in ((SIGN, s), (EXP, e), (MAN, m)):
        for _ in range(n):
            d.rect(x, ry + 2, CW - 1.6, 22, fill=role[1], stroke=role[0], rx=2, sw=1.0)
            x += CW
    d.text(x + 6, ry + 18, f"{s + e + m} bits", 11.5, MUTE, mono=True)
    ix = sx + 32 * CW + 70
    d.text(ix, ry + 17, bias, 12, INK, mono=True)
    d.text(ix + 60, ry + 17, mx, 12, INK, mono=True)
    d.text(ix + 175, ry + 17, step, 12, INK, mono=True)
ix = sx + 32 * CW + 70
for off, h in ((0, "bias"), (60, "largest"), (175, "step at 1.0")):
    d.text(ix + off, y0 + 64, h, 12, MUTE, "bold")

# ============================================================================
# Panel 2: 0.3 in every format
# ============================================================================
y1 = y0 + P1_H + 20
ex = [
    ("FP32", "0 01111101 00110011001100110011010", "0x3E99999A", "0.30000001", "0.000004 %"),
    ("BF16", "0 01111101 0011010", "0x3E9A", "0.30078125", "0.26 %"),
    ("FP16", "0 01101 0011001101", "0x34CD", "0.30004883", "0.016 %"),
    ("E4M3", "0 0101 010", "0x2A", "0.3125", "4.2 %"),
    ("E5M2", "0 01101 01", "0x35", "0.3125", "4.2 %"),
    ("E2M1", "0 00 1", "0x1", "0.5", "67 %"),
]
P2_H = 96 + len(ex) * 24 + 28
d.panel(y1, P2_H, 2, "Worked example: store 0.3 = 1.2 × 2^-2",
        "Round the mantissa 0.2 to the bits that the format has. Fewer bits give a larger error.")
hx = [46, 130, 470, 590, 720]
for j, h in enumerate(["format", "bits (sign exponent mantissa)", "hex", "stored value", "error"]):
    d.text(hx[j], y1 + 80, h, 12, MUTE, "bold")
for i, row in enumerate(ex):
    ry = y1 + 104 + i * 24
    for j, v in enumerate(row):
        col = INK
        d.text(hx[j], ry, v, 12.5 if j else 13, col, "bold" if j in (0, 3) else "normal", mono=j > 0)
d.text(46, y1 + P2_H - 14, "E2M1 alone cannot store 0.3 well. A shared scale fixes this: 0.3 / 0.0625 = 4.8 → code 4 → 4 × 0.0625 = 0.25 (17 %).",
       12, TEAL[0], "bold")

y = y1 + P2_H + 24
d.legend(30, y, [(SIGN, "sign bit"), (EXP, "exponent bits"), (MAN, "mantissa bits"), (TEAL, "scaled example")])
y += 36
y = d.footnotes(30, y, [
    "E4M3 here is the 'fn' variant (torch.float8_e4m3fn): no infinity; the code S.1111.111 is NaN. E5M2 keeps infinity and NaN like IEEE.",
    "The DeepInfer code uses E4M3 max 448 and E2M1 max 6 (tilelang_ops/common.py:24-27). The table rounds to nearest, ties to even.",
])
d.save(height=y + 10)
