const express = require("express");
const { client } = require("../lib/api");
const { requireRole, publicPage } = require("../middleware/auth");
const { isLocal, buildOptions } = require("../lib/locations");

const router = express.Router();

// ---- Public shop front -----------------------------------------------------
// A visitor can browse the shop before creating an account: the home page and the
// category list are open, everything that spends money or touches an account
// (cart, checkout, orders, wishlist, alerts, profile) still requires a login.
router.get("/", publicPage, async (req, res, next) => {
  if (req.user) return next();          // logged-in users get the role redirect in server.js
  const api = client();                 // no token — the API serves these to guests
  const [batchesRes, promoRes, ratingsRes, adsRes, annRes, statsRes] = await Promise.all([
    api.get("/api/batches"),
    api.get("/api/promotions/active"),
    api.get("/api/warehouses/ratings"),
    api.get("/api/advertisements/active"),
    api.get("/api/announcements/active"),
    api.get("/api/stats/guest").catch(() => ({ data: { users: 0 } })),
  ]);
  const all = Array.isArray(batchesRes.data) ? batchesRes.data : [];
  // shop window: newest first, in stock, still sellable
  const featured = all
    .filter((b) => !b.expired && Number(b.qty_kg) > 0)
    .sort((a, b) => Number(b.id) - Number(a.id))
    .slice(0, 6);
  res.render("home", {
    featured,
    totalProducts: all.length,
    warehouseCount: new Set(all.map((b) => b.warehouse_id)).size,
    userCount: Number(statsRes.data && statsRes.data.users) || 0,
    promotions: Array.isArray(promoRes.data) ? promoRes.data : [],
    ratings: ratingsRes.data || {},
    ads: Array.isArray(adsRes.data) ? adsRes.data : [],
    announcements: Array.isArray(annRes.data) ? annRes.data : [],
    flash: req.query.msg || null,
    error: req.query.err || null,
  });
});

// About us — public. The admin can override the page copy (Edit this page);
// if the API is unreachable the built-in bilingual defaults still render.
router.get("/about", publicPage, async (req, res) => {
  let about = {};
  try {
    const r = await client(req.token).get("/api/content/about");
    if (r.status === 200 && r.data && typeof r.data === "object" && !Array.isArray(r.data)) about = r.data;
  } catch (e) { /* backend down — show the defaults */ }
  res.render("about", { about, flash: req.query.msg || null, error: req.query.err || null });
});

// Browse catalogue + active promotions (optional ?grade=A|B|C filter).
// Open to guests — the "Add to cart" control becomes "Login to buy" for them.
router.get("/batches", publicPage, async (req, res) => {
  const api = client(req.token);
  const grade = ["A", "B", "C"].includes(req.query.grade) ? req.query.grade : "";
  const [allRes, promoRes, ratingsRes] = await Promise.all([
    api.get("/api/batches"),
    api.get("/api/promotions/active"),
    api.get("/api/warehouses/ratings"),
  ]);
  const all = allRes.data || [];
  // Flag categories added since this customer last opened the page, then mark
  // everything seen (clears the header badge) — like a "what's new" highlight.
  if (req.user && req.user.role === "customer") {
    const hasSeen = req.cookies.cat_seen !== undefined; // first visit => set a baseline only
    const prevSeen = parseInt(req.cookies.cat_seen || "0", 10) || 0;
    let maxId = prevSeen;
    all.forEach((b) => {
      b.isNew = hasSeen && Number(b.id) > prevSeen;
      if (Number(b.id) > maxId) maxId = Number(b.id);
    });
    if (!hasSeen || maxId > prevSeen) {
      res.cookie("cat_seen", String(maxId), { httpOnly: true, sameSite: "lax" });
    }
    res.locals.newCategoryCount = 0; // badge clears the moment they view the page
  }
  const byId = new Map(all.map((b) => [b.id, b]));
  const batches = grade ? all.filter((b) => b.grade === grade) : all.slice();
  // surface brand-new categories at the very top so they're impossible to miss
  batches.sort((a, b) => (b.isNew === true) - (a.isNew === true));
  const cv = enrichCart(req.cart, byId);
  res.render("customer/batches", {
    batches,
    promotions: promoRes.data || [],
    ratings: ratingsRes.data || {},
    selectedGrade: grade,
    cartItems: cv.items,
    cartSubtotal: cv.subtotal,
    flash: req.query.msg || null,
    error: req.query.err || null,
  });
});

