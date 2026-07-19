/* ==========================================================================
   DV FINANCE PLATFORM — app.js
   Vanilla JS SPA. Handles auth, role-based rendering, and all 8 modules.
   ========================================================================== */

const API_BASE = window.location.origin.includes("5500") || window.location.protocol === "file:"
  ? "http://localhost:8000/api"   // adjust if your API runs elsewhere
  : "/api";

const qs = (sel, root = document) => root.querySelector(sel);
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const fmtINR = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n || 0);
const fmtNum = (n, d = 2) => Number(n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmtPct = (n, d = 2) => (n === null || n === undefined) ? "—" : `${n >= 0 ? "+" : ""}${fmtNum(n, d)}%`;
const fmtDate = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
const fmtDateTime = (iso) => new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const initials = (name) => (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

/* ==========================================================================
   AUTH / SESSION
   ========================================================================== */

const session = {
  get token() { return localStorage.getItem("dv_token"); },
  set token(v) { v ? localStorage.setItem("dv_token", v) : localStorage.removeItem("dv_token"); },
  get user() {
    try { return JSON.parse(localStorage.getItem("dv_user") || "null"); } catch { return null; }
  },
  set user(v) { v ? localStorage.setItem("dv_user", JSON.stringify(v)) : localStorage.removeItem("dv_user"); },
  clear() { this.token = null; this.user = null; },
};

async function apiRequest(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  if (session.token) headers["Authorization"] = `Bearer ${session.token}`;
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : (body !== undefined ? JSON.stringify(body) : undefined),
  });

  if (res.status === 401) {
    logout();
    throw new Error("Session expired — please sign in again.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { detail = (await res.json()).detail || detail; } catch { /* noop */ }
    throw new Error(detail);
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res.blob();
}

const apiGet = (path) => apiRequest(path);
const apiPost = (path, body) => apiRequest(path, { method: "POST", body });
const apiPatch = (path, body) => apiRequest(path, { method: "PATCH", body });
const apiDelete = (path) => apiRequest(path, { method: "DELETE" });

function isFirmRole(role) { return ["admin", "analyst", "staff"].includes(role); }

/* ==========================================================================
   LOGIN
   ========================================================================== */

function initLogin() {
  qsa(".demo-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      qs("#login-email").value = btn.dataset.email;
      qs("#login-password").value = btn.dataset.password;
    });
  });

  qs("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = qs("#login-error");
    const btn = qs("#login-submit");
    errEl.classList.remove("is-visible");
    btn.disabled = true;
    btn.textContent = "Signing in…";

    try {
      const data = await apiPost("/auth/login", {
        email: qs("#login-email").value.trim(),
        password: qs("#login-password").value,
      });
      session.token = data.access_token;
      session.user = { id: data.user_id, name: data.name, role: data.role, client_id: data.client_id };
      enterApp();
    } catch (err) {
      errEl.textContent = err.message || "Sign-in failed.";
      errEl.classList.add("is-visible");
    } finally {
      btn.disabled = false;
      btn.textContent = "Sign In";
    }
  });
}

function logout() {
  session.clear();
  qs("#app-shell").classList.add("hidden");
  qs("#login-screen").classList.remove("hidden");
  qs("#login-password").value = "";
}

function enterApp() {
  const user = session.user;
  qs("#login-screen").classList.add("hidden");
  qs("#app-shell").classList.remove("hidden");

  qs("#user-name").textContent = user.name;
  qs("#user-role").textContent = user.role;
  qs("#user-avatar").textContent = initials(user.name);
  qs("#topbar-avatar").textContent = initials(user.name);
  qs("#portal-label").textContent = user.role === "client" ? "CLIENT PORTAL" : "FIRM PORTAL";
  qs("#dash-greeting").textContent = `Welcome back, ${user.name.split(" ")[0]}`;

  qsa("[data-firm-only]").forEach((el) => {
    el.classList.toggle("hidden", !isFirmRole(user.role));
  });

  loadedPanels.clear();
  switchPanel("dashboard");
}

