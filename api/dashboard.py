from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from app.database import engine
from app.intelligence.aging_rules import classify_status_with_default
from app.intelligence.danger_rules import calculate_age_in_days, danger_level

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SUPPLYSETU Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" cross origin>
    <link
      href="https://fonts.googleapis.com/css2?family=Frances:wght@500;700&family=Sora:wght@300;400;600&display=swap"
      rel="stylesheet"
    >
    <style>
      :root {
        --sage-400: #ACC82A;
        --olive-900: #1A2517;
        --ink-900: var(--olive-900);
        --ink-700: rgba(26, 37, 23, 0.82);
        --ink-500: rgba(26, 37, 23, 0.62);
        --sand-100: #f9fbf2;
        --sand-200: #f1f5e2;
        --mist-100: #edf2dc;
        --mint-400: var(--sage-400);
        --mint-600: var(--olive-900);
        --coral-500: var(--sage-400);
        --sun-400: var(--sage-400);
        --steel-400: rgba(26, 37, 23, 0.45);
        --white: #ffffff;
        --shadow: 0 20px 45px rgba(26, 37, 23, 0.18);
        --shadow-soft: 0 12px 28px rgba(26, 37, 23, 0.12);
        --radius-lg: 22px;
        --radius-md: 16px;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Sora", "Noto Sans", sans-serif;
        color: var(--ink-900);
        background:
          radial-gradient(1100px 560px at 10% -10%, #f6f9e6 0, transparent 55%),
          radial-gradient(900px 520px at 110% 10%, #eef4d8 0, transparent 50%),
          linear-gradient(180deg, var(--sand-100) 0%, var(--mist-100) 100%);
        position: relative;
      }

      body::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
          radial-gradient(rgba(26, 37, 23, 0.05) 1px, transparent 0),
          radial-gradient(rgba(26, 37, 23, 0.04) 1px, transparent 0);
        background-size: 22px 22px, 28px 28px;
        background-position: 0 0, 7px 9px;
        pointer-events: none;
        opacity: 0.6;
      }

      .page {
        position: relative;
        z-index: 1;
        padding: 32px 20px 60px;
        max-width: 1200px;
        margin: 0 auto;
      }

      header {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 28px;
      }

      .title {
        display: grid;
        gap: 6px;
      }

      h1 {
        font-family: "Frances", "Georgia", serif;
        font-size: clamp(28px, 4vw, 40px);
        margin: 0;
        color: var(--ink-900);
      }

      .subtitle {
        color: var(--ink-500);
        font-size: 14px;
        letter-spacing: 0.4px;
        text-transform: uppercase;
      }

      .controls {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
      }

      .chip {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(26, 37, 23, 0.18);
        padding: 10px 16px;
        border-radius: 999px;
        font-size: 13px;
        color: var(--ink-700);
        box-shadow: var(--shadow-soft);
      }

      .button {
        border: none;
        padding: 12px 18px;
        border-radius: 999px;
        background: var(--sage-400);
        color: var(--olive-900);
        font-weight: 600;
        cursor: pointer;
        box-shadow: var(--shadow-soft);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }

      .button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow);
      }

      .button-outline {
        background: var(--white);
        color: var(--ink-900);
        border: 1px solid rgba(26, 37, 23, 0.24);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 18px;
        margin-bottom: 28px;
      }

      .card {
        background: rgba(255, 255, 255, 0.92);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(26, 37, 23, 0.12);
        animation: floatUp 0.7s ease both;
        animation-delay: var(--delay, 0ms);
      }

      .card h2 {
        margin: 0 0 6px 0;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--ink-500);
      }

      .card .value {
        font-size: clamp(22px, 3vw, 28px);
        font-weight: 600;
      }

      .card .note {
        margin-top: 8px;
        font-size: 13px;
        color: var(--ink-500);
      }

      .section {
        display: grid;
        gap: 16px;
      }

      .panel {
        background: rgba(255, 255, 255, 0.94);
        border-radius: var(--radius-lg);
        padding: 18px 20px 6px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(26, 37, 23, 0.12);
      }

      .panel header {
        margin-bottom: 14px;
      }

      .panel-title {
        font-family: "Frances", "Georgia", serif;
        font-size: 20px;
        margin: 0;
      }

      .panel-sub {
        color: var(--ink-500);
        margin-top: 4px;
        font-size: 13px;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }

      thead th {
        text-align: left;
        padding: 12px 10px;
        font-size: 12px;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        color: var(--ink-500);
        border-bottom: 1px solid rgba(26, 37, 23, 0.2);
      }

      tbody td {
        padding: 12px 10px;
        border-bottom: 1px solid rgba(26, 37, 23, 0.12);
      }

      tbody tr:hover {
        background: rgba(172, 200, 42, 0.12);
      }

      .store-id {
        font-weight: 600;
        color: var(--ink-700);
      }

      .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
      }

      .pill.early {
        background: rgba(172, 200, 42, 0.2);
        color: var(--olive-900);
      }

      .pill.high {
        background: rgba(172, 200, 42, 0.35);
        color: var(--olive-900);
      }

      .pill.critical {
        background: var(--olive-900);
        color: var(--sand-100);
      }

      .pill.none {
        background: rgba(26, 37, 23, 0.08);
        color: var(--ink-700);
      }

      .pill.healthy {
        background: rgba(172, 200, 42, 0.18);
        color: var(--olive-900);
      }

      .pill.transfer {
        background: rgba(172, 200, 42, 0.32);
        color: var(--olive-900);
      }

      .pill.rr-tt {
        background: rgba(26, 37, 23, 0.16);
        color: var(--olive-900);
      }

      .pill.very-danger {
        background: var(--olive-900);
        color: var(--sand-100);
      }

      .pill.unknown {
        background: rgba(26, 37, 23, 0.08);
        color: var(--ink-700);
      }

      .search {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }

      .search-input {
        border: 1px solid rgba(26, 37, 23, 0.24);
        border-radius: 999px;
        padding: 10px 14px;
        font-size: 13px;
        min-width: 220px;
        background: var(--white);
        color: var(--ink-900);
      }

      .total {
        font-weight: 600;
        color: var(--ink-900);
      }

      .status {
        margin-top: 12px;
        font-size: 13px;
        color: var(--ink-500);
      }

      .empty {
        padding: 24px;
        text-align: center;
        color: var(--ink-500);
      }

      @keyframes floatUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
      }

      @media (max-width: 680px) {
        header {
          flex-direction: column;
          align-items: flex-start;
        }
        .controls {
          width: 100%;
          justify-content: space-between;
        }
        .search {
          width: 100%;
        }
        .search-input {
          width: 100%;
        }
        table, thead, tbody, th, td, tr {
          display: block;
        }
        thead {
          display: none;
        }
        tbody tr {
          margin-bottom: 16px;
          border-radius: var(--radius-md);
          background: var(--white);
          box-shadow: var(--shadow-soft);
        }
        tbody td {
          border: none;
          padding: 10px 14px;
          display: flex;
          justify-content: space-between;
        }
        tbody td::before {
          content: attr(data-label);
          color: var(--ink-500);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
      }
    </style>
  </head>
  <body>
    <div class="page">
      <header>
        <div class="title">
          <div class="subtitle">SINDH FASHION</div>
          <h1>SINDH FASHION</h1>
        </div>
        <div class="controls">
          <div class="chip" id="as-of">As of --</div>
          <button class="button" id="refresh">Refresh</button>
        </div>
      </header>

      <section class="grid">
        <div class="card" style="--delay: 0ms;">
          <h2>Total Danger Capital</h2>
          <div class="value" id="summary-total">INR --</div>
          <div class="note">Only EARLY, HIGH, CRITICAL inventory</div>
        </div>
        <div class="card" style="--delay: 120ms;">
          <h2>Stores in Alert Zone</h2>
          <div class="value" id="summary-count">--</div>
          <div class="note">Stores with any alert-visible stock</div>
        </div>
        <div class="card" style="--delay: 240ms;">
          <h2>Most Exposed Store</h2>
          <div class="value" id="summary-top">--</div>
          <div class="note" id="summary-top-note">Waiting for data</div>
        </div>
      </section>

      <section class="section">
        <div class="panel">
          <header>
            <div>
              <h3 class="panel-title">Store Breakdown</h3>
              <div class="panel-sub">Capital by danger tier, sorted by total exposure.</div>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Store</th>
                <th>Early</th>
                <th>High</th>
                <th>Critical</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody id="store-rows">
              <tr><td class="empty" colspan="5">Loading data...</td></tr>
            </tbody>
          </table>
          <div class="status" id="status">Fetching latest data.</div>
        </div>

        <div class="panel">
          <header>
            <div>
              <h3 class="panel-title">Aging Status Summary</h3>
              <div class="panel-sub">Capital by aging status across all inventory.</div>
            </div>
            <div class="search">
              <input class="search-input" id="aging-search-input" placeholder="Filter by store ID" />
              <button class="button button-outline" id="aging-search-button">Filter</button>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Store</th>
                <th>Healthy</th>
                <th>Transfer</th>
                <th>RR_TT</th>
                <th>VERY_DANGER</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody id="aging-rows">
              <tr><td class="empty" colspan="6">Loading data...</td></tr>
            </tbody>
          </table>
          <div class="status" id="aging-status">Fetching latest data.</div>
        </div>

        <div class="panel">
          <header>
            <div>
              <h3 class="panel-title">Inventory Search</h3>
              <div class="panel-sub">Search by style code or article name.</div>
            </div>
            <div class="search">
              <input class="search-input" id="search-input" placeholder="Search inventory" />
              <button class="button button-outline" id="search-button">Search</button>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Style</th>
                <th>Article</th>
                <th>Category</th>
                <th>Department</th>
                <th>Supplier</th>
                <th>Store</th>
                <th>Qty</th>
                <th>Days</th>
                <th>Item MRP</th>
                <th>Aging</th>
                <th>Danger</th>
              </tr>
            </thead>
            <tbody id="search-rows">
              <tr><td class="empty" colspan="11">Enter a query to search inventory.</td></tr>
            </tbody>
          </table>
          <div class="status" id="search-status">Waiting for query.</div>
        </div>
      </section>
    </div>

    <script>
      const formatCurrency = new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      });

      const formatDate = (value) => {
        if (!value) return "--";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString("en-IN", {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      };

      let agingCache = [];

      const renderEmpty = (message) => {
        const tbody = document.getElementById("store-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="5">${message}</td></tr>`;
      };

      const renderTable = (rows) => {
        const tbody = document.getElementById("store-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="store-id" data-label="Store">Store ${row.store_id}</td>
            <td data-label="Early"><span class="pill early">EARLY</span>${formatCurrency.format(row.EARLY || 0)}</td>
            <td data-label="High"><span class="pill high">HIGH</span>${formatCurrency.format(row.HIGH || 0)}</td>
            <td data-label="Critical"><span class="pill critical">CRITICAL</span>${formatCurrency.format(row.CRITICAL || 0)}</td>
            <td class="total" data-label="Total">${formatCurrency.format(row.total_danger_capital || 0)}</td>
          `;
          tbody.appendChild(tr);
        });
      };

      const renderAgingEmpty = (message) => {
        const tbody = document.getElementById("aging-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="6">${message}</td></tr>`;
      };

      const renderAgingTable = (rows) => {
        const tbody = document.getElementById("aging-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="store-id" data-label="Store">Store ${row.store_id}</td>
            <td data-label="Healthy"><span class="pill healthy">HEALTHY</span>${formatCurrency.format(row.HEALTHY || 0)}</td>
            <td data-label="Transfer"><span class="pill transfer">TRANSFER</span>${formatCurrency.format(row.TRANSFER || 0)}</td>
            <td data-label="RR_TT"><span class="pill rr-tt">RR_TT</span>${formatCurrency.format(row.RR_TT || 0)}</td>
            <td data-label="VERY_DANGER"><span class="pill very-danger">VERY_DANGER</span>${formatCurrency.format(row.VERY_DANGER || 0)}</td>
            <td class="total" data-label="Total">${formatCurrency.format(row.total_aging_capital || 0)}</td>
          `;
          tbody.appendChild(tr);
        });
      };

      const applyAgingFilter = () => {
        const input = document.getElementById("aging-search-input");
        const status = document.getElementById("aging-status");
        const query = input.value.trim().toLowerCase();

        if (!agingCache || agingCache.length === 0) {
          renderAgingEmpty("No inventory found.");
          status.textContent = "No inventory found.";
          return;
        }

        const filtered = query
          ? agingCache.filter((row) => String(row.store_id).toLowerCase().includes(query))
          : agingCache;

        if (filtered.length === 0) {
          renderAgingEmpty("No matches found.");
          status.textContent = "No matching stores.";
          return;
        }

        renderAgingTable(filtered);
        status.textContent = query
          ? `Showing ${filtered.length} stores for "${query}".`
          : "Latest aging summary loaded.";
      };

      const renderSearchEmpty = (message) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="11">${message}</td></tr>`;
      };

      const renderSearchTable = (rows) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const level = row.danger_level || "NONE";
          const levelClass = level === "NONE" ? "none" : level.toLowerCase();
          const aging = row.aging_status || "UNKNOWN";
          const agingClass = aging === "UNKNOWN" ? "unknown" : aging.toLowerCase().replace(/_/g, "-");
          const categoryName = row.category_name || row.category || "--";
          const departmentName = row.department_name || "--";
          const supplierName = row.supplier_name ? row.supplier_name : "--";
          const ageDays = row.age_days == null ? "--" : row.age_days;
          let itemMrp = row.item_mrp;
          if (itemMrp == null) {
            itemMrp = row.mrp;
          }
          const itemMrpLabel = itemMrp == null ? "--" : formatCurrency.format(itemMrp);
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td data-label="Style">${row.style_code}</td>
            <td data-label="Article">${row.article_name}</td>
            <td data-label="Category">${categoryName}</td>
            <td data-label="Department">${departmentName}</td>
            <td data-label="Supplier">${supplierName}</td>
            <td data-label="Store">Store ${row.store_id}</td>
            <td data-label="Qty">${row.quantity}</td>
            <td data-label="Days">${ageDays}</td>
            <td data-label="Item MRP">${itemMrpLabel}</td>
            <td data-label="Aging"><span class="pill ${agingClass}">${aging}</span></td>
            <td data-label="Danger"><span class="pill ${levelClass}">${level}</span></td>
          `;
          tbody.appendChild(tr);
        });
      };

      const updateSummary = (data) => {
        const total = data.results.reduce((acc, row) => acc + (row.total_danger_capital || 0), 0);
        document.getElementById("summary-total").textContent = formatCurrency.format(total);
        document.getElementById("summary-count").textContent = data.store_count;
        document.getElementById("as-of").textContent = `As of ${formatDate(data.date)}`;

        if (data.results.length > 0) {
          const top = [...data.results].sort((a, b) => b.total_danger_capital - a.total_danger_capital)[0];
          document.getElementById("summary-top").textContent = `Store ${top.store_id}`;
          document.getElementById("summary-top-note").textContent = `${formatCurrency.format(top.total_danger_capital)} at risk`;
        } else {
          document.getElementById("summary-top").textContent = "--";
          document.getElementById("summary-top-note").textContent = "No alert-visible inventory";
        }
      };

      const loadDashboard = async () => {
        const status = document.getElementById("status");
        const agingStatus = document.getElementById("aging-status");
        status.textContent = "Refreshing data...";
        agingStatus.textContent = "Refreshing data...";
        try {
          const response = await fetch("store-danger-summary");
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data = await response.json();
          if (!data.results || data.results.length === 0) {
            renderEmpty("No alert-visible inventory found.");
          } else {
            const sorted = [...data.results].sort(
              (a, b) => b.total_danger_capital - a.total_danger_capital
            );
            renderTable(sorted);
          }

          agingCache = [...(data.aging_results || [])].sort(
            (a, b) => b.total_aging_capital - a.total_aging_capital
          );
          applyAgingFilter();
          updateSummary(data);
          status.textContent = "Latest data loaded.";
        } catch (error) {
          renderEmpty("Unable to load data. Check the API and try again.");
          status.textContent = `Error: ${error.message}`;
          renderAgingEmpty("Unable to load data. Check the API and try again.");
          agingStatus.textContent = `Error: ${error.message}`;
        }
      };

      const searchInventory = async () => {
        const input = document.getElementById("search-input");
        const status = document.getElementById("search-status");
        const query = input.value.trim();

        if (query.length < 2) {
          renderSearchEmpty("Enter at least 2 characters.");
          status.textContent = "Waiting for query.";
          return;
        }

        status.textContent = "Searching...";
        try {
          const response = await fetch(`/search/inventory?query=${encodeURIComponent(query)}`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data = await response.json();
          if (!data.results || data.results.length === 0) {
            renderSearchEmpty("No matches found.");
          } else {
            renderSearchTable(data.results);
          }
          status.textContent = `Found ${data.count} items.`;
        } catch (error) {
          renderSearchEmpty("Search failed. Check the API and try again.");
          status.textContent = `Error: ${error.message}`;
        }
      };

      document.getElementById("refresh").addEventListener("click", loadDashboard);
      document.getElementById("aging-search-button").addEventListener("click", applyAgingFilter);
      document.getElementById("search-button").addEventListener("click", searchInventory);
      document.getElementById("aging-search-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          applyAgingFilter();
        }
      });
      document.getElementById("search-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          searchInventory();
        }
      });
      loadDashboard();
    </script>
  </body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def dashboard_page():
    return HTMLResponse(_DASHBOARD_HTML)


@router.get("/store-danger-summary")
def store_wise_danger_summary():
    """
    Store-wise capital summary for ALERT-VISIBLE inventory only
    (EARLY / HIGH / CRITICAL), plus aging status across all inventory.
    """

    # noinspection SqlNoDataSourceInspection
    sql = text("""
        SELECT
            i.store_id,
            i.quantity,
            i.cost_price,
            i.lifecycle_start_date,
            p.category
        FROM inventory i
        LEFT JOIN products p ON p.id = i.product_id
    """)

    today = date.today()
    danger_summary = {}
    aging_summary = {}

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    for row in rows:
        store_id = row["store_id"]
        capital = row["quantity"] * row["cost_price"]
        level = danger_level(row["lifecycle_start_date"])

        # =========================
        # ONLY ALERT-VISIBLE ITEMS
        # =========================
        if level is not None:
            if store_id not in danger_summary:
                danger_summary[store_id] = {
                    "store_id": store_id,
                    "EARLY": 0.0,
                    "HIGH": 0.0,
                    "CRITICAL": 0.0,
                    "total_danger_capital": 0.0,
                }

            danger_summary[store_id][level] += capital
            danger_summary[store_id]["total_danger_capital"] += capital

        age_days = calculate_age_in_days(row["lifecycle_start_date"])
        if age_days is None:
            continue

        # Aging status uses category rules with default thresholds for unknown categories.
        aging_status = classify_status_with_default(row["category"], age_days)

        if store_id not in aging_summary:
            aging_summary[store_id] = {
                "store_id": store_id,
                "HEALTHY": 0.0,
                "TRANSFER": 0.0,
                "RR_TT": 0.0,
                "VERY_DANGER": 0.0,
                "total_aging_capital": 0.0,
            }

        aging_summary[store_id][aging_status] += capital
        aging_summary[store_id]["total_aging_capital"] += capital

    return {
        "date": today,
        "store_count": len(danger_summary),
        "results": list(danger_summary.values()),
        "aging_results": list(aging_summary.values()),
    }
