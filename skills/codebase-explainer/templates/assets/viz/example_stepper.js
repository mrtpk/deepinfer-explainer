/* example_stepper.js - PATTERN for an interactive visual: a stepper through the stops of a flow.
 *
 * Mounts into <x-viz id="example-stepper">. Vanilla JS, no libraries, no network, deterministic.
 * Copy this file to assets/viz/<name>.js, change VIZ_ID, the CSS prefix (exs-) and STOPS.
 *
 * In a real visual, list here the rules that you copied from the code, with file:line at the pinned
 * commit, and the things that the visual leaves out. Example:
 *   - stop 2: the engine takes the request from the queue (pkg/engine.py:120-131)
 * Left out: errors, retries, threads.
 *
 * Rules (STYLE.md section 10): IIFE scope; prefixed classes scoped under the mount; colours from the
 * site.css custom properties (dark mode works); real <button> elements (min 40 px); keyboard and touch;
 * an aria-live region; works at 390 px width; seeded random numbers; a Reset button.
 */
(function () {
  "use strict";

  var VIZ_ID = "example-stepper";
  var SEED = 20260101;

  // Placeholder stops. Replace with the real stops, each with its file and function.
  var STOPS = [
    { title: "The user calls the API", where: "pkg/api.py · submit()", part: "api" },
    { title: "The engine takes the request", where: "pkg/engine.py · step()", part: "engine" },
    { title: "The engine stores the result", where: "pkg/store.py · put()", part: "store" },
    { title: "The API returns the result", where: "pkg/api.py · result()", part: "api" }
  ];
  var PART_COLOR = { api: "var(--viz-c1)", engine: "var(--viz-c4)", store: "var(--viz-c3)" };

  // Seeded generator (mulberry32): every reader sees the same example values.
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  var CSS = [
    ".exs-root{font-family:var(--sans);color:var(--ink)}",
    ".exs-stops{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px;padding:0;list-style:none}",
    ".exs-stop{min-width:40px;min-height:40px;border:1px solid var(--line);border-radius:6px;background:var(--surface);",
    "  font:600 15px var(--mono);color:var(--ink);cursor:pointer}",
    ".exs-stop[aria-current=step]{border-color:var(--blue);box-shadow:inset 0 -3px 0 var(--blue)}",
    ".exs-card{border-left:4px solid var(--exs-c,var(--line));padding:8px 14px;margin:0 0 12px;background:var(--panel-bg)}",
    ".exs-title{margin:0;font-weight:700;font-size:17px}",
    ".exs-where{margin:4px 0 0;font:13.5px var(--mono);color:var(--mute);overflow-wrap:anywhere}",
    ".exs-val{margin:4px 0 0;font:13.5px var(--mono)}",
    ".exs-ctrl{display:flex;flex-wrap:wrap;gap:8px}",
    ".exs-btn{min-height:40px;padding:0 16px;border:1px solid var(--line);border-radius:6px;background:var(--surface);",
    "  color:var(--ink);font:600 14.5px var(--sans);cursor:pointer}",
    ".exs-btn:disabled{opacity:.45;cursor:default}",
    ".exs-live{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}"
  ].join("\n");

  function injectCss() {
    if (document.getElementById("exs-style")) return;
    var st = document.createElement("style");
    st.id = "exs-style";
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function Viz(mount) {
    this.mount = mount;
    mount.innerHTML = "";                     // removes the .viz-fallback text
    var root = el("div", "exs-root");
    this.list = el("ol", "exs-stops");
    this.card = el("div", "exs-card");
    this.ttl = el("p", "exs-title");
    this.where = el("p", "exs-where");
    this.val = el("p", "exs-val");
    this.card.appendChild(this.ttl); this.card.appendChild(this.where); this.card.appendChild(this.val);
    var ctrl = el("div", "exs-ctrl");
    this.prev = el("button", "exs-btn", "← Previous");
    this.next = el("button", "exs-btn", "Next →");
    var rst = el("button", "exs-btn", "Reset");
    [this.prev, this.next, rst].forEach(function (b) { b.type = "button"; ctrl.appendChild(b); });
    this.live = el("div", "exs-live");
    this.live.setAttribute("aria-live", "polite");
    var self = this;
    this.stopBtns = STOPS.map(function (s, i) {
      var li = el("li");
      var b = el("button", "exs-stop", String(i + 1));
      b.type = "button";
      b.setAttribute("aria-label", "Stop " + (i + 1) + ": " + s.title);
      b.addEventListener("click", function () { self.go(i); });
      li.appendChild(b);
      self.list.appendChild(li);
      return b;
    });
    this.prev.addEventListener("click", function () { self.go(self.i - 1); });
    this.next.addEventListener("click", function () { self.go(self.i + 1); });
    rst.addEventListener("click", function () { self.reset(); });
    root.appendChild(this.list); root.appendChild(this.card); root.appendChild(ctrl); root.appendChild(this.live);
    mount.appendChild(root);
    this.reset(true);
  }

  Viz.prototype.reset = function (quiet) {
    var rnd = mulberry32(SEED);
    this.requestId = 1000 + Math.floor(rnd() * 9000);   // same id for every reader
    this.go(0, quiet);
  };

  Viz.prototype.go = function (i, quiet) {
    if (i < 0 || i >= STOPS.length) return;
    this.i = i;
    var s = STOPS[i];
    this.card.style.setProperty("--exs-c", PART_COLOR[s.part] || "var(--line)");
    this.ttl.textContent = (i + 1) + ". " + s.title;
    this.where.textContent = s.where;
    this.val.textContent = "request id = " + this.requestId;
    this.stopBtns.forEach(function (b, k) {
      if (k === i) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    });
    this.prev.disabled = i === 0;
    this.next.disabled = i === STOPS.length - 1;
    if (!quiet) this.live.textContent = "Stop " + (i + 1) + " of " + STOPS.length + ": " + s.title;
  };

  function init() {
    injectCss();
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    Array.prototype.forEach.call(mounts, function (m) { new Viz(m); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
