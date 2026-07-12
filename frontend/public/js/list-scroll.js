/* Long lists get a scrollbar.
   Any data table (table.tbl) with MORE THAN 10 body rows is capped to ~10 rows
   tall and scrolls vertically; the header row stays pinned (sticky) on top.
   Runs on first load, after in-place page swaps (pjax:load), on resize, and
   watches the DOM so tables that are filtered/filled later also get capped —
   with no page refresh. Tables with 10 rows or fewer are left exactly as-is. */
(function () {
  var LIMIT = 10;

  function bodyRows(tbl) {
    return (tbl.tBodies && tbl.tBodies[0]) ? tbl.tBodies[0].rows : [];
  }

  function cap(tbl) {
    if (!tbl || tbl.tagName !== "TABLE") return;
    var rows = bodyRows(tbl);
    var wrap = (tbl.parentNode && tbl.parentNode.classList &&
                tbl.parentNode.classList.contains("vscroll")) ? tbl.parentNode : null;

    // 10 or fewer rows -> no cap (undo any previous cap)
    if (rows.length <= LIMIT) {
      if (wrap) { wrap.style.maxHeight = ""; wrap.classList.remove("is-capped"); }
      return;
    }

    // wrap the table once in a scroll container
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "vscroll";
      tbl.parentNode.insertBefore(wrap, tbl);
      wrap.appendChild(tbl);
    }

    // cap height = header + first 10 rows (so the 11th peeks and the scrollbar shows)
    var h = (tbl.tHead ? tbl.tHead.offsetHeight : 0);
    for (var i = 0; i < LIMIT && i < rows.length; i++) h += rows[i].offsetHeight;
    if (h > 0) {
      wrap.style.maxHeight = (h + 2) + "px";
      wrap.classList.add("is-capped");
    }
  }

  function run(scope) {
    (scope || document).querySelectorAll("table.tbl").forEach(cap);
  }

  // exposed so the no-reload engine can re-cap right after an in-place swap
  window.__capLongLists = run;

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", function () { run(); });
  else run();

  document.addEventListener("pjax:load", function () { run(); });

  var rz;
  window.addEventListener("resize", function () {
    clearTimeout(rz);
    rz = setTimeout(function () { run(); }, 150);
  });

  try {
    var mo = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var n = added[j];
          if (!n || n.nodeType !== 1) continue;
          if (n.matches && n.matches("table.tbl")) cap(n);
          if (n.querySelectorAll) n.querySelectorAll("table.tbl").forEach(cap);
          if (n.closest) { var t = n.closest("table.tbl"); if (t) cap(t); }
        }
      }
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) { /* MutationObserver unsupported — load + pjax handlers still cover it */ }
})();
