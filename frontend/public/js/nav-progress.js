/* A thin top loading bar (like YouTube/GitHub). The moment you click a link that
   navigates, it starts filling — so every click feels instant and responsive even
   while the next page is loading. It vanishes when the new page renders. */
(function () {
  var bar = document.createElement("div");
  bar.id = "__navbar";
  (document.body || document.documentElement).appendChild(bar);

  function start() {
    bar.classList.remove("go", "done");
    void bar.offsetWidth;      // restart the animation
    bar.classList.add("go");
  }
  function done() {
    // quickly complete & fade — used by the no-reload engine after an in-place swap
    bar.classList.add("done");
    setTimeout(function () { bar.className = ""; }, 280);
  }
  // exposed for ajax-forms.js (in-place form submits)
  window.__nav = { start: start, done: done };

  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
    var href = a.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#" || /^(javascript:|mailto:|tel:)/i.test(href)) return;
    var u; try { u = new URL(a.href, location.href); } catch (err) { return; }
    if (u.origin !== location.origin) return;                       // external link
    if (u.pathname === location.pathname && u.search === location.search) return; // same page / anchor
    start();
  }, true);

  // back/forward (bfcache) restores the old page — make sure the bar is reset.
  window.addEventListener("pageshow", function () { bar.className = ""; });
})();
