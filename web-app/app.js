const STORAGE_KEY = "homeai-web-settings-v1";

const TOOL_PRESETS = [
  {
    id: "interior-design",
    title: "Interior Design",
    subtitle: "Upload a pic, choose a style, let AI redesign the room.",
    styleId: "modern",
    operation: "restyle",
    beforeImage: "https://picsum.photos/id/1062/960/960",
    afterImage: "https://picsum.photos/id/1063/960/960",
  },
  {
    id: "exterior-design",
    title: "Exterior Design",
    subtitle: "Snap your facade and transform curb appeal.",
    styleId: "scandi",
    operation: "restyle",
    beforeImage: "https://picsum.photos/id/104/960/960",
    afterImage: "https://picsum.photos/id/105/960/960",
  },
  {
    id: "paint",
    title: "Paint",
    subtitle: "Test walls with a new color in seconds.",
    styleId: "color-refresh",
    operation: "repaint",
    beforeImage: "https://picsum.photos/id/1076/960/960",
    afterImage: "https://picsum.photos/id/1077/960/960",
  },
  {
    id: "floor-restyle",
    title: "Floor Restyle",
    subtitle: "Preview flooring materials with instant swaps.",
    styleId: "oak-floor",
    operation: "replace",
    beforeImage: "https://picsum.photos/id/1078/960/960",
    afterImage: "https://picsum.photos/id/1079/960/960",
  },
  {
    id: "garden-design",
    title: "Garden Design",
    subtitle: "Give your backyard a fresh concept.",
    styleId: "garden-modern",
    operation: "restyle",
    beforeImage: "https://picsum.photos/id/101/960/960",
    afterImage: "https://picsum.photos/id/102/960/960",
  },
  {
    id: "reference-style",
    title: "Reference Style",
    subtitle: "Apply a curated style mood across your space.",
    styleId: "reference-style",
    operation: "restyle",
    beforeImage: "https://picsum.photos/id/1035/960/960",
    afterImage: "https://picsum.photos/id/1039/960/960",
  },
];

const TERMINAL_JOB_STATUS = new Set(["completed", "failed", "canceled"]);

const state = {
  apiBaseUrl: "http://localhost:8000",
  userId: "homeai_demo_user",
  token: "",
  currentTab: "tools",
  discoverTab: "",
  me: null,
  profile: null,
  experimentAssignments: [],
  catalog: [],
  board: [],
  discoverFeed: null,
  currentJob: null,
  pollHandle: null,
};

