/* Global, attractive confirmation dialog (replaces the browser's native confirm()).
   Triggers on:
     1) any <form data-confirm="message"> — shows that message, and
     2) ANY delete/remove button or form (action contains /delete or /remove, or the
        clicked button says delete/remove/🗑) — even without data-confirm.
   The form only submits if the user confirms. */
(function () {
  var modal = document.getElementById("confirmModal");
  if (!modal) return;
  var msgEl = document.getElementById("confirmMsg");
  var titleEl = document.getElementById("confirmTitle");
  var icoEl = document.getElementById("confirmIco");
  var okBtn = document.getElementById("confirmOk");
  var cancelBtn = document.getElementById("confirmCancel");
  var pending = null;

  // remember which button activated the submit (to read its label)
  var lastSubmitter = null;
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest('button[type="submit"], input[type="submit"], button:not([type])');
    if (b) lastSubmitter = b;
  }, true);

  function isDeleteIntent(form, submitter) {
    var action = (form.getAttribute("action") || "").toLowerCase();
    if (/\/(delete|remove)(\/|\b|$)/.test(action)) return true;
    var txt = submitter ? (submitter.textContent || submitter.value || "") : "";
    return /(delete|remove|🗑)/i.test(txt);
  }

  function open(msg, form, del) {
    // window.__i18n is injected by the header in the user's chosen language;
    // the English literals stay as fallbacks if it's ever missing.
    var T = window.__i18n || {};
    icoEl.textContent = del ? "🗑️" : "❓";
    titleEl.textContent = del ? (T.delTitle || "Delete this?") : (T.confirmTitle || "Please confirm");
    msgEl.textContent = msg || (del ? (T.delMsg || "This item will be permanently deleted. This can't be undone.")
                                    : (T.confirmMsg || "Are you sure you want to continue?"));
    okBtn.textContent = del ? (T.delOk || "🗑️ Yes, delete") : (T.otherOk || "✓ Yes, continue");
    modal.classList.toggle("is-other", !del);
    pending = form;
    modal.style.display = "flex";
    setTimeout(function () { okBtn.focus(); }, 30);
  }
  function close() { modal.style.display = "none"; pending = null; }

  // Intercept submits (capture phase, before other handlers).
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!f || !f.getAttribute || f.dataset.confirmed === "1") return;
    var submitter = e.submitter || lastSubmitter;
    var dc = f.getAttribute("data-confirm");
    if (dc) {
      e.preventDefault(); e.stopPropagation();
      var verb = (dc || "").trim().split(/\s+/)[0].toLowerCase();
      open(dc, f, verb === "delete" || verb === "remove");
    } else if (isDeleteIntent(f, submitter)) {
      e.preventDefault(); e.stopPropagation();
      open(null, f, true);
    }
  }, true);

  okBtn.addEventListener("click", function () {
    var f = pending; close();
    if (!f) return;
    f.dataset.confirmed = "1";
    // Cover-photo remove → update the card thumbnail in place (no reload).
    if (window.__imageRemoveInPlace && window.__imageRemoveInPlace(f)) return;
    // Delete via the no-reload engine: it submits to the server and re-renders the
    // page from the server's ACTUAL response — so an item only disappears if it was
    // really removed from the database (a blocked/skipped delete stays visible, with
    // a message), keeping the screen and the database always in sync.
    if (window.__pjaxForm) { window.__pjaxForm(f); return; }
    if (window.__submitInPlace && window.__submitInPlace(f)) return;  // fallback (no engine)
    f.submit();  // last-resort full submit
  });
  cancelBtn.addEventListener("click", close);
  modal.addEventListener("click", function (e) { if (e.target === modal) close(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.style.display === "flex") close();
  });
})();
