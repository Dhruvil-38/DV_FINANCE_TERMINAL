/* ==========================================================================
   DV FINANCE PLATFORM — app.js
   Vanilla JS SPA. Handles auth, role-based rendering, and all 8 modules.
   ========================================================================== */

const API_BASE = window.location.origin.includes("5500") || window.location.protocol === "file:"
  ? "http://localhost:8000/api"   // adjust if your API runs elsewhere
  : "/api";

/* DOM lookup, formatting, rendering and chart helpers live in utils.js. */

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

const toastError = (err) => toast(err.message, true);

/** Runs a load/render step, surfacing any failure as an error toast. */
async function guard(work) {
  try { return await work(); } catch (err) { toastError(err); }
}

/**
 * Runs a write request, then confirms it and refreshes the affected panels.
 * `reload` is re-fetched immediately; `invalidate` panels re-fetch on next visit.
 */
async function mutate(request, { success, reload, invalidate = [] } = {}) {
  return guard(async () => {
    const result = await request();
    if (success) toast(success);
    invalidate.forEach((name) => loadedPanels.delete(name));
    if (reload) reloadPanel(reload);
    return result;
  });
}

/** Attaches a handler that receives the element, for every match of `selector`. */
function bindEach(selector, event, handler) {
  qsa(selector).forEach((el) => el.addEventListener(event, () => handler(el)));
}

/** Wires a toolbar button that opens a modal — once, since panels re-render. */
function bindOnce(selector, handler) {
  qs(selector)?.addEventListener("click", handler, { once: true });
}

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

/** Drops the cached state of a panel and re-runs its loader. */
function reloadPanel(name) {
  loadedPanels.delete(name);
  PANEL_LOADERS[name]?.();
}

function initNav() {
  bindEach(".nav-item[data-panel]", "click", (btn) => switchPanel(btn.dataset.panel));
  bindEach("[data-refresh]", "click", (btn) => reloadPanel(btn.dataset.refresh));
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

/**
 * Wires a modal form: submits, closes the modal, then refreshes `reload`.
 * `submit` reads the form fields and performs the write request.
 */
function bindModalForm(formSelector, { submit, success, reload }) {
  qs(formSelector).addEventListener("submit", (e) => {
    e.preventDefault();
    mutate(async () => { await submit(); closeModal(); }, { success, reload });
  });
}

function openModal(html, onMount) {
  qs("#modal-box").innerHTML = html;
  qs("#modal-overlay").classList.remove("hidden");
  qsa("[data-modal-close]").forEach((b) => b.addEventListener("click", closeModal));
  onMount?.(qs("#modal-box"));
}
function closeModal() { qs("#modal-overlay").classList.add("hidden"); }
qs("#modal-overlay").addEventListener("click", (e) => { if (e.target.id === "modal-overlay") closeModal(); });

/* ==========================================================================
   DASHBOARD
   ========================================================================== */

async function loadDashboard() {
  await guard(async () => {
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

    renderList(qs("#dash-notifications"), notif.notifications, (n) => `
      <div class="kv-row"><span class="k">${n.message}</span><span class="v" style="color:var(--text-low);font-weight:400;font-size:10.5px">${fmtDateTime(n.created_at)}</span></div>
    `, "No notifications.");

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
  });
}

/* ==========================================================================
   MARKET
   ========================================================================== */

const CALL_STATUSES = ["ACTIVE", "TARGET_HIT", "SL_HIT", "CLOSED", "CANCELLED"];

async function loadMarket() {
  const isFirm = isFirmRole(session.user.role);
  await guard(async () => {
    const [watchlist, calls] = await Promise.all([apiGet("/market/watchlist"), apiGet("/market/calls")]);

    renderRows(qs("#watchlist-body"), watchlist, (w) => `
      <tr>
        <td class="mono">${w.symbol}</td>
        <td>${w.sector}</td>
        <td class="mono">${fmtNum(w.last_price)}</td>
        <td class="mono ${signClass(w.day_change_pct)}">${fmtPct(w.day_change_pct)}</td>
        <td style="color:var(--text-low)">${w.added_by || "—"}</td>
        ${isFirm ? `<td><button class="icon-btn" data-del-watch="${w.id}">Remove</button></td>` : ""}
      </tr>
    `, { colspan: 6, emptyMessage: "Watchlist is empty." });

    bindEach("[data-del-watch]", "click", (btn) => mutate(
      () => apiDelete(`/market/watchlist/${btn.dataset.delWatch}`),
      { success: "Removed from watchlist.", reload: "market" },
    ));

    renderRows(qs("#calls-body"), calls, (c) => `
      <tr>
        <td class="mono">${c.symbol}</td>
        <td>${c.sector}</td>
        <td>${c.direction}</td>
        <td class="mono">${fmtNum(c.entry)}</td>
        <td class="mono">${fmtNum(c.stop_loss)}</td>
        <td class="mono">${fmtNum(c.target)}</td>
        <td><span class="badge ${c.status}">${humanize(c.status)}</span></td>
        <td class="mono ${signClass(c.result_pct)}">${fmtPct(c.result_pct)}</td>
        <td style="max-width:180px;white-space:normal;color:var(--text-low)">${c.notes || "—"}</td>
        ${isFirm ? `<td>
          <select data-call-status="${c.id}" style="background:var(--bg-input);border:1px solid var(--border);border-radius:5px;font-size:10.5px;padding:4px;">
            ${selectOptions(CALL_STATUSES, c.status)}
          </select>
        </td>` : ""}
      </tr>
    `, { colspan: 10, emptyMessage: "No trade calls yet." });

    bindEach("[data-call-status]", "change", (sel) => mutate(
      () => apiPatch(`/market/calls/${sel.dataset.callStatus}`, { status: sel.value }),
      { success: "Call status updated.", reload: "market", invalidate: ["analytics"] },
    ));
  });

  bindOnce("#btn-add-watchlist", openAddWatchlistModal);
  bindOnce("#btn-add-call", openAddCallModal);
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
  `, () => bindModalForm("#watch-form", {
    submit: () => apiPost("/market/watchlist", {
      symbol: qs("#w-symbol").value.toUpperCase(), sector: qs("#w-sector").value,
      last_price: parseFloat(qs("#w-price").value), day_change_pct: parseFloat(qs("#w-change").value),
    }),
    success: "Added to watchlist.", reload: "market",
  }));
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
  `, () => bindModalForm("#call-form", {
    submit: () => apiPost("/market/calls", {
      symbol: qs("#c-symbol").value.toUpperCase(), sector: qs("#c-sector").value,
      direction: qs("#c-direction").value, entry: parseFloat(qs("#c-entry").value),
      stop_loss: parseFloat(qs("#c-sl").value), target: parseFloat(qs("#c-target").value),
      notes: qs("#c-notes").value,
    }),
    success: "Trade call created.", reload: "market",
  }));
}

