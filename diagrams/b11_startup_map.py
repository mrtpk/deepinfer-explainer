"""Diagram: map of the tour "Start-up": processes, then the 14 stops in code order.

Used by: src/tours/startup.html
Sources (commit 9bd9cf2):
  examples/offline_inference.py:24-28, 112-113   --ep 8 --cp 1 -> dp_size 8, launch_dp(main, dp_size)
  examples/_launch.py:26-50                      run_dp: one spawned process per DP rank of this node
  examples/_config.py:55-64, 104-125             CUDA_VISIBLE_DEVICES first, then import deepinfer, then LLM(...)
  deepinfer/entrypoints/llm.py:67-84             LLM.__init__ -> EngineArgs -> LLMEngine.from_engine_args
  deepinfer/engine/arg_utils.py:48-114           __post_init__ (ZOS default), create_engine_configs
  deepinfer/engine/llm_engine.py:200-221         tokenizer, MultimodalProcessor (_bind_numa, fork)
  deepinfer/engine/llm_engine.py:368-414         CP followers (spawn) and the driver Worker
  deepinfer/worker/base.py:58-123, 182-201       init_model (NUMA, device, CPU binding, seed), init_dist
  deepinfer/model_executor/parallel_utils/parallel_state.py:70-126   groups
  deepinfer/model_executor/models/deepseek.py:446-521, 255-321       load_model, DFlash, EPLB, userbuffer
  deepinfer/worker/base.py:211-288               profile, mean over ranks, cache engine, graph capture
  deepinfer/engine/llm_engine.py:263-305         block managers, scheduler, StatsLogger
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Start-up: from python3 offline_inference.py to a ready engine",
    "Example: examples/offline_inference.py with --ep 8 --cp 1 on one host  ·  commit 9bd9cf2",
    params="dp_size = 8   max_num_seqs = 4   max_model_len = 32768   gpu_memory_utilization = 0.85",
)

# ---------------------------------------------------------------------------
# Panel 1: processes
# ---------------------------------------------------------------------------
y0 = 112
BH = 116
P1_H = 72 + BH + 22
d.panel(y0, P1_H, 1, "Which processes does start-up make?",
        "The launcher spawns one process per DP rank. Each process builds one full engine.")
bx = [46, 402, 758]
bw = 296
by = y0 + 72
d.box(bx[0], by, bw, BH, "launcher process", [
    "examples/offline_inference.py",
    "launch_dp -> run_dp",
    "spawn x 8, then join()",
    "no deepinfer import here",
], col=AMBER, align="start")
d.box(bx[1], by, bw, BH, "DP rank process (x 8)", [
    "main(8, dp_rank)",
    "main thread: LLM, LLMEngine,",
    "  driver Worker, C++ scheduler",
    "rank = dp_rank, 1 device",
    "CUDA_VISIBLE_DEVICES = dp_rank",
], col=BLUE, align="start")
d.box(bx[2], by, bw, BH, "helpers of one engine", [
    "CP followers: cp_size - 1 = 0",
    "  (spawn, one per extra CP rank)",
    "multimodal worker: fork x 1",
    "stats log thread (daemon)",
    "profile HTTP thread (optional)",
], col=PINK, align="start")
ay = by + BH / 2
d.arrow(bx[0] + bw, ay, bx[1] - 2, ay, AMBER)
d.arrow_label((bx[0] + bw + bx[1]) / 2, ay, "spawn", AMBER)
d.arrow(bx[1] + bw, ay, bx[2] - 2, ay, BLUE)
d.arrow_label((bx[1] + bw + bx[2]) / 2, ay, "start", BLUE)

# ---------------------------------------------------------------------------
# Panel 2: stops
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
CARD_H = 50
GAP = 10
L, E, R = AMBER, BLUE, EMERALD
stops = [
    ("The launcher starts one process per DP rank", "dp_size = 8 // 1 = 8   main(dp_size, dp_rank)", L, "launcher"),
    ("Environment and devices, then import deepinfer", "CUDA_VISIBLE_DEVICES, NEXTN=5, FORCE_TOPK=4096", L, "each DP process"),
    ("LLM.__init__ makes EngineArgs", "offline_inference=True   ZOS=1 (setdefault)", E, "engine"),
    ("EngineArgs makes four config objects", "runtime_max_model_len 32784   block_size 128", E, "engine"),
    ("HF config, tokenizer, multimodal worker", "config.json -> model_cfg   BOS 0, EOS 1", E, "engine"),
    ("Workers: CP followers, then the driver", "0 followers   driver Worker in this process", E, "engine"),
    ("Device setup: NUMA, device, CPU, seed", "libnuma bind   cuda:0   bind_cpu   seed + rank", R, "every rank"),
    ("Process groups", "gloo world -> tcp://localhost:23283   NCCL groups", R, "every rank"),
    ("Model build and weight loading", "extra experts   meta device   safetensors", R, "every rank"),
    ("Runtime model: DFlash, EPLB, userbuffer", "one load balancer per MoE layout", R, "every rank"),
    ("Profile run and KV cache size", "4 x 8192 tokens, 449 temporary blocks, mean of 8", R, "every rank"),
    ("CacheEngine allocation", "gpu_blocks [N, bytes]   gpu_states [5, bytes]", R, "every rank"),
    ("CUDA graph capture", "6 graphs [1 .. 24] + 3 DFlash   (defaults: 195 + 35)", R, "every rank"),
    ("Ready: block managers, scheduler, statistics", "BlockManager x 2   Scheduler   StatsLogger", E, "engine"),
]
P2_H = 72 + len(stops) * (CARD_H + GAP) - GAP + 22
d.panel(y1, P2_H, 2, "In which order does start-up run?",
        "Each card is one stop of the tour. The pill says where the stop runs.")
cy = y1 + 72
for i, (title, row, col, where) in enumerate(stops):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    pw = len(where) * 11 * 0.602 + 20
    d.pill(1054 - 10 - pw, cy + 8, pw, where, col[0])
    if i < len(stops) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + GAP - 2, col)
    cy += CARD_H + GAP

y = y1 + P2_H + 22
d.legend(30, y, [(AMBER, "launcher, before import"), (BLUE, "engine process, once"),
                 (EMERALD, "every rank (driver and CP followers)"), (PINK, "helper processes and threads")])
y += 38
y = d.footnotes(30, y, [
    "Stops 7-13 run inside Worker calls; with --cp > 1 the CP followers run them too.",
    "Numbers use the example settings; 195 + 35 graphs are for the EngineArgs default max_num_seqs = 256.",
])
d.save(height=y + 10)
