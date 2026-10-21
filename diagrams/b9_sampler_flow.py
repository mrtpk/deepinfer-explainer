"""Diagram: Sampler.forward, from hidden states to tokens.

Used by: src/concepts/sampler.html ("The picture")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/layers/sampler.py:140-143      gather rows, get_logits (fp32)
  deepinfer/model_executor/layers/sampler.py:167-169      decode token blacklist -> -inf
  deepinfer/model_executor/layers/sampler.py:183-190      prefill: EOS suppression, SO mask, _prefill_golden_gen
  deepinfer/model_executor/layers/sampler.py:213-251      decode: _verification, then DFlash decode_forward
  deepinfer/model_executor/layers/sampler.py:410-595      _verification
  deepinfer/model_executor/layers/sampler_utils.py:20-28  get_logits: float32 [rows, vocab_size], bf16 GEMM
  deepinfer/model_executor/layers/sampler_utils.py:113-196 process_sampling (force top-k, fused_sample)
  deepinfer/model_executor/layers/tilelang_ops/fused_sample.py:209-246   reference: temperature, top-p, top-k, log-softmax, sample
  deepinfer/model_executor/layers/tilelang_ops/random_sampling.py:70-84  u = hash(seed, 3 * position + case), inverse CDF
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
_box = d.box
d.box = lambda *a, **k: _box(*a, mono_size=12, **k)
W = d.W

d.header(
    "Sampler.forward: from hidden states to tokens",
    "One call per engine step; only the driver rank samples  ·  prefill: 1 row per request  ·  decode: seqlen_q rows per request",
    params="hidden_states [rows_out, hidden] bf16  →  logits float32 [R, vocab_size]  →  token ids int32",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 214
d.panel(y0, P1, 1, "Which rows get logits? Only the rows that need a token",
        "The model returns hidden states. The sampler takes R rows, then makes float32 logits for those rows only.")
by = y0 + 72
bw, bh = 300, 104
xs = [46, 400, 754]
d.box(xs[0], by, bw, bh, "Model output", [
    "hidden_states", "[rows_out, hidden] bf16", "rows_out may include", "CUDA graph padding"], col=BLUE)
d.box(xs[1], by, bw, bh, "gather(selected_token_indices)", [
    "prefill: last row of each prompt", "decode: all seqlen_q rows", "→ [R, hidden]", "sampler.py:141"], col=BLUE)
d.box(xs[2], by, bw, bh, "get_logits", [
    "bf16 GEMM with the LM head", "→ float32 [R, vocab_size]", "blacklist ids → -inf", "sampler.py:142, 169"], col=VIOLET)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, BLUE)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, BLUE)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 398
d.panel(y1, P2, 2, "What happens next? Prefill samples; decode verifies the drafts",
        "Both paths call process_sampling. Only the decode path compares with the drafts of the previous step.")
lx, lw = 46, 492
rx, rw = 562, 492
ly = y1 + 70
d.text(lx, ly, "is_prompt = True  (prefill)", 14, BLUE[0], "bold", mono=True)
d.text(rx, ly, "is_prompt = False  (decode)", 14, PINK[0], "bold", mono=True)
pre = [
    ("1", "EOS suppression", "logits[row, eos_id] = -inf  (first_n_token_no_eos=1)"),
    ("2", "Structured-output mask", "xgrammar bitmask on the rows of SO requests"),
    ("3", "_prefill_golden_gen", "process_sampling → 1 token per request"),
    ("4", "Extras", "top logprobs · golden override · sum_smaller_probs"),
]
dec = [
    ("1", "prepare_verification_metadata", "row_to_req, local_step, is_verify  [total_q]"),
    ("2", "Structured-output masks", "one mask per step: rows ftp + step"),
    ("3", "process_sampling + drafts", "accept min(1, q/p) or sample the residual"),
    ("4", "get_accept_result, finalize", "accepted prefix, sampled token per request"),
    ("5", "DFlash decode_forward", "drafts for the next step (sampler.py:237)"),
]
ch = 52
for i, (n, t, s) in enumerate(pre):
    cy = ly + 16 + i * (ch + 10)
    d.step_card(lx, cy, lw, ch, n, t, BLUE)
    d.text(lx + 38, cy + 40, s, 12, INK, mono=True)
for i, (n, t, s) in enumerate(dec):
    cy = ly + 16 + i * (ch + 10)
    d.step_card(rx, cy, rw, ch, n, t, PINK)
    d.text(rx + 38, cy + 40, s, 12, INK, mono=True)
cy = ly + 16 + 4 * (ch + 10)
d.text(lx + 4, cy + 22, "Result: sampled_token [num_reqs]", 12.5, MUTE, mono=True)
d.text(lx + 4, cy + 40, "sampler.py:171-211", 12, MUTE, mono=True)

# ---------------------------------------------------------------- panel 3
y2 = y1 + P2 + 20
P3 = 262
d.panel(y2, P3, 3, "What does one row go through? The fused_sample kernel",
        "The same kernel serves prefill, decode and the draft model. The reference code shows the order.")
by = y2 + 70
bw3, bh3 = 300, 74
d.box(46, by, bw3, bh3, "1. scale", ["logits / temperature", "temperature ≥ 1e-5"], col=EMERALD)
d.box(400, by, bw3, bh3, "2. filter", ["top-p first, then top-k", "removed tokens → -inf"], col=EMERALD)
d.box(754, by, bw3, bh3, "3. normalize", ["logprobs = log_softmax", "float32 [R, V]"], col=EMERALD)
d.arrow(46 + bw3, by + bh3 / 2, 398, by + bh3 / 2, EMERALD)
d.arrow(400 + bw3, by + bh3 / 2, 752, by + bh3 / 2, EMERALD)
by2 = by + bh3 + 26
d.box(46, by2, 474, 74, "4. sample (fresh row)", [
    "u = hash(seq_seed, 3·position + 0)", "token = first index where CDF > u"], col=EMERALD)
d.box(580, by2, 474, 74, "4'. verify row (decode only)", [
    "accept draft if  q/p > u'  (case 2)", "else sample max(q - p·α, 0)  (case 1)"], col=PINK)
d.path_arrow(f"M {754 + bw3 / 2},{by + bh3} L {754 + bw3 / 2},{by + bh3 + 12} L {283},{by + bh3 + 12} L {283},{by2 - 2}", EMERALD)
d.arrow(817, by + bh3 + 12, 817, by2 - 2, PINK)

y = y2 + P3 + 24
d.legend(30, y, [(BLUE, "prefill path"), (PINK, "decode path (speculative)"), (VIOLET, "matrix multiply"),
                 (EMERALD, "per-row sampling kernel")])
y += 36
y = d.footnotes(30, y, [
    "Not shown: prompt logprobs (computed in chunks of 8192 rows), force top-k remapping, follower ranks of context parallelism.",
    "α = exp(-DRAFT_PROB_PENALTY) = exp(-5e-5). Sources: sampler.py, sampler_utils.py, tilelang_ops/fused_sample.py (commit 9bd9cf2).",
])
d.save(height=y + 10)
