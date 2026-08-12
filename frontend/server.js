// Load .env from this file's own folder so the server works no matter which
// directory it is started from (e.g. `node frontend/server.js` from the repo root).
require("dotenv").config({ path: require("path").join(__dirname, ".env") });
const path = require("path");
const express = require("express");
const cookieParser = require("cookie-parser");
const compression = require("compression");

const { attachUser } = require("./middleware/auth");
const { client } = require("./lib/api");
const i18n = require("./lib/i18n");

const app = express();

// gzip every HTML/CSS/JS response — much smaller transfers = faster page loads,
// especially over a slow/remote connection.
app.use(compression());

// When hosted behind a TLS proxy (Render/Railway/Nginx), trust it so secure cookies
// and req.protocol=https work correctly. Harmless in local development.
app.set("trust proxy", 1);

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

// Friendly order-status labels (shared across warehouse, customer & admin views).
// The underlying status value is unchanged — only the text shown to users.
// Payment-driven flow: pending (unpaid) → waiting (paid) → shipped (+ cancelled).
const STATUS_LABELS = { pending: "Pending", waiting: "Waiting", shipped: "Shipped", cancelled: "Cancelled" };
app.locals.statusLabel = (s) => STATUS_LABELS[s] || s;
const WH_STATUS_LABELS = STATUS_LABELS;
app.locals.whStatusLabel = (s) => WH_STATUS_LABELS[s] || s;

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());
// Language (English / Burmese): reads the "lang" cookie and gives every view
// t(), lang and locale-aware status labels. Must run before any route renders.
app.use(i18n.middleware);
app.use(express.static(path.join(__dirname, "public"), { maxAge: "30d", etag: true }));
// Never cache rendered HTML pages — prevents the browser showing a stale page
// after edits/redirects. (Static assets above still cache + use ?v= versioning.)
app.use((req, res, next) => {
  res.set("Cache-Control", "no-store, must-revalidate");
  next();
});
app.use(attachUser);

