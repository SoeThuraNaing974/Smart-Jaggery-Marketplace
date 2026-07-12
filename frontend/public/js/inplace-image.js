/* In-place COVER-image change for product cards (admin) and the warehouse stock
   table. Picking a new photo (or removing it) updates the picture right where it
   is — no page reload, no scroll jump. Because the cover is the single
   batch.image_path, this same change shows everywhere in the system at once.
   The inline onchange keeps a `if(!window.__inplaceImage)` guard so the old
   full-submit still works if this script ever fails to load. */
(function () {
  window.__inplaceImage = true;

  // The element that visually represents one product (card OR table row).
  function hostOf(el) {
    return el.closest(".cat-card, .ad-admin-card, tr, li") || el.parentElement;
  }
  function bust(name) { return "/uploads/" + encodeURIComponent(name) + "?t=" + Date.now(); }

  // Update the cover picture inside a host, for either layout.
  function applyCover(host, filename) {
    if (!host) return;
    var thumb = host.querySelector(".cat-thumb");
    if (thumb) {                                   // ---- card layout (admin) ----
      if (filename) {
        var img = thumb.querySelector("img");
        if (!img) { thumb.innerHTML = ""; img = document.createElement("img"); img.alt = "jaggery"; thumb.appendChild(img); }
        img.src = bust(filename);
      } else {
        thumb.innerHTML = '<span class="cat-noimg">No image</span>';
      }
      return;
    }
    var wrap = host.querySelector(".wh-imgs");
    if (wrap) {                                    // ---- warehouse table layout ----
      var cover = wrap.querySelector(".wh-img.cover");
      if (filename) {
        if (!cover) {
          cover = document.createElement("span");
          cover.className = "wh-img cover"; cover.title = "Cover photo";
          var im = document.createElement("img"); im.alt = "cover"; cover.appendChild(im);
          wrap.insertBefore(cover, wrap.firstChild);
        }
        cover.querySelector("img").src = bust(filename);
      } else if (cover) {
        cover.parentNode.removeChild(cover);
      }
    }
  }

  function busy(host, on) {
    var t = host && (host.querySelector(".cat-thumb") || host.querySelector(".wh-img.cover") || host.querySelector(".wh-imgs"));
    if (t) t.classList.toggle("thumb-busy", !!on);
  }

  function toast(msg, bad) {
    var t = document.createElement("div");
    t.className = "inplace-toast" + (bad ? " bad" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("show"); });
    setTimeout(function () { t.classList.remove("show"); setTimeout(function () { t.remove(); }, 280); }, 1900);
  }

  function isCoverUploadForm(form) {
    return /\/batches\/\d+\/image$/.test((form && form.getAttribute("action")) || "");
  }
  function isRemoveForm(form) {
    return /\/batches\/\d+\/image\/remove$/.test((form && form.getAttribute("action")) || "");
  }
  function enableRemoveBtn(host, on) {
    var b = host && host.querySelector('form[action$="/image/remove"] button');
    if (b) b.disabled = !on;
  }

  // ---- UPLOAD / CHANGE cover photo ---------------------------------------
  document.addEventListener("change", function (e) {
    var input = e.target;
    if (!input || input.tagName !== "INPUT" || input.type !== "file") return;
    var form = input.closest("form");
    if (!isCoverUploadForm(form)) return;          // ignore the multi "Add photos" input
    if (!input.files || !input.files.length) return;

    var host = hostOf(form);
    busy(host, true);
    var fd = new FormData();
    fd.append("file", input.files[0]);

    fetch(form.action, {
      method: "POST", body: fd, credentials: "same-origin",
      headers: { "X-Requested-With": "fetch" },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }, function () { return { ok: r.ok, d: {} }; }); })
      .then(function (res) {
        busy(host, false);
        input.value = "";
        if (res.ok && res.d && res.d.image_path) {
          applyCover(host, res.d.image_path);
          enableRemoveBtn(host, true);
          toast("✓ Image updated everywhere");
        } else {
          toast("⚠ " + ((res.d && res.d.error) || "Upload failed"), true);
        }
      })
      .catch(function () {
        busy(host, false);
        window.__inplaceImage = false;             // network failed — fall back to normal submit
        form.submit();
      });
  });

  // ---- REMOVE cover photo (called by confirm.js after the admin confirms) --
  window.__imageRemoveInPlace = function (form) {
    if (!isRemoveForm(form)) return false;
    var host = hostOf(form);
    busy(host, true);
    fetch(form.action, {
      method: "POST", credentials: "same-origin",
      headers: { "X-Requested-With": "fetch" },
    })
      .then(function (r) { return r.ok; })
      .then(function (ok) {
        busy(host, false);
        if (ok) {
          applyCover(host, null);
          var btn = form.querySelector("button");
          if (btn) btn.disabled = true;
          toast("✓ Image removed everywhere");
        } else {
          toast("⚠ Could not remove image", true);
        }
      })
      .catch(function () { busy(host, false); window.__inplaceImage = false; form.submit(); });
    return true;
  };
})();
