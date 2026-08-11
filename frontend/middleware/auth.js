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

// Anyone may browse; `user` is simply null for a guest. Used by the shop pages
// (home, category list) that must work before someone registers.
function publicPage(req, res, next) {
  next();
}

const LOGIN_PROMPT = "Please log in to continue.";

/**
 * Send a guest to the login page, remembering where they were headed so they land
 * back on it afterwards. AJAX callers get JSON so the page can redirect itself
 * instead of stuffing a login page into a fetch() response.
 */
function askToLogin(req, res, message = LOGIN_PROMPT) {
  const wantsJson = req.headers["x-requested-with"] === "fetch"
    || (req.headers.accept || "").includes("application/json");
  // GET → come back here; POST (e.g. "Add to cart") → back to the page it came from
  const target = req.method === "GET"
    ? req.originalUrl
    : (() => {
        try { return new URL(req.get("Referer")).pathname; } catch (_) { return "/batches"; }
      })();
  const loginUrl = "/login?next=" + encodeURIComponent(target)
    + "&err=" + encodeURIComponent(message);
  if (wantsJson) {
    return res.status(401).json({ ok: false, login_required: true, login_url: loginUrl,
                                 error: message });
  }
  return res.redirect(loginUrl);
}

function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) return askToLogin(req, res);
    if (!roles.includes(req.user.role)) return res.status(403).render("error", {
      message: "You don't have access to this page.",
    });
    next();
  };
}

module.exports = { attachUser, requireRole, publicPage, askToLogin };