// Header notification badges (admin: pending requests + new payments;
// customer: newly-added categories the customer hasn't browsed yet).
app.use(async (req, res, next) => {
  res.locals.pendingRequestCount = 0;
  res.locals.newPaymentCount = 0;
  res.locals.newCategoryCount = 0;
  res.locals.orderUpdateCount = 0;
  res.locals.whCategoryCount = 0;
  res.locals.whPlanCount = 0;
  res.locals.whOrderCount = 0;
  res.locals.whDeletedCount = 0;
  res.locals.whDeletedItems = [];
  res.locals.deletedStockCount = 0;
  res.locals.newWarehouseCount = 0;
  res.locals.newUserCount = 0;
  // The JWT doesn't carry the avatar; fetch the current user so the header can show
  // their real photo (all roles). Cheap call; falls back to an initial if none.
  if (req.user && req.token) {
    try {
      const me = await client(req.token).get("/api/me");
      if (me.data && me.data.user) {
        req.user.avatar_path = me.data.user.avatar_path || null;
        req.user.blocked = !!me.data.user.blocked;   // admin "Block" — locked out
        req.user.blocked_until = me.data.user.blocked_until || null;   // optional auto-expiry
        // The JWT carries the name from login, so it goes stale after a profile rename.
        // Sync the live DB name so the header (and anywhere using res.locals.user) updates.
        if (me.data.user.name) req.user.name = me.data.user.name;
      }
    } catch (_) { /* keep going without a photo */ }
  }
  // A blocked account does nothing but read the notice + log out, so skip the badge work.
  if (req.user && req.user.blocked) return next();
  if (req.user && req.user.role === "admin" && req.token) {
    try {
      const api = client(req.token);
      const [pr, pay, del, dir] = await Promise.all([
        api.get("/api/admin/product-requests?status=pending"),
        api.get("/api/admin/payments"),
        api.get("/api/admin/deleted-stocks"),
        api.get("/api/admin/directory"),
      ]);
      // stocks a warehouse deleted that the admin hasn't acknowledged yet → alarm badge
      res.locals.deletedStockCount = Array.isArray(del.data) ? del.data.length : 0;
      // new warehouse product requests not yet seen → Category badge
      if (Array.isArray(pr.data)) {
        if (req.cookies.pr_seen === undefined) {
          const maxId = pr.data.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
          res.cookie("pr_seen", String(maxId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
          req.cookies.pr_seen = String(maxId);
        } else {
          const seenMax = parseInt(req.cookies.pr_seen, 10) || 0;
          res.locals.pendingRequestCount = pr.data.filter((p) => Number(p.id) > seenMax).length;
        }
      }
      // new subscription payments not yet seen → Subscription badge
      const payments = (pay.data && pay.data.payments) || [];
      if (req.cookies.pay_seen === undefined) {
        const maxId = payments.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
        res.cookie("pay_seen", String(maxId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
        req.cookies.pay_seen = String(maxId);
      } else {
        const paySeen = parseInt(req.cookies.pay_seen, 10) || 0;
        res.locals.newPaymentCount = payments.filter((p) => Number(p.id) > paySeen).length;
      }
      // newly-registered warehouses / customers not yet reviewed → Maintain badge + popup
      const dirData = dir.data || {};
      const dirWh = Array.isArray(dirData.warehouses) ? dirData.warehouses : [];
      const dirUsers = Array.isArray(dirData.users) ? dirData.users : [];
      if (req.cookies.wh_acc_seen === undefined) {
        const maxId = dirWh.reduce((m, w) => Math.max(m, Number(w.id) || 0), 0);
        res.cookie("wh_acc_seen", String(maxId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
        req.cookies.wh_acc_seen = String(maxId);
      } else {
        const seen = parseInt(req.cookies.wh_acc_seen, 10) || 0;
        res.locals.newWarehouseCount = dirWh.filter((w) => Number(w.id) > seen).length;
      }
      if (req.cookies.user_acc_seen === undefined) {
        const maxId = dirUsers.reduce((m, u) => Math.max(m, Number(u.id) || 0), 0);
        res.cookie("user_acc_seen", String(maxId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
        req.cookies.user_acc_seen = String(maxId);
      } else {
        const seen = parseInt(req.cookies.user_acc_seen, 10) || 0;
        // only count self-registered customers (warehouse arrive via warehouse registration)
        res.locals.newUserCount = dirUsers.filter((u) => u.role === "customer" && Number(u.id) > seen).length;
      }
    } catch (_) { /* ignore — badges just won't show */ }
  } else if (req.user && req.user.role === "customer" && req.token) {
    try {
      const api = client(req.token);
      const [b, ord] = await Promise.all([
        api.get("/api/batches"),
        api.get("/api/orders"),
      ]);
      // --- new categories (Category badge) ---
      if (Array.isArray(b.data)) {
        if (req.cookies.cat_seen === undefined) {
          // First load anywhere: set a baseline so notifications can reach the header on
          // EVERY page (not only after the customer opens the Category page). Nothing is
          // "new" yet — only categories added after this point will light up the badge.
          const maxId = b.data.reduce((m, x) => Math.max(m, Number(x.id) || 0), 0);
          res.cookie("cat_seen", String(maxId), { httpOnly: true, sameSite: "lax" });
          req.cookies.cat_seen = String(maxId); // so this same request reads the baseline
        } else {
          const catSeen = parseInt(req.cookies.cat_seen, 10) || 0;
          res.locals.newCategoryCount = b.data.filter((x) => Number(x.id) > catSeen).length;
        }
      }
      // --- order shipped/delivered updates (My Order badge) ---
      const orders = Array.isArray(ord.data) ? ord.data : [];
      const keys = orders
        .filter((o) => o.status === "shipped" || o.status === "delivered")
        .map((o) => o.id + ":" + o.status);
      if (req.cookies.ord_seen === undefined) {
        // baseline on first load: existing shipped/delivered orders aren't "new"
        res.cookie("ord_seen", keys.join(","), { httpOnly: true, sameSite: "lax" });
        req.cookies.ord_seen = keys.join(",");
      } else {
        const seen = new Set((req.cookies.ord_seen || "").split(",").filter(Boolean));
        res.locals.orderUpdateCount = keys.filter((k) => !seen.has(k)).length;
      }
    } catch (_) { /* ignore — badges just won't show */ }
  } else if (req.user && req.user.role === "warehouse" && req.token) {
    try {
      const api = client(req.token);
      const [stock, plans, orders] = await Promise.all([
        api.get("/api/warehouse/stock"),
        api.get("/api/warehouse/subscription-plans"),
        api.get("/api/warehouse/orders"),
      ]);
      const batches = (stock.data && stock.data.batches) || [];
      const planList = Array.isArray(plans.data) ? plans.data : [];
      // a "new order" for the warehouse = a paid (waiting) order it hasn't checked yet
      // (tracked by id-set so it fires when an order becomes paid, not just when created)
      const waitingKeys = (Array.isArray(orders.data) ? orders.data : [])
        .filter((o) => o.status === "waiting").map((o) => String(o.id));
      if (req.cookies.wh_order_seen === undefined) {
        res.cookie("wh_order_seen", waitingKeys.join(","), { httpOnly: true, sameSite: "lax" });
        req.cookies.wh_order_seen = waitingKeys.join(",");
      } else {
        const seen = new Set((req.cookies.wh_order_seen || "").split(",").filter(Boolean));
        res.locals.whOrderCount = waitingKeys.filter((k) => !seen.has(k)).length;
      }
      // new product categories in this warehouse's own stock (e.g. an approved request)
      if (req.cookies.wh_cat_seen === undefined) {
        const maxB = batches.reduce((m, x) => Math.max(m, Number(x.id) || 0), 0);
        res.cookie("wh_cat_seen", String(maxB), { httpOnly: true, sameSite: "lax" });
        req.cookies.wh_cat_seen = String(maxB);
      } else {
        const cs = parseInt(req.cookies.wh_cat_seen, 10) || 0;
        res.locals.whCategoryCount = batches.filter((x) => Number(x.id) > cs).length;
      }
      // new subscription plans the admin has published
      if (req.cookies.wh_plan_seen === undefined) {
        const maxP = planList.reduce((m, x) => Math.max(m, Number(x.id) || 0), 0);
        res.cookie("wh_plan_seen", String(maxP), { httpOnly: true, sameSite: "lax" });
        req.cookies.wh_plan_seen = String(maxP);
      } else {
        const ps = parseInt(req.cookies.wh_plan_seen, 10) || 0;
        res.locals.whPlanCount = planList.filter((x) => Number(x.id) > ps).length;
      }
      // categories the ADMIN removed from this warehouse — alarm until dismissed.
      // No first-load baseline on purpose: a deletion must always be seen once.
      const adminDeleted = (stock.data && stock.data.admin_deleted) || [];
      const delSeen = new Set((req.cookies.wh_del_seen || "").split(",").filter(Boolean));
      const unseenDeleted = adminDeleted.filter((b) => !delSeen.has(String(b.id)));
      res.locals.whDeletedCount = unseenDeleted.length;
      res.locals.whDeletedItems = unseenDeleted;
    } catch (_) { /* ignore — badges just won't show */ }
  }
  next();
});

// Gate: a blocked account is shown the notice on EVERY page and can do nothing
// but log out. (Static assets are served earlier; /api/me + logout still work.)
app.use((req, res, next) => {
  if (req.user && req.user.blocked && req.path !== "/logout") {
    return res.status(403).render("blocked", { user: req.user });
  }
  next();
});

// "Stay in place" after list/card actions ----------------------------------
// Management actions (delete, update, block, status change, …) normally redirect
// to a FIXED source page, which bounces the admin off whichever "view all" page
// they were on and jumps to the top. Instead, send them back to the page they
// submitted from (the Referer), carrying the flash message, so they stay exactly
// where they were (scroll-keep.js then restores the scroll position).
// Auth + commerce-flow endpoints are excluded — those must move forward.
const STAY_FLOW_PATHS = /(^\/login\/?$|^\/register\/?$|^\/logout\/?$|\/cart\/checkout$|\/gateway$|\/pay(\/otp)?$|^\/pin(\/|$)|^\/pin-reset\/|\/subscription\/(pay|otp)$|\/orders\/repeat$)/;
app.use((req, res, next) => {
  // let any page show a flash toast after a redirect
  if (res.locals.flash === undefined && req.query.msg) res.locals.flash = String(req.query.msg);
  if (res.locals.error === undefined && req.query.err) res.locals.error = String(req.query.err);

  if (req.method === "POST" && !STAY_FLOW_PATHS.test(req.path)) {
    const ref = req.get("Referer");
    if (ref) {
      const orig = res.redirect.bind(res);
      res.redirect = (url) => {
        try {
          const dest = new URL(ref);
          if (dest.host === req.headers.host) {
            const tgt = new URL(String(url), dest.origin);          // intended target (for its flash)
            ["msg", "err", "added", "paid", "ok"].forEach((k) => dest.searchParams.delete(k));
            tgt.searchParams.forEach((v, k) => dest.searchParams.set(k, v));
            return orig(dest.pathname + dest.search);               // back to the SAME page
          }
        } catch (e) { /* malformed referer — fall through */ }
        return orig(url);
      };
    }
  }
  next();
});

// Language switcher: set the cookie, then send the user straight back to the
// page they were on (same-host Referer only). Works for guests and all roles.
app.get("/lang/:code", (req, res) => {
  const code = i18n.SUPPORTED.indexOf(req.params.code) !== -1 ? req.params.code : "en";
  res.cookie("lang", code, { sameSite: "lax", maxAge: 31536000000 });
  const ref = req.get("Referer");
  if (ref) {
    try {
      const u = new URL(ref);
      if (u.host === req.headers.host) return res.redirect(u.pathname + u.search);
    } catch (_) { /* malformed referer — fall through */ }
  }
  return res.redirect("/");
});

// routes
app.use("/", require("./routes/auth"));
app.use("/", require("./routes/customer"));
app.use("/warehouse", require("./routes/warehouse"));
app.use("/admin", require("./routes/admin"));

// Serve uploaded files (product images, certificates, avatars) THROUGH the frontend,
// so the browser only ever talks to this origin. This makes images load correctly on
// phones/other devices over the LAN (they can't reach the API's 127.0.0.1 directly).
app.get("/uploads/:file", async (req, res) => {
  try {
    const r = await client(req.token).get("/uploads/" + encodeURIComponent(req.params.file),
      { responseType: "arraybuffer" });
    if (r.status !== 200) return res.sendStatus(404);
    if (r.headers["content-type"]) res.setHeader("Content-Type", r.headers["content-type"]);
    res.setHeader("Cache-Control", "public, max-age=86400");
    return res.send(Buffer.from(r.data));
  } catch (_) {
    return res.sendStatus(404);
  }
});

app.get("/", (req, res) => {
  if (!req.user) return res.redirect("/login");
  if (req.user.role === "admin") return res.redirect("/admin");
  if (req.user.role === "warehouse") return res.redirect("/warehouse");
  return res.redirect("/dashboard");
});

app.use((req, res) => res.status(404).render("error", { message: "Page not found." }));

// An async route that throws (e.g. the Flask API is down/restarting → axios
// ECONNREFUSED) must not kill the whole website for everyone — that request
// fails, the server stays up and recovers as soon as the API is back.
process.on("unhandledRejection", (err) => {
  console.error("[frontend] unhandled rejection (request failed, server kept alive):",
    (err && err.message) || err);
});
process.on("uncaughtException", (err) => {
  console.error("[frontend] uncaught exception (server kept alive):", (err && err.stack) || err);
});

const PORT = process.env.PORT || 3000;
// 0.0.0.0 = listen on all network interfaces so other devices (your phone) on the
// same Wi-Fi can open the site at http://<your-laptop-ip>:3000
app.listen(PORT, "0.0.0.0", () => console.log(`Frontend running on http://localhost:${PORT} (and on your LAN IP for phones)`));
