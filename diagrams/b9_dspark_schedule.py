"""Diagram: DSpark confidence-scheduled verification - from confidences to seqlen_q.

Used by: src/concepts/dspark.html ("In the code" / scheduling)
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:1242-1251        accept_rates = running product of the confidences
  csrc/engine/mtp_varlen.hpp:150-267         MTPVarlen::schedule: sort rates, best total_q by throughput, split
  csrc/engine/mtp_varlen.hpp:139-148         update_runtime: measured forward / sampler times
  deepinfer/worker/worker.py:218-234         ZOS: GPU recomputes the per-request split; D2H copy + d2h_evt
  deepinfer/model_executor/layers/tilelang_ops/schedule_mtp_varlen.py:35-98  reference of the GPU split
Panel 1 uses toy confidences and a toy cost curve; DeepInfer measures the curve at start-up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
_box = d.box
d.box = lambda *a, **k: _box(*a, mono_size=12, **k)
W = d.W

d.header(
    "DSpark: how confidences set the verification length",
    "DEEPINFER_ENABLE_MTP_VARLEN=1  ·  3 requests, 5 drafts each  ·  toy confidences and a toy cost curve",
    params="rate_j = c1 × … × cj   ·   E(total_q) = num_seqs + Σ chosen rates   ·   pick total_q with the best E / time",
)

conf = {"A": [0.95, 0.9, 0.85, 0.8, 0.7], "B": [0.6, 0.5, 0.5, 0.4, 0.3], "C": [0.9, 0.3, 0.5, 0.5, 0.5]}
cum = {}
for n, c in conf.items():
    r, out = 1.0, []
    for x in c:
        r *= x
        out.append(r)
    cum[n] = out
order = sorted(((cum[n][j], i, n, j) for i, n in enumerate(conf) for j in range(5)), key=lambda t: (-t[0], t[1]))
best_total = 12
chosen = order[: best_total - 3]
chosen_set = {(n, j) for _, _, n, j in chosen}

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 394
d.panel(y0, P1, 1, "Which drafts are worth a check? The ones with a high running product",
        "The scheduler multiplies the confidences, sorts all drafts of the batch, and keeps the best prefix.")

tx = 46
ty = y0 + 84
d.text(tx, ty, "request", 12.5, MUTE, "bold")
for j in range(5):
    d.text(tx + 150 + j * 120, ty, f"draft {j + 1}", 12.5, MUTE, "bold")
d.text(tx + 760, ty, "seqlen_q", 12.5, MUTE, "bold")
cell_w, cell_h = 108, 44
for r, n in enumerate(conf):
    ry = ty + 14 + r * (cell_h + 10)
    d.text(tx + 10, ry + 28, n, 15, INK, "bold", mono=True)
    for j in range(5):
        cx = tx + 150 + j * 120
        on = (n, j) in chosen_set
        col = EMERALD if on else None
        d.rect(cx, ry, cell_w, cell_h, fill=EMERALD[1] if on else WHITE, stroke=EMERALD[0] if on else LINE,
               rx=6, sw=1.4 if on else 1.1, dash=None if on else "4 3")
        d.text(cx + cell_w / 2, ry + 18, f"c {conf[n][j]:.2f}", 12, MUTE, anchor="middle", mono=True)
        d.text(cx + cell_w / 2, ry + 36, f"{cum[n][j]:.3f}", 13, EMERALD[0] if on else INK, "bold", "middle", mono=True)
    sq = 1 + sum(1 for j in range(5) if (n, j) in chosen_set)
    d.rect(tx + 760, ry + 7, 80, 30, fill=WHITE, stroke=BLUE, rx=6, sw=1.4)
    d.text(tx + 800, ry + 27, str(sq), 14, BLUE[0], "bold", "middle", mono=True)

ly = ty + 14 + 3 * (cell_h + 10) + 26
d.text(tx, ly, "Sorted rates (best first):", 13, INK, "bold")
items = [f"{c:.3f}{n}{j + 1}" for c, _, n, j in order[:11]]
d.text(tx + 182, ly, "  ".join(items[:9]) + "  |  " + "  ".join(items[9:11]) + " …", 12, INK, mono=True)
d.text(tx, ly + 24, "Toy cost curve (graph size → ms): 4 → 10.0   8 → 10.4   12 → 11.6   16 → 12.4   20 → 13.2", 12.5, INK, mono=True)
d.text(tx, ly + 48, "total_q 8: E = 7.03, 7.03 / 10.4 = 0.676     total_q 12: E = 8.59, 8.59 / 11.6 = 0.741  ← best",
       12.5, INK, mono=True)
d.text(tx, ly + 72, "fixed 1 + 5 (total_q 18): E = 9.05, 9.05 / 13.2 = 0.686 expected tokens per ms", 12.5, MUTE, mono=True)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 262
d.panel(y1, P2, 2, "Who decides, and with which confidences? CPU picks the total, GPU splits it",
        "With ZOS the newest confidences are still on the device when the CPU schedules the next step.")
by = y1 + 72
bw, bh = 300, 128
xs = [46, 400, 754]
d.box(xs[0], by, bw, bh, "CPU: MTPVarlen::schedule", [
    "rates of step N−2 → best total_q", "rates of step N−1 → split", "(when post-processing has", "not caught up: one step older)",
    "mtp_varlen.hpp:150-267"], col=VIOLET)
d.box(xs[1], by, bw, bh, "GPU: compute_seqlens_q_…", [
    "same total_q, newest confidences", "cumprod → global sort", "→ seqlen_q per request", "new requests: rate 0, last",
    "worker.py:218-219"], col=PINK)
d.box(xs[2], by, bw, bh, "Back to the CPU", [
    "copy seqlens_q to pinned memory", "wait for d2h_evt", "update the sequence metadata", "then sample",
    "worker.py:146-152, 229-234"], col=BLUE)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, VIOLET)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, PINK)
d.callout(46, by + bh + 16, 1008, "Feedback:", "after each decode step, update_mtp_runtime stores the measured forward and sampler times.",
          AMBER)

y = y1 + P2 + 24
d.legend(30, y, [(EMERALD, "draft that is verified"), (BLUE, "result per request"), (VIOLET, "CPU scheduler"),
                 (PINK, "GPU kernel"), (AMBER, "runtime feedback")])
y += 36
y = d.footnotes(30, y, [
    "Panel 1 uses one set of rates for both decisions, and no slope or sampler time. The real cost per step is",
    "  baseline_ms(graph) + slope_ms × graph_size + sampler_ms (mtp_varlen.hpp:242-244).",
    "E counts the real token of each request (1 each) plus the expected number of accepted drafts.",
])
d.save(height=y + 10)
