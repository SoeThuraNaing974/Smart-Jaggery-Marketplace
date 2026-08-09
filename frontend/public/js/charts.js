/* Chart.js helpers shared by customer/warehouse/admin dashboards.
   Each dashboard embeds `window.CHART_DATA = {...}` and calls these. */
(function () {
  const BROWN = "#7a4a1e";
  const PALETTE = ["#1f7a3d", "#c98a00", "#8a8a8a", "#2667c9", "#5a3a8a", "#b3261e"];

  function ctx(id) {
    const el = document.getElementById(id);
    return el ? el.getContext("2d") : null;
  }

  window.JaggeryCharts = {
    line(id, labels, values, label) {
      const el = document.getElementById(id); if (!el) return;
      const c = el.getContext("2d");
      // soft top-to-bottom gradient fill under the line
      const grad = c.createLinearGradient(0, 0, 0, el.height || 200);
      grad.addColorStop(0, "rgba(201,138,58,.42)");
      grad.addColorStop(1, "rgba(201,138,58,0)");
      new Chart(c, {
        type: "line",
        data: { labels, datasets: [{
          label, data: values,
          borderColor: BROWN, borderWidth: 3,
          backgroundColor: grad, fill: true, tension: .4,
          pointRadius: 3, pointHoverRadius: 6,
          pointBackgroundColor: "#c98a3a", pointBorderColor: "#fff", pointBorderWidth: 2,
          pointHoverBackgroundColor: "#7a4a1e", pointHoverBorderColor: "#fff",
        }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,   // respect the CSS height cap on dashboard cards
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#3d2a16", titleColor: "#ffd9a0", bodyColor: "#fff",
              padding: 10, cornerRadius: 8, displayColors: false,
              callbacks: { label: (i) => Number(i.parsed.y).toLocaleString() + " Kyats" },
            },
          },
          scales: {
            y: { beginAtZero: true, border: { display: false },
              grid: { color: "rgba(122,74,30,.08)" },
              ticks: { color: "#9a8b76", callback: (v) => v + " Kyats" } },
            x: { border: { display: false }, grid: { display: false },
              ticks: { color: "#9a8b76" } },
          },
        },
      });
    },
    // iconic spending chart: rounded gradient bars with Kyats value labels on top
    spendBar(id, labels, values) {
      const el = document.getElementById(id); if (!el) return;
      const c = el.getContext("2d");
      const grad = c.createLinearGradient(0, 0, 0, el.height || 200);
      grad.addColorStop(0, "#e0a653");
      grad.addColorStop(1, "#7a4a1e");
      const valueLabels = {
        id: "spendValueLabels",
        afterDatasetsDraw(chart) {
          const g = chart.ctx;
          (chart.getDatasetMeta(0).data || []).forEach((bar, i) => {
            const v = values[i]; if (v == null) return;
            g.save();
            g.fillStyle = "#7a4a1e";
            g.font = "700 11px Helvetica, Arial, sans-serif";
            g.textAlign = "center";
            g.fillText(Number(v).toLocaleString() + " Kyats", bar.x, bar.y - 7);
            g.restore();
          });
        },
      };
      new Chart(c, {
        type: "bar",
        data: { labels, datasets: [{
          data: values, backgroundColor: grad, hoverBackgroundColor: "#c98a3a",
          borderRadius: 8, borderSkipped: false, maxBarThickness: 64,
        }] },
        options: {
          responsive: true,
          layout: { padding: { top: 20 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#3d2a16", titleColor: "#ffd9a0", bodyColor: "#fff",
              padding: 10, cornerRadius: 8, displayColors: false,
              callbacks: { label: (i) => Number(i.parsed.y).toLocaleString() + " Kyats" },
            },
          },
          scales: {
            y: { beginAtZero: true, border: { display: false },
              grid: { color: "rgba(122,74,30,.08)" },
              ticks: { color: "#9a8b76", callback: (v) => v + " Kyats" } },
            x: { border: { display: false }, grid: { display: false },
              ticks: { color: "#5a3514", font: { weight: "600" } } },
          },
        },
        plugins: [valueLabels],
      });
    },
    bar(id, labels, values, label) {
      const el = document.getElementById(id); if (!el) return;
      const c = el.getContext("2d");
      const grad = c.createLinearGradient(0, 0, 0, el.height || 200);
      grad.addColorStop(0, "#e0a653");
      grad.addColorStop(1, "#7a4a1e");
      const valueLabels = {
        id: "barCountLabels",
        afterDatasetsDraw(chart) {
          const g = chart.ctx;
          (chart.getDatasetMeta(0).data || []).forEach((bar, i) => {
            const v = values[i]; if (v == null) return;
            g.save();
            g.fillStyle = "#7a4a1e";
            g.font = "700 11px Helvetica, Arial, sans-serif";
            g.textAlign = "center";
            g.fillText(Number(v).toLocaleString(), bar.x, bar.y - 7);
            g.restore();
          });
        },
      };
      new Chart(c, {
        type: "bar",
        data: { labels, datasets: [{
          label, data: values, backgroundColor: grad, hoverBackgroundColor: "#c98a3a",
          borderRadius: 8, borderSkipped: false, maxBarThickness: 60,
        }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,   // respect the CSS height cap on dashboard cards
          layout: { padding: { top: 20 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#3d2a16", titleColor: "#ffd9a0", bodyColor: "#fff",
              padding: 10, cornerRadius: 8, displayColors: false,
              callbacks: { label: (i) => " " + Number(i.parsed.y).toLocaleString() + (label ? " " + label : "") },
            },
          },
          scales: {
            y: { beginAtZero: true, border: { display: false },
              grid: { color: "rgba(122,74,30,.08)" },
              ticks: { color: "#9a8b76", precision: 0 } },
            x: { border: { display: false }, grid: { display: false },
              ticks: { color: "#5a3514", font: { weight: "600" } } },
          },
        },
        plugins: [valueLabels],
      });
    },
    pie(id, labelValueObj, label) {
      const c = ctx(id); if (!c) return;
      const labels = Object.keys(labelValueObj);
      const values = labels.map((k) => labelValueObj[k]);
      new Chart(c, {
        type: "doughnut",
        data: { labels, datasets: [{ label, data: values,
          backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]) }] },
        options: { responsive: true, maintainAspectRatio: false },
      });
    },
  };
})();
