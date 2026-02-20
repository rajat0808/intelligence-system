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
   * @property {number=} store_count_total
   * @property {number=} store_count_query
   * @property {{HEALTHY:number, TRANSFER:number, RR_TT:number, VERY_DANGER:number}=} status_counts
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
   * @property {string=} image_url
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
   * @typedef {Object} InventoryStatusResponse
   * @property {number=} count
   * @property {boolean=} limited
   * @property {number=} total_count
   * @property {number=} total_qty
   * @property {number=} total_value
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

  /** @type {{ allStores: StoreSummary[], baseStores: StoreSummary[], filteredStores: StoreSummary[], agingFilters: Set<string>, live: boolean, liveTimer: number | null, inventoryAlertOnly: boolean, inventoryResults: InventoryItem[], filterRequestId: number, filterLoading: boolean, inventoryMode: "manual" | "status", inventoryFilterRequestId: number }} */
  const state = {
    allStores: [],
    baseStores: [],
    filteredStores: [],
    agingFilters: new Set(),
    live: true,
    liveTimer: null,
    inventoryAlertOnly: false,
    inventoryResults: [],
    filterRequestId: 0,
    filterLoading: false,
    inventoryMode: "manual",
    inventoryFilterRequestId: 0,
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
    tablePanel: document.getElementById("table-panel"),
    searchInput: document.getElementById("search-input"),
    filtersPanel: document.getElementById("filters-panel"),
    agingHealthy: document.getElementById("aging-healthy"),
    agingTransfer: document.getElementById("aging-transfer"),
    agingRateRevised: document.getElementById("aging-rate-revised"),
    agingVeryDanger: document.getElementById("aging-very-danger"),
    healthInsights: document.getElementById("health-insights"),
    toast: document.getElementById("toast"),
    refreshBtn: document.getElementById("refresh-btn"),
    exportBtn: document.getElementById("export-btn"),
    resetBtn: document.getElementById("reset-btn"),
    applyFiltersBtn: document.getElementById("apply-filters-btn"),
    liveToggle: document.getElementById("live-toggle"),
    liveStatus: document.getElementById("live-status"),
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
    imagePopout: document.getElementById("image-popout"),
    imagePopoutPreview: document.getElementById("image-popout-preview"),
    imagePopoutCaption: document.getElementById("image-popout-caption"),
    imagePopoutClose: document.getElementById("image-popout-close"),
  };

  const numberFormatter = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  let filterDebounceTimer = null;

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
    RR_TT: "Rate revision",
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

  function setFilterLoading(isLoading) {
    state.filterLoading = isLoading;
    if (elements.tablePanel) {
      elements.tablePanel.classList.toggle("loading", isLoading);
    }
    if (isLoading) {
      elements.tableStatus.textContent = "Filtering stores...";
    }
  }

  function updateSummary(stores) {
    const totals = computeTotals(stores);

    elements.storeCount.textContent = formatNumber(totals.count);

    elements.healthyCapital.textContent = formatNumber(totals.aging.HEALTHY);
    elements.transferCapital.textContent = formatNumber(totals.aging.TRANSFER);
    elements.rateRevisedCapital.textContent = formatNumber(totals.aging.RR_TT);
    elements.veryDangerCapital.textContent = formatNumber(totals.aging.VERY_DANGER);

    elements.agingHealthy.textContent = formatNumber(totals.aging.HEALTHY);
    elements.agingTransfer.textContent = formatNumber(totals.aging.TRANSFER);
    elements.agingRateRevised.textContent = formatNumber(totals.aging.RR_TT);
    elements.agingVeryDanger.textContent = formatNumber(totals.aging.VERY_DANGER);

    updateHealthBars(totals);
    updateHealthInsights(totals);
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
      { label: "Avg inventory value per store", value: formatNumber(averageCapital) },
      { label: "Rate revision stores", value: formatNumber(totals.agingCounts.RR_TT) },
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

  function computeStatusCounts(stores) {
    const counts = { HEALTHY: 0, TRANSFER: 0, RR_TT: 0, VERY_DANGER: 0 };
    stores.forEach((store) => {
      if (toNumber(store.aging.HEALTHY) > 0) counts.HEALTHY += 1;
      if (toNumber(store.aging.TRANSFER) > 0) counts.TRANSFER += 1;
      if (toNumber(store.aging.RR_TT) > 0) counts.RR_TT += 1;
      if (toNumber(store.aging.VERY_DANGER) > 0) counts.VERY_DANGER += 1;
    });
    return counts;
  }

  function updateFilterCounts(counts) {
    const source = state.baseStores ?? state.allStores;
    const resolved = counts ?? computeStatusCounts(source);
    document.querySelectorAll("[data-count-for]").forEach((node) => {
      const key = node.dataset.countFor;
      node.textContent = formatNumber(resolved[key] ?? 0);
    });
  }

  function updateAgingFilterButtons() {
    document.querySelectorAll('[data-filter-group="aging"]').forEach((btn) => {
      const value = btn.dataset.filter;
      const active = value ? state.agingFilters.has(value) : false;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setAgingFilters(nextSet) {
    state.agingFilters.clear();
    nextSet.forEach((value) => state.agingFilters.add(value));
    updateAgingFilterButtons();
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

  function buildPillGroup(items, storeId) {
    const wrapper = document.createElement("div");
    wrapper.className = "chip-row";
    let hasValues = false;
    items.forEach((item) => {
      const value = toNumber(item.value);
      if (value <= 0) return;
      hasValues = true;
      if (item.statusKey && storeId !== undefined && storeId !== null) {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = `pill clickable ${item.className}`;
        pill.textContent = `${item.label} ${formatNumber(value)}`;
        pill.dataset.status = item.statusKey;
        pill.dataset.storeId = String(storeId);
        pill.setAttribute("aria-label", `${item.label} items for store ${storeId}`);
        wrapper.appendChild(pill);
      } else {
        wrapper.appendChild(buildPill(`${item.label} ${formatNumber(value)}`, item.className));
      }
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

  function buildStoreBar(store) {
    const bar = document.createElement("div");
    bar.className = "store-bar";
    const segments = [
      { key: "HEALTHY", className: "healthy", label: levelLabels.HEALTHY },
      { key: "TRANSFER", className: "transfer", label: levelLabels.TRANSFER },
      { key: "RR_TT", className: "rate-revised", label: levelLabels.RR_TT },
      { key: "VERY_DANGER", className: "very-danger", label: levelLabels.VERY_DANGER },
    ];
    const total =
      toNumber(store.aging.HEALTHY) +
      toNumber(store.aging.TRANSFER) +
      toNumber(store.aging.RR_TT) +
      toNumber(store.aging.VERY_DANGER);

    if (total <= 0) {
      bar.classList.add("empty");
      const empty = document.createElement("span");
      empty.className = "bar-empty";
      empty.textContent = "No inventory value recorded";
      bar.appendChild(empty);
      return bar;
    }

    const ariaParts = [];
    segments.forEach((segment) => {
      const value = toNumber(store.aging[segment.key]);
      if (value <= 0) return;
      const percent = (value / total) * 100;
      const span = document.createElement("span");
      span.className = `bar-seg ${segment.className}`;
      span.style.width = `${percent.toFixed(2)}%`;
      span.title = `${segment.label}: ${formatNumber(value)}`;
      bar.appendChild(span);
      ariaParts.push(`${segment.label} ${formatNumber(value)}`);
    });
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `Status mix. ${ariaParts.join(", ")}`);
    return bar;
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
      totalCell.dataset.label = "Total inventory value";
      totalCell.textContent = formatNumber(store.totalAging);
      row.appendChild(totalCell);

      const statusCell = document.createElement("td");
      statusCell.className = "status-cell";
      statusCell.dataset.label = "Status mix";
      const stack = document.createElement("div");
      stack.className = "status-stack";
      stack.appendChild(buildStoreBar(store));
      const pills = buildPillGroup([
        {
          label: levelLabels.HEALTHY,
          value: store.aging.HEALTHY,
          className: "healthy",
          statusKey: "HEALTHY",
        },
        {
          label: levelLabels.TRANSFER,
          value: store.aging.TRANSFER,
          className: "transfer",
          statusKey: "TRANSFER",
        },
        {
          label: levelLabels.RR_TT,
          value: store.aging.RR_TT,
          className: "rate-revised",
          statusKey: "RR_TT",
        },
        {
          label: levelLabels.VERY_DANGER,
          value: store.aging.VERY_DANGER,
          className: "very-danger",
          statusKey: "VERY_DANGER",
        },
      ], store.id);
      pills.classList.add("store-pills");
      stack.appendChild(pills);
      statusCell.appendChild(stack);
      row.appendChild(statusCell);

      elements.tableBody.appendChild(row);
    });
  }

  function renderInventoryResults(items) {
    elements.inventoryTableBody.innerHTML = "";

    items.forEach((item) => {
      const row = document.createElement("tr");

      const imageCell = document.createElement("td");
      imageCell.dataset.label = "Image";
      const thumbButton = document.createElement("button");
      thumbButton.type = "button";
      thumbButton.className = "item-thumb-button";
      const image = document.createElement("img");
      image.className = "item-thumb";
      const imageUrl = item.image_url ?? item.image ?? item.thumbnail;
      const fallbackUrl = "/static/sindh-logo.png";
      image.src = imageUrl || fallbackUrl;
      image.alt = item.article_name ?? item.style_code ?? "Item image";
      image.loading = "lazy";
      image.decoding = "async";
      thumbButton.dataset.previewSrc = image.src;
      thumbButton.dataset.previewAlt = image.alt;
      thumbButton.dataset.previewCaption = [item.style_code, item.article_name].filter(Boolean).join(" - ");
      thumbButton.setAttribute("aria-label", "Open image preview");
      image.dataset.previewSrc = thumbButton.dataset.previewSrc;
      image.dataset.previewAlt = thumbButton.dataset.previewAlt;
      image.dataset.previewCaption = thumbButton.dataset.previewCaption;
      thumbButton.addEventListener("click", () => {
        openImagePopout(
          thumbButton.dataset.previewSrc || image.src || fallbackUrl,
          thumbButton.dataset.previewAlt || image.alt || "Inventory image preview",
          thumbButton.dataset.previewCaption || ""
        );
      });
      image.addEventListener("click", () => {
        openImagePopout(
          image.dataset.previewSrc || thumbButton.dataset.previewSrc || image.src || fallbackUrl,
          image.dataset.previewAlt || thumbButton.dataset.previewAlt || image.alt || "Inventory image preview",
          image.dataset.previewCaption || thumbButton.dataset.previewCaption || ""
        );
      });
      image.onerror = () => {
        image.onerror = null;
        image.src = fallbackUrl;
        thumbButton.dataset.previewSrc = fallbackUrl;
        image.dataset.previewSrc = fallbackUrl;
      };
      thumbButton.appendChild(image);
      imageCell.appendChild(thumbButton);
      row.appendChild(imageCell);

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

  function openImagePopout(src, alt, caption) {
    if (!src) {
      return;
    }
    if (!elements.imagePopout || !elements.imagePopoutPreview) {
      window.open(src, "_blank", "noopener,noreferrer");
      return;
    }
    elements.imagePopoutPreview.src = src;
    elements.imagePopoutPreview.alt = alt || "Inventory image preview";
    if (elements.imagePopoutCaption) {
      elements.imagePopoutCaption.textContent = caption || "";
    }
    elements.imagePopout.hidden = false;
    elements.imagePopout.removeAttribute("hidden");
    elements.imagePopout.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
  }

  function closeImagePopout() {
    if (!elements.imagePopout || elements.imagePopout.hidden) {
      return;
    }
    elements.imagePopout.hidden = true;
    elements.imagePopout.setAttribute("hidden", "");
    elements.imagePopout.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    if (elements.imagePopoutPreview) {
      elements.imagePopoutPreview.removeAttribute("src");
    }
  }

  function resetInventoryResults(message) {
    elements.inventoryStatus.textContent = message;
    elements.inventoryTableBody.innerHTML = "";
    elements.inventoryEmpty.hidden = true;
  }

  function computeInventoryTotals(items) {
    let totalQty = 0;
    let totalValue = 0;
    items.forEach((item) => {
      const qty = toNumber(item.quantity ?? item.qty);
      const mrpValue = toNumber(item.item_mrp ?? item.mrp);
      totalQty += qty;
      totalValue += qty * mrpValue;
    });
    return { count: items.length, qty: totalQty, value: totalValue };
  }

  async function runInventorySearch() {
    state.inventoryMode = "manual";
    state.inventoryFilterRequestId += 1;
    const query = elements.inventoryQuery.value.trim();
    const storeId = elements.inventoryStore.value.trim();

    if (query.length < 2 && !storeId) {
      resetInventoryResults("Enter at least 2 characters or a store id to search inventory.");
      return;
    }

    const params = new URLSearchParams();
    if (query) {
      params.set("query", query);
    }
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
      const totals = computeInventoryTotals(results);
      elements.inventoryStatus.textContent = `Found ${data.count ?? results.length} items. Total qty ${formatNumber(
        totals.qty
      )}. Total value ${formatNumber(totals.value)}.`;
    } catch (error) {
      resetInventoryResults("Inventory search failed.");
      console.error(error);
    }
  }

  function formatStatusLabel(status) {
    return levelLabels[status] ?? status;
  }

  async function syncInventoryWithFilters(activeFilters, storeQuery) {
    const storeQueryValue = storeQuery ? storeQuery.trim() : "";
    const hasStatusFilters = activeFilters.length > 0;
    if (!hasStatusFilters && !storeQueryValue) {
      if (state.inventoryMode === "status") {
        resetInventoryResults("Select a status filter to view item details.");
      }
      state.inventoryMode = "manual";
      return;
    }

    const requestId = ++state.inventoryFilterRequestId;
    state.inventoryMode = "status";

    const params = new URLSearchParams();
    if (hasStatusFilters) {
      params.set("status", activeFilters.join(","));
    }
    if (storeQueryValue) {
      if (/^\d+$/.test(storeQueryValue)) {
        params.set("store_id", storeQueryValue);
      } else {
        params.set("query", storeQueryValue);
      }
    }
    params.set("limit", "200");

    elements.inventoryStatus.textContent = "Loading items for selected status...";

    try {
      const result = await fetchJsonWithAuth(`/dashboard/inventory-by-status?${params.toString()}`, {
        cache: "no-store",
      });
      if (requestId !== state.inventoryFilterRequestId) {
        return;
      }
      if (result.unauthorized) {
        return;
      }
      if (!result.ok || !result.data) {
        resetInventoryResults("Failed to load filtered items.");
        logResultError(result);
        return;
      }
      const data = /** @type {InventoryStatusResponse} */ (result.data ?? {});
      const results = Array.isArray(data.results) ? data.results : [];
      state.inventoryResults = results;
      renderInventoryResults(results);
      const labels = hasStatusFilters ? activeFilters.map(formatStatusLabel).join(", ") : "";
      const statusLabel = hasStatusFilters ? `${labels} items` : "items";
      const storePart = storeQueryValue ? ` for stores matching "${storeQueryValue}"` : "";
      const totals = computeInventoryTotals(results);
      const totalCount = Number.isFinite(data.total_count) ? data.total_count : totals.count;
      const totalQty = Number.isFinite(data.total_qty) ? data.total_qty : totals.qty;
      const totalValue = Number.isFinite(data.total_value) ? data.total_value : totals.value;
      const limitedNote = data.limited ? " Showing first 200 items." : "";
      elements.inventoryStatus.textContent = `Found ${totalCount} ${statusLabel}${storePart}. Total qty ${formatNumber(
        totalQty
      )}. Total value ${formatNumber(totalValue)}.${limitedNote}`;
    } catch (error) {
      if (requestId !== state.inventoryFilterRequestId) {
        return;
      }
      resetInventoryResults("Failed to load filtered items.");
      console.error(error);
    }
  }

  function applyLocalFilters(query) {
    const agingActive = state.agingFilters.size > 0;
    const queryIsNumeric = !!query && /^\d+$/.test(query);
    return state.allStores.filter((store) => {
      if (query) {
        const storeText = store.id.toLowerCase();
        if (queryIsNumeric) {
          if (storeText !== query) {
            return false;
          }
        } else if (!storeText.includes(query)) {
          return false;
        }
      }
      if (agingActive) {
        const matchesAging = Array.from(state.agingFilters).some(
          (level) => toNumber(store.aging[level]) > 0
        );
        if (!matchesAging) return false;
      }
      return true;
    });
  }

  async function applyFilters() {
    const queryValue = elements.searchInput.value.trim();
    const query = queryValue.toLowerCase();
    const activeFilters = Array.from(state.agingFilters);
    const hasFilters = activeFilters.length > 0 || !!query;
    const requestId = ++state.filterRequestId;

    if (!hasFilters) {
      setFilterLoading(false);
      state.baseStores = [...state.allStores];
      state.filteredStores = [...state.allStores];
      renderTable(state.filteredStores);
      const totals = computeTotals(state.filteredStores);
      updateSummary(state.filteredStores);
      updateFilterCounts();

      const totalCount = state.allStores.length;
      const filteredCount = state.filteredStores.length;
      const statusParts = [
        `Showing ${filteredCount} of ${totalCount} stores`,
        `Total value ${formatNumber(totals.aging.total)}`,
      ];
      elements.filterStatus.textContent = statusParts.join(". ") + ".";
      elements.tableStatus.textContent = filteredCount === 0 ? "No stores match the current filters." : "Ready.";

      elements.emptyState.hidden = filteredCount !== 0;
      elements.filtersPanel.classList.toggle("filters-open", false);
      void syncInventoryWithFilters(activeFilters, queryValue);
      return;
    }

    setFilterLoading(true);
    elements.filterStatus.textContent = "Filtering stores...";

    const params = new URLSearchParams();
    if (queryValue) params.set("query", queryValue);
    if (activeFilters.length) params.set("status", activeFilters.join(","));

    const result = await fetchJsonWithAuth(`/dashboard/store-danger-summary?${params.toString()}`, {
      cache: "no-store",
    });

    if (requestId !== state.filterRequestId) {
      return;
    }

    setFilterLoading(false);

    if (result.unauthorized) {
      return;
    }

    if (!result.ok || !result.data) {
      const fallback = applyLocalFilters(query);
      state.baseStores = fallback;
      state.filteredStores = fallback;
      renderTable(state.filteredStores);
      const totals = computeTotals(state.filteredStores);
      updateSummary(state.filteredStores);
      updateFilterCounts();
      const totalCount = state.allStores.length;
      const filteredCount = state.filteredStores.length;
      const statusParts = [
        `Showing ${filteredCount} of ${totalCount} stores`,
        `Total value ${formatNumber(totals.aging.total)}`,
      ];
      if (activeFilters.length) statusParts.push(`${activeFilters.length} status tags active`);
      if (query) statusParts.push("Search active");
      elements.filterStatus.textContent = statusParts.join(". ") + ".";
      elements.tableStatus.textContent =
        filteredCount === 0 ? "No stores match the current filters." : "Showing cached results.";
      elements.emptyState.hidden = filteredCount !== 0;
      elements.filtersPanel.classList.toggle("filters-open", true);
      showToast("Filters failed, showing cached data", "error");
      logResultError(result);
      void syncInventoryWithFilters(activeFilters, queryValue);
      return;
    }

    const data = result.data ?? {};
    const stores = buildStoreList(data);
    state.baseStores = stores;
    state.filteredStores = stores;
    renderTable(stores);
    const totals = computeTotals(stores);
    updateSummary(stores);
    updateFilterCounts(data.status_counts);

    const totalCount = Number.isFinite(data.store_count_total)
      ? data.store_count_total
      : state.allStores.length;
    const queryCount = Number.isFinite(data.store_count_query) ? data.store_count_query : totalCount;
    const filteredCount = stores.length;
    const statusParts = [
      `Showing ${filteredCount} of ${query ? queryCount : totalCount} stores`,
      `Total value ${formatNumber(totals.aging.total)}`,
    ];
    if (activeFilters.length) statusParts.push(`${activeFilters.length} status tags active`);
    if (query) statusParts.push("Search active");
    elements.filterStatus.textContent = statusParts.join(". ") + ".";
    elements.tableStatus.textContent = filteredCount === 0 ? "No stores match the current filters." : "Ready.";

    elements.emptyState.hidden = filteredCount !== 0;
    elements.filtersPanel.classList.toggle("filters-open", true);
    void syncInventoryWithFilters(activeFilters, queryValue);
  }

  function scheduleApplyFilters() {
    if (filterDebounceTimer) {
      window.clearTimeout(filterDebounceTimer);
    }
    filterDebounceTimer = window.setTimeout(() => {
      void applyFilters();
    }, 220);
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
      void applyFilters();
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
    setAgingFilters(new Set());
    elements.searchInput.value = "";
    void applyFilters();
  }

  function bindEvents() {
    elements.searchInput.addEventListener("input", scheduleApplyFilters);

    document.querySelectorAll("[data-filter-group]").forEach((button) => {
      button.addEventListener("click", (event) => {
        const group = button.dataset.filterGroup;
        const value = button.dataset.filter;
        if (group !== "aging" || !value) return;
        const isMulti = event.shiftKey || event.ctrlKey || event.metaKey;
        const alreadyActive = state.agingFilters.has(value);

        if (!isMulti) {
          if (alreadyActive) {
            setAgingFilters(new Set());
            scheduleApplyFilters();
            return;
          }
          setAgingFilters(new Set([value]));
          scheduleApplyFilters();
          return;
        }

        const nextSet = new Set(state.agingFilters);
        if (alreadyActive) {
          nextSet.delete(value);
        } else {
          nextSet.add(value);
        }
        setAgingFilters(nextSet);
        scheduleApplyFilters();
      });
    });

    if (elements.applyFiltersBtn) {
      elements.applyFiltersBtn.addEventListener("click", () => {
        flashAction(elements.applyFiltersBtn);
        void applyFilters();
      });
    }

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

    if (elements.inventoryTableBody) {
      elements.inventoryTableBody.addEventListener("click", (event) => {
        const trigger = event.target.closest(".item-thumb-button, .item-thumb");
        if (!trigger) return;
        const src = trigger.dataset.previewSrc || trigger.getAttribute("src");
        if (!src) return;
        openImagePopout(
          src,
          trigger.dataset.previewAlt || trigger.getAttribute("alt") || "Inventory image preview",
          trigger.dataset.previewCaption || ""
        );
      });
    }

    if (elements.imagePopout) {
      elements.imagePopout.addEventListener("click", (event) => {
        if (event.target === elements.imagePopout) {
          closeImagePopout();
        }
      });
    }
    if (elements.imagePopoutClose) {
      elements.imagePopoutClose.addEventListener("click", () => {
        closeImagePopout();
      });
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeImagePopout();
      }
    });

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

    if (elements.tableBody) {
      elements.tableBody.addEventListener("click", (event) => {
        const pill = event.target.closest(".pill[data-status][data-store-id]");
        if (!pill) return;
        const status = pill.dataset.status;
        const storeId = pill.dataset.storeId;
        if (!status || !storeId) return;
        elements.searchInput.value = storeId;
        elements.inventoryStore.value = storeId;
        setAgingFilters(new Set([status]));
        scheduleApplyFilters();
      });
    }

    elements.liveToggle.addEventListener("click", () => {
      setLiveState(!state.live);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    const seed = readSeedData();
    if (seed) {
      state.allStores = buildStoreList(seed);
      elements.lastUpdated.textContent = seed?.date ? String(seed.date) : "unknown";
      void applyFilters();
    } else {
      elements.filterStatus.textContent = "Loading store data...";
      elements.tableStatus.textContent = "Loading store data...";
      void refreshData(false);
    }
    setLiveState(true);
  });
})();
