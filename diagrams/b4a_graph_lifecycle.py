"""Diagram: how DeepInfer captures CUDA graphs at start-up and replays them in decode steps.

Used by: src/concepts/cuda-graphs.html, src/code/cuda-graph-runner.html
Sources (commit 9bd9cf2):
  deepinfer/worker/model_runner.py:73-79              graphs on unless DEEPINFER_ENFORCE_EAGER or PROMPT engine; max = max_num_seqs * (1 + nextn)
  deepinfer/worker/cuda_graph_runner.py:41-51         build_graph_batch_sizes: powers of two below the interval, then steps of interval
  deepinfer/worker/cuda_graph_runner.py:93-96         full-size buffers made once from placeholder sequences
  deepinfer/worker/cuda_graph_runner.py:102-141       capture loop: largest first, cut views, warm-up, clean, capture, share pool
  deepinfer/worker/cuda_graph_runner.py:143-154       select (bisect_left) and replay
  deepinfer/worker/model_runner.py:182-191            decode only; padding rows; C++ fills the graph buffers
  deepinfer/worker/base.py:274-285                    warm_up_model calls the capture at start-up
Numbers: examples/offline_inference.py (max_num_seqs 4), default nextn 5, default interval 8.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "CUDA graphs: capture once, replay in every decode step",
    "Main model forward only  ·  example: max_num_seqs 4, nextn 5, interval 8",
    params="max size = 4 x (1 + 5) = 24 rows   ·   sizes [1, 2, 4, 8, 16, 24]",
)

# ============================================================================
# Panel 1: capture at start-up
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "Start-up: what does the capture make?",
        "One set of input buffers for 24 rows. Each graph uses a view of its first rows. All graphs share one memory pool.")

d.box(46, y0 + 74, 300, 150, "Full input buffers", [
    "24 placeholder sequences,",
    "1 row each",
    "positions       [24]",
    "slot_mapping_*  [24]",
    "block_tables    [24, 320]",
    "... one row per token",
], col=AMBER, align="start", mono_size=12)
d.arrow(348, y0 + 149, 396, y0 + 149, AMBER)
d.arrow_label(372, y0 + 149, "[:bs]", AMBER)

d.step_card(398, y0 + 74, 330, 150, 1, "For bs = 24, 16, 8, 4, 2, 1", VIOLET, tag="capture()",
            rows=[("1", "cut views [:bs]"),
                  ("2", "warm-up run (not recorded)"),
                  ("3", "clear derived fields"),
                  ("4", "record one forward pass"),
                  ("5", "keep the pool of the first graph")], key_w=24)
d.arrow(730, y0 + 149, 778, y0 + 149, VIOLET)

d.box(780, y0 + 74, 274, 150, "graphs: dict[bs, data]", [
    "graph       CUDAGraph",
    "input_metadata_source",
    "input_metadata_device",
    "output      rows [:bs]",
    "graph_handle (timer)",
], col=EMERALD, align="start", mono_size=12)
d.text(46, y0 + 252, "Largest first: the first capture sets the memory pool, and the smaller graphs reuse it.", 12, MUTE,
       italic=True)
d.text(46, y0 + 270, "The cut views share storage, so one write into the size-24 buffers feeds every graph.", 12, MUTE,
       italic=True)

# ============================================================================
# Panel 2: each decode step
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 196
d.panel(y1, P2_H, 2, "Each decode step: select, fill, replay",
        "The step pads its rows up to the next captured size. Nothing is recorded again.")
cards = [
    (BLUE, "select(12) -> 16", "bisect_left", [("in", "total_q = 12"), ("out", "graph of size 16")]),
    (AMBER, "fill the buffers", "C++ / kernel", [("rows", "12 real + 4 padding"), ("into", "views [:16]")]),
    (EMERALD, "replay()", "one call", [("run", "all kernels of one"), ("", "forward pass")]),
]
cw = 316
for i, (col, title, tag, rows) in enumerate(cards):
    x = 46 + i * (cw + 30)
    d.step_card(x, y1 + 70, cw, 92, i + 1, title, col, tag=tag, rows=rows, key_w=44)
    if i < 2:
        d.arrow(x + cw + 2, y1 + 116, x + cw + 28, y1 + 116, col)
d.text(46, y1 + 182, "Rows past the largest size raise ValueError in select(). There is no eager fallback for a large batch.", 12,
       PINK[0])

# ============================================================================
# Panel 3: when eager
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 150
d.panel(y2, P3_H, 3, "When does the model run without a graph (eager)?",
        "Prefill steps always. Decode steps only when graphs are off or not captured yet.")
items = [
    ("prefill step", "run_cuda_graph needs not is_prompt (model_runner.py:182)"),
    ("DEEPINFER_ENFORCE_EAGER=1", "use_cuda_graph = False (model_runner.py:73)"),
    ("PROMPT engine", "use_cuda_graph = False (model_runner.py:73)"),
    ("before capture", "the profile run at start-up: graphs is still None"),
]
for i, (a, b) in enumerate(items):
    yy = y2 + 76 + i * 18
    d.text(46, yy, a, 12, INK, "bold", mono=True)
    d.text(330, yy, b, 12, INK)

y = y2 + P3_H + 24
d.legend(30, y, [(AMBER, "input buffers"), (VIOLET, "capture loop"), (EMERALD, "captured graphs"), (BLUE, "selection")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: DFlash has a second runner with its own sizes over sequences (not rows). See the deep dive.",
    "With ZOS on, the buffers are on the device; with ZOS off, they are pinned CPU memory and the graph copies them first.",
])
d.save(height=y + 14)
