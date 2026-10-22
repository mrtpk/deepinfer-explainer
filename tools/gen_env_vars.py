#!/usr/bin/env python3
"""Generate the variable tables of src/reference/env-vars.html from deepinfer/environ.py.

Owner: the env-var reference writer. Python 3 standard library only.

What the script does:
  1. Parses ../DeepInfer/deepinfer/environ.py with `ast`. For each attribute of class `envs` it gets
     the name, the group (the `# -- Group --` comment above it), the line, the type and the default.
  2. Scans deepinfer/, examples/, tests/ and eval/ (Python, with `ast`) and csrc/ (getenv regex) for
     every use. A read is "import time" when Python evaluates it while it imports the module
     (module or class body, or a default argument of a function).
  3. Merges the scan with the hand-written text in VARS below (what it does, citations, related page).
     It checks that every declared variable has an entry, that every cited line exists, and it warns
     when a cited range does not contain the variable name (review those by hand).
  4. Writes HTML between the markers in src/reference/env-vars.html:
       <!-- BEGIN GENERATED env-tables -->  ...  <!-- END GENERATED env-tables -->
       <!-- BEGIN GENERATED import-time -->  ...  <!-- END GENERATED import-time -->

Usage:
  python3 tools/gen_env_vars.py            # write the page
  python3 tools/gen_env_vars.py --check    # only check; exit 1 if the page is out of date
  python3 tools/gen_env_vars.py --report   # print every use site per variable (for review)
"""
from __future__ import annotations

import ast
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = (ROOT / ".." / "DeepInfer").resolve()
PAGE = ROOT / "src" / "reference" / "env-vars.html"
ENVIRON = "deepinfer/environ.py"
SCAN_DIRS = ("deepinfer", "examples", "tests", "eval", "deep_cluster")

