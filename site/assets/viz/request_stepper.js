/* request_stepper.js - step through the 13 stops of Tour 1 "Life of a request" (DeepInfer Explained).
 *
 * Mounts into <x-viz id="request-stepper">. Vanilla JS, no network, no randomness.
 * All values are the illustrative values of the "What the data looks like now" blocks
 * of src/tours/life-of-a-request.html (request "1" of examples/offline_inference.py).
 * "Read stop N" links to the section ids #stop-1 ... #stop-13 that build.py makes for <x-stop>.
 */
(function () {
  "use strict";

  var VIZ_ID = "request-stepper";
  var LANES = [
    { key: "py", name: "Python" },
    { key: "cpp", name: "C++ engine" },
    { key: "dev", name: "device" }
  ];

  var STOPS = [
    {
      title: "The user script starts the engine and calls generate()",
      lanes: ["py"],
      where: "examples/offline_inference.py, _config.create_llm, _launch.run_dp",
      says: "The launcher starts one process per DP rank. Each process sets its visible devices, makes the LLM object and calls generate().",
      data: [
        "# in the process of dp_rank 0",
        "os.environ[\"CUDA_VISIBLE_DEVICES\"] == \"0\"   # one device per process when cp = 1",
        "prompts          # 5 strings; prompts[1] is our request",
        "sampling_params  # 5 SamplingParams; sampling_params[1].seq_seed == 1",
        "multi_modal_data # 5 dicts; ours is {\"image_bytes\": [], \"image_sizes\": []}"
      ]
    },
    {
      title: "The public API: LLM.generate() and _add_request()",
      lanes: ["py"],
      where: "deepinfer/entrypoints/llm.py: LLM.generate, _add_request",
      says: "generate() adds one request per prompt. The request id is a counter, so our request is \"1\". The engine gets a copy of the sampling parameters.",
      data: [
        "request_id        = \"1\"",
        "sampling_params   = SamplingParams(temperature=0.4, top_p=1.0, top_k=-1,",
        "                      max_tokens=128, first_n_token_no_eos=1,",
        "                      top_logprobs=4, seq_seed=1)   # a copy",
        "prompt_token_ids  = np.array([0, 15823, 25, 3085, ..., 25],",
        "                             dtype=np.int32)       # shape (41,)",
        "multi_modal_data  = {\"image_bytes\": [], \"image_sizes\": []}"
      ]
    },
    {
      title: "Tokenization: text becomes token ids",
      lanes: ["py"],
      where: "deepinfer/hugging_face/tokenizer.py: get_hf_tokenizer",
      says: "The tokenizer cuts the text into tokens and gives each token an integer id. BOS (id 0) is always first.",
      data: [
        "tokenizer.encode(prompt)",
        "# [0, 15823, 25, 3085, 344, 270, 7426, ..., 6233, 25]   41 ids",
        "#  ^ BOS                               \"Answer\" \":\"",
        "tokenizer.eos_token_id   # 1",
        "tokenizer.pad_token_id   # 2"
      ]
    },
    {
      title: "Admission: LLMEngine.add_request() makes a C++ Sequence",
      lanes: ["py", "cpp"],
      where: "deepinfer/engine/llm_engine.py: add_request",
      says: "The engine checks the ids, makes a C++ Sequence and puts it in the waiting queue. It is not schedulable yet: the multimodal worker must answer first.",
      data: [
        "Sequence  # C++, held by std::shared_ptr",
        "  request.seq_id          = 1",
        "  request.request_id      = \"1\"",
        "  input.tokens            = SequenceData(token_ids=[0, 15823, ..., 25], prompt_len=41)",
        "  generation.sampling     = {temperature: 0.4, top_p: 1.0, top_k: -1, seq_seed: 1,",
        "                             top_logprobs: 4, first_n_token_no_eos: 1, eos_id: 1}",
        "  generation.stopping     = {max_tokens: 128, ignore_eos: False}",
        "  cache                   = {block_size: 128, num_tokens: 0, block_table: [], state_id: -1}",
        "  mtp.last_output_token   = 25",
        "  schedule.status         = WAITING",
        "  schedule.schedulable    = False",
        "Scheduler.waiting = deque([seq \"0\", seq \"1\", seq \"2\", seq \"3\", seq \"4\"])"
      ]
    },
    {
      title: "Scheduling in C++: which requests run in this step",
      lanes: ["cpp"],
      where: "csrc/engine/scheduler.hpp: _schedule",
      says: "The scheduler selects a prefill step. Requests \"0\" to \"3\" fit. max_num_seqs is 4, so request \"4\" waits. Our request gets one KV block and one state slot.",
      table: {
        head: ["seq", "tokens", "block_table", "state_id", "status"],
        rows: [
          ["\"0\"", "..", "[1]", "..", "RUNNING"],
          ["\"1\"", "41", "[2]", "2", "RUNNING", true],
          ["\"2\"", "..", "..", "..", "RUNNING"],
          ["\"3\"", "..", "..", "..", "RUNNING"],
          ["\"4\"", "..", "[]", "-1", "WAITING"]
        ]
      },
      data: [
        "SchedulerOutputs:",
        "  prompt_run = True,  scheduled_seqs = [seq \"0\", seq \"1\", seq \"2\", seq \"3\"]",
        "  seqlens_q  = [.., 41, .., ..],  num_batched_tokens = sum(seqlens_q)",
        "seq \"1\": mtp.info_slot = 2   # one row group in the draft-token pool"
      ]
    },
    {
      title: "Batch metadata: from sequences to tensors",
      lanes: ["cpp", "py"],
      where: "Scheduler::schedule, prepare_tensor_input_v4.cpp, ModelRunner._prepare_input",
      says: "The batch becomes flat tensors with one row per query token. Offset arrays mark where each request starts. Here our request is shown alone.",
      data: [
        "SequenceMetadata(request_id=\"1\", is_prompt=True, seqlen_q=41, seqlen_k=41,",
        "                 block_table=[2], state_id=2, last_output_token=25)",
        "total_q          = 41",
        "positions        int32 [41]  = [0, 1, 2, ..., 40]",
        "input_ids        int32 [41]  = [0, 15823, 25, ..., 25]",
        "cu_seqlens_q     int32 [2]   = [0, 41]",
        "cu_seqlens_k     int32 [2]   = [0, 41]",
        "slot_mapping_store_swa    int32 [41] = [268, 269, ..., 308]  # 2 * 134 + position",
        "slot_mapping_store_ca[\"2\"] int32 [20] = [128, 129, ..., 147]  # block 2 * 64 + index",
        "state_block_idx  int32 [1]   = [2]"
      ]
    },
    {
      title: "The worker step: forward N, post-process N-1, sample N",
      lanes: ["py"],
      where: "deepinfer/worker/worker.py: execute_model_step",
      says: "The worker starts forward N, post-processes step N-1, then starts the sampler of step N. With ZOS, a decode step is post-processed in the next step.",
      data: [
        "self.prev_step_state = WorkerStepState(      # None after a prefill step",
        "    seq_metadata_list=[...], scheduler_outputs=...,",
        "    sampler_output=SamplerOutput(...), is_prompt=False,",
        "    is_placeholder=False, sample_end_evt=torch.cuda.Event(), graph_size=8)",
        "request_outputs = np.array([140231233421312, ...],",
        "                           dtype=np.uint64)  # pointers to C++ objects"
      ]
    },
    {
      title: "The forward pass: the model runs on the device",
      lanes: ["dev"],
      where: "ModelRunner.execute_main_model, DeepseekModel.forward",
      says: "A prefill step runs the model directly. A decode step replays a CUDA graph. One decode request with 6 tokens uses the graph of size 8.",
      data: [
        "prefill:  hidden_states  [41, hidden_size]   # one row per prompt token",
        "decode:   hidden_states  [8, hidden_size]    # graph size 8: 6 real rows + 2 padding rows"
      ]
    },
    {
      title: "The KV cache: what this step writes",
      lanes: ["dev"],
      where: "deepinfer/worker/cache_engine.py, slot maps from stop 6",
      says: "The attention kernels write the KV cache at the slots of stop 6. Compressed entries go to block 2. Sliding-window entries go to the ring of state slot 2.",
      data: [
        "ca_cache[ratio 2]   block 2, rows 0..19      # 20 compressed entries for positions 0..39",
        "swa_cache           state slot 2, rows 0..40  # ring rows = position % 134",
        "ca_state            state slot 2              # the half-done pair: position 40 waits for 41",
        "Sequence \"1\": cache.num_tokens = 41  (set in stop 12)"
      ]
    },
    {
      title: "Sampling: the sampler selects the next token",
      lanes: ["dev"],
      where: "deepinfer/model_executor/layers/sampler.py: Sampler.forward",
      says: "The sampler computes logits only for the last prompt row. EOS is forbidden for the first token. It samples one token with temperature 0.4.",
      data: [
        "logits                       float32 [1, vocab_size]  # our row only; vocab_size 129280 inferred",
        "sampled_token.token_ids      int32   [1] = [14200]     # \" William\"",
        "sampled_token.token_logprobs float32 [1] = [-0.02]",
        "topk_tokens.logps / tokens   [1, 4]                    # top_logprobs = 4",
        "next_n_token_ids             None                      # no drafts in a prefill step"
      ]
    },
    {
      title: "Draft tokens: DFlash guesses the next tokens",
      lanes: ["dev"],
      where: "deepinfer/model_executor/models/mtp/dflash.py",
      says: "In decode steps, DFlash guesses 5 draft tokens. After a prefill step there are no drafts, so the engine uses 5 placeholder ids.",
      data: [
        "# after the prefill step: no drafts; the engine pads (stop 12)",
        "seq.mtp.draft_tokens = [129279, 129279, 129279, 129279, 129279]",
        "                       # vocab_size - 1 (vocab_size 129280 inferred)",
        "# after a decode step:",
        "predict_tokens.token_ids        int32   [1, 5] = [[41813, 198, 198, 21265, 25]]",
        "predict_tokens.confidence_rates float32 [1, 5] or None"
      ]
    },
    {
      title: "Output assembly: the engine updates the sequence and builds outputs",
      lanes: ["py", "cpp"],
      where: "LLMEngine._process_model_outputs, outputs.hpp",
      says: "The C++ engine appends the new token, checks the stop conditions and makes one RequestOutput per new token.",
      data: [
        "Sequence \"1\":",
        "  input.tokens.token_ids = [0, 15823, ..., 25, 14200]   # 42 ids, prompt_len 41",
        "  cache.num_tokens       = 41",
        "  mtp.last_output_token  = 14200",
        "  scheduler.running      = [..., seq \"1\", ...]",
        "RequestOutput(request_id=\"1\", prompt_len=41, token_id=14200, finished=False,",
        "              finish_reason=\"\", token_logprobs=-0.02, top_logprobs=[4 floats],",
        "              top_token_ids=[4 ids], num_output_tokens=1, draft_tok=1, accept_tok=1)"
      ]
    },
    {
      title: "Back to the user: tokens and text",
      lanes: ["py"],
      where: "deepinfer/entrypoints/llm.py: LLM._run_engine",
      says: "The loop calls step() until all requests finish. It clones each output. The example script decodes the text itself.",
      data: [
        "outputs[1]                          # list of RequestOutput, one per token, up to 128",
        "[x.token_id for x in outputs[1]]    # [14200, 41813, 198, 198, 21265, 25, ...]",
        "outputs[1][-1].finished             # True",
        "outputs[1][-1].finish_reason        # \"length\" (128 tokens) or \"stop\" (EOS id 1)",
        "tokenizer.decode(ids)               # \" William Shakespeare\\n\\nQuestion: ...\""
      ]
    }
  ];

  var CSS = [
    ".rqs-root{font-family:var(--sans);color:var(--ink)}",
    ".rqs-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".rqs-count{font:600 14px var(--mono);color:var(--mute);margin-left:4px}",
    ".rqs-list{display:grid;grid-template-columns:repeat(13,minmax(0,1fr));gap:4px;margin:12px 0 0;padding:0;list-style:none}",
    ".rqs-list li{margin:0;padding:0}",
    ".rqs-num{width:100%;min-width:0;min-height:40px;padding:4px 0;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink);font:600 14px var(--mono);cursor:pointer;touch-action:manipulation}",
    ".rqs-num:hover{border-color:var(--gray-mid);background:var(--panel-bg)}",
    ".rqs-num[aria-current='step']{border:2px solid var(--blue);background:var(--blue-tint);color:var(--blue)}",
    ".rqs-num.rqs-seen{color:var(--mute)}",
    ".rqs-card{margin-top:14px;border-top:1px solid var(--border);padding-top:12px}",
    ".rqs-title{margin:0 0 8px;font-size:17px;font-weight:700;color:var(--ink-strong,var(--ink));line-height:1.35}",
    ".rqs-title span{font-family:var(--mono);color:var(--blue);margin-right:6px}",
    ".rqs-lanes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:0 0 10px;padding:0;list-style:none}",
    ".rqs-lane{margin:0;border:1px dashed var(--line);border-radius:6px;padding:5px 8px;font-size:13.5px;color:var(--mute);background:var(--surface);line-height:1.3;min-width:0}",
    ".rqs-lane b{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}",
    ".rqs-lane.rqs-on{border-style:solid;border-width:2px;color:var(--ink);font-weight:600}",
    ".rqs-lane.rqs-on b{color:inherit}",
    ".rqs-on.rqs-py{border-color:var(--blue);background:var(--blue-tint)}",
    ".rqs-on.rqs-cpp{border-color:var(--violet);background:var(--violet-tint)}",
    ".rqs-on.rqs-dev{border-color:var(--emerald);background:var(--emerald-tint)}",
    ".rqs-where{margin:0 0 6px;font-size:14px;color:var(--mute)}",
    ".rqs-where code{font:13px var(--mono);color:var(--ink);overflow-wrap:anywhere}",
    ".rqs-says{margin:0 0 10px;font-size:15px}",
    ".rqs-h{margin:10px 0 4px;font-size:12.5px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".rqs-pre{margin:0;padding:10px 12px;border-radius:6px;background:var(--code-bg,var(--panel-bg));border:1px solid var(--border);font:12.5px/1.55 var(--mono);color:var(--ink);overflow-x:auto;white-space:pre;max-width:100%}",
    ".rqs-tablewrap{overflow-x:auto;max-width:100%;margin:0 0 8px}",
    ".rqs-table{border-collapse:collapse;font:13px var(--mono);min-width:100%}",
    ".rqs-table th,.rqs-table td{border:1px solid var(--border);padding:3px 8px;text-align:left;white-space:nowrap}",
    ".rqs-table th{font-family:var(--sans);font-weight:600;color:var(--mute);background:var(--panel-bg)}",
    ".rqs-table tr.rqs-ours td{background:var(--blue-tint);font-weight:700}",
    ".rqs-foot{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;margin-top:10px;font-size:14px}",
    ".rqs-foot a{font-weight:600}",
    ".rqs-note{color:var(--mute);font-size:13px}",
    ".rqs-live{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}",
    "@media (max-width:560px){.rqs-list{grid-template-columns:repeat(7,minmax(0,1fr))}.rqs-lane{padding:4px 6px;font-size:12.5px}.rqs-title{font-size:16px}}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("rqs-style")) return;
    var st = document.createElement("style");
    st.id = "rqs-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "'] ";
    st.textContent = CSS.split("\n").map(function (r) {
      if (r.charAt(0) === "@") {
        return r.replace(/\{\.rqs-/g, "{" + P + ".rqs-").replace(/\}\.rqs-/g, "}" + P + ".rqs-");
      }
      return r.split("{")[0].split(",").map(function (s) { return P + s.trim(); }).join(",") + "{" + r.split("{").slice(1).join("{");
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function Stepper(mount) {
    this.mount = mount;
    this.cur = 0;
    this.seen = {};
    this.build();
    this.show(0, false);
  }

  Stepper.prototype.build = function () {
    var self = this;
    var m = this.mount;
    m.innerHTML = "";
    var root = el("div", "rqs-root");

    var ctl = el("div", "rqs-controls");
    this.prev = el("button", "viz-btn", "← Prev");
    this.next = el("button", "viz-btn viz-btn-primary", "Next →");
    this.reset = el("button", "viz-btn", "Reset");
    [this.prev, this.next, this.reset].forEach(function (b) { b.type = "button"; ctl.appendChild(b); });
    this.count = el("span", "rqs-count");
    ctl.appendChild(this.count);
    root.appendChild(ctl);

    this.prev.addEventListener("click", function () { self.go(self.cur - 1); });
    this.next.addEventListener("click", function () { self.go(self.cur + 1); });
    this.reset.addEventListener("click", function () { self.seen = {}; self.go(0); });

    var list = el("ol", "rqs-list");
    list.setAttribute("aria-label", "Stops of the tour");
    this.nums = STOPS.map(function (s, i) {
      var li = el("li");
      var b = el("button", "rqs-num", String(i + 1));
      b.type = "button";
      b.setAttribute("aria-label", "Stop " + (i + 1) + ": " + s.title);
      b.title = s.title;
      b.addEventListener("click", function () { self.go(i); });
      li.appendChild(b);
      list.appendChild(li);
      return b;
    });
    root.appendChild(list);

    this.card = el("div", "rqs-card");
    root.appendChild(this.card);

    this.live = el("p", "rqs-live");
    this.live.setAttribute("aria-live", "polite");
    root.appendChild(this.live);

    root.addEventListener("keydown", function (ev) {
      var t = ev.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (ev.key === "ArrowRight") { self.go(self.cur + 1, true); ev.preventDefault(); }
      else if (ev.key === "ArrowLeft") { self.go(self.cur - 1, true); ev.preventDefault(); }
    });

    m.appendChild(root);
  };

  Stepper.prototype.go = function (i, focusNum) {
    if (i < 0 || i >= STOPS.length) return;
    this.show(i, true);
    if (focusNum && document.activeElement && document.activeElement.classList.contains("rqs-num")) this.nums[i].focus();
  };

  Stepper.prototype.show = function (i, announce) {
    var s = STOPS[i];
    this.seen[this.cur] = true;
    this.cur = i;
    this.prev.disabled = i === 0;
    this.next.disabled = i === STOPS.length - 1;
    this.count.textContent = "Stop " + (i + 1) + " of " + STOPS.length;
    var self = this;
    this.nums.forEach(function (b, k) {
      if (k === i) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
      b.classList.toggle("rqs-seen", k !== i && !!self.seen[k]);
    });

    var c = this.card;
    c.innerHTML = "";
    var h = el("h3", "rqs-title");
    h.appendChild(el("span", null, String(i + 1)));
    h.appendChild(document.createTextNode(s.title));
    c.appendChild(h);

    var lanes = el("ul", "rqs-lanes");
    lanes.setAttribute("aria-label", "Where the code runs");
    LANES.forEach(function (L) {
      var on = s.lanes.indexOf(L.key) >= 0;
      var li = el("li", "rqs-lane rqs-" + L.key + (on ? " rqs-on" : ""));
      li.appendChild(el("b", null, on ? "active" : "idle"));
      li.appendChild(document.createTextNode(L.name));
      lanes.appendChild(li);
    });
    c.appendChild(lanes);

    var w = el("p", "rqs-where");
    w.appendChild(document.createTextNode("Where: "));
    w.appendChild(el("code", null, s.where));
    c.appendChild(w);
    c.appendChild(el("p", "rqs-says", s.says));

    if (s.table) {
      c.appendChild(el("p", "rqs-h", "The batch of this step"));
      var wrap = el("div", "rqs-tablewrap");
      var t = el("table", "rqs-table");
      var thead = el("thead"), tr = el("tr");
      s.table.head.forEach(function (x) { tr.appendChild(el("th", null, x)); });
      thead.appendChild(tr); t.appendChild(thead);
      var tb = el("tbody");
      s.table.rows.forEach(function (r) {
        var row = el("tr", r[5] ? "rqs-ours" : null);
        for (var k = 0; k < 5; k++) row.appendChild(el("td", null, r[k]));
        tb.appendChild(row);
      });
      t.appendChild(tb); wrap.appendChild(t); c.appendChild(wrap);
    }

    c.appendChild(el("p", "rqs-h", "What the data looks like now (illustrative)"));
    var pre = el("pre", "rqs-pre");
    pre.setAttribute("tabindex", "0");
    pre.setAttribute("aria-label", "Data at stop " + (i + 1));
    pre.textContent = s.data.join("\n");
    c.appendChild(pre);

    var foot = el("div", "rqs-foot");
    var a = el("a", null, "Read stop " + (i + 1) + " ↓");
    a.href = "#stop-" + (i + 1);
    foot.appendChild(a);
    foot.appendChild(el("span", "rqs-note", "Simplified: one request, values as in the text."));
    c.appendChild(foot);

    if (announce) this.live.textContent = "Stop " + (i + 1) + " of " + STOPS.length + ": " + s.title;
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    if (!mounts.length) return;
    injectStyle();
    for (var i = 0; i < mounts.length; i++) new Stepper(mounts[i]);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
