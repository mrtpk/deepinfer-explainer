"""Diagram: DP replicas vote on the step type; why the type must match on all replicas.

Used by: src/concepts/dp-step-votes.html
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:295-341          _schedule NORMAL branch: attempt points, vote 1 (ALL / ANY), vote 2, empty prompt step
  csrc/engine/scheduler.hpp:170-182          _dp_allreduce over dp_group
  deepinfer/engine/llm_engine.py:665-679     has_unfinished_requests: all-reduce MAX over the DP group
  deepinfer/engine/llm_engine.py:961-975     is_placeholder = scheduler_outputs.is_empty()
  deepinfer/worker/worker.py:121-127         placeholder: run the model on one dummy sequence
  deepinfer/model_executor/models/v4_modules/mlp.py:461-511, 565-616   dispatch / combine over the EP group per MoE layer
  deepinfer/model_executor/models/v4_modules/mlp.py:476                token limit: prefill vs decode
  deepinfer/model_executor/layers/sampler.py:145-161, 225-248          decode only: DFlash draft layers (with MoE)
  deepinfer/model_executor/eplb/__init__.py:131-138, 167-190           EPLB step every step; all-gather every 128 steps
Example: --ep 4 --cp 1, so dp = 4 and the EP group is the world group (examples/offline_inference.py:24-28,
parallel_state.py:102-103). Defaults: ALL every 70, ANY every 100 (environ.py:174-177).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "DP replicas vote, then all run the same kind of step",
    "NORMAL engine  ·  4 data-parallel replicas (--ep 4 --cp 1)  ·  default attempt intervals  ·  commit 9bd9cf2",
    params="ALL point: decode_step % 70 == 0   ANY point: decode_step % 100 == 0 (not 0)   vote = all-reduce MIN over the DP group",
)

# ---------------------------------------------------------------------------
# Panel 1: a timeline of steps on 4 replicas
# ---------------------------------------------------------------------------
y0 = 112
cols = [
    ("69", "", ["D", "D", "D", "d"]),
    ("70", "ALL", ["D", "D", "D", "d"]),
    ("71", "", ["D", "D", "D", "d"]),
    ("99", "", ["D", "D", "D", "d"]),
    ("100", "ANY", ["P", "P", "P", "p"]),
    ("0", "ALL", ["D", "D", "D", "d"]),
]
ROWS = 4
CW, CH, CG = 104, 40, 8
LX = 210
top = y0 + 112
P1_H = (top - y0) + ROWS * (CH + CG) + 112
d.panel(y0, P1_H, 1, "What does each replica run?",
        "Replicas 0-2 run sequences and have waiting requests. Replica 3 has no work. Each column is one step, on all replicas.")

d.text(46, top - 34, "decode_step", 12.5, MUTE, "bold", mono=True)
d.text(46, top - 14, "point", 12.5, MUTE, "bold", mono=True)
for c, (ds, kind, _) in enumerate(cols):
    x = LX + c * (CW + CG)
    d.text(x + CW / 2, top - 34, ds, 13, INK, "bold", "middle", mono=True)
    if kind:
        col = AMBER if kind == "ALL" else PINK
        d.pill(x + CW / 2 - 24, top - 28, 48, kind, col)
    if c == 2:
        d.text(x + CW + CG / 2, top - 34, "...", 14, MUTE, "bold", "middle")
STYLE = {
    "D": (BLUE, "decode"),
    "P": (EMERALD, "prefill"),
    "p": (NEUTRAL, "empty prefill"),
    "d": (NEUTRAL, "empty decode"),
}
for r in range(ROWS):
    y = top + r * (CH + CG)
    d.text(46, y + 25, f"replica {r} (rank {r})", 13, INK, "bold")
    for c, (_, _, cells) in enumerate(cols):
        x = LX + c * (CW + CG)
        code = cells[r]
        col, label = STYLE[code]
        dash = "4 3" if code in "pd" else None
        d.rect(x, y, CW, CH, fill=col[1], stroke=col, rx=6, sw=1.3, dash=dash)
        d.text(x + CW / 2, y + 25, label, 12, col[0] if code not in "pd" else MUTE, "bold", "middle")

ny = top + ROWS * (CH + CG) + 10
notes = [
    "70 (ALL): replicas 0-2 send 1, replica 3 sends 0. MIN = 0, so nobody prefills.",
    "100 (ANY): replicas 0-2 send 0, replica 3 sends 1. MIN = 0, so all prefill; replica 3 runs an empty prompt step.",
    "0 (ALL, right after a prefill): replica 0 still has work, the others do not. Vote 1 fails, so all decode.",
]
for i, s in enumerate(notes):
    d.text(46, ny + 18 + i * 20, s, 12.5, INK)
d.text(46, ny + 18 + 3 * 20, "Grey dashed cell: a placeholder step (one dummy sequence). The replica still runs every collective.",
       12, MUTE, italic=True)

# ---------------------------------------------------------------------------
# Panel 2: why the type must match
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
BX_W = 494
BX_H = 196
P2_H = 72 + BX_H + 60
d.panel(y1, P2_H, 2, "Why must the step type match?",
        "The EP group holds all 4 replicas. The two step types call different device collectives.")
for i, (title, col, lines) in enumerate((
    ("prefill step (is_prompt = True)", EMERALD, [
        "per MoE layer: dispatch + combine (EP)",
        "  token limit max_num_prefilling_tokens",
        "with CP > 1: CP all-gathers per layer",
        "no draft model",
        "eager forward (no CUDA graph)",
        "sampler: prefill path",
        "EPLB step(is_prompt=True)",
    ]),
    ("decode step (is_prompt = False)", BLUE, [
        "per MoE layer: dispatch + combine (EP)",
        "  token limit max_num_decoding_tokens",
        "no CP all-gather",
        "draft model: more MoE layers (DFlash)",
        "CUDA graph replay when graphs exist",
        "sampler: verification path",
        "EPLB step(is_prompt=False)",
    ]),
)):
    bx = 46 + i * (BX_W + 20)
    by = y1 + 72
    d.rect(bx, by, BX_W, BX_H, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold")
    for j, s in enumerate(lines):
        d.text(bx + 14, by + 50 + j * 20, s, 12.5, INK, mono=True)
d.callout(46, y1 + 72 + BX_H + 14, 1008, "Rule:",
          "a collective finishes only when every rank of the group calls it. Different call lists on two replicas make them wait.",
          VIOLET)

y = y1 + P2_H + 22
d.legend(30, y, [(BLUE, "decode step"), (EMERALD, "prefill step"), (NEUTRAL, "placeholder step"),
                 (AMBER, "ALL point"), (PINK, "ANY point")])
y += 38
y = d.footnotes(30, y, [
    "Vote 2 (did any replica schedule a batch?) and the per-step MAX vote of has_unfinished_requests are not drawn.",
    "With ZOS on (the default), the votes use the Gloo copy of the DP group, on the CPU (llm_engine.py:313).",
    "Panel 2 lists differences in the code (mlp.py:476, sampler.py:156 and 237, model_runner.py:182). The rule is general collective behaviour.",
])
d.save(height=y + 10)
