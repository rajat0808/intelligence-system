from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from datetime import date
from app.database import engine
from app.intelligence.danger_rules import danger_level

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SINDH Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" cross origin>
    <link
      href="https://fonts.googleapis.com/css2?family=Frances:wght@500;700&family=Sora:wght@300;400;600&display=swap"
      rel="stylesheet"
    >
    <style>
      :root {
        --ink-900: #111111;
        --ink-700: #2b2b2b;
        --ink-500: #4a4a4a;
        --sand-100: #ffffff;
        --sand-200: #f4f4f4;
        --mist-100: #ededed;
        --mint-400: #1f1f1f;
        --mint-600: #000000;
        --coral-500: #2f2f2f;
        --sun-400: #3a3a3a;
        --steel-400: #5a5a5a;
        --white: #ffffff;
        --shadow: 0 20px 45px rgba(0, 0, 0, 0.18);
        --shadow-soft: 0 12px 28px rgba(0, 0, 0, 0.1);
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
          radial-gradient(1100px 560px at 10% -10%, #f5f5f5 0, transparent 55%),
          radial-gradient(900px 520px at 110% 10%, #e9e9e9 0, transparent 50%),
          linear-gradient(180deg, var(--sand-100) 0%, var(--mist-100) 100%);
        position: relative;
      }

      body::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
          radial-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 0),
          radial-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 0);
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
        border: 1px solid rgba(46, 65, 60, 0.12);
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
        background: var(--ink-900);
        color: var(--white);
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
        border: 1px solid rgba(0, 0, 0, 0.2);
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
        border: 1px solid rgba(46, 65, 60, 0.08);
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
        border: 1px solid rgba(46, 65, 60, 0.08);
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
        border-bottom: 1px solid rgba(46, 65, 60, 0.12);
      }

      tbody td {
        padding: 12px 10px;
        border-bottom: 1px solid rgba(46, 65, 60, 0.08);
      }

      tbody tr:hover {
        background: rgba(45, 138, 120, 0.06);
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
        background: rgba(0, 0, 0, 0.08);
        color: var(--ink-900);
      }

      .pill.high {
        background: rgba(0, 0, 0, 0.16);
        color: var(--ink-900);
      }

      .pill.critical {
        background: rgba(0, 0, 0, 0.24);
        color: var(--ink-900);
      }

      .pill.none {
        background: rgba(0, 0, 0, 0.04);
        color: var(--ink-700);
      }

      .search {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }

      .search-input {
        border: 1px solid rgba(0, 0, 0, 0.18);
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
          <div class="subtitle">SINDH</div>
          <h1>SINDH Store Danger Dashboard</h1>
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
                <th>Store</th>
                <th>Qty</th>
                <th>Danger</th>
              </tr>
            </thead>
            <tbody id="search-rows">
              <tr><td class="empty" colspan="5">Enter a query to search inventory.</td></tr>
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

      const renderSearchEmpty = (message) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="5">${message}</td></tr>`;
      };

      const renderSearchTable = (rows) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const level = row.danger_level || "NONE";
          const levelClass = level === "NONE" ? "none" : level.toLowerCase();
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td data-label="Style">${row.style_code}</td>
            <td data-label="Article">${row.article_name}</td>
            <td data-label="Store">Store ${row.store_id}</td>
            <td data-label="Qty">${row.quantity}</td>
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
        status.textContent = "Refreshing data...";
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
          updateSummary(data);
          status.textContent = "Latest data loaded.";
        } catch (error) {
          renderEmpty("Unable to load data. Check the API and try again.");
          status.textContent = `Error: ${error.message}`;
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
      document.getElementById("search-button").addEventListener("click", searchInventory);
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
    (EARLY / HIGH / CRITICAL)
    """

    sql = text("""
        SELECT
            i.store_id,
            i.quantity,
            i.cost_price,
            i.lifecycle_start_date
        FROM inventory i
    """)

    today = date.today()
    summary = {}

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    for row in rows:
        level = danger_level(row["lifecycle_start_date"])

        # =========================
        # ONLY ALERT-VISIBLE ITEMS
        # =========================
        if level is None:
            continue

        store_id = row["store_id"]
        capital = row["quantity"] * row["cost_price"]

        if store_id not in summary:
            summary[store_id] = {
                "store_id": store_id,
                "EARLY": 0.0,
                "HIGH": 0.0,
                "CRITICAL": 0.0,
                "total_danger_capital": 0.0,
            }

        summary[store_id][level] += capital
        summary[store_id]["total_danger_capital"] += capital

    return {
        "date": today,
        "store_count": len(summary),
        "results": list(summary.values()),
    }
