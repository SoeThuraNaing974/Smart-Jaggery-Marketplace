/* Generic "Select all" for any delete table.
   Markup:
     <input type="checkbox" class="bulk-all" data-group="G">           (in a <th>)
     <input type="checkbox" class="bulk-cb" data-group="G" form="F">   (one per row)
     <form id="F" action="..." method="post" data-confirm="...">       (standalone bulk-delete form)
     <button form="F" type="submit">Delete selected</button>
   The master ticks only the visible rows of its group; rows hidden by a filter are
   never submitted because the master/individual sync ignores them. */
(function () {
  function boxes(group) {
    return Array.prototype.slice.call(document.querySelectorAll('.bulk-cb[data-group="' + group + '"]'));
  }
  function visible(group) {
    return boxes(group).filter(function (cb) {
      var tr = cb.closest('tr');
      return !tr || tr.style.display !== 'none';
    });
  }
  document.querySelectorAll('.bulk-all').forEach(function (master) {
    master.addEventListener('change', function () {
      visible(master.dataset.group).forEach(function (cb) { cb.checked = master.checked; });
    });
  });
  // keep each master in sync when individual boxes change
  document.addEventListener('change', function (e) {
    var cb = e.target;
    if (!cb || !cb.classList || !cb.classList.contains('bulk-cb')) return;
    var master = document.querySelector('.bulk-all[data-group="' + cb.dataset.group + '"]');
    if (!master) return;
    var v = visible(cb.dataset.group);
    master.checked = v.length > 0 && v.every(function (b) { return b.checked; });
  });
})();
