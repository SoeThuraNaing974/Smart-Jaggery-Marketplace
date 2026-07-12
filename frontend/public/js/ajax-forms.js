/* ===================================================================
   System-wide "no reload" engine  (forms + SPA-style link navigation).

   • Every normal POST action (Save, status change, approve, toggle, …)
     is submitted with fetch and only <main> is swapped in place.
   • Every same-origin link click and GET filter form navigates the same
     way — fetch the page, swap <main>, update the URL (Back/Forward
     work), the title, the active nav item, and scroll to top. No reload,
     no white flash.

   Safety:
   • The request ALWAYS reaches the server, so data is never at risk.
   • Anything unusual (cross-page redirect for POST, non-HTML response,
     network error) falls back to a normal full navigation.
   • Forward flows (login, register, logout, checkout, payment, PIN) and
     downloads (PDF/QR/CSV/XLSX/export/backup) navigate for real.
   • Delete/confirm forms and file uploads keep their own handlers.

   Page scripts are torn down & re-run cleanly on every swap (listeners +
   timers tracked between the header/footer markers), so modals, filters
   and charts keep working without double-binding.
   =================================================================== */
(function () {
  if (!window.__L) return;                 // tracker (in <head>) missing → stay on normal navigation
  var L = window.__L;
  var MAIN = "main.container";

  var FULL_NAV = /(^\/login\/?$|^\/register\/?$|^\/logout\/?$|\/cart\/checkout$|\/gateway$|\/pay(\/otp)?$|^\/pin(\/|$)|^\/pin-reset\/|\/subscription\/(pay|otp)$|\/orders\/repeat$|\/export|\/report|\/download|\/backup|\/csv|\/xlsx|\/pdf|\/qr$)/;
  var ASSET = /^\/(uploads|js|css|icons)\//;

  function navStart() { if (window.__nav && window.__nav.start) window.__nav.start(); }
  function navDone() { if (window.__nav && window.__nav.done) window.__nav.done(); }

  // ---- tear down the previous render's page listeners / timers ----
  function teardownPage() {
    (L.listeners || []).forEach(function (l) { try { l.t.removeEventListener(l.type, l.fn, l.opts); } catch (e) {} });
    (L.timers || []).forEach(function (id) { try { clearInterval(id); clearTimeout(id); } catch (e) {} });
    L.listeners = []; L.timers = [];
  }

  function reexecScripts(root) {
    var scripts = root.querySelectorAll("script");
    for (var i = 0; i < scripts.length; i++) {
      var old = scripts[i];
      var s = document.createElement("script");
      for (var a = 0; a < old.attributes.length; a++) s.setAttribute(old.attributes[a].name, old.attributes[a].value);
      s.textContent = old.textContent;
      old.parentNode.replaceChild(s, old);
    }
  }

  function rehydrate(main) { if (window.__rehydrateTables) try { window.__rehydrateTables(main); } catch (e) {} }

  // Keep the nav cart badge in sync (it lives outside <main>).
  function syncCart(parsed) {
    try {
      var link = document.querySelector(".nav-links .cart-link");
      if (!link) return;
      var fresh = parsed.querySelector(".nav-links .cart-count");
      var cur = link.querySelector(".cart-count");
      if (fresh) { if (cur) cur.textContent = fresh.textContent; else link.appendChild(fresh.cloneNode(true)); }
      else if (cur) cur.remove();
    } catch (e) {}
  }

  // On link navigation, update which nav item is highlighted (nav isn't swapped).
  function syncNavActive(parsed) {
    try {
      var freshLinks = parsed.querySelectorAll(".nav-links a[href]");
      var map = {};
      freshLinks.forEach(function (a) { map[a.getAttribute("href")] = a.className; });
      document.querySelectorAll(".nav-links a[href]").forEach(function (a) {
        var c = map[a.getAttribute("href")];
        if (c != null) a.className = c;
      });
    } catch (e) {}
  }

  function loadScript(src) {
    return new Promise(function (res) {
      var s = document.createElement("script"); s.src = src;
      s.onload = res; s.onerror = res; document.head.appendChild(s);
    });
  }
  // Chart.js is only loaded on dashboard pages. If we navigate INTO a chart page
  // from a non-chart page, make sure the library is present before we run its script.
  function ensureCharts(html) {
    if (!/JaggeryCharts|chart\.umd|<canvas/i.test(html)) return Promise.resolve();
    var p = Promise.resolve();
    if (typeof window.Chart === "undefined") p = p.then(function () { return loadScript("https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"); });
    p = p.then(function () { if (typeof window.JaggeryCharts === "undefined") return loadScript("/js/charts.js?v=6"); });
    return p;
  }

  // Swap <main> from fetched HTML. Returns true on success. Scroll is the caller's job.
  function applyMain(parsed) {
    var nm = parsed.querySelector(MAIN), cm = document.querySelector(MAIN);
    if (!nm || !cm) return false;
    teardownPage();
    L.recording = true; L.listeners = []; L.timers = [];
    cm.innerHTML = nm.innerHTML;
    reexecScripts(cm);
    L.recording = false;
    rehydrate(cm);
    syncCart(parsed);
    return true;
  }

  function parse(html) { try { return new DOMParser().parseFromString(html, "text/html"); } catch (e) { return null; } }

  // ============================ FORM ACTIONS ============================
  function shouldSkipForm(form, submitter) {
    if (!form || form.tagName !== "FORM") return true;
    if (form.hasAttribute("data-no-ajax")) return true;
    if ((form.getAttribute("enctype") || "").indexOf("multipart") !== -1) return true;   // uploads
    var tgt = form.getAttribute("target"); if (tgt && tgt !== "_self") return true;
    if (form.hasAttribute("data-confirm")) return true;                                   // confirm.js owns these
    var action = form.getAttribute("action") || location.pathname;
    var path; try { path = new URL(action, location.origin).pathname; } catch (e) { path = action; }
    if (FULL_NAV.test(path)) return true;
    return false;
  }

  // Submit a POST form via fetch and re-render <main> from the server's response,
  // so the page ALWAYS reflects the true database state (a delete that the server
  // couldn't perform stays visible instead of vanishing). Exposed so confirm.js can
  // route confirmed deletes through it.
  function submitPost(form, submitter) {
    var action = (submitter && submitter.getAttribute("formaction")) || form.action || location.href;
    var fd = new FormData(form);
    if (submitter && submitter.name && !fd.has(submitter.name)) fd.append(submitter.name, submitter.value || "");
    var body = new URLSearchParams();
    fd.forEach(function (v, k) { body.append(k, typeof v === "string" ? v : ""); });

    navStart();
    var keepY = window.scrollY || 0;
    fetch(action, { method: "POST", body: body, credentials: "same-origin", headers: { "X-Requested-With": "fetch" }, redirect: "follow" })
      .then(function (r) { return r.text().then(function (t) { return { url: r.url, ct: r.headers.get("content-type") || "", text: t }; }); })
      .then(function (res) {
        // The action returned JSON / non-HTML (an AJAX endpoint like /cart/remove): it
        // already ran on the server, so re-render the CURRENT page to reflect the change.
        if (res.ct.indexOf("text/html") === -1) {
          navDone();
          navigate(location.pathname + location.search, false, keepY);
          return;
        }
        var dest; try { dest = new URL(res.url, location.origin); } catch (e2) { location.href = res.url; return; }
        if (dest.pathname !== location.pathname) { location.href = res.url; return; }   // moved to another page
        var parsed = parse(res.text); if (!parsed) { location.href = res.url; return; }
        try { history.replaceState({ pjax: 1, y: keepY }, "", dest.pathname + dest.search); } catch (e3) {}
        if (!applyMain(parsed)) { location.href = res.url; return; }
        window.scrollTo(0, keepY);
        navDone();
        try { document.dispatchEvent(new CustomEvent("pjax:load")); } catch (e4) {}
      })
      .catch(function () { navDone(); L.recording = false; form.submit(); });
  }
  window.__pjaxForm = submitPost;

  document.addEventListener("submit", function (e) {
    if (e.defaultPrevented) return;                       // confirm.js already handled it
    var form = e.target, submitter = e.submitter;
    if (shouldSkipForm(form, submitter)) return;
    var method = ((submitter && submitter.getAttribute("formmethod")) || form.getAttribute("method") || "get").toLowerCase();
    var action = (submitter && submitter.getAttribute("formaction")) || form.action || location.href;

    // GET form (search / date filter) → navigate in place with the query string
    if (method !== "post") {
      e.preventDefault();
      var u; try { u = new URL(action, location.origin); } catch (er) { return; }
      var fd0 = new FormData(form); var qs = new URLSearchParams();
      fd0.forEach(function (v, k) { if (typeof v === "string") qs.append(k, v); });
      u.search = qs.toString();
      navigate(u.pathname + u.search, true, 0);
      return;
    }

    e.preventDefault();
    submitPost(form, submitter);
  });

  // ============================ LINK NAVIGATION ============================
  function navigate(url, push, scrollY) {
    var abs; try { abs = new URL(url, location.origin); } catch (e) { location.href = url; return; }
    if (abs.origin !== location.origin || ASSET.test(abs.pathname) || FULL_NAV.test(abs.pathname)) { location.href = url; return; }

    navStart();
    fetch(abs.href, { credentials: "same-origin", redirect: "follow" })
      .then(function (r) { return r.text().then(function (t) { return { url: r.url, ct: r.headers.get("content-type") || "", text: t }; }); })
      .then(function (res) {
        var dest; try { dest = new URL(res.url, location.origin); } catch (e) { location.href = res.url; return; }
        if (dest.origin !== location.origin || res.ct.indexOf("text/html") === -1 || FULL_NAV.test(dest.pathname)) { location.href = res.url; return; }
        return ensureCharts(res.text).then(function () {
          var parsed = parse(res.text); if (!parsed) { location.href = res.url; return; }
          if (!applyMain(parsed)) { location.href = res.url; return; }
          var ttl = parsed.querySelector("title"); if (ttl) document.title = ttl.textContent;
          syncNavActive(parsed);
          var t = document.getElementById("navToggle"); if (t) t.checked = false;   // close mobile menu
          if (push) { try { history.pushState({ pjax: 1, y: 0 }, "", dest.pathname + dest.search); } catch (e) {} }
          window.scrollTo(0, scrollY || 0);
          navDone();
          try { document.dispatchEvent(new CustomEvent("pjax:load")); } catch (e) {}
        });
      })
      .catch(function () { navDone(); location.href = url; });
  }

  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    if (a.target && a.target !== "_self") return;
    if (a.hasAttribute("download") || a.hasAttribute("data-no-ajax")) return;
    var href = a.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#" || /^(javascript:|mailto:|tel:)/i.test(href)) return;
    var u; try { u = new URL(a.href, location.href); } catch (er) { return; }
    if (u.origin !== location.origin) return;
    if (ASSET.test(u.pathname) || FULL_NAV.test(u.pathname)) return;
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return;   // same-page anchor
    e.preventDefault();
    try { history.replaceState({ pjax: 1, y: window.scrollY || 0 }, "", location.pathname + location.search); } catch (er2) {}
    navigate(u.pathname + u.search, true, 0);
  });

  window.addEventListener("popstate", function (e) {
    var y = (e.state && e.state.y) || 0;
    navigate(location.pathname + location.search, false, y);
  });
})();