// Live "new category" count for the header badge — polled by the client so a newly
// published category reaches the header like a Facebook notification, no reload needed.
router.get("/notifications/categories", requireRole("customer"), async (req, res) => {
  try {
    const b = await client(req.token).get("/api/batches");
    let count = 0;
    if (Array.isArray(b.data) && req.cookies.cat_seen !== undefined) {
      const seen = parseInt(req.cookies.cat_seen, 10) || 0;
      count = b.data.filter((x) => Number(x.id) > seen).length;
    }
    res.json({ count });
  } catch (_) {
    res.json({ count: 0 });
  }
});

// ---- Multi-item cart (stored in a cookie) --------------------------------
const CART_OPTS = { httpOnly: true, sameSite: "lax" };

function saveCart(res, cart) {
  res.cookie("cart", JSON.stringify(cart), CART_OPTS);
}

// build a display-ready cart (names, prices, line totals) from the cookie + a batch map
function enrichCart(cart, byId) {
  let subtotal = 0;
  const items = (cart || []).map((ci) => {
    const b = byId.get(ci.batch_pk);
    const price = b ? Number(b.price_per_kg) : 0;
    const line = b ? +(price * ci.qty_kg).toFixed(2) : 0;
    subtotal += line;
    return { batch_pk: ci.batch_pk, name: b ? b.batch_id : ("#" + ci.batch_pk),
             qty_kg: ci.qty_kg, price, line_total: line };
  });
  return { items, subtotal: +subtotal.toFixed(2) };
}

async function cartViewFor(req, cart) {
  const r = await client(req.token).get("/api/batches");
  const byId = new Map((r.data || []).map((b) => [b.id, b]));
  return enrichCart(cart, byId);
}

// Add (or increment) a batch in the cart
router.post("/cart/add", requireRole("customer"), async (req, res) => {
  const wantsJson = req.headers["x-requested-with"] === "fetch"
    || (req.headers.accept || "").includes("application/json");
  const batch_pk = Number(req.body.batch_pk);
  const qty_kg = Number(req.body.qty_kg);
  if (!batch_pk || !(qty_kg > 0)) {
    if (wantsJson) return res.status(400).json({ ok: false, error: "Invalid quantity" });
    return res.redirect("/batches?err=" + encodeURIComponent("Invalid quantity"));
  }
  const cart = req.cart.slice();
  const existing = cart.find((i) => i.batch_pk === batch_pk);
  if (existing) existing.qty_kg += qty_kg;
  else cart.push({ batch_pk, qty_kg });
  saveCart(res, cart);
  // stay on the products page; AJAX gets the updated selection, plain form posts redirect back
  if (wantsJson) {
    const v = await cartViewFor(req, cart);
    return res.json({ ok: true, count: cart.length, items: v.items, subtotal: v.subtotal });
  }
  res.redirect("/batches?msg=Added+to+cart");
});

router.post("/cart/remove", requireRole("customer"), async (req, res) => {
  const wantsJson = req.headers["x-requested-with"] === "fetch"
    || (req.headers.accept || "").includes("application/json");
  const batch_pk = Number(req.body.batch_pk);
  const cart = req.cart.filter((i) => i.batch_pk !== batch_pk);
  saveCart(res, cart);
  if (wantsJson) {
    const v = await cartViewFor(req, cart);
    return res.json({ ok: true, count: cart.length, items: v.items, subtotal: v.subtotal });
  }
  res.redirect("/cart?msg=Item+removed");
});

router.post("/cart/clear", requireRole("customer"), (req, res) => {
  res.clearCookie("cart");
  res.redirect("/cart");
});

