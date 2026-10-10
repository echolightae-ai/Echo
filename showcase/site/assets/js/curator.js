/* Private curator: tick clips, name the client, get a link to a mini page of just those clips. */
(function () {
  "use strict";
  var $ = M.$, el = M.el, ALL = window.ALL, picked = [], map = {};
  ALL.forEach(function (e) { e.clips.forEach(function (c) { map[c.k] = { c: c, e: e }; }); });
  var list = $("#list"), cnt = $("#cnt");
  function thumb(c) { return M.poster(c); }
  function render() {
    list.textContent = "";
    ALL.forEach(function (e) {
      var d = el("details", { class: "cev" }), s = el("summary", {}, [el("span", { class: "ct", text: e.title }), el("span", { class: "cm", text: e.clips.length + (e.clips.length === 1 ? " clip · " : " clips · ") + (e.city || "") })]); d.appendChild(s);
      var g = el("div", { class: "cg" });
      e.clips.forEach(function (c) { var on = picked.indexOf(c.k) > -1; var b = el("button", { type: "button", class: "ct-clip" + (on ? " on" : ""), "aria-pressed": on ? "true" : "false", "aria-label": (c.t === "p" ? "Photo" : "Video") + " from " + e.title }, [el("img", { src: thumb(c), alt: "", loading: "lazy" }), c.t !== "p" ? el("span", { class: "vb", text: "▶" }) : null, el("span", { class: "ck", text: on ? "✓" : "" })]);
        b.onclick = function () { var i = picked.indexOf(c.k); if (i > -1) picked.splice(i, 1); else picked.push(c.k); render(); d.open = true; }; g.appendChild(b); });
      var all = el("button", { type: "button", class: "btn small", text: "Select all" }); all.onclick = function () { e.clips.forEach(function (c) { if (picked.indexOf(c.k) < 0) picked.push(c.k); }); render(); };
      d.appendChild(g); d.appendChild(all); list.appendChild(d); if (e.clips.some(function (c) { return picked.indexOf(c.k) > -1; })) d.open = true;
    });
    cnt.textContent = picked.length + (picked.length === 1 ? " clip" : " clips") + " selected"; sel(); link();
  }
  function sel() {
    var r = $("#sel"); r.textContent = "";
    picked.forEach(function (k, i) { var o = map[k]; if (!o) return; var x = el("button", { type: "button", class: "sel-i", title: "Remove" }, [el("img", { src: thumb(o.c), alt: "" }), el("span", { text: "×" })]); x.onclick = function () { picked.splice(i, 1); render(); }; r.appendChild(x); });
  }
  function link() {
    var n = $("#client").value.trim(), note = $("#note").value.trim(), out = $("#out"), base = location.href.replace(/curator\.html.*$/, "") + "c.html";
    if (!picked.length) { out.value = ""; $("#open").removeAttribute("href"); return; }
    var u = base + "?c=" + picked.join("~") + (n ? "&n=" + encodeURIComponent(n) : "") + (note ? "&m=" + encodeURIComponent(note) : ""); out.value = u; $("#open").href = u;
  }
  $("#client").addEventListener("input", link); $("#note").addEventListener("input", link);
  $("#copy").addEventListener("click", function () { var o = $("#out"); o.select(); (navigator.clipboard ? navigator.clipboard.writeText(o.value) : Promise.reject()).then(function () { $("#copy").textContent = "Copied"; setTimeout(function () { $("#copy").textContent = "Copy link"; }, 1500); }, function () { document.execCommand && document.execCommand("copy"); }); });
  $("#clear").addEventListener("click", function () { picked = []; render(); });
  render();
})();
