/* Shared helpers: media paths, WhatsApp links, autoplay manager, lightbox. */
(function () {
  "use strict";
  var ROOT = window.ROOT || "", WA = "971567220533";
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, r) { return (r || document).querySelector(s); }, $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  function el(tag, a, kids) { var n = document.createElement(tag), k; for (k in a || {}) { if (k === "class") n.className = a[k]; else if (k === "text") n.textContent = a[k]; else n.setAttribute(k, a[k]); } (kids || []).forEach(function (c) { if (c) n.appendChild(c); }); return n; }
  function stem(c) { return c.t === "s" ? c.k : c.f; }
  var M = {
    img: function (c) { return ROOT + "assets/img/" + c.f + ".jpg"; },
    src: function (c) { return c.t === "p" ? M.img(c) : ROOT + "assets/v/" + stem(c) + ".mp4"; },
    poster: function (c) { return c.t === "p" ? M.img(c) : ROOT + "assets/v/" + stem(c) + ".jpg"; }
  };
  function wa(parts) { return "https://wa.me/" + WA + "?text=" + encodeURIComponent(parts.filter(Boolean).join(" ")); }

  /* play at most 4 videos at once, only when mostly in view */
  var playing = [], io;
  function mount(tile) {
    if (tile._v || reduced) return; var v = el("video", { muted: "", loop: "", playsinline: "", preload: "metadata", "aria-hidden": "true" }); v.muted = true; v.src = tile.getAttribute("data-src");
    v.addEventListener("playing", function () { v.classList.add("on"); }); tile.insertBefore(v, tile.firstChild.nextSibling); tile._v = v;
    if (playing.length >= 4) unmount(playing[0]); playing.push(tile); var p = v.play(); if (p && p.catch) p.catch(function () {});
  }
  function unmount(tile) { if (!tile._v) return; tile._v.pause(); tile._v.removeAttribute("src"); tile._v.load(); tile._v.remove(); tile._v = null; playing = playing.filter(function (t) { return t !== tile; }); }
  function watch(tiles) {
    if (!window.IntersectionObserver || reduced) return; io = io || new IntersectionObserver(function (en) { en.forEach(function (e) { if (e.isIntersecting && e.intersectionRatio >= 0.6) mount(e.target); else unmount(e.target); }); }, { threshold: [0, 0.6] });
    tiles.forEach(function (t) { io.observe(t); });
  }

  /* lightbox */
  var lb;
  function build() {
    lb = el("div", { class: "lb", role: "dialog", "aria-modal": "true", "aria-label": "Viewer", hidden: "" }, [
      el("button", { class: "lb-x", type: "button", "aria-label": "Close", text: "×" }), el("button", { class: "lb-nav prev", type: "button", "aria-label": "Previous", text: "‹" }), el("button", { class: "lb-nav next", type: "button", "aria-label": "Next", text: "›" }),
      el("figure", { class: "lb-fig" }, [el("div", { class: "lb-media" }), el("figcaption", {}, [el("div", {}, [el("strong", { class: "lb-t" }), el("span", { class: "lb-m" })]), el("a", { class: "btn btn-wa small", target: "_blank", rel: "noopener", text: "Ask about this look" })])])]);
    document.body.appendChild(lb); var self = M.lightbox;
    lb.querySelector(".lb-x").onclick = M.close; lb.querySelector(".prev").onclick = function () { step(-1); }; lb.querySelector(".next").onclick = function () { step(1); };
    lb.addEventListener("click", function (e) { if (e.target === lb || e.target.classList.contains("lb-fig")) M.close(); });
    document.addEventListener("keydown", function (e) { if (lb.hidden) return; if (e.key === "Escape") M.close(); else if (e.key === "ArrowRight") step(1); else if (e.key === "ArrowLeft") step(-1); });
    var x0 = null; lb.addEventListener("pointerdown", function (e) { x0 = e.clientX; }); lb.addEventListener("pointerup", function (e) { if (x0 == null) return; var d = e.clientX - x0; x0 = null; if (Math.abs(d) > 70) step(d < 0 ? 1 : -1); });
  }
  var cur = { list: [], i: 0, from: null, cap: null };
  function show() {
    var it = cur.list[cur.i]; if (!it) return; var c = it.c, m = lb.querySelector(".lb-media"); m.textContent = "";
    var n; if (c.t === "p") n = el("img", { src: M.src(c), alt: it.alt || "" }); else { n = el("video", { controls: "", autoplay: "", loop: "", playsinline: "", poster: M.poster(c) }); n.muted = true; n.src = (c.full ? ROOT + "assets/v/" + c.full + ".mp4" : M.src(c)); }
    m.appendChild(n); lb.querySelector(".lb-t").textContent = it.title || ""; lb.querySelector(".lb-m").textContent = (cur.i + 1) + " / " + cur.list.length + (it.sub ? " · " + it.sub : "");
    lb.querySelector(".btn-wa").href = wa([cur.cap ? cur.cap(it) : "Hello EchoLight, I saw " + (it.title || "this") + " on your showcase and I'd like something like it."]);
  }
  function step(d) { var L = cur.list.length; cur.i = (cur.i + d + L) % L; show(); }
  M.open = function (list, i, from, cap) { if (!lb) build(); cur = { list: list, i: i, from: from, cap: cap }; lb.hidden = false; document.body.classList.add("noscroll"); show(); lb.querySelector(".lb-x").focus(); };
  M.close = function () { if (!lb || lb.hidden) return; lb.hidden = true; lb.querySelector(".lb-media").textContent = ""; document.body.classList.remove("noscroll"); if (cur.from) cur.from.focus(); };
  M.$ = $; M.$$ = $$; M.el = el; M.wa = wa; M.watch = watch; M.reduced = reduced; M.stem = stem;
  /* when embedded in another site (Squarespace), tell the parent how tall we are */
  if (window.parent !== window) {
    var send = function () { try { parent.postMessage({ echolightHeight: document.documentElement.scrollHeight }, "*"); } catch (e) {} };
    addEventListener("load", send); if (window.ResizeObserver) new ResizeObserver(send).observe(document.body); setInterval(send, 1500);
  }
  window.M = M;
})();