// View cart: resolve current batch details + preview the promotion
router.get("/cart", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const [batchesRes, promoRes, meRes] = await Promise.all([
    api.get("/api/batches"),
    api.get("/api/promotions/active"),
    api.get("/api/me"),
  ]);
  const byId = new Map((batchesRes.data || []).map((b) => [b.id, b]));
  const promotions = promoRes.data || [];
  const me = (meRes.data && meRes.data.user) || {};
  // Admin-configured delivery charges → the pickable Local / Foreign locations.
  // Checkout prices the fee from this list, so it always equals the admin's amount.
  const locRes = await api.get("/api/delivery-locations");
  const charges = (locRes.data && locRes.data.locations) || [];
  const defaultFee = Number((locRes.data && locRes.data.default_charge) || 0);
  // backend-resolved per-country foreign fees (admin override + 20k–50k band)
  const foreignFees = (locRes.data && locRes.data.foreign_fees) || {};
  const options = buildOptions(charges, defaultFee, foreignFees);
  // catch-all foreign fee for a country not in the built-in list
  const foreignRow = charges.find((c) => String(c.location).trim().toLowerCase() === "foreign");
  const foreignFee = Number(
    (locRes.data && locRes.data.foreign_default_charge)
    ?? (foreignRow ? foreignRow.charge : defaultFee));

  // pre-select the customer's saved location (profile) when we can price it
  const saved = (me.pincode || "").trim();
  const savedScope = saved && !isLocal(saved)
    && options.foreign.some((o) => o.name.toLowerCase() === saved.toLowerCase())
    ? "foreign" : "local";
  const pool = savedScope === "foreign" ? options.foreign : options.local;
  const savedOpt = pool.find((o) => o.name.toLowerCase() === saved.toLowerCase()) || null;
  const deliveryFee = savedOpt ? savedOpt.fee : (savedScope === "foreign" ? foreignFee : defaultFee);

  let subtotal = 0;
  let totalQty = 0;
  const items = req.cart.map((ci) => {
    const b = byId.get(ci.batch_pk);
    const lineTotal = b ? +(b.price_per_kg * ci.qty_kg).toFixed(2) : 0;
    subtotal += lineTotal;
    totalQty += ci.qty_kg;
    return {
      batch_pk: ci.batch_pk,
      qty_kg: ci.qty_kg,
      batch: b || null, // null => batch vanished
      line_total: lineTotal,
      issue: !b ? "no longer available"
        : b.near_expiry ? "near expiry — not orderable"
        : b.qty_kg < ci.qty_kg ? `only ${b.qty_kg}kg in stock`
        : null,
    };
  });

  // preview the same rule the backend applies: best active promo meeting min_qty
  const eligible = promotions.filter((p) => totalQty >= p.min_qty);
  const promo = eligible.sort((a, b) => b.discount_percent - a.discount_percent)[0] || null;
  const discount = promo ? +(subtotal * (promo.discount_percent / 100)).toFixed(2) : 0;

  const goods = +(subtotal - discount).toFixed(2);
  res.render("customer/cart", {
    items,
    subtotal: +subtotal.toFixed(2),
    totalQty,
    promo,
    discount,
    total: goods,
    deliveryFee: +(+deliveryFee).toFixed(2),
    deliveryTotal: +(goods + (+deliveryFee)).toFixed(2),
    address: me.address || "",
    pincode: savedOpt ? savedOpt.name : "",
    deliveryScope: savedScope,
    localOptions: options.local,
    foreignOptions: options.foreign,
    defaultFee,
    foreignFee,
    canCheckout: items.length > 0 && items.every((i) => !i.issue),
    flash: req.query.msg || null,
    error: req.query.err || null,
  });
});

