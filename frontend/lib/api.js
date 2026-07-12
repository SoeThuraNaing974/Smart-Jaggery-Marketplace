// Thin axios wrapper that talks to the Flask API and forwards the JWT.
const axios = require("axios");
const http = require("http");
const https = require("https");

const API_BASE = process.env.API_BASE || "http://127.0.0.1:5000";

// Reuse TCP connections to the API instead of opening a new one per request.
// Each page makes several API calls — keep-alive removes the per-call handshake
// and makes everything noticeably snappier.
const httpAgent = new http.Agent({ keepAlive: true, maxSockets: 64, keepAliveMsecs: 15000 });
const httpsAgent = new https.Agent({ keepAlive: true, maxSockets: 64, keepAliveMsecs: 15000 });

function client(token) {
  return axios.create({
    baseURL: API_BASE,
    timeout: 10000,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    // don't throw on 4xx — we handle status codes ourselves
    validateStatus: () => true,
    httpAgent,
    httpsAgent,
  });
}

module.exports = { client, API_BASE };
