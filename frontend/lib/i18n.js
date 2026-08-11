const fs = require("fs");
const path = require("path");

// English is the source language written in the templates; Burmese ("my") is
// looked up from the dictionaries below. Unknown keys fall back to the English
// text itself, so a missing translation can never break a page.
const SUPPORTED = ["en", "my"];
const LOCALES_DIR = path.join(__dirname, "..", "locales", "my");

// The dictionary is split across a few JSON files (common / public / customer /
// warehouse / admin) purely to keep them editable — merged into one map at boot.
let MY = {};
(function load() {
  const merged = {};
  for (const f of fs.readdirSync(LOCALES_DIR)) {
    if (!f.endsWith(".json")) continue;
    Object.assign(merged, JSON.parse(fs.readFileSync(path.join(LOCALES_DIR, f), "utf8")));
  }
  MY = merged;
})();

// "{n} new orders" + {n: 3} → "3 new orders" (any {token} works)
function format(str, vars) {
  if (!vars) return str;
  return String(str).replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined ? String(vars[k]) : m));
}

// Mirrors STATUS_LABELS in server.js, routed through t() so statuses translate.
// "delivered" has no English label on purpose (matches the raw fall-through the
// app always had) — the raw word itself is translatable via the dictionary.
const STATUS_EN = { pending: "Pending", waiting: "Waiting", shipped: "Shipped", cancelled: "Cancelled" };

function middleware(req, res, next) {
  const cookieLang = req.cookies && req.cookies.lang;
  const lang = SUPPORTED.indexOf(cookieLang) !== -1 ? cookieLang : "en";
  const t = (s, vars) => {
    if (s === undefined || s === null) return s;
    const out = lang === "my" && Object.prototype.hasOwnProperty.call(MY, s) ? MY[s] : s;
    return format(out, vars);
  };
  res.locals.lang = lang;
  res.locals.t = t;
  // locale-aware order-status labels (res.locals wins over the app.locals English ones)
  res.locals.statusLabel = (s) => t(STATUS_EN[s] || s);
  res.locals.whStatusLabel = res.locals.statusLabel;
  next();
}

module.exports = { middleware, SUPPORTED };