/* ==========================================================================
   NAVIGATION
   ========================================================================== */

const PANEL_LOADERS = {
  dashboard: loadDashboard,
  market: loadMarket,
  news: () => loadNews(""),
  analytics: loadAnalytics,
  clients: loadClients,
  research: loadResearch,
  tasks: loadTasks,
  documents: loadDocuments,
};

const loadedPanels = new Set();

function switchPanel(name) {
  qsa(".nav-item").forEach((b) => b.classList.toggle("is-active", b.dataset.panel === name));
  qsa(".panel").forEach((p) => p.classList.toggle("is-active", p.dataset.panel === name));
  if (!loadedPanels.has(name)) {
    loadedPanels.add(name);
    PANEL_LOADERS[name]?.();
  }
}

function initNav() {
  qsa(".nav-item[data-panel]").forEach((btn) => btn.addEventListener("click", () => switchPanel(btn.dataset.panel)));
  qsa("[data-refresh]").forEach((btn) => btn.addEventListener("click", () => {
    loadedPanels.delete(btn.dataset.refresh);
    PANEL_LOADERS[btn.dataset.refresh]?.();
  }));
  qs("#logout-btn").addEventListener("click", logout);

  qs("#bell-btn").addEventListener("click", () => qs("#notif-dropdown").classList.toggle("hidden"));
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#bell-btn") && !e.target.closest("#notif-dropdown")) {
      qs("#notif-dropdown").classList.add("hidden");
    }
  });
}

/* ==========================================================================
   TOAST
   ========================================================================== */

