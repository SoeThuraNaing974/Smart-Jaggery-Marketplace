// Built-in grade descriptions shown on the customer Category page when a grade
// chip (A/B/C) is selected. English is the source text (translated to Burmese
// through the locale dictionaries, like every template string); the admin can
// override any field from /admin/grade-edit — overrides are stored in the
// backend's site_content table under the "grades" key and replace the built-in
// text in both languages. A field left blank there falls back to these defaults.
const GRADE_INFO = {
  A: {
    icon: "🏆",
    title: "Grade A (best quality, highest price)",
    quality: "Carries the full natural aroma and taste of pure toddy palm sap, with a golden-yellow or glossy dark natural colour. The texture is firm, free of moisture, and of the highest purity.",
    strengths: [
      "Best for health — packed with natural minerals and nutrients.",
      "Excellent aroma and taste — ideal for premium confectionery and for eating directly in its natural form.",
    ],
    weaknesses: [
      "The price is very high, making it costly for ordinary daily use.",
    ],
  },
  B: {
    icon: "🥈",
    title: "Grade B (medium quality, fair price)",
    quality: "Ordinary-quality jaggery with a medium level of colour, aroma and taste. It may be blended with a small amount of sugar or other sweeteners.",
    strengths: [
      "Fairly priced with reasonably good quality — the best fit for most consumers.",
      "Widely usable in home cooking and everyday confectionery.",
    ],
    weaknesses: [
      "Lacks the natural, full aroma and taste of Grade A.",
    ],
  },
  C: {
    icon: "🥉",
    title: "Grade C (lowest quality, cheapest price)",
    quality: "The lowest quality, often with high moisture content and a larger amount of sugar or other ingredients mixed in. The colour may be pale, or irregular and overly dark.",
    strengths: [
      "Cheap and easy to buy — suitable for businesses that need to keep costs especially low.",
      "The most economical choice for wholesale purchases.",
    ],
    weaknesses: [
      "Very little natural jaggery taste and low nutritional value.",
      "Hard to store for long — its moisture makes it sticky and easily spoiled.",
    ],
  },
};

module.exports = { GRADE_INFO };
