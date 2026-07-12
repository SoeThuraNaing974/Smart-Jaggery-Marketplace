// Per-country national-number max length. When the country code changes,
// the phone input's max length + validation update to match that country.
window.PHONE_MAXLEN = {
  "+95": 9,   // Myanmar
  "+66": 9,   // Thailand
  "+91": 10,  // India
  "+65": 8,   // Singapore
  "+60": 10,  // Malaysia
  "+86": 11,  // China
  "+1": 10,   // USA / Canada
  "+44": 10,  // UK
  "+61": 9,   // Australia
  "+81": 10,  // Japan
  "+82": 10,  // South Korea
  "+84": 9,   // Vietnam
  "+880": 10, // Bangladesh
  "+977": 10, // Nepal
  "+62": 11,  // Indonesia
  "+63": 10   // Philippines
};

window.phoneLenFor = function (code) {
  return window.PHONE_MAXLEN[code] || 12;
};

window.applyPhoneLen = function (input, code) {
  if (!input) return;
  var len = window.phoneLenFor(code);
  input.maxLength = len;
  input.setAttribute("pattern", "[0-9]{1," + len + "}");
  input.title = "Up to " + len + " digits";
  input.placeholder = "number (max " + len + " digits)";
  input.value = (input.value || "").replace(/\D/g, "").slice(0, len);
};

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".phone-cc-select").forEach(function (sel) {
    var group = sel.closest(".phone-group");
    var input = group && group.querySelector('input[name="phone"]');
    if (!input) return;
    // set the initial length from the current country (unless it's in bank mode)
    if (sel.style.display !== "none" && !input.classList.contains("no-cc")) {
      window.applyPhoneLen(input, sel.value);
    }
    sel.addEventListener("change", function () { window.applyPhoneLen(input, sel.value); });
  });
  // keep phone inputs digits-only, capped at their current max length
  document.querySelectorAll('.phone-group input[name="phone"]').forEach(function (inp) {
    inp.addEventListener("input", function () {
      this.value = this.value.replace(/\D/g, "").slice(0, this.maxLength || 12);
    });
  });
});