// Checkout: send the whole cart to the API as one order
router.post("/cart/checkout", requireRole("customer"), async (req, res) => {
  if (!req.cart.length) return res.redirect("/cart?err=Cart+is+empty");
  const api = client(req.token);
  const fulfillment = req.body.fulfillment === "pickup" ? "pickup" : "delivery";
  const payOnline = req.body.pay_when === "online";
  // Local => a Myanmar city, Foreign => a country. The chosen location is what the
  // admin's delivery-charge table is priced against.
  const scope = req.body.delivery_scope === "foreign" ? "foreign" : "local";
  const location = String((scope === "foreign" ? req.body.country : req.body.city) || "").trim();
  if (fulfillment === "delivery" && !location) {
    return res.redirect("/cart?err=" + encodeURIComponent(
      scope === "foreign" ? "Please choose your country" : "Please choose your city"));
  }
  // the ward / home number IS the delivery address now (the city is sent separately)
  const details = String(req.body.address_details || "").trim();
  if (!details) {
    return res.redirect("/cart?err=" + encodeURIComponent(
      "Please enter your address details (ward and home no.)"));
  }
  const r = await api.post("/api/orders", {
    delivery_address: details,
    preferred_date: req.body.preferred_date || null,
    pincode: location || null,
    delivery_scope: scope,
    fulfillment,
    // 'cod' marks the order pay-on-delivery; online leaves it unpaid until the pay page
    payment_method: payOnline ? null : "cod",
    items: req.cart.map((i) => ({ batch_pk: i.batch_pk, qty_kg: i.qty_kg })),
  });
  if (r.status !== 201) {
    return res.redirect("/cart?err=" + encodeURIComponent(r.data.error || "Order failed"));
  }
  res.clearCookie("cart");
  const orderId = r.data.order && r.data.order.id;
  if (payOnline && orderId) {
    return res.redirect("/orders/" + orderId + "/pay");  // go straight to online payment
  }
  res.redirect("/orders?msg=" + encodeURIComponent("Order placed! Pay on delivery."));
});

// Step 1 — merchant checkout: choose provider + phone
router.get("/orders/:id/pay", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const [orderRes, methodsRes, meRes] = await Promise.all([
    api.get("/api/orders/" + req.params.id),
    api.get("/api/payment-methods"),
    api.get("/api/me"),
  ]);
  if (orderRes.status !== 200) return res.redirect("/orders?err=Order+not+found");
  const order = orderRes.data;
  if (order.payment_status === "paid") return res.redirect("/orders?msg=Order+already+paid");
  // pre-fill the phone field with the purchased warehouse's number (the account being paid to)
  const whItem = (order.items || []).find((it) => it.warehouse_phone);
  const warehousePhone = whItem ? whItem.warehouse_phone : "";
  res.render("customer/order_pay", {
    order,
    methods: methodsRes.data || [],
    phone: warehousePhone || (meRes.data && meRes.data.user && meRes.data.user.phone) || "",
    error: req.query.err || null,
  });
});

// Step 2 — redirect into the (simulated) provider payment form
router.post("/orders/:id/gateway", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const [orderRes, methodsRes, pinRes] = await Promise.all([
    api.get("/api/orders/" + req.params.id),
    api.get("/api/payment-methods"),
    api.get("/api/payment-pin"),
  ]);
  if (orderRes.status !== 200) return res.redirect("/orders?err=Order+not+found");
  const order = orderRes.data;
  if (order.payment_status === "paid") return res.redirect("/orders?msg=Order+already+paid");

  const methods = methodsRes.data || [];
  const chosen = methods.find((m) => m.key === req.body.method);
  if (!chosen) return res.redirect("/orders/" + req.params.id + "/pay?err=Please+choose+a+payment+method");

  let phone;
  if (chosen.key === "bank") {
    // bank transfer: a bank account number, no +95 prefix
    phone = (req.body.phone || "").replace(/\D/g, "").slice(0, 20);
    if (!phone) return res.redirect("/orders/" + req.params.id + "/pay?err=Bank+number+is+required");
  } else {
    // wallets: chosen country code in front of the local number
    const cc = (req.body.country_code || "+95").trim();
    const local = (req.body.phone || "").replace(/\D/g, "").replace(/^0+/, "").slice(0, 9);
    if (!local) return res.redirect("/orders/" + req.params.id + "/pay?err=Phone+number+is+required");
    phone = cc + local;
  }

  // auto-generate a transaction id (the "gateway" issues it, like a real wallet)
  const ref = chosen.label.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4) +
    Date.now().toString().slice(-9);
  const payer = (req.body.payer || "").trim();
  res.render("customer/gateway", {
    order, method: chosen, phone, reference: ref, payer,
    pinSet: !!(pinRes.data && pinRes.data.pin_set),
  });
});

