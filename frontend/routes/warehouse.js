const express = require("express");
const multer = require("multer");
const FormData = require("form-data");
const { client } = require("../lib/api");
const { requireRole } = require("../middleware/auth");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

router.get("/", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const [stockRes, chartsRes, expiryRes, subRes, reqRes, cartsRes] = await Promise.all([
    api.get("/api/warehouse/stock"),
    api.get("/api/warehouse/charts"),
    api.get("/api/warehouse/expiry-alerts"),
    api.get("/api/warehouse/subscription"),
    api.get("/api/warehouse/product-requests"),
    api.get("/api/warehouse/abandoned-carts"),
  ]);
  res.render("warehouse/dashboard", {
    stock: stockRes.data || { batches: [], low_stock_alerts: [] },
    charts: chartsRes.data || { stock_by_grade: {}, revenue_7d: { labels: [], values: [] } },
    expiry: expiryRes.data || { alerts: [], count: 0 },
    subscription: subRes.data || { active: false, current: null },
    productRequests: reqRes.data || [],
    carts: Array.isArray(cartsRes.data) ? cartsRes.data : [],
    flash: req.query.msg || null,
    error: req.query.err || null,
  });
});

// Live notification counts for the warehouse header (polled by the client):
// new product categories in this warehouse's stock + new subscription plans.
router.get("/notifications", requireRole("warehouse"), async (req, res) => {
  try {
    const api = client(req.token);
    const [stock, plans, orders] = await Promise.all([
      api.get("/api/warehouse/stock"),
      api.get("/api/warehouse/subscription-plans"),
      api.get("/api/warehouse/orders"),
    ]);
    const batches = (stock.data && stock.data.batches) || [];
    const planList = Array.isArray(plans.data) ? plans.data : [];
    const waitingOrders = (Array.isArray(orders.data) ? orders.data : []).filter((o) => o.status === "waiting");
    let categories = 0, planCount = 0, orderCount = 0, items = [];
    if (req.cookies.wh_cat_seen !== undefined) {
      const cs = parseInt(req.cookies.wh_cat_seen, 10) || 0;
      categories = batches.filter((x) => Number(x.id) > cs).length;
    }
    if (req.cookies.wh_plan_seen !== undefined) {
      const ps = parseInt(req.cookies.wh_plan_seen, 10) || 0;
      planCount = planList.filter((x) => Number(x.id) > ps).length;
    }
    if (req.cookies.wh_order_seen !== undefined) {
      const seen = new Set((req.cookies.wh_order_seen || "").split(",").filter(Boolean));
      const fresh = waitingOrders.filter((o) => !seen.has(String(o.id)));
      orderCount = fresh.length;
      items = fresh.map((o) => ({ customer: o.customer_name }));
    }
    res.json({ categories, plans: planCount, orders: orderCount, orderItems: items });
  } catch (_) {
    res.json({ categories: 0, plans: 0, orders: 0, orderItems: [] });
  }
});

// helper: keep rows whose created_at (YYYY-MM-DD) is within [from, to]
function inDateRange(createdAt, from, to) {
  const d = createdAt ? String(createdAt).substring(0, 10) : null;
  if (!d) return false;
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

// Full current-stock list (Read more) — searchable by added date
router.get("/stock-all", requireRole("warehouse"), async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const r = await client(req.token).get("/api/warehouse/stock");
  const all = (r.data && r.data.batches) || [];
  // flag categories added since the last visit (so we can highlight them) ...
  const hasSeen = req.cookies.wh_cat_seen !== undefined;
  const prevSeen = parseInt(req.cookies.wh_cat_seen || "0", 10) || 0;
  const maxId = all.reduce((m, b) => Math.max(m, Number(b.id) || 0), 0);
  all.forEach(b => { b.isNew = hasSeen && Number(b.id) > prevSeen; });
  // ... then mark them seen → clears the Category badge
  res.cookie("wh_cat_seen", String(maxId), { httpOnly: true, sameSite: "lax" });
  res.locals.whCategoryCount = 0;
  let batches = all;
  if (from || to) batches = batches.filter(b => inDateRange(b.created_at, from, to));
  // pull brand-new categories to the top so they're obvious
  batches = batches.slice().sort((a, b) => (b.isNew === true) - (a.isNew === true));
  const newCount = batches.filter(b => b.isNew).length;
  res.render("warehouse/stock_all", { batches, from, to, newCount,
    flash: req.query.msg || null, error: req.query.err || null });
});