# ---------------------------------------------------------------------------
# Hand-written text (ASD-STE100). One entry per variable in environ.py.
#   does  : one sentence (HTML; inline tags allowed)
#   cites : 1-3 "path:line[-line]" (the main places that read the variable)
#   page  : (page id, short label) of a related page, or None
#   type / default : only for custom EnvVar(...) definitions that the parser cannot describe
# ---------------------------------------------------------------------------
VARS: dict[str, dict] = {
    # -- Platform --
    "DEEPINFER_ACCELERATOR": dict(
        does="Selects the build folder <code>deepinfer/_so/&lt;value&gt;-&lt;arch&gt;/</code> at "
             "<code>import deepinfer</code>. It does not select the Platform class.",
        cites=["deepinfer/__init__.py:15-25", "deepinfer/__init__.py:30-32"],
        # read inside _so_platform_tag(), which the module calls at line 30: the AST rule cannot see this
        import_time=["deepinfer/__init__.py:15"],
        page=("concepts/hardware-platforms", "NVIDIA and Ascend")),
    # -- Runtime --
    "DEEPINFER_COMPUTE_SUM_SMALLER_PROBS": dict(
        does="When on, the sampler also returns <code>sum_smaller_probs</code>: the probability sum of the "
             "sampled token and all tokens that are less probable.",
        cites=["deepinfer/model_executor/layers/sampler.py:104",
               "deepinfer/model_executor/layers/sampler.py:616-622",
               "deepinfer/model_executor/layers/tilelang_ops/sum_smaller_probs.py:14-24"],
        page=("concepts/sampler", "The sampler")),
    "DEEPINFER_JIT_CACHE_DIR": dict(
        does="Root folder for compiled-kernel caches. When set, each worker sets <code>TILELANG_CACHE_DIR</code>, "
             "<code>DG_JIT_CACHE_DIR</code> and <code>EP_JIT_CACHE_DIR</code> to sub-folders of it.",
        cites=["deepinfer/worker/runtime_config.py:45-51"],
        page=("concepts/tilelang-kernels", "TileLang kernels")),
    # -- Distributed Communication --
    "DEEPINFER_NCCL_NUM_SMS": dict(
        does="Sets <code>max_ctas</code> and <code>min_ctas</code> of each NCCL process group. "
             "This sets how many SMs one NCCL operation uses (NVIDIA only).",
        cites=["deepinfer/platform.py:80-82"],
        page=("concepts/hardware-platforms", "NVIDIA and Ascend")),
    "DEEPINFER_USERBUFFER_COMM_SMS": dict(
        does="Number of SMs for DeepEP dispatch and combine. With 0, the code calculates a value when it "
             "makes the EP buffer and writes it back into <code>envs</code>.",
        cites=["deepinfer/model_executor/parallel_utils/userbuffer.py:86-90",
               "deepinfer/model_executor/models/v4_modules/mlp.py:471",
               "deepinfer/model_executor/models/v4_modules/mlp.py:602"],
        page=("concepts/expert-parallelism", "Expert parallelism")),
    "DEEPINFER_GLOO_TIMEOUT": dict(
        type="seconds (float), converted to <code>timedelta</code>",
        default="<code>14400</code> (4 hours)",
        does="Time-out of the default Gloo process group that each worker makes at start-up. Only the default group "
             "uses it: the split groups (also the Gloo DP group of the step votes) get no time-out argument, so the "
             "PyTorch default applies.",
        cites=["deepinfer/worker/base.py:334-340",
               "deepinfer/model_executor/parallel_utils/parallel_state.py:34"],
        page=None),
    "DEEPINFER_REARRANGE_P2P_GROUPS": dict(
        does="Number of buckets for the point-to-point sends and receives that move expert weights in EPLB. "
             "Each bucket is one <code>batch_isend_irecv</code> call.",
        cites=["deepinfer/model_executor/eplb/shuffle.py:114",
               "deepinfer/model_executor/eplb/shuffle.py:135-138"],
        page=("concepts/eplb", "EPLB")),
    # -- MoE & Expert Parallelism --
    "DEEPINFER_OVERRIDE_NUM_EXTRA_EXPERTS": dict(
        does="Lower limit for the number of redundant expert slots. The loader increases it until routed "
             "plus redundant experts divide by the EP size.",
        cites=["deepinfer/model_executor/model_loader.py:122-123",
               "deepinfer/model_executor/eplb/__init__.py:26-28"],
        page=("concepts/eplb", "EPLB")),
    "DEEPINFER_EXPERT_COUNT_WINDOW_SIZE": dict(
        does="Number of past steps of token counts per expert that EPLB keeps. With rearrangement on, it must "
             "be from 1 to the rearrangement interval.",
        cites=["deepinfer/model_executor/eplb/__init__.py:102-119"],
        page=("concepts/eplb", "EPLB")),
    "DEEPINFER_EXPERT_REARRANGEMENT_STEP_INTERVAL": dict(
        does="EPLB moves experts between devices every N steps. The value 0 turns rearrangement off.",
        cites=["deepinfer/model_executor/eplb/__init__.py:103",
               "deepinfer/model_executor/eplb/__init__.py:147-148",
               "deepinfer/model_executor/eplb/__init__.py:161-165"],
        page=("concepts/eplb", "EPLB")),
    "DEEPINFER_REARRANGE_AFTER_PREFILL_IN_NORMAL_ENGINE": dict(
        does="NORMAL engine only. When on, EPLB rearranges at the first decode step after a prefill step. "
             "When off, prefill steps do not count.",
        cites=["deepinfer/model_executor/eplb/__init__.py:83-84",
               "deepinfer/model_executor/eplb/__init__.py:149-159"],
        page=("concepts/eplb", "EPLB")),
    "DEEPINFER_MOE_LB_STAT_INTERVAL": dict(
        does="Every N steps, the EP ranks all-gather their token counts and calculate the MoE load-balance ratio.",
        cites=["deepinfer/model_executor/eplb/__init__.py:125-129",
               "deepinfer/model_executor/eplb/__init__.py:176-193"],
        page=("concepts/eplb", "EPLB")),
    "DEEPINFER_FORCE_IMBALANCE_RATIO": dict(
        does="Profiling setting. With an EP size above 1, a value above 0 replaces MoE routing with random "
             "choices that send more tokens to the first EP rank. The value must then be 1.0 or more (assertion). "
             "The memory profile run sets it to 1.8 and then to 0.0, so a value from the environment never takes effect.",
        cites=["deepinfer/model_executor/models/v4_modules/mlp.py:367-371",
               "deepinfer/worker/model_runner.py:509-512"],
        page=("concepts/moe-routing", "MoE routing")),
    "DEEPINFER_FORCE_LOAD_BALANCE": dict(
        does="Sets <code>gate_force_random</code> for every token. The MoE gate then uses random logits, "
             "so the load on the experts is balanced.",
        cites=["deepinfer/model_executor/model_metadata_utils.py:166",
               "csrc/engine/input_metadata/prepare_tensor_input_base.cpp:85",
               "deepinfer/model_executor/input_metadata/input_metadata.py:48-50"],
        page=("concepts/moe-routing", "MoE routing")),
    "DEEPINFER_SHOW_EPLB_DETAIL": dict(
        does="After each rearrangement, EP rank 0 also logs a table of expert loads for each layer.",
        cites=["deepinfer/model_executor/eplb/__init__.py:327-335"],
        page=("concepts/eplb", "EPLB")),
    # -- Attention --
    "DEEPINFER_PREFILL_MAX_SUM_SEQLEN_K": dict(
        does="Limit for the sum of the sequence lengths in one prefill batch. Unset or 0 sends "
             "<code>2**30</code> to the C++ scheduler, which means no limit.",
        cites=["deepinfer/engine/llm_engine.py:317",
               "csrc/engine/scheduler.hpp:444-449",
               "deepinfer/worker/model_runner.py:417-422"],
        page=("concepts/scheduler", "The scheduler")),
    "DEEPINFER_INDEX_ATTN_MEMORY_LIMIT": dict(
        does="Byte budget for the indexer logits. The indexer splits the work into chunks of "
             "<code>min(8192, limit // row_bytes // 8 * 8)</code> rows.",
        cites=["deepinfer/model_executor/models/v4_modules/index_attn.py:117-118"],
        page=("concepts/sparse-attention-indexer", "Sparse attention")),
    # -- MTP --
    "DEEPINFER_USE_NEXTN_DECODE": dict(
        does="Maximum number of draft tokens for each request in one decode step. The value 0 turns "
             "speculative decoding off. Python and C++ read it separately.",
        cites=["deepinfer/config.py:224",
               "deepinfer/worker/worker.py:74",
               "csrc/engine/utils.hpp:36-40"],
        page=("concepts/speculative-decoding", "Speculative decoding")),
    "DEEPINFER_ENABLE_MTP_VARLEN": dict(
        does="Each request verifies its own number of draft tokens, from the confidence rates. "
             "It also turns on the decode speed profile at start-up.",
        cites=["deepinfer/worker/worker.py:218-219",
               "deepinfer/worker/base.py:280-281",
               "deepinfer/model_executor/input_metadata/prepare_tensor_input_zos.py:93-95"],
        page=("concepts/dspark", "DSpark")),
    "DEEPINFER_MAX_BACKTRACKING_TOKENS": dict(
        type="int (derived)",
        default="<code>max(value, DEEPINFER_USE_NEXTN_DECODE + 1)</code>, so <code>6</code>",
        does="Extra token slots in the sliding-window and compression state rings, so that a request can "
             "go back over rejected draft tokens.",
        cites=["deepinfer/worker/cache_engine.py:93",
               "deepinfer/worker/cache_engine.py:133",
               "deepinfer/model_executor/model_metadata_utils.py:178"],
        page=("concepts/sliding-window-attention", "Sliding-window attention")),
    "DEEPINFER_DFLASH_CONFIDENCE_HEAD_TEMPERATURE": dict(
        type="float, or comma-separated floats",
        default="<code>1.0</code>",
        does="Temperature of the DFlash confidence head: one value for all draft steps, or a list with exactly "
             "<code>DEEPINFER_USE_NEXTN_DECODE</code> values.",
        cites=["deepinfer/model_executor/models/mtp/dflash.py:62-64"],
        page=("concepts/dspark", "DSpark")),
    # -- Model Loading --
    "DEEPINFER_ENGRAM_PAD_TOKEN": dict(
        does="Raw token id that Engram uses as the pad token. After tokenizer compression, the code maps it "
             "through the lookup table.",
        cites=["deepinfer/model_executor/models/v4_modules/engram.py:42",
               "deepinfer/model_executor/models/v4_modules/engram.py:53"],
        page=("concepts/engram", "Engram")),
    "DEEPINFER_ENGRAM_FORCE_GPU_STORAGE": dict(
        type="bool (derived)",
        default="<code>False</code>; always <code>True</code> when <code>DEEPINFER_ACCELERATOR=ascend</code>",
        does="Keeps the Engram tables in device memory, not in CPU memory.",
        cites=["deepinfer/model_executor/models/deepseek.py:473",
               "deepinfer/model_executor/parallel_utils/userbuffer.py:148",
               "deepinfer/worker/runtime_config.py:18-26"],
        page=("concepts/engram", "Engram")),
    # -- Sampling --
    "DEEPINFER_SAMPLER_FORCE_TOPK": dict(
        does="When above 0, the sampler and DFlash keep only the K largest logits of each token for softmax "
             "and sampling. The value 0 uses all tokens.",
        cites=["deepinfer/model_executor/layers/sampler.py:91",
               "deepinfer/model_executor/layers/sampler.py:99",
               "deepinfer/model_executor/models/mtp/dflash.py:102-105"],
        page=("concepts/sampler", "The sampler")),
    "DEEPINFER_DECODE_TOKEN_BLACKLIST": dict(
        does="Token ids, for example <code>0..3,7</code>. The sampler sets their logits to minus infinity "
             "before it samples.",
        cites=["deepinfer/model_executor/layers/sampler.py:108-112",
               "deepinfer/model_executor/layers/sampler.py:168-169",
               "deepinfer/model_executor/utils.py:35"],
        page=("concepts/sampler", "The sampler")),
    # -- CUDA Graph --
    "DEEPINFER_ENFORCE_EAGER": dict(
        does="Turns off CUDA graph capture for the main model. Every decode step then runs in eager mode.",
        cites=["deepinfer/worker/model_runner.py:73"],
        page=("concepts/cuda-graphs", "CUDA graphs")),
    "DEEPINFER_CUDAGRAPH_BATCH_SIZE_INTERVAL": dict(
        does="Spacing of the captured graph batch sizes: powers of two below the interval, then each multiple "
             "of the interval, then the maximum.",
        cites=["deepinfer/worker/cuda_graph_runner.py:74",
               "deepinfer/worker/cuda_graph_runner.py:41-51"],
        page=("concepts/cuda-graphs", "CUDA graphs")),
    "DEEPINFER_DFLASH_ENFORCE_EAGER": dict(
        does="Turns off CUDA graph capture for the DFlash draft model only.",
        cites=["deepinfer/worker/model_runner.py:80-85"],
        page=("concepts/cuda-graphs", "CUDA graphs")),
    "DEEPINFER_DFLASH_CUDAGRAPH_BATCH_SIZE_INTERVAL": dict(
        does="The same spacing rule for the DFlash graphs. Their maximum batch size is <code>max_num_seqs</code>.",
        cites=["deepinfer/worker/dflash_cuda_graph_runner.py:36"],
        page=("concepts/cuda-graphs", "CUDA graphs")),
    "DEEPINFER_DECODE_PERF_CACHE_DIR": dict(
        does="Folder for the cached decode speed curve (milliseconds for each graph batch size). Unset means "
             "no cache: each start measures the curve again.",
        cites=["deepinfer/worker/decode_perf_cache.py:34",
               "deepinfer/worker/decode_perf_cache.py:126-128",
               "deepinfer/worker/model_runner.py:576-579"],
        page=("concepts/dspark", "DSpark")),
    "DEEPINFER_DECODE_PERF_CACHE_TTL_SEC": dict(
        does="Maximum age in seconds of a cached decode speed curve. Files older than this value plus "
             "2 hours are deleted.",
        cites=["deepinfer/worker/decode_perf_cache.py:105",
               "deepinfer/worker/decode_perf_cache.py:138-139"],
        page=None),
    # -- KV Cache Store --
    "DEEPINFER_NUM_STATE_SLOTS_RATIO": dict(
        does="Sets the number of {{term state-slot | state slots}} (one for each active sequence) to "
             "<code>int(max_num_seqs * ratio) + 1</code>.",
        cites=["deepinfer/worker/cache_engine.py:201-202",
               "deepinfer/worker/cache_engine.py:650"],
        page=("concepts/paged-kv-cache", "Paged KV cache")),
    "DEEPINFER_PREFILL_STORE_EXTRA_STATE": dict(
        does="Keeps more sliding-window state after prefill, so that the KV store can save state at its "
             "128-token grain and later turns can hit it.",
        cites=["deepinfer/worker/cache_engine.py:101-110",
               "deepinfer/worker/cache_engine.py:788-790"],
        page=("concepts/sliding-window-attention", "Sliding-window attention")),
    "DEEPINFER_PREFILL_STORE_EXTRA_SIZE": dict(
        does="Number of extra tokens that <code>DEEPINFER_PREFILL_STORE_EXTRA_STATE</code> adds to the "
             "KV-store sliding-window block.",
        cites=["deepinfer/worker/cache_engine.py:108-110"],
        page=None),
    # -- Structured Output --
    "DEEPINFER_XGRAMMAR_DEBUG": dict(
        does="Sends <code>debug_print=True</code> to xgrammar when the matcher accepts a token or fills a "
             "token bitmask.",
        cites=["deepinfer/structure_output/matcher.py:18",
               "deepinfer/structure_output/matcher.py:158",
               "deepinfer/structure_output/matcher.py:193"],
        page=("concepts/structured-outputs", "Structured outputs")),
    "DEEPINFER_XGRAMMAR_TIMEOUT": dict(
        does="Seconds to wait for the xgrammar matcher of a request. After that, the request gets an "
             "aborted matcher.",
        cites=["deepinfer/structure_output/matcher.py:19",
               "deepinfer/structure_output/matcher.py:265",
               "deepinfer/structure_output/matcher.py:305-310"],
        page=("concepts/structured-outputs", "Structured outputs")),
    "DEEPINFER_XGRAMMAR_DISABLE_CACHE": dict(
        does="Turns off the xgrammar compiler cache. The code comment calls it the kill switch.",
        cites=["deepinfer/structure_output/compiler.py:17-18",
               "deepinfer/structure_output/compiler.py:36"],
        page=("concepts/structured-outputs", "Structured outputs")),
    "DEEPINFER_XGRAMMAR_CACHE_LIMIT_BYTES": dict(
        does="Size limit of the xgrammar compiler cache. A value of 0 or less means no limit and logs a "
             "warning.",
        cites=["deepinfer/structure_output/compiler.py:19-29"],
        page=("concepts/structured-outputs", "Structured outputs")),
    "DEEPINFER_SO_BUILDER_CPUS": dict(
        does="Number of CPU cores that build structured-output matchers. <code>get_idle_cpus</code> raises "
             "<code>RuntimeError</code> if the physical cores for each GPU are fewer than this value.",
        cites=["deepinfer/utils.py:157-161",
               "deepinfer/engine/llm_engine.py:334-340"],
        page=("concepts/structured-outputs", "Structured outputs")),
    # -- Scheduling --
    "DEEPINFER_PREFILL_ATTEMPT_INTERVAL": dict(
        does="NORMAL engine. Every N decode steps, the DP ranks vote. They do a prefill step only if all "
             "ranks have prefill work (the ALL point).",
        cites=["deepinfer/config.py:193",
               "csrc/engine/scheduler.hpp:308-318"],
        page=("concepts/dp-step-votes", "DP step votes")),
    "DEEPINFER_PREFILL_ANY_ATTEMPT_INTERVAL": dict(
        does="NORMAL engine. Every N decode steps, the DP ranks do a prefill step if any rank has prefill "
             "work (the ANY point).",
        cites=["deepinfer/config.py:194",
               "csrc/engine/scheduler.hpp:308",
               "csrc/engine/scheduler.hpp:315-316"],
        page=("concepts/dp-step-votes", "DP step votes")),
    "DEEPINFER_ZERO_OVERHEAD_SCHEDULING": dict(
        does="Turns on zero-overhead scheduling (ZOS): the CPU schedules the next step while the device runs. "
             "<code>EngineArgs</code> sets <code>1</code> for NORMAL and COMPLETION engines.",
        cites=["deepinfer/engine/arg_utils.py:51-55",
               "deepinfer/model_executor/model_metadata_utils.py:143",
               "deepinfer/engine/llm_engine.py:313"],
        page=("concepts/zero-overhead-scheduling", "ZOS")),
    # -- Logging --
    "DEEPINFER_LOGGING_INTERVAL_STEP": dict(
        does="Steps between two statistics log lines. The PROMPT engine uses one fifth of it. "
             "A value of 0 or less turns the log off.",
        cites=["deepinfer/engine/stats_logger.py:384-389"],
        page=None),
    "DEEPINFER_NCCL_MEMORY_SAMPLE_INTERVAL_STEPS": dict(
        does="Steps between two samples of NCCL communicator memory. The driver logs a snapshot when the "
             "value changes.",
        cites=["deepinfer/model_executor/parallel_utils/nccl_memory.py:14-21",
               "deepinfer/model_executor/parallel_utils/nccl_memory.py:83"],
        page=None),
    "DEEPINFER_RINGBUFFER_WARNING_INTERVAL": dict(
        does="Seconds between two debug messages while a shared-memory ring buffer waits for a free block.",
        cites=["deepinfer/distributed/shm_broadcast.py:313-315"],
        page=None),
    "DEEPINFER_GC_INTERVAL_STEP": dict(
        does="Steps between two <code>gc.collect()</code> calls in a worker. Automatic garbage collection is off. "
             "COMPLETION engines use 10 times the value.",
        cites=["deepinfer/worker/base.py:102-106",
               "deepinfer/worker/base.py:153-157"],
        page=None),
    # -- YoCo --
    "DEEPINFER_YOCO_PREFILL_TRUNCATION_MODE": dict(
        does="YOCO consumer prefill truncation. <code>mask</code> keeps all queries and narrows the "
             "sliding window. <code>compact</code> removes the truncated queries.",
        cites=["deepinfer/model_executor/model_metadata_utils.py:90-92",
               "deepinfer/model_executor/models/deepseek.py:126-128",
               "deepinfer/engine/llm_engine.py:259-260"],
        page=("concepts/yoco-swa-replay", "YOCO")),
    "DEEPINFER_YOCO_PREFILL_KEEP_TOKENS": dict(
        does="Number of last query tokens that truncation keeps. With truncation on, it must be at least "
             "<code>window_size + DEEPINFER_MAX_BACKTRACKING_TOKENS</code>.",
        cites=["deepinfer/worker/model_runner.py:110-113",
               "deepinfer/model_executor/model_metadata_utils.py:92",
               "deepinfer/engine/llm_engine.py:260"],
        page=("concepts/yoco-swa-replay", "YOCO")),
    # -- Profiling & Debug --
    "DEEPINFER_BATCH_INVARIANT": dict(
        does="Makes model results independent of the batch: batch-invariant attention, deterministic DeepGEMM "
             "and TileKernels. NVIDIA only (asserted on NPU).",
        cites=["deepinfer/worker/runtime_config.py:61-69",
               "deepinfer/model_executor/models/v4_modules/attn.py:666",
               "deepinfer/model_executor/parallel_utils/userbuffer.py:79"],
        page=("concepts/determinism", "Determinism")),
    "DEEPINFER_DISABLE_SYNC_GUARD": dict(
        does="Turns off <code>forbid_cuda_sync</code>, the check that raises on a CPU-GPU synchronization "
             "in model forward and sampling launch. For debug.",
        cites=["deepinfer/utils.py:127-132"],
        page=None),
    "DEEPINFER_PROFILE_TORCH_CUDA_MEMORY": dict(
        does="When set to any value, each worker calls "
             "<code>torch.cuda.memory._record_memory_history(max_entries=100000)</code>. The code does not use "
             "the value.",
        cites=["deepinfer/worker/base.py:110-111"],
        page=None),
    "DEEPINFER_ENABLE_MEMORY_TRACING": dict(
        does="Rank 0 records CUDA memory history in the profile run and writes "
             "<code>./tracing/profile_run_memory_snapshot.pickle</code>.",
        cites=["deepinfer/worker/base.py:223-227"],
        page=None),
    "DEEPINFER_PROFILE_HTTP_ENABLE": dict(
        does="Starts an HTTP server in each engine process. <code>POST /profile</code> records a torch profile "
             "of some steps.",
        cites=["deepinfer/engine/llm_engine.py:237-239",
               "deepinfer/engine/profile_server.py:3-5"],
        page=None),
    "DEEPINFER_PROFILE_HTTP_PORT_BASE": dict(
        does="The profiling server listens on this port plus the driver GPU id.",
        cites=["deepinfer/engine/profile_server.py:117"],
        page=None),
    "DEEPINFER_TORCH_PROFILER_DIR": dict(
        does="Output folder of the profiling server when the request gives no <code>output_dir</code>.",
        cites=["deepinfer/engine/profile_server.py:208"],
        page=None),
    # -- Multi-Modal --
    "DEEPINFER_USE_MULTIMODAL_POOL": dict(
        does="Uses one shared, pinned host-memory pool for multimodal (image) data. <code>EngineArgs</code> "
             "sets <code>1</code> for all engines except COMPLETION.",
        cites=["deepinfer/shared_memory.py:359-363",
               "deepinfer/engine/arg_utils.py:56-60",
               "deepinfer/ve/multimodal_processor.py:49-56"],
        page=("concepts/vision-encoder", "Vision encoder")),
    "DEEPINFER_MULTIMODAL_POOL_SIZE_GB": dict(
        does="Size of the multimodal pool for each rank, in GiB.",
        cites=["deepinfer/shared_memory.py:363"],
        page=("concepts/vision-encoder", "Vision encoder")),
    "DEEPINFER_MULTI_MODAL_BUFFER_SIZE": dict(
        does="Maximum number of items in the output queue of the multimodal preprocessing workers.",
        cites=["deepinfer/ve/multimodal_processor.py:96"],
        page=("concepts/vision-encoder", "Vision encoder")),
    "DEEPINFER_MULTI_MODAL_WORKER_TIMEOUT": dict(
        does="If the multimodal workers have pending requests and give no output for this many seconds, the "
             "process aborts. 0 or less turns the check off.",
        cites=["deepinfer/ve/multimodal_processor.py:266-275"],
        page=("concepts/vision-encoder", "Vision encoder")),
}

