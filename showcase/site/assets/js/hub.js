/* Hub: event finder, filters, recommendations. Cards are static HTML; this only re-orders and filters them. */
(function () {
  "use strict";
  var $ = M.$, $$ = M.$$, el = M.el, H = window.HUB, cards = {}, grid = $("#cards");
  var TYPES = { corporate: "Corporate & Conferences", gala: "Galas & Awards", wedding: "Weddings", launch: "Launches & Openings", government: "National & Government", private: "Private Celebrations", exhibition: "Exhibitions", show: "Light Shows & Showreels" };
  var SV = { lighting: "Stage Lighting", led: "LED Screens", sound: "Sound", mapping: "3D Mapping", laser: "Laser & Light Shows" };
  var KW = {
    corporate: ["corporate", "conference", "summit", "seminar", "meeting", "agm", "company", "business", "forum", "keynote", "congress", "شركة", "مؤتمر", "قمة", "ملتقى", "اجتماع", "ندوة"],
    gala: ["gala", "awards", "award", "dinner", "anniversary", "ceremony", "fashion", "حفل جوائز", "جوائز", "تكريم", "عشاء", "ذكرى", "أزياء"],
    wedding: ["wedding", "bride", "bridal", "groom", "engagement", "henna", "reception", "عرس", "زفاف", "خطوبة", "حنة", "عروس", "فرح", "كوشة"],
    launch: ["launch", "opening", "inauguration", "showroom", "product", "car", "brand", "activation", "reveal", "store", "إطلاق", "افتتاح", "تدشين", "سيارة", "منتج", "علامة"],
    government: ["national day", "government", "ministry", "heritage", "national", "royal", "اليوم الوطني", "وطني", "حكومي", "تراث"],
    private: ["birthday", "party", "new year", "nye", "private", "celebration", "ramadan", "iftar", "eid", "عيد ميلاد", "حفلة", "رأس السنة", "رمضان", "إفطار", "عيد", "احتفال"],
    exhibition: ["exhibition", "expo", "booth", "stand", "trade show", "معرض"],
    show: ["show", "concert", "performance", "showreel", "music", "festival", "عرض", "حفل غنائي", "مهرجان"]
  };
  var SKW = { laser: ["laser", "beam", "sky", "fireworks", "light show", "ليزر", "أشعة"], mapping: ["mapping", "projection", "projector", "facade", "3d", "hologram", "إسقاط", "ماب", "ثلاثي", "واجهة"], led: ["led", "screen", "video wall", "wall", "شاشة", "شاشات", "ليد"], sound: ["sound", "audio", "speaker", "mic", "dj", "صوت", "سماعات", "ساوند"], lighting: ["light", "lighting", "stage", "spot", "truss", "إضاءة", "اضاءة", "مسرح"] };
  var RECO = { corporate: ["led", "sound", "lighting", "laser"], gala: ["lighting", "laser", "led", "sound"], wedding: ["lighting", "laser", "led", "sound"], launch: ["mapping", "led", "laser", "lighting"], government: ["laser", "mapping", "lighting", "led"], private: ["lighting", "laser", "led", "sound"], exhibition: ["led", "lighting", "sound", "mapping"], show: ["laser", "lighting", "mapping", "led"] };
  var WHY = { led: "Big, sharp content readable from the last row.", sound: "Clear coverage for speech and music in every seat.", lighting: "Stage and room lighting designed cue by cue.", laser: "Beams and laser moments people film and remember.", mapping: "Projection fitted to a building, product or stage set." };
  var PAL = { default: ["#2bc4e0", "#5b7cff", "#b46bff", "#ffffff"], corporate: ["#3da9ff", "#7fd8ff", "#ffffff", "#5b7cff"], gala: ["#ffd27a", "#ff7aa8", "#ffffff", "#7fd8ff"], wedding: ["#ffb86b", "#ff7aa8", "#fff1d6", "#ffd27a"], launch: ["#c04dff", "#ff3df0", "#3dd6ff", "#ffffff"], government: ["#2ee59d", "#ff4d5e", "#ffffff", "#2ee59d"], private: ["#ff9f43", "#ee5a9b", "#ffffff", "#7a8cff"], exhibition: ["#3dd6ff", "#ffffff", "#5b7cff", "#2bc4e0"], show: ["#ff3df0", "#3dd6ff", "#c04dff", "#ffffff"] };
  var state = { ty: null, sv: [], q: "" }, hero;
  $$(".ecard", grid).forEach(function (c) { cards[c.getAttribute("data-slug")] = c; });

  function parse(q) {
    var s = q.toLowerCase(), ty = null, best = 0, sv = [];
    Object.keys(KW).forEach(function (k) { var n = 0; KW[k].forEach(function (w) { if (s.indexOf(w) > -1) n += w.length > 3 ? 2 : 1; }); if (n > best) { best = n; ty = k; } });
    Object.keys(SKW).forEach(function (k) { if (SKW[k].some(function (w) { return s.indexOf(w) > -1; })) sv.push(k); });
    return { ty: ty, sv: sv };
  }
  function score(e) {
    var s = 0;
    if (state.ty) { var i = e.types.indexOf(state.ty); s += i === 0 ? 6 : i > 0 ? 4 : -2; }
    if (state.sv.length) { var hit = state.sv.filter(function (x) { return e.svc.indexOf(x) > -1; }).length; s += hit ? 3 * hit : -3; }
    if (state.ty) (RECO[state.ty] || []).forEach(function (x, r) { if (e.svc.indexOf(x) > -1) s += (4 - r) * 0.3; });
    if (e.hero) s += 1.5; if (e.old) s -= 3; s += Math.min(e.clips, 12) * 0.05; s += (e.rank || 0) * 0.001; return s;
  }
  function render() {
    var strict = state.ty || state.sv.length, list = H.map(function (e) { return { e: e, s: score(e) }; }).sort(function (a, b) { return b.s - a.s; }), shown = 0;
    function match(e) { return (!state.ty || e.types.indexOf(state.ty) > -1) && (!state.sv.length || state.sv.some(function (s) { return e.svc.indexOf(s) > -1; })); }
    list.forEach(function (x) { var c = cards[x.e.slug], ok = !strict || match(x.e); c.hidden = !ok; if (ok) { shown++; grid.appendChild(c); } });
    $("#count").textContent = shown + (shown === 1 ? " event" : " events");
    $("#empty").hidden = shown > 0;
    $("#g-sub").textContent = state.q ? "Closest matches for “" + state.q + "” first." : (strict ? "Filtered to what you picked." : "Pick an event type or describe yours above.");
    pills(); reco();
  }
  function pills() {
    var ft = $("#f-types"), fs = $("#f-svc"); ft.textContent = ""; fs.textContent = "";
    function pill(label, on, fn, col) { var b = el("button", { class: "pill" + (on ? " on" : ""), type: "button", "aria-pressed": on ? "true" : "false" }, [col ? el("i", { style: "background:" + col }) : null, el("span", { text: label })]); b.onclick = fn; return b; }
    ft.appendChild(pill("All events", !state.ty, function () { state.ty = null; state.q = ""; apply(); }));
    Object.keys(TYPES).forEach(function (k) { ft.appendChild(pill(TYPES[k], state.ty === k, function () { state.ty = state.ty === k ? null : k; state.q = ""; apply(); }, PAL[k][0])); });
    fs.appendChild(pill("All services", !state.sv.length, function () { state.sv = []; apply(); }));
    Object.keys(SV).forEach(function (k) { fs.appendChild(pill(SV[k], state.sv.indexOf(k) > -1, function () { var i = state.sv.indexOf(k); if (i > -1) state.sv.splice(i, 1); else state.sv.push(k); apply(); })); });
  }
  function reco() {
    var box = $("#reco"); if (!state.ty && !state.sv.length) { box.hidden = true; box.textContent = ""; return; }
    var base = state.ty ? RECO[state.ty].slice() : ["lighting", "led", "laser", "mapping"], l = state.sv.slice(); base.forEach(function (s) { if (l.indexOf(s) < 0) l.push(s); }); l = l.slice(0, 4);
    box.hidden = false; box.textContent = ""; box.appendChild(el("h3", { text: state.ty ? "For " + (TYPES[state.ty].toLowerCase()) + ", this is what we'd build" : "Here's what we'd build for you" }));
    var row = el("div", { class: "reco-row" });
    l.forEach(function (s) { var n = H.filter(function (e) { return e.svc.indexOf(s) > -1 && (!state.ty || e.types.indexOf(state.ty) > -1); }).length; var b = el("button", { class: "rcard", type: "button" }, [el("strong", { text: SV[s] }), el("p", { text: WHY[s] }), el("em", { text: n ? n + (n === 1 ? " event" : " events") + " to look at" : "Ask us for references" })]); b.onclick = function () { state.sv = [s]; apply(); jump(); }; row.appendChild(b); });
    box.appendChild(row); box.appendChild(el("a", { class: "btn btn-wa small", href: M.wa(["Hello EchoLight, I'm planning " + (state.ty ? "a " + TYPES[state.ty].toLowerCase() + " event" : "an event") + (state.sv.length ? " and I'm interested in " + state.sv.map(function (s) { return SV[s]; }).join(", ") : "") + ". Date / venue / guests: "]), target: "_blank", rel: "noopener", text: "Get a quote for this setup" }));
  }
  function theme() { var p = PAL[state.ty || "default"]; if (hero) hero.setColors(p.concat(p)); document.documentElement.style.setProperty("--accent", p[0]); document.documentElement.style.setProperty("--accent2", p[1]); }
  function apply() { theme(); render(); try { var h = state.ty ? "#t=" + state.ty : state.sv.length ? "#s=" + state.sv.join(",") : ""; history.replaceState(null, "", location.pathname + location.search + h); } catch (e) {} }
  function jump() { $("#work").scrollIntoView({ behavior: M.reduced ? "auto" : "smooth", block: "start" }); }
  $("#finder").addEventListener("submit", function (e) { e.preventDefault(); var q = $("#q").value.trim(); if (!q) return; var p = parse(q); state = { ty: p.ty, sv: p.sv, q: q }; apply(); jump(); });
  $$("[data-pick]").forEach(function (b) { b.addEventListener("click", function () { state = { ty: b.getAttribute("data-pick"), sv: [], q: "" }; $("#q").value = ""; apply(); jump(); }); });
  $$("[data-svc]").forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); state = { ty: null, sv: [b.getAttribute("data-svc")], q: "" }; apply(); jump(); }); });
  /* hero beams + typing placeholder */
  if (window.Beams) hero = new Beams($("#hero-canvas"), { count: innerWidth < 700 ? 6 : 9, colors: PAL.default.concat(PAL.default), host: $(".hero") });
  var ph = ["a corporate summit", "a wedding in a ballroom", "a car launch", "National Day outdoors", "an awards night with lasers", "a hotel facade mapping"], pi = 0, pj = 0, del = false, q = $("#q");
  (function tick() { if (M.reduced) { q.placeholder = ph[0]; return; } var s = ph[pi]; q.placeholder = s.slice(0, pj); if (!del && pj < s.length) { pj++; setTimeout(tick, 55); } else if (!del) { del = true; setTimeout(tick, 1300); } else if (pj > 0) { pj--; setTimeout(tick, 22); } else { del = false; pi = (pi + 1) % ph.length; setTimeout(tick, 250); } })();
  /* card hover preview */
  $$(".ecard[data-v]").forEach(function (c) { var t = c.querySelector(".cov"); if (!t || M.reduced) return; c.addEventListener("pointerenter", function (ev) { if (ev.pointerType === "touch") return; t.setAttribute("data-src", c.getAttribute("data-v")); var v = M.el("video", { muted: "", loop: "", playsinline: "", "aria-hidden": "true" }); v.muted = true; v.src = c.getAttribute("data-v"); v.addEventListener("playing", function () { v.classList.add("on"); }); t.appendChild(v); c._v = v; v.play().catch(function () {}); }); c.addEventListener("pointerleave", function () { if (c._v) { c._v.pause(); c._v.remove(); c._v = null; } }); });
  /* deep links like #t=wedding */
  var m = /#t=(\w+)/.exec(location.hash), ms = /#s=([\w,]+)/.exec(location.hash); if (m && TYPES[m[1]]) state.ty = m[1]; if (ms) state.sv = ms[1].split(",").filter(function (x) { return SV[x]; });
  var q0 = new URLSearchParams(location.search).get("q"); if (q0) { $("#q").value = q0; var p0 = parse(q0); state = { ty: p0.ty, sv: p0.sv, q: q0 }; }
  apply();
})();