// Assigned-orders page — every order not yet shipped/cancelled, searchable by date.
// Viewing this page marks new orders as seen, clearing the header badge.
router.get("/orders-all", requireRole("warehouse"), async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const r = await client(req.token).get("/api/warehouse/orders");
  const all = r.data || [];
  const seen = new Set((req.cookies.wh_order_seen || "").split(",").filter(Boolean));
  const hasSeen = req.cookies.wh_order_seen !== undefined;
  all.forEach((o) => { o.isNew = hasSeen && o.status === "waiting" && !seen.has(String(o.id)); });
  const waitingKeys = all.filter((o) => o.status === "waiting").map((o) => String(o.id));
  res.cookie("wh_order_seen", waitingKeys.join(","), { httpOnly: true, sameSite: "lax" });
  res.locals.whOrderCount = 0;  // viewing this page clears the badge
  let orders = all.filter(o => ["waiting", "assigned", "packed"].indexOf(o.status) !== -1);
  if (from || to) orders = orders.filter(o => inDateRange(o.created_at, from, to));
  // brand-new orders first so they're obvious
  orders.sort((a, b) => (b.isNew === true) - (a.isNew === true));
  // orders history lives on this page too, as a card under the assigned orders
  const historyOrders = all.filter(o => ["shipped", "delivered", "cancelled"].includes(o.status));
  res.render("warehouse/orders_all", { orders, historyOrders, from, to });
});

// Full transfer-history list (Read more) — searchable by request date
router.get("/transfers-all", requireRole("warehouse"), async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const r = await client(req.token).get("/api/warehouse/transfers");
  let transfers = r.data || [];
  if (from || to) transfers = transfers.filter(t => inDateRange(t.requested_at, from, to));
  res.render("warehouse/transfers_all", { transfers, from, to });
});

// Full product-requests list (Read more) — searchable by request date
router.get("/product-requests-all", requireRole("warehouse"), async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const r = await client(req.token).get("/api/warehouse/product-requests");
  let requests = r.data || [];
  if (from || to) requests = requests.filter(x => inDateRange(x.created_at, from, to));
  res.render("warehouse/product_requests_all", { productRequests: requests, from, to });
});

// Printable PDF of the warehouse's order history (honours ?from/?to)
router.get("/orders-history/pdf", requireRole("warehouse"), async (req, res) => {
  const qs = [];
  if (req.query.from) qs.push("from=" + encodeURIComponent(req.query.from));
  if (req.query.to) qs.push("to=" + encodeURIComponent(req.query.to));
  const r = await client(req.token).get("/api/warehouse/orders/history/pdf" + (qs.length ? "?" + qs.join("&") : ""), { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/warehouse/orders-all?err=PDF+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=order_history.pdf");
  res.send(Buffer.from(r.data));
});

// Old standalone history page → now a card on the Orders page
router.get("/orders-history", requireRole("warehouse"), (req, res) => res.redirect("/warehouse/orders-all"));

// Add a new batch
router.post("/batches", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const r = await api.post("/api/warehouse/batches", {
    batch_id: req.body.batch_id,
    grade: req.body.grade,
    qty_kg: req.body.qty_kg,
    harvest_date: req.body.harvest_date,
    price_per_kg: req.body.price_per_kg,
  });
  const q = r.status === 201 ? "?msg=Batch+added" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/warehouse" + q);
});

// Update category details (name, grade, qty, price, production date, description)
router.post("/batches/:pk/update", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const body = {
    qty_kg: req.body.qty_kg,
    price_per_kg: req.body.price_per_kg,
  };
  if ((req.body.batch_id || "").trim()) body.batch_id = req.body.batch_id.trim();
  if (req.body.grade) body.grade = req.body.grade;
  if ((req.body.harvest_date || "").trim()) body.harvest_date = req.body.harvest_date.trim();
  // Ingredients + Effectiveness are edited as two fields and recombined into the
  // product description (same shape the admin side uses).
  if (req.body.ingredients !== undefined || req.body.effectiveness !== undefined) {
    const parts = [];
    if ((req.body.ingredients || "").trim()) parts.push("Ingredients: " + req.body.ingredients.trim());
    if ((req.body.effectiveness || "").trim()) parts.push("Effectiveness: " + req.body.effectiveness.trim());
    body.description = parts.join("\n\n");
  }
  const back = req.body._back === "all" ? "/warehouse/stock-all" : "/warehouse";
  const r = await api.put(`/api/warehouse/batches/${req.params.pk}`, body);
  const q = r.status === 200 ? "?msg=Batch+updated" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect(back + q);
});

