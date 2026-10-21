/* kv_allocator.js - paged KV cache block allocator simulator (DeepInfer Explained).
 *
 * Mounts into <x-viz id="kv-allocator">. Vanilla JS, no network, seeded and deterministic.
 * Rules copied from DeepInfer at commit 9bd9cf2 (toy sizes: 24 blocks of 4 tokens):
 *   - block 0 is never handed out (csrc/engine/block_manager.hpp:27-35)
 *   - allocate() pops the head of the free list; free() pushes to the tail,
 *     and a block table is freed in reverse order (block_manager.hpp:73-103, 147-149)
 *   - a prefill reserves ceil(tokens / block_size) blocks at once; a waiting queue
 *     head that does not fit blocks the queue (scheduler.hpp:386-396, 516-520)
 *   - a new prefill starts only if cache usage <= 90 %, usage = (num_blocks - free) / num_blocks
 *     (scheduler.hpp:80, 313, 830-835)
 *   - decode: sort running by output length (most first); serve from the end (fewest
 *     output first); while no block is free, preempt from the front (most output);
 *     if only the current request is left, preempt it (scheduler.hpp:622-645)
 *   - preempted: stop (FINISHED_PREEMPTED) or recompute (front of waiting queue)
 *     (scheduler.hpp:766-790)
 * Left out: draft tokens, in-flight tokens, state slots, shared blocks, batch limits, DP.
 */
