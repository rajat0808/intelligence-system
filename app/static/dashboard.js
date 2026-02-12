(() => {
  /**
   * @typedef {Object} DangerSummary
   * @property {string} store_id
   * @property {number} EARLY
   * @property {number} HIGH
   * @property {number} CRITICAL
   * @property {number} total_danger_capital
   */
  /**
   * @typedef {Object} AgingSummary
   * @property {string} store_id
   * @property {number} HEALTHY
   * @property {number} TRANSFER
   * @property {number} RR_TT
   * @property {number} VERY_DANGER
   * @property {number} total_aging_capital
   */
  /**
   * @typedef {Object} DashboardData
   * @property {string=} date
   * @property {number=} store_count
   * @property {DangerSummary[]=} results
   * @property {AgingSummary[]=} aging_results
   */
  /**
   * @typedef {Object} DangerTotals
   * @property {number} EARLY
   * @property {number} HIGH
   * @property {number} CRITICAL
   * @property {number} total_danger_capital
   */
  /**
   * @typedef {Object} AgingTotals
   * @property {number} HEALTHY
   * @property {number} TRANSFER
   * @property {number} RR_TT
   * @property {number} VERY_DANGER
   * @property {number} total_aging_capital
   */
  /**
   * @typedef {Object} StoreSummary
   * @property {string} id
   * @property {DangerTotals} danger
   * @property {AgingTotals} aging
   * @property {number} totalAging
   */
  /**
   * @typedef {Object} InventoryItem
   * @property {string=} style_code
   * @property {string=} article_name
   * @property {string=} category
   * @property {string=} department_name
   * @property {string=} department
   * @property {string=} supplier_name
   * @property {string=} supplier
   * @property {string|number=} store_id
   * @property {number=} quantity
   * @property {number=} qty
   * @property {number=} age_days
   * @property {number=} days
   * @property {number=} item_mrp
   * @property {number=} mrp
   * @property {string=} aging_status
   */
  /**
   * @typedef {Object} InventorySearchResponse
   * @property {number=} count
   * @property {InventoryItem[]=} results
   */
  /**
   * @typedef {Object} FetchResult
   * @property {boolean} ok
   * @property {boolean} unauthorized
   * @property {number} status
   * @property {any} data
   * @property {any=} error
   */

  /** @type {{ allStores: StoreSummary[], filteredStores: StoreSummary[], agingFilters: Set<string>, live: boolean, liveTimer: number | null, inventoryAlertOnly: boolean, inventoryResults: InventoryItem[] }} */
  const state = {
    allStores: [],
    filteredStores: [],
    agingFilters: new Set(),
    live: true,
    liveTimer: null,
    inventoryAlertOnly: false,
    inventoryResults: [],
  };

  const elements = {
    storeCount: document.getElementById("store-count"),
    healthyCapital: document.getElementById("healthy-capital"),
    transferCapital: document.getElementById("transfer-capital"),
    rateRevisedCapital: document.getElementById("rate-revised-capital"),
    veryDangerCapital: document.getElementById("very-danger-capital"),
    lastUpdated: document.getElementById("last-updated"),
    tableBody: document.getElementById("store-table-body"),
    emptyState: document.getElementById("empty-state"),
    filterStatus: document.getElementById("filter-status"),
    tableStatus: document.getElementById("table-status"),
    searchInput: document.getElementById("search-input"),
    filtersPanel: document.getElementById("filters-panel"),
    trendHealthy: document.getElementById("trend-healthy"),
    trendTransfer: document.getElementById("trend-transfer"),
    trendRateRevised: document.getElementById("trend-rate-revised"),
    trendVeryDanger: document.getElementById("trend-very-danger"),
    trendHealthyLabel: document.getElementById("trend-healthy-label"),
    trendTransferLabel: document.getElementById("trend-transfer-label"),
    trendRateRevisedLabel: document.getElementById("trend-rate-revised-label"),
    trendVeryDangerLabel: document.getElementById("trend-very-danger-label"),
    agingHealthy: document.getElementById("aging-healthy"),
    agingTransfer: document.getElementById("aging-transfer"),
    agingRateRevised: document.getElementById("aging-rate-revised"),
    agingVeryDanger: document.getElementById("aging-very-danger"),
    healthInsights: document.getElementById("health-insights"),
    statusChart: document.getElementById("status-chart"),
    toast: document.getElementById("toast"),
    refreshBtn: document.getElementById("refresh-btn"),
    exportBtn: document.getElementById("export-btn"),
    resetBtn: document.getElementById("reset-btn"),
    liveToggle: document.getElementById("live-toggle"),
    liveStatus: document.getElementById("live-status"),
    analyticsLive: document.getElementById("analytics-live"),
    analyticsPredictive: document.getElementById("analytics-predictive"),
    systemHealthStatus: document.getElementById("system-health-status"),
    healthLatency: document.getElementById("health-latency"),
    healthLatencyBar: document.getElementById("health-latency-bar"),
    healthApiStatus: document.getElementById("health-api-status"),
    healthIngestion: document.getElementById("health-ingestion"),
    healthAutomation: document.getElementById("health-automation"),
    healthWorkflow: document.getElementById("health-workflow"),
    healthAlert: document.getElementById("health-alert"),
    healthApp: document.getElementById("health-app"),
    healthEnvironment: document.getElementById("health-environment"),
    healthTime: document.getElementById("health-time"),
    inventoryQuery: document.getElementById("inventory-query"),
    inventoryStore: document.getElementById("inventory-store"),
    inventorySearchBtn: document.getElementById("inventory-search-btn"),
    inventoryExportBtn: document.getElementById("inventory-export-btn"),
    inventoryTableBody: document.getElementById("inventory-table-body"),
    inventoryEmpty: document.getElementById("inventory-empty"),
    inventoryStatus: document.getElementById("inventory-status"),
    inventoryAlertOnly: document.getElementById("inventory-alert-only"),
  };

  const numberFormatter = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

  const dangerDefaults = { EARLY: 0, HIGH: 0, CRITICAL: 0, total_danger_capital: 0 };
  const agingDefaults = {
    HEALTHY: 0,
    TRANSFER: 0,
    RR_TT: 0,
    VERY_DANGER: 0,
    total_aging_capital: 0,
  };

  const levelLabels = {
    EARLY: "Early",
    HIGH: "High",
    CRITICAL: "Critical",
    HEALTHY: "Healthy",
    TRANSFER: "Transfer",
    RR_TT: "Rate revised",
    VERY_DANGER: "Very danger",
  };
  const agingClassMap = {
    HEALTHY: "healthy",
    TRANSFER: "transfer",
    RR_TT: "rate-revised",
    VERY_DANGER: "very-danger",
  };

  /** @returns {DashboardData | null} */
  function readSeedData() {
    const node = document.getElementById("dashboard-data");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      console.warn("Failed to parse dashboard seed data", error);
      return null;
    }
  }

  function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function formatNumber(value) {
    return numberFormatter.format(Math.round(toNumber(value)));
  }

  function formatOptional(value) {
    if (value === null || value === undefined || value === "") {
      return "--";
    }
    return formatNumber(value);
  }

  /**
   * @param {DashboardData | null | undefined} data
   * @returns {StoreSummary[]}
   */
  function buildStoreList(data) {
    const dangerResults = Array.isArray(data?.results) ? data.results : [];
    const agingResults = Array.isArray(data?.aging_results) ? data.aging_results : [];
    const dangerMap = new Map();
    const agingMap = new Map();

    dangerResults.forEach((row) => {
      if (!row) return;
      const storeId = String(row.store_id ?? "").trim();
      if (!storeId) return;
      dangerMap.set(storeId, {
        EARLY: toNumber(row.EARLY),
        HIGH: toNumber(row.HIGH),
        CRITICAL: toNumber(row.CRITICAL),
        total_danger_capital: toNumber(row.total_danger_capital),
      });
    });

    agingResults.forEach((row) => {
      if (!row) return;
      const storeId = String(row.store_id ?? "").trim();
      if (!storeId) return;
      agingMap.set(storeId, {
        HEALTHY: toNumber(row.HEALTHY),
        TRANSFER: toNumber(row.TRANSFER),
        RR_TT: toNumber(row.RR_TT),
        VERY_DANGER: toNumber(row.VERY_DANGER),
        total_aging_capital: toNumber(row.total_aging_capital),
      });
    });

    const storeIds = new Set([...dangerMap.keys(), ...agingMap.keys()]);
    const stores = [];

    storeIds.forEach((storeId) => {
      const danger = dangerMap.get(storeId) ?? { ...dangerDefaults };
      const aging = agingMap.get(storeId) ?? { ...agingDefaults };
      stores.push({
        id: storeId,
        danger,
        aging,
        totalAging: toNumber(aging.total_aging_capital),
      });
    });

    stores.sort((a, b) => b.totalAging - a.totalAging);
    return stores;
  }

  function computeTotals(stores) {
    const totals = {
      count: stores.length,
      aging: { HEALTHY: 0, TRANSFER: 0, RR_TT: 0, VERY_DANGER: 0, total: 0 },
      agingCounts: { HEALTHY: 0, TRANSFER: 0, RR_TT: 0, VERY_DANGER: 0 },
    };

    stores.forEach((store) => {
      totals.aging.HEALTHY += store.aging.HEALTHY;
      totals.aging.TRANSFER += store.aging.TRANSFER;
      totals.aging.RR_TT += store.aging.RR_TT;
      totals.aging.VERY_DANGER += store.aging.VERY_DANGER;
      totals.aging.total += store.totalAging;

      if (store.aging.HEALTHY > 0) totals.agingCounts.HEALTHY += 1;
      if (store.aging.TRANSFER > 0) totals.agingCounts.TRANSFER += 1;
      if (store.aging.RR_TT > 0) totals.agingCounts.RR_TT += 1;
      if (store.aging.VERY_DANGER > 0) totals.agingCounts.VERY_DANGER += 1;
    });

    return totals;
  }

  function showToast(message, variant = "success") {
    if (!elements.toast) return;
    elements.toast.textContent = message;
    elements.toast.className = `toast show ${variant}`;
    window.setTimeout(() => {
      elements.toast.className = "toast";
    }, 2400);
  }

  function flashAction(button) {
    if (!button) return;
    button.classList.remove("clicked");
    void button.offsetWidth;
    button.classList.add("clicked");
  }

  function updateSummary(stores) {
    const totals = computeTotals(stores);

    elements.storeCount.textContent = formatNumber(totals.count);

    elements.healthyCapital.textContent = formatNumber(totals.aging.HEALTHY);
    elements.transferCapital.textContent = formatNumber(totals.aging.TRANSFER);
    elements.rateRevisedCapital.textContent = formatNumber(totals.aging.RR_TT);
    elements.veryDangerCapital.textContent = formatNumber(totals.aging.VERY_DANGER);

    elements.trendHealthy.textContent = formatNumber(totals.aging.HEALTHY);
    elements.trendTransfer.textContent = formatNumber(totals.aging.TRANSFER);
    elements.trendRateRevised.textContent = formatNumber(totals.aging.RR_TT);
    elements.trendVeryDanger.textContent = formatNumber(totals.aging.VERY_DANGER);

    elements.trendHealthyLabel.textContent = `Healthy capital (${totals.agingCounts.HEALTHY})`;
    elements.trendTransferLabel.textContent = `Transfer capital (${totals.agingCounts.TRANSFER})`;
    elements.trendRateRevisedLabel.textContent = `Rate revised capital (${totals.agingCounts.RR_TT})`;
    elements.trendVeryDangerLabel.textContent = `Very danger capital (${totals.agingCounts.VERY_DANGER})`;

    elements.agingHealthy.textContent = formatNumber(totals.aging.HEALTHY);
    elements.agingTransfer.textContent = formatNumber(totals.aging.TRANSFER);
    elements.agingRateRevised.textContent = formatNumber(totals.aging.RR_TT);
    elements.agingVeryDanger.textContent = formatNumber(totals.aging.VERY_DANGER);

    updateHealthBars(totals);
    updateHealthInsights(totals);
    updateChart(totals);
  }

  function updateHealthBars(totals) {
    const total = totals.aging.total || 0;
    document.querySelectorAll(".health-item").forEach((item) => {
      const key = item.dataset.aging;
      const value = totals.aging[key] || 0;
      const percent = total > 0 ? Math.min(100, (value / total) * 100) : 0;
      const bar = item.querySelector(".health-bar span");
      if (bar) {
        bar.style.width = `${percent.toFixed(1)}%`;
      }
    });
  }

  function updateHealthInsights(totals) {
    const averageCapital = totals.count > 0 ? totals.aging.total / totals.count : 0;
    const insights = [
      { label: "Avg capital per store", value: formatNumber(averageCapital) },
      { label: "Rate revised stores", value: formatNumber(totals.agingCounts.RR_TT) },
      { label: "Very danger stores", value: formatNumber(totals.agingCounts.VERY_DANGER) },
    ];

    elements.healthInsights.innerHTML = "";
    insights.forEach((insight) => {
      const row = document.createElement("div");
      row.className = "health-insight";
      const label = document.createElement("span");
      label.textContent = insight.label;
      const value = document.createElement("span");
      value.textContent = insight.value;
      row.appendChild(label);
      row.appendChild(value);
      elements.healthInsights.appendChild(row);
    });
  }

  function updateChart(totals) {
    if (totals.aging.total <= 0) {
      elements.statusChart.innerHTML = '<div class="empty">No status capital recorded.</div>';
      return;
    }
    const values = [
      totals.aging.HEALTHY,
      totals.aging.TRANSFER,
      totals.aging.RR_TT,
      totals.aging.VERY_DANGER,
    ];
    const labels = ["Healthy", "Transfer", "Rate revised", "Very danger"];
    const fills = [
      "var(--maroon-200)",
      "var(--maroon-300)",
      "var(--maroon-400)",
      "var(--maroon-600)",
    ];
    const max = Math.max(...values, 1);
    const barWidth = 50;
    const gap = 22;
    const chartHeight = 120;
    const baseline = 150;
    const startX = 24;
    const bars = values
      .map((value, index) => {
        const height = Math.max(8, Math.round((value / max) * chartHeight));
        const x = startX + index * (barWidth + gap);
        const y = baseline - height;
        return `<rect x="${x}" y="${y}" width="${barWidth}" height="${height}" rx="10" fill="${fills[index]}" />`;
      })
      .join("");
    const labelsMarkup = labels
      .map((label, index) => {
        const x = startX + index * (barWidth + gap) + barWidth / 2;
        return `<text x="${x}" y="170" text-anchor="middle" font-size="9" fill="var(--text-300)">${label}</text>`;
      })
      .join("");

    elements.statusChart.innerHTML = `
      <svg viewBox="0 0 360 180" width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true">
        ${bars}
        ${labelsMarkup}
      </svg>
    `;
  }

  function updateSystemHealth(data, latencyMs) {
    if (!elements.healthLatency) return;
    const statusValue = data?.status === "ok" ? "Online" : "Degraded";
    const latencyText = Number.isFinite(latencyMs) ? `${latencyMs} ms` : "--";
    const latencyPercent = Number.isFinite(latencyMs) ? Math.min(100, (latencyMs / 200) * 100) : 0;

    elements.healthLatency.textContent = latencyText;
    elements.healthLatencyBar.style.width = `${latencyPercent.toFixed(0)}%`;
    elements.healthApiStatus.textContent = statusValue;
    elements.healthIngestion.textContent = statusValue;
    elements.healthAlert.textContent = statusValue;
    elements.healthAutomation.textContent = "Unavailable";
    elements.healthWorkflow.textContent = "Unavailable";
    elements.healthApp.textContent = data?.app ?? "--";
    elements.healthEnvironment.textContent = data?.environment ?? "--";
    elements.healthTime.textContent = data?.time ?? "--";
  }

  /** @returns {Promise<FetchResult>} */
  async function fetchJsonWithAuth(url, options = {}) {
    try {
      const response = await fetch(url, options);
      if (response.status === 401) {
        window.location.href = "/login";
        return { ok: false, unauthorized: true, status: response.status, data: null };
      }
      let data;
      try {
        data = await response.json();
      } catch (error) {
        data = null;
      }
      return { ok: response.ok, unauthorized: false, status: response.status, data };
    } catch (error) {
      return { ok: false, unauthorized: false, status: 0, data: null, error };
    }
  }

  /** @param {FetchResult} result */
  function logResultError(result) {
    if (result.error) {
      console.error(result.error);
    }
  }

  async function refreshHealth(showNotice) {
    if (!elements.systemHealthStatus) return;
    elements.systemHealthStatus.textContent = "Checking system health...";
    const start = performance.now();
    try {
      const response = await fetch("/health", { cache: "no-store" });
      const latencyMs = Math.round(performance.now() - start);
      if (!response.ok) {
        elements.systemHealthStatus.textContent = "Failed to load system health.";
        showToast("Failed to load system health", "error");
        console.error(new Error(`Request failed with ${response.status}`));
        return;
      }
      const data = await response.json();
      updateSystemHealth(data, latencyMs);
      elements.systemHealthStatus.textContent = `Updated ${new Date().toLocaleTimeString()}.`;
      if (showNotice) {
        showToast("System health refreshed", "success");
      }
    } catch (error) {
      elements.systemHealthStatus.textContent = "Failed to load system health.";
      showToast("Failed to load system health", "error");
      console.error(error);
    }
  }

  function buildPill(text, className) {
    const pill = document.createElement("span");
    pill.className = `pill ${className}`;
    pill.textContent = text;
    return pill;
  }

  function buildPillGroup(items) {
    const wrapper = document.createElement("div");
    wrapper.className = "chip-row";
    let hasValues = false;
    items.forEach((item) => {
      const value = toNumber(item.value);
      if (value <= 0) return;
      hasValues = true;
      wrapper.appendChild(buildPill(`${item.label} ${formatNumber(value)}`, item.className));
    });
    if (!hasValues) {
      wrapper.appendChild(buildPill("None", "none"));
    }
    return wrapper;
  }

  function buildStatusPill(value, type) {
    if (!value) {
      return buildPill("None", "none");
    }
    const label = levelLabels[value] ?? value;
    const classMap = type === "aging" ? agingClassMap : {};
    const className = classMap[value];
    return buildPill(label, className ?? "unknown");
  }

  function renderTable(stores) {
    elements.tableBody.innerHTML = "";

    stores.forEach((store) => {
      const row = document.createElement("tr");

      const storeCell = document.createElement("td");
      storeCell.className = "store-id";
      storeCell.dataset.label = "Store";
      storeCell.textContent = store.id;
      row.appendChild(storeCell);

      const totalCell = document.createElement("td");
      totalCell.className = "total";
      totalCell.dataset.label = "Total capital";
      totalCell.textContent = formatNumber(store.totalAging);
      row.appendChild(totalCell);

      const statusCell = document.createElement("td");
      statusCell.dataset.label = "Status mix";
      statusCell.appendChild(
        buildPillGroup([
          { label: levelLabels.HEALTHY, value: store.aging.HEALTHY, className: "healthy" },
          { label: levelLabels.TRANSFER, value: store.aging.TRANSFER, className: "transfer" },
          { label: levelLabels.RR_TT, value: store.aging.RR_TT, className: "rate-revised" },
          { label: levelLabels.VERY_DANGER, value: store.aging.VERY_DANGER, className: "very-danger" },
        ])
      );
      row.appendChild(statusCell);

      elements.tableBody.appendChild(row);
    });
  }

  function renderInventoryResults(items) {
    elements.inventoryTableBody.innerHTML = "";

    items.forEach((item) => {
      const row = document.createElement("tr");

      const cells = [
        { label: "Style", value: item.style_code ?? "--" },
        { label: "Article", value: item.article_name ?? "--" },
        { label: "Category", value: item.category ?? "--" },
        { label: "Department", value: item.department_name ?? "--" },
        { label: "Supplier", value: item.supplier_name ?? "--" },
        { label: "Store", value: item.store_id ?? "--" },
        { label: "Qty", value: formatOptional(item.quantity) },
        { label: "Days", value: formatOptional(item.age_days ?? item.days) },
        { label: "Item MRP", value: formatOptional(item.item_mrp ?? item.mrp) },
      ];

      cells.forEach((cell) => {
        const td = document.createElement("td");
        td.dataset.label = cell.label;
        td.textContent = cell.value;
        row.appendChild(td);
      });

      const agingCell = document.createElement("td");
      agingCell.dataset.label = "Status";
      agingCell.appendChild(buildStatusPill(item.aging_status, "aging"));
      row.appendChild(agingCell);

      elements.inventoryTableBody.appendChild(row);
    });

    elements.inventoryEmpty.hidden = items.length !== 0;
  }

  function resetInventoryResults(message) {
    elements.inventoryStatus.textContent = message;
    elements.inventoryTableBody.innerHTML = "";
    elements.inventoryEmpty.hidden = true;
  }

  async function runInventorySearch() {
    const query = elements.inventoryQuery.value.trim();
    const storeId = elements.inventoryStore.value.trim();

    if (query.length < 2) {
      resetInventoryResults("Enter at least 2 characters to search inventory.");
      return;
    }

    const params = new URLSearchParams({ query });
    if (storeId) {
      params.set("store_id", storeId);
    }
    if (state.inventoryAlertOnly) {
      params.set("alert_only", "true");
    }

    elements.inventoryStatus.textContent = "Searching inventory...";

    try {
      const result = await fetchJsonWithAuth(`/search/inventory?${params.toString()}`, {
        cache: "no-store",
      });
      if (result.unauthorized) {
        return;
      }
      if (!result.ok) {
        let message = "Inventory search failed.";
        if (result.data?.detail) {
          message = result.data.detail;
        }
        resetInventoryResults(message);
        logResultError(result);
        return;
      }
      if (!result.data) {
        resetInventoryResults("Inventory search failed.");
        return;
      }
      const data = /** @type {InventorySearchResponse} */ (result.data ?? {});
      const results = Array.isArray(data.results) ? data.results : [];
      state.inventoryResults = results;
      renderInventoryResults(results);
      elements.inventoryStatus.textContent = `Found ${data.count ?? results.length} items.`;
    } catch (error) {
      resetInventoryResults("Inventory search failed.");
      console.error(error);
    }
  }

  function applyFilters() {
    const query = elements.searchInput.value.trim().toLowerCase();
    const agingActive = state.agingFilters.size > 0;

    state.filteredStores = state.allStores.filter((store) => {
      if (query && !store.id.toLowerCase().includes(query)) {
        return false;
      }
      if (agingActive) {
        const matchesAging = Array.from(state.agingFilters).some(
          (level) => toNumber(store.aging[level]) > 0
        );
        if (!matchesAging) return false;
      }
      return true;
    });

    renderTable(state.filteredStores);
    updateSummary(state.filteredStores);

    const totalCount = state.allStores.length;
    const filteredCount = state.filteredStores.length;
    const activeFilters = state.agingFilters.size;
    const statusParts = [`Showing ${filteredCount} of ${totalCount} stores`];
    if (activeFilters > 0) statusParts.push(`${activeFilters} status tags active`);
    if (query) statusParts.push("Search active");
    elements.filterStatus.textContent = statusParts.join(". ") + ".";
    elements.tableStatus.textContent = filteredCount === 0 ? "No stores match the current filters." : "Ready.";

    elements.emptyState.hidden = filteredCount !== 0;
    elements.filtersPanel.classList.toggle("filters-open", activeFilters > 0 || !!query);
  }

  function escapeCsv(value) {
    const text = String(value ?? "");
    if (text.includes(",") || text.includes('"') || text.includes("\n")) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  }

  function downloadCsv(filename, headers, rows) {
    const csv = [headers.join(","), ...rows.map((row) => row.map(escapeCsv).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  function exportCsv() {
    if (!state.filteredStores.length) {
      showToast("No stores to export", "error");
      return;
    }
    const headers = [
      "store_id",
      "total_aging_capital",
      "HEALTHY",
      "TRANSFER",
      "RR_TT",
      "VERY_DANGER",
    ];
    const rows = state.filteredStores.map((store) => [
      store.id,
      store.totalAging,
      store.aging.HEALTHY,
      store.aging.TRANSFER,
      store.aging.RR_TT,
      store.aging.VERY_DANGER,
    ]);
    downloadCsv("store_status_export.csv", headers, rows);
    showToast("Export ready", "success");
  }

  function exportInventoryCsv() {
    if (!state.inventoryResults.length) {
      showToast("No inventory to export", "error");
      return;
    }

    const headers = [
      "style_code",
      "article_name",
      "category",
      "department",
      "supplier",
      "store_id",
      "quantity",
      "days",
      "item_mrp",
      "status",
    ];
    const exportValue = (value) => (value === null || value === undefined ? "" : value);
    const rows = state.inventoryResults.map((item) => [
      exportValue(item.style_code),
      exportValue(item.article_name),
      exportValue(item.category),
      exportValue(item.department_name ?? item.department),
      exportValue(item.supplier_name ?? item.supplier),
      exportValue(item.store_id),
      exportValue(item.quantity ?? item.qty),
      exportValue(item.age_days ?? item.days),
      exportValue(item.item_mrp ?? item.mrp),
      exportValue(item.aging_status),
    ]);
    downloadCsv("inventory_search_export.csv", headers, rows);
    showToast("Inventory export ready", "success");
  }

  function setLiveState(enabled) {
    state.live = enabled;
    elements.liveToggle.classList.toggle("off", !enabled);
    elements.liveStatus.textContent = enabled ? "Live feed" : "Paused";
    if (state.liveTimer) {
      window.clearInterval(state.liveTimer);
      state.liveTimer = null;
    }
    if (enabled) {
      void refreshHealth(false);
      state.liveTimer = window.setInterval(() => {
        void refreshData(false);
        void refreshHealth(false);
      }, 60000);
    }
  }

  async function refreshData(showNotice) {
    elements.tableStatus.textContent = "Loading data...";
    try {
      const result = await fetchJsonWithAuth("/dashboard/store-danger-summary", { cache: "no-store" });
      if (result.unauthorized) {
        return;
      }
      if (!result.ok || !result.data) {
        elements.tableStatus.textContent = "Failed to load dashboard data.";
        showToast("Failed to load dashboard data", "error");
        logResultError(result);
        return;
      }
      const data = /** @type {DashboardData} */ (result.data ?? {});
      state.allStores = buildStoreList(data);
      elements.lastUpdated.textContent = data?.date ? String(data.date) : "unknown";
      applyFilters();
      elements.tableStatus.textContent = `Updated ${new Date().toLocaleTimeString()}.`;
      if (showNotice) {
        showToast("Dashboard refreshed", "success");
      }
    } catch (error) {
      elements.tableStatus.textContent = "Failed to load dashboard data.";
      showToast("Failed to load dashboard data", "error");
      console.error(error);
    }
  }

  function resetFilters() {
    state.agingFilters.clear();
    elements.searchInput.value = "";
    document.querySelectorAll("[data-filter-group]").forEach((button) => {
      button.classList.remove("active");
    });
    applyFilters();
  }

  function bindEvents() {
    elements.searchInput.addEventListener("input", applyFilters);

    document.querySelectorAll("[data-filter-group]").forEach((button) => {
      button.addEventListener("click", () => {
        const group = button.dataset.filterGroup;
        const value = button.dataset.filter;
        if (group !== "aging" || !value) return;
        const targetSet = state.agingFilters;
        if (targetSet.has(value)) {
          targetSet.delete(value);
          button.classList.remove("active");
        } else {
          targetSet.add(value);
          button.classList.add("active");
        }
        applyFilters();
      });
    });

    elements.inventoryAlertOnly.addEventListener("click", () => {
      state.inventoryAlertOnly = !state.inventoryAlertOnly;
      elements.inventoryAlertOnly.classList.toggle("active", state.inventoryAlertOnly);
    });

    elements.inventorySearchBtn.addEventListener("click", () => {
      flashAction(elements.inventorySearchBtn);
      void runInventorySearch();
    });

    if (elements.inventoryExportBtn) {
      elements.inventoryExportBtn.addEventListener("click", () => {
        exportInventoryCsv();
      });
    }

    const inventoryKeyHandler = (event) => {
      if (event.key === "Enter") {
        void runInventorySearch();
      }
    };
    elements.inventoryQuery.addEventListener("keydown", inventoryKeyHandler);
    elements.inventoryStore.addEventListener("keydown", inventoryKeyHandler);

    elements.refreshBtn.addEventListener("click", () => {
      flashAction(elements.refreshBtn);
      void refreshData(true);
      void refreshHealth(false);
    });

    elements.exportBtn.addEventListener("click", () => {
      flashAction(elements.exportBtn);
      exportCsv();
    });

    elements.resetBtn.addEventListener("click", () => {
      flashAction(elements.resetBtn);
      resetFilters();
      showToast("Filters cleared", "success");
    });

    elements.liveToggle.addEventListener("click", () => {
      setLiveState(!state.live);
    });

    elements.analyticsLive.addEventListener("click", () => {
      elements.analyticsLive.classList.add("active");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    const seed = readSeedData();
    if (seed) {
      state.allStores = buildStoreList(seed);
      elements.lastUpdated.textContent = seed?.date ? String(seed.date) : "unknown";
      applyFilters();
    } else {
      elements.filterStatus.textContent = "Loading store data...";
      elements.tableStatus.textContent = "Loading store data...";
      void refreshData(false);
    }
    setLiveState(true);
  });
})();