function toast(message, isError = false) {
  const el = qs("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("is-visible");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("is-visible"), 3200);
}

/* ==========================================================================
   MODALS
   ========================================================================== */

function openModal(html, onMount) {
  qs("#modal-box").innerHTML = html;
  qs("#modal-overlay").classList.remove("hidden");
  qsa("[data-modal-close]").forEach((b) => b.addEventListener("click", closeModal));
  onMount?.(qs("#modal-box"));
}
function closeModal() { qs("#modal-overlay").classList.add("hidden"); }
qs("#modal-overlay").addEventListener("click", (e) => { if (e.target.id === "modal-overlay") closeModal(); });

/* ==========================================================================
   LIGHTWEIGHT CHARTS (no external dependency)
   ========================================================================== */

function renderBarChart(container, items, { labelKey = "label", valueKey = "value" } = {}) {
  if (!items.length) { container.innerHTML = `<div class="empty-state">No data yet.</div>`; return; }
  const max = Math.max(...items.map((i) => Math.abs(i[valueKey])), 1);
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
  if (!items.length) { container.innerHTML = `<div class="empty-state">No data yet.</div>`; return; }
  const max = Math.max(...items.map((i) => Math.abs(i[valueKey])), 1);
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
  if (!points.length) { container.innerHTML = `<div class="empty-state">No data yet.</div>`; return; }
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

/* ==========================================================================
   DASHBOARD
   ========================================================================== */

async function loadDashboard() {
  try {
    const [summary, notif, updates, perf] = await Promise.all([
      apiGet("/dashboard/summary"),
      apiGet("/dashboard/notifications"),
      apiGet("/dashboard/recent-updates"),
      apiGet("/dashboard/call-performance"),
    ]);

    qs("#summary-cards").innerHTML = summary.cards.map((c) => `
      <div class="card summary-card">
        <div class="card-label">${c.label}</div>
        <div class="summary-value ${c.trend === "up" ? "up" : c.trend === "down" ? "down" : ""}">${c.value}</div>
      </div>
    `).join("");

    renderSparkline(qs("#call-perf-chart"), perf.series.map((s) => ({ x: s.date, y: s.cumulative_pct })));

    const notifBody = notif.notifications.map((n) => `
      <div class="kv-row"><span class="k">${n.message}</span><span class="v" style="color:var(--text-low);font-weight:400;font-size:10.5px">${fmtDateTime(n.created_at)}</span></div>
    `).join("") || `<div class="empty-state">No notifications.</div>`;
    qs("#dash-notifications").innerHTML = notifBody;

    qs("#notif-list").innerHTML = notif.notifications.map((n) => `
      <div class="notif-item"><span class="notif-dot ${n.level}"></span><span>${n.message}</span></div>
    `).join("") || `<div class="notif-item">No notifications.</div>`;
    qs("#bell-dot").style.display = notif.notifications.length ? "block" : "none";

    qs("#recent-updates").innerHTML = `
      <table class="data-table"><tbody>
        ${updates.updates.map((u) => `
          <tr>
            <td><span class="badge ${u.type === "call" ? "ACTIVE" : u.type === "news" ? "info" : "DONE"}">${u.type}</span></td>
            <td>${u.title}</td>
            <td style="color:var(--text-low)">${u.meta}</td>
            <td style="color:var(--text-low)">${fmtDateTime(u.timestamp)}</td>
          </tr>`).join("") || `<tr><td class="empty-state">No recent activity.</td></tr>`}
      </tbody></table>`;
  } catch (err) {
    toast(err.message, true);
  }
}

/* ==========================================================================
   MARKET
   ========================================================================== */

async function loadMarket() {
  const isFirm = isFirmRole(session.user.role);
  try {
    const [watchlist, calls] = await Promise.all([apiGet("/market/watchlist"), apiGet("/market/calls")]);

    qs("#watchlist-body").innerHTML = watchlist.map((w) => `
      <tr>
        <td class="mono">${w.symbol}</td>
        <td>${w.sector}</td>
        <td class="mono">${fmtNum(w.last_price)}</td>
        <td class="mono ${w.day_change_pct >= 0 ? "pos" : "neg"}">${fmtPct(w.day_change_pct)}</td>
        <td style="color:var(--text-low)">${w.added_by || "—"}</td>
        ${isFirm ? `<td><button class="icon-btn" data-del-watch="${w.id}">Remove</button></td>` : ""}
      </tr>
    `).join("") || `<tr><td colspan="6" class="empty-state">Watchlist is empty.</td></tr>`;

    qsa("[data-del-watch]").forEach((btn) => btn.addEventListener("click", async () => {
      try { await apiDelete(`/market/watchlist/${btn.dataset.delWatch}`); toast("Removed from watchlist."); loadedPanels.delete("market"); loadMarket(); }
      catch (err) { toast(err.message, true); }
    }));

    qs("#calls-body").innerHTML = calls.map((c) => `
      <tr>
        <td class="mono">${c.symbol}</td>
        <td>${c.sector}</td>
        <td>${c.direction}</td>
        <td class="mono">${fmtNum(c.entry)}</td>
        <td class="mono">${fmtNum(c.stop_loss)}</td>
        <td class="mono">${fmtNum(c.target)}</td>
        <td><span class="badge ${c.status}">${c.status.replace("_", " ")}</span></td>
        <td class="mono ${(c.result_pct ?? 0) >= 0 ? "pos" : "neg"}">${fmtPct(c.result_pct)}</td>
        <td style="max-width:180px;white-space:normal;color:var(--text-low)">${c.notes || "—"}</td>
        ${isFirm ? `<td>
          <select data-call-status="${c.id}" style="background:var(--bg-input);border:1px solid var(--border);border-radius:5px;font-size:10.5px;padding:4px;">
            ${["ACTIVE", "TARGET_HIT", "SL_HIT", "CLOSED", "CANCELLED"].map((s) => `<option value="${s}" ${s === c.status ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("")}
          </select>
        </td>` : ""}
      </tr>
    `).join("") || `<tr><td colspan="10" class="empty-state">No trade calls yet.</td></tr>`;

    qsa("[data-call-status]").forEach((sel) => sel.addEventListener("change", async () => {
      try { await apiPatch(`/market/calls/${sel.dataset.callStatus}`, { status: sel.value }); toast("Call status updated."); loadedPanels.delete("market"); loadMarket(); loadedPanels.delete("analytics"); }
      catch (err) { toast(err.message, true); }
    }));
  } catch (err) { toast(err.message, true); }

  qs("#btn-add-watchlist")?.addEventListener("click", openAddWatchlistModal, { once: true });
  qs("#btn-add-call")?.addEventListener("click", openAddCallModal, { once: true });
}

function openAddWatchlistModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">Add to Watchlist</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="watch-form">
      <div class="form-field"><label>Symbol</label><input type="text" id="w-symbol" required></div>
      <div class="form-field"><label>Sector</label><input type="text" id="w-sector" value="Unclassified"></div>
      <div class="form-grid">
        <div class="form-field"><label>Last Price</label><input type="number" step="0.01" id="w-price" value="0"></div>
        <div class="form-field"><label>Day Change %</label><input type="number" step="0.01" id="w-change" value="0"></div>
      </div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Add</button></div>
    </form>
  `, () => {
    qs("#watch-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiPost("/market/watchlist", {
          symbol: qs("#w-symbol").value.toUpperCase(), sector: qs("#w-sector").value,
          last_price: parseFloat(qs("#w-price").value), day_change_pct: parseFloat(qs("#w-change").value),
        });
        toast("Added to watchlist."); closeModal(); loadedPanels.delete("market"); loadMarket();
      } catch (err) { toast(err.message, true); }
    });
  });
}

function openAddCallModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">New Trade Call</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="call-form">
      <div class="form-grid">
        <div class="form-field"><label>Symbol</label><input type="text" id="c-symbol" required></div>
        <div class="form-field"><label>Sector</label><input type="text" id="c-sector" value="Technology"></div>
      </div>
      <div class="form-field"><label>Direction</label>
        <select id="c-direction"><option value="LONG">LONG</option><option value="SHORT">SHORT</option></select>
      </div>
      <div class="form-grid">
        <div class="form-field"><label>Entry</label><input type="number" step="0.01" id="c-entry" required></div>
        <div class="form-field"><label>Stop Loss</label><input type="number" step="0.01" id="c-sl" required></div>
      </div>
      <div class="form-field"><label>Target</label><input type="number" step="0.01" id="c-target" required></div>
      <div class="form-field"><label>Notes</label><textarea id="c-notes"></textarea></div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Create Call</button></div>
    </form>
  `, () => {
    qs("#call-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiPost("/market/calls", {
          symbol: qs("#c-symbol").value.toUpperCase(), sector: qs("#c-sector").value,
          direction: qs("#c-direction").value, entry: parseFloat(qs("#c-entry").value),
          stop_loss: parseFloat(qs("#c-sl").value), target: parseFloat(qs("#c-target").value),
          notes: qs("#c-notes").value,
        });
        toast("Trade call created."); closeModal(); loadedPanels.delete("market"); loadMarket();
      } catch (err) { toast(err.message, true); }
    });
  });
}

/* ==========================================================================
   NEWS
   ========================================================================== */

async function loadNews(category) {
  qsa("#news-tabs .tab-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.cat === category));
  try {
    const items = await apiGet(`/news${category ? `?category=${category}` : ""}`);
    qs("#news-list").innerHTML = items.map((n) => `
      <div class="card news-card">
        <div class="news-card-head">
          <h3 class="news-title">${n.title}</h3>
          <span class="badge ${n.category === "FIRM" ? "success" : n.category === "COMPANY" ? "warning" : "info"}">${n.category}</span>
        </div>
        <p class="news-meta">${n.source} · ${fmtDateTime(n.published_at)}</p>
        <p class="news-body">${n.body}</p>
      </div>
    `).join("") || `<div class="empty-state">No news in this category yet.</div>`;
  } catch (err) { toast(err.message, true); }

  qsa("#news-tabs .tab-btn").forEach((b) => {
    b.onclick = () => loadNews(b.dataset.cat);
  });
  qs("#btn-add-news")?.addEventListener("click", openAddNewsModal, { once: true });
}

function openAddNewsModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">Post Update</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="news-form">
      <div class="form-field"><label>Category</label>
        <select id="n-category"><option value="MARKET">Market</option><option value="COMPANY">Company</option><option value="FIRM">Firm Announcement</option></select>
      </div>
      <div class="form-field"><label>Title</label><input type="text" id="n-title" required></div>
      <div class="form-field"><label>Body</label><textarea id="n-body"></textarea></div>
      <div class="form-field"><label>Source</label><input type="text" id="n-source" value="DV Finance Desk"></div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Publish</button></div>
    </form>
  `, () => {
    qs("#news-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiPost("/news", { category: qs("#n-category").value, title: qs("#n-title").value, body: qs("#n-body").value, source: qs("#n-source").value });
        toast("Published."); closeModal(); loadNews("");
      } catch (err) { toast(err.message, true); }
    });
  });
}

