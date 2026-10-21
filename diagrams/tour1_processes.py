"""Diagram: processes and threads that touch one request (offline example).

Used by: src/tours/life-of-a-request.html
Sources (commit 9bd9cf2):
  examples/offline_inference.py:24-28, 112-113   dp_size = ep // cp, world_size = dp * cp, launch_dp(main, dp_size)
  examples/_launch.py:15-50                     launch_dp / run_dp: spawn one process per DP rank, join
  examples/_config.py:86-125                      create_llm: CUDA_VISIBLE_DEVICES before import deepinfer
  deepinfer/engine/llm_engine.py:368-414          _init_workers: CP workers spawned, driver Worker in-process
  deepinfer/worker/base.py:120-133, 290-302       slave loop on cp_broadcast_object; run_workers
  deepinfer/model_executor/parallel_utils/parallel_state.py:17-23, 122-124   shm MessageQueue for CP
  deepinfer/worker/model_runner.py:200-230        broadcast_tensor_dict(input metadata)
  deepinfer/ve/multimodal_processor.py:29-104     MultimodalProcessor, forked worker, mp.Queue
  deepinfer/engine/llm_engine.py:329-342          SO matcher builder (lazy), idle CPUs
  deepinfer/structure_output/so_matcher_builder.py:45-48, 97-121   ThreadPoolExecutor, submit/pump
  deepinfer/utils.py:154-161                      get_idle_cpus: DEEPINFER_SO_BUILDER_CPUS (default 4)
  csrc/engine/scheduler.hpp:170-182, 295-341      DP all-reduce votes
  deepinfer/engine/llm_engine.py:665-679          has_unfinished_requests: DP all-reduce MAX
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, VIOLET, Diagram  # noqa: E402

d = Diagram()
d.header(
    "Which processes and threads serve one request?",
    "Offline example on one node  ·  python examples/offline_inference.py --ep 8 --cp 1  ·  commit 9bd9cf2",
    params="dp_size = ep // cp = 8   world_size = dp_size x cp = 8   one device per rank",
)


def card(x, y, w, h, title, lines, col, dash=None, tsize=15):
    d.rect(x, y, w, h, fill=col[1] if not dash else "#ffffff", stroke=col, sw=1.5 if not dash else 1.3, dash=dash)
    d.text(x + 16, y + 26, title, tsize, col if dash else INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 16, y + 50 + i * 18, s, 13, INK, mono=True)


# ============================================================================
# Panel 1
# ============================================================================
y0 = 112
P1_H = 470
d.panel(y0, P1_H, 1, "Which processes and threads run?",
        "One process per DP rank. Each one is a full engine. Helpers start only when a model or a request needs them.")

top = y0 + 78
# launcher
lx, lw, lh = 46, 330, 132
card(lx, top + 120, lw, lh, "Launcher process", ["python offline_inference.py", "launch_dp() -> run_dp()", "spawn 8, then join()", "(dp_size 1: no spawn)"], AMBER)

# replica container
rx, rw = 430, 1024
ry, rh = top, P1_H - 100
d.rect(rx, ry, rw, rh, fill=BLUE[2], stroke=BLUE, rx=12, sw=1.2, dash="4 4", stroke_op=0.5)
d.text(rx + 18, ry + 26, "DP replica process  (dp_rank r, one device)", 15, BLUE, "bold")
d.pill_auto(rx + rw - 200, ry + 10, "x 8, one per dp_rank", BLUE)

# arrow launcher -> replica
d.arrow(lx + lw, top + 120 + lh / 2, rx - 2, top + 120 + lh / 2, AMBER, sw=1.8)
d.arrow_label((lx + lw + rx) / 2, top + 120 + lh / 2, "spawn", AMBER)

# main thread
mx, my, mw, mh = rx + 20, ry + 46, 420, 150
card(mx, my, mw, mh, "Main thread (driver)", [
    "main() -> create_llm() -> LLM",
    "LLMEngine + C++ Scheduler",
    "driver Worker: cp_rank 0, device 0",
    "runs every step: stops 2-13",
], BLUE)

# SO threads
sx, sy, sw_, sh = rx + 20, my + mh + 30, 420, 96
card(sx, sy, sw_, sh, "SO builder threads", [
    "ThreadPoolExecutor, 4 workers",
    "made on the first so_args request",
], AMBER, dash="4 3", tsize=14)

# CP workers
cx, cy, cw, ch = rx + 564, ry + 46, 440, 150
card(cx, cy, cw, ch, "CP worker processes (spawn)", [
    "cp_rank 1 .. cp-1  (none for --cp 1)",
    "start_slave_worker_loop()",
    "same forward on their own device",
    "get inputs from the driver",
], VIOLET, dash="4 3", tsize=14)

# multimodal
mmx, mmy, mmw, mmh = rx + 564, cy + ch + 30, 440, 96
card(mmx, mmy, mmw, mmh, "Multimodal worker process (fork)", [
    "VL models only, 1 worker",
    "input_queue -> preprocess -> output_queue",
], EMERALD, dash="4 3", tsize=14)

# links main <-> helpers
d.arrow(mx + mw, my + 60, cx - 2, cy + 60, VIOLET, sw=1.6, dash="5 4")
d.arrow_label((mx + mw + cx) / 2, my + 60, "method name", VIOLET)
d.arrow(mx + mw, my + 112, cx - 2, cy + 112, VIOLET, sw=1.6, dash="5 4")
d.arrow_label((mx + mw + cx) / 2, my + 112, "input tensors", VIOLET)
d.arrow(sx + sw_ / 2, my + mh, sx + sw_ / 2, sy - 2, AMBER, sw=1.6, dash="5 4")
d.text(sx + sw_ / 2 + 10, my + mh + 16, "submit(); pump() each step", 12, AMBER, "bold")
mid_y = mmy + mmh / 2
vx = mmx - 44
d.path_arrow(f"M {mx + mw:.1f},{my + 138:.1f} L {vx:.1f},{my + 138:.1f} L {vx:.1f},{mid_y:.1f} L {mmx - 2:.1f},{mid_y:.1f}",
             EMERALD, sw=1.6, dash="5 4")
d.text(vx - 8, (my + 138 + mid_y) / 2 + 4, "mp.Queue", 12, EMERALD, "bold", "end")


# ============================================================================
# Panel 2
# ============================================================================
y1 = y0 + P1_H + 20
rows = [
    ("launcher -> replicas", "multiprocessing spawn, then join()", "_launch.py:35-44", AMBER),
    ("driver -> CP workers", "(method, kwargs) through a shared-memory MessageQueue", "base.py:290-302", VIOLET),
    ("driver -> CP workers", "broadcast_tensor_dict(input metadata) before forward", "model_runner.py:200-212", VIOLET),
    ("DP rank <-> DP ranks", "all-reduce: step-type vote, has_unfinished_requests()", "scheduler.hpp:170-182", BLUE),
    ("all ranks <-> all ranks", "MoE dispatch / combine inside the forward pass (EP)", "v4_modules/mlp.py:461-511", BLUE),
    ("driver <-> multimodal", "mp.Queue in, mp.Queue out; fetch() each step", "multimodal_processor.py:281-303", EMERALD),
    ("driver <-> SO threads", "futures; pump() in pre_sampler_sync()", "so_matcher_builder.py:97-121", AMBER),
]
ROW_H = 30
P2_H = 78 + len(rows) * ROW_H + 18
d.panel(y1, P2_H, 2, "How do they talk?",
        "Each channel carries one kind of data. Only the driver talks to the user script.")
ty = y1 + 84
d.text(46, ty, "from -> to", 13, MUTE, "bold")
d.text(330, ty, "channel and what it carries", 13, MUTE, "bold")
d.text(1080, ty, "source", 13, MUTE, "bold")
for i, (a, b, c, col) in enumerate(rows):
    yy = ty + 24 + i * ROW_H
    d.line(46, yy - 19, 1454, yy - 19, LINE, 0.8)
    d.text(46, yy, a, 13, col, "bold", mono=True)
    d.text(330, yy, b, 13, INK)
    d.text(1080, yy, c, 13, INK, mono=True)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "driver and engine work"), (VIOLET, "context parallelism (CP)"),
                 (EMERALD, "vision preprocessing"), (AMBER, "launcher and SO helpers")])
y += 38
y = d.footnotes(30, y, [
    "Dashed boxes: optional. CP workers exist only for --cp > 1, the multimodal worker only for VL models, SO threads only after a so_args request.",
    "Simplified: the profile HTTP server and the DP group objects are not shown. Sources: docstring of diagrams/tour1_processes.py.",
])
d.save(height=y + 10)