# Short labels for the group headings (the comment text in environ.py stays visible in the heading).
GROUP_IDS = {
    "Platform": "g-platform", "Runtime": "g-runtime", "Distributed Communication": "g-distributed",
    "MoE & Expert Parallelism": "g-moe", "Attention": "g-attention", "MTP": "g-mtp",
    "Model Loading": "g-model-loading", "Sampling": "g-sampling", "CUDA Graph": "g-cuda-graph",
    "KV Cache Store": "g-kv-store", "Structured Output": "g-structured-output", "Scheduling": "g-scheduling",
    "Logging": "g-logging", "YoCo": "g-yoco", "Profiling & Debug": "g-profiling", "Multi-Modal": "g-multimodal",
}


# ---------------------------------------------------------------------------
# 1. Parse environ.py
# ---------------------------------------------------------------------------
@dataclass
class Var:
    name: str
    group: str
    line: int
    end_line: int
    type: str = ""
    default: str = ""
    docstring: str | None = None
    doc_line: int | None = None
    reads: list[tuple[str, int, bool]] = field(default_factory=list)   # (path, line, import_time)
    writes: list[tuple[str, int]] = field(default_factory=list)
    cpp: list[tuple[str, int]] = field(default_factory=list)
    env_sets: list[tuple[str, int]] = field(default_factory=list)       # string literal of the name (os.environ, dicts)


