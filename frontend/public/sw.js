/* Service worker for "Smart Jaggery Mart" PWA.
   - Pre-caches the static app shell (CSS, JS, icons) for fast loads + basic offline.
   - Pages (HTML) use network-first so logged-in users always get fresh, correct data;
     if offline, a simple fallback message is shown.
   - Static assets use cache-first. */
const CACHE = "jaggery-pwa-v78";
const SHELL = [
  "/css/style.css?v=196",
  "/js/charts.js?v=6",
  "/js/confirm.js?v=6",
  "/js/responsive-tables.js?v=3",
  "/js/nav-progress.js?v=2",
  "/js/inplace-delete.js?v=2",
  "/js/inplace-image.js?v=3",
  "/js/ajax-forms.js?v=6",
  "/js/bulk-select.js?v=1",
  "/js/phone.js?v=1",
  "/js/scroll-keep.js?v=1",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return /\/(css|js|icons)\//.test(url.pathname) || url.pathname === "/manifest.webmanifest";
}

// Only store a response if it's genuinely the asset we asked for. A tunnel/proxy
// (e.g. ngrok's free browser-warning page) can answer a .css/.js request with a 200
// HTML page; caching that would "stick" the broken styling. Guard against it.
function responseLooksValid(url, res) {
  if (!res || !res.ok || res.type === "opaque") return false;
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (/\.css(\?|$)/.test(url.pathname)) return ct.includes("text/css");
  if (/\.js(\?|$)/.test(url.pathname)) return ct.includes("javascript");
  return true;  // icons, manifest — trust the 200
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                 // never cache POSTs (logins, orders, etc.)
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // only handle same-origin

  // static assets → cache-first, but only cache a response that's truly that asset
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (responseLooksValid(url, res)) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => hit))
    );
    return;
  }

  // pages & everything else → network-first, fall back to cache/offline note
  event.respondWith(
    fetch(req).catch(() =>
      caches.match(req).then((hit) =>
        hit || new Response(
          // charset must be declared BOTH in the header and the document — without
          // it the browser decodes the Burmese text as Latin-1 (mojibake).
          "<!doctype html><html><head><meta charset='utf-8'>" +
          "<meta name='viewport' content='width=device-width, initial-scale=1'><title>Offline</title></head><body>" +
          "<h2 style='font-family:sans-serif;color:#7a4a1e;text-align:center;margin-top:3rem'>You are offline &middot; အင်တာနက် ချိတ်ဆက်မှု မရှိပါ</h2>" +
          "<p style='font-family:sans-serif;color:#888;text-align:center'>Reconnect to use Smart Jaggery Mart.<br>Smart Jaggery Mart ကို သုံးရန် ပြန်လည်ချိတ်ဆက်ပါ။</p>" +
          "</body></html>",
          { headers: { "Content-Type": "text/html; charset=utf-8" } }
        )
      )
    )
  );
});
