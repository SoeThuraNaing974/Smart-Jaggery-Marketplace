/* Mobile-friendly tables, system-wide.
   On phones, every data table (.tbl) becomes a stack of cards where each cell
   reads "Header: value" — so you never have to scroll a wide table sideways.
   The CSS does the visual stacking; this script copies each column's header
   text onto its body cells as data-label (used by `td::before`).

   It runs on first load, again after every in-place page swap (pjax:load), and
   it watches the DOM so ANY rows added later — by a filter, "see more"
   pagination, or an in-place update — also get their labels, with no refresh. */
(function () {
  function labelTable(tbl) {
    if (!tbl || !tbl.querySelectorAll) return;
    var heads = tbl.querySelectorAll("thead th");
    if (!heads.length) return;
    var labels = Array.prototype.map.call(heads, function (th) { return (th.textContent || "").trim(); });
    tbl.querySelectorAll("tbody tr").forEach(function (tr) {
      var cells = tr.children;
      for (var i = 0; i < cells.length; i++) {
        if (!cells[i].hasAttribute("data-label") && labels[i]) cells[i].setAttribute("data-label", labels[i]);
      }
    });
  }
  function run(scope) { (scope || document).querySelectorAll("table.tbl").forEach(labelTable); }

  // exposed so the no-reload engine can re-label tables right after an in-place swap
  window.__rehydrateTables = run;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { run(); });
  else run();

  // re-label after the no-reload engine renders a new page in place
  document.addEventListener("pjax:load", function () { run(); });

  // auto-label rows/tables added later (filters, "see more", in-place updates) — no refresh needed
  try {
    var mo = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var n = added[j];
          if (!n || n.nodeType !== 1) continue;
          if (n.matches && n.matches("table.tbl")) labelTable(n);
          if (n.querySelectorAll) n.querySelectorAll("table.tbl").forEach(labelTable);
          if (n.closest) { var tbl = n.closest("table.tbl"); if (tbl) labelTable(tbl); }  // a row added directly
        }
      }
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) { /* MutationObserver unsupported — the load + pjax handlers still cover most cases */ }
})();