def _src(node: ast.AST, text: str) -> str:
    return ast.get_source_segment(text, node) or ""


def _wbr(name: str) -> str:
    """Allow a line break after each underscore of a long variable name."""
    return name.replace("_", "_<wbr>")


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def describe(call: ast.expr, text: str) -> tuple[str, str]:
    """Return (type, default) as HTML for an EnvVar factory call. ('', '') if unknown."""
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == "EnvVar"):
        return "", ""
    kind = call.func.attr
    d = _kw(call, "default")
    dsrc = _src(d, text) if d is not None else None

    def val(expr_src: str, fallback: str) -> str:
        s = expr_src if expr_src is not None else fallback
        out = f"<code>{html.escape(s)}</code>"
        if d is not None and not isinstance(d, ast.Constant):
            v = eval(compile(ast.Expression(d), "<default>", "eval"), {})   # literal arithmetic only
            out += f" = <code>{v}</code>"
            if isinstance(v, int) and v % 2**30 == 0:
                out += f" ({v // 2**30} GiB)"
        return out

    if kind == "int":
        return "int", val(dsrc, "0")
    if kind == "float":
        return "float", val(dsrc, "0.0")
    if kind == "bool":
        return "bool", val(dsrc, "False")
    if kind == "str":
        return "str", val(dsrc, '""')
    if kind == "str_or_none":
        return "str or unset", "<code>None</code> (unset)"
    if kind == "int_or_none":
        return "int or unset", "<code>None</code> (unset)"
    if kind == "choice":
        ch = ast.literal_eval(_kw(call, "choices"))
        return ("one of " + ", ".join(f"<code>{html.escape(c)}</code>" for c in ch)), val(dsrc, "None")
    return "", ""


