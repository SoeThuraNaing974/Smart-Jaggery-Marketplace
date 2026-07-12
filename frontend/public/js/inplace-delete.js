/* Delete in place — no page reload.
   When a delete is confirmed, submit it via fetch and remove the affected item
   straight from the DOM (a table row OR a card). The page never reloads, so you
   stay at the exact same scroll position and any open "view all" pop-up stays open.

   Handles table-row deletes (bulk "Delete selected" + per-row 🗑) AND card deletes
   (advertisements, promotions, Category products). Anything else — photo/sub-item
   removes, cancels, saves — returns false and submits normally. */
(function () {
  // The containers that represent one deletable item.
  var ITEM_SEL = "tr, .cat-card, .promo-card, .ad-admin-card";

  function toast(msg, isErr) {
    var t = document.getElementById("__ipToast");
    if (!t) { t = document.createElement("div"); t.id = "__ipToast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg;
    t.className = "toast show" + (isErr ? " err" : "");
    clearTimeout(t.__t);
    t.__t = setTimeout(function () { t.className = "toast"; }, 2200);
  }

  // The item(s) that should disappear: the checked checkboxes' items (bulk) OR,
  // for a per-row/per-card form, the item the form sits in.
  function targetItems(form) {
    var items = [], checked = [];
    if (form.id) checked = Array.prototype.slice.call(document.querySelectorAll('input[type="checkbox"][form="' + form.id + '"]:checked'));
    checked = checked.concat(Array.prototype.slice.call(form.querySelectorAll('input[type="checkbox"]:checked')));
    if (checked.length) {
      checked.forEach(function (cb) { var el = cb.closest(ITEM_SEL); if (el && items.indexOf(el) === -1) items.push(el); });
    } else {
      var el = form.closest(ITEM_SEL);
      if (el) items.push(el);
    }
    return items;
  }

  // Called by confirm.js after the user clicks "Yes". Returns true if handled in place.
  window.__submitInPlace = function (form) {
    try {
      if (!form || (form.getAttribute("method") || "").toLowerCase() !== "post") return false;
      var action = (form.getAttribute("action") || "").toLowerCase();
      if (/\/images?\//.test(action)) return false;                              // photo/sub-item remove — don't touch the parent
      if (!/(\/delete|\/remove|bulk-delete)(\/|\?|$)/.test(action)) return false; // only genuine delete actions

      var items = targetItems(form);
      if (!items.length) return false;                                           // can't locate the item — submit normally

      var body = new URLSearchParams(new FormData(form));
      items.forEach(function (el) { el.style.opacity = "0.35"; el.style.pointerEvents = "none"; });  // instant feedback

      fetch(form.action || location.href, { method: "POST", body: body, headers: { "X-Requested-With": "fetch" }, redirect: "follow" })
        .then(function (res) { return res.url || ""; })
        .then(function (finalUrl) {
          if (/[?&]err=/.test(finalUrl)) {
            items.forEach(function (el) { el.style.opacity = ""; el.style.pointerEvents = ""; });
            toast(decodeURIComponent((finalUrl.split("err=")[1] || "").split("&")[0].replace(/\+/g, " ")) || "Could not delete", true);
          } else {
            items.forEach(function (el) { if (el.parentNode) el.parentNode.removeChild(el); });
            document.querySelectorAll(".bulk-all, .cart-all, .co-all, .ord-all").forEach(function (m) { m.checked = false; });
            toast("Deleted");
          }
        })
        .catch(function () {
          items.forEach(function (el) { el.style.opacity = ""; el.style.pointerEvents = ""; });
          toast("Could not delete", true);
        });
      return true;
    } catch (e) { return false; }
  };
})();
