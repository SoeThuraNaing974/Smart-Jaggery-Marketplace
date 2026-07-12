const express = require("express");
const multer = require("multer");
const FormData = require("form-data");
const { client } = require("../lib/api");
const { requireRole } = require("../middleware/auth");

const router = express.Router();
const adminOnly = requireRole("admin");
const upload = multer({ storage: multer.memoryStorage() });

// ---------------------------------------------------- dashboard (KPIs+charts)
router.get("/", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [kpis, charts, orders, warehouses] = await Promise.all([
    api.get("/api/admin/kpis"),
    api.get("/api/admin/charts"),
    api.get("/api/admin/orders"),
    api.get("/api/admin/warehouses"),
  ]);
  res.render("admin/dashboard", {
    kpis: kpis.data || {},
    charts: charts.data || { revenue_30d: { labels: [], values: [] }, top_warehouses: { labels: [], values: [] } },
    orders: orders.data || [],
    warehouses: warehouses.data || [],
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// ------------------------------------------------ all orders (search + PDF)
function ordersQuery(req) {
  const from = req.query.from || "", to = req.query.to || "", warehouse = req.query.warehouse || "";
  const qs = [];
  if (from) qs.push("from=" + encodeURIComponent(from));
  if (to) qs.push("to=" + encodeURIComponent(to));
  if (warehouse) qs.push("warehouse=" + encodeURIComponent(warehouse));
  return { from, to, warehouse, qs: qs.length ? "?" + qs.join("&") : "" };
}
router.get("/orders", adminOnly, async (req, res) => {
  const { from, to, qs } = ordersQuery(req);
  const r = await client(req.token).get("/api/admin/orders" + qs);
  res.render("admin/orders", { orders: r.data || [], from, to,
    error: req.query.err || null });
});
router.get("/orders/pdf", adminOnly, async (req, res) => {
  const { qs } = ordersQuery(req);
  const r = await client(req.token).get("/api/admin/orders/pdf" + qs, { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/admin/orders?err=Could+not+generate+PDF");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=orders.pdf");
  res.send(Buffer.from(r.data));
});
// bulk-delete customer orders (from the admin home "Customer Orders of Warehouses" table)
router.post("/orders/delete", adminOnly, async (req, res) => {
  let ids = req.body.order_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  if (!ids.length) return res.redirect("/admin?err=" + encodeURIComponent("Select at least one order"));
  const r = await client(req.token).post("/api/admin/orders/delete", { ids });
  res.redirect("/admin" + (r.status === 200 ? "?msg=Orders+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// ------------------------------------------- all categories (search by date)
router.get("/categories", adminOnly, async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const qs = [];
  if (from) qs.push("from=" + encodeURIComponent(from));
  if (to) qs.push("to=" + encodeURIComponent(to));
  const r = await client(req.token).get("/api/admin/batches" + (qs.length ? "?" + qs.join("&") : ""));
  res.render("admin/categories_all", { batches: r.data || [], from, to });
});

// ----------------------------------------------------------------- insights
router.get("/insights", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [segments, promoAnalytics, perf] = await Promise.all([
    api.get("/api/admin/segments"),
    api.get("/api/admin/promotions/analytics"),
    api.get("/api/admin/warehouses/performance"),
  ]);
  res.render("admin/insights", {
    segments: segments.data || { counts: {}, segments: {} },
    promoAnalytics: promoAnalytics.data || [],
    performance: perf.data || [],
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// --------------------------------------------------------- batch management
// Live notification counts for the admin header (polled by the client):
// new warehouse product requests + new subscription payments.
router.get("/notifications", adminOnly, async (req, res) => {
  try {
    const api = client(req.token);
    const [pr, pay, del, dir] = await Promise.all([
      api.get("/api/admin/product-requests?status=pending"),
      api.get("/api/admin/payments"),
      api.get("/api/admin/deleted-stocks"),
      api.get("/api/admin/directory"),
    ]);
    let requests = 0, payments = 0;
    if (Array.isArray(pr.data) && req.cookies.pr_seen !== undefined) {
      const seen = parseInt(req.cookies.pr_seen, 10) || 0;
      requests = pr.data.filter((p) => Number(p.id) > seen).length;
    }
    const pays = (pay.data && pay.data.payments) || [];
    if (req.cookies.pay_seen !== undefined) {
      const seen = parseInt(req.cookies.pay_seen, 10) || 0;
      payments = pays.filter((p) => Number(p.id) > seen).length;
    }
    const deletedStocks = Array.isArray(del.data) ? del.data.length : 0;
    // newly-registered warehouses / customers since the admin last reviewed Maintain
    const dd = dir.data || {};
    const dWh = Array.isArray(dd.warehouses) ? dd.warehouses : [];
    const dUsers = Array.isArray(dd.users) ? dd.users : [];
    let newWarehouses = 0, newUsers = 0;
    if (req.cookies.wh_acc_seen !== undefined) {
      const seen = parseInt(req.cookies.wh_acc_seen, 10) || 0;
      newWarehouses = dWh.filter((w) => Number(w.id) > seen).length;
    }
    if (req.cookies.user_acc_seen !== undefined) {
      const seen = parseInt(req.cookies.user_acc_seen, 10) || 0;
      newUsers = dUsers.filter((u) => u.role === "customer" && Number(u.id) > seen).length;
    }
    res.json({ requests, payments, deletedStocks, newWarehouses, newUsers });
  } catch (_) {
    res.json({ requests: 0, payments: 0, deletedStocks: 0, newWarehouses: 0, newUsers: 0 });
  }
});

router.get("/batches", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [batches, warehouses, requests, deleted] = await Promise.all([
    api.get("/api/admin/batches"),
    api.get("/api/admin/warehouses"),
    api.get("/api/admin/product-requests?status=pending"),
    api.get("/api/admin/deleted-stocks"),
  ]);
  const reqList = requests.data || [];
  const deletedStocks = Array.isArray(deleted.data) ? deleted.data : [];
  // flag requests that are NEW since the admin's last visit (before updating the marker)
  const prevSeen = parseInt(req.cookies.pr_seen || "0", 10) || 0;
  reqList.forEach((r) => { r.isNew = Number(r.id) > prevSeen; });
  // then mark all current pending requests as "seen" so the header badge clears
  const maxId = reqList.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
  res.cookie("pr_seen", String(maxId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.locals.pendingRequestCount = 0; // hide the badge on this page too
  res.render("admin/batches", {
    batches: batches.data || [], warehouses: warehouses.data || [],
    requests: reqList, deletedStocks,
    added: req.query.added === "1",
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
// Admin acknowledges a warehouse-deleted stock → it disappears from the admin view
router.post("/deleted-stocks/:id/ack", adminOnly, async (req, res) => {
  await client(req.token).post(`/api/admin/deleted-stocks/${req.params.id}/ack`);
  res.redirect("/admin/batches?msg=Deleted+stock+acknowledged");
});
router.post("/deleted-stocks/ack-all", adminOnly, async (req, res) => {
  await client(req.token).post("/api/admin/deleted-stocks/ack-all");
  res.redirect("/admin/batches?msg=All+deleted+stock+acknowledged");
});
router.post("/product-requests/:id/decision", adminOnly, async (req, res) => {
  const r = await client(req.token).post(`/api/admin/product-requests/${req.params.id}/decision`, {
    decision: req.body.decision, note: req.body.note || "",
  });
  // return to whichever page the admin acted from (Operations or Category Management)
  const back = (req.get("Referer") || "").includes("/admin/ops") ? "/admin/ops" : "/admin/batches";
  res.redirect(back + (r.status === 200 ? "?msg=Request+" + req.body.decision : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/batches", adminOnly, async (req, res) => {
  // combine the two halves into the product description shown on the catalogue
  const parts = [];
  if ((req.body.ingredients || "").trim()) parts.push("Ingredients: " + req.body.ingredients.trim());
  if ((req.body.effectiveness || "").trim()) parts.push("Effectiveness: " + req.body.effectiveness.trim());
  const r = await client(req.token).post("/api/admin/batches", {
    warehouse_id: Number(req.body.warehouse_id), batch_id: req.body.batch_id,
    grade: req.body.grade, qty_kg: Number(req.body.qty_kg),
    harvest_date: req.body.harvest_date, price_per_kg: Number(req.body.price_per_kg),
    description: parts.join("\n\n"),
  });
  res.redirect("/admin/batches" + (r.status === 201 ? "?added=1" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/batches/:pk/update", adminOnly, async (req, res) => {
  const body = {
    qty_kg: Number(req.body.qty_kg), price_per_kg: Number(req.body.price_per_kg),
    grade: req.body.grade, is_active: req.body.is_active === "on",
  };
  // Ingredients + Effectiveness are edited as two fields and recombined into the
  // product description (same shape used when a category is created).
  if (req.body.ingredients !== undefined || req.body.effectiveness !== undefined) {
    const parts = [];
    if ((req.body.ingredients || "").trim()) parts.push("Ingredients: " + req.body.ingredients.trim());
    if ((req.body.effectiveness || "").trim()) parts.push("Effectiveness: " + req.body.effectiveness.trim());
    body.description = parts.join("\n\n");
  }
  const r = await client(req.token).put(`/api/admin/batches/${req.params.pk}`, body);
  const fired = r.data && r.data.price_alerts_fired;
  const msg = r.status === 200
    ? "Batch updated" + (fired ? ` (${fired} price alert${fired === 1 ? "" : "s"} fired)` : "")
    : null;
  res.redirect("/admin/batches" + (msg ? "?msg=" + encodeURIComponent(msg) : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/batches/:pk/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/batches/${req.params.pk}`);
  res.redirect("/admin/batches" + (r.status === 200 ? "?msg=Batch+deleted" : "?err=" + encodeURIComponent(r.data.error)));
});
// Upload a jaggery photo for a batch (Node receives via multer, forwards to API)
router.post("/batches/:pk/image", adminOnly, upload.single("file"), async (req, res) => {
  const ajax = req.get("X-Requested-With") === "fetch";
  if (!req.file) {
    if (ajax) return res.status(400).json({ error: "No file chosen" });
    return res.redirect("/admin/batches?err=No+file");
  }
  const form = new FormData();
  form.append("file", req.file.buffer, { filename: req.file.originalname, contentType: req.file.mimetype });
  const r = await client(req.token).post(`/api/admin/batches/${req.params.pk}/image`, form, { headers: form.getHeaders() });
  if (ajax) return res.status(r.status).json(r.data || {});
  res.redirect("/admin/batches" + (r.status === 200 ? "?msg=Image+uploaded" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Upload failed")));
});
router.post("/batches/:pk/image/remove", adminOnly, async (req, res) => {
  const ajax = req.get("X-Requested-With") === "fetch";
  const r = await client(req.token).delete(`/api/admin/batches/${req.params.pk}/image`);
  if (ajax) return res.status(r.status).json(r.data || {});
  res.redirect("/admin/batches?msg=Image+removed");
});
router.post("/batches/:pk/images", adminOnly, upload.array("files", 8), async (req, res) => {
  if (!req.files || !req.files.length) return res.redirect("/admin/batches?err=No+images+chosen");
  const form = new FormData();
  req.files.forEach(f => form.append("files", f.buffer, { filename: f.originalname, contentType: f.mimetype }));
  const r = await client(req.token).post(`/api/admin/batches/${req.params.pk}/images`, form, { headers: form.getHeaders() });
  res.redirect("/admin/batches" + (r.status === 200 ? "?msg=Images+added" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Upload failed")));
});
router.post("/batches/:pk/images/:imgId/delete", adminOnly, async (req, res) => {
  await client(req.token).delete(`/api/admin/batches/${req.params.pk}/images/${req.params.imgId}`);
  res.redirect("/admin/batches?msg=Image+removed");
});

// ------------------------------------------------ subscription plan management
router.get("/subscriptions", adminOnly, async (req, res) => {
  const [plans, subs, payments] = await Promise.all([
    client(req.token).get("/api/admin/subscription-plans"),
    client(req.token).get("/api/admin/subscriptions"),
    client(req.token).get("/api/admin/payments"),
  ]);
  const payList = (payments.data && payments.data.payments) || [];
  // Only show warehouses that have actually bought a package (active or expired).
  // Warehouses that never bought one are left out of the status list.
  const subList = (subs.data || []).filter((s) => s.current);
  // warehouses with NEW payments (new subscription / extension) since last visit
  const prevPaySeen = parseInt(req.cookies.pay_seen || "0", 10) || 0;
  const newWhIds = new Set(payList.filter((p) => Number(p.id) > prevPaySeen).map((p) => p.warehouse_id));
  subList.forEach((s) => { s.isNew = newWhIds.has(s.warehouse_id); });
  // then mark current payments as "seen" so the Subscription header badge clears
  const maxPayId = payList.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
  res.cookie("pay_seen", String(maxPayId), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.locals.newPaymentCount = 0;
  res.render("admin/subscriptions", {
    plans: plans.data || [], subs: subList,
    payments: payList,
    totalCollected: (payments.data && payments.data.total_collected) || 0,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// ----------------- all warehouse subscription statuses (search by start date)
router.get("/subscription-statuses", adminOnly, async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const r = await client(req.token).get("/api/admin/subscriptions");
  // only warehouses that have actually bought a package
  let subs = (r.data || []).filter((s) => s.current);
  // filter by the subscription's start (assigned) date, when a range is given
  if (from || to) {
    subs = subs.filter(s => {
      const d = s.current && s.current.start_date ? s.current.start_date.substring(0, 10) : null;
      if (!d) return false;
      if (from && d < from) return false;
      if (to && d > to) return false;
      return true;
    });
  }
  res.render("admin/subscription_statuses", { subs, from, to,
    flash: req.query.msg || null, error: req.query.err || null });
});

// ------------------------- all subscription payments (search by date)
router.get("/subscription-payments", adminOnly, async (req, res) => {
  // load ALL payments — filtering (by warehouse + date) happens client-side, like the subscriptions page
  const r = await client(req.token).get("/api/admin/payments");
  res.render("admin/subscription_payments", {
    payments: (r.data && r.data.payments) || [],
    totalCollected: (r.data && r.data.total_collected) || 0,
  });
});

router.get("/payments/pdf", adminOnly, async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "", warehouse = req.query.warehouse || "";
  const qs = [];
  if (from) qs.push("from=" + encodeURIComponent(from));
  if (to) qs.push("to=" + encodeURIComponent(to));
  if (warehouse) qs.push("warehouse=" + encodeURIComponent(warehouse));
  const url = "/api/admin/payments/pdf" + (qs.length ? "?" + qs.join("&") : "");
  const r = await client(req.token).get(url, { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/admin/subscription-payments?err=Could+not+generate+PDF");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=payments.pdf");
  res.send(Buffer.from(r.data));
});

router.post("/subscriptions/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/subscriptions/${req.params.id}`);
  res.redirect("/admin/subscriptions" + (r.status === 200 ? "?msg=Package+deleted" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/subscription-plans", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/subscription-plans", {
    name: req.body.name, duration_months: Number(req.body.duration_months), price: Number(req.body.price),
  });
  res.redirect("/admin/subscriptions" + (r.status === 201 ? "?msg=Plan+created" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/subscription-plans/:id/update", adminOnly, async (req, res) => {
  const r = await client(req.token).put(`/api/admin/subscription-plans/${req.params.id}`, {
    name: req.body.name, duration_months: Number(req.body.duration_months),
    price: Number(req.body.price), is_active: req.body.is_active === "on",
  });
  res.redirect("/admin/subscriptions" + (r.status === 200 ? "?msg=Plan+updated" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/subscription-plans/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/subscription-plans/${req.params.id}`);
  res.redirect("/admin/subscriptions" + (r.status === 200 ? "?msg=Plan+deleted" : "?err=" + encodeURIComponent(r.data.error)));
});

// ------------------------------------------------------- advertisements
router.get("/advertisements", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/advertisements");
  res.render("admin/advertisements", {
    ads: r.data || [],
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
// All advertisements with name + date filters (the "See more" page)
router.get("/advertisements-all", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/advertisements");
  let ads = Array.isArray(r.data) ? r.data : [];
  const q = (req.query.q || "").trim(), from = req.query.from || "", to = req.query.to || "";
  if (q) { const ql = q.toLowerCase(); ads = ads.filter((a) => (a.title || "").toLowerCase().includes(ql)); }
  if (from || to) {
    // keep ads whose running window [starts_on, ends_on] overlaps [from, to]
    // (a missing start/end = open-ended; an ad with no dates always matches)
    ads = ads.filter((a) => {
      const s = a.starts_on || "", e = a.ends_on || "";
      if (from && e && e < from) return false;   // ended before the range
      if (to && s && s > to) return false;        // starts after the range
      return true;
    });
  }
  res.render("admin/advertisements_all", { ads, q, from, to });
});
router.post("/advertisements", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/advertisements", {
    title: req.body.title, body: req.body.body, icon: req.body.icon,
    accent: req.body.accent, link_url: req.body.link_url, link_label: req.body.link_label,
    starts_on: req.body.starts_on || null, ends_on: req.body.ends_on || null,
    is_active: req.body.is_active === "on",
  });
  res.redirect("/admin/advertisements" + (r.status === 201 ? "?msg=Advertisement+created" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/advertisements/:id/toggle", adminOnly, async (req, res) => {
  const r = await client(req.token).put(`/api/admin/advertisements/${req.params.id}`, {
    is_active: req.body.is_active === "on",
  });
  res.redirect("/admin/advertisements" + (r.status === 200 ? "?msg=Advertisement+updated" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/advertisements/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/advertisements/${req.params.id}`);
  res.redirect("/admin/advertisements" + (r.status === 200 ? "?msg=Advertisement+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// -------------------------------------------- users & warehouses directory
router.get("/directory", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/directory");
  const d = r.data || {};
  // The Accounts "Users" list shows customer accounts only — warehouse (and
  // admins) are managed under Warehouses, so they're excluded here.
  const users = (d.users || []).filter((u) => u.role === "customer");
  const counts = Object.assign({}, d.counts || {}, {
    users_total: users.length,
    users_active: users.filter((u) => u.active).length,
  });
  res.render("admin/directory", {
    users, warehouses: d.warehouses || [], counts,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
// full lists (the "Read more" pages, with search + Active/Inactive filter)
router.get("/directory/users", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/directory");
  const users = ((r.data && r.data.users) || []).filter((u) => u.role === "customer");
  res.render("admin/directory_users", { users,
    flash: req.query.msg || null, error: req.query.err || null });
});
router.get("/directory/warehouses", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/directory");
  res.render("admin/directory_warehouses", { warehouses: (r.data && r.data.warehouses) || [],
    flash: req.query.msg || null, error: req.query.err || null });
});
// bulk delete (used by both the overview and the full-list pages)
function dirDeleteRedirect(r, back) {
  if (r.status !== 200) return back + "?err=" + encodeURIComponent((r.data && r.data.error) || "Delete failed");
  const d = r.data || {};
  // Nothing actually deleted → report as an error so the in-place handler keeps the row.
  if (!(d.deleted > 0) && d.skipped && d.skipped.length) {
    return back + "?err=" + encodeURIComponent("Couldn't delete: " + d.skipped.join(", "));
  }
  let msg = "Deleted " + (d.deleted || 0);
  if (d.skipped && d.skipped.length) msg += " · couldn't delete " + d.skipped.join(", ");
  return back + "?msg=" + encodeURIComponent(msg);
}
router.post("/directory/users/delete", adminOnly, async (req, res) => {
  let ids = req.body.user_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const back = req.body._back === "all" ? "/admin/directory/users" : "/admin/directory";
  if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one user"));
  const r = await client(req.token).post("/api/admin/users/delete", { ids });
  res.redirect(dirDeleteRedirect(r, back));
});
router.post("/directory/warehouses/delete", adminOnly, async (req, res) => {
  let ids = req.body.wh_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const back = req.body._back === "all" ? "/admin/directory/warehouses" : "/admin/directory";
  if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one warehouse"));
  const r = await client(req.token).post("/api/admin/warehouses/delete", { ids });
  res.redirect(dirDeleteRedirect(r, back));
});

// ---- generic table "Select all" bulk deletes (Operations + Subscriptions pages) ----
function bulkDelete(apiPath, field, back, okMsg) {
  return async (req, res) => {
    let ids = req.body[field] || []; if (!Array.isArray(ids)) ids = [ids];
    ids = ids.map(Number).filter(Boolean);
    if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one item"));
    const r = await client(req.token).post(apiPath, { ids });
    res.redirect(back + (r.status === 200 ? "?msg=" + encodeURIComponent(okMsg) : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
  };
}
router.post("/delivery-charges/bulk-delete", adminOnly, bulkDelete("/api/admin/delivery-charges/delete", "dc_ids", "/admin/ops", "Charges deleted"));
router.post("/announcements/bulk-delete", adminOnly, bulkDelete("/api/admin/announcements/delete", "ann_ids", "/admin/ops", "Announcements deleted"));
router.post("/warehouses/bulk-delete", adminOnly, bulkDelete("/api/admin/warehouses/delete", "wh_ids", "/admin/ops", "Warehouses deleted"));
router.post("/users/bulk-delete", adminOnly, bulkDelete("/api/admin/users/delete", "user_ids", "/admin/ops", "Users deleted"));
router.post("/payments/delete", adminOnly, bulkDelete("/api/admin/payments/delete", "payment_ids", "/admin/subscription-payments", "Payments deleted"));
router.post("/subscription-plans/bulk-delete", adminOnly, bulkDelete("/api/admin/subscription-plans/delete", "plan_ids", "/admin/subscriptions", "Plans deleted"));
router.post("/subscriptions/bulk-delete", adminOnly, async (req, res) => {
  let ids = req.body.sub_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const back = req.body._back === "statuses" ? "/admin/subscription-statuses" : "/admin/subscriptions";
  if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one package"));
  const r = await client(req.token).post("/api/admin/subscriptions/delete", { ids });
  res.redirect(back + (r.status === 200 ? "?msg=Packages+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// ----------------------------------------------------------- operations hub
router.get("/ops", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [warehouses, staff, promos, charges, anns, audit, transfers, carts, preqs, dir] = await Promise.all([
    api.get("/api/admin/warehouses"),
    api.get("/api/admin/staff"),
    api.get("/api/admin/promotions"),
    api.get("/api/admin/delivery-charges"),
    api.get("/api/admin/announcements"),
    api.get("/api/admin/audit-logs?limit=30"),
    api.get("/api/admin/transfers"),
    api.get("/api/admin/abandoned-carts"),
    api.get("/api/admin/product-requests?status=pending"),
    api.get("/api/admin/directory"),
  ]);
  // Flag warehouses/users that registered since the admin last opened Maintain, then
  // mark them seen so the header badge + pop-up clears. New ones are sorted to the top
  // so they're obvious among the rest.
  const whList = warehouses.data || [];
  const userList = (dir.data && dir.data.users) || [];
  const prevWhSeen = parseInt(req.cookies.wh_acc_seen || "0", 10) || 0;
  const prevUserSeen = parseInt(req.cookies.user_acc_seen || "0", 10) || 0;
  whList.forEach((w) => { w.isNew = Number(w.id) > prevWhSeen; });
  userList.forEach((u) => { u.isNew = Number(u.id) > prevUserSeen; });
  whList.sort((a, b) => (b.isNew === true) - (a.isNew === true) || Number(b.id) - Number(a.id));
  userList.sort((a, b) => (b.isNew === true) - (a.isNew === true) || Number(b.id) - Number(a.id));
  const whMax = whList.reduce((m, w) => Math.max(m, Number(w.id) || 0), 0);
  const userMax = userList.reduce((m, u) => Math.max(m, Number(u.id) || 0), 0);
  res.cookie("wh_acc_seen", String(whMax), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.cookie("user_acc_seen", String(userMax), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.locals.newWarehouseCount = 0;
  res.locals.newUserCount = 0;
  res.render("admin/ops", {
    warehouses: whList, staff: staff.data || [], promotions: promos.data || [],
    charges: charges.data || [], announcements: anns.data || [], audit: audit.data || [],
    transfers: transfers.data || [], carts: carts.data || [],
    productRequests: preqs.data || [],
    users: userList,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// --------------------------------------------------------- report exports
function streamProxy(path, contentType, filename) {
  return async (req, res) => {
    const period = req.query.period || "monthly";
    const r = await client(req.token).get(`${path}?period=${encodeURIComponent(period)}`, { responseType: "arraybuffer" });
    if (r.status !== 200) return res.redirect("/admin?err=Export+failed");
    res.setHeader("Content-Type", contentType);
    res.setHeader("Content-Disposition", `attachment; filename=${filename(period)}`);
    res.send(Buffer.from(r.data));
  };
}
router.get("/reports/export", adminOnly, streamProxy("/api/admin/reports/export", "text/csv", p => `sales_${p}.csv`));
router.get("/reports/pdf", adminOnly, streamProxy("/api/admin/reports/pdf", "application/pdf", p => `sales_${p}.pdf`));
router.get("/reports/excel", adminOnly,
  streamProxy("/api/admin/reports/excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", p => `sales_${p}.xlsx`));

// -------------------------------------------------------------- mutations
const back = (res, ok, okMsg, r) =>
  res.redirect((ok ? "?msg=" + encodeURIComponent(okMsg) : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));

// Warehouse detail page (admin)
router.get("/warehouses/:id", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [whs, batches, staff, subs] = await Promise.all([
    api.get("/api/admin/warehouses"),
    api.get("/api/admin/batches?warehouse_id=" + req.params.id),
    api.get("/api/admin/staff"),
    api.get("/api/admin/subscriptions"),
  ]);
  const warehouse = (whs.data || []).find(w => String(w.id) === String(req.params.id));
  if (!warehouse) return res.redirect("/admin/ops?err=Warehouse+not+found");
  res.render("admin/warehouse_detail", {
    warehouse,
    batches: batches.data || [],
    staff: (staff.data || []).filter(s => String(s.warehouse_id) === String(req.params.id)),
    sub: (subs.data || []).find(s => String(s.warehouse_id) === String(req.params.id)) || null,
  });
});

router.post("/warehouses", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/warehouses", req.body);
  res.redirect("/admin/ops" + (r.status === 201 ? "?msg=Warehouse+created" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/warehouses/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/warehouses/${req.params.id}`);
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Deleted" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/users/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/users/delete", { ids: [Number(req.params.id)] });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
// Block / unblock (suspend) — keeps all data, just locks the account.
// Block carries an optional time limit (minutes preset OR an absolute `until` ISO).
const blockProxy = (apiPath, okMsg) => async (req, res) => {
  const body = { minutes: req.body.minutes ? Number(req.body.minutes) : null, until: req.body.until || null };
  const r = await client(req.token).post(apiPath(req.params.id), body);
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=" + encodeURIComponent(okMsg) : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
};
router.post("/users/:id/block", adminOnly, blockProxy((id) => `/api/admin/users/${id}/block`, "User blocked"));
router.post("/users/:id/unblock", adminOnly, blockProxy((id) => `/api/admin/users/${id}/unblock`, "User unblocked"));
router.post("/warehouses/:id/block", adminOnly, blockProxy((id) => `/api/admin/warehouses/${id}/block`, "Warehouse blocked"));
router.post("/warehouses/:id/unblock", adminOnly, blockProxy((id) => `/api/admin/warehouses/${id}/unblock`, "Warehouse unblocked"));
router.post("/staff", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/staff", {
    name: req.body.name, email: req.body.email, password: req.body.password,
    warehouse_id: Number(req.body.warehouse_id),
  });
  res.redirect("/admin/ops" + (r.status === 201 ? "?msg=Staff+created" : "?err=" + encodeURIComponent(r.data.error)));
});
// --------------------------------------------------------- promotion management
router.get("/promotions", adminOnly, async (req, res) => {
  const [promos, analytics] = await Promise.all([
    client(req.token).get("/api/admin/promotions"),
    client(req.token).get("/api/admin/promotions/analytics"),
  ]);
  // index analytics (orders/revenue) by promotion id for display
  const stats = {};
  (analytics.data || []).forEach(a => { stats[a.promotion_id] = a; });
  res.render("admin/promotions", {
    promotions: promos.data || [], stats,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// All promotions (card style, search by date — shows promos running in the range)
router.get("/promotions-all", adminOnly, async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const [promos, analytics] = await Promise.all([
    client(req.token).get("/api/admin/promotions"),
    client(req.token).get("/api/admin/promotions/analytics"),
  ]);
  const stats = {};
  (analytics.data || []).forEach(a => { stats[a.promotion_id] = a; });
  let promotions = promos.data || [];
  if (from || to) {
    promotions = promotions.filter(p => {
      const s = (p.start_date || "").substring(0, 10);
      const e = (p.end_date || "").substring(0, 10);
      if (from && e && e < from) return false;   // ended before the range
      if (to && s && s > to) return false;        // starts after the range
      return true;
    });
  }
  res.render("admin/promotions_all", { promotions, stats, from, to });
});

router.post("/promotions", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/promotions", {
    title: req.body.title, discount_percent: Number(req.body.discount_percent),
    min_qty: Number(req.body.min_qty), start_date: req.body.start_date, end_date: req.body.end_date,
  });
  res.redirect("/admin/promotions" + (r.status === 201 ? "?msg=Promotion+created" : "?err=" + encodeURIComponent(r.data.error)));
});

router.post("/promotions/:id/update", adminOnly, async (req, res) => {
  const r = await client(req.token).put(`/api/admin/promotions/${req.params.id}`, {
    title: req.body.title, discount_percent: Number(req.body.discount_percent),
    min_qty: Number(req.body.min_qty), start_date: req.body.start_date,
    end_date: req.body.end_date, is_active: req.body.is_active === "on",
  });
  res.redirect("/admin/promotions" + (r.status === 200 ? "?msg=Promotion+updated" : "?err=" + encodeURIComponent(r.data.error)));
});

router.post("/promotions/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/promotions/${req.params.id}`);
  res.redirect("/admin/promotions" + (r.status === 200 ? "?msg=Promotion+deleted" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/delivery-charges", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/delivery-charges", {
    pincode: req.body.pincode, charge_amount: Number(req.body.charge_amount),
  });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Charge+saved" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/delivery-charges/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/delivery-charges/${req.params.id}`);
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Charge+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/announcements", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/announcements", {
    title: req.body.title, message: req.body.message, expires_at: req.body.expires_at || null,
  });
  res.redirect("/admin/ops" + (r.status === 201 ? "?msg=Announcement+posted" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/abandoned-carts/delete", adminOnly, async (req, res) => {
  let ids = req.body.cart_ids || [];
  if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const r = await client(req.token).post("/api/admin/abandoned-carts/delete", { ids });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Carts+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/audit-logs/delete", adminOnly, async (req, res) => {
  let ids = req.body.audit_ids || [];
  if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  if (!ids.length) return res.redirect("/admin/ops?err=" + encodeURIComponent("Select at least one log"));
  const r = await client(req.token).post("/api/admin/audit-logs/delete", { ids });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Audit+logs+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/announcements/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/announcements/${req.params.id}`);
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Announcement+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/transfers/delete", adminOnly, async (req, res) => {
  let ids = req.body.transfer_ids || [];
  if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const r = await client(req.token).post("/api/admin/transfers/delete", { ids });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Transfers+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/transfers/:id/decision", adminOnly, async (req, res) => {
  const r = await client(req.token).post(`/api/admin/transfers/${req.params.id}/decision`, { decision: req.body.decision });
  res.redirect("/admin/ops" + (r.status === 200 ? "?msg=Transfer+" + req.body.decision : "?err=" + encodeURIComponent(r.data.error)));
});

// assignment stays on the dashboard
router.post("/orders/:id/assign", adminOnly, async (req, res) => {
  const r = await client(req.token).post(`/api/admin/orders/${req.params.id}/assign`, {
    warehouse_id: Number(req.body.warehouse_id),
  });
  res.redirect("/admin" + (r.status === 200 ? "?msg=Order+assigned" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/backup", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/backup", {}, { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/admin/ops?err=" + encodeURIComponent("Backup failed"));
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=backup_slip.pdf");
  res.send(Buffer.from(r.data));
});
router.post("/email/bulk", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/email/bulk", {
    subject: req.body.subject, body: req.body.body,
  });
  let msg = r.data && r.data.error ? r.data.error
    : r.data.status === "sent" ? `Sent to ${r.data.count} customers`
    : `Dry-run (${r.data.count} recipients) — set SMTP_* in .env to send for real`;
  res.redirect("/admin/ops?msg=" + encodeURIComponent(msg));
});

module.exports = router;