// Remove a batch (e.g. an expired product) from this warehouse's stock
router.post("/batches/:pk/delete", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).delete(`/api/warehouse/batches/${req.params.pk}`);
  const q = r.status === 200
    ? "?msg=" + encodeURIComponent((r.data && r.data.message) || "Removed")
    : "?err=" + encodeURIComponent((r.data && r.data.error) || "Could not remove");
  const back = req.body._back === "all" ? "/warehouse/stock-all" : "/warehouse";
  res.redirect(back + q);
});
// Warehouse dismisses the "admin removed your category" alarm — remembers the
// acknowledged batch ids in a cookie so the banner/badge stop showing them.
router.post("/deleted-ack", requireRole("warehouse"), (req, res) => {
  let ids = req.body.ids || []; if (!Array.isArray(ids)) ids = [ids];
  const seen = new Set((req.cookies.wh_del_seen || "").split(",").filter(Boolean));
  ids.map(String).filter(Boolean).forEach((i) => seen.add(i));
  res.cookie("wh_del_seen", Array.from(seen).join(","),
    { httpOnly: true, sameSite: "lax", maxAge: 31536000000 });
  res.redirect(req.body._back === "all" ? "/warehouse/stock-all" : "/warehouse");
});

// Bulk soft-delete stock (table "Select all")
router.post("/batches/bulk-delete", requireRole("warehouse"), async (req, res) => {
  let ids = req.body.stock_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  const back = req.body._back === "all" ? "/warehouse/stock-all" : "/warehouse";
  if (!ids.length) return res.redirect(back + "?err=" + encodeURIComponent("Select at least one product"));
  const r = await client(req.token).post("/api/warehouse/batches/delete", { ids });
  res.redirect(back + (r.status === 200 ? "?msg=Products+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// Bulk-delete orders from this warehouse's history
router.post("/orders/delete", requireRole("warehouse"), async (req, res) => {
  let ids = req.body.order_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  if (!ids.length) return res.redirect("/warehouse/orders-all?err=" + encodeURIComponent("Select at least one order"));
  const r = await client(req.token).post("/api/warehouse/orders/delete", { ids });
  res.redirect("/warehouse/orders-all" + (r.status === 200 ? "?msg=Orders+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// Bulk-delete this warehouse's own product requests
router.post("/product-requests/delete", requireRole("warehouse"), async (req, res) => {
  let ids = req.body.request_ids || []; if (!Array.isArray(ids)) ids = [ids];
  ids = ids.map(Number).filter(Boolean);
  if (!ids.length) return res.redirect("/warehouse/product-requests-all?err=" + encodeURIComponent("Select at least one request"));
  const r = await client(req.token).post("/api/warehouse/product-requests/delete", { ids });
  res.redirect("/warehouse/product-requests-all" + (r.status === 200 ? "?msg=Requests+deleted" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Failed")));
});

// Advance order status (assigned->packed->shipped)
router.post("/orders/:id/status", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const r = await api.post(`/api/warehouse/orders/${req.params.id}/status`, {
    status: req.body.status,
  });
  const q = r.status === 200 ? "?msg=Status+updated" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/warehouse" + q);
});

// Upload PDF certificate — Node receives via multer, forwards to Flask as multipart
router.post(
  "/batches/:pk/certificate",
  requireRole("warehouse"),
  upload.single("file"),
  async (req, res) => {
    if (!req.file) return res.redirect("/warehouse?err=No+file");
    const form = new FormData();
    form.append("file", req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype,
    });
    const api = client(req.token);
    const r = await api.post(`/api/warehouse/batches/${req.params.pk}/certificate`, form, {
      headers: form.getHeaders(),
    });
    const q = r.status === 200 ? "?msg=Certificate+uploaded" : "?err=" + encodeURIComponent(r.data.error);
    res.redirect("/warehouse" + q);
  }
);

// Add / remove extra product photos (on this warehouse's own stock)
router.post("/batches/:pk/images", requireRole("warehouse"), upload.array("files", 8), async (req, res) => {
  if (!req.files || !req.files.length) return res.redirect("/warehouse/stock-all?err=No+images+chosen");
  const form = new FormData();
  req.files.forEach(f => form.append("files", f.buffer, { filename: f.originalname, contentType: f.mimetype }));
  const r = await client(req.token).post(`/api/warehouse/batches/${req.params.pk}/images`, form, { headers: form.getHeaders() });
  res.redirect("/warehouse/stock-all" + (r.status === 200 ? "?msg=Images+added" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Upload failed")));
});
router.post("/batches/:pk/images/:imgId/delete", requireRole("warehouse"), async (req, res) => {
  await client(req.token).delete(`/api/warehouse/batches/${req.params.pk}/images/${req.params.imgId}`);
  res.redirect("/warehouse/stock-all?msg=Image+removed");
});
// Set / change the COVER photo (shown across the whole system). AJAX-aware.
router.post("/batches/:pk/image", requireRole("warehouse"), upload.single("file"), async (req, res) => {
  const ajax = req.get("X-Requested-With") === "fetch";
  if (!req.file) {
    if (ajax) return res.status(400).json({ error: "No file chosen" });
    return res.redirect("/warehouse/stock-all?err=No+file");
  }
  const form = new FormData();
  form.append("file", req.file.buffer, { filename: req.file.originalname, contentType: req.file.mimetype });
  const r = await client(req.token).post(`/api/warehouse/batches/${req.params.pk}/image`, form, { headers: form.getHeaders() });
  if (ajax) return res.status(r.status).json(r.data || {});
  res.redirect("/warehouse/stock-all" + (r.status === 200 ? "?msg=Cover+updated" : "?err=" + encodeURIComponent((r.data && r.data.error) || "Upload failed")));
});
router.post("/batches/:pk/image/remove", requireRole("warehouse"), async (req, res) => {
  const ajax = req.get("X-Requested-With") === "fetch";
  const r = await client(req.token).delete(`/api/warehouse/batches/${req.params.pk}/image`);
  if (ajax) return res.status(r.status).json(r.data || {});
  res.redirect("/warehouse/stock-all?msg=Cover+removed");
});

// Transfers page + request
router.get("/transfers", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const [transfers, warehouses, stock, sub, preqs] = await Promise.all([
    api.get("/api/warehouse/transfers"),
    api.get("/api/warehouse/warehouses"),
    api.get("/api/warehouse/stock"),
    api.get("/api/warehouse/subscription"),
    api.get("/api/warehouse/product-requests"),
  ]);
  res.render("warehouse/transfers", {
    transfers: transfers.data || [],
    warehouses: warehouses.data || [],
    batches: (stock.data && stock.data.batches) || [],
    productRequests: preqs.data || [],
    myWarehouseId: req.user.warehouse_id,
    subscribed: !!(sub.data && sub.data.active),
    submitted: req.query.submitted === "1",
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.post("/transfers", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/transfers", {
    batch_id: Number(req.body.batch_id),
    to_warehouse_id: Number(req.body.to_warehouse_id),
    quantity_kg: Number(req.body.quantity_kg),
  });
  const q = r.status === 201 ? "?msg=Transfer+requested" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/warehouse/transfers" + q);
});

// Bulk CSV stock upload
router.post("/batches/bulk", requireRole("warehouse"), upload.single("file"), async (req, res) => {
  if (!req.file) return res.redirect("/warehouse?err=No+file");
  const form = new FormData();
  form.append("file", req.file.buffer, { filename: req.file.originalname, contentType: "text/csv" });
  const r = await client(req.token).post("/api/warehouse/batches/bulk", form, { headers: form.getHeaders() });
  const msg = r.status === 200 ? `Imported ${r.data.created}, ${r.data.errors.length} errors` : (r.data.error || "Upload failed");
  res.redirect("/warehouse?msg=" + encodeURIComponent(msg));
});

// Packing slip PDF (proxy)
router.get("/orders/:id/packing-slip", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get(`/api/warehouse/orders/${req.params.id}/packing-slip`, { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/warehouse?err=Slip+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", `inline; filename=packing_${req.params.id}.pdf`);
  res.send(Buffer.from(r.data));
});

// Batch QR PNG (proxy)
router.get("/batches/:pk/qr", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get(`/api/warehouse/batches/${req.params.pk}/qr`, { responseType: "arraybuffer" });
  if (r.status !== 200) return res.status(404).send("QR unavailable");
  res.setHeader("Content-Type", "image/png");
  res.send(Buffer.from(r.data));
});

// Submit a product upload request (multipart: fields + optional image). Needs subscription.
router.post("/product-requests", requireRole("warehouse"), upload.array("files", 8), async (req, res) => {
  const form = new FormData();
  form.append("product_name", req.body.product_name || "");
  form.append("grade", req.body.grade || "");
  form.append("qty_kg", req.body.qty_kg || "");
  form.append("price_per_kg", req.body.price_per_kg || "");
  form.append("harvest_date", req.body.harvest_date || "");
  // combine the two halves into the product description shown on the catalogue
  const parts = [];
  if ((req.body.ingredients || "").trim()) parts.push("Ingredients: " + req.body.ingredients.trim());
  if ((req.body.effectiveness || "").trim()) parts.push("Effectiveness: " + req.body.effectiveness.trim());
  form.append("description", parts.join("\n\n"));
  (req.files || []).forEach(f => form.append("files", f.buffer, {
    filename: f.originalname, contentType: f.mimetype }));
  const r = await client(req.token).post("/api/warehouse/product-requests", form, { headers: form.getHeaders() });
  const q = r.status === 201 ? "?submitted=1" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/warehouse/transfers" + q);
});

// Subscription page (view status + plans, buy)
router.get("/subscription", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const [sub, plans, payments] = await Promise.all([
    api.get("/api/warehouse/subscription"),
    api.get("/api/warehouse/subscription-plans"),
    api.get("/api/warehouse/payments"),
  ]);
  const planList = plans.data || [];
  // viewing the subscription page marks plans seen → clears the Subscription badge
  const maxPlan = planList.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
  res.cookie("wh_plan_seen", String(maxPlan), { httpOnly: true, sameSite: "lax" });
  res.locals.whPlanCount = 0;
  res.render("warehouse/subscription", {
    sub: sub.data || { current: null, active: false, history: [] },
    plans: planList,
    payments: payments.data || [],
    paid: req.query.paid === "1",
    payMsg: req.query.pm || "Your subscription payment has been confirmed. Thank you!",
    payAmount: req.query.pa || null,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
// Old separate purchase-history page → merged into the payment-history page
router.get("/purchase-history-all", requireRole("warehouse"), (req, res) => res.redirect("/warehouse/payment-history-all"));

// Combined purchase & payment history (Read more) — searchable by payment date.
// Payments carry the plan period they bought; purchases with no payment record
// (legacy/granted) are appended so nothing disappears.
router.get("/payment-history-all", requireRole("warehouse"), async (req, res) => {
  const from = req.query.from || "", to = req.query.to || "";
  const api = client(req.token);
  const [payRes, subRes] = await Promise.all([
    api.get("/api/warehouse/payments"),
    api.get("/api/warehouse/subscription"),
  ]);
  const payments = payRes.data || [];
  const history = (subRes.data && subRes.data.history) || [];
  const covered = new Set(payments.map(p => p.subscription_id).filter(Boolean));
  let rows = payments.map(p => ({
    date: p.created_at ? p.created_at.substring(0, 10) : "", plan: p.plan_name,
    from: p.start_date, to: p.end_date, amount: p.amount,
    method: p.method_label, reference: p.reference, active: p.sub_active, slip: p.id,
  }));
  history.forEach(h => {
    if (!covered.has(h.id)) rows.push({ date: h.start_date, plan: h.plan_name,
      from: h.start_date, to: h.end_date, amount: h.price_paid,
      method: null, reference: null, active: h.active, slip: null });
  });
  if (from || to) rows = rows.filter(r => inDateRange(r.date, from, to));
  rows.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  res.render("warehouse/payment_history_all", { rows, from, to });
});

// Checkout / payment page for a selected plan
router.get("/subscription/checkout", requireRole("warehouse"), async (req, res) => {
  const api = client(req.token);
  const [plans, methods, pin] = await Promise.all([
    api.get("/api/warehouse/subscription-plans"),
    api.get("/api/warehouse/payment-methods"),
    api.get("/api/warehouse/payment-pin"),
  ]);
  const plan = (plans.data || []).find(p => p.id === Number(req.query.plan_id));
  if (!plan) return res.redirect("/warehouse/subscription?err=Plan+not+found");
  res.render("warehouse/checkout", {
    plan, methods: methods.data || [], pinSet: !!(pin.data && pin.data.pin_set),
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// KPay-style PIN: verify an entered PIN (JSON in/out, called by the PIN pad)
router.post("/verify-pin", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/verify-pin", { pin: req.body.pin });
  res.json({ ok: !!(r.data && r.data.ok), pin_set: !!(r.data && r.data.pin_set) });
});

// KPay-style PIN: create/reset the 6-digit PIN (first-time setup)
router.post("/set-pin", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/payment-pin", { new_pin: req.body.pin });
  res.json({ ok: r.status === 200, error: r.data && r.data.error });
});

// Forgot PIN: email a reset code, verify it, then set a new PIN
router.post("/pin-reset/request", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/pin-reset/request");
  res.json(r.data || { sent: false });
});
router.post("/pin-reset/verify", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/pin-reset/verify", { code: req.body.code });
  res.json({ ok: !!(r.data && r.data.ok) });
});
router.post("/pin-reset/confirm", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/pin-reset/confirm", {
    code: req.body.code, new_pin: req.body.pin });
  res.json({ ok: r.status === 200, error: r.data && r.data.error });
});

// email a payment verification code (AJAX, called by the checkout "Confirm" button)
router.post("/subscription/otp", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).post("/api/warehouse/subscription/request-otp");
  res.json(r.data || {});
});

// Sample CSV format as a viewable PDF (opens in a new tab)
router.get("/sample-stock-template", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get("/api/warehouse/sample-stock-template", { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/warehouse?err=Sample+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "inline; filename=sample-stock-format.pdf");
  res.send(Buffer.from(r.data));
});

// Download a subscription payment slip PDF
router.get("/payments/:id/slip", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get("/api/warehouse/payments/" + req.params.id + "/slip", { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/warehouse/subscription?err=Payment+slip+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=subscription_payment_" + req.params.id + ".pdf");
  res.send(Buffer.from(r.data));
});

// Process the payment, then activate/extend the subscription
router.post("/subscription/pay", requireRole("warehouse"), async (req, res) => {
  // bank transfer keeps a raw account number; wallets get the +95 prefix
  let contact;
  if (req.body.method === "bank") {
    contact = (req.body.phone || "").replace(/\D/g, "").slice(0, 20);
  } else {
    const cc = (req.body.country_code || "+95").trim();
    const local = (req.body.phone || "").replace(/\D/g, "").replace(/^0+/, "").slice(0, 9);
    contact = local ? cc + local : "";
  }
  // fold the description + phone/bank number into the stored payer field (no schema change)
  const description = (req.body.description || "").trim();
  const payer = [description, contact].filter(Boolean).join(" · ") || null;
  // the wallet auto-issues a transaction reference (no manual entry anymore)
  const ref = (req.body.method || "PAY").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4) +
    Date.now().toString().slice(-9);
  const r = await client(req.token).post("/api/warehouse/subscription", {
    plan_id: Number(req.body.plan_id),
    method: req.body.method,
    payer,
    reference: ref,
    otp: req.body.otp,
  });
  if (r.status !== 201) {
    return res.redirect(`/warehouse/subscription/checkout?plan_id=${Number(req.body.plan_id)}&err=` + encodeURIComponent(r.data.error || "Payment failed"));
  }
  const amt = (r.data.payment && r.data.payment.amount) || "";
  res.redirect("/warehouse/subscription?paid=1&pm=" + encodeURIComponent(r.data.message || "Subscription activated.") +
    (amt ? "&pa=" + encodeURIComponent(amt) : ""));
});

// Per-order message thread (warehouse side)
// Order detail page (read-only view for warehouse)
router.get("/orders/:id/details", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get("/api/warehouse/orders");
  const order = (r.data || []).find(o => String(o.id) === String(req.params.id));
  if (!order) return res.redirect("/warehouse?err=Order+not+found");
  res.render("warehouse/order_detail", { order });
});

router.get("/orders/:id/messages", requireRole("warehouse"), async (req, res) => {
  const r = await client(req.token).get(`/api/orders/${req.params.id}/messages`);
  if (r.status !== 200) return res.redirect("/warehouse?err=Cannot+open+messages");
  res.render("messages", {
    orderId: req.params.id, messages: r.data || [],
    postUrl: `/warehouse/orders/${req.params.id}/messages`, backUrl: "/warehouse",
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.post("/orders/:id/messages", requireRole("warehouse"), async (req, res) => {
  await client(req.token).post(`/api/orders/${req.params.id}/messages`, { message: req.body.message });
  res.redirect(`/warehouse/orders/${req.params.id}/messages`);
});

module.exports = router;