/* ==========================================================================
   NEWS
   ========================================================================== */

async function loadNews(category) {
  qsa("#news-tabs .tab-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.cat === category));
  await guard(async () => {
    const items = await apiGet(`/news${category ? `?category=${category}` : ""}`);
    renderList(qs("#news-list"), items, (n) => `
      <div class="card news-card">
        <div class="news-card-head">
          <h3 class="news-title">${n.title}</h3>
          <span class="badge ${n.category === "FIRM" ? "success" : n.category === "COMPANY" ? "warning" : "info"}">${n.category}</span>
        </div>
        <p class="news-meta">${n.source} · ${fmtDateTime(n.published_at)}</p>
        <p class="news-body">${n.body}</p>
      </div>
    `, "No news in this category yet.");
  });

  qsa("#news-tabs .tab-btn").forEach((b) => {
    b.onclick = () => loadNews(b.dataset.cat);
  });
  bindOnce("#btn-add-news", openAddNewsModal);
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
  `, () => bindModalForm("#news-form", {
    submit: () => apiPost("/news", { category: qs("#n-category").value, title: qs("#n-title").value, body: qs("#n-body").value, source: qs("#n-source").value }),
    success: "Published.", reload: "news",
  }));
}

/* ==========================================================================
   ANALYTICS
   ========================================================================== */

async function loadAnalytics() {
  const isFirm = isFirmRole(session.user.role);
  await guard(async () => {
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
  });

  qsa("[data-export]").forEach((btn) => {
    btn.onclick = () => guard(async () => {
      const blob = await apiRequest(`/reports/export?type=${btn.dataset.export}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `dvfinance_${btn.dataset.export}.csv`; a.click();
      URL.revokeObjectURL(url);
    });
  });
}

/* ==========================================================================
   CLIENTS
   ========================================================================== */

