const express = require("express");
const multer = require("multer");
const FormData = require("form-data");
const { client } = require("../lib/api");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// In production (hosted over HTTPS) mark the auth cookie Secure; locally it stays
// non-secure so http://localhost still works.
const TOKEN_COOKIE = {
  httpOnly: true,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
  maxAge: 1000 * 60 * 60 * 12, // 12h, matches the JWT expiry
};

router.get("/login", (req, res) => res.render("login", { error: null }));
router.get("/register", (req, res) => res.render("register", { error: null }));

router.post("/login", async (req, res) => {
  const { email, password } = req.body;
  const r = await client().post("/api/login", { email, password });
  if (r.status !== 200) {
    return res.status(r.status).render("login", { error: r.data.error || "Login failed" });
  }
  // store the API's JWT in our own HTTP-only cookie
  res.cookie("token", r.data.token, TOKEN_COOKIE);
  res.redirect("/");
});

router.post("/register", async (req, res) => {
  const { name, email, password } = req.body;
  const accountType = req.body.account_type === "warehouse" ? "warehouse" : "customer";
  // store the phone with the chosen country code in front of the local number (like profile)
  const cc = (req.body.country_code || "+95").trim();
  const local = (req.body.phone || "").replace(/\D/g, "").replace(/^0+/, "").slice(0, 9);
  const phone = local ? cc + local : "";
  const payload = { name, email, password, phone, account_type: accountType };
  if (accountType === "warehouse") {
    payload.warehouse_name = name;   // the single name field is the warehouse / business name
    payload.location = req.body.location;
  } else {
    payload.address = req.body.address;
  }
  const r = await client().post("/api/register", payload);
  if (r.status !== 201) {
    return res.status(r.status).render("register", { error: r.data.error || "Registration failed" });
  }
  res.cookie("token", r.data.token, TOKEN_COOKIE);
  res.redirect("/");   // role-based redirect → warehouse lands on /warehouse
});

router.post("/logout", async (req, res) => {
  // capture a non-empty cart as "abandoned" before the session ends
  if (req.user && req.user.role === "customer" && req.cart && req.cart.length) {
    try {
      await client(req.token).post("/api/cart/abandon", { items: req.cart });
    } catch (_) { /* best-effort */ }
  }
  res.clearCookie("token");
  res.clearCookie("cart");
  res.redirect("/login");
});

// ------------------------------------------------ profile (any logged-in user)
function requireLogin(req, res, next) {
  if (!req.user) return res.redirect("/login");
  next();
}

router.get("/profile", requireLogin, async (req, res) => {
  const r = await client(req.token).get("/api/me");
  res.render("profile", {
    profile: (r.data && r.data.user) || {},
    flash: req.query.msg || null, error: req.query.err || null,
  });
});

router.post("/profile", requireLogin, async (req, res) => {
  // store the phone with the chosen country code in front of the local number
  const cc = (req.body.country_code || "+95").trim();
  const local = (req.body.phone || "").replace(/\D/g, "").replace(/^0+/, "").slice(0, 9);
  const phone = local ? cc + local : "";
  const r = await client(req.token).put("/api/me", {
    name: req.body.name, phone,
    address: req.body.address, pincode: req.body.pincode,
  });
  res.redirect("/profile" + (r.status === 200 ? "?msg=Profile+updated" : "?err=" + encodeURIComponent(r.data.error)));
});

// Profile picture upload (Node receives via multer, forwards to Flask as multipart)
router.post("/profile/avatar", requireLogin, upload.single("file"), async (req, res) => {
  if (!req.file) return res.redirect("/profile?err=Please+choose+an+image");
  const form = new FormData();
  form.append("file", req.file.buffer, req.file.originalname);
  const r = await client(req.token).post("/api/me/avatar", form, { headers: form.getHeaders() });
  res.redirect("/profile" + (r.status === 200 ? "?msg=Photo+updated" : "?err=" + encodeURIComponent(r.data.error)));
});

router.post("/profile/avatar/remove", requireLogin, async (req, res) => {
  await client(req.token).delete("/api/me/avatar");
  res.redirect("/profile?msg=Photo+removed");
});

router.post("/change-password", requireLogin, async (req, res) => {
  const r = await client(req.token).post("/api/change-password", {
    current_password: req.body.current_password, new_password: req.body.new_password,
  });
  res.redirect("/profile" + (r.status === 200 ? "?msg=Password+changed" : "?err=" + encodeURIComponent(r.data.error)));
});

module.exports = router;
