/* EchoLight showcase — vanilla JS, works from file:// and any static host. */
(function () {
  "use strict";
  var WA = "971567220533";
  var ITEMS = window.ITEMS || [], EV = window.EVENTS, SV = window.SERVICES;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var state = { lang: "en", ev: null, sv: [], q: "", limit: 18, list: [], lab: { color: 0, pattern: "fan" } };
  var store = { get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };

  function t(key, vars) {
    var parts = key.split("."), v = window.I18N[state.lang];
    for (var i = 0; i < parts.length && v != null; i++) v = v[parts[i]];
    if (v == null) { v = window.I18N.en; for (i = 0; i < parts.length && v != null; i++) v = v[parts[i]]; }
    if (typeof v === "string" && vars) v = v.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] != null ? vars[k] : m; });
    return v == null ? key : v;
  }
  function el(tag, attrs, kids) {
    var n = document.createElement(tag), k;
    for (k in (attrs || {})) { if (k === "class") n.className = attrs[k]; else if (k === "text") n.textContent = attrs[k]; else n.setAttribute(k, attrs[k]); }
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function path(it) { return it.t === "v" ? "assets/vid/" + it.f + ".mp4" : "assets/img/" + it.f + ".jpg"; }
  function poster(it) { return it.t === "v" ? "assets/vid/" + it.f + ".jpg" : "assets/img/" + it.f + ".jpg"; }
  function title(it) { return t("lb_t", { s: t("sv." + (it.s[0] || "lighting")), e: it.e[0] ? t("ev." + it.e[0]) : t("ev_general") }); }
  function proof(n) { return n === 1 ? t("proof_1") : n ? t("proof_n", { n: n }) : t("proof_soon"); }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) % 1000; }

  /* ---------- language ---------- */
  function applyLang() {
    var L = state.lang; document.documentElement.lang = L; document.documentElement.dir = L === "ar" ? "rtl" : "ltr";
    $$("[data-i18n]").forEach(function (n) { n.textContent = t(n.getAttribute("data-i18n")); });
    $("#lang span").textContent = L === "ar" ? "English" : "العربية";
    startPlaceholder(); buildChips(); buildStats(); buildFilters(); buildServices(); buildPatterns(); render(); renderReco(); setWA(); if (!$("#lb").hidden) lbShow(lb.i);
  }

  /* ---------- hero: typing placeholder, chips, stats ---------- */
  var phTimer;
  function startPlaceholder() {
    clearTimeout(phTimer); var q = $("#q"), list = t("ph"), i = 0, j = 0, del = false;
    if (reduced) { q.placeholder = list[0]; return; }
    (function tick() {
      var s = list[i]; q.placeholder = s.slice(0, j) + (j % 2 ? "" : "");
      if (!del && j < s.length) { j++; phTimer = setTimeout(tick, 55); }
      else if (!del) { del = true; phTimer = setTimeout(tick, 1400); }
      else if (j > 0) { j--; phTimer = setTimeout(tick, 22); }
      else { del = false; i = (i + 1) % list.length; phTimer = setTimeout(tick, 250); }
    })();
  }
  function buildChips() {
    var box = $("#chips"); box.textContent = "";
    EV.forEach(function (e) {
      var b = el("button", { class: "chip", type: "button", "data-ev": e }, [el("i", { style: "background:" + window.PALETTE[e][0] }), el("span", { text: t("ev." + e) })]);
      b.addEventListener("click", function () { $("#q").value = ""; pick(e, ""); });
      box.appendChild(b);
    });
  }
  function buildStats() {
    var data = [["400+", "stat_events"], ["50+", "stat_venues"], ["14+", "stat_clients"], ["5.0 ★", "stat_rating"]], box = $("#stats"); box.textContent = "";
    data.forEach(function (d) { box.appendChild(el("div", {}, [el("b", { text: d[0] }), el("span", { text: t(d[1]) })])); });
  }

  /* ---------- understanding what the visitor typed ---------- */
  function parse(q) {
    var s = q.toLowerCase(), out = { ev: null, sv: [], evHits: {} }, e, k, best = 0;
    EV.forEach(function (ev) { var n = 0; window.KW.events[ev].forEach(function (w) { if (s.indexOf(w) > -1) n += w.length > 3 ? 2 : 1; }); out.evHits[ev] = n; if (n > best) { best = n; out.ev = ev; } });
    SV.forEach(function (sv) { if (window.KW.services[sv].some(function (w) { return s.indexOf(w) > -1; })) out.sv.push(sv); });
    return out;
  }
  function pick(ev, q) {
    state.ev = ev; state.q = q || ""; state.sv = []; state.limit = 18; setTheme(ev); render(); renderReco(); buildFilters(); setWA(); jump();
  }
  function submit(q) {
    q = q.trim(); if (!q) return; var p = parse(q);
    state.q = q; state.ev = p.ev; state.sv = p.sv.slice(); state.limit = 18; setTheme(p.ev);
    render(); renderReco(); buildFilters(); setWA(); jump();
    try { var u = new URL(location.href); u.searchParams.set("q", q); history.replaceState(null, "", u); } catch (e) {}
  }
  function jump() { var g = $("#gallery"); g.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); }
  function setTheme(ev) { var p = window.PALETTE[ev || "default"]; if (hero) hero.setColors(p); document.documentElement.style.setProperty("--accent", p[0]); document.documentElement.style.setProperty("--accent2", p[1]); }

  /* ---------- ranking ---------- */
  function rank() {
    var out = [], rec = state.ev ? window.RECO[state.ev] : [];
    ITEMS.forEach(function (it, i) {
      var sc = 0;
      if (state.ev) { if (it.e.indexOf(state.ev) > -1) sc += 4; else if (it.e.length === 0) sc += 0.5; else sc -= 1; }
      if (state.sv.length) { var hit = state.sv.filter(function (s) { return it.s.indexOf(s) > -1; }).length; sc += hit ? 3 + hit : -3; }
      rec.forEach(function (s, r) { if (it.s.indexOf(s) > -1) sc += (4 - r) * 0.4; });
      if (it.ft) sc += 1.2; if (it.t === "v") sc += 0.4;
      sc += hash(it.id) / 5000;
      out.push({ it: it, sc: sc });
    });
    out.sort(function (a, b) { return b.sc - a.sc; });
    var strict = state.ev || state.sv.length;
    return out.filter(function (x) { return !strict || x.sc > 0; }).map(function (x) { return x.it; });
  }

  /* ---------- gallery ---------- */
  var vm = { playing: [] };
  function render() {
    state.list = rank(); var grid = $("#grid"); grid.textContent = ""; stopAll();
    var shown = state.list.slice(0, state.limit), frag = document.createDocumentFragment();
    shown.forEach(function (it, i) { frag.appendChild(tile(it, i)); });
    grid.appendChild(frag);
    $("#more").hidden = state.list.length <= state.limit; $("#empty").hidden = state.list.length > 0;
    var sub = $("#g-sub"); sub.textContent = state.q ? t("g_sub_q", { q: state.q }) : (state.ev || state.sv.length ? t("g_sub_f") : t("g_sub_all"));
    observeTiles();
  }
  function tile(it, i) {
    var ratio = Math.min(1.7, Math.max(0.58, it.w / it.h));
    var img = el("img", { src: poster(it), width: it.w, height: it.h, alt: title(it), decoding: "async" }); if (i > 5) img.loading = "lazy";
    var b = el("button", { class: "tile" + (it.t === "v" ? " is-v" : ""), type: "button", style: "aspect-ratio:" + ratio.toFixed(3) + ";background:" + it.c, "data-i": i, "aria-label": title(it) }, [
      img, it.t === "v" ? el("span", { class: "vbadge", "aria-hidden": "true", text: "▶ " + Math.round(it.d) + "s" }) : null,
      el("span", { class: "cap", text: title(it) })]);
    b.addEventListener("click", function () { lbOpen(i, b); });
    return b;
  }
  var tio;
  function observeTiles() {
    if (!window.IntersectionObserver || reduced) return;
    if (tio) tio.disconnect();
    tio = new IntersectionObserver(function (en) {
      en.forEach(function (e) { var b = e.target; if (e.isIntersecting && e.intersectionRatio >= 0.6) play(b); else stop(b); });
    }, { threshold: [0, 0.6] });
    $$("#grid .tile.is-v").forEach(function (b) { tio.observe(b); });
  }
  function play(b) {
    if (b._v) return; var it = state.list[+b.getAttribute("data-i")]; if (!it) return;
    if (vm.playing.length >= 4) stop(vm.playing[0]);
    var v = el("video", { muted: "", loop: "", playsinline: "", preload: "metadata", "aria-hidden": "true" }); v.muted = true; v.src = path(it);
    v.addEventListener("playing", function () { v.classList.add("on"); }); b.insertBefore(v, b.firstChild.nextSibling); b._v = v; vm.playing.push(b);
    var p = v.play(); if (p && p.catch) p.catch(function () {});
  }
  function stop(b) { if (!b._v) return; b._v.pause(); b._v.removeAttribute("src"); b._v.load(); b._v.remove(); b._v = null; vm.playing = vm.playing.filter(function (x) { return x !== b; }); }
  function stopAll() { vm.playing.slice().forEach(stop); }

  function buildFilters() {
    var fe = $("#f-events"), fs = $("#f-services"); fe.textContent = ""; fs.textContent = "";
    function pill(label, on, fn, color) { var b = el("button", { class: "pill" + (on ? " on" : ""), type: "button", "aria-pressed": on ? "true" : "false" }, [color ? el("i", { style: "background:" + color }) : null, el("span", { text: label })]); b.addEventListener("click", fn); return b; }
    fe.appendChild(pill(t("all"), !state.ev, function () { state.ev = null; state.q = ""; afterFilter(); }));
    EV.forEach(function (e) { fe.appendChild(pill(t("ev." + e), state.ev === e, function () { state.ev = state.ev === e ? null : e; state.q = ""; afterFilter(); }, window.PALETTE[e][0])); });
    fs.appendChild(pill(t("all"), !state.sv.length, function () { state.sv = []; afterFilter(); }));
    SV.forEach(function (s) { fs.appendChild(pill(t("sv." + s), state.sv.indexOf(s) > -1, function () { var i = state.sv.indexOf(s); if (i > -1) state.sv.splice(i, 1); else state.sv.push(s); afterFilter(); })); });
  }
  function afterFilter() { state.limit = 18; setTheme(state.ev); render(); renderReco(); buildFilters(); setWA(); }
  $("#more").addEventListener("click", function () { state.limit += 18; var y = scrollY; render(); scrollTo(0, y); });

  /* ---------- recommendation panel ---------- */
  function renderReco() {
    var box = $("#reco"); if (!state.ev && !state.sv.length && !state.q) { box.hidden = true; box.textContent = ""; return; }
    var base = state.ev ? window.RECO[state.ev].slice() : ["lighting", "led", "laser", "mapping"], list = state.sv.slice();
    base.forEach(function (s) { if (list.indexOf(s) < 0) list.push(s); }); list = list.slice(0, 4);
    box.hidden = false; box.textContent = "";
    box.appendChild(el("h3", { text: state.ev ? t("reco_for", { e: t("ev_one." + state.ev) }) : t("reco_generic", { q: state.q || "" }) }));
    var row = el("div", { class: "reco-row" });
    list.forEach(function (s, i) {
      var n = ITEMS.filter(function (it) { return it.s.indexOf(s) > -1 && (!state.ev || it.e.indexOf(state.ev) > -1); }).length;
      var why = state.ev && window.I18N[state.lang].why[state.ev][s] ? t("why." + state.ev + "." + s) : t("sv_desc." + s);
      var c = el("button", { class: "rcard", type: "button" }, [el("small", { text: "0" + (i + 1) }), el("strong", { text: t("sv." + s) }), el("p", { text: why }), el("em", { text: proof(n) })]);
      c.addEventListener("click", function () { state.sv = [s]; afterFilter(); jump(); });
      row.appendChild(c);
    });
    box.appendChild(row);
    box.appendChild(el("a", { class: "btn btn-wa small", href: "#", target: "_blank", rel: "noopener", "data-wa": "", "data-ctx": "reco" }, [el("span", { text: t("reco_cta") })]));
    setWA();
  }

  /* ---------- reel marquee ---------- */
  function buildReel() {
    var feat = ITEMS.filter(function (i) { return i.t === "v" && i.ft; }).sort(function (a, b) { return hash(a.id) - hash(b.id); }).slice(0, 10), track = $("#reel-track");
    if (!feat.length) { $("#reel").hidden = true; return; }
    function card(it) {
      var v = el("video", { muted: "", loop: "", playsinline: "", preload: "none", poster: poster(it), "aria-hidden": "true" }); v.muted = true; v.dataset.src = path(it);
      return el("div", { class: "rv", style: "aspect-ratio:" + (it.w / it.h).toFixed(3) }, [v]);
    }
    [0, 1].forEach(function () { var g = el("div", { class: "rv-set" }); feat.forEach(function (it) { g.appendChild(card(it)); }); track.appendChild(g); });
    if (reduced || !window.IntersectionObserver) return;
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (e) {
        var v = e.target;
        if (e.isIntersecting) { if (!v.getAttribute("src")) v.src = v.dataset.src; var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause();
      });
    }, { rootMargin: "100px" });
    $$("#reel-track video").forEach(function (v) { io.observe(v); });
  }

  /* ---------- services ---------- */
  function buildServices() {
    var box = $("#s-grid"); box.textContent = "";
    SV.forEach(function (s, i) {
      var mine = ITEMS.filter(function (it) { return it.s.indexOf(s) > -1; }), cover = mine.filter(function (x) { return x.ft && x.t === "p"; })[0] || mine.filter(function (x) { return x.ft; })[0] || mine[0];
      var card = el("button", { class: "scard", type: "button", "data-s": s }, [
        cover ? el("img", { src: poster(cover), alt: "", loading: "lazy", decoding: "async" }) : null,
        el("div", { class: "scard-in" }, [el("small", { text: "0" + (i + 1) }), el("h3", { text: t("sv." + s) }), el("p", { text: t("sv_desc." + s) }),
          el("span", { class: "go", text: proof(mine.length) + (state.lang === "ar" ? "  ←" : "  →") })])]);
      card.addEventListener("click", function () { state.ev = null; state.q = ""; state.sv = [s]; afterFilter(); jump(); });
      box.appendChild(card);
    });
  }

  /* ---------- Beam Lab ---------- */
  var LAB = [["#2bc4e0", "#5b7cff", "#ffffff"], ["#ff3df0", "#c04dff", "#3dd6ff"], ["#ffb86b", "#ff7aa8", "#fff1d6"], ["#2ee59d", "#ff4d5e", "#ffffff"], ["#8dff3d", "#2bc4e0", "#ffffff"], ["#ffffff", "#bcd7ff", "#ffffff"]];
  var LABN = { en: ["Aqua", "Neon", "Gold", "National", "Lime", "White"], ar: ["أزرق", "نيون", "ذهبي", "وطني", "ليموني", "أبيض"] };
  function buildPatterns() {
    var sw = $("#sw"), pat = $("#pat"); sw.textContent = ""; pat.textContent = "";
    LAB.forEach(function (c, i) {
      var b = el("button", { class: "swatch" + (i === state.lab.color ? " on" : ""), type: "button", "aria-label": LABN[state.lang][i], style: "background:linear-gradient(135deg," + c[0] + "," + c[1] + ")" });
      b.addEventListener("click", function () { state.lab.color = i; lab.setColors(c.concat(c)); buildPatterns(); }); sw.appendChild(b);
    });
    ["fan", "cross", "sweep", "tunnel"].forEach(function (p) {
      var b = el("button", { class: "seg-b" + (p === state.lab.pattern ? " on" : ""), type: "button", text: t("pat_" + p) });
      b.addEventListener("click", function () { state.lab.pattern = p; lab.set("pattern", p); buildPatterns(); }); pat.appendChild(b);
    });
  }

  /* ---------- WhatsApp ---------- */
  function waText(ctx, it) {
    var parts = [t("wa_base")];
    if (state.ev) parts.push(t("wa_event", { e: t("ev_one." + state.ev) }));
    if (state.sv.length) parts.push(t("wa_svc", { s: state.sv.map(function (s) { return t("sv." + s); }).join(", ") }));
    if (it) parts.push(t("wa_item", { t: title(it) }));
    if (ctx === "lab") parts.push(t("wa_lab", { c: LABN[state.lang][state.lab.color], p: t("pat_name." + state.lab.pattern) }));
    parts.push(t("wa_tail")); return parts.join(" ");
  }
  function waURL(ctx, it) { return "https://wa.me/" + WA + "?text=" + encodeURIComponent(waText(ctx, it)); }
  function setWA() { $$("[data-wa]").forEach(function (a) { a.href = waURL(a.getAttribute("data-ctx") || "", null); }); }

  /* ---------- lightbox ---------- */
  var lb = { i: 0, from: null, x: null };
  function lbOpen(i, from) { lb.i = i; lb.from = from; var n = $("#lb"); n.hidden = false; document.body.classList.add("noscroll"); lbShow(i); $("#lb-x").focus(); }
  function lbShow(i) {
    var it = state.list[i]; if (!it) return; lb.i = i; var m = $("#lb-media"); m.textContent = "";
    var node;
    if (it.t === "v") { node = el("video", { controls: "", autoplay: "", loop: "", playsinline: "", poster: poster(it) }); node.muted = true; node.src = path(it); }
    else node = el("img", { src: path(it), alt: title(it) });
    m.appendChild(node); $("#lb-title").textContent = title(it);
    $("#lb-meta").textContent = (i + 1) + " / " + state.list.length; $("#lb-wa").href = waURL("lb", it);
    [1, -1].forEach(function (d) { var n = state.list[(i + d + state.list.length) % state.list.length]; if (n && n.t === "p") { var im = new Image(); im.src = path(n); } });
  }
  function lbClose() { var n = $("#lb"); n.hidden = true; $("#lb-media").textContent = ""; document.body.classList.remove("noscroll"); if (lb.from) lb.from.focus(); }
  function lbStep(d) { var L = state.list.length; lbShow((lb.i + d + L) % L); }
  $("#lb-x").addEventListener("click", lbClose); $("#lb-prev").addEventListener("click", function () { lbStep(-1); }); $("#lb-next").addEventListener("click", function () { lbStep(1); });
  $("#lb").addEventListener("click", function (e) { if (e.target.id === "lb" || e.target.classList.contains("lb-fig")) lbClose(); });
  document.addEventListener("keydown", function (e) {
    if ($("#lb").hidden) return; if (e.key === "Escape") lbClose(); else if (e.key === "ArrowRight") lbStep(state.lang === "ar" ? -1 : 1); else if (e.key === "ArrowLeft") lbStep(state.lang === "ar" ? 1 : -1);
    else if (e.key === "Tab") { var f = $$("#lb button, #lb a, #lb video").filter(function (x) { return !x.disabled; }); if (!f.length) return; var a = f[0], z = f[f.length - 1]; if (e.shiftKey && document.activeElement === a) { z.focus(); e.preventDefault(); } else if (!e.shiftKey && document.activeElement === z) { a.focus(); e.preventDefault(); } }
  });
  $("#lb").addEventListener("pointerdown", function (e) { lb.x = e.clientX; }); $("#lb").addEventListener("pointerup", function (e) { if (lb.x == null) return; var d = e.clientX - lb.x; lb.x = null; if (Math.abs(d) > 70) lbStep(d < 0 ? 1 : -1); });

  /* ---------- boot ---------- */
  var hero, lab;
  function boot() {
    var saved = store.get("el_lang"); state.lang = saved || ((navigator.language || "en").slice(0, 2) === "ar" ? "ar" : "en");
    hero = new Beams($("#hero-canvas"), { count: innerWidth < 700 ? 6 : 9, speed: 1, colors: window.PALETTE.default.concat(window.PALETTE.default), host: $(".hero") });
    lab = new Beams($("#lab-canvas"), { count: 12, speed: 0.6, pattern: "fan", colors: LAB[0].concat(LAB[0]), host: $("#lab") });
    $("#cnt").addEventListener("input", function (e) { lab.set("count", +e.target.value); });
    $("#spd").addEventListener("input", function (e) { lab.set("speed", +e.target.value / 6); });
    $("#lang").addEventListener("click", function () { state.lang = state.lang === "ar" ? "en" : "ar"; store.set("el_lang", state.lang); applyLang(); });
    $("#finder").addEventListener("submit", function (e) { e.preventDefault(); submit($("#q").value); });
    $("#yr").textContent = new Date().getFullYear();
    $$("[data-wa]").forEach(function (a) { a.addEventListener("click", function () { a.href = waURL(a.getAttribute("data-ctx") || "", null); }); });
    var top = $("#top-bar"); addEventListener("scroll", function () { top.classList.toggle("solid", scrollY > 24); }, { passive: true });
    buildReel(); applyLang();
    var q0 = null; try { q0 = new URL(location.href).searchParams.get("q"); } catch (e) {}
    if (q0) { $("#q").value = q0; submit(q0); }
  }
  boot();
})();