/* ==========================================================================
   ANALYTICS
   ========================================================================== */

async function loadAnalytics() {
  const isFirm = isFirmRole(session.user.role);
  try {
    const calls = [
      apiGet("/analytics/win-rate"), apiGet("/analytics/accuracy"),
      apiGet("/analytics/monthly-performance"), apiGet("/analytics/sector-performance"),
      apiGet("/analytics/call-history"),
    ];
    if (isFirm) calls.push(apiGet("/analytics/client-engagement"));
    const results = await Promise.all(calls);
    const [winRate, accuracy, monthly, sector, history, engagement] = results;

    qs("#an-winrate").textContent = `${winRate.win_rate_pct}%`;
    qs("#an-winrate-sub").textContent = `${winRate.wins}W / ${winRate.losses}L of ${winRate.total_closed} closed`;

    qs("#an-accuracy").textContent = `${accuracy.accuracy_pct}%`;
    qs("#an-accuracy-sub").textContent = `Sample: ${accuracy.sample_size} calls · σ ${accuracy.std_dev_pct}%`;

    qs("#an-avgresult").textContent = fmtPct(accuracy.avg_result_pct);

    renderBarChart(qs("#chart-monthly"), monthly.months, { labelKey: "month", valueKey: "avg_result_pct" });
    renderHBarChart(qs("#chart-sector"), sector.sectors, { labelKey: "sector", valueKey: "avg_result_pct" });
    renderSparkline(qs("#chart-history"), history.history.map((h) => ({ x: h.created_at, y: h.cumulative_pct })));

    if (isFirm && engagement) {
      renderHBarChart(qs("#chart-engagement"), engagement.clients, { labelKey: "client_name", valueKey: "engagement_score" });
    }
  } catch (err) { toast(err.message, true); }

  qsa("[data-export]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const blob = await apiRequest(`/reports/export?type=${btn.dataset.export}`);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = `dvfinance_${btn.dataset.export}.csv`; a.click();
        URL.revokeObjectURL(url);
      } catch (err) { toast(err.message, true); }
    };
  });
}

/* ==========================================================================
   CLIENTS
   ========================================================================== */

async function loadClients() {
  try {
    const clients = await apiGet("/clients");
    qs("#clients-body").innerHTML = clients.map((c) => `
      <tr>
        <td>${c.name}</td>
        <td style="color:var(--text-low)">${c.email}</td>
        <td><span class="client-tier-tag ${c.tier}">${c.tier}</span></td>
        <td><span class="badge ${c.status}">${c.status}</span></td>
        <td>${c.assigned_analyst || "—"}</td>
        <td class="mono">${fmtINR(c.aum)}</td>
        <td style="color:var(--text-low)">${fmtDate(c.joined_at)}</td>
      </tr>
    `).join("") || `<tr><td colspan="7" class="empty-state">No clients yet.</td></tr>`;
  } catch (err) { toast(err.message, true); }

  qs("#btn-add-client")?.addEventListener("click", openAddClientModal, { once: true });
}

function openAddClientModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">Add Client</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="client-form">
      <div class="form-field"><label>Name</label><input type="text" id="cl-name" required></div>
      <div class="form-field"><label>Email</label><input type="email" id="cl-email" required></div>
      <div class="form-grid">
        <div class="form-field"><label>Phone</label><input type="text" id="cl-phone"></div>
        <div class="form-field"><label>Tier</label>
          <select id="cl-tier"><option>Standard</option><option>Premium</option><option>Institutional</option></select>
        </div>
      </div>
      <div class="form-grid">
        <div class="form-field"><label>Assigned Analyst</label><input type="text" id="cl-analyst"></div>
        <div class="form-field"><label>AUM (₹)</label><input type="number" step="1000" id="cl-aum" value="0"></div>
      </div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Add Client</button></div>
    </form>
  `, () => {
    qs("#client-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiPost("/clients", {
          name: qs("#cl-name").value, email: qs("#cl-email").value, phone: qs("#cl-phone").value,
          tier: qs("#cl-tier").value, assigned_analyst: qs("#cl-analyst").value, aum: parseFloat(qs("#cl-aum").value || 0),
        });
        toast("Client added."); closeModal(); loadedPanels.delete("clients"); loadClients();
      } catch (err) { toast(err.message, true); }
    });
  });
}

/* ==========================================================================
   RESEARCH NOTES
   ========================================================================== */

async function loadResearch() {
  try {
    const notes = await apiGet("/research-notes");
    qs("#notes-list").innerHTML = notes.map((n) => `
      <div class="card">
        <div class="news-card-head"><h3 class="news-title">${n.title}</h3><span class="mono" style="font-size:10.5px;color:var(--text-low)">${fmtDate(n.created_at)}</span></div>
        <p class="news-body">${n.body}</p>
        <p style="font-size:10.5px;color:var(--text-low);margin-top:8px;">By ${n.created_by}${n.client_id ? ` · Client #${n.client_id}` : ""}${n.call_id ? ` · Call #${n.call_id}` : ""}</p>
      </div>
    `).join("") || `<div class="empty-state">No research notes yet.</div>`;
  } catch (err) { toast(err.message, true); }

  qs("#btn-add-note")?.addEventListener("click", async () => {
    let clientOptions = "<option value=''>— None —</option>";
    if (isFirmRole(session.user.role)) {
      try {
        const clients = await apiGet("/clients");
        clientOptions += clients.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
      } catch { /* ignore */ }
    }
    openModal(`
      <div class="modal-head"><h3 class="modal-title">New Research Note</h3><button class="modal-close" data-modal-close>×</button></div>
      <form id="note-form">
        <div class="form-field"><label>Title</label><input type="text" id="note-title" required></div>
        <div class="form-field"><label>Body</label><textarea id="note-body"></textarea></div>
        <div class="form-field"><label>Linked Client (optional)</label><select id="note-client">${clientOptions}</select></div>
        <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Save Note</button></div>
      </form>
    `, () => {
      qs("#note-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await apiPost("/research-notes", {
            title: qs("#note-title").value, body: qs("#note-body").value,
            client_id: qs("#note-client").value ? parseInt(qs("#note-client").value) : null,
          });
          toast("Note saved."); closeModal(); loadedPanels.delete("research"); loadResearch();
        } catch (err) { toast(err.message, true); }
      });
    });
  }, { once: true });
}

/* ==========================================================================
   TASKS
   ========================================================================== */

async function loadTasks() {
  try {
    const tasks = await apiGet("/tasks");
    ["TODO", "IN_PROGRESS", "DONE"].forEach((status) => {
      const col = qs(`#task-col-${status}`);
      const items = tasks.filter((t) => t.status === status);
      col.innerHTML = items.map((t) => `
        <div class="task-card">
          <div class="task-card-title">${t.title}</div>
          <div class="task-card-meta"><span class="badge ${t.priority}">${t.priority}</span><span>${t.assigned_to || "Unassigned"}</span></div>
          ${t.due_date ? `<div style="font-size:10px;color:var(--text-low);margin-top:6px;">Due ${fmtDate(t.due_date)}</div>` : ""}
          <select data-task-status="${t.id}">
            ${["TODO", "IN_PROGRESS", "DONE"].map((s) => `<option value="${s}" ${s === t.status ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("")}
          </select>
        </div>
      `).join("") || `<div class="empty-state">Empty</div>`;
    });

    qsa("[data-task-status]").forEach((sel) => sel.addEventListener("change", async () => {
      try { await apiPatch(`/tasks/${sel.dataset.taskStatus}`, { status: sel.value }); toast("Task updated."); loadedPanels.delete("tasks"); loadTasks(); }
      catch (err) { toast(err.message, true); }
    }));
  } catch (err) { toast(err.message, true); }

  qs("#btn-add-task")?.addEventListener("click", openAddTaskModal, { once: true });
}

function openAddTaskModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">New Task</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="task-form">
      <div class="form-field"><label>Title</label><input type="text" id="t-title" required></div>
      <div class="form-field"><label>Description</label><textarea id="t-desc"></textarea></div>
      <div class="form-grid">
        <div class="form-field"><label>Priority</label><select id="t-priority"><option>LOW</option><option selected>MEDIUM</option><option>HIGH</option></select></div>
        <div class="form-field"><label>Assigned To</label><input type="text" id="t-assignee"></div>
      </div>
      <div class="form-field"><label>Due Date</label><input type="date" id="t-due"></div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Create Task</button></div>
    </form>
  `, () => {
    qs("#task-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiPost("/tasks", {
          title: qs("#t-title").value, description: qs("#t-desc").value, priority: qs("#t-priority").value,
          assigned_to: qs("#t-assignee").value, due_date: qs("#t-due").value ? new Date(qs("#t-due").value).toISOString() : null,
        });
        toast("Task created."); closeModal(); loadedPanels.delete("tasks"); loadTasks();
      } catch (err) { toast(err.message, true); }
    });
  });
}

