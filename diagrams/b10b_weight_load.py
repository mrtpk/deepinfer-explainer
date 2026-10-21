"""Diagram: weight loading, from config.json to the runtime model, and what each EP rank reads.

Used by: src/concepts/weight-loading.html
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/config.py:237-328          load_hf_model_config (checks at 241-262)
  deepinfer/config.py:89-94                          ModelConfig._load_model_cfg (4 runtime fields)
  deepinfer/model_executor/model_loader.py:109-125   finalize_model_config
  deepinfer/model_executor/model_metadata_utils.py:42  ModelMetadata(cfg.gpt)
  deepinfer/model_executor/models/deepseek.py:457-514  load_model order
  deepinfer/hugging_face/loading.py:28-83            prepare_hf_coverage, cover_tied_parameters
  deepinfer/model_executor/model_loader.py:136-153   load_hf_checkpoint
  deepinfer/model_executor/eplb/__init__.py:21-39    extra experts, initial physical->logical map
  deepinfer/hugging_face/weights.py:248-272          local expert ids per EP rank
  deepinfer/model_executor/models/v4_modules/engram_parameters.py:27-39  Engram row_start
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Weight loading: from config.json to the runtime model",
    "Every rank runs these steps itself, from the same HF folder  ·  commit 9bd9cf2",
    params="example in panel 3: 8 logical experts (not from the repo), EP size 3, DEEPINFER_OVERRIDE_NUM_EXTRA_EXPERTS=0",
)

# ---------------------------------------------------------------------------
# Panel 1: config
# ---------------------------------------------------------------------------
y0 = 112
BW, BH, GAP = 316, 168, 30
P1_H = 72 + BH + 24
d.panel(y0, P1_H, 1, "How does config.json become the model config?",
        "The parser checks the format first. Later steps add runtime and parallel fields to the same AttrDict.")
by = y0 + 72
boxes = [
    ("1. load_hf_model_config", VIOLET, [
        "one registered architecture",
        "model_type == deepseek_v41",
        "silu, no bias/dropout, 1 KV, bf16",
        "fp8 + fp4 experts, [32, 32]",
        "  blocks, ue8m0, dynamic",
        "else ValueError",
        "hugging_face/config.py:237-262",
    ]),
    ("2. model_cfg (AttrDict)", BLUE, [
        "architecture, gpt, vl_aligner,",
        "  vision, mlp_projector, dtype",
        "+ ModelConfig: max_num_seqs,",
        "  max_num_batched_tokens, ...",
        "+ finalize_model_config:",
        "  token limits, extra experts",
        "model_loader.py:109-125",
    ]),
    ("3. ModelMetadata(cfg.gpt)", TEAL, [
        "per-layer lists: compress",
        "  ratio, top-k, SWA, indexer",
        "only ratios 0, 1, 2",
        "MoE is required",
        "made again where needed:",
        "  engine, cache, layers",
        "model_metadata_utils.py:42",
    ]),
]
for i, (title, col, lines) in enumerate(boxes):
    bx = 46 + i * (BW + GAP)
    d.rect(bx, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold", mono=True)
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, by + 48 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)
    if i < 2:
        ax = bx + BW
        d.arrow(ax, by + BH / 2, ax + GAP - 2, by + BH / 2, INK)

# ---------------------------------------------------------------------------
# Panel 2: the load steps
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
steps = [
    ("check the files, plan the coverage", "index + shards readable; names -> HFCoverage", "loading.py:28-66", VIOLET),
    ("build every parameter on the meta device", "V41Builder(model_cfg).build_model(): shapes, no memory", "model_loader.py:128-133", BLUE),
    ("tie MTP embedding and head to the backbone", "cover_tied_parameters: target -> source alias", "loading.py:69-83", BLUE),
    ("give each parameter real memory", "cuda; Engram tables on cpu unless forced to the device", "deepseek.py:473-498", BLUE),
    ("load: missing check, shape check, then copy", "3 channels: ordinary, routed experts, Engram tables", "model_loader.py:136-153", EMERALD),
    ("build the runtime model from the containers", "cls.from_model_cfg(gpt, model_cfg)", "deepseek.py:514", TEAL),
]
CARD_H, CARD_GAP = 50, 12
P2_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y1, P2_H, 2, "In which order does DeepseekForCausalLM.load_model work?",
        "The checks run before any weight is read. A missing parameter stops the load with RuntimeError.")
cy = y1 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    pw = len(cite) * 11 * 0.602 + 20
    d.pill(1054 - 10 - pw, cy + 8, pw, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

# ---------------------------------------------------------------------------
# Panel 3: what each EP rank reads
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
BH3 = 150
P3_H = 72 + 40 + BH3 + 24
d.panel(y2, P3_H, 3, "Which experts does each EP rank read?",
        "extra = 0 + (-(8 + 0) % 3) = 1, so 9 physical slots, 3 per rank. The extra slot (extra index 0) copies expert 0 % 8 = 0.")
my = y2 + 72
d.text(46, my + 16, "physical_to_logical = [0, 1, 2, 3, 4, 5, 6, 7, 0]   (eplb/__init__.py:31-39)", 12.5, INK, "bold", mono=True)
by = my + 40
ranks = [
    ("EP rank 0: slots 0-2", ["experts 0, 1, 2", "all ordinary parameters", "its Engram rows only", "  (row_start = rank x part)"]),
    ("EP rank 1: slots 3-5", ["experts 3, 4, 5", "all ordinary parameters", "its Engram rows only", "  (row_start = rank x part)"]),
    ("EP rank 2: slots 6-8", ["experts 6, 7, and 0 again", "all ordinary parameters", "its Engram rows only", "  (row_start = rank x part)"]),
]
for i, (title, lines) in enumerate(ranks):
    bx = 46 + i * (BW + GAP)
    col = AMBER if i == 2 else EMERALD
    d.rect(bx, by, BW, BH3, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0], "bold", mono=True)
    for j, s in enumerate(lines):
        d.text(bx + 14, by + 50 + j * 20, s, 12, INK, mono=True)
d.rect(46 + 2 * (BW + GAP) + 10, by + BH3 - 30, BW - 20, 22, fill=WHITE, stroke=AMBER, rx=6, sw=1.2)
d.text(46 + 2 * (BW + GAP) + BW / 2, by + BH3 - 15, "slot 8 reads expert 0 from the HF files", 11.5, AMBER[0], "bold", "middle", mono=True)

y = y2 + P3_H + 22
d.legend(30, y, [(VIOLET, "checks"), (BLUE, "config / containers"), (EMERALD, "reads weights"),
                 (TEAL, "runtime objects"), (AMBER, "redundant copy")])
y += 38
y = d.footnotes(30, y, [
    "Engram rows follow the Engram group, not the EP group (engram_parameters.py:18-31). The expert count 8 is an example.",
    "Not shown: skip_load (load_format \"dummy\"), which makes dummy weights and reads no file (deepseek.py:488-494).",
])
d.save(height=y + 10)
