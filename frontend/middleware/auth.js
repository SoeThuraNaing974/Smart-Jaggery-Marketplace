const jwt = require("jsonwebtoken");

const JWT_SECRET = process.env.JWT_SECRET || "change-me-in-prod";
const API_BASE = process.env.API_BASE || "http://127.0.0.1:5000";

// Decode (and verify) the JWT stored in our HTTP-only cookie so views can
// gate UI by role. The Flask API re-validates on every call regardless.
function attachUser(req, res, next) {
  const token = req.cookies.token;
  req.token = token || null;
  req.user = null;
  if (token) {
    try {
      const payload = jwt.verify(token, JWT_SECRET);
      req.user = {
        id: payload.sub,
        role: payload.role,
        name: payload.name,
        warehouse_id: payload.warehouse_id,
      };
    } catch (_) {
      res.clearCookie("token");
    }
  }
  res.locals.user = req.user; // available in all EJS views
  res.locals.apiBase = ""; // images load same-origin via the frontend's /uploads proxy (works on phones)
  res.locals.currentPath = req.path; // so the nav can highlight the active page

  // parse the cart cookie once so nav can show an item count everywhere
  req.cart = [];
  if (req.cookies.cart) {
    try {
      const parsed = JSON.parse(req.cookies.cart);
      if (Array.isArray(parsed)) req.cart = parsed;
    } catch (_) {
      res.clearCookie("cart");
    }
  }
  res.locals.cartCount = req.cart.length;
  next();
}

function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) return res.redirect("/login");
    if (!roles.includes(req.user.role)) return res.status(403).render("error", {
      message: "You don't have access to this page.",
    });
    next();
  };
}

module.exports = { attachUser, requireRole };
