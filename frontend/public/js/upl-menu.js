/* "⬆ Upload" popover — pick Cover (single, replaces current) or Photos
   (multiple). Global delegation so it works on every page that renders a
   .upl-menu-wrap, and keeps working after pjax <main> swaps. */
(function () {
  function openMenu() { return document.querySelector(".upl-menu:not([hidden])"); }
  // Keep the trigger's aria-expanded (and its caret flip) in sync with the panel.
  function setOpen(menu, on) {
    if (!menu) return;
    menu.hidden = !on;
    var btn = menu.parentElement.querySelector(".upl-menu-btn");
    if (btn) btn.setAttribute("aria-expanded", on ? "true" : "false");
  }
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".upl-menu-btn");
    if (btn) {
      var menu = btn.parentElement.querySelector(".upl-menu");
      var already = openMenu();
      if (already && already !== menu) setOpen(already, false);
      setOpen(menu, menu.hidden);
      e.stopPropagation();
      return;
    }
    var current = openMenu();
    if (current && !e.target.closest(".upl-menu")) setOpen(current, false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setOpen(openMenu(), false);
  });
  document.addEventListener("change", function (e) {
    if (!e.target.matches(".upl-menu input[type=file]")) return;
    setOpen(e.target.closest(".upl-menu"), false);
  });
})();
