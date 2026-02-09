const STORAGE_KEY = "homeai-admin-connection-v1";

const defaults = {
  apiBaseUrl: "http://localhost:8000",
  authToken: "",
  adminApiToken: "",
  adminActor: "dashboard",
  actionReason: "manual_update",
};

const OPERATION_KEYS = ["restyle", "replace", "remove", "repaint"];
const PART_KEYS = ["full_room", "walls", "floor", "furniture", "decor"];
const INITIAL_PROVIDERS = ["fal", "openai", "mock"];
const DEFAULT_PROVIDER_SETTINGS = {
  default_provider: "fal",
  enabled_providers: ["fal", "openai"],
  fallback_chain: ["fal", "openai"],
  operation_routes: {
    restyle: { preview_provider: "fal", final_provider: "fal" },
    replace: { preview_provider: "fal", final_provider: "fal" },
    remove: { preview_provider: "fal", final_provider: "fal" },
    repaint: { preview_provider: "fal", final_provider: "fal" },
  },
  part_routes: {
    full_room: { preview_provider: "fal", final_provider: "fal" },
    walls: { preview_provider: "fal", final_provider: "fal" },
    floor: { preview_provider: "fal", final_provider: "fal" },
    furniture: { preview_provider: "fal", final_provider: "fal" },
    decor: { preview_provider: "fal", final_provider: "fal" },
  },
  provider_models: {
    fal: { preview_model: "fal-ai/flux-1/schnell", final_model: "fal-ai/flux-pro/kontext" },
    openai: { preview_model: "gpt-image-1-mini", final_model: "gpt-image-1" },
    mock: { preview_model: "mock-preview", final_model: "mock-final" },
  },
  cost_controls: {
    max_retries: 1,
    max_output_megapixels: 1.2,
    preview_required_before_final: true,
  },
};

let providerSettingsSnapshot = null;
let providerOptions = [...INITIAL_PROVIDERS];
let experimentTemplates = [];

const refs = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  authToken: document.getElementById("authToken"),
  adminApiToken: document.getElementById("adminApiToken"),
  adminActor: document.getElementById("adminActor"),
  actionReason: document.getElementById("actionReason"),
  connectionState: document.getElementById("connectionState"),
  lastSyncValue: document.getElementById("lastSyncValue"),
  providerJsonEditor: document.getElementById("providerJsonEditor"),
  providerSourceLabel: document.getElementById("providerSourceLabel"),
  versionsList: document.getElementById("versionsList"),
  auditList: document.getElementById("auditList"),
  productAuditList: document.getElementById("productAuditList"),
  experimentsTableBody: document.getElementById("experimentsTableBody"),
  experimentTemplateSelect: document.getElementById("experimentTemplateSelect"),
  experimentAuditList: document.getElementById("experimentAuditList"),
  experimentAutomationHistoryList: document.getElementById("experimentAutomationHistoryList"),
  experimentGuardrailHours: document.getElementById("experimentGuardrailHours"),
  experimentGuardrailDryRun: document.getElementById("experimentGuardrailDryRun"),
  experimentGuardrailResult: document.getElementById("experimentGuardrailResult"),
  experimentPerformanceId: document.getElementById("experimentPerformanceId"),
  experimentPerformanceHours: document.getElementById("experimentPerformanceHours"),
  experimentPerformanceTableBody: document.getElementById("experimentPerformanceTableBody"),
  experimentPerformanceSummary: document.getElementById("experimentPerformanceSummary"),
  experimentTrendId: document.getElementById("experimentTrendId"),
  experimentTrendHours: document.getElementById("experimentTrendHours"),
  experimentTrendBucketHours: document.getElementById("experimentTrendBucketHours"),
  experimentTrendTableBody: document.getElementById("experimentTrendTableBody"),
  experimentTrendSummary: document.getElementById("experimentTrendSummary"),
  experimentTrendChart: document.getElementById("experimentTrendChart"),
  experimentRolloutId: document.getElementById("experimentRolloutId"),
  experimentRolloutHours: document.getElementById("experimentRolloutHours"),
  experimentRolloutDryRun: document.getElementById("experimentRolloutDryRun"),
  experimentRolloutLimit: document.getElementById("experimentRolloutLimit"),
  experimentRolloutResult: document.getElementById("experimentRolloutResult"),
  experimentAutomationHours: document.getElementById("experimentAutomationHours"),
  experimentAutomationDryRun: document.getElementById("experimentAutomationDryRun"),
  experimentAutomationLimit: document.getElementById("experimentAutomationLimit"),
  experimentAutomationResult: document.getElementById("experimentAutomationResult"),
  plansTableBody: document.getElementById("plansTableBody"),
  variablesTableBody: document.getElementById("variablesTableBody"),
  providerHealthTableBody: document.getElementById("providerHealthTableBody"),
  analyticsProviderTableBody: document.getElementById("analyticsProviderTableBody"),
  analyticsOperationTableBody: document.getElementById("analyticsOperationTableBody"),
  analyticsPlatformTableBody: document.getElementById("analyticsPlatformTableBody"),
  analyticsSubscriptionSourceTableBody: document.getElementById("analyticsSubscriptionSourceTableBody"),
  analyticsExperimentTableBody: document.getElementById("analyticsExperimentTableBody"),
  analyticsStatusList: document.getElementById("analyticsStatusList"),
  analyticsAlertsList: document.getElementById("analyticsAlertsList"),
  analyticsWindowHours: document.getElementById("analyticsWindowHours"),
  metricTotalEvents: document.getElementById("metricTotalEvents"),
  metricRenderSuccessRate: document.getElementById("metricRenderSuccessRate"),
  metricAvgLatency: document.getElementById("metricAvgLatency"),
  metricP95Latency: document.getElementById("metricP95Latency"),
  metricTotalCost: document.getElementById("metricTotalCost"),
  metricRenderSuccessCount: document.getElementById("metricRenderSuccessCount"),
  metricRenderFailedCount: document.getElementById("metricRenderFailedCount"),
  metricAvgCostPerRender: document.getElementById("metricAvgCostPerRender"),
  metricPreviewToFinal: document.getElementById("metricPreviewToFinal"),
  metricActiveUsers: document.getElementById("metricActiveUsers"),
  metricCheckoutStarts: document.getElementById("metricCheckoutStarts"),
  metricPaidActivations: document.getElementById("metricPaidActivations"),
  metricCheckoutToPaidRate: document.getElementById("metricCheckoutToPaidRate"),
  metricCreditsConsumed: document.getElementById("metricCreditsConsumed"),
  metricCreditsGranted: document.getElementById("metricCreditsGranted"),
  metricCreditsRefunded: document.getElementById("metricCreditsRefunded"),
  metricCreditsDailyReset: document.getElementById("metricCreditsDailyReset"),
  metricCreditsConsumers: document.getElementById("metricCreditsConsumers"),
  metricSubscriptionsActive: document.getElementById("metricSubscriptionsActive"),
  metricSubscriptionsRenewals7d: document.getElementById("metricSubscriptionsRenewals7d"),
  metricSubscriptionsExpiring7d: document.getElementById("metricSubscriptionsExpiring7d"),
  metricQueueQueued: document.getElementById("metricQueueQueued"),
  metricQueueInProgress: document.getElementById("metricQueueInProgress"),
  metricQueueCompletedWindow: document.getElementById("metricQueueCompletedWindow"),
  metricQueueFailedWindow: document.getElementById("metricQueueFailedWindow"),
  metricQueueCanceledWindow: document.getElementById("metricQueueCanceledWindow"),
  metricFunnelLoginUsers: document.getElementById("metricFunnelLoginUsers"),
  metricFunnelPreviewUsers: document.getElementById("metricFunnelPreviewUsers"),
  metricFunnelFinalUsers: document.getElementById("metricFunnelFinalUsers"),
  metricFunnelCheckoutStarts: document.getElementById("metricFunnelCheckoutStarts"),
  metricFunnelPaidActivations: document.getElementById("metricFunnelPaidActivations"),
  creditResetForm: document.getElementById("creditResetForm"),
  creditResetEnabled: document.getElementById("creditResetEnabled"),
  creditResetHour: document.getElementById("creditResetHour"),
  creditResetMinute: document.getElementById("creditResetMinute"),
  creditResetFreeCredits: document.getElementById("creditResetFreeCredits"),
  creditResetProCredits: document.getElementById("creditResetProCredits"),
  creditResetLastRun: document.getElementById("creditResetLastRun"),
  creditResetNextRun: document.getElementById("creditResetNextRun"),
  creditResetResult: document.getElementById("creditResetResult"),
  defaultProviderSelect: document.getElementById("defaultProviderSelect"),
  fallbackChainInput: document.getElementById("fallbackChainInput"),
  enabledProvidersCheckboxes: document.getElementById("enabledProvidersCheckboxes"),
  operationRoutesTableBody: document.getElementById("operationRoutesTableBody"),
  partRoutesTableBody: document.getElementById("partRoutesTableBody"),
  providerModelsTableBody: document.getElementById("providerModelsTableBody"),
  costMaxRetries: document.getElementById("costMaxRetries"),
  costMaxMegapixels: document.getElementById("costMaxMegapixels"),
  costPreviewRequired: document.getElementById("costPreviewRequired"),
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

