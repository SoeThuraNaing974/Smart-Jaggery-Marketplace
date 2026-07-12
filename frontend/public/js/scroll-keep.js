/* Keep the scroll position when a form submit triggers a full-page reload/redirect.
   Without this, every action button (Waiting, Packing, Save, Remove, ...) jumps the
   page back to the top after the server redirect. We stash scrollY keyed by pathname
   just before navigating, then restore it once the same page loads again. */
(function () {
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";

  var KEY = "scrollpos:" + location.pathname;

  function save() {
    try { sessionStorage.setItem("scrollpos:" + location.pathname, String(window.scrollY || window.pageYOffset || 0)); }
    catch (e) {}
  }

  function restore() {
    var v;
    try { v = sessionStorage.getItem(KEY); } catch (e) { v = null; }
    if (v !== null) {
      var y = parseInt(v, 10) || 0;
      // restore now and again on the next frame (covers async layout / images)
      window.scrollTo(0, y);
      requestAnimationFrame(function () { window.scrollTo(0, y); });
      try { sessionStorage.removeItem(KEY); } catch (e) {}
    }
  }

  // Save before leaving (covers form submits, which navigate away and reload).
  window.addEventListener("beforeunload", save);
  window.addEventListener("pagehide", save);
  document.addEventListener("submit", save, true);

  if (document.readyState === "complete") restore();
  else window.addEventListener("load", restore);
})();