(function () {
  "use strict";

  var VIZ_ID = "kv-allocator";
  var NUM_BLOCKS = 24;       // physical blocks, including reserved block 0
  var BS = 4;                // tokens per block (DeepInfer: 128)
  var SEED = 20261021;
  var WATERMARK = 0.9;
  var MAX_WAITING = 6;
  var MIN_PROMPT = 3, MAX_PROMPT = 14;

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  var CSS = [
    ".kva-root{font-family:var(--sans);color:var(--ink)}",
    ".kva-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".kva-mode{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center;margin:10px 0 0;padding:0;border:0;font-size:14px}",
    ".kva-mode legend{float:left;padding:0;margin-right:6px;font-weight:600;color:var(--mute)}",
    ".kva-mode label{display:inline-flex;align-items:center;gap:6px;min-height:32px;cursor:pointer}",
    ".kva-mode input{width:18px;height:18px;margin:0;accent-color:var(--blue)}",
    ".kva-stats{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px;padding:0;list-style:none}",
    ".kva-stats li{margin:0;border:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute);line-height:1.3}",
    ".kva-stats b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".kva-stats .kva-warn b{color:var(--amber-text)}",
    ".kva-body{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;margin-top:10px}",
    ".kva-wide .kva-body{grid-template-columns:minmax(0,1.15fr) minmax(0,1fr)}",
    ".kva-h{margin:0 0 6px;font-size:13px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".kva-pool{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:0;padding:0;list-style:none}",
    ".kva-pool6 .kva-pool{grid-template-columns:repeat(6,minmax(0,1fr))}",
    ".kva-blk{margin:0;border:1.5px solid var(--line);border-radius:6px;padding:4px 5px 5px;background:var(--surface);min-width:0}",
    ".kva-blk-top{display:flex;justify-content:space-between;gap:2px;font:600 11.5px/1.3 var(--mono);color:var(--mute);white-space:nowrap;overflow:hidden}",
    ".kva-blk-own{font-weight:700}",
    ".kva-slots{display:grid;grid-template-columns:repeat(4,1fr);gap:2px;margin-top:4px}",
    ".kva-slot{height:14px;border-radius:2px;border:1px solid var(--line);background:var(--cell-empty)}",
    ".kva-blk.kva-res{background:var(--border);border-color:var(--gray-mid)}",
    ".kva-blk.kva-res .kva-slot{visibility:hidden}",
    ".kva-blk.kva-new{outline:2px solid var(--ink);outline-offset:1px}",
    ".kva-slot.kva-full{border-color:transparent}",
    ".kva-slot.kva-waste{background:transparent;border-style:dashed;border-width:1.5px}",
    ".kva-free{margin:8px 0 0;font:12.5px/1.5 var(--mono);color:var(--mute);overflow-wrap:anywhere}",
    ".kva-reqs{margin:0;padding:0;list-style:none;display:grid;gap:6px}",
    ".kva-req{margin:0;border:1px solid var(--border);border-left:5px solid var(--line);border-radius:6px;padding:6px 8px;background:var(--surface);font-size:13.5px;line-height:1.4}",
    ".kva-req.kva-wait{border-style:dashed;border-left-style:solid}",
    ".kva-req-top{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}",
    ".kva-req-name{font:700 14px var(--mono)}",
    ".kva-pill{font:600 11.5px/1.5 var(--mono);border:1px solid var(--line);border-radius:999px;padding:0 7px;color:var(--ink)}",
    ".kva-req-info{color:var(--mute);font-size:13px}",
    ".kva-tab{font:12.5px var(--mono);color:var(--ink);overflow-wrap:anywhere}",
    ".kva-lstrip{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}",
    ".kva-lblk{display:grid;grid-template-columns:repeat(4,9px);gap:1px;padding:2px;border:1px solid var(--line);border-radius:3px}",
    ".kva-lblk span{height:9px;border-radius:1px;background:var(--cell-empty)}",
    ".kva-empty{color:var(--mute);font-size:13.5px;margin:0}",
    ".kva-done{margin:8px 0 0;font-size:13px;color:var(--mute)}",
    ".kva-log{margin:12px 0 0;border-top:1px solid var(--border);padding-top:8px}",
    ".kva-live{margin:0;font-size:14px;font-weight:600;min-height:1.5em}",
    ".kva-hist{margin:4px 0 0;padding-left:18px;font-size:13px;color:var(--mute);max-height:7.5em;overflow:auto}",
    ".kva-hist li{margin:0}",
    ".kva-rule{margin:8px 0 0;font-size:13px;color:var(--mute)}",
    "@media (prefers-reduced-motion: no-preference){.viz-mount[data-viz='kv-allocator'] .kva-blk{transition:background-color .2s,border-color .2s}}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("kva-style")) return;
    var st = document.createElement("style");
    st.id = "kva-style";
    var P = ".viz-mount[data-viz='kv-allocator'] ";
    st.textContent = CSS.split("\n").map(function (r) {
      if (r.charAt(0) !== ".") return r;                 // @media rules are already scoped below
      return r.split("{")[0].split(",").map(function (s) { s = s.trim(); return /^\.kva-(root|wide|pool6)\b/.test(s) ? P.trim() + s : P + s; }).join(",") + "{" + r.split("{").slice(1).join("{");
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function colorOf(req) { return "var(--viz-c" + (((req.id - 1) % 8) + 1) + ")"; }
  function blocksFor(tokens) { return Math.ceil(tokens / BS); }

  function Sim(mount) {
    this.mount = mount;
    this.mode = "recompute";
    this.build();
    this.reset();
  }

  Sim.prototype.reset = function () {
    this.rng = mulberry32(SEED);
    this.blocks = [];
    for (var i = 0; i < NUM_BLOCKS; i++) this.blocks.push({ owner: null, lb: -1 });
    this.free = [];
    for (var k = 1; k < NUM_BLOCKS; k++) this.free.push(k);
    this.reqs = [];          // all requests, by id
    this.running = [];       // in arrival order
    this.waiting = [];       // queue, front first
    this.nextId = 1;
    this.step = 0;
    this.preempted = 0;
    this.fresh = {};
    this.history = [];
    this.done = [];
    this.say("Empty pool: 23 usable blocks of 4 tokens. Block 0 is reserved. Click Add request.");
    this.render();
  };

  // ---- block manager -------------------------------------------------------
  Sim.prototype.alloc = function (req) {
    var b = this.free.shift();                    // head of the free list
    this.blocks[b].owner = req;
    this.blocks[b].lb = req.table.length;
    req.table.push(b);
    this.fresh[b] = true;
    return b;
  };
  Sim.prototype.freeAll = function (req) {
    for (var i = req.table.length - 1; i >= 0; i--) {  // reverse order, push to the tail
      var b = req.table[i];
      this.blocks[b].owner = null;
      this.blocks[b].lb = -1;
      this.free.push(b);
    }
    req.table = [];
  };
  Sim.prototype.usage = function () { return (NUM_BLOCKS - this.free.length) / NUM_BLOCKS; };

  // ---- scheduler -------------------------------------------------------------
  Sim.prototype.tryPrefill = function (msgs) {
    if (!this.waiting.length) return;
    var u = this.usage();
    if (u > WATERMARK) {
      msgs.push("No prefill: cache usage " + Math.round(u * 100) + " % is above 90 %. " + this.waiting[0].name + " waits.");
      return;
    }
    while (this.waiting.length) {
      var r = this.waiting[0];
      var need = blocksFor(r.len);
      if (need >= NUM_BLOCKS) {
        this.waiting.shift();
        r.status = "ignored";
        this.retire(r);
        msgs.push(r.name + " can never fit (" + need + " blocks). It ends as ignored.");
        continue;
      }
      if (need > this.free.length) {
        msgs.push(r.name + " waits: it needs " + need + " blocks, " + this.free.length + " are free.");
        break;
      }
      this.waiting.shift();
      for (var i = 0; i < need; i++) this.alloc(r);
      r.status = "running";
      this.running.push(r);
      msgs.push((r.recompute ? "Recompute " : "Prefill ") + r.name + ": " + r.len + " tokens → blocks [" + r.table.join(", ") + "].");
      r.recompute = false;
    }
  };

  Sim.prototype.preempt = function (r, msgs, why) {
    this.preempted++;
    this.running.splice(this.running.indexOf(r), 1);
    var blocks = r.table.slice();
    this.freeAll(r);
    if (this.mode === "stop") {
      r.status = "stopped";
      this.retire(r);
      msgs.push("Preempt " + r.name + " (" + why + "). It stops: insufficient_system_resource. Blocks [" + blocks.join(", ") + "] are free.");
    } else {
      r.status = "waiting";
      r.recompute = true;
      this.waiting.unshift(r);
      msgs.push("Preempt " + r.name + " (" + why + "). It goes to the front of the queue and must recompute " + r.len + " tokens.");
    }
  };

  Sim.prototype.retire = function (r) {
    this.done = this.done || [];
    this.done.unshift(r);
  };

  Sim.prototype.addRequest = function () {
    var p = MIN_PROMPT + Math.floor(this.rng() * (MAX_PROMPT - MIN_PROMPT + 1));
    var r = { id: this.nextId++, prompt: p, len: p, table: [], status: "waiting", recompute: false };
    r.name = "R" + r.id;
    this.reqs.push(r);
    this.waiting.push(r);
    this.fresh = {};
    var msgs = [r.name + " arrives with a prompt of " + p + " tokens (" + blocksFor(p) + " blocks)."];
    this.tryPrefill(msgs);
    this.finishAction(msgs);
  };

  Sim.prototype.decode = function () {
    var msgs = [];
    this.fresh = {};
    this.tryPrefill(msgs);               // waiting requests start before the decode (toy: one click = prefill + decode)
    if (!this.running.length) { this.finishAction(msgs.concat(["No running request. Add a request first."])); return; }
    this.step++;
    var pre = msgs; msgs = [];
    // sort: most output tokens first; ties: earlier arrival first (std::sort order is not fixed)
    var list = this.running.slice().sort(function (a, b) {
      return (b.len - b.prompt) - (a.len - a.prompt) || a.id - b.id;
    });
    var l = 0, r = list.length, grew = [];
    while (l < r) {
      var seq = list[r - 1];
      while (this.free.length === 0 && r - l > 1) {
        var v = list[l];
        this.preempt(v, msgs, "most output tokens: " + (v.len - v.prompt));
        l++;
      }
      if (this.free.length >= 1) {
        seq.len += 1;
        if (seq.table.length < blocksFor(seq.len)) {
          var b = this.alloc(seq);
          grew.push(b);
          msgs.push(seq.name + " gets new block #" + b + ".");
        }
      } else {
        this.preempt(seq, msgs, "no free block, and no other request is left");
      }
      r--;
    }
    msgs.unshift("Step " + this.step + ": " + this.running.length + " request(s) decode one token" +
      (grew.length ? "." : "; no new block needed."));
    this.finishAction(pre.concat(msgs));
  };

  Sim.prototype.finishOldest = function () {
    if (!this.running.length) { this.finishAction(["No running request to finish."]); return; }
    this.fresh = {};
    var r = this.running.slice().sort(function (a, b) { return a.id - b.id; })[0];
    this.running.splice(this.running.indexOf(r), 1);
    var blocks = r.table.slice();
    this.freeAll(r);
    r.status = "finished";
    this.retire(r);
    var msgs = [r.name + " finishes. Blocks [" + blocks.join(", ") + "] go to the end of the free list (last block first)."];
    this.tryPrefill(msgs);
    this.finishAction(msgs);
  };

  Sim.prototype.finishAction = function (msgs) {
    this.say(msgs.join(" "));
    this.render();
    var self = this;
    this.freshTimer && clearTimeout(this.freshTimer);
    this.freshTimer = setTimeout(function () { self.fresh = {}; self.renderPool(); }, 1600);
  };

  Sim.prototype.say = function (text) {
    this.history.unshift((this.step ? "[step " + this.step + "] " : "") + text);
    if (this.history.length > 30) this.history.pop();
    if (this.live) this.live.textContent = text;
  };

  // ---- view -------------------------------------------------------------------
  Sim.prototype.build = function () {
    var m = this.mount, self = this;
    m.textContent = "";                      // remove the no-JS fallback
    m.classList.add("kva-root");
    var ctr = el("div", "kva-controls");
    function btn(label, cls, fn) {
      var b = el("button", "viz-btn" + (cls ? " " + cls : ""), label);
      b.type = "button";
      b.addEventListener("click", fn);
      ctr.appendChild(b);
      return b;
    }
    this.bAdd = btn("Add request", "viz-btn-primary", function () { self.addRequest(); });
    this.bDec = btn("Decode step", "viz-btn-primary", function () { self.decode(); });
    this.bFin = btn("Finish oldest", "", function () { self.finishOldest(); });
    btn("Reset", "", function () { self.reset(); });
    m.appendChild(ctr);

    var fs = el("fieldset", "kva-mode");
    fs.appendChild(el("legend", null, "When a request is preempted:"));
    [["recompute", "Recompute it later (offline LLM default)"], ["stop", "Stop it (EngineArgs default)"]].forEach(function (o) {
      var lab = el("label");
      var inp = el("input");
      inp.type = "radio"; inp.name = "kva-mode-" + (Sim.count = (Sim.count || 0) + 1); inp.value = o[0];
      inp.checked = o[0] === self.mode;
      inp.addEventListener("change", function () { if (inp.checked) { self.mode = o[0]; self.say("Preemption mode: " + o[1].toLowerCase() + "."); } });
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(o[1]));
      fs.appendChild(lab);
    });
    m.appendChild(fs);

    this.stats = el("ul", "kva-stats");
    this.stats.setAttribute("aria-label", "Counters");
    m.appendChild(this.stats);

    var body = el("div", "kva-body");
    var left = el("div", "kva-poolwrap");
    left.appendChild(el("p", "kva-h", "Physical pool"));
    this.pool = el("ul", "kva-pool");
    this.pool.setAttribute("aria-label", "Physical blocks 0 to 23");
    left.appendChild(this.pool);
    this.freeLine = el("p", "kva-free");
    left.appendChild(this.freeLine);
    var right = el("div", "kva-reqwrap");
    right.appendChild(el("p", "kva-h", "Requests and block tables"));
    this.reqList = el("ul", "kva-reqs");
    right.appendChild(this.reqList);
    this.doneLine = el("p", "kva-done");
    right.appendChild(this.doneLine);
    body.appendChild(left);
    body.appendChild(right);
    m.appendChild(body);

    var log = el("div", "kva-log");
    this.live = el("p", "kva-live");
    this.live.setAttribute("aria-live", "polite");
    this.live.setAttribute("role", "status");
    log.appendChild(this.live);
    var det = el("details");
    det.appendChild(el("summary", null, "Earlier messages"));
    this.hist = el("ol", "kva-hist");
    det.appendChild(this.hist);
    log.appendChild(det);
    log.appendChild(el("p", "kva-rule",
      "Preemption rule (as in DeepInfer's code): a decode step serves the requests with the fewest output tokens first. " +
      "If no block is free, it preempts the request with the most output tokens. Ties: the earlier request goes first."));
    m.appendChild(log);

    var fit = function () {
      var w = m.clientWidth;
      m.classList.toggle("kva-wide", w >= 680);
      var poolW = w >= 680 ? w * 0.52 : w;
      m.classList.toggle("kva-pool6", poolW >= 400);
    };
    fit();
    if (window.ResizeObserver) new ResizeObserver(fit).observe(m);
    else window.addEventListener("resize", fit);
  };

  Sim.prototype.render = function () {
    this.renderStats();
    this.renderPool();
    this.renderReqs();
    this.hist.textContent = "";
    for (var i = 1; i < this.history.length; i++) this.hist.appendChild(el("li", null, this.history[i]));
    this.bDec.disabled = !this.running.length;
    this.bFin.disabled = !this.running.length;
    this.bAdd.disabled = this.waiting.length >= MAX_WAITING;
    this.bAdd.title = this.bAdd.disabled ? "The waiting queue is full in this toy (" + MAX_WAITING + " requests)." : "";
  };

  Sim.prototype.renderStats = function () {
    var used = NUM_BLOCKS - 1 - this.free.length, waste = 0, tokens = 0;
    this.running.forEach(function (r) { waste += r.table.length * BS - r.len; tokens += r.len; });
    var u = Math.round(this.usage() * 100);
    var items = [
      ["Step", String(this.step)],
      ["Used blocks", used + " / 23"],
      ["Free", String(this.free.length)],
      ["Tokens stored", String(tokens)],
      ["Wasted slots", String(waste)],
      ["Cache usage", u + " %", this.usage() > WATERMARK],
      ["Preempted", String(this.preempted), this.preempted > 0]
    ];
    this.stats.textContent = "";
    var s = this.stats;
    items.forEach(function (it) {
      var li = el("li", it[2] ? "kva-warn" : null, it[0]);
      if (it[0] === "Cache usage") li.title = "DeepInfer formula: (all blocks - free) / all blocks, so block 0 counts as used. Prefill needs 90 % or less.";
      li.appendChild(el("b", null, it[1]));
      s.appendChild(li);
    });
  };

  Sim.prototype.renderPool = function () {
    var pool = this.pool, self = this;
    pool.textContent = "";
    this.blocks.forEach(function (blk, k) {
      var li = el("li", "kva-blk");
      var top = el("div", "kva-blk-top");
      top.appendChild(el("span", null, "#" + k));
      var slots = el("div", "kva-slots");
      slots.setAttribute("aria-hidden", "true");
      if (k === 0) {
        li.classList.add("kva-res");
        top.appendChild(el("span", null, "res."));
        li.setAttribute("aria-label", "Block 0: reserved, never used");
        li.title = "Block 0 is reserved: 0 means \"no block\" in DeepInfer";
      } else if (blk.owner) {
        var r = blk.owner, col = colorOf(r);
        var used = Math.max(0, Math.min(BS, r.len - blk.lb * BS));
        var own = el("span", "kva-blk-own", r.name);
        own.style.color = col;
        top.appendChild(own);
        li.style.borderColor = col;
        for (var i = 0; i < BS; i++) {
          var c = el("span", "kva-slot");
          if (i < used) { c.classList.add("kva-full"); c.style.background = col; }
          else { c.classList.add("kva-waste"); c.style.borderColor = col; }
          slots.appendChild(c);
        }
        li.setAttribute("aria-label", "Block " + k + ": " + r.name + ", logical block " + blk.lb + ", " + used + " of " + BS + " slots used");
      } else {
        top.appendChild(el("span", null, "free"));
        li.setAttribute("aria-label", "Block " + k + ": free");
      }
      if (k !== 0 && !blk.owner) for (var j = 0; j < BS; j++) slots.appendChild(el("span", "kva-slot"));
      if (self.fresh[k]) li.classList.add("kva-new");
      li.appendChild(top);
      li.appendChild(slots);
      pool.appendChild(li);
    });
    this.freeLine.textContent = "Free list (next first): " +
      (this.free.length ? this.free.map(function (b) { return "#" + b; }).join(" ") : "empty");
  };

  Sim.prototype.renderReqs = function () {
    var list = this.reqList;
    list.textContent = "";
    var show = this.running.slice().sort(function (a, b) { return a.id - b.id; }).concat(this.waiting);
    if (!show.length) list.appendChild(el("li", "kva-empty", "No requests yet."));
    var waitPos = 0;
    show.forEach(function (r) {
      var li = el("li", "kva-req" + (r.status === "waiting" ? " kva-wait" : ""));
      var col = colorOf(r);
      li.style.borderLeftColor = col;
      var top = el("div", "kva-req-top");
      var nm = el("span", "kva-req-name", r.name);
      nm.style.color = col;
      top.appendChild(nm);
      var st = r.status === "waiting" ? "waiting #" + (++waitPos) + (r.recompute ? ", preempted" : "") : "running";
      top.appendChild(el("span", "kva-pill", st));
      var out = r.len - r.prompt;
      top.appendChild(el("span", "kva-req-info", "prompt " + r.prompt + " + output " + out + " = " + r.len + " tokens"));
      li.appendChild(top);
      if (r.status === "running") {
        li.appendChild(el("div", "kva-tab", "block_table = [" + r.table.join(", ") + "]"));
        var strip = el("div", "kva-lstrip");
        strip.setAttribute("aria-hidden", "true");
        for (var lb = 0; lb < r.table.length; lb++) {
          var g = el("span", "kva-lblk");
          g.style.borderColor = col;
          g.title = "logical block " + lb + " → #" + r.table[lb];
          for (var i = 0; i < BS; i++) {
            var c = el("span");
            if (lb * BS + i < r.len) c.style.background = col;
            g.appendChild(c);
          }
          strip.appendChild(g);
        }
        li.appendChild(strip);
      } else {
        li.appendChild(el("div", "kva-tab", "needs " + blocksFor(r.len) + " blocks to start" + (r.recompute ? " (recompute)" : "")));
      }
      list.appendChild(li);
    });
    var done = (this.done || []).slice(0, 6).map(function (r) {
      return r.name + " " + (r.status === "stopped" ? "stopped (preempted)" : r.status);
    });
    this.doneLine.textContent = done.length ? "Ended: " + done.join(", ") + ((this.done.length > 6) ? ", …" : "") : "";
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    if (!mounts.length) return;
    injectStyle();
    for (var i = 0; i < mounts.length; i++) {
      if (mounts[i].getAttribute("data-viz-ready")) continue;
      mounts[i].setAttribute("data-viz-ready", "1");
      new Sim(mounts[i]);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