function normalizeBaseUrl(rawValue) {
  return rawValue.trim().replace(/\/+$/, "");
}

function getConnectionValues() {
  return {
    apiBaseUrl: normalizeBaseUrl(refs.apiBaseUrl.value),
    authToken: refs.authToken.value.trim(),
    adminApiToken: refs.adminApiToken.value.trim(),
    adminActor: refs.adminActor.value.trim() || defaults.adminActor,
    actionReason: refs.actionReason.value.trim() || defaults.actionReason,
  };
}

function saveConnectionValues() {
  const values = getConnectionValues();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
  log(`Saved API settings for ${values.apiBaseUrl || "(empty url)"}`);
}

function loadConnectionValues() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) {
    refs.apiBaseUrl.value = defaults.apiBaseUrl;
    refs.authToken.value = defaults.authToken;
    refs.adminApiToken.value = defaults.adminApiToken;
    refs.adminActor.value = defaults.adminActor;
    refs.actionReason.value = defaults.actionReason;
    return;
  }

  try {
    const values = JSON.parse(saved);
    refs.apiBaseUrl.value = values.apiBaseUrl || defaults.apiBaseUrl;
    refs.authToken.value = values.authToken || defaults.authToken;
    refs.adminApiToken.value = values.adminApiToken || defaults.adminApiToken;
    refs.adminActor.value = values.adminActor || defaults.adminActor;
    refs.actionReason.value = values.actionReason || defaults.actionReason;
  } catch (error) {
    log(`Failed to parse saved settings: ${error.message}`, "ERROR");
  }
}

function log(message, level = "INFO") {
  const timestamp = new Date().toLocaleTimeString();
  const current = refs.activityLog.textContent || "";
  const line = `[${timestamp}] [${level}] ${message}`;
  refs.activityLog.textContent = current === "Waiting for actions..." ? line : `${line}\n${current}`;
}

function setConnectionBadge(status, tone = "muted") {
  refs.connectionState.textContent = `Connection: ${status}`;
  refs.connectionState.className = `badge badge-${tone}`;
}

function setLastSync() {
  refs.lastSyncValue.textContent = new Date().toLocaleString();
}

function actorReasonQuery() {
  const values = getConnectionValues();
  const params = new URLSearchParams({ actor: values.adminActor });
  if (values.actionReason) {
    params.set("reason", values.actionReason);
  }
  return params.toString();
}