def parse_environ() -> list[Var]:
    path = REPO / ENVIRON
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "envs")
    out: list[Var] = []
    body = cls.body
    for i, node in enumerate(body):
        name = None
        call = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, call = node.targets[0].id, node.value
        elif isinstance(node, ast.FunctionDef) and any(
                isinstance(dec, ast.Name) and dec.id == "EnvVar" for dec in node.decorator_list):
            name = node.name
        if not name or not name.isupper():
            continue
        # group: nearest "# -- X --" comment above the definition
        group = "?"
        start = node.lineno if not isinstance(node, ast.FunctionDef) else node.decorator_list[0].lineno
        for ln in range(start - 1, 0, -1):
            m = re.match(r"\s*# -- (.+?) --\s*$", lines[ln - 1])
            if m:
                group = m.group(1)
                break
        v = Var(name, group, start, node.end_lineno or start)
        if call is not None:
            v.type, v.default = describe(call, text)
        nxt = body[i + 1] if i + 1 < len(body) else None
        if isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Constant) and isinstance(nxt.value.value, str):
            v.docstring = nxt.value.value
            v.doc_line = nxt.lineno
            v.end_line = nxt.end_lineno or nxt.lineno
        out.append(v)
    return out


# ---------------------------------------------------------------------------
# 2. Scan uses
# ---------------------------------------------------------------------------
def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    par = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            par[c] = p
    return par


