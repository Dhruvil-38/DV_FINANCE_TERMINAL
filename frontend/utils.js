/* ==========================================================================
   DV FINANCE PLATFORM — utils.js
   DOM lookup, formatting, list/table rendering and the lightweight charts.
   Pure helpers only: no app state, no API calls. Loaded before app.js.
   ========================================================================== */

const qs = (sel, root = document) => root.querySelector(sel);
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const fmtINR = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n || 0);
const fmtNum = (n, d = 2) => Number(n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmtPct = (n, d = 2) => (n === null || n === undefined) ? "—" : `${n >= 0 ? "+" : ""}${fmtNum(n, d)}%`;
const fmtDate = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
const fmtDateTime = (iso) => new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const initials = (name) => (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

/* Enum-ish values (TARGET_HIT, IN_PROGRESS) are shown space-separated. */
const humanize = (value) => value.replace(/_/g, " ");

const signClass = (n) => ((n ?? 0) >= 0 ? "pos" : "neg");

/* ==========================================================================
   RENDERING
   ========================================================================== */

const emptyState = (message) => `<div class="empty-state">${message}</div>`;

/** Renders `items` through `itemHtml`, falling back to an empty-state block. */
function renderList(container, items, itemHtml, emptyMessage) {
  container.innerHTML = items.map(itemHtml).join("") || emptyState(emptyMessage);
}

/** Same as renderList, but the fallback is a table row spanning the columns. */
function renderRows(container, items, rowHtml, { colspan, emptyMessage }) {
  container.innerHTML = items.map(rowHtml).join("")
    || `<tr><td colspan="${colspan}" class="empty-state">${emptyMessage}</td></tr>`;
}

/** <option> markup for a fixed set of enum values, marking the current one. */
function selectOptions(values, selected) {
  return values.map((v) => `<option value="${v}" ${v === selected ? "selected" : ""}>${humanize(v)}</option>`).join("");
}

/* ==========================================================================
   LIGHTWEIGHT CHARTS (no external dependency)
   ========================================================================== */

/** Largest magnitude in the series, floored so a flat/zero series still draws. */
const chartScale = (items, valueKey, floor = 1) => Math.max(...items.map((i) => Math.abs(i[valueKey])), floor);

function renderBarChart(container, items, { labelKey = "label", valueKey = "value" } = {}) {
  if (!items.length) { container.innerHTML = emptyState("No data yet."); return; }
  const max = chartScale(items, valueKey);
  container.innerHTML = `<div class="bar-chart">${items.map((i) => {
    const val = i[valueKey];
    const heightPct = Math.max((Math.abs(val) / max) * 100, 2);
    return `
      <div class="bar-col">
        <span class="bar-value">${fmtNum(val, 1)}</span>
        <div class="bar-fill ${val < 0 ? "neg" : ""}" style="height:${heightPct}%"></div>
        <span class="bar-label">${i[labelKey]}</span>
      </div>`;
  }).join("")}</div>`;
}

function renderHBarChart(container, items, { labelKey = "label", valueKey = "value" } = {}) {
  if (!items.length) { container.innerHTML = emptyState("No data yet."); return; }
  const max = chartScale(items, valueKey);
  container.innerHTML = items.map((i) => {
    const val = i[valueKey];
    const widthPct = Math.max((Math.abs(val) / max) * 100, 1.5);
    return `
      <div class="hbar-row">
        <span>${i[labelKey]}</span>
        <div class="hbar-track"><div class="hbar-fill ${val < 0 ? "neg" : ""}" style="width:${widthPct}%"></div></div>
        <span class="mono">${fmtNum(val, 1)}</span>
      </div>`;
  }).join("");
}

function renderSparkline(container, points, { height = 140 } = {}) {
  if (!points.length) { container.innerHTML = emptyState("No data yet."); return; }
  const width = Math.max(points.length * 26, 260);
  const values = points.map((p) => p.y);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const range = max - min || 1;
  const stepX = width / Math.max(points.length - 1, 1);

  const coords = points.map((p, i) => {
    const x = i * stepX;
    const y = height - ((p.y - min) / range) * (height - 20) - 10;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const last = values[values.length - 1];
  const strokeColor = last >= 0 ? "#14b8a6" : "#ef4444";
  const zeroY = height - ((0 - min) / range) * (height - 20) - 10;

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none">
      <line x1="0" y1="${zeroY}" x2="${width}" y2="${zeroY}" stroke="#212836" stroke-width="1" stroke-dasharray="4 4" />
      <polyline points="${coords.join(" ")}" fill="none" stroke="${strokeColor}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />
    </svg>`;
}