/* ==========================================================================
   DOCUMENTS
   ========================================================================== */

async function loadDocuments() {
  try {
    const docs = await apiGet("/documents");
    qs("#documents-body").innerHTML = docs.map((d) => `
      <tr>
        <td>▥ ${d.filename}</td>
        <td><span class="badge info">${d.category}</span></td>
        <td class="mono">${fmtNum(d.size_kb, 0)} KB</td>
        <td style="color:var(--text-low)">${d.uploaded_by}</td>
        <td style="color:var(--text-low)">${fmtDate(d.uploaded_at)}</td>
      </tr>
    `).join("") || `<tr><td colspan="5" class="empty-state">No documents yet.</td></tr>`;
  } catch (err) { toast(err.message, true); }

  qs("#btn-add-document")?.addEventListener("click", openAddDocumentModal, { once: true });
}

function openAddDocumentModal() {
  openModal(`
    <div class="modal-head"><h3 class="modal-title">Register Document</h3><button class="modal-close" data-modal-close>×</button></div>
    <form id="doc-form">
      <div class="form-field"><label>File</label><input type="file" id="doc-file" required></div>
      <div class="form-field"><label>Category</label>
        <select id="doc-category"><option>General</option><option>Research</option><option>Compliance</option><option>Client</option></select>
      </div>
      <div class="modal-footer"><button type="button" class="btn-ghost" data-modal-close>Cancel</button><button type="submit" class="btn-solid">Upload</button></div>
    </form>
  `, () => {
    qs("#doc-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fileInput = qs("#doc-file");
      if (!fileInput.files.length) return;
      const form = new FormData();
      form.append("file", fileInput.files[0]);
      form.append("category", qs("#doc-category").value);
      try {
        await apiRequest("/documents/upload", { method: "POST", body: form, isForm: true });
        toast("Document uploaded."); closeModal(); loadedPanels.delete("documents"); loadDocuments();
      } catch (err) { toast(err.message, true); }
    });
  });
}

/* ==========================================================================
   INIT
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initLogin();
  initNav();

  if (session.token && session.user) {
    enterApp();
  }
});
