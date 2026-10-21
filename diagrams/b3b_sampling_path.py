"""Diagram: where each SamplingParams field goes, from the Python object to the sampler arrays.

Used by: src/code/sampling-params.html
Sources (commit 9bd9cf2):
  deepinfer/sampling_params.py:47-83       constructor: del logprobs, max_tokens 0 -> 1, seed, verify, temperature clamp
  deepinfer/engine/llm_engine.py:525-537   dict -> SamplingParams; eos_id overwritten; prompt_logprobs off under YOCO
  deepinfer/engine/llm_engine.py:562,607-628  golden_token_ids -> Sequence; so_args -> grammar builder
  csrc/engine/sequence.hpp:92-116          SamplingScalars::capture (9 attributes, once)
  csrc/engine/sequence.hpp:181-191         StoppingCriteria::capture (max_tokens, ignore_eos)
  csrc/engine/sequence.hpp:380             SequenceMetadata copies the scalars each step
  csrc/engine/prepare_sample.cpp:82-88,157-161  per-sequence arrays (float32, int32, uint64)
  csrc/engine/prepare_sample.cpp:192-195,217-219  EOS suppression rows, stop_token_ids
  csrc/engine/scheduler.hpp:1035-1052      _check_stop uses ignore_eos and max_tokens
Example values are made up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "SamplingParams: from Python to the sampler",
    "The C++ sequence copies the numbers once; each step copies them again into flat per-sequence arrays",
    params="R1: temperature 0.6, top_p 0.95, seq_seed 7     R2: temperature 0 (defaults otherwise), no seed",
)

# ============================================================================
# Panel 1: at add_request
# ============================================================================
y0 = 112
P1_H = 254
d.panel(y0, P1_H, 1, "Once per request: what changes, and where each field goes",
        "Some fields change in Python first. Then C++ reads 11 values; so_args and golden_token_ids take other paths.")

d.box(46, y0 + 72, 300, 160, "SamplingParams (Python)", [
    "temperature   top_p   top_k",
    "seq_seed      top_logprobs",
    "prompt_logprobs",
    "first_n_token_no_eos  eos_id",
    "ignore_eos    max_tokens",
    "so_args       golden_token_ids",
    "logprobs  -> deleted",
], col=BLUE, align="start", mono_size=12)
d.text(46, y0 + 246, "LLM deep-copies it per request (llm.py:151)", 11.5, MUTE, italic=True)

d.step_card(380, y0 + 72, 330, 160, 1, "changes in Python", AMBER, rows=[
    ("t<1e-5", "t=1e-5, top_p=1, top_k=-1"),
    ("seed", "None -> random 64 bits"),
    ("max", "0 -> 1"),
    ("eos_id", "= tokenizer EOS (engine)"),
    ("YOCO", "prompt_logprobs -> False"),
    ("check", "else ValueError"),
], key_w=58)

d.arrow(712, y0 + 108, 742, y0 + 108, VIOLET)
d.box(744, y0 + 72, 310, 74, "C++ Sequence, once", [
    "SamplingScalars: 9 values",
    "StoppingCriteria: max_tokens,",
    "                  ignore_eos",
], col=VIOLET, align="start", mono_size=12)
d.arrow(712, y0 + 196, 742, y0 + 196, PINK)
d.box(744, y0 + 158, 310, 74, "other paths", [
    "so_args -> grammar builder",
    "golden_token_ids -> Sequence",
], col=PINK, align="start", mono_size=12)

# ============================================================================
# Panel 2: every step
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 250
d.panel(y1, P2_H, 2, "Every step: one entry per sequence",
        "prepare_sampler_inputs fills pinned CPU arrays, then copies them to the device without a wait.")
rows = [
    ("temperatures", "float32 [n]", "[0.6, 1e-05]"),
    ("top_ps", "float32 [n]", "[0.95, 1.0]"),
    ("top_ks", "int32   [n]", "[-1, -1]"),
    ("seq_seeds", "uint64  [n]", "[7, 1302…(random)]"),
    ("stop_token_ids", "int32 [n, 2]", "[[EOS, -1], [EOS, -1]]  (decode, nextn > 0)"),
    ("max_top_logprobs", "int", "max over the batch: 0"),
]
d.text(46, y1 + 78, "array", 12, MUTE, "bold")
d.text(250, y1 + 78, "type, shape", 12, MUTE, "bold")
d.text(430, y1 + 78, "value for R1, R2 in one decode step", 12, MUTE, "bold")
for i, (a, b, c) in enumerate(rows):
    yy = y1 + 102 + i * 22
    d.text(46, yy, a, 12.5, EMERALD[0], "bold", mono=True)
    d.text(250, yy, b, 12.5, INK, mono=True)
    d.text(430, yy, c, 12.5, INK, mono=True)
d.text(46, y1 + 236, "n = number of sequences in the step (a prefill also has n entries). Prefill adds EOS rows if first_n_token_no_eos == 1.",
       12, MUTE)

y = y1 + P2_H + 24
d.legend(30, y, [(BLUE, "user object"), (AMBER, "changed in Python"), (VIOLET, "C++ copy"), (PINK, "not in C++ scalars"),
                 (EMERALD, "sampler arrays")])
y += 40
y = d.footnotes(30, y, [
    "C++ keeps temperature and top_p as double; prepare_sampler_inputs casts them to float32 (prepare_sample.cpp:158-159).",
    "Later changes to the Python object do not reach the sampler: C++ read the numbers when it made the Sequence.",
])
d.save(height=y + 14)