const refs = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  userId: document.getElementById("userId"),
  authState: document.getElementById("authState"),
  creditState: document.getElementById("creditState"),
  planState: document.getElementById("planState"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  panels: Array.from(document.querySelectorAll(".panel")),
  toolsGrid: document.getElementById("toolsGrid"),
  boardGrid: document.getElementById("boardGrid"),
  boardEmpty: document.getElementById("boardEmpty"),
  imageUrl: document.getElementById("imageUrl"),
  projectId: document.getElementById("projectId"),
  styleId: document.getElementById("styleId"),
  operation: document.getElementById("operation"),
  tier: document.getElementById("tier"),
  promptOverrides: document.getElementById("promptOverrides"),
  jobResult: document.getElementById("jobResult"),
  discoverTabs: document.getElementById("discoverTabs"),
  discoverSections: document.getElementById("discoverSections"),
  profileSummary: document.getElementById("profileSummary"),
  catalogTableBody: document.getElementById("catalogTableBody"),
  checkoutPlanId: document.getElementById("checkoutPlanId"),
  successUrl: document.getElementById("successUrl"),
  cancelUrl: document.getElementById("cancelUrl"),
  activityLog: document.getElementById("activityLog"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function log(message, level = "INFO") {
  const timestamp = new Date().toLocaleTimeString();
  const current = refs.activityLog.textContent === "Waiting for actions..." ? "" : refs.activityLog.textContent;
  const line = `[${timestamp}] [${level}] ${message}`;
  const merged = current ? `${line}\n${current}` : line;
  refs.activityLog.textContent = merged.split("\n").slice(0, 150).join("\n");
}

function normalizeBaseUrl(rawValue) {
  return rawValue.trim().replace(/\/+$/, "");
}

function readInputsToState() {
  state.apiBaseUrl = normalizeBaseUrl(refs.apiBaseUrl.value || "");
  state.userId = refs.userId.value.trim();
}

function syncInputsFromState() {
  refs.apiBaseUrl.value = state.apiBaseUrl;
  refs.userId.value = state.userId;
}

function setDefaultCheckoutUrls() {
  const base = `${window.location.origin}${window.location.pathname}`;
  refs.successUrl.value = `${base}?checkout=success`;
  refs.cancelUrl.value = `${base}?checkout=cancel`;
}

function saveSessionSettings() {
  const payload = {
    apiBaseUrl: state.apiBaseUrl,
    userId: state.userId,
    token: state.token,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function loadSessionSettings() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    syncInputsFromState();
    return;
  }

  try {
    const parsed = JSON.parse(raw);
    state.apiBaseUrl = normalizeBaseUrl(parsed.apiBaseUrl || state.apiBaseUrl);
    state.userId = parsed.userId || state.userId;
    state.token = parsed.token || "";
  } catch (error) {
    log(`Failed to read saved session: ${error.message}`, "ERROR");
  }
  syncInputsFromState();
}

async function apiRequest(path, { method = "GET", body = undefined, authRequired = true } = {}) {
  if (!state.apiBaseUrl) {
    throw new Error("API Base URL is required.");
  }

  if (authRequired && !state.token) {
    throw new Error("Login is required for this action.");
  }

  const headers = { "Content-Type": "application/json" };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(`${state.apiBaseUrl}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail =
      typeof payload === "string"
        ? payload
        : payload?.detail
          ? typeof payload.detail === "string"
            ? payload.detail
            : JSON.stringify(payload.detail)
          : JSON.stringify(payload);
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return payload;
}

async function trackEvent(eventName, extra = {}) {
  try {
    await apiRequest("/v1/analytics/events", {
      method: "POST",
      authRequired: false,
      body: {
        event_name: eventName,
        user_id: state.userId || null,
        platform: "web",
        ...extra,
      },
    });
  } catch {
    // Do not block UX when analytics endpoint is unavailable.
  }
}

function setTab(tabName) {
  state.currentTab = tabName;
  for (const button of refs.tabButtons) {
    button.classList.toggle("active", button.dataset.tab === tabName);
  }
  for (const panel of refs.panels) {
    panel.classList.toggle("active", panel.id === `panel-${tabName}`);
  }
}

function renderStatusPills() {
  if (state.token && state.me) {
    refs.authState.textContent = `Auth: ${state.me.user_id}`;
  } else if (state.token) {
    refs.authState.textContent = `Auth: token saved`;
  } else {
    refs.authState.textContent = "Auth: logged out";
  }

  const balance = state.profile?.credits?.balance;
  refs.creditState.textContent = typeof balance === "number" ? `Credits: ${balance}` : "Credits: -";

  const planName = state.profile?.effective_plan?.display_name || "-";
  refs.planState.textContent = `Plan: ${planName}`;
}

function renderTools() {
  refs.toolsGrid.innerHTML = TOOL_PRESETS.map((tool) => {
    return `<article class="tool-card">
      <div class="tool-images">
        <img src="${escapeHtml(tool.beforeImage)}" alt="${escapeHtml(tool.title)} before" />
        <img src="${escapeHtml(tool.afterImage)}" alt="${escapeHtml(tool.title)} after" />
      </div>
      <div class="tool-content">
        <h4>${escapeHtml(tool.title)}</h4>
        <p>${escapeHtml(tool.subtitle)}</p>
        <button
          type="button"
          class="btn btn-primary"
          data-tool-try="1"
          data-style="${escapeHtml(tool.styleId)}"
          data-operation="${escapeHtml(tool.operation)}"
          data-image="${escapeHtml(tool.beforeImage)}"
        >
          Try It
        </button>
      </div>
    </article>`;
  }).join("");

  if (!Array.isArray(state.board) || state.board.length === 0) {
    refs.boardGrid.innerHTML = "";
    refs.boardEmpty.classList.remove("hidden");
    return;
  }

  refs.boardEmpty.classList.add("hidden");
  refs.boardGrid.innerHTML = state.board
    .map((item) => {
      const image = item.last_output_url || item.cover_image_url || "https://picsum.photos/id/1084/900/700";
      return `<article class="board-card">
        <img src="${escapeHtml(image)}" alt="${escapeHtml(item.project_id)}" />
        <div class="board-content">
          <p><strong>${escapeHtml(item.project_id)}</strong></p>
          <small>Status: ${escapeHtml(item.last_status || "-")}</small>
          <small>Generations: ${escapeHtml(item.generation_count || 0)}</small>
        </div>
      </article>`;
    })
    .join("");
}

function renderJobResult() {
  const job = state.currentJob;
  if (!job) {
    refs.jobResult.innerHTML = '<p class="muted">No render job yet.</p>';
    return;
  }

  const output = job.output_url
    ? `<img class="job-output" src="${escapeHtml(job.output_url)}" alt="Rendered output" />`
    : '<p class="muted">No output yet. Polling while job is running.</p>';
  refs.jobResult.innerHTML = `<p class="job-meta"><strong>${escapeHtml(job.id)}</strong></p>
    <p class="job-meta">Status: ${escapeHtml(job.status)} | Provider: ${escapeHtml(job.provider || "-")}</p>
    <p class="job-meta">Model: ${escapeHtml(job.provider_model || "-")} | Est Cost: $${Number(job.estimated_cost_usd || 0).toFixed(4)}</p>
    <div class="job-grid">
      <div>${output}</div>
      <div>
        <p class="job-meta">Updated: ${escapeHtml(job.updated_at ? new Date(job.updated_at).toLocaleString() : "-")}</p>
        <p class="job-meta">Error: ${escapeHtml(job.error_code || "-")}</p>
        <button id="pollNowButton" type="button" class="btn">Poll Now</button>
      </div>
    </div>`;

  const pollNowButton = document.getElementById("pollNowButton");
  if (pollNowButton) {
    pollNowButton.addEventListener("click", async () => {
      if (!state.currentJob?.id) {
        return;
      }
      try {
        await pollRenderJob(state.currentJob.id);
      } catch (error) {
        log(`Polling failed: ${error.message}`, "ERROR");
      }
    });
  }
}

function renderDiscover() {
  const tabs = state.discoverFeed?.tabs || [];
  const activeTab = state.discoverTab || "";
  refs.discoverTabs.innerHTML = [
    `<button type="button" class="discover-pill ${activeTab === "" ? "active" : ""}" data-discover-tab="">All</button>`,
    ...tabs.map((tab) => {
      const isActive = tab.toLowerCase() === activeTab.toLowerCase();
      return `<button type="button" class="discover-pill ${isActive ? "active" : ""}" data-discover-tab="${escapeHtml(tab)}">${escapeHtml(tab)}</button>`;
    }),
  ].join("");

  const sections = state.discoverFeed?.sections || [];
  if (sections.length === 0) {
    refs.discoverSections.innerHTML = '<p class="empty-text">No discover items for this category.</p>';
    return;
  }

  refs.discoverSections.innerHTML = sections
    .map((section) => {
      const items = section.items || [];
      return `<article class="discover-group">
        <h3>${escapeHtml(section.title)}</h3>
        <div class="discover-items">
          ${items
            .map((item) => {
              return `<article class="discover-card">
                <div class="pair">
                  <img src="${escapeHtml(item.before_image_url)}" alt="${escapeHtml(item.title)} before" />
                  <img src="${escapeHtml(item.after_image_url)}" alt="${escapeHtml(item.title)} after" />
                </div>
                <div class="copy">
                  <h4>${escapeHtml(item.title)}</h4>
                  <p>${escapeHtml(item.subtitle)}</p>
                </div>
              </article>`;
            })
            .join("")}
        </div>
      </article>`;
    })
    .join("");
}

function renderCatalog() {
  if (!Array.isArray(state.catalog) || state.catalog.length === 0) {
    refs.catalogTableBody.innerHTML = '<tr><td colspan="5">No active plans found.</td></tr>';
    refs.checkoutPlanId.innerHTML = "";
    return;
  }

  refs.catalogTableBody.innerHTML = state.catalog
    .map((plan) => {
      return `<tr>
        <td>${escapeHtml(plan.display_name)}<br /><small>${escapeHtml(plan.plan_id)}</small></td>
        <td>${escapeHtml(plan.daily_credits)}</td>
        <td>${escapeHtml(plan.preview_cost_credits)}</td>
        <td>${escapeHtml(plan.final_cost_credits)}</td>
        <td>$${Number(plan.monthly_price_usd || 0).toFixed(2)}</td>
      </tr>`;
    })
    .join("");

  const selected = refs.checkoutPlanId.value;
  refs.checkoutPlanId.innerHTML = state.catalog
    .map((plan) => `<option value="${escapeHtml(plan.plan_id)}">${escapeHtml(plan.display_name)} (${escapeHtml(plan.plan_id)})</option>`)
    .join("");
  if (selected && state.catalog.some((plan) => plan.plan_id === selected)) {
    refs.checkoutPlanId.value = selected;
  }
}

function renderProfile() {
  if (!state.token || !state.profile) {
    refs.profileSummary.innerHTML = '<p class="muted">Login first to load profile and subscription data.</p>';
    return;
  }

  const entitlement = state.profile.entitlement || {};
  refs.profileSummary.innerHTML = `<div class="summary-grid">
    <article class="summary-metric">
      <p>User</p>
      <strong>${escapeHtml(state.profile.user_id || "-")}</strong>
    </article>
    <article class="summary-metric">
      <p>Credits</p>
      <strong>${escapeHtml(state.profile.credits?.balance || 0)}</strong>
    </article>
    <article class="summary-metric">
      <p>Plan</p>
      <strong>${escapeHtml(state.profile.effective_plan?.display_name || "-")}</strong>
    </article>
    <article class="summary-metric">
      <p>Entitlement Status</p>
      <strong>${escapeHtml(entitlement.status || "-")}</strong>
    </article>
    <article class="summary-metric">
      <p>Entitlement Source</p>
      <strong>${escapeHtml(entitlement.source || "-")}</strong>
    </article>
    <article class="summary-metric">
      <p>Next Credit Reset</p>
      <strong>${escapeHtml(state.profile.next_credit_reset_at ? new Date(state.profile.next_credit_reset_at).toLocaleString() : "-")}</strong>
    </article>
  </div>`;

  if (state.experimentAssignments.length > 0) {
    const assignmentMarkup = state.experimentAssignments
      .map(
        (item) =>
          `<li>${escapeHtml(item.experiment_id)} -> ${escapeHtml(item.variant_id)} (${item.from_cache ? "cached" : "new"})</li>`,
      )
      .join("");
    refs.profileSummary.innerHTML += `<div class="section-head"><h3>Active Experiments</h3></div><ul class="list">${assignmentMarkup}</ul>`;
  }
}

function renderAll() {
  renderStatusPills();
  renderTools();
  renderJobResult();
  renderDiscover();
  renderCatalog();
  renderProfile();
}

function stopPolling() {
  if (state.pollHandle) {
    clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function pollRenderJob(jobId) {
  const status = await apiRequest(`/v1/ai/render-jobs/${encodeURIComponent(jobId)}`, { authRequired: true });
  state.currentJob = status;
  renderJobResult();

  if (TERMINAL_JOB_STATUS.has(status.status)) {
    stopPolling();
    log(`Render job ${jobId} completed with status=${status.status}.`);
    await trackEvent("web_render_terminal", { status: status.status });
    await refreshAuthenticatedData();
    renderAll();
  }
}

function startPolling(jobId) {
  stopPolling();
  state.pollHandle = setInterval(() => {
    void pollRenderJob(jobId).catch((error) => {
      log(`Polling failed: ${error.message}`, "ERROR");
      stopPolling();
    });
  }, 2500);
}

async function loadDiscover(tab = "") {
  const query = tab ? `?tab=${encodeURIComponent(tab)}` : "";
  state.discoverFeed = await apiRequest(`/v1/discover/feed${query}`, { authRequired: false });
  state.discoverTab = tab;
}

async function loadCatalog() {
  state.catalog = await apiRequest("/v1/subscriptions/catalog", { authRequired: false });
}

async function refreshAuthenticatedData() {
  const bootstrap = await apiRequest("/v1/session/bootstrap/me?board_limit=30&experiment_limit=50", {
    authRequired: true,
  });

  state.me = bootstrap.me || null;
  if (state.me?.user_id && state.userId !== state.me.user_id) {
    state.userId = state.me.user_id;
    syncInputsFromState();
    saveSessionSettings();
    log(`Active session belongs to ${state.userId}.`);
  }
  state.profile = bootstrap.profile || null;
  state.board = bootstrap.board?.projects || [];
  state.experimentAssignments = bootstrap.experiments?.assignments || [];
  if (Array.isArray(bootstrap.catalog)) {
    state.catalog = bootstrap.catalog;
  }
}

async function refreshAllData() {
  readInputsToState();
  saveSessionSettings();

  await loadDiscover(state.discoverTab);

  if (state.token) {
    await refreshAuthenticatedData();
  } else {
    await loadCatalog();
    state.me = null;
    state.profile = null;
    state.board = [];
    state.experimentAssignments = [];
  }
}

async function syncAfterCheckoutReturn(checkoutState) {
  if (!state.token) {
    log(`Checkout returned with state=${checkoutState}, but no active session token was found.`, "ERROR");
    return;
  }

  const maxAttempts = checkoutState === "success" ? 5 : 1;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await refreshAllData();
      renderAll();
      const entitlementStatus = state.profile?.entitlement?.status || "-";
      const entitlementSource = state.profile?.entitlement?.source || "-";
      log(
        `Checkout ${checkoutState} sync ${attempt}/${maxAttempts}: entitlement=${entitlementStatus}, source=${entitlementSource}.`,
      );

      if (checkoutState !== "success" || entitlementStatus === "active") {
        return;
      }
    } catch (error) {
      log(`Checkout ${checkoutState} sync attempt ${attempt} failed: ${error.message}`, "ERROR");
    }

    if (attempt < maxAttempts) {
      await new Promise((resolve) => {
        window.setTimeout(resolve, 3000);
      });
    }
  }
}

async function handleLogin() {
  readInputsToState();
  if (!state.userId) {
    log("User ID is required.", "ERROR");
    return;
  }

  try {
    const response = await apiRequest("/v1/auth/login-dev", {
      method: "POST",
      authRequired: false,
      body: {
        user_id: state.userId,
        platform: "web",
        ttl_hours: 24 * 30,
      },
    });
    state.token = response.access_token;
    saveSessionSettings();
    await refreshAllData();
    renderAll();
    log(`Logged in as ${state.userId}.`);
    await trackEvent("web_login_success");
  } catch (error) {
    log(`Login failed: ${error.message}`, "ERROR");
  }
}

async function handleLogout() {
  try {
    if (state.token) {
      await apiRequest("/v1/auth/logout", { method: "POST", authRequired: true });
    }
  } catch (error) {
    log(`Logout warning: ${error.message}`, "ERROR");
  } finally {
    state.token = "";
    state.me = null;
    state.profile = null;
    state.board = [];
    state.experimentAssignments = [];
    state.currentJob = null;
    stopPolling();
    saveSessionSettings();
    renderAll();
    log("Logged out.");
  }
}

async function handleRenderSubmit(event) {
  event.preventDefault();
  readInputsToState();
  if (!state.token) {
    log("Login first to create render jobs.", "ERROR");
    return;
  }

  const selectedParts = Array.from(document.querySelectorAll('input[name="targetPart"]:checked')).map((input) => input.value);
  if (selectedParts.length === 0) {
    log("Select at least one target part.", "ERROR");
    return;
  }

  let promptOverrides = {};
  const rawOverrides = refs.promptOverrides.value.trim();
  if (rawOverrides) {
    try {
      promptOverrides = JSON.parse(rawOverrides);
    } catch (error) {
      log(`Prompt overrides JSON invalid: ${error.message}`, "ERROR");
      return;
    }
  }

  const imageUrl = refs.imageUrl.value.trim();
  const projectId = refs.projectId.value.trim() || `web_${Date.now()}`;
  refs.projectId.value = projectId;

  const payload = {
    user_id: state.userId,
    platform: "web",
    project_id: projectId,
    image_url: imageUrl,
    style_id: refs.styleId.value.trim(),
    operation: refs.operation.value,
    tier: refs.tier.value,
    target_parts: selectedParts,
    prompt_overrides: promptOverrides,
  };

  try {
    const job = await apiRequest("/v1/ai/render-jobs", {
      method: "POST",
      body: payload,
      authRequired: true,
    });
    state.currentJob = job;
    renderJobResult();
    if (!TERMINAL_JOB_STATUS.has(job.status)) {
      startPolling(job.id);
    }
    log(`Render job created: ${job.id}`);
    await trackEvent("web_render_submitted", {
      operation: payload.operation,
      status: job.status,
    });
  } catch (error) {
    log(`Render request failed: ${error.message}`, "ERROR");
  }
}

async function handleCheckoutSubmit(event) {
  event.preventDefault();
  if (!state.token) {
    log("Login first to start checkout.", "ERROR");
    return;
  }

  const planId = refs.checkoutPlanId.value;
  if (!planId) {
    log("Choose a plan for checkout.", "ERROR");
    return;
  }

  try {
    const session = await apiRequest("/v1/subscriptions/web/checkout-session", {
      method: "POST",
      authRequired: true,
      body: {
        user_id: state.userId,
        plan_id: planId,
        success_url: refs.successUrl.value.trim(),
        cancel_url: refs.cancelUrl.value.trim(),
      },
    });
    window.open(session.checkout_url, "_blank", "noopener,noreferrer");
    log(`Checkout session created: ${session.session_id}`);
    await trackEvent("checkout_started", {
      status: "in_progress",
    });
  } catch (error) {
    log(`Checkout failed: ${error.message}`, "ERROR");
  }
}

function handleToolPresetClick(event) {
  const trigger = event.target.closest("[data-tool-try]");
  if (!trigger) {
    return;
  }
  refs.styleId.value = trigger.dataset.style || refs.styleId.value;
  refs.operation.value = trigger.dataset.operation || refs.operation.value;
  refs.imageUrl.value = trigger.dataset.image || refs.imageUrl.value;
  setTab("create");
  log(`Preset applied: style=${refs.styleId.value}, operation=${refs.operation.value}`);
}

async function handleDiscoverTabClick(event) {
  const trigger = event.target.closest("[data-discover-tab]");
  if (!trigger) {
    return;
  }
  const tab = trigger.dataset.discoverTab || "";
  try {
    await loadDiscover(tab);
    renderDiscover();
    await trackEvent("discover_tab_changed");
  } catch (error) {
    log(`Discover refresh failed: ${error.message}`, "ERROR");
  }
}

function bindEvents() {
  document.getElementById("loginButton").addEventListener("click", () => {
    void handleLogin();
  });
  document.getElementById("logoutButton").addEventListener("click", () => {
    void handleLogout();
  });
  document.getElementById("refreshButton").addEventListener("click", () => {
    void refreshAllData()
      .then(() => {
        renderAll();
        log("Data refreshed.");
      })
      .catch((error) => {
        log(`Refresh failed: ${error.message}`, "ERROR");
      });
  });

  for (const button of refs.tabButtons) {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      if (!tab) {
        return;
      }
      setTab(tab);
      void trackEvent(`web_tab_opened_${tab}`);
    });
  }

  refs.toolsGrid.addEventListener("click", handleToolPresetClick);
  document.getElementById("renderForm").addEventListener("submit", (event) => {
    void handleRenderSubmit(event);
  });
  document.getElementById("checkoutForm").addEventListener("submit", (event) => {
    void handleCheckoutSubmit(event);
  });
  refs.discoverTabs.addEventListener("click", (event) => {
    void handleDiscoverTabClick(event);
  });

  document.getElementById("loadDemoImage").addEventListener("click", () => {
    refs.imageUrl.value = "https://picsum.photos/id/1068/1280/960";
    if (!refs.projectId.value.trim()) {
      refs.projectId.value = `web_${Date.now()}`;
    }
    log("Loaded demo image into Create form.");
  });
}

async function bootstrap() {
  loadSessionSettings();
  setDefaultCheckoutUrls();
  bindEvents();
  setTab(state.currentTab);
  renderTools();
  renderJobResult();

  const checkoutState = new URLSearchParams(window.location.search).get("checkout");
  if (checkoutState === "success") {
    log("Checkout returned with success URL. Syncing entitlement...");
    await syncAfterCheckoutReturn(checkoutState);
  } else if (checkoutState === "cancel") {
    log("Checkout returned with cancel URL.");
    await syncAfterCheckoutReturn(checkoutState);
  }

  try {
    await loadCatalog();
    await loadDiscover("");
  } catch (error) {
    log(`Failed to load public data: ${error.message}`, "ERROR");
  }

  if (state.token) {
    try {
      await refreshAuthenticatedData();
    } catch (error) {
      state.token = "";
      state.me = null;
      state.profile = null;
      state.board = [];
      saveSessionSettings();
      log(`Saved session expired. Please login again (${error.message}).`, "ERROR");
    }
  }

  renderAll();
}

void bootstrap();
