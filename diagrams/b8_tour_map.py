"""Diagram: map of the tour "One step on many GPUs": ranks, groups and the stops of one prefill step.

Used by: src/tours/multi-gpu-step.html
Sources (commit 9bd9cf2):
  examples/offline_inference.py:24-28           --ep 4 --cp 2 -> dp = 2, world = 4
  examples/_config.py:55-63                      engine e sees devices 2e, 2e+1
  deepinfer/worker/base.py:79, 329               global rank = engine_rank * cp_size + cp_rank
  deepinfer/engine/llm_engine.py:368-414         CP rank 1 spawned; driver Worker in the engine process
  deepinfer/model_executor/parallel_utils/parallel_state.py:91-106   DP, CP, EP groups
  csrc/engine/scheduler.hpp:308-341              stop 1-2 votes
  deepinfer/worker/base.py:290-302               stop 3 run_workers -> cp_broadcast_object
  deepinfer/worker/model_runner.py:171-231       stop 4 broadcast_tensor_dict
  deepinfer/model_executor/models/deepseek.py:161-170, 241-244   stops 5 and 9
  deepinfer/model_executor/models/v4_modules/attn.py:782-829     stop 6
  deepinfer/model_executor/models/v4_modules/mlp.py:565-616      stop 7
  deepinfer/model_executor/eplb/__init__.py:131-138              stop 8
  deepinfer/model_executor/layers/sampler.py:142-161             stop 9: followers return before sampling
  deepinfer/worker/worker.py:182-189                             stop 10
Example request A: 8 prompt tokens on engine 0. Engine 1 has no waiting request. The step is an ANY point.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "One prefill step on 4 GPUs: ranks, groups, stops",
    "--ep 4 --cp 2  ->  2 DP replicas (engines) x 2 CP ranks  ·  request A: 8 prompt tokens on engine 0  ·  commit 9bd9cf2",
    params="rank = engine_rank x 2 + cp_rank   CP groups [0,1] [2,3]   DP groups [0,2] [1,3]   EP group [0,1,2,3]",
)

# ---------------------------------------------------------------------------
# Panel 1: processes and ranks
# ---------------------------------------------------------------------------
y0 = 112
EW, EH = 494, 178
P1_H = 72 + EH + 24
d.panel(y0, P1_H, 1, "Which processes and ranks take part?",
        "Each engine is one DP replica. Its driver spawns one CP follower process.")
for e in range(2):
    ex = 46 + e * (EW + 20)
    ey = y0 + 72
    d.rect(ex, ey, EW, EH, fill=WHITE, stroke=MUTE, rx=12, sw=1.2, dash="4 4", stroke_op=0.6)
    d.text(ex + 14, ey + 22, f"engine {e}  (engine_rank {e}, CUDA_VISIBLE_DEVICES={2 * e},{2 * e + 1})", 13.5, INK, "bold")
    for c in range(2):
        rx = ex + 14 + c * 236
        ry = ey + 38
        col = TEAL if c == 0 else PINK
        name = "driver: LLMEngine + Worker" if c == 0 else "CP follower: Worker only"
        d.rect(rx, ry, 226, 124, fill=col[1], stroke=col, sw=1.5)
        d.text(rx + 12, ry + 22, f"rank {2 * e + c}  (cp_rank {c})", 13.5, col[0], "bold")
        d.text(rx + 12, ry + 42, name, 12, INK)
        lines = (["scheduler, sampler", "process from _launch.py", f"device {2 * e}"] if c == 0
                 else ["no scheduler, no sampling", "spawned by _init_workers", f"device {2 * e + 1}"])
        for j, s in enumerate(lines):
            d.text(rx + 12, ry + 64 + j * 18, s, 12, INK, mono=True)

# ---------------------------------------------------------------------------
# Panel 2: the stops
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
CARD_H = 50
CARD_GAP = 12
stops = [
    ("votes: prefill or decode?", "all-reduce MIN over DP [0,2] -> both engines prefill", "DP", EMERALD),
    ("each engine schedules", "engine 0: A, 8 tokens   engine 1: empty prompt step (placeholder)", "local", BLUE),
    ("driver sends the method call", "('execute_model_step', is_prompt=True) through shm", "CP", AMBER),
    ("driver sends the input metadata", "broadcast_tensor_dict: objects via shm, tensors via NCCL/HCCL", "CP", AMBER),
    ("mirror-CP layout", "rank 0: t0 t1 t6 t7   rank 1: t2 t3 t4 t5   [4, H] each", "local", BLUE),
    ("attention with CP all-gather", "KV [2 x 4] -> full [8] on both CP ranks (CPManager)", "CP", AMBER),
    ("MoE: dispatch and combine", "own rows to the experts on all 4 ranks and back", "EP", VIOLET),
    ("EPLB counting", "expert_count += received tokens; all-gather each 128 steps", "EP", VIOLET),
    ("last all-gather, sample on driver", "hidden [8, H] on both; only rank 0 and rank 2 sample", "CP", AMBER),
    ("outputs", "driver post-processes; RequestOutput for A", "local", BLUE),
]
P2_H = 72 + len(stops) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y1, P2_H, 2, "What are the stops of the tour?",
        "Each card is one stop. The pill names the group that communicates in that stop.")
cy = y1 + 72
GCOL = {"DP": EMERALD, "CP": AMBER, "EP": VIOLET, "local": BLUE}
for i, (title, row, grp, col) in enumerate(stops):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    label = f"{grp} group" if grp != "local" else "no communication"
    d.pill_auto(1054 - 10 - (len(label) * 11 * 0.602 + 20), cy + 8, label, GCOL[grp][0])
    if i < len(stops) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y1 + P2_H + 22
d.legend(30, y, [(EMERALD, "DP group"), (AMBER, "CP group"), (VIOLET, "EP group"), (BLUE, "one rank, no communication"),
                 (TEAL, "CP driver"), (PINK, "CP follower")])
y += 38
y = d.footnotes(30, y, [
    "H = hidden size (from the checkpoint). Stops 6-7 repeat in every decoder layer; the stop-8 counter grows in each MoE layer.",
    "Engine 1 runs the same stops on a placeholder sequence.",
    "Device numbers assume DEVICE_OFFSET = 0 on one host with 4 devices (examples/_config.py:55-63).",
])
d.save(height=y + 10)
