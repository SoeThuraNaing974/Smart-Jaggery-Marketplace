// Delivery locations used by checkout (customer) and the delivery-charge page (admin).
// Keeping one list in one place means a city the admin prices is exactly a city the
// customer can pick at checkout.

// Myanmar cities — "Local" delivery.
const MM_CITIES = [
  "Yangon", "Mandalay", "Naypyitaw", "Bago", "Mawlamyine", "Taunggyi", "Pathein",
  "Monywa", "Meiktila", "Myitkyina", "Sittwe", "Pyay", "Hpa-An", "Magway", "Dawei",
  "Lashio", "Pakokku", "Hinthada", "Myingyan", "Pyin Oo Lwin", "Kalaw", "Nyaung-U",
];

// Countries we ship to — "Foreign" delivery.
const COUNTRIES = [
  "Thailand", "China", "India", "Bangladesh", "Laos", "Vietnam", "Malaysia",
  "Singapore", "Indonesia", "Japan", "South Korea", "Cambodia", "Philippines",
  "Australia", "United Kingdom", "United States", "Canada", "Germany", "France",
  "United Arab Emirates", "Saudi Arabia", "Qatar", "Nepal", "Sri Lanka",
];

const norm = (s) => String(s || "").trim().toLowerCase();

/** true when a location name is a Myanmar city (i.e. a "local" location). */
function isLocal(name) {
  return MM_CITIES.some((c) => norm(c) === norm(name));
}

/**
 * Merge the admin's configured charges into the pickable lists.
 * `charges` = [{ location, charge }] from /api/delivery-locations.
 * `foreignFees` = { countryLowercase: fee } from the same endpoint — the
 * backend-resolved per-country foreign fee (admin override + 20k–50k band),
 * i.e. exactly what an order to that country gets charged.
 * Returns { local, foreign } as [{ name, charge|null, fee }] — charge null
 * means "the admin hasn't priced this one" (the standard rate applies).
 */
function buildOptions(charges, defaultCharge, foreignFees) {
  const priced = new Map();
  (charges || []).forEach((c) => priced.set(norm(c.location), c));
  const fees = foreignFees || {};

  const decorate = (names, isForeign) => names.map((name) => {
    const hit = priced.get(norm(name));
    const resolved = isForeign ? fees[norm(name)] : undefined;
    return { name, charge: hit ? Number(hit.charge) : null,
             fee: resolved !== undefined ? Number(resolved)
               : (hit ? Number(hit.charge) : Number(defaultCharge)) };
  });

  // Locations the admin typed that aren't in either list (e.g. a smaller town).
  // They're not known countries, so they're offered as local places.
  const known = new Set(MM_CITIES.concat(COUNTRIES).map(norm));
  const extras = (charges || [])
    .filter((c) => !known.has(norm(c.location)) && norm(c.location) !== "foreign")
    .map((c) => c.location);

  return {
    local: decorate(MM_CITIES.concat(extras), false),
    foreign: decorate(COUNTRIES, true),
  };
}

module.exports = { MM_CITIES, COUNTRIES, isLocal, buildOptions };
