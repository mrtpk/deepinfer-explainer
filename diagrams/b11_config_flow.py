"""Diagram: how settings become the four config objects, and who reads or writes them.

Used by: src/code/config.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:67-84           LLM kwargs -> EngineArgs
  deepinfer/engine/arg_utils.py:48-114         __post_init__, create_engine_configs
  deepinfer/config.py:19-216                   the four classes
  deepinfer/worker/base.py:267                 writes CacheConfig.num_gpu_blocks
  deepinfer/worker/cache_engine.py:949-951     writes bytes_of_state_per_seqs, num_state_seqs, bytes_per_block
  deepinfer/engine/llm_engine.py:252-253, 307-327   writes SchedulerConfig.engine_type / driver_gpu_id, passes it to C++
  csrc/engine/scheduler.hpp:94-108             C++ reads SchedulerConfig attributes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "From LLM(...) arguments to four config objects",
    "deepinfer/config.py and engine/arg_utils.py  ·  who makes each object, who writes it later, who reads it  ·  commit 9bd9cf2",
)

y0 = 100
P1_H = 214
d.panel(y0, P1_H, 1, "How do the user's arguments become config objects?",
        "LLM fills EngineArgs; create_engine_configs() makes the four objects in one call.")
by = y0 + 72
d.box(46, by, 300, 100, "LLM(model, **kwargs)", [
    "disable_log_stats=True",
    "stop_preempted_request=False",
    "offline_inference=True",
    "llm.py:67-84",
], col=AMBER)
d.box(400, by, 300, 100, "EngineArgs (dataclass)", [
    "26 fields with defaults",
    "__post_init__: ZOS=1, MM pool=1",
    "create_engine_configs()",
    "arg_utils.py:17-114",
], col=BLUE)
d.box(754, by, 300, 100, "four config objects", [
    "ModelConfig     CacheConfig",
    "ParallelConfig  SchedulerConfig",
    "-> LLMEngine.__init__",
    "llm_engine.py:460-469",
], col=VIOLET)
ay = by + 50
d.arrow(346, ay, 398, ay, AMBER)
d.arrow(700, ay, 752, ay, BLUE)

y1 = y0 + P1_H + 20
rows = [
    ("ModelConfig", "model, tokenizer, max_model_len -> runtime_max_model_len, model_cfg (config.json)",
     "tokenizer, get_model, ModelRunner, CacheEngine sizes"),
    ("CacheConfig", "block_size 128, gpu_memory_utilization;  later: num_gpu_blocks (base.py:267),",
     "bytes_per_block, num_state_seqs (cache_engine.py:949-951) -> BlockManager x 2"),
    ("ParallelConfig", "dp, cp, ep, enp sizes, engine_rank -> data_parallel_rank, world_size",
     "Worker global rank, init_dist, rendezvous port, MFU"),
    ("SchedulerConfig", "max_num_seqs, max_num_batched_tokens, chunked_prefill, attempt intervals;",
     "later: engine_type, driver_gpu_id -> C++ Scheduler reads 9 attributes"),
]
RH = 62
P2_H = 72 + len(rows) * (RH + 10) + 12
d.panel(y1, P2_H, 2, "What does each object hold, and who uses it?",
        "Two objects get more fields after start-up measurements; the C++ scheduler reads one of them.")
cy = y1 + 72
cols = [VIOLET] * 4
for (name, l1, l2), col in zip(rows, cols):
    d.rect(46, cy, 1008, RH, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, RH, fill=col[0], stroke=None, rx=3)
    d.text(66, cy + 24, name, 14, col[0], "bold")
    d.text(230, cy + 24, l1, 12, INK, mono=True)
    d.text(230, cy + 44, l2, 12, INK, mono=True)
    cy += RH + 10

y = y1 + P2_H + 22
d.legend(30, y, [(AMBER, "user API"), (BLUE, "EngineArgs"), (VIOLET, "config objects")])
y += 38
y = d.footnotes(30, y, [
    "CP follower processes get pickled copies; ModelConfig drops model_cfg when pickled and loads config.json again (config.py:96-113).",
    "CacheConfig is shared by object identity between LLMEngine and the driver Worker, so their later writes are visible to the engine.",
])
d.save(height=y + 10)
