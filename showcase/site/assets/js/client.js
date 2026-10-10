/* Client mini page: only the clips the curator chose. */
(function () {
  "use strict";
  var $ = M.$, el = M.el, p = new URLSearchParams(location.search), ids = (p.get("c") || "").split("~").filter(Boolean), n = p.get("n"), note = p.get("m"), map = {};
  window.ALL.forEach(function (e) { e.clips.forEach(function (c) { map[c.k] = { c: c, e: e }; }); });
  $("#h").textContent = n ? "Selected for " + n : "Selected for you";
  if (note) $("#n").textContent = note;
  var g = $("#g"), items = ids.map(function (k) { return map[k]; }).filter(Boolean);
  if (!items.length) { g.appendChild(el("p", { class: "empty", text: "This selection is empty or the link is incomplete. Ask EchoLight for a fresh one." })); return; }
  var list = items.map(function (o) { return { c: o.c, alt: o.c.alt, title: o.e.title, sub: o.e.venue || o.e.city || "" }; }), tiles = [];
  items.forEach(function (o, i) {
    var c = o.c, a = el("a", { class: "tile" + (c.t === "p" ? "" : " is-v"), href: M.src(c), "data-src": M.src(c), style: "aspect-ratio:" + Math.min(1.7, Math.max(0.58, c.w / c.h)).toFixed(3) }, [el("img", { src: M.poster(c), alt: c.alt || o.e.title, width: c.w, height: c.h, loading: i > 5 ? "lazy" : "eager" }), c.t !== "p" ? el("span", { class: "vbadge", text: "▶" }) : null, el("span", { class: "cap", text: o.e.title })]);
    a.onclick = function (ev) { ev.preventDefault(); M.open(list, i, a, function (it) { return "Hello EchoLight, I saw \"" + it.title + "\" in the selection you sent me" + (n ? " (" + n + ")" : "") + ". I'd like to discuss it. Date / venue / guests: "; }); }; g.appendChild(a); tiles.push(a);
  });
  M.watch(tiles.filter(function (t) { return t.classList.contains("is-v"); }));
  $("#wa").href = M.wa(["Hello EchoLight, I've seen the selection you sent" + (n ? " for " + n : "") + " and I'd like to talk about my event. Date / venue / guests: "]);
})();