// email a payment verification code (AJAX, called by the gateway "Pay" button)
router.post("/orders/:id/pay/otp", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/orders/" + req.params.id + "/pay/request-otp");
  res.json(r.data || {});
});

router.post("/orders/:id/pay", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/orders/" + req.params.id + "/pay", {
    method: req.body.method, reference: req.body.reference, phone: req.body.phone, otp: req.body.otp,
  });
  if (r.status !== 200) {
    return res.redirect("/orders/" + req.params.id + "/pay?err=" +
      encodeURIComponent((r.data && r.data.error) || "Payment failed"));
  }
  res.redirect("/orders?paid=1");
});

// Download a payment slip PDF for a paid order
router.get("/orders/:id/payment-slip", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).get("/api/orders/" + req.params.id + "/payment-slip", { responseType: "arraybuffer" });
  if (r.status !== 200) return res.redirect("/orders?err=Payment+slip+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=payment_order_" + req.params.id + ".pdf");
  res.send(Buffer.from(r.data));
});

// --- KPay-style payment PIN (AJAX, called by the PIN pad on the pay page) ---
router.post("/pin/verify", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/verify-pin", { pin: req.body.pin });
  res.json({ ok: !!(r.data && r.data.ok), pin_set: !!(r.data && r.data.pin_set) });
});
router.post("/pin/set", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/payment-pin", { new_pin: req.body.pin });
  res.json({ ok: !!(r.data && r.data.ok), error: r.data && r.data.error });
});
router.post("/pin-reset/request", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/pin-reset/request");
  res.json(r.data || {});
});
router.post("/pin-reset/verify", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/pin-reset/verify", { code: req.body.code });
  res.json({ ok: !!(r.data && r.data.ok) });
});
router.post("/pin-reset/confirm", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/pin-reset/confirm", {
    code: req.body.code, new_pin: req.body.pin });
  res.json({ ok: !!(r.data && r.data.ok), error: r.data && r.data.error });
});

// Order history
router.get("/orders", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const r = await api.get("/api/orders");
  const all = r.data || [];
  // which shipped/delivered orders are NEW since the last visit → highlight them on the page
  const hasSeen = req.cookies.ord_seen !== undefined;
  const oldSeen = new Set((req.cookies.ord_seen || "").split(",").filter(Boolean));
  const keys = all
    .filter(o => o.status === "shipped" || o.status === "delivered")
    .map(o => o.id + ":" + o.status);
  // then acknowledge them (clears the header badge)
  res.cookie("ord_seen", keys.join(","), { httpOnly: true, sameSite: "lax" });
  res.locals.orderUpdateCount = 0;

  const justCancelled = req.query.cancelled === "1";
  // Cancelled orders are never shown in My Orders — the popup still confirms the cancel.
  const orders = all.filter(o => o.status !== "cancelled");
  orders.forEach((o, i) => {
    o.displayNo = orders.length - i; // stable display number (newest-first), survives sorting
    o.isUpdate = hasSeen
      && (o.status === "shipped" || o.status === "delivered")
      && !oldSeen.has(o.id + ":" + o.status);
  });
  // cards: pull freshly shipped/delivered orders to the top so they're obvious
  const cardOrders = orders.slice().sort((a, b) => (b.isUpdate === true) - (a.isUpdate === true));
  const updateCount = orders.filter(o => o.isUpdate).length;
  res.render("customer/orders", {
    orders, cardOrders, updateCount,
    cancelled: justCancelled,
    paid: req.query.paid === "1",
    payMsg: "Your payment has been confirmed. Thank you for your order!",
    flash: req.query.msg || null,
    error: req.query.err || null,
  });
});