async function apiRequest(path, options = {}) {
  const values = getConnectionValues();
  if (!values.apiBaseUrl) {
    throw new Error("API Base URL is required.");
  }

  const url = `${values.apiBaseUrl}${path}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (values.authToken) {
    headers.Authorization = `Bearer ${values.authToken}`;
  }
  if (values.adminApiToken) {
    headers["X-Admin-Token"] = values.adminApiToken;
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null ? payload.detail || JSON.stringify(payload) : payload;
    throw new Error(`${response.status} ${response.statusText} - ${detail}`);
  }

  return payload;
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function parseProviderSettingsFromEditor() {
  try {
    return JSON.parse(refs.providerJsonEditor.value || "{}");
  } catch (error) {
    throw new Error(`Provider JSON is invalid: ${error.message}`);
  }
}

function normalizeProviderSettings(settings = {}) {
  const merged = {
    ...DEFAULT_PROVIDER_SETTINGS,
    ...settings,
    operation_routes: {
      ...DEFAULT_PROVIDER_SETTINGS.operation_routes,
      ...(settings.operation_routes || {}),
    },
    part_routes: {
      ...DEFAULT_PROVIDER_SETTINGS.part_routes,
      ...(settings.part_routes || {}),
    },
    provider_models: {
      ...DEFAULT_PROVIDER_SETTINGS.provider_models,
      ...(settings.provider_models || {}),
    },
    cost_controls: {
      ...DEFAULT_PROVIDER_SETTINGS.cost_controls,
      ...(settings.cost_controls || {}),
    },
  };
  if (!Array.isArray(merged.enabled_providers)) {
    merged.enabled_providers = [...DEFAULT_PROVIDER_SETTINGS.enabled_providers];
  }
  if (!Array.isArray(merged.fallback_chain)) {
    merged.fallback_chain = [...DEFAULT_PROVIDER_SETTINGS.fallback_chain];
  }
  return merged;
}

function updateProviderOptions(settings) {
  const candidates = [...INITIAL_PROVIDERS];
  candidates.push(settings.default_provider);
  candidates.push(...(settings.enabled_providers || []));
  candidates.push(...(settings.fallback_chain || []));
  candidates.push(...Object.keys(settings.provider_models || {}));

  for (const operation of OPERATION_KEYS) {
    const rule = settings.operation_routes?.[operation];
    if (rule) {
      candidates.push(rule.preview_provider);
      candidates.push(rule.final_provider);
    }
  }
  for (const part of PART_KEYS) {
    const rule = settings.part_routes?.[part];
    if (rule) {
      candidates.push(rule.preview_provider);
      candidates.push(rule.final_provider);
    }
  }

  providerOptions = uniqueSorted(candidates.map((item) => String(item).trim()));
}

function providerOptionMarkup(selected) {
  return providerOptions
    .map((provider) => {
      const option = escapeHtml(provider);
      const isSelected = selected === provider ? "selected" : "";
      return `<option value="${option}" ${isSelected}>${option}</option>`;
    })
    .join("");
}

function setProviderControls(settings) {
  const normalizedSettings = normalizeProviderSettings(settings);
  providerSettingsSnapshot = JSON.parse(JSON.stringify(normalizedSettings));

  updateProviderOptions(normalizedSettings);

  refs.defaultProviderSelect.innerHTML = providerOptionMarkup(normalizedSettings.default_provider);
  refs.fallbackChainInput.value = (normalizedSettings.fallback_chain || []).join(",");

  refs.enabledProvidersCheckboxes.innerHTML = providerOptions
    .map((provider) => {
      const checked = (normalizedSettings.enabled_providers || []).includes(provider) ? "checked" : "";
      const safeProvider = escapeHtml(provider);
      return `<label><input type="checkbox" data-enabled-provider="${safeProvider}" ${checked} />${safeProvider}</label>`;
    })
    .join("");

  refs.operationRoutesTableBody.innerHTML = OPERATION_KEYS
    .map((operation) => {
      const rule = normalizedSettings.operation_routes?.[operation] || {};
      return `<tr>
        <td>${escapeHtml(operation)}</td>
        <td>
          <select data-route-scope="operation" data-route-tier="preview" data-route-key="${escapeHtml(operation)}">
            ${providerOptionMarkup(rule.preview_provider || normalizedSettings.default_provider)}
          </select>
        </td>
        <td>
          <select data-route-scope="operation" data-route-tier="final" data-route-key="${escapeHtml(operation)}">
            ${providerOptionMarkup(rule.final_provider || normalizedSettings.default_provider)}
          </select>
        </td>
      </tr>`;
    })
    .join("");

  refs.partRoutesTableBody.innerHTML = PART_KEYS
    .map((part) => {
      const rule = normalizedSettings.part_routes?.[part] || {};
      return `<tr>
        <td>${escapeHtml(part)}</td>
        <td>
          <select data-route-scope="part" data-route-tier="preview" data-route-key="${escapeHtml(part)}">
            ${providerOptionMarkup(rule.preview_provider || normalizedSettings.default_provider)}
          </select>
        </td>
        <td>
          <select data-route-scope="part" data-route-tier="final" data-route-key="${escapeHtml(part)}">
            ${providerOptionMarkup(rule.final_provider || normalizedSettings.default_provider)}
          </select>
        </td>
      </tr>`;
    })
    .join("");

  refs.providerModelsTableBody.innerHTML = providerOptions
    .map((provider) => {
      const modelInfo = normalizedSettings.provider_models?.[provider] || {};
      const previewModel = escapeHtml(modelInfo.preview_model || "");
      const finalModel = escapeHtml(modelInfo.final_model || "");
      const safeProvider = escapeHtml(provider);
      return `<tr>
        <td>${safeProvider}</td>
        <td><input type="text" data-provider-model-provider="${safeProvider}" data-provider-model-tier="preview" value="${previewModel}" placeholder="${safeProvider}-preview-model" /></td>
        <td><input type="text" data-provider-model-provider="${safeProvider}" data-provider-model-tier="final" value="${finalModel}" placeholder="${safeProvider}-final-model" /></td>
      </tr>`;
    })
    .join("");

  refs.costMaxRetries.value = String(normalizedSettings.cost_controls?.max_retries ?? 1);
  refs.costMaxMegapixels.value = String(normalizedSettings.cost_controls?.max_output_megapixels ?? 1.2);
  refs.costPreviewRequired.checked = Boolean(normalizedSettings.cost_controls?.preview_required_before_final ?? true);
}

function getSelectedEnabledProviders() {
  const checked = Array.from(
    refs.enabledProvidersCheckboxes.querySelectorAll("input[data-enabled-provider]:checked")
  ).map((element) => element.getAttribute("data-enabled-provider") || "");
  return uniqueSorted(checked);
}

function getRouteMap(scope, fallbackProvider) {
  const result = {};
  const keys = scope === "operation" ? OPERATION_KEYS : PART_KEYS;
  for (const key of keys) {
    const preview = document.querySelector(
      `select[data-route-scope="${scope}"][data-route-tier="preview"][data-route-key="${key}"]`
    );
    const final = document.querySelector(
      `select[data-route-scope="${scope}"][data-route-tier="final"][data-route-key="${key}"]`
    );
    result[key] = {
      preview_provider: preview?.value || fallbackProvider,
      final_provider: final?.value || fallbackProvider,
    };
  }
  return result;
}

function getProviderModels(baseProviderModels = {}) {
  const models = {};
  for (const provider of providerOptions) {
    const previewInput = document.querySelector(
      `input[data-provider-model-provider="${provider}"][data-provider-model-tier="preview"]`
    );
    const finalInput = document.querySelector(
      `input[data-provider-model-provider="${provider}"][data-provider-model-tier="final"]`
    );

    const fallback = baseProviderModels?.[provider] || {};
    models[provider] = {
      preview_model: previewInput?.value.trim() || fallback.preview_model || `${provider}-preview`,
      final_model: finalInput?.value.trim() || fallback.final_model || `${provider}-final`,
    };
  }
  return models;
}

function buildProviderSettingsFromControls(baseSettings) {
  let enabledProviders = getSelectedEnabledProviders();
  const selectedDefault = refs.defaultProviderSelect.value || baseSettings.default_provider || "fal";

  if (!enabledProviders.includes(selectedDefault)) {
    enabledProviders = uniqueSorted([...enabledProviders, selectedDefault]);
  }
  if (enabledProviders.length === 0) {
    enabledProviders = [selectedDefault];
  }

  const fallbackChainInput = refs.fallbackChainInput.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const fallbackChain = fallbackChainInput.filter((provider) => enabledProviders.includes(provider));
  const normalizedFallback = fallbackChain.length > 0 ? fallbackChain : [selectedDefault];

  return {
    ...baseSettings,
    default_provider: selectedDefault,
    enabled_providers: enabledProviders,
    fallback_chain: normalizedFallback,
    operation_routes: getRouteMap("operation", selectedDefault),
    part_routes: getRouteMap("part", selectedDefault),
    provider_models: getProviderModels(baseSettings.provider_models || {}),
    cost_controls: {
      max_retries: Number(refs.costMaxRetries.value || 1),
      max_output_megapixels: Number(refs.costMaxMegapixels.value || 1.2),
      preview_required_before_final: refs.costPreviewRequired.checked,
    },
  };
}

function formatLatency(value) {
  return value == null ? "-" : `${Number(value).toFixed(0)}ms`;
}

function formatPercent(value) {
  return value == null ? "-" : `${Number(value).toFixed(1)}%`;
}

function formatPValue(value) {
  return value == null ? "-" : Number(value).toFixed(4);
}

function formatUsd(value) {
  return value == null ? "-" : `$${Number(value).toFixed(2)}`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

function renderVersions(items) {
  if (!Array.isArray(items) || items.length === 0) {
    refs.versionsList.innerHTML = "<li>No versions available.</li>";
    return;
  }

  refs.versionsList.innerHTML = items
    .map((item) => {
      const created = new Date(item.created_at).toLocaleString();
      const reason = item.reason ? ` - ${escapeHtml(item.reason)}` : "";
      return `<li><strong>v${item.version}</strong> by ${escapeHtml(item.actor)} on ${created}${reason}</li>`;
    })
    .join("");
}

function renderAudit(items) {
  if (!Array.isArray(items) || items.length === 0) {
    refs.auditList.innerHTML = "<li>No audit records.</li>";
    return;
  }

  refs.auditList.innerHTML = items
    .map((item) => {
      const created = new Date(item.created_at).toLocaleString();
      const reason = item.reason ? ` - ${escapeHtml(item.reason)}` : "";
      return `<li>${escapeHtml(item.action)} by ${escapeHtml(item.actor)} on ${created}${reason}</li>`;
    })
    .join("");
}

function renderProductAudit(items) {
  if (!Array.isArray(items) || items.length === 0) {
    refs.productAuditList.innerHTML = "<li>No product audit records.</li>";
    return;
  }

  refs.productAuditList.innerHTML = items
    .map((item) => {
      const created = new Date(item.created_at).toLocaleString();
      const reason = item.reason ? ` - ${escapeHtml(item.reason)}` : "";
      return `<li>${escapeHtml(item.action)} by ${escapeHtml(item.actor)} on ${created}${reason}</li>`;
    })
    .join("");
}

function renderPlans(plans) {
  if (!Array.isArray(plans) || plans.length === 0) {
    refs.plansTableBody.innerHTML = '<tr><td colspan="6">No plans found.</td></tr>';
    return;
  }

  refs.plansTableBody.innerHTML = plans
    .map(
      (plan) => `<tr>
          <td><strong>${escapeHtml(plan.plan_id)}</strong><br />${escapeHtml(plan.display_name)}</td>
          <td>${plan.daily_credits}</td>
          <td>${plan.preview_cost_credits}</td>
          <td>${plan.final_cost_credits}</td>
          <td>
            $${Number(plan.monthly_price_usd).toFixed(2)}
            <br />
            <small>iOS:${escapeHtml(plan.ios_product_id || "-")} | Android:${escapeHtml(plan.android_product_id || "-")} | Web:${escapeHtml(plan.web_product_id || "-")}</small>
          </td>
          <td>${plan.is_active ? "yes" : "no"}</td>
        </tr>`,
    )
    .join("");
}

function renderExperiments(experiments) {
  if (!Array.isArray(experiments) || experiments.length === 0) {
    refs.experimentsTableBody.innerHTML = '<tr><td colspan="5">No experiments found.</td></tr>';
    return;
  }

  refs.experimentsTableBody.innerHTML = experiments
    .map((experiment) => {
      const variants = Array.isArray(experiment.variants) ? experiment.variants : [];
      const variantSummary = variants.map((item) => `${item.variant_id}(${item.weight})`).join(", ");
      return `<tr>
        <td><strong>${escapeHtml(experiment.experiment_id)}</strong></td>
        <td>${escapeHtml(experiment.name || "-")}<br /><small>${escapeHtml(experiment.description || "")}</small></td>
        <td>${escapeHtml(experiment.primary_metric || "-")}</td>
        <td>${escapeHtml(variantSummary || "-")}</td>
        <td>${experiment.is_active ? "yes" : "no"}</td>
      </tr>`;
    })
    .join("");
}

function renderExperimentTemplates(templates) {
  experimentTemplates = Array.isArray(templates) ? templates : [];
  const current = refs.experimentTemplateSelect.value;
  const options = ['<option value="">Select template...</option>'];
  for (const template of experimentTemplates) {
    const selected = current === template.template_id ? "selected" : "";
    options.push(
      `<option value="${escapeHtml(template.template_id)}" ${selected}>${escapeHtml(template.name || template.template_id)}</option>`,
    );
  }
  refs.experimentTemplateSelect.innerHTML = options.join("");
}

function renderExperimentAudit(items) {
  if (!Array.isArray(items) || items.length === 0) {
    refs.experimentAuditList.innerHTML = "<li>No experiment audit records.</li>";
    return;
  }

  refs.experimentAuditList.innerHTML = items
    .map((item) => {
      const created = new Date(item.created_at).toLocaleString();
      const reason = item.reason ? ` - ${escapeHtml(item.reason)}` : "";
      return `<li>${escapeHtml(item.action)} by ${escapeHtml(item.actor)} on ${created}${reason}</li>`;
    })
    .join("");
}

function renderVariables(variables) {
  if (!Array.isArray(variables) || variables.length === 0) {
    refs.variablesTableBody.innerHTML = '<tr><td colspan="3">No variables found.</td></tr>';
    return;
  }

  refs.variablesTableBody.innerHTML = variables
    .map(
      (item) => `<tr>
          <td><strong>${escapeHtml(item.key)}</strong></td>
          <td><code>${escapeHtml(JSON.stringify(item.value))}</code></td>
          <td>${escapeHtml(item.description || "")}</td>
        </tr>`,
    )
    .join("");
}

function renderProviderHealth(health) {
  const entries = Object.entries(health || {});
  if (entries.length === 0) {
    refs.providerHealthTableBody.innerHTML = '<tr><td colspan="6">No provider health data.</td></tr>';
    return;
  }

  refs.providerHealthTableBody.innerHTML = entries
    .map(([provider, metrics]) => {
      const successRate = Number(metrics.success_rate || 0);
      return `<tr>
          <td>${escapeHtml(provider)}</td>
          <td>${Number(metrics.total_events || 0)}</td>
          <td>${successRate.toFixed(1)}%</td>
          <td>${Number(metrics.failed_events || 0)}</td>
          <td>${Number(metrics.avg_latency_ms || 0).toFixed(0)}</td>
          <td>${Number(metrics.health_score || 0).toFixed(1)}</td>
        </tr>`;
    })
    .join("");
}

function renderAnalytics(dashboard) {
  const summary = dashboard.summary || {};
  const credits = dashboard.credits || {};
  const subscriptions = dashboard.subscriptions || {};
  const funnel = dashboard.funnel || {};
  const queue = dashboard.queue || {};

  refs.metricTotalEvents.textContent = String(summary.total_events ?? 0);
  refs.metricRenderSuccessRate.textContent = formatPercent(summary.render_success_rate ?? 0);
  refs.metricAvgLatency.textContent = formatLatency(summary.avg_latency_ms);
  refs.metricP95Latency.textContent = formatLatency(summary.p95_latency_ms);
  refs.metricTotalCost.textContent = formatUsd(summary.total_cost_usd ?? 0);
  refs.metricRenderSuccessCount.textContent = String(summary.render_success ?? 0);
  refs.metricRenderFailedCount.textContent = String(summary.render_failed ?? 0);
  refs.metricAvgCostPerRender.textContent = formatUsd(summary.avg_cost_per_render_usd);
  refs.metricPreviewToFinal.textContent = formatPercent(summary.preview_to_final_rate ?? 0);
  refs.metricActiveUsers.textContent = String(summary.active_render_users ?? 0);
  refs.metricCheckoutStarts.textContent = String(funnel.checkout_starts ?? 0);
  refs.metricPaidActivations.textContent = String(funnel.paid_activations ?? 0);
  refs.metricCheckoutToPaidRate.textContent = formatPercent(funnel.checkout_to_paid_rate ?? 0);

  refs.metricCreditsConsumed.textContent = String(credits.consumed_total ?? 0);
  refs.metricCreditsGranted.textContent = String(credits.granted_total ?? 0);
  refs.metricCreditsRefunded.textContent = String(credits.refunded_total ?? 0);
  refs.metricCreditsDailyReset.textContent = String(credits.daily_reset_total ?? 0);
  refs.metricCreditsConsumers.textContent = String(credits.unique_consumers ?? 0);

  refs.metricSubscriptionsActive.textContent = String(subscriptions.active_subscriptions ?? 0);
  refs.metricSubscriptionsRenewals7d.textContent = String(subscriptions.renewals_due_7d ?? 0);
  refs.metricSubscriptionsExpiring7d.textContent = String(subscriptions.expirations_due_7d ?? 0);

  refs.metricQueueQueued.textContent = String(queue.queued_jobs ?? 0);
  refs.metricQueueInProgress.textContent = String(queue.in_progress_jobs ?? 0);
  refs.metricQueueCompletedWindow.textContent = String(queue.completed_jobs_window ?? 0);
  refs.metricQueueFailedWindow.textContent = String(queue.failed_jobs_window ?? 0);
  refs.metricQueueCanceledWindow.textContent = String(queue.canceled_jobs_window ?? 0);

  refs.metricFunnelLoginUsers.textContent = String(funnel.login_users ?? 0);
  refs.metricFunnelPreviewUsers.textContent = String(funnel.preview_users ?? 0);
  refs.metricFunnelFinalUsers.textContent = String(funnel.final_users ?? 0);
  refs.metricFunnelCheckoutStarts.textContent = String(funnel.checkout_starts ?? 0);
  refs.metricFunnelPaidActivations.textContent = String(funnel.paid_activations ?? 0);

  const providerRows = dashboard.provider_breakdown || [];
  refs.analyticsProviderTableBody.innerHTML =
    providerRows.length === 0
      ? '<tr><td colspan="5">No analytics provider data.</td></tr>'
      : providerRows
          .map(
            (row) => `<tr>
      <td>${escapeHtml(row.provider)}</td>
      <td>${Number(row.total_events || 0)}</td>
      <td>${formatPercent(row.success_rate || 0)}</td>
      <td>${formatLatency(row.p95_latency_ms)}</td>
      <td>${formatUsd(row.total_cost_usd || 0)}</td>
    </tr>`
          )
          .join("");

  const operationRows = dashboard.operation_breakdown || [];
  refs.analyticsOperationTableBody.innerHTML =
    operationRows.length === 0
      ? '<tr><td colspan="5">No operation analytics data.</td></tr>'
      : operationRows
          .map(
            (row) => `<tr>
      <td>${escapeHtml(row.operation)}</td>
      <td>${Number(row.total_events || 0)}</td>
      <td>${formatPercent(row.success_rate || 0)}</td>
      <td>${formatLatency(row.avg_latency_ms)}</td>
      <td>${formatUsd(row.avg_cost_usd)}</td>
    </tr>`
          )
          .join("");

  const platformRows = dashboard.platform_breakdown || [];
  refs.analyticsPlatformTableBody.innerHTML =
    platformRows.length === 0
      ? '<tr><td colspan="4">No platform analytics data.</td></tr>'
      : platformRows
          .map(
            (row) => `<tr>
      <td>${escapeHtml(row.platform)}</td>
      <td>${Number(row.total_events || 0)}</td>
      <td>${Number(row.render_events || 0)}</td>
      <td>${formatPercent(row.render_success_rate || 0)}</td>
    </tr>`
          )
          .join("");

  const sourceRows = dashboard.subscription_sources || [];
  refs.analyticsSubscriptionSourceTableBody.innerHTML =
    sourceRows.length === 0
      ? '<tr><td colspan="3">No subscription source data.</td></tr>'
      : sourceRows
          .map(
            (row) => `<tr>
      <td>${escapeHtml(row.source)}</td>
      <td>${Number(row.active_subscriptions || 0)}</td>
      <td>${formatPercent(row.active_share_pct || 0)}</td>
    </tr>`
          )
          .join("");

  const experimentRows = dashboard.experiment_breakdown || [];
  refs.analyticsExperimentTableBody.innerHTML =
    experimentRows.length === 0
      ? '<tr><td colspan="6">No experiment performance data.</td></tr>'
      : experimentRows
          .map((row) => {
            const variantSummary = (row.variants || [])
              .map(
                (variant) =>
                  `${escapeHtml(variant.variant_id)}: ${variant.active_paid_users}/${variant.assigned_users} (${formatPercent(
                    variant.paid_conversion_rate || 0
                  )})`,
              )
              .join("<br />");
            return `<tr>
      <td>${escapeHtml(row.name || row.experiment_id)}<br /><small>${escapeHtml(row.experiment_id)}</small></td>
      <td>${escapeHtml(row.primary_metric || "-")}<br /><small>${row.is_active ? "active" : "inactive"}</small></td>
      <td>${Number(row.total_assigned_users || 0)}</td>
      <td>${Number(row.active_paid_users || 0)}</td>
      <td>${formatPercent(row.paid_conversion_rate || 0)}</td>
      <td>${variantSummary || "-"}</td>
    </tr>`;
          })
          .join("");

  const statusRows = dashboard.status_breakdown || [];
  refs.analyticsStatusList.innerHTML =
    statusRows.length === 0
      ? "<li>No status distribution.</li>"
      : statusRows
          .map((row) => `<li>${escapeHtml(row.status)}: ${Number(row.count || 0)}</li>`)
          .join("");

  const alerts = dashboard.alerts || [];
  refs.analyticsAlertsList.innerHTML =
    alerts.length === 0
      ? "<li>No active alerts.</li>"
      : alerts
          .map((alert) => {
            const valuePart = alert.current_value != null ? ` | current=${escapeHtml(alert.current_value)}` : "";
            const thresholdPart = alert.threshold != null ? ` | threshold=${escapeHtml(alert.threshold)}` : "";
            return `<li><strong>${escapeHtml(alert.severity.toUpperCase())}</strong> ${escapeHtml(alert.message)}${valuePart}${thresholdPart}</li>`;
          })
          .join("");
}

function renderExperimentAutomationHistory(items) {
  if (!Array.isArray(items) || items.length === 0) {
    refs.experimentAutomationHistoryList.innerHTML = "<li>No automation runs recorded.</li>";
    return;
  }
  refs.experimentAutomationHistoryList.innerHTML = items
    .map((item) => {
      const created = new Date(item.created_at).toLocaleString();
      const metadata = item.metadata || {};
      const guardrails = metadata.guardrails || {};
      const rollouts = metadata.rollouts || {};
      return `<li>${created} | actor=${escapeHtml(item.actor || "-")} | breached=${Number(
        guardrails.breached_count || 0,
      )}, paused=${Number(guardrails.paused_count || 0)}, applied=${Number(
        rollouts.applied_count || 0,
      )}, blocked=${Number(rollouts.blocked_count || 0)}</li>`;
    })
    .join("");
}

function setProviderEditor(settings, source) {
  providerSettingsSnapshot = JSON.parse(JSON.stringify(settings));
  refs.providerJsonEditor.value = JSON.stringify(providerSettingsSnapshot, null, 2);
  refs.providerSourceLabel.textContent = `Editor source: ${source}`;
  setProviderControls(providerSettingsSnapshot);
}

async function loadDraftSettings() {
  const draft = await apiRequest("/v1/admin/provider-settings/draft");
  setProviderEditor(draft, "draft");
  log("Loaded provider draft settings.");
}

async function loadPublishedSettings() {
  const published = await apiRequest("/v1/admin/provider-settings");
  setProviderEditor(published, "published");
  log("Loaded provider published settings.");
}

async function refreshVersionsAndAudit() {
  const [versions, audit] = await Promise.all([
    apiRequest("/v1/admin/provider-settings/versions"),
    apiRequest("/v1/admin/provider-settings/audit?limit=30"),
  ]);
  renderVersions(versions);
  renderAudit(audit);
}

async function refreshPlans() {
  const plans = await apiRequest("/v1/admin/plans");
  renderPlans(plans);
  log(`Loaded ${plans.length} plan(s).`);
}

async function refreshVariables() {
  const variables = await apiRequest("/v1/admin/variables");
  renderVariables(variables);
  log(`Loaded ${variables.length} variable(s).`);
}

async function refreshExperiments() {
  const experiments = await apiRequest("/v1/admin/experiments");
  renderExperiments(experiments);
  if (!refs.experimentPerformanceId.value.trim() && Array.isArray(experiments) && experiments.length > 0) {
    refs.experimentPerformanceId.value = experiments[0].experiment_id || "";
  }
  if (!refs.experimentTrendId.value.trim() && Array.isArray(experiments) && experiments.length > 0) {
    refs.experimentTrendId.value = experiments[0].experiment_id || "";
  }
  if (!refs.experimentRolloutId.value.trim() && Array.isArray(experiments) && experiments.length > 0) {
    refs.experimentRolloutId.value = experiments[0].experiment_id || "";
  }
  log(`Loaded ${experiments.length} experiment(s).`);
}

async function refreshExperimentTemplates() {
  const templates = await apiRequest("/v1/admin/experiments/templates");
  renderExperimentTemplates(templates);
  log(`Loaded ${templates.length} experiment template(s).`);
}

function applySelectedExperimentTemplate() {
  const templateId = refs.experimentTemplateSelect.value;
  if (!templateId) {
    throw new Error("Select an experiment template first.");
  }
  const template = experimentTemplates.find((item) => item.template_id === templateId);
  if (!template) {
    throw new Error(`Template not found: ${templateId}`);
  }

  document.getElementById("experimentId").value = template.template_id;
  document.getElementById("experimentName").value = template.name || template.template_id;
  document.getElementById("experimentDescription").value = template.description || "";
  document.getElementById("experimentPrimaryMetric").value = template.primary_metric || "upgrade_conversion_7d";
  document.getElementById("experimentAssignmentUnit").value = template.assignment_unit || "user_id";
  document.getElementById("experimentActive").checked = true;
  document.getElementById("experimentVariantsJson").value = JSON.stringify(template.variants || [], null, 2);
  document.getElementById("experimentGuardrailsJson").value = JSON.stringify(template.guardrails || {}, null, 2);
  if (!refs.experimentPerformanceId.value.trim()) {
    refs.experimentPerformanceId.value = template.template_id;
  }
  if (!refs.experimentTrendId.value.trim()) {
    refs.experimentTrendId.value = template.template_id;
  }
  if (!refs.experimentRolloutId.value.trim()) {
    refs.experimentRolloutId.value = template.template_id;
  }
  log(`Applied experiment template ${template.template_id}.`);
}

async function refreshExperimentAudit() {
  const records = await apiRequest("/v1/admin/experiments/audit?limit=30");
  renderExperimentAudit(records);
  log("Loaded experiment audit records.");
}

async function refreshExperimentAutomationHistory() {
  const records = await apiRequest("/v1/admin/experiments/automation/history?limit=20");
  renderExperimentAutomationHistory(records);
  log("Loaded experiment automation history.");
}

function setExperimentGuardrailResult(payload, label) {
  refs.experimentGuardrailResult.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

function setExperimentPerformanceSummary(payload, label) {
  refs.experimentPerformanceSummary.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

function setExperimentTrendSummary(payload, label) {
  refs.experimentTrendSummary.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

function renderExperimentPerformance(payload) {
  const variants = payload.variants || [];
  refs.experimentPerformanceTableBody.innerHTML =
    variants.length === 0
      ? '<tr><td colspan="9">No performance data for this experiment yet.</td></tr>'
      : variants
          .map((variant) => {
            const isControl = payload.control_variant_id === variant.variant_id;
            const sourceSummary = Object.entries(variant.paid_source_breakdown || {})
              .map(([source, count]) => `${source}:${count}`)
              .join(", ");
            return `<tr>
      <td>${escapeHtml(variant.variant_id)}${isControl ? " <small>(control)</small>" : ""}</td>
      <td>${Number(variant.assigned_users || 0)}</td>
      <td>${formatPercent(variant.primary_metric_value || 0)}</td>
      <td>${variant.lift_vs_control_pct == null ? "-" : formatPercent(variant.lift_vs_control_pct)}</td>
      <td>${formatPValue(variant.p_value)}</td>
      <td>${variant.statistically_significant ? "yes" : "no"}</td>
      <td>${formatPercent(variant.render_success_rate || 0)}</td>
      <td>${formatUsd(variant.avg_cost_usd)}</td>
      <td>${escapeHtml(sourceSummary || "-")}</td>
    </tr>`;
          })
          .join("");

  const recommendation =
    payload.recommended_variant_id == null
      ? `Recommendation: hold (${payload.recommendation_reason || "no recommendation"})`
      : `Recommendation: rollout ${payload.recommended_variant_id} (${payload.recommendation_reason || "significant winner"})`;
  setExperimentPerformanceSummary(
    payload,
    [
      `Experiment ${payload.experiment_id} (${payload.primary_metric})`,
      `Control: ${payload.control_variant_id || "-"}`,
      `Window: ${payload.window_hours}h`,
      `Alpha: ${payload.significance_alpha}`,
      `Min Sample: ${payload.minimum_sample_size}`,
      recommendation,
    ].join(" | "),
  );
}

function renderExperimentTrend(payload) {
  const rows = [];
  (payload.variants || []).forEach((variant) => {
    (variant.points || []).forEach((point) => {
      rows.push({
        variant_id: variant.variant_id,
        bucket_end: point.bucket_end,
        point,
      });
    });
  });

  rows.sort((a, b) => {
    const left = new Date(a.bucket_end || 0).getTime();
    const right = new Date(b.bucket_end || 0).getTime();
    if (left !== right) {
      return right - left;
    }
    return a.variant_id.localeCompare(b.variant_id);
  });

  refs.experimentTrendTableBody.innerHTML =
    rows.length === 0
      ? '<tr><td colspan="9">No trend data for this experiment yet.</td></tr>'
      : rows
          .map(({ variant_id, point }) => {
            const isControl = payload.control_variant_id === variant_id;
            return `<tr>
      <td>${escapeHtml((point.bucket_end || "").replace("T", " ").replace("Z", " UTC"))}</td>
      <td>${escapeHtml(variant_id)}${isControl ? " <small>(control)</small>" : ""}</td>
      <td>${Number(point.assigned_users || 0)}</td>
      <td>${formatPercent(point.primary_metric_value || 0)}</td>
      <td>${formatPercent(point.render_success_rate || 0)}</td>
      <td>${formatPercent(point.preview_to_final_rate || 0)}</td>
      <td>${formatPercent(point.paid_activation_rate || 0)}</td>
      <td>${point.avg_latency_ms == null ? "-" : Number(point.avg_latency_ms).toLocaleString()}</td>
      <td>${formatUsd(point.total_cost_usd || 0)}</td>
    </tr>`;
          })
          .join("");

  const bucketCount =
    payload.variants && payload.variants.length > 0 ? (payload.variants[0].points || []).length : 0;
  const variantCount = (payload.variants || []).length;
  setExperimentTrendSummary(
    payload,
    [
      `Experiment ${payload.experiment_id} (${payload.primary_metric})`,
      `Control: ${payload.control_variant_id || "-"}`,
      `Window: ${payload.window_hours}h`,
      `Bucket: ${payload.bucket_hours}h`,
      `Variants: ${variantCount}`,
      `Buckets per variant: ${bucketCount}`,
    ].join(" | "),
  );
  renderExperimentTrendChart(payload);
}

function renderExperimentTrendChart(payload) {
  const canvas = refs.experimentTrendChart;
  if (!canvas || typeof canvas.getContext !== "function") {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbf7ef";
  ctx.fillRect(0, 0, width, height);

  const variants = payload.variants || [];
  const pointCount = variants.reduce((max, variant) => Math.max(max, (variant.points || []).length), 0);
  if (variants.length === 0 || pointCount === 0) {
    ctx.fillStyle = "#5a6a5f";
    ctx.font = "14px IBM Plex Mono, monospace";
    ctx.fillText("No trend data to chart.", 24, 36);
    return;
  }

  const left = 60;
  const right = 22;
  const top = 22;
  const bottom = 42;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const palette = ["#0f766e", "#d9480f", "#334155", "#9333ea", "#059669", "#dc2626"];

  const values = [];
  variants.forEach((variant) => {
    (variant.points || []).forEach((point) => {
      values.push(Number(point.primary_metric_value || 0));
    });
  });
  const maxValue = Math.max(100, ...values);
  const axisColor = "#b8ad99";
  const gridColor = "#e3dbce";

  ctx.strokeStyle = axisColor;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, top + plotHeight);
  ctx.lineTo(left + plotWidth, top + plotHeight);
  ctx.stroke();

  const yTicks = 4;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const y = top + (plotHeight * tick) / yTicks;
    const value = maxValue - (maxValue * tick) / yTicks;
    ctx.strokeStyle = gridColor;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + plotWidth, y);
    ctx.stroke();

    ctx.fillStyle = "#5a6a5f";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText(`${value.toFixed(0)}%`, 10, y + 4);
  }

  const xStep = pointCount <= 1 ? 0 : plotWidth / (pointCount - 1);
  variants.forEach((variant, index) => {
    const points = variant.points || [];
    const color = palette[index % palette.length];

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((point, pointIndex) => {
      const x = pointCount <= 1 ? left + plotWidth / 2 : left + xStep * pointIndex;
      const metric = Number(point.primary_metric_value || 0);
      const normalized = Math.max(0, Math.min(1, metric / maxValue));
      const y = top + (1 - normalized) * plotHeight;
      if (pointIndex === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    points.forEach((point, pointIndex) => {
      const x = pointCount <= 1 ? left + plotWidth / 2 : left + xStep * pointIndex;
      const metric = Number(point.primary_metric_value || 0);
      const normalized = Math.max(0, Math.min(1, metric / maxValue));
      const y = top + (1 - normalized) * plotHeight;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    const legendX = left + index * 170;
    const legendY = 14;
    ctx.fillRect(legendX, legendY - 8, 12, 3);
    ctx.fillStyle = "#304539";
    ctx.font = "11px IBM Plex Mono, monospace";
    const suffix = payload.control_variant_id === variant.variant_id ? " (control)" : "";
    ctx.fillText(`${variant.variant_id}${suffix}`, legendX + 16, legendY - 4);
  });

  ctx.fillStyle = "#5a6a5f";
  ctx.font = "11px IBM Plex Mono, monospace";
  ctx.fillText("Oldest", left, top + plotHeight + 18);
  ctx.fillText("Latest", left + plotWidth - 36, top + plotHeight + 18);
}

async function runExperimentGuardrails() {
  const hours = Number(refs.experimentGuardrailHours.value || 24);
  const dryRun = refs.experimentGuardrailDryRun.checked;
  const payload = await apiRequest(
    `/v1/admin/experiments/guardrails/evaluate?hours=${hours}&dry_run=${dryRun ? "true" : "false"}&${actorReasonQuery()}`,
    { method: "POST" },
  );
  setExperimentGuardrailResult(payload, dryRun ? "Guardrail dry run result" : "Guardrail live enforcement result");
  await refreshExperiments();
  await refreshExperimentAudit();
  log(
    dryRun
      ? `Guardrail dry run completed (breached=${payload.breached_count}, paused=${payload.paused_count}).`
      : `Guardrail enforcement completed (breached=${payload.breached_count}, paused=${payload.paused_count}).`,
  );
}

async function runExperimentPerformance() {
  const experimentId = refs.experimentPerformanceId.value.trim();
  if (!experimentId) {
    throw new Error("Experiment ID is required for performance evaluation.");
  }
  const hours = Number(refs.experimentPerformanceHours.value || 24);
  const payload = await apiRequest(
    `/v1/admin/experiments/${encodeURIComponent(experimentId)}/performance?hours=${hours}`,
  );
  renderExperimentPerformance(payload);
  log(
    payload.recommended_variant_id
      ? `Performance evaluated for ${experimentId}. Winner: ${payload.recommended_variant_id}.`
      : `Performance evaluated for ${experimentId}. Recommendation: hold.`,
  );
}

async function runExperimentTrend() {
  const experimentId = refs.experimentTrendId.value.trim();
  if (!experimentId) {
    throw new Error("Experiment ID is required for trend analysis.");
  }
  const hours = Number(refs.experimentTrendHours.value || 168);
  const bucketHours = Number(refs.experimentTrendBucketHours.value || 24);
  const payload = await apiRequest(
    `/v1/admin/experiments/${encodeURIComponent(experimentId)}/trends?hours=${hours}&bucket_hours=${bucketHours}`,
  );
  renderExperimentTrend(payload);
  log(
    `Trend analysis loaded for ${experimentId} (window=${hours}h, bucket=${bucketHours}h).`,
  );
}

function setExperimentRolloutResult(payload, label) {
  refs.experimentRolloutResult.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

function setExperimentAutomationResult(payload, label) {
  refs.experimentAutomationResult.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

async function runExperimentRollout() {
  const experimentId = refs.experimentRolloutId.value.trim();
  if (!experimentId) {
    throw new Error("Experiment ID is required for rollout evaluation.");
  }
  const hours = Number(refs.experimentRolloutHours.value || 168);
  const dryRun = refs.experimentRolloutDryRun.checked;
  const payload = await apiRequest(
    `/v1/admin/experiments/${encodeURIComponent(experimentId)}/rollout/evaluate?hours=${hours}&dry_run=${dryRun ? "true" : "false"}&${actorReasonQuery()}`,
    { method: "POST" },
  );
  const label = dryRun ? "Rollout dry-run result" : "Rollout apply result";
  setExperimentRolloutResult(payload, label);
  await refreshExperiments();
  await refreshExperimentAudit();
  log(
    dryRun
      ? `Rollout dry-run for ${experimentId}: blocked=${payload.blocked_reason || "none"}, next=${payload.next_rollout_percent}%.`
      : `Rollout apply for ${experimentId}: applied=${payload.applied}, next=${payload.next_rollout_percent}%.`,
  );
}

async function runAllExperimentRollouts() {
  const hours = Number(refs.experimentRolloutHours.value || 168);
  const dryRun = refs.experimentRolloutDryRun.checked;
  const limit = Number(refs.experimentRolloutLimit.value || 200);
  const payload = await apiRequest(
    `/v1/admin/experiments/rollout/evaluate-all?hours=${hours}&dry_run=${dryRun ? "true" : "false"}&limit=${limit}&${actorReasonQuery()}`,
    { method: "POST" },
  );
  const label = dryRun ? "Bulk rollout dry-run result" : "Bulk rollout apply result";
  setExperimentRolloutResult(payload, label);
  await refreshExperiments();
  await refreshExperimentAudit();
  log(
    dryRun
      ? `Bulk rollout dry-run evaluated ${payload.evaluated_count} experiments (blocked=${payload.blocked_count}).`
      : `Bulk rollout apply evaluated ${payload.evaluated_count} experiments (applied=${payload.applied_count}).`,
  );
}

async function runExperimentAutomation() {
  const hours = Number(refs.experimentAutomationHours.value || 168);
  const dryRun = refs.experimentAutomationDryRun.checked;
  const rolloutLimit = Number(refs.experimentAutomationLimit.value || 200);
  const payload = await apiRequest(
    `/v1/admin/experiments/automation/run?hours=${hours}&dry_run=${dryRun ? "true" : "false"}&rollout_limit=${rolloutLimit}&${actorReasonQuery()}`,
    { method: "POST" },
  );
  const label = dryRun ? "Automation dry-run result" : "Automation live result";
  setExperimentAutomationResult(payload, label);
  await refreshExperiments();
  await refreshExperimentAudit();
  await refreshExperimentAutomationHistory();
  log(
    dryRun
      ? `Automation dry-run completed (guardrail_breached=${payload.guardrails.breached_count}, rollout_blocked=${payload.rollouts.blocked_count}).`
      : `Automation live run completed (paused=${payload.guardrails.paused_count}, rollout_applied=${payload.rollouts.applied_count}).`,
  );
}

async function refreshHealth() {
  const health = await apiRequest("/v1/admin/providers/health?hours=24");
  renderProviderHealth(health);
  log("Loaded provider health metrics.");
}

async function refreshAnalytics() {
  const hours = Number(refs.analyticsWindowHours?.value || 24);
  const dashboard = await apiRequest(`/v1/admin/analytics/dashboard?hours=${hours}`);
  renderAnalytics(dashboard);
  log("Loaded analytics overview.");
}

async function refreshProductAudit() {
  const records = await apiRequest("/v1/admin/product-audit?limit=30");
  renderProductAudit(records);
  log("Loaded product audit records.");
}

function setCreditResetForm(schedule) {
  refs.creditResetEnabled.checked = Boolean(schedule.enabled);
  refs.creditResetHour.value = String(schedule.reset_hour_utc ?? 0);
  refs.creditResetMinute.value = String(schedule.reset_minute_utc ?? 0);
  refs.creditResetFreeCredits.value = String(schedule.free_daily_credits ?? 3);
  refs.creditResetProCredits.value = String(schedule.pro_daily_credits ?? 80);
  refs.creditResetLastRun.value = formatDateTime(schedule.last_run_at);
  refs.creditResetNextRun.value = formatDateTime(schedule.next_run_at);
}

function setCreditResetResult(payload, label) {
  refs.creditResetResult.textContent = `${label}\n${JSON.stringify(payload, null, 2)}`;
}

async function loadCreditResetSchedule() {
  const schedule = await apiRequest("/v1/admin/credits/reset-schedule");
  setCreditResetForm(schedule);
  log("Loaded credit reset schedule.");
}

async function saveCreditResetSchedule() {
  const payload = {
    enabled: refs.creditResetEnabled.checked,
    reset_hour_utc: Number(refs.creditResetHour.value),
    reset_minute_utc: Number(refs.creditResetMinute.value),
    free_daily_credits: Number(refs.creditResetFreeCredits.value),
    pro_daily_credits: Number(refs.creditResetProCredits.value),
  };
  const schedule = await apiRequest("/v1/admin/credits/reset-schedule", {
    method: "PUT",
    body: payload,
  });
  setCreditResetForm(schedule);
  setCreditResetResult(schedule, "Saved credit reset schedule");
  log("Updated credit reset schedule.");
}

async function runCreditReset(dryRun) {
  const payload = await apiRequest(`/v1/admin/credits/run-daily-reset?dry_run=${dryRun ? "true" : "false"}`, {
    method: "POST",
  });
  setCreditResetResult(payload, dryRun ? "Dry-run reset result" : "Live reset result");
  await loadCreditResetSchedule();
  log(dryRun ? "Executed dry-run credit reset." : "Executed live credit reset.");
}

async function tickCreditReset() {
  const payload = await apiRequest("/v1/admin/credits/tick-reset", {
    method: "POST",
  });
  setCreditResetResult(payload, "Tick scheduler result");
  await loadCreditResetSchedule();
  log("Executed credit reset scheduler tick.");
}

function syncStructuredFromEditor() {
  const settings = parseProviderSettingsFromEditor();
  setProviderControls(settings);
  log("Quick router controls synced from JSON editor.");
}

function applyStructuredToEditor() {
  const baseSettings = parseProviderSettingsFromEditor();
  const merged = buildProviderSettingsFromControls(baseSettings);
  setProviderEditor(merged, "quick-controls");
  log("Applied quick router controls into JSON editor.");
}

async function refreshAll() {
  setConnectionBadge("syncing", "pending");
  try {
    await Promise.all([
      loadDraftSettings(),
      refreshVersionsAndAudit(),
      refreshPlans(),
      refreshVariables(),
      refreshExperiments(),
      refreshExperimentTemplates(),
      refreshExperimentAudit(),
      refreshExperimentAutomationHistory(),
      loadCreditResetSchedule(),
      refreshHealth(),
      refreshAnalytics(),
      refreshProductAudit(),
    ]);
    setConnectionBadge("connected", "muted");
    setLastSync();
  } catch (error) {
    setConnectionBadge("error", "danger");
    log(error.message, "ERROR");
    throw error;
  }
}

function parseVariableValue(type, rawValue) {
  if (type === "number") {
    const numberValue = Number(rawValue);
    if (!Number.isFinite(numberValue)) {
      throw new Error("Variable value must be a valid number.");
    }
    return numberValue;
  }

  if (type === "boolean") {
    const lowered = rawValue.trim().toLowerCase();
    if (["true", "1", "yes", "on"].includes(lowered)) {
      return true;
    }
    if (["false", "0", "no", "off"].includes(lowered)) {
      return false;
    }
    throw new Error('Boolean values must be one of: true, false, 1, 0, yes, no.');
  }

  return rawValue;
}

async function testHealth() {
  try {
    const response = await apiRequest("/healthz");
    const status = typeof response === "object" ? response.status : String(response);
    setConnectionBadge(status, "muted");
    log(`Health check succeeded: ${status}`);
  } catch (error) {
    setConnectionBadge("error", "danger");
    log(`Health check failed: ${error.message}`, "ERROR");
  }
}

function bindEvents() {
  document.getElementById("saveConnection").addEventListener("click", () => {
    saveConnectionValues();
    setConnectionBadge("saved", "pending");
  });

  document.getElementById("testConnection").addEventListener("click", async () => {
    await testHealth();
  });

  document.getElementById("refreshAll").addEventListener("click", async () => {
    try {
      await refreshAll();
    } catch {
      // error already logged.
    }
  });

  document.getElementById("syncStructuredFromJson").addEventListener("click", () => {
    try {
      syncStructuredFromEditor();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("applyStructuredToJson").addEventListener("click", () => {
    try {
      applyStructuredToEditor();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("loadDraft").addEventListener("click", async () => {
    try {
      await loadDraftSettings();
      await refreshVersionsAndAudit();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("loadPublished").addEventListener("click", async () => {
    try {
      await loadPublishedSettings();
      await refreshVersionsAndAudit();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("formatProviderJson").addEventListener("click", () => {
    try {
      const parsed = JSON.parse(refs.providerJsonEditor.value);
      refs.providerJsonEditor.value = JSON.stringify(parsed, null, 2);
      setProviderControls(parsed);
      log("Formatted provider JSON.");
    } catch (error) {
      log(`Invalid provider JSON: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("saveDraft").addEventListener("click", async () => {
    try {
      const payload = JSON.parse(refs.providerJsonEditor.value);
      const result = await apiRequest(`/v1/admin/provider-settings/draft?${actorReasonQuery()}`, {
        method: "PUT",
        body: payload,
      });
      setProviderEditor(result, "draft");
      await refreshVersionsAndAudit();
      setLastSync();
      log("Saved provider draft settings.");
    } catch (error) {
      log(`Save draft failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("publishDraft").addEventListener("click", async () => {
    try {
      const values = getConnectionValues();
      const summary = await apiRequest("/v1/admin/provider-settings/publish", {
        method: "POST",
        body: {
          actor: values.adminActor,
          reason: values.actionReason,
        },
      });
      await loadPublishedSettings();
      await refreshVersionsAndAudit();
      setLastSync();
      log(`Published provider draft as version ${summary.version}.`);
    } catch (error) {
      log(`Publish failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("rollbackButton").addEventListener("click", async () => {
    const versionRaw = document.getElementById("rollbackVersion").value.trim();
    if (!versionRaw) {
      log("Enter a version number before rollback.", "ERROR");
      return;
    }

    const version = Number(versionRaw);
    if (!Number.isInteger(version) || version < 1) {
      log("Rollback version must be a positive integer.", "ERROR");
      return;
    }

    try {
      const values = getConnectionValues();
      const summary = await apiRequest(`/v1/admin/provider-settings/rollback/${version}`, {
        method: "POST",
        body: {
          actor: values.adminActor,
          reason: values.actionReason,
        },
      });
      await loadPublishedSettings();
      await refreshVersionsAndAudit();
      setLastSync();
      log(`Rollback completed. Active version is now ${summary.version}.`);
    } catch (error) {
      log(`Rollback failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("refreshPlans").addEventListener("click", async () => {
    try {
      await refreshPlans();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("planForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const planId = document.getElementById("planId").value.trim();
      if (!planId) {
        throw new Error("Plan ID is required.");
      }

      const payload = {
        display_name: document.getElementById("planDisplayName").value.trim(),
        is_active: document.getElementById("planActive").checked,
        daily_credits: Number(document.getElementById("dailyCredits").value),
        preview_cost_credits: Number(document.getElementById("previewCost").value),
        final_cost_credits: Number(document.getElementById("finalCost").value),
        monthly_price_usd: Number(document.getElementById("monthlyPrice").value),
        ios_product_id: document.getElementById("iosProductId").value.trim() || null,
        android_product_id: document.getElementById("androidProductId").value.trim() || null,
        web_product_id: document.getElementById("webProductId").value.trim() || null,
        features: document
          .getElementById("featuresCsv")
          .value.split(",")
          .map((part) => part.trim())
          .filter(Boolean),
      };

      await apiRequest(`/v1/admin/plans/${encodeURIComponent(planId)}?${actorReasonQuery()}`, {
        method: "PUT",
        body: payload,
      });
      await refreshPlans();
      await refreshProductAudit();
      setLastSync();
      log(`Upserted plan ${planId}.`);
    } catch (error) {
      log(`Upsert plan failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("deletePlanButton").addEventListener("click", async () => {
    const planId = document.getElementById("deletePlanId").value.trim();
    if (!planId) {
      log("Enter a plan ID to delete.", "ERROR");
      return;
    }

    if (!window.confirm(`Delete plan ${planId}?`)) {
      return;
    }

    try {
      await apiRequest(`/v1/admin/plans/${encodeURIComponent(planId)}?${actorReasonQuery()}`, {
        method: "DELETE",
      });
      await refreshPlans();
      await refreshProductAudit();
      setLastSync();
      log(`Deleted plan ${planId}.`);
    } catch (error) {
      log(`Delete plan failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("refreshVariables").addEventListener("click", async () => {
    try {
      await refreshVariables();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("refreshExperiments").addEventListener("click", async () => {
    try {
      await refreshExperiments();
      await refreshExperimentTemplates();
      await refreshExperimentAudit();
      await refreshExperimentAutomationHistory();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("refreshExperimentTemplates").addEventListener("click", async () => {
    try {
      await refreshExperimentTemplates();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("applyExperimentTemplate").addEventListener("click", () => {
    try {
      applySelectedExperimentTemplate();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("runExperimentGuardrails").addEventListener("click", async () => {
    try {
      await runExperimentGuardrails();
      setLastSync();
    } catch (error) {
      log(`Experiment guardrail run failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runExperimentPerformance").addEventListener("click", async () => {
    try {
      await runExperimentPerformance();
      setLastSync();
    } catch (error) {
      log(`Experiment performance evaluation failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runExperimentTrend").addEventListener("click", async () => {
    try {
      await runExperimentTrend();
      setLastSync();
    } catch (error) {
      log(`Experiment trend analysis failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runExperimentRollout").addEventListener("click", async () => {
    try {
      await runExperimentRollout();
      setLastSync();
    } catch (error) {
      log(`Experiment rollout evaluation failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runExperimentRolloutAll").addEventListener("click", async () => {
    try {
      await runAllExperimentRollouts();
      setLastSync();
    } catch (error) {
      log(`Bulk experiment rollout evaluation failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runExperimentAutomation").addEventListener("click", async () => {
    try {
      await runExperimentAutomation();
      setLastSync();
    } catch (error) {
      log(`Experiment automation run failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("experimentForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const experimentId = document.getElementById("experimentId").value.trim();
      if (!experimentId) {
        throw new Error("Experiment ID is required.");
      }

      let variants = [];
      let guardrails = {};
      try {
        variants = JSON.parse(document.getElementById("experimentVariantsJson").value);
      } catch (error) {
        throw new Error(`Variants JSON invalid: ${error.message}`);
      }
      try {
        guardrails = JSON.parse(document.getElementById("experimentGuardrailsJson").value || "{}");
      } catch (error) {
        throw new Error(`Guardrails JSON invalid: ${error.message}`);
      }

      const payload = {
        name: document.getElementById("experimentName").value.trim(),
        description: document.getElementById("experimentDescription").value.trim() || null,
        is_active: document.getElementById("experimentActive").checked,
        assignment_unit: document.getElementById("experimentAssignmentUnit").value.trim() || "user_id",
        primary_metric: document.getElementById("experimentPrimaryMetric").value.trim(),
        guardrails,
        variants,
      };

      await apiRequest(`/v1/admin/experiments/${encodeURIComponent(experimentId)}?${actorReasonQuery()}`, {
        method: "PUT",
        body: payload,
      });
      await refreshExperiments();
      await refreshExperimentAudit();
      setLastSync();
      log(`Upserted experiment ${experimentId}.`);
    } catch (error) {
      log(`Upsert experiment failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("deleteExperimentButton").addEventListener("click", async () => {
    const experimentId = document.getElementById("deleteExperimentId").value.trim();
    if (!experimentId) {
      log("Enter an experiment ID to delete.", "ERROR");
      return;
    }

    if (!window.confirm(`Delete experiment ${experimentId}?`)) {
      return;
    }

    try {
      await apiRequest(`/v1/admin/experiments/${encodeURIComponent(experimentId)}?${actorReasonQuery()}`, {
        method: "DELETE",
      });
      await refreshExperiments();
      await refreshExperimentAudit();
      setLastSync();
      log(`Deleted experiment ${experimentId}.`);
    } catch (error) {
      log(`Delete experiment failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("variableForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const key = document.getElementById("variableKey").value.trim();
      if (!key) {
        throw new Error("Variable key is required.");
      }

      const variableType = document.getElementById("variableType").value;
      const rawValue = document.getElementById("variableValue").value;
      const payload = {
        value: parseVariableValue(variableType, rawValue),
        description: document.getElementById("variableDescription").value.trim() || null,
      };

      await apiRequest(`/v1/admin/variables/${encodeURIComponent(key)}?${actorReasonQuery()}`, {
        method: "PUT",
        body: payload,
      });
      await refreshVariables();
      await refreshProductAudit();
      setLastSync();
      log(`Upserted variable ${key}.`);
    } catch (error) {
      log(`Upsert variable failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("deleteVariableButton").addEventListener("click", async () => {
    const key = document.getElementById("deleteVariableKey").value.trim();
    if (!key) {
      log("Enter a variable key to delete.", "ERROR");
      return;
    }

    if (!window.confirm(`Delete variable ${key}?`)) {
      return;
    }

    try {
      await apiRequest(`/v1/admin/variables/${encodeURIComponent(key)}?${actorReasonQuery()}`, {
        method: "DELETE",
      });
      await refreshVariables();
      await refreshProductAudit();
      setLastSync();
      log(`Deleted variable ${key}.`);
    } catch (error) {
      log(`Delete variable failed: ${error.message}`, "ERROR");
    }
  });

  refs.creditResetForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await saveCreditResetSchedule();
      setLastSync();
    } catch (error) {
      log(`Save credit reset schedule failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("refreshCreditReset").addEventListener("click", async () => {
    try {
      await loadCreditResetSchedule();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("dryRunCreditReset").addEventListener("click", async () => {
    try {
      await runCreditReset(true);
      setLastSync();
    } catch (error) {
      log(`Dry-run reset failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("runCreditResetNow").addEventListener("click", async () => {
    try {
      await runCreditReset(false);
      setLastSync();
    } catch (error) {
      log(`Live reset failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("tickCreditReset").addEventListener("click", async () => {
    try {
      await tickCreditReset();
      setLastSync();
    } catch (error) {
      log(`Tick reset failed: ${error.message}`, "ERROR");
    }
  });

  document.getElementById("refreshHealth").addEventListener("click", async () => {
    try {
      await refreshHealth();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("refreshAnalytics").addEventListener("click", async () => {
    try {
      await refreshAnalytics();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  refs.analyticsWindowHours.addEventListener("change", async () => {
    try {
      await refreshAnalytics();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });

  document.getElementById("refreshProductAudit").addEventListener("click", async () => {
    try {
      await refreshProductAudit();
      setLastSync();
    } catch (error) {
      log(error.message, "ERROR");
    }
  });
}

function init() {
  loadConnectionValues();
  setProviderEditor(DEFAULT_PROVIDER_SETTINGS, "defaults");
  renderProviderHealth({});
  renderProductAudit([]);
  renderExperiments([]);
  renderExperimentTemplates([]);
  renderExperimentAudit([]);
  renderExperimentAutomationHistory([]);
  renderAnalytics({
    summary: {
      total_events: 0,
      render_success_rate: 0,
      render_success: 0,
      render_failed: 0,
      avg_latency_ms: null,
      p95_latency_ms: null,
      total_cost_usd: 0,
      avg_cost_per_render_usd: null,
      preview_to_final_rate: 0,
      active_render_users: 0,
    },
    provider_breakdown: [],
    operation_breakdown: [],
    platform_breakdown: [],
    status_breakdown: [],
    subscription_sources: [],
    credits: {
      consumed_total: 0,
      granted_total: 0,
      refunded_total: 0,
      daily_reset_total: 0,
      unique_consumers: 0,
    },
    subscriptions: {
      active_subscriptions: 0,
      renewals_due_7d: 0,
      expirations_due_7d: 0,
    },
    queue: {
      queued_jobs: 0,
      in_progress_jobs: 0,
      completed_jobs_window: 0,
      failed_jobs_window: 0,
      canceled_jobs_window: 0,
    },
    funnel: {
      login_users: 0,
      preview_users: 0,
      final_users: 0,
      checkout_starts: 0,
      paid_activations: 0,
      login_to_preview_rate: 0,
      preview_to_final_rate: 0,
      final_to_checkout_rate: 0,
      checkout_to_paid_rate: 0,
    },
    experiment_breakdown: [],
    alerts: [],
  });
  setCreditResetResult({}, "No reset actions yet.");
  setExperimentGuardrailResult({}, "No guardrail runs yet.");
  renderExperimentPerformance({
    experiment_id: "-",
    primary_metric: "-",
    control_variant_id: null,
    window_hours: 24,
    significance_alpha: 0.05,
    minimum_sample_size: 100,
    recommendation_reason: "No performance evaluation yet.",
    variants: [],
  });
  setExperimentPerformanceSummary({}, "No performance evaluation yet.");
  renderExperimentTrend({
    experiment_id: "-",
    primary_metric: "-",
    control_variant_id: null,
    window_hours: 168,
    bucket_hours: 24,
    variants: [],
  });
  setExperimentTrendSummary({}, "No trend analysis yet.");
  setExperimentRolloutResult({}, "No rollout evaluation yet.");
  setExperimentAutomationResult({}, "No automation run yet.");
  bindEvents();
  setConnectionBadge("idle", "pending");
  log("Admin dashboard ready. Set API settings and click Refresh All Data.");
}

init();