def _import_time(node: ast.AST, par: dict[ast.AST, ast.AST]) -> bool:
    """True if Python evaluates `node` while it imports the module."""
    child, p = node, par.get(node)
    while p is not None:
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child in p.body:
                return False          # inside the body: runs when the function is called
        elif isinstance(p, ast.Lambda):
            if child is p.body:
                return False
        elif isinstance(p, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            pass
        child, p = p, par.get(p)
    return True


def scan(vars_: list[Var]) -> None:
    by_name = {v.name: v for v in vars_}
    for d in SCAN_DIRS:
        for f in sorted((REPO / d).rglob("*.py")):
            rel = f.relative_to(REPO).as_posix()
            if rel == ENVIRON:
                continue
            text = f.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            par = _parents(tree)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute) and node.attr in by_name
                        and isinstance(node.value, ast.Name) and node.value.id == "envs"):
                    v = by_name[node.attr]
                    if isinstance(node.ctx, ast.Store):
                        v.writes.append((rel, node.lineno))
                    else:
                        v.reads.append((rel, node.lineno, _import_time(node, par)))
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in by_name:
                    by_name[node.value].env_sets.append((rel, node.lineno))
    for f in sorted((REPO / "csrc").rglob("*")):
        if f.suffix not in (".cpp", ".hpp", ".h", ".cu", ".cc"):
            continue
        rel = f.relative_to(REPO).as_posix()
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in re.finditer(r'getenv\("([A-Z0-9_]+)"\)', line):
                if m.group(1) in by_name:
                    by_name[m.group(1)].cpp.append((rel, i))


