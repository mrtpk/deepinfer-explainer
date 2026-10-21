"""Diagram: how StatsLogger turns per-step records into one log line, and three of its formulas.

Used by: src/code/stats-logger.html
Sources (commit 9bd9cf2):
  deepinfer/engine/llm_engine.py:763-785       StepStats made in _process_model_outputs; log_step runs in post_process
  deepinfer/engine/stats_logger.py:355-379     _record: append to windows
  deepinfer/engine/stats_logger.py:381-390     _should_log: every DEEPINFER_LOGGING_INTERVAL_STEP steps
  deepinfer/engine/stats_logger.py:438-477     log_step: trim, aggregate, emit, clear timers
  deepinfer/engine/stats_logger.py:116-126, 342-349   queue + daemon log thread
  deepinfer/engine/stats_logger.py:194-209, 238-241   throughput, MFU, moe_lb
Example numbers are invented.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "StatsLogger: from one step to one log line",
    "deepinfer/engine/stats_logger.py  ·  one engine process  ·  example numbers are invented  ·  commit 9bd9cf2",
)

y0 = 100
BH = 100
P1_H = 72 + BH + 24
d.panel(y0, P1_H, 1, "What happens in every step, and what only every N steps?",
        "Every step appends to the windows. Every N steps the logger trims, sums, and hands one message to a thread.")
by = y0 + 72
bw = 300
d.box(46, by, bw, BH, "every step: log_step(StepStats)", [
    "_record: append (time, payload,",
    "  step) to 6 windows",
    "running / pending / cache usage",
    "stats_logger.py:438-459",
], col=BLUE, align="start")
d.box(400, by, bw, BH, "every N steps (N = 10 here)", [
    "trim windows to age <= N steps",
    "  (moe_lb: >= 128 steps)",
    "aggregate: TPS, MFU, accept, moe_lb",
    "build the [stats] line",
], col=EMERALD, align="start")
d.box(754, by, bw, BH, "log thread (daemon)", [
    "SimpleQueue.get()",
    "sleep (rank % 8) x 5 ms",
    "logger.info(each line)",
    "stats_logger.py:116-126",
], col=AMBER, align="start")
ay = by + BH / 2
d.arrow(46 + bw, ay, 398, ay, BLUE)
d.arrow_label(373, ay, "if due", BLUE)
d.arrow(400 + bw, ay, 752, ay, EMERALD)
d.arrow_label(727, ay, "put", EMERALD)

y1 = y0 + P1_H + 20
BH2 = 134
P2_H = 72 + BH2 + 24
d.panel(y1, P2_H, 2, "How are three of the numbers computed?",
        "Sums over the window. The first entry only marks the start time.")
by2 = y1 + 72
d.box(46, by2, bw, BH2, "completion_TPS", [
    "sum(tokens, entries 1..) /",
    "  (now - t of entry 0)",
    "",
    "11 entries, 24 tokens each,",
    "first at t = 0, now = 0.1 s",
    "-> 240 / 0.1 = 2400 tok/s",
], col=VIOLET, align="start", mono_size=12)
d.box(400, by2, bw, BH2, "MFU", [
    "(sum TFLOPs, entries 1..) /",
    "  (t last - t first)",
    "  / cp_size / (2 x BF16 peak)",
    "",
    "10 entries x 9 TFLOP in 0.1 s",
    "-> 900 / 1 / 4500 = 0.2",
], col=VIOLET, align="start", mono_size=12)
d.box(754, by2, bw, BH2, "moe_lb", [
    "sum of maxima / sum of means",
    "  over steps x MoE layers",
    "rank tokens [100,120,80,100]",
    "  mean 100, max 120",
    "and [90,150,60,100]: 100, 150",
    "-> (120+150)/(100+100) = 1.35",
], col=VIOLET, align="start", mono_size=12)

y = y1 + P2_H + 22
d.legend(30, y, [(BLUE, "main thread, every step"), (EMERALD, "main thread, logging step"),
                 (AMBER, "log thread"), (VIOLET, "formula")])
y += 38
y = d.footnotes(30, y, [
    "N is DEEPINFER_LOGGING_INTERVAL_STEP (default 100; the offline example sets 10). N <= 0 turns the log off.",
    "The doc calls moe_lb 'slowest rank / mean' (doc/inference_deployment_qa.md:99); the code sums maxima and means first.",
])
d.save(height=y + 10)
