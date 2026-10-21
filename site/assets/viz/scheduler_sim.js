/* scheduler_sim.js - step-by-step model of DeepInfer's C++ scheduler (DeepInfer Explained).
 *
 * Mounts into <x-viz id="scheduler-sim">. Vanilla JS, no network, deterministic (seeded).
 * One click on "Next step" = one engine step (one call of Scheduler::schedule plus the
 * result of that step). Rules follow csrc/engine/scheduler.hpp at commit 9bd9cf2:
 *   - step type (NORMAL engine), lines 295-341: a prefill is tried only at an attempt point.
 *     ALL point: decode_step % ALL == 0. ANY point: decode_step != 0 && decode_step % ANY == 0.
 *     "want" = cache usage <= 90 % and a waiting request. If the prefill batch is empty,
 *     the step becomes a decode step (second vote). One DP rank: ALL and ANY votes agree.
 *   - schedule(): a prefill step sets decode_step = 0; a decode step adds 1 (lines 676-681).
 *   - prefill batch, lines 360-546: waiting queue in order; too long -> ignored; blocks for the
 *     WHOLE prompt are taken at the first chunk; LATER (not enough blocks) stops the loop;
 *     at most max_num_seqs sequences (running ones count); a prompt that does not fit in the
 *     rest of the token budget is cut (chunked prefill); a chunk is the last one in the step.
 *   - after a prefill step (process_outputs, lines 940-1020): a full prefill makes the first
 *     output token and goes to running; an unfinished chunk goes to the FRONT of waiting.
 *   - decode batch, lines 559-660: finished sequences leave running; sort running by output
 *     length, most first; serve from the end; while no block is free, preempt from the front;
 *     if only the current sequence is left, preempt it. _append_slot adds a block if needed.
 *   - finished sequences keep their blocks until the next decode step frees them
 *     (free_finished_seqs, then finalize_seq in pre_sampler_sync).
 *   - _preempt, lines 766-790: stop (FINISHED_PREEMPTED) or recompute (front of waiting).
 * Simplified (said on the page): 16 blocks of 4 tokens, 1 token per decode step (no drafts),
 * ZOS off, one DP rank, every request is schedulable at once, no images, ties sorted by id.
 */