# ---------------------------------------------------------------------------
# 3. Check the hand-written data
# ---------------------------------------------------------------------------
def check(vars_: list[Var]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    names = {v.name for v in vars_}
    for n in names - VARS.keys():
        errors.append(f"{n}: declared in environ.py but has no entry in VARS")
    for n in VARS.keys() - names:
        errors.append(f"{n}: entry in VARS but not declared in environ.py")
    for v in vars_:
        e = VARS.get(v.name)
        if not e:
            continue
        if not (v.type or e.get("type")):
            errors.append(f"{v.name}: custom EnvVar; give 'type' and 'default' in VARS")
        if not 1 <= len(e["cites"]) <= 3:
            warnings.append(f"{v.name}: {len(e['cites'])} citations (want 1-3)")
        for c in e["cites"]:
            path, _, rng = c.partition(":")
            p = REPO / path
            if not p.is_file():
                errors.append(f"{v.name}: cite {c}: no such file")
                continue
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            a, _, b = rng.partition("-")
            a, b = int(a), int(b or a)
            if not (1 <= a <= b <= len(lines)):
                errors.append(f"{v.name}: cite {c}: out of range (file has {len(lines)} lines)")
                continue
            chunk = "\n".join(lines[a - 1:b])
            if v.name not in chunk:
                warnings.append(f"{v.name}: cite {c} does not contain the name (check by hand)")
    return errors, warnings


# ---------------------------------------------------------------------------
# 4. HTML
# ---------------------------------------------------------------------------
def short(path: str) -> str:
    """Short link text: the file name (with its folder for __init__.py). The link title keeps the full path."""
    parts = path.split("/")
    if parts[-1] == "__init__.py" and len(parts) > 1:
        return "/".join(parts[-2:])
    return parts[-1]


def cite(c: str) -> str:
    path, _, rng = c.partition(":")
    return f"{{{{cite {c} | <code>{html.escape(short(path))}:{rng}</code>}}}}"


def render_tables(vars_: list[Var]) -> str:
    out: list[str] = []
    groups: list[str] = []
    for v in vars_:
        if v.group not in groups:
            groups.append(v.group)
    for g in groups:
        members = [v for v in vars_ if v.group == g]
        gid = GROUP_IDS.get(g, "g-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-"))
        n = len(members)
        out.append(f'<h3 id="{gid}">{html.escape(g)} ({n})</h3>')
        out.append('<table class="env-table">')
        out.append("  <thead><tr><th>Variable</th><th>What it does, and where the code reads it</th></tr></thead>")
        out.append("  <tbody>")
        for v in members:
            e = VARS[v.name]
            typ = e.get("type") or v.type
            dflt = e.get("default") or v.default
            rng = f"{v.line}" if v.line == v.end_line else f"{v.line}-{v.end_line}"
            first = (f'<code id="{v.name}">{_wbr(v.name)}</code><br>{typ}, default {dflt}<br>'
                     f"defined in {cite(f'{ENVIRON}:{rng}')}")
            does = e["does"]
            if e.get("page"):
                pid, label = e["page"]
                does += f" See {{{{link {pid} | {html.escape(label)}}}}}."
            reads = ", ".join(cite(c) for c in e["cites"])
            second = f"{does}<br>Read in: {reads}."
            if import_sites(v):
                second += " <em>Read at import time.</em>"
            out.append(f"    <tr><td>{first}</td><td>{second}</td></tr>")
        out.append("  </tbody>")
        out.append("</table>")
    return "\n".join(out)


