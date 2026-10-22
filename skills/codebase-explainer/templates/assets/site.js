/* Codebase explainer site - site behaviour (vanilla JS, no dependencies).
   Features: sidebar drawer, theme toggle, search, glossary tooltips, quiz,
   code copy, deep-dive expand/collapse, diagram lightbox, TOC highlight. */
(function () {
  "use strict";
  var doc = document;
  var body = doc.body;
  var root = body.getAttribute("data-root") || "";

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }
  function store(key, val) {
    try {
      if (val === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, val);
    } catch (e) { return null; }
    return null;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- sidebar drawer ---------- */
  var menuBtn = $(".menu-btn");
  var scrim = $(".scrim");
  function setNav(open) {
    body.classList.toggle("nav-open", open);
    if (menuBtn) menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (scrim) scrim.hidden = !open;
  }
  if (menuBtn) menuBtn.addEventListener("click", function () { setNav(!body.classList.contains("nav-open")); });
  if (scrim) scrim.addEventListener("click", function () { setNav(false); });
  var cur = $(".sidebar a.current");
  if (cur && cur.scrollIntoView) {
    var sb = $(".sidebar");
    if (sb) sb.scrollTop = Math.max(0, cur.offsetTop - sb.clientHeight / 3);
  }

  /* ---------- theme toggle ---------- */
  var themeBtn = $(".theme-btn");
  function effectiveTheme() {
    var t = doc.documentElement.getAttribute("data-theme");
    // Light is the default for everyone; dark only when the reader chose it.
    return t === "dark" ? "dark" : "light";
  }
  if (themeBtn) themeBtn.addEventListener("click", function () {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    if (next === "dark") doc.documentElement.setAttribute("data-theme", "dark");
    else doc.documentElement.removeAttribute("data-theme");
    store("explainer-theme", next);
  });

  /* ---------- search ---------- */
  var input = $("#search-input");
  var results = $("#search-results");
  var selected = -1;
  function words(q) { return q.toLowerCase().split(/\s+/).filter(Boolean); }
  function score(entry, ws) {
    var t = entry.t.toLowerCase(), s = (entry.s || "").toLowerCase();
    var h = (entry.h || []).join(" \u0001 ").toLowerCase();
    var a = (entry.a || []).join(" ").toLowerCase();
    var total = 0;
    for (var i = 0; i < ws.length; i++) {
      var w = ws[i], sc = 0;
      if (t.indexOf(w) === 0) sc = 12;
      else if (t.indexOf(w) >= 0) sc = 9;
      else if (a.indexOf(w) >= 0) sc = 7;
      else if (h.indexOf(w) >= 0) sc = 4;
      else if (s.indexOf(w) >= 0) sc = 2;
      if (!sc) return 0;
      total += sc;
    }
    if (entry.k === "term") total += 1;
    return total;
  }
  function mark(text, ws) {
    var out = escapeHtml(text);
    ws.forEach(function (w) {
      var re = new RegExp("(" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }
  function runSearch() {
    var q = input.value.trim();
    var index = window.EXPLAINER_SEARCH_INDEX || [];
    if (!q) { results.hidden = true; results.innerHTML = ""; return; }
    var ws = words(q);
    var hits = [];
    index.forEach(function (e) { var sc = score(e, ws); if (sc) hits.push([sc, e]); });
    hits.sort(function (x, y) { return y[0] - x[0] || x[1].t.localeCompare(y[1].t); });
    hits = hits.slice(0, 12);
    selected = hits.length ? 0 : -1;
    if (!hits.length) {
      results.innerHTML = '<p class="sr-empty">No results for “' + escapeHtml(q) + '”.' +
        (index.length ? "" : " (The search index did not load.)") + "</p>";
    } else {
      results.innerHTML = hits.map(function (hit, i) {
        var e = hit[1];
        var kind = e.k === "term" ? "Glossary" : (e.sec || "");
        return '<a role="option" href="' + escapeHtml(root + e.u) + '"' + (i === 0 ? ' aria-selected="true"' : "") + ">" +
          '<span class="sr-top"><span class="sr-title">' + mark(e.t, ws) + '</span><span class="sr-kind">' + escapeHtml(kind) + "</span></span>" +
          '<span class="sr-sum">' + mark(e.s || "", ws) + "</span></a>";
      }).join("");
    }
    results.hidden = false;
  }
  function moveSel(d) {
    var items = $$("a", results);
    if (!items.length) return;
    selected = (selected + d + items.length) % items.length;
    items.forEach(function (a, i) { a.setAttribute("aria-selected", i === selected ? "true" : "false"); });
    items[selected].scrollIntoView({ block: "nearest" });
  }
  if (input && results) {
    input.addEventListener("input", runSearch);
    input.addEventListener("focus", function () { if (input.value.trim()) runSearch(); });
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown") { ev.preventDefault(); moveSel(1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); moveSel(-1); }
      else if (ev.key === "Enter") {
        var items = $$("a", results);
        if (items[selected]) { ev.preventDefault(); window.location.href = items[selected].getAttribute("href"); }
      } else if (ev.key === "Escape") { input.value = ""; results.hidden = true; input.blur(); }
    });
    doc.addEventListener("click", function (ev) {
      if (!ev.target.closest(".search")) results.hidden = true;
    });
  }
  doc.addEventListener("keydown", function (ev) {
    var tag = (ev.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "textarea" || ev.target.isContentEditable;
    if (ev.key === "/" && !typing && input) { ev.preventDefault(); input.focus(); input.select(); }
    if (ev.key === "Escape") { setNav(false); closeLightbox(); hideTip(); }
  });

  /* ---------- glossary tooltips ---------- */
  var tip = $("#term-tooltip");
  var tipFor = null;
  var lastPointer = "mouse";
  function showTip(el) {
    if (!tip) return;
    tipFor = el;
    tip.innerHTML = "<strong>" + escapeHtml(el.getAttribute("data-term")) + "</strong>" + escapeHtml(el.getAttribute("data-def")) +
      (lastPointer === "touch" ? '<span class="tt-hint">Tap again to open the glossary.</span>' : "");
    tip.hidden = false;
    var r = el.getBoundingClientRect();
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left), window.innerWidth - tw - 8);
    var y = r.bottom + 8;
    if (y + th > window.innerHeight - 8) y = Math.max(8, r.top - th - 8);
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  function hideTip() { if (tip) { tip.hidden = true; tipFor = null; } }
  var tipAtDown = null;
  doc.addEventListener("pointerdown", function (ev) { lastPointer = ev.pointerType || "mouse"; tipAtDown = tipFor; }, true);
  $$("a.term").forEach(function (el) {
    el.setAttribute("aria-describedby", "term-tooltip");
    el.addEventListener("mouseenter", function () { if (lastPointer !== "touch") showTip(el); });
    el.addEventListener("mouseleave", function () { if (lastPointer !== "touch") hideTip(); });
    el.addEventListener("focus", function () { showTip(el); });
    el.addEventListener("blur", hideTip);
    el.addEventListener("click", function (ev) {
      // touch: the first tap shows the definition, a second tap opens the glossary
      if (lastPointer === "touch" && tipAtDown !== el) { ev.preventDefault(); showTip(el); }
    });
  });
  window.addEventListener("scroll", hideTip, { passive: true });
  doc.addEventListener("pointerdown", function (ev) { if (tipFor && !ev.target.closest("a.term")) hideTip(); });

  /* ---------- quiz ---------- */
  $$(".quiz").forEach(function (quiz) {
    var btn = $(".quiz-toggle", quiz);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var all = $$("details.q-answer", quiz);
      var open = !all.every(function (d) { return d.open; });
      all.forEach(function (d) { d.open = open; });
      btn.textContent = open ? "Hide all answers" : "Show all answers";
    });
  });

  /* ---------- copy code ---------- */
  function copyText(text, done) {
    function fallback() {
      var ta = doc.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.top = "-1000px";
      body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = doc.execCommand("copy"); } catch (e) { ok = false; }
      body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, fallback);
    } else { fallback(); }
  }
  $$(".code-copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var code = $("pre code", btn.closest(".code-excerpt"));
      if (!code) return;
      copyText(code.textContent, function (ok) {
        btn.textContent = ok ? "Copied" : "Copy failed";
        btn.classList.toggle("done", ok);
        setTimeout(function () { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1600);
      });
    });
  });

  /* ---------- deep dives ---------- */
  var ddBtn = $(".dd-toggle-all");
  if (ddBtn) ddBtn.addEventListener("click", function () {
    var all = $$("details.deepdive");
    var open = !all.every(function (d) { return d.open; });
    all.forEach(function (d) { d.open = open; });
    ddBtn.textContent = open ? "Close all deep dives" : "Open all deep dives";
  });
  function revealHash() {
    var id = decodeURIComponent((location.hash || "").slice(1));
    if (!id) return;
    var el = doc.getElementById(id);
    if (!el) return;
    var d = el.closest("details");
    var changed = false;
    while (d) { if (!d.open) { d.open = true; changed = true; } d = d.parentElement && d.parentElement.closest("details"); }
    if (changed) el.scrollIntoView();
  }
  window.addEventListener("hashchange", revealHash);
  revealHash();

  /* ---------- diagram lightbox ---------- */
  var lb = $(".lightbox");
  var lbBody = lb && $(".lightbox-body", lb);
  var lastFocus = null;
  function closeLightbox() {
    if (!lb || lb.hidden) return;
    lb.hidden = true; lbBody.innerHTML = ""; body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }
  $$(".diagram-zoom").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var svg = $("svg", btn);
      if (!svg || !lb) return;
      lastFocus = btn;
      var clone = svg.cloneNode(true);
      clone.style.width = (svg.getAttribute("width") || 1500) + "px";
      clone.style.height = "auto";
      lbBody.innerHTML = "";
      lbBody.appendChild(clone);
      lb.hidden = false; body.style.overflow = "hidden";
      $(".lightbox-close", lb).focus();
    });
  });
  if (lb) {
    $(".lightbox-close", lb).addEventListener("click", closeLightbox);
    lb.addEventListener("click", function (ev) { if (ev.target === lb || ev.target === lbBody) closeLightbox(); });
  }

  /* ---------- TOC highlight ---------- */
  var tocLinks = $$(".toc a");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var heads = Object.keys(map).map(function (id) { return doc.getElementById(id); }).filter(Boolean);
    var visible = {};
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      var firstVisible = null;
      for (var i = 0; i < heads.length; i++) { if (visible[heads[i].id]) { firstVisible = heads[i].id; break; } }
      if (firstVisible) {
        tocLinks.forEach(function (a) { a.classList.remove("active"); });
        map[firstVisible].classList.add("active");
      }
    }, { rootMargin: "-56px 0px -60% 0px" });
    heads.forEach(function (h) { obs.observe(h); });
  }
})();