(function () {
  "use strict";

  var VIZ_ID = "scheduler-sim";
  var NUM_BLOCKS = 16;      // physical blocks, block 0 is reserved
  var BS = 4;               // tokens per block (DeepInfer: 128)
  var WATERMARK = 0.9;      // GPU_CACHE_PREFILL_WATERMARK, scheduler.hpp:80
  var MAX_MODEL_LEN = 40;   // toy max_model_len
  var MAX_REQS = 8;
  var SEED = 20261021;
  var START = [[9, 6], [6, 10], [18, 5], [5, 12], [7, 4]]; // [prompt tokens, max_tokens]

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function ceilDiv(a, b) { return Math.floor((a + b - 1) / b); }

  // ---------------------------------------------------------------------------
  // Core model (no DOM). cfg: {budget, chunked, allInt, anyInt, maxSeqs, mode}
  // ---------------------------------------------------------------------------
  function Core(cfg) { this.cfg = cfg; this.reset(); }

  Core.prototype.reset = function () {
    this.rng = mulberry32(SEED);
    this.free = [];
    for (var b = 1; b < NUM_BLOCKS; b++) this.free.push(b);
    this.owner = [];
    for (var k = 0; k < NUM_BLOCKS; k++) this.owner.push(null);
    this.reqs = [];
    this.waiting = [];
    this.running = [];
    this.toFree = [];         // finished: blocks are freed at the end of the next decode step
    this.stepNo = 0;
    this.decodeStep = 0;
    this.preempted = 0;
    this.history = [];        // per step: {n, type, tokens, ds}
    this.last = null;
    for (var i = 0; i < START.length; i++) this.addRequest(START[i][0], START[i][1]);
  };

  Core.prototype.addRequest = function (prompt, maxOut) {
    if (this.reqs.length >= MAX_REQS) return null;
    if (prompt == null) {
      prompt = 3 + Math.floor(this.rng() * 14);
      maxOut = 3 + Math.floor(this.rng() * 8);
    }
    var r = { id: this.reqs.length + 1, prompt: prompt, maxOut: maxOut, len: prompt, out: 0,
      cached: 0, table: [], status: "waiting", reason: "", recompute: false, lastQ: 0, lastKind: "" };
    r.name = "R" + r.id;
    this.reqs.push(r);
    this.waiting.push(r);
    return r;
  };

  Core.prototype.usage = function () { return (NUM_BLOCKS - this.free.length) / NUM_BLOCKS; };
  Core.prototype.promptLimit = function () {
    return this.cfg.chunked ? MAX_MODEL_LEN : Math.min(MAX_MODEL_LEN, this.cfg.budget);
  };
  Core.prototype.isAttempt = function (ds) {
    var any = ds !== 0 && ds % this.cfg.anyInt === 0;
    var all = ds % this.cfg.allInt === 0;
    return any ? "ANY" : (all ? "ALL" : "");
  };
  Core.prototype.nextAttempt = function () {
    for (var ds = this.decodeStep; ds < this.decodeStep + 1000; ds++) if (this.isAttempt(ds)) return ds;
    return -1;
  };
  Core.prototype.done = function () { return !this.waiting.length && !this.running.length && !this.toFree.length; };

  Core.prototype.alloc = function (r, n) {
    for (var i = 0; i < n; i++) {
      var b = this.free.shift();            // head of the FIFO free list
      this.owner[b] = r;
      r.table.push(b);
    }
  };
  Core.prototype.freeAll = function (r) {
    for (var i = r.table.length - 1; i >= 0; i--) {  // reverse order, to the tail
      this.owner[r.table[i]] = null;
      this.free.push(r.table[i]);
    }
    r.table = [];
  };

  Core.prototype.schedulePrefill = function (msgs) {
    var c = this.cfg, scheduled = [], ignored = [];
    var numCurr = this.running.length, batched = 0;
    while (this.waiting.length) {
      var s = this.waiting[0];
      var need = 0;
      if (!s.table.length) {
        if (s.len > this.promptLimit()) {
          this.waiting.shift(); s.status = "finished"; s.reason = "prompt_length_exceeded";
          ignored.push(s);
          msgs.push(s.name + " is too long (" + s.len + " > prompt_limit " + this.promptLimit() + "): it ends as FINISHED_IGNORED.");
          continue;
        }
        need = ceilDiv(s.len, BS);
        if (need >= NUM_BLOCKS) {
          this.waiting.shift(); s.status = "finished"; s.reason = "prompt_length_exceeded";
          ignored.push(s);
          msgs.push(s.name + " can never fit (" + need + " blocks): FINISHED_IGNORED.");
          continue;
        }
        if (this.free.length < need) {
          msgs.push(s.name + " needs " + need + " blocks, only " + this.free.length + " are free (LATER): the queue stops.");
          break;
        }
      }
      if (numCurr + 1 > c.maxSeqs) {
        msgs.push(s.name + " waits: " + numCurr + " sequences already hold a slot (max_num_seqs " + c.maxSeqs + ").");
        break;
      }
      var workload = s.len - s.cached, q = workload, remain = c.budget - batched;
      if (workload > remain) q = Math.min(workload, remain);
      if (q === 0) { msgs.push("The token budget is used up."); break; }
      var chunked = q < workload;
      if (chunked && !c.chunked) {
        msgs.push(s.name + " (" + workload + " tokens) does not fit in the " + remain + " tokens left, and chunked prefill is off.");
        break;
      }
      batched += q;
      if (!s.table.length) this.alloc(s, need);
      if (!chunked) { numCurr += 1; }
      s.lastQ = q; s.lastKind = chunked ? "chunk" : (s.cached ? "last chunk" : (s.recompute ? "recompute" : "prompt"));
      scheduled.push(s);
      this.waiting.shift();
      if (chunked) {
        msgs.push(s.name + ": chunk of " + q + " tokens (" + (s.len - s.cached - q) + " left). A chunk ends the batch.");
        break;
      }
    }
    if (!scheduled.length && !ignored.length) return null;
    return { scheduled: scheduled, ignored: ignored, tokens: batched };
  };

  Core.prototype.preempt = function (s, msgs, why) {
    this.preempted += 1;
    var blocks = s.table.length;
    this.freeAll(s);
    if (this.cfg.mode === "stop") {
      s.status = "finished"; s.reason = "insufficient_system_resource";
      msgs.push("Preempt " + s.name + " (" + why + "): it stops, " + blocks + " blocks are free again.");
    } else {
      s.cached = 0; s.status = "waiting"; s.recompute = true;
      this.waiting.unshift(s);
      msgs.push("Preempt " + s.name + " (" + why + "): " + blocks + " blocks are free again; it goes to the front of waiting and must prefill " + s.len + " tokens again.");
    }
  };

  Core.prototype.step = function () {
    if (this.done()) return null;
    var c = this.cfg, msgs = [], i, s;
    this.stepNo += 1;
    this.reqs.forEach(function (r) { r.lastQ = 0; r.lastKind = ""; });
    var ds = this.decodeStep, point = this.isAttempt(ds), res = null, why;
    if (!point) {
      why = "decode_step " + ds + " is not an attempt point";
    } else {
      var u = this.usage();
      var want = u <= WATERMARK && this.waiting.length > 0;
      if (!want) {
        why = "decode_step " + ds + " is an " + point + " point, but " +
          (this.waiting.length ? "cache usage " + Math.round(u * 100) + " % is above 90 %" : "no request waits");
      } else {
        res = this.schedulePrefill(msgs);
        if (!res) why = "decode_step " + ds + " is an " + point + " point, but no request fits (second vote: decode)";
      }
    }
    var info = { n: this.stepNo, ds: ds, point: point, tokens: 0, seqs: [] };
    if (res) {
      info.type = res.scheduled.length ? "prefill" : "empty prefill";
      info.tokens = res.tokens;
      info.why = "decode_step " + ds + " is an " + point + " point and a request fits";
      for (i = 0; i < res.scheduled.length; i++) {
        s = res.scheduled[i];
        info.seqs.push(s);
        s.cached += s.lastQ;
        if (s.cached >= s.len) {
          s.status = "running"; s.recompute = false;
          this.running.push(s);
          s.out += 1; s.len += 1;
          if (s.out >= s.maxOut) { s.status = "finished"; s.reason = "length"; }
        } else {
          s.status = "waiting";
          this.waiting.unshift(s);
        }
      }
      this.decodeStep = 0;
    } else {
      info.type = "decode";
      info.why = why;
      var finished = this.running.filter(function (r) { return r.status === "finished"; });
      this.running = this.running.filter(function (r) { return r.status !== "finished"; });
      var list = this.running.slice().sort(function (a, b) { return (b.out - a.out) || (a.id - b.id); });
      var l = 0, r = list.length, sched = [];
      while (l < r && sched.length < c.maxSeqs) {
        s = list[r - 1];
        while (!this.free.length && r - l > 1) {
          this.preempt(list[l], msgs, "most output tokens: " + list[l].out);
          l += 1;
        }
        if (this.free.length) {
          var needB = ceilDiv(s.len, BS);
          if (s.table.length < needB) {
            this.alloc(s, 1);
            msgs.push(s.name + " gets block #" + s.table[s.table.length - 1] + ".");
          }
          s.lastQ = 1; s.lastKind = "decode";
          sched.push(s);
        } else {
          this.preempt(s, msgs, "no free block and no other sequence left");
        }
        r -= 1;
      }
      this.running = sched;
      for (i = 0; i < sched.length; i++) {
        s = sched[i];
        s.cached = s.len; s.out += 1; s.len += 1;
        if (s.out >= s.maxOut) { s.status = "finished"; s.reason = "length"; }
      }
      info.seqs = sched;
      info.tokens = sched.length;
      if (!sched.length) info.type = "empty decode";
      // pre_sampler_sync of this step: finalize_seq frees the blocks of the sequences
      // that free_finished_seqs took out of running in this step.
      for (i = 0; i < finished.length; i++) {
        var nb = finished[i].table.length;
        this.freeAll(finished[i]);
        finished[i].freed = true;
        msgs.push(finished[i].name + " is finished: its " + nb + " blocks go back to the free list.");
      }
      this.decodeStep = ds + 1;
    }
    info.msgs = msgs;
    this.history.push({ n: info.n, type: info.type, tokens: info.tokens, ds: ds });
    this.last = info;
    return info;
  };

  if (typeof module !== "undefined" && module.exports) module.exports = { Core: Core, NUM_BLOCKS: NUM_BLOCKS, BS: BS };
  if (typeof document === "undefined") return;

  // ---------------------------------------------------------------------------
  // View
  // ---------------------------------------------------------------------------
  var CSS = [
    ".sch-root{font-family:var(--sans);color:var(--ink)}",
    ".sch-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".sch-opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px 12px;margin:12px 0 0;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel-bg)}",
    ".sch-opts label{display:flex;flex-direction:column;gap:3px;font-size:13px;font-weight:600;color:var(--mute)}",
    ".sch-opts select{min-height:36px;font:500 14px var(--sans);color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:4px 6px}",
    ".sch-stats{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px;padding:0;list-style:none}",
    ".sch-stats li{margin:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute);line-height:1.3}",
    ".sch-stats b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".sch-stats .sch-warn b{color:var(--amber-text)}",
    ".sch-h{margin:14px 0 6px;font-size:13px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".sch-now{margin:0;padding:8px 10px;border-left:4px solid var(--line);border-radius:4px;background:var(--panel-bg);font-size:14px}",
    ".sch-now.sch-p{border-left-color:var(--violet)}",
    ".sch-now.sch-d{border-left-color:var(--teal)}",
    ".sch-now b{font-family:var(--mono)}",
    ".sch-budget{display:flex;height:22px;margin-top:8px;border:1px solid var(--line);border-radius:4px;overflow:hidden;background:var(--cell-empty)}",
    ".sch-budget span{display:block;height:100%;border-right:1px solid var(--surface);font:700 11.5px/22px var(--mono);color:#fff;text-align:center;overflow:hidden;white-space:nowrap}",
    ".sch-blabel{margin:3px 0 0;font:12.5px var(--mono);color:var(--mute)}",
    ".sch-time{display:flex;flex-wrap:wrap;gap:3px;margin:0;padding:0;list-style:none}",
    ".sch-time li{margin:0;min-width:30px;padding:2px 3px;border:1px solid var(--line);border-radius:4px;text-align:center;font:600 11.5px/1.35 var(--mono);color:var(--mute);background:var(--surface)}",
    ".sch-time li b{display:block;font-size:13px}",
    ".sch-time .sch-tp{border-color:var(--violet);background:var(--violet-tint)}",
    ".sch-time .sch-tp b{color:var(--violet)}",
    ".sch-time .sch-td b{color:var(--teal)}",
    ".sch-time .sch-te{border-style:dashed}",
    ".sch-time .sch-tnext{border-style:dashed;border-color:var(--violet);color:var(--violet)}",
    ".sch-body{display:grid;grid-template-columns:minmax(0,1fr);gap:4px 18px}",
    ".sch-wide .sch-body{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr)}",
    ".sch-reqs{margin:0;padding:0;list-style:none;display:grid;gap:6px}",
    ".sch-req{margin:0;border:1px solid var(--border);border-left:5px solid var(--line);border-radius:6px;padding:6px 8px;background:var(--surface);font-size:13.5px;line-height:1.4}",
    ".sch-req.sch-in{outline:2px solid var(--ink);outline-offset:1px}",
    ".sch-req.sch-gone{opacity:.62}",
    ".sch-req-top{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}",
    ".sch-name{font:700 14px var(--mono)}",
    ".sch-pill{font:600 11.5px/1.5 var(--mono);border:1px solid var(--line);border-radius:999px;padding:0 7px;color:var(--ink)}",
    ".sch-info{color:var(--mute);font-size:12.5px;font-family:var(--mono)}",
    ".sch-toks{display:flex;flex-wrap:wrap;gap:2px;margin-top:4px}",
    ".sch-tok{width:10px;height:12px;border-radius:2px;border:1.5px solid var(--line);background:var(--surface)}",
    ".sch-tok.sch-o{border-radius:6px}",
    ".sch-tok.sch-future{border-style:dotted}",
    ".sch-legend{margin:6px 0 0;font-size:12.5px;color:var(--mute)}",
    ".sch-pool{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:4px;margin:0;padding:0;list-style:none}",
    ".sch-blk{margin:0;min-width:0;border:1.5px solid var(--line);border-radius:5px;padding:3px 2px;text-align:center;font:600 11.5px/1.3 var(--mono);color:var(--mute);background:var(--surface);overflow:hidden;white-space:nowrap}",
    ".sch-blk.sch-res{background:var(--border);border-color:var(--gray-mid)}",
    ".sch-blk b{display:block;font-size:12px}",
    ".sch-free{margin:6px 0 0;font:12.5px/1.5 var(--mono);color:var(--mute);overflow-wrap:anywhere}",
    ".sch-log{margin:12px 0 0;border-top:1px solid var(--border);padding-top:8px}",
    ".sch-live{margin:0;font-size:14px;min-height:1.5em}",
    ".sch-hist{margin:4px 0 0;padding-left:18px;font-size:13px;color:var(--mute);max-height:9em;overflow:auto}",
    ".sch-hist li{margin:0 0 2px}",
    ".sch-rule{margin:8px 0 0;font-size:13px;color:var(--mute)}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("sch-style")) return;
    var st = document.createElement("style");
    st.id = "sch-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "']";
    st.textContent = CSS.split("\n").map(function (rule) {
      var sel = rule.split("{")[0], body = rule.slice(sel.length);
      return sel.split(",").map(function (x) {
        x = x.trim();
        return /^\.sch-(root|wide)\b/.test(x) ? P + x : P + " " + x;
      }).join(",") + body;
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function colorOf(r) { return "var(--viz-c" + (((r.id - 1) % 8) + 1) + ")"; }

  var OPTS = [
    { key: "budget", label: "Max tokens per step", values: [[8, "8"], [12, "12"], [16, "16"], [24, "24"]], def: 12 },
    { key: "chunked", label: "Chunked prefill", values: [[true, "on"], [false, "off"]], def: true },
    { key: "allInt", label: "ALL attempt interval", values: [[1, "1"], [2, "2"], [3, "3"], [4, "4"], [6, "6"]], def: 3 },
    { key: "anyInt", label: "ANY attempt interval", values: [[4, "4"], [5, "5"], [7, "7"], [10, "10"]], def: 5 },
    { key: "maxSeqs", label: "max_num_seqs", values: [[2, "2"], [3, "3"], [4, "4"]], def: 4 },
    { key: "mode", label: "Preempted request", values: [["recompute", "recompute (LLM)"], ["stop", "stop (EngineArgs)"]], def: "recompute" }
  ];

  function View(mount) {
    var cfg = {};
    OPTS.forEach(function (o) { cfg[o.key] = o.def; });
    this.core = new Core(cfg);
    this.mount = mount;
    this.log = [];
    this.build();
    this.say("Start: 5 requests wait. The pool has 15 usable blocks of 4 tokens. Click Next step.");
    this.render();
  }

  View.prototype.build = function () {
    var m = this.mount, self = this;
    m.textContent = "";
    m.classList.add("sch-root");
    var ctr = el("div", "sch-controls");
    function btn(label, cls, fn) {
      var b = el("button", "viz-btn" + (cls ? " " + cls : ""), label);
      b.type = "button";
      b.addEventListener("click", fn);
      ctr.appendChild(b);
      return b;
    }
    this.bStep = btn("Next step", "viz-btn-primary", function () { self.doStep(); });
    this.bAdd = btn("Add request", "", function () { self.doAdd(); });
    btn("Reset", "", function () { self.core.reset(); self.log = []; self.say("Reset: the same 5 requests wait again. Settings stay as selected."); self.render(); });
    m.appendChild(ctr);

    var opts = el("div", "sch-opts");
    OPTS.forEach(function (o) {
      var lab = el("label", null, o.label);
      var sel = el("select");
      o.values.forEach(function (v, i) {
        var op = el("option", null, v[1]);
        op.value = String(i);
        if (v[0] === o.def) op.selected = true;
        sel.appendChild(op);
      });
      sel.addEventListener("change", function () {
        var v = o.values[+sel.value];
        self.core.cfg[o.key] = v[0];
        self.say(o.label + " is now " + v[1] + ". It applies from the next step.");
        self.render();
      });
      lab.appendChild(sel);
      opts.appendChild(lab);
    });
    m.appendChild(opts);

    this.stats = el("ul", "sch-stats");
    this.stats.setAttribute("aria-label", "Counters");
    m.appendChild(this.stats);

    m.appendChild(el("p", "sch-h", "This step"));
    this.now = el("div", "sch-now");
    m.appendChild(this.now);
    this.budget = el("div", "sch-budget");
    this.budget.setAttribute("aria-hidden", "true");
    m.appendChild(this.budget);
    this.blabel = el("p", "sch-blabel");
    m.appendChild(this.blabel);

    m.appendChild(el("p", "sch-h", "Steps so far (P prefill, D decode; dashed: empty)"));
    this.time = el("ol", "sch-time");
    this.time.setAttribute("aria-label", "Step types so far");
    m.appendChild(this.time);

    var body = el("div", "sch-body");
    var left = el("div");
    left.appendChild(el("p", "sch-h", "Requests"));
    this.reqList = el("ul", "sch-reqs");
    left.appendChild(this.reqList);
    var lg = el("p", "sch-legend", "Squares: prompt tokens (filled = KV cache written). Round: output tokens. Dotted: not made yet.");
    left.appendChild(lg);
    var right = el("div");
    right.appendChild(el("p", "sch-h", "KV blocks (4 tokens each)"));
    this.pool = el("ul", "sch-pool");
    this.pool.setAttribute("aria-label", "KV blocks 0 to 15");
    right.appendChild(this.pool);
    this.freeLine = el("p", "sch-free");
    right.appendChild(this.freeLine);
    body.appendChild(left);
    body.appendChild(right);
    m.appendChild(body);

    var log = el("div", "sch-log");
    this.live = el("p", "sch-live");
    this.live.setAttribute("aria-live", "polite");
    this.live.setAttribute("role", "status");
    log.appendChild(this.live);
    var det = el("details");
    det.appendChild(el("summary", null, "Earlier steps"));
    this.hist = el("ol", "sch-hist");
    det.appendChild(this.hist);
    log.appendChild(det);
    log.appendChild(el("p", "sch-rule",
      "Rules from scheduler.hpp: a prefill can start only at an attempt point (decode_step % ALL = 0, or decode_step % ANY = 0). " +
      "Prefill and decode never share a step. Decode serves the fewest output tokens first and preempts the most output tokens first."));
    m.appendChild(log);

    var fit = function () { m.classList.toggle("sch-wide", m.clientWidth >= 700); };
    fit();
    if (window.ResizeObserver) new ResizeObserver(fit).observe(m);
    else window.addEventListener("resize", fit);
  };

  View.prototype.say = function (text) {
    this.log.unshift(text);
    if (this.log.length > 40) this.log.pop();
    this.live.textContent = text;
  };

  View.prototype.doStep = function () {
    var info = this.core.step();
    if (!info) { this.say("All requests are done. Add a request or Reset."); this.render(); return; }
    var names = info.seqs.map(function (s) { return s.name + (s.lastKind === "chunk" ? " (chunk " + s.lastQ + ")" : ""); });
    var head = "Step " + info.n + ": " + info.type.toUpperCase() + ", " + info.tokens + " token" + (info.tokens === 1 ? "" : "s") +
      (names.length ? " (" + names.join(", ") + ")" : "") + ". Why: " + info.why + ".";
    this.say([head].concat(info.msgs).join(" "));
    this.render();
  };

  View.prototype.doAdd = function () {
    var r = this.core.addRequest();
    if (!r) { this.say("This toy stops at " + MAX_REQS + " requests."); }
    else {
      var na = this.core.nextAttempt();
      this.say(r.name + " arrives: prompt " + r.prompt + " tokens, max_tokens " + r.maxOut +
        ". It waits for the next attempt point (decode_step " + na + ").");
    }
    this.render();
  };

  View.prototype.render = function () {
    var c = this.core, self = this;
    // counters
    var used = NUM_BLOCKS - 1 - c.free.length, u = c.usage();
    var na = c.nextAttempt();
    var items = [
      ["Step", String(c.stepNo)],
      ["decode_step", String(c.decodeStep)],
      ["Next attempt point", na === c.decodeStep ? "now" : "in " + (na - c.decodeStep)],
      ["Waiting", String(c.waiting.length)],
      ["Blocks used", used + " / 15"],
      ["Cache usage", Math.round(u * 100) + " %", u > WATERMARK],
      ["Preempted", String(c.preempted), c.preempted > 0]
    ];
    this.stats.textContent = "";
    items.forEach(function (it) {
      var li = el("li", it[2] ? "sch-warn" : null, it[0]);
      li.appendChild(el("b", null, it[1]));
      self.stats.appendChild(li);
    });
    // this step
    var L = c.last;
    this.now.className = "sch-now" + (L ? (L.type.indexOf("prefill") >= 0 ? " sch-p" : " sch-d") : "");
    this.now.textContent = "";
    if (!L) {
      this.now.appendChild(document.createTextNode("No step yet. decode_step is 0, so the first step is an ALL attempt point."));
    } else {
      var b = el("b", null, L.type.toUpperCase());
      this.now.appendChild(document.createTextNode("Step " + L.n + ": "));
      this.now.appendChild(b);
      this.now.appendChild(document.createTextNode(" because " + L.why + "." + (c.done() ? " All requests are done: add a request or press Reset." : "")));
    }
    // budget bar
    this.budget.textContent = "";
    var cap = c.cfg.budget;
    if (L) {
      L.seqs.forEach(function (s) {
        var seg = el("span", null, s.name);
        seg.style.width = (100 * s.lastQ / Math.max(cap, L.tokens)) + "%";
        seg.style.background = colorOf(s);
        self.budget.appendChild(seg);
      });
    }
    this.blabel.textContent = L ? ("Tokens in step " + L.n + ": " + L.tokens + " of max " + cap +
      (L.type.indexOf("decode") >= 0 ? " (decode: 1 token per sequence in this toy; DeepInfer sends 1 + 5 drafts)" : "")) :
      ("Token budget per step: " + cap + " (max_num_batched_tokens)");
    // timeline
    this.time.textContent = "";
    var hs = c.history.slice(-28);
    hs.forEach(function (h) {
      var cls = h.type === "prefill" ? "sch-tp" : (h.type === "decode" ? "sch-td" : "sch-te");
      if (h.type === "empty prefill") cls = "sch-tp sch-te";
      var li = el("li", cls);
      li.appendChild(el("b", null, h.type.indexOf("prefill") >= 0 ? "P" : "D"));
      li.appendChild(document.createTextNode(String(h.n)));
      li.title = "step " + h.n + ": " + h.type + ", " + h.tokens + " tokens, decode_step was " + h.ds;
      li.setAttribute("aria-label", li.title);
      self.time.appendChild(li);
    });
    if (!c.done()) {
      var nx = el("li", "sch-tnext");
      var pt = c.isAttempt(c.decodeStep);
      nx.appendChild(el("b", null, pt ? "?" : "D"));
      nx.appendChild(document.createTextNode(String(c.stepNo + 1)));
      nx.title = pt ? "next step: " + pt + " attempt point" : "next step: decode (no attempt point)";
      nx.setAttribute("aria-label", nx.title);
      this.time.appendChild(nx);
    }
    // requests
    this.reqList.textContent = "";
    var inStep = {};
    if (L) L.seqs.forEach(function (s) { inStep[s.id] = true; });
    var wpos = {};
    c.waiting.forEach(function (r, i) { wpos[r.id] = i + 1; });
    c.reqs.forEach(function (r) {
      var gone = r.status === "finished" && r.freed;
      var li = el("li", "sch-req" + (inStep[r.id] ? " sch-in" : "") + ((r.status === "finished" && !r.table.length) ? " sch-gone" : ""));
      var col = colorOf(r);
      li.style.borderLeftColor = col;
      var top = el("div", "sch-req-top");
      var nm = el("span", "sch-name", r.name);
      nm.style.color = col;
      top.appendChild(nm);
      var st;
      if (r.status === "waiting") st = "waiting #" + wpos[r.id] + (r.cached ? ", chunked" : "") + (r.recompute ? ", preempted" : "");
      else if (r.status === "running") st = "running";
      else st = "finished: " + r.reason + (r.table.length ? " (blocks held)" : "");
      top.appendChild(el("span", "sch-pill", st));
      var promptDone = Math.min(r.cached, r.prompt);
      top.appendChild(el("span", "sch-info", "prompt " + r.prompt + " · output " + r.out + "/" + r.maxOut +
        " · blocks " + r.table.length + (inStep[r.id] ? " · this step +" + r.lastQ : "")));
      li.appendChild(top);
      var toks = el("div", "sch-toks");
      toks.setAttribute("aria-hidden", "true");
      for (var i = 0; i < r.prompt + r.maxOut; i++) {
        var t = el("span", "sch-tok" + (i >= r.prompt ? " sch-o" : ""));
        if (i < r.len) {
          t.style.borderColor = col;
          if (i < r.cached || i >= r.prompt) t.style.background = col;
        } else t.classList.add("sch-future");
        toks.appendChild(t);
      }
      li.appendChild(toks);
      li.setAttribute("aria-label", r.name + ": " + st + ", prompt " + r.prompt + " tokens, " + promptDone +
        " in the KV cache, output " + r.out + " of " + r.maxOut + ", " + r.table.length + " blocks");
      self.reqList.appendChild(li);
      void gone;
    });
    // pool
    this.pool.textContent = "";
    for (var k = 0; k < NUM_BLOCKS; k++) {
      var o = c.owner[k];
      var blk = el("li", "sch-blk" + (k === 0 ? " sch-res" : ""));
      blk.appendChild(el("span", null, "#" + k));
      var lab = el("b", null, k === 0 ? "res." : (o ? o.name : "free"));
      if (o) { lab.style.color = colorOf(o); blk.style.borderColor = colorOf(o); }
      blk.appendChild(lab);
      blk.setAttribute("aria-label", "Block " + k + ": " + (k === 0 ? "reserved" : (o ? o.name : "free")));
      this.pool.appendChild(blk);
    }
    this.freeLine.textContent = "Free list (next first): " + (c.free.length ? c.free.map(function (x) { return "#" + x; }).join(" ") : "empty");
    // history
    this.hist.textContent = "";
    for (var j = 1; j < this.log.length; j++) this.hist.appendChild(el("li", null, this.log[j]));
    this.bStep.disabled = c.done();
    this.bAdd.disabled = c.reqs.length >= MAX_REQS;
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    if (!mounts.length) return;
    injectStyle();
    for (var i = 0; i < mounts.length; i++) {
      if (mounts[i].getAttribute("data-viz-ready")) continue;
      mounts[i].setAttribute("data-viz-ready", "1");
      new View(mounts[i]);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
