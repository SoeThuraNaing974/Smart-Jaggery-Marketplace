const express = require("express");
const multer = require("multer");
const FormData = require("form-data");
const { client } = require("../lib/api");
const { requireRole } = require("../middleware/auth");
const { MM_CITIES, COUNTRIES } = require("../lib/locations");
const { GRADE_INFO } = require("../lib/gradeInfo");

const router = express.Router();
const adminOnly = requireRole("admin");
const upload = multer({ storage: multer.memoryStorage() });

// ---------------------------------------------------- dashboard (KPIs+charts)
router.get("/", adminOnly, async (req, res) => {
  const api = client(req.token);
  const [kpis, charts] = await Promise.all([
    api.get("/api/admin/kpis"),
    api.get("/api/admin/charts"),
  ]);
  res.render("admin/dashboard", {
    kpis: kpis.data || {},
    charts: charts.data || { revenue_30d: { labels: [], values: [] }, top_warehouses: { labels: [], values: [] } },
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
  const [batches, warehouses, requests, deleted, approved] = await Promise.all([
    api.get("/api/admin/batches"),
    api.get("/api/admin/warehouses"),
    api.get("/api/admin/product-requests?status=pending"),
    api.get("/api/admin/deleted-stocks"),
    api.get("/api/admin/product-requests?status=approved"),
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
    approvedRequests: approved.data || [],
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
  res.redirect("/admin/batches" + (r.status === 200 ? "?msg=Request+" + req.body.decision : "?err=" + encodeURIComponent(r.data.error)));
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
  // name + production date are edited on the card; skip when left empty so the
  // backend never receives a blank name or an unparseable date
  if ((req.body.batch_id || "").trim()) body.batch_id = req.body.batch_id.trim();
  if ((req.body.harvest_date || "").trim()) body.harvest_date = req.body.harvest_date.trim();
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
  res.redirect("/admin/batches" + (r.status === 200
    ? "?msg=" + encodeURIComponent((r.data && r.data.message) || "Batch deleted")
    : "?err=" + encodeURIComponent(r.data.error)));
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
  // Only show warehouses that have actually bought a subscription (active or expired).
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
  // only warehouses that have actually bought a subscription
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
  res.redirect("/admin/subscriptions" + (r.status === 200 ? "?msg=Subscription+deleted" : "?err=" + encodeURIComponent(r.data.error)));
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
  // Mark newly-registered warehouses/users as seen so the header badge + pop-up
  // clears (this page is where new registrations are reviewed).
  const whMax = (d.warehouses || []).reduce((m, w) => Math.max(m, Number(w.id) || 0), 0);
  const userMax = users.reduce((m, u) => Math.max(m, Number(u.id) || 0), 0);
  res.cookie("wh_acc_seen", String(whMax), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.cookie("user_acc_seen", String(userMax), { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.locals.newWarehouseCount = 0;
  res.locals.newUserCount = 0;
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
router.post("/delivery-charges/bulk-delete", adminOnly, bulkDelete("/api/admin/delivery-charges/delete", "dc_ids", "/admin/delivery-charges", "Charges deleted"));
router.post("/announcements/bulk-delete", adminOnly, bulkDelete("/api/admin/announcements/delete", "ann_ids", "/admin/announcements", "Announcements deleted"));
router.post("/payments/delete", adminOnly, bulkDelete("/api/admin/payments/delete", "payment_ids", "/admin/subscription-payments", "Payments deleted"));
router.post("/subscription-plans/bulk-delete", adminOnly, bulkDelete("/api/admin/subscription-plans/delete", "plan_ids", "/admin/subscriptions", "Plans deleted"));
router.post("/subscriptions/bulk-delete", adminOnly, async (req, res) => {
  let ids = req.body.sub_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const back = req.body._back === "statuses" ? "/admin/subscription-statuses" : "/admin/subscriptions";
  if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one subscription"));
  const r = await client(req.token).post("/api/admin/subscriptions/delete", { ids });
  res.redirect(back + (r.status === 200 ? "?msg=Subscriptions+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// ------------------------------------------- delivery charges & announcements
// Each split out of the operations hub onto its own page.
router.get("/delivery-charges", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/delivery-charges");
  res.render("admin/delivery_charges", {
    charges: r.data || [],
    // same lists the customer picks from at checkout, so every amount priced here
    // matches a location a customer can actually choose ("Foreign" = catch-all)
    localCities: MM_CITIES,
    countries: COUNTRIES,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.get("/announcements", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/admin/announcements");
  res.render("admin/announcements", {
    announcements: r.data || [],
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// --------------------------------------------------------- About Us page editor
// The public /about page shows the saved fields; blank fields fall back to the
// built-in bilingual text (reached from the "Edit this page" button on /about).
router.get("/about-edit", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/content/about");
  res.render("admin/about_edit", {
    c: (r.status === 200 && r.data && typeof r.data === "object") ? r.data : {},
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.post("/about-edit", adminOnly, async (req, res) => {
  const r = await client(req.token).put("/api/admin/content/about", {
    headline_a: req.body.headline_a || "", headline_b: req.body.headline_b || "",
    hero_sub: req.body.hero_sub || "",
    who_p1: req.body.who_p1 || "", who_p2: req.body.who_p2 || "",
    contact_blurb: req.body.contact_blurb || "", contact_email: req.body.contact_email || "",
  });
  res.redirect(r.status === 200 ? "/about?msg=About+page+updated"
    : "/admin/about-edit?err=" + encodeURIComponent((r.data && r.data.error) || "Failed"));
});

// ------------------------------------------------ grade descriptions editor
// The customer Category page shows a description box when a grade chip (A/B/C)
// is selected. The admin edits those texts here; blank fields fall back to the
// built-in bilingual defaults (same site_content mechanism as the About page).
router.get("/grade-edit", adminOnly, async (req, res) => {
  const r = await client(req.token).get("/api/content/grades");
  res.render("admin/grade_edit", {
    c: (r.status === 200 && r.data && typeof r.data === "object" && !Array.isArray(r.data)) ? r.data : {},
    gradeInfo: GRADE_INFO,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.post("/grade-edit", adminOnly, async (req, res) => {
  const fields = {};
  ["a", "b", "c"].forEach((g) => {
    ["title", "quality", "strengths", "weaknesses"].forEach((f) => {
      fields[g + "_" + f] = req.body[g + "_" + f] || "";
    });
  });
  const r = await client(req.token).put("/api/admin/content/grades", fields);
  res.redirect(r.status === 200 ? "/admin/grade-edit?msg=Grade+descriptions+updated"
    : "/admin/grade-edit?err=" + encodeURIComponent((r.data && r.data.error) || "Failed"));
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
  // The add form declares the location type (local city / foreign country) —
  // reject a name filed under the wrong type. Row-edit saves carry no scope
  // and skip this check (their location already exists).
  const scope = String(req.body.scope || "").toLowerCase();
  const pincode = String(req.body.pincode || "").trim();
  const isCountry = pincode.toLowerCase() === "foreign"
    || COUNTRIES.some((c) => c.toLowerCase() === pincode.toLowerCase());
  if (scope === "foreign" && !isCountry) {
    return res.redirect("/admin/delivery-charges?err="
      + encodeURIComponent("Please choose a country from the Foreign list"));
  }
  if (scope === "local" && isCountry) {
    return res.redirect("/admin/delivery-charges?err="
      + encodeURIComponent(pincode + " is a country — switch the type to Foreign (country)"));
  }
  const r = await client(req.token).post("/api/admin/delivery-charges", {
    pincode, charge_amount: Number(req.body.charge_amount),
  });
  res.redirect("/admin/delivery-charges" + (r.status === 200 ? "?msg=Charge+saved" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/delivery-charges/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/delivery-charges/${req.params.id}`);
  res.redirect("/admin/delivery-charges" + (r.status === 200 ? "?msg=Charge+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
router.post("/announcements", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/announcements", {
    title: req.body.title, message: req.body.message, expires_at: req.body.expires_at || null,
  });
  res.redirect("/admin/announcements" + (r.status === 201 ? "?msg=Announcement+posted" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/announcements/:id/delete", adminOnly, async (req, res) => {
  const r = await client(req.token).delete(`/api/admin/announcements/${req.params.id}`);
  res.redirect("/admin/announcements" + (r.status === 200 ? "?msg=Announcement+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});
// assignment stays on the dashboard
router.post("/orders/:id/assign", adminOnly, async (req, res) => {
  const r = await client(req.token).post(`/api/admin/orders/${req.params.id}/assign`, {
    warehouse_id: Number(req.body.warehouse_id),
  });
  res.redirect("/admin" + (r.status === 200 ? "?msg=Order+assigned" : "?err=" + encodeURIComponent(r.data.error)));
});
router.post("/email/bulk", adminOnly, async (req, res) => {
  const r = await client(req.token).post("/api/admin/email/bulk", {
    subject: req.body.subject, body: req.body.body,
  });
  let msg = r.data && r.data.error ? r.data.error
    : r.data.status === "sent" ? `Sent to ${r.data.count} customers`
    : `Dry-run (${r.data.count} recipients) — set SMTP_* in .env to send for real`;
  res.redirect("/admin/announcements?msg=" + encodeURIComponent(msg));
});

module.exports = router;
