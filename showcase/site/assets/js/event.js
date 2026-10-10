/* Event page: gallery tiles open the lightbox, videos autoplay in view. */
(function () {
  var E = window.EVENT, tiles = M.$$(".gal .tile");
  var list = E.clips.map(function (c) { return { c: c, alt: c.alt, title: c.title, sub: E.title }; });
  tiles.forEach(function (t, i) { t.addEventListener("click", function (e) { e.preventDefault(); M.open(list, i, t, function (it) { return "Hello EchoLight, I saw \"" + E.title + "\" on your showcase and I'd like something like it for my event. Date / venue / guests: "; }); }); });
  M.watch(tiles.filter(function (t) { return t.classList.contains("is-v"); }));
  var full = M.$("[data-full]"); if (full) full.addEventListener("click", function (e) { e.preventDefault(); M.open([{ c: { t: "v", k: E.fullClip, full: E.fullClip, f: E.fullClip }, title: E.title + " (full)", sub: "Full show" }], 0, full); });
  var cp = M.$("[data-copy]"); if (cp) cp.addEventListener("click", function () { var u = location.href; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = "Link copied"; }, function () { cp.textContent = u; }); });
})();