def import_sites(v: Var) -> list[tuple[str, int]]:
    """Reads in deepinfer/ that run at import time (AST rule plus the manual list in VARS)."""
    sites = {(p, ln) for p, ln, it in v.reads if it and p.startswith("deepinfer/")}
    for c in VARS[v.name].get("import_time", []):
        p, _, ln = c.partition(":")
        sites.add((p, int(ln)))
    return sorted(sites)


def render_import_time(vars_: list[Var]) -> str:
    rows = [(v.name, p, ln) for v in vars_ for p, ln in import_sites(v)]
    out = ["<table>", "  <thead><tr><th>Variable</th><th>Read at import in</th></tr></thead>", "  <tbody>"]
    for name, p, ln in rows:
        out.append(f'    <tr><td><a class="cite" href="#{name}"><code>{_wbr(name)}</code></a></td><td>{cite(f"{p}:{ln}")}</td></tr>')
    out += ["  </tbody>", "</table>"]
    return "\n".join(out)


def splice(page: str, marker: str, content: str) -> str:
    pat = re.compile(rf"(<!-- BEGIN GENERATED {marker} -->\n).*?(<!-- END GENERATED {marker} -->)", re.S)
    if not pat.search(page):
        raise SystemExit(f"marker {marker!r} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + content + "\n" + m.group(2), page)


def main() -> int:
    vars_ = parse_environ()
    scan(vars_)
    errors, warnings = check(vars_)
    if "--report" in sys.argv:
        for v in vars_:
            print(f"== {v.name}  [{v.group}] environ.py:{v.line}  type={v.type!r} default={v.default!r}")
            for p, ln, it in v.reads:
                print(f"   read  {p}:{ln}{'  (IMPORT TIME)' if it else ''}")
            for p, ln in v.writes:
                print(f"   write {p}:{ln}")
            for p, ln in v.cpp:
                print(f"   c++   {p}:{ln}")
            for p, ln in v.env_sets:
                print(f"   str   {p}:{ln}")
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    for e in errors:
        print("error:", e, file=sys.stderr)
    if errors:
        return 1
    if "--report" in sys.argv:
        return 0
    page = PAGE.read_text(encoding="utf-8")
    new = splice(page, "env-tables", render_tables(vars_))
    new = splice(new, "import-time", render_import_time(vars_))
    if "--check" in sys.argv:
        if new != page:
            print(f"{PAGE.relative_to(ROOT)} is out of date; run tools/gen_env_vars.py", file=sys.stderr)
            return 1
        print(f"ok: {len(vars_)} variables, page is up to date")
        return 0
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
    print(f"wrote {len(vars_)} variables in {len({v.group for v in vars_})} groups to {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