async function loadClients() {
  await guard(async () => {
    const clients = await apiGet("/clients");
    renderRows(qs("#clients-body"), clients, (c) => `
      <tr>
        <td>${c.name}</td>
        <td style="color:var(--text-low)">${c.email}</td>
        <td><span class="client-tier-tag ${c.tier}">${c.tier}</span></td>
        <td><span class="badge ${c.status}">${c.status}</span></td>
        <td>${c.assigned_analyst || "—"}</td>
        <td class="mono">${fmtINR(c.aum)}</td>
        <td style="color:var(--text-low)">${fmtDate(c.joined_at)}</td>
      </tr>
    `, { colspan: 7, emptyMessage: "No clients yet." });
  });

  bindOnce("#btn-add-client", openAddClientModal);
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
  `, () => bindModalForm("#client-form", {
    submit: () => apiPost("/clients", {
      name: qs("#cl-name").value, email: qs("#cl-email").value, phone: qs("#cl-phone").value,
      tier: qs("#cl-tier").value, assigned_analyst: qs("#cl-analyst").value, aum: parseFloat(qs("#cl-aum").value || 0),
    }),
    success: "Client added.", reload: "clients",
  }));
}

/* ==========================================================================
   RESEARCH NOTES
   ========================================================================== */

async function loadResearch() {
  await guard(async () => {
    const notes = await apiGet("/research-notes");
    renderList(qs("#notes-list"), notes, (n) => `
      <div class="card">
        <div class="news-card-head"><h3 class="news-title">${n.title}</h3><span class="mono" style="font-size:10.5px;color:var(--text-low)">${fmtDate(n.created_at)}</span></div>
        <p class="news-body">${n.body}</p>
        <p style="font-size:10.5px;color:var(--text-low);margin-top:8px;">By ${n.created_by}${n.client_id ? ` · Client #${n.client_id}` : ""}${n.call_id ? ` · Call #${n.call_id}` : ""}</p>
      </div>
    `, "No research notes yet.");
  });

  bindOnce("#btn-add-note", async () => {
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
    `, () => bindModalForm("#note-form", {
      submit: () => apiPost("/research-notes", {
        title: qs("#note-title").value, body: qs("#note-body").value,
        client_id: qs("#note-client").value ? parseInt(qs("#note-client").value) : null,
      }),
      success: "Note saved.", reload: "research",
    }));
  });
}

/* ==========================================================================
   TASKS
   ========================================================================== */

const TASK_STATUSES = ["TODO", "IN_PROGRESS", "DONE"];

async function loadTasks() {
  await guard(async () => {
    const tasks = await apiGet("/tasks");
    TASK_STATUSES.forEach((status) => {
      renderList(qs(`#task-col-${status}`), tasks.filter((t) => t.status === status), (t) => `
        <div class="task-card">
          <div class="task-card-title">${t.title}</div>
          <div class="task-card-meta"><span class="badge ${t.priority}">${t.priority}</span><span>${t.assigned_to || "Unassigned"}</span></div>
          ${t.due_date ? `<div style="font-size:10px;color:var(--text-low);margin-top:6px;">Due ${fmtDate(t.due_date)}</div>` : ""}
          <select data-task-status="${t.id}">
            ${selectOptions(TASK_STATUSES, t.status)}
          </select>
        </div>
      `, "Empty");
    });

    bindEach("[data-task-status]", "change", (sel) => mutate(
      () => apiPatch(`/tasks/${sel.dataset.taskStatus}`, { status: sel.value }),
      { success: "Task updated.", reload: "tasks" },
    ));
  });

  bindOnce("#btn-add-task", openAddTaskModal);
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
  `, () => bindModalForm("#task-form", {
    submit: () => apiPost("/tasks", {
      title: qs("#t-title").value, description: qs("#t-desc").value, priority: qs("#t-priority").value,
      assigned_to: qs("#t-assignee").value, due_date: qs("#t-due").value ? new Date(qs("#t-due").value).toISOString() : null,
    }),
    success: "Task created.", reload: "tasks",
  }));
}

/* ==========================================================================
   DOCUMENTS
   ========================================================================== */

async function loadDocuments() {
  await guard(async () => {
    const docs = await apiGet("/documents");
    renderRows(qs("#documents-body"), docs, (d) => `
      <tr>
        <td>▥ ${d.filename}</td>
        <td><span class="badge info">${d.category}</span></td>
        <td class="mono">${fmtNum(d.size_kb, 0)} KB</td>
        <td style="color:var(--text-low)">${d.uploaded_by}</td>
        <td style="color:var(--text-low)">${fmtDate(d.uploaded_at)}</td>
      </tr>
    `, { colspan: 5, emptyMessage: "No documents yet." });
  });

  bindOnce("#btn-add-document", openAddDocumentModal);
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
  `, () => bindModalForm("#doc-form", {
    submit: () => {
      const form = new FormData();
      form.append("file", qs("#doc-file").files[0]);
      form.append("category", qs("#doc-category").value);
      return apiRequest("/documents/upload", { method: "POST", body: form, isForm: true });
    },
    success: "Document uploaded.", reload: "documents",
  }));
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
