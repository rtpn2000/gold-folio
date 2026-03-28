const currency = {
  usd: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }),
  inr: new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }),
};

// Small helper for all API calls used by the dashboard.
async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed: ${response.status}`);
  }
  return response.json();
}

function formatChange(value, formatter) {
  if (value === null || value === undefined) {
    return "No change data yet";
  }
  const className = value > 0 ? "up" : value < 0 ? "down" : "";
  const prefix = value > 0 ? "+" : "";
  return `<span class="${className}">${prefix}${formatter.format(value)} vs previous record</span>`;
}

// Draws a simple SVG line chart for history and forecast data.
function drawLineChart(svg, values, color) {
  const width = 800;
  const height = 320;
  const padX = 26;
  const padY = 24;

  if (!values.length) {
    svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#6f6257" font-size="18">No data available</text>`;
    return;
  }

  const nums = values.map((item) => item.value);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;

  const points = values.map((item, index) => {
    const x = padX + (index / Math.max(values.length - 1, 1)) * (width - padX * 2);
    const y = height - padY - ((item.value - min) / span) * (height - padY * 2);
    return `${x},${y}`;
  }).join(" ");

  const areaPoints = `${padX},${height - padY} ${points} ${width - padX},${height - padY}`;
  const finalPoint = values[values.length - 1];

  svg.innerHTML = `
    <defs>
      <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity="0.34"></stop>
        <stop offset="100%" stop-color="${color}" stop-opacity="0.03"></stop>
      </linearGradient>
    </defs>
    <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="rgba(99,77,54,0.18)" stroke-width="1"></line>
    <polygon points="${areaPoints}" fill="url(#chartFill)"></polygon>
    <polyline points="${points}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
    <circle cx="${padX + ((values.length - 1) / Math.max(values.length - 1, 1)) * (width - padX * 2)}" cy="${height - padY - ((finalPoint.value - min) / span) * (height - padY * 2)}" r="5" fill="${color}"></circle>
  `;
}

// Renders the latest stored rows into the table at the bottom of the page.
function renderTable(items) {
  const tbody = document.getElementById("historyTable");
  tbody.innerHTML = "";

  items.slice(-10).reverse().forEach((item) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.date}</td>
      <td>${item.price_per_gram_usd == null ? "--" : currency.usd.format(item.price_per_gram_usd)}</td>
      <td>${item.price_per_gram_inr == null ? "--" : currency.inr.format(item.price_per_gram_inr)}</td>
    `;
    tbody.appendChild(row);
  });
}

// Loads the top summary cards.
async function loadSummary() {
  const summary = await fetchJson("/api/summary");
  const latest = summary.latest;

  document.getElementById("historyCount").textContent = String(summary.history_points);
  document.getElementById("usdPrice").textContent = latest ? currency.usd.format(latest.price_per_gram_usd) : "--";
  document.getElementById("inrPrice").textContent = latest && latest.price_per_gram_inr != null ? currency.inr.format(latest.price_per_gram_inr) : "--";
  document.getElementById("latestDate").textContent = latest ? `Latest record: ${latest.date}` : "No records loaded";
  document.getElementById("usdChange").innerHTML = formatChange(summary.change.usd, currency.usd);
  document.getElementById("inrChange").innerHTML = formatChange(summary.change.inr, currency.inr);
}

// Loads the historical chart and recent table data.
async function loadHistory() {
  const days = document.getElementById("historyWindow").value;
  const data = await fetchJson(`/api/history?days=${days}`);
  drawLineChart(
    document.getElementById("historyChart"),
    data.items.map((item) => ({ label: item.date, value: item.price_per_gram_usd })),
    "#b8860b"
  );
  renderTable(data.items);
}

// Loads the ARIMA forecast if a trained model artifact exists.
async function loadForecast() {
  const result = await fetchJson("/api/forecast?days=30");
  const status = document.getElementById("forecastStatus");

  if (result.error) {
    status.textContent = result.error;
    drawLineChart(document.getElementById("forecastChart"), [], "#7c5a08");
    return;
  }

  status.textContent = "Forecast generated from the saved ARIMA model artifact.";
  drawLineChart(
    document.getElementById("forecastChart"),
    result.items.map((item) => ({ label: item.date, value: item.price })),
    "#7c5a08"
  );
}

// Refreshes live pricing via the aggregation endpoint, then reloads the dashboard.
async function refreshAggregation() {
  const status = document.getElementById("refreshStatus");
  status.textContent = "Fetching fresh gold prices and saving them.";

  try {
    const result = await fetchJson("/aggregate");
    status.textContent = `Saved ${result.rows} row(s). Sources: ${result.sources.join(", ") || "n/a"}.`;
    await Promise.all([loadSummary(), loadHistory(), loadForecast()]);
  } catch (error) {
    status.textContent = `Refresh failed: ${error.message}`;
  }
}

// Dashboard bootstrap.
async function initDashboard() {
  await Promise.all([loadSummary(), loadHistory(), loadForecast()]);

  document.getElementById("historyWindow").addEventListener("change", loadHistory);
  document.getElementById("refreshButton").addEventListener("click", refreshAggregation);
}

initDashboard().catch((error) => {
  document.getElementById("refreshStatus").textContent = `Dashboard load failed: ${error.message}`;
});