// Live "order update" count for the header badge — fires when a warehouse ships/delivers.
router.get("/orders/notifications", requireRole("customer"), async (req, res) => {
  try {
    const r = await client(req.token).get("/api/orders");
    const orders = Array.isArray(r.data) ? r.data : [];
    const updates = orders.filter(o => o.status === "shipped" || o.status === "delivered");
    let count = 0, items = [];
    if (req.cookies.ord_seen !== undefined) {
      const seen = new Set((req.cookies.ord_seen || "").split(",").filter(Boolean));
      const fresh = updates.filter(o => !seen.has(o.id + ":" + o.status));
      count = fresh.length;
      items = fresh.map(o => ({ seq: o.customer_seq, status: o.status }));
    }
    res.json({ count, items });
  } catch (_) {
    res.json({ count: 0, items: [] });
  }
});

// Single order detail page (customer)
router.get("/orders/:id/details", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).get("/api/orders/" + req.params.id);
  if (r.status !== 200 || !r.data) return res.redirect("/orders?err=Order+not+found");
  res.render("customer/order_detail", { order: r.data, displayNo: req.query.n || null });
});

router.post("/orders/:id/cancel", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const r = await api.post(`/api/orders/${req.params.id}/cancel`);
  if (r.status !== 200) {
    return res.redirect("/orders?err=" + encodeURIComponent(r.data.error || "Cancel failed"));
  }
  res.redirect("/orders?cancelled=1");
});

// Customer dashboard with order-history chart + announcements
router.get("/dashboard", requireRole("customer"), async (req, res) => {
  const api = client(req.token);
  const [chart, ann, orders, alerts, ads] = await Promise.all([
    api.get("/api/orders/history-chart"),
    api.get("/api/announcements/active"),
    api.get("/api/orders"),
    api.get("/api/price-alerts"),
    api.get("/api/advertisements/active"),
  ]);
  const dropped = (Array.isArray(alerts.data) ? alerts.data : []).filter(a => a.is_notified);
  res.render("customer/dashboard", {
    chart: chart.data || { labels: [], values: [] },
    announcements: ann.data || [],
    ads: Array.isArray(ads.data) ? ads.data : [],
    orders: (orders.data || []).filter(o => o.status !== "cancelled"),
    recentCutoffMs: Date.now() - 3 * 24 * 60 * 60 * 1000, // cutoff for "ordered within 3 days"
    priceDrops: dropped,
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

// Price-drop alert (from batches page)
router.post("/price-alerts", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/price-alerts", {
    batch_id: Number(req.body.batch_id), desired_price: Number(req.body.desired_price),
  });
  const q = r.status === 201 ? "?msg=Alert+set" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/batches" + q);
});

// Rate & review a delivered order
router.post("/orders/:id/review", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post(`/api/orders/${req.params.id}/review`, {
    rating: Number(req.body.rating), comment: req.body.comment,
  });
  const q = r.status === 201 ? "?msg=Thanks+for+your+review" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/orders" + q);
});

// Repeat last order (1-click)
router.post("/orders/repeat", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).post("/api/orders/repeat");
  const q = r.status === 201 ? "?msg=Order+repeated" : "?err=" + encodeURIComponent(r.data.error);
  res.redirect("/orders" + q);
});

// Invoice PDF — proxied through BFF so the browser session can download it
router.get("/orders/:id/invoice", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).get(`/api/orders/${req.params.id}/invoice`, {
    responseType: "arraybuffer",
  });
  if (r.status !== 200) return res.redirect("/orders?err=Invoice+unavailable");
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", `inline; filename=invoice_${req.params.id}.pdf`);
  res.send(Buffer.from(r.data));
});

// Per-order message thread
router.get("/orders/:id/messages", requireRole("customer"), async (req, res) => {
  const r = await client(req.token).get(`/api/orders/${req.params.id}/messages`);
  if (r.status !== 200) return res.redirect("/orders?err=Cannot+open+messages");
  res.render("messages", {
    orderId: req.params.id, messages: r.data || [],
    postUrl: `/orders/${req.params.id}/messages`, backUrl: "/orders",
    flash: req.query.msg || null, error: req.query.err || null,
  });
});
router.post("/orders/:id/messages", requireRole("customer"), async (req, res) => {
  await client(req.token).post(`/api/orders/${req.params.id}/messages`, { message: req.body.message });
  res.redirect(`/orders/${req.params.id}/messages`);
});

module.exports = router;
