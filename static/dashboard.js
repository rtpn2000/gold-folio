const currency = {
  usd: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }),
  inr: new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }),
};
const OUNCE_TO_GRAMS = 31.1034768;

let latestSummary = null;
let activeTooltipPointCleanup = null;

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

const metalSymbols = {
  XAU: { label: "Au", name: "Gold" },
  XAG: { label: "Ag", name: "Silver" },
  XPT: { label: "Pt", name: "Platinum" },
};
const LIVE_DASHBOARD_SYMBOL = "XAU";

let currentSymbol = localStorage.getItem("selectedMetal") || "XAU";

function getSymbolMeta(symbol) {
  return metalSymbols[symbol] || metalSymbols.XAU;
}

function isLiveDashboardSymbol(symbol) {
  return symbol === LIVE_DASHBOARD_SYMBOL;
}

function updateDashboardMode(symbol) {
  const meta = getSymbolMeta(symbol);
  const liveDashboard = isLiveDashboardSymbol(symbol);
  const heroMetrics = document.getElementById("heroMetrics");
  const heroComingSoon = document.getElementById("heroComingSoon");
  const goldDashboard = document.getElementById("goldDashboard");
  const metalComingSoon = document.getElementById("metalComingSoon");
  const comingSoonHistoryTitle = document.getElementById("comingSoonHistoryTitle");
  const comingSoonHistoryText = document.getElementById("comingSoonHistoryText");
  const comingSoonForecastTitle = document.getElementById("comingSoonForecastTitle");
  const comingSoonForecastText = document.getElementById("comingSoonForecastText");
  const refreshButton = document.getElementById("refreshButton");

  heroMetrics?.classList.toggle("is-hidden", !liveDashboard);
  heroComingSoon?.classList.toggle("is-hidden", liveDashboard);
  goldDashboard?.classList.toggle("is-hidden", !liveDashboard);
  metalComingSoon?.classList.toggle("is-hidden", liveDashboard);

  if (heroComingSoon) {
    heroComingSoon.textContent = `${meta.name} dashboard coming soon.`;
  }

  if (comingSoonHistoryTitle) {
    comingSoonHistoryTitle.textContent = "Coming soon";
  }

  if (comingSoonHistoryText) {
    comingSoonHistoryText.textContent = `${meta.name} price history and charting will appear here in a later update.`;
  }

  if (comingSoonForecastTitle) {
    comingSoonForecastTitle.textContent = "Coming soon";
  }

  if (comingSoonForecastText) {
    comingSoonForecastText.textContent = `${meta.name} forecasting will appear here in a later update.`;
  }

  if (refreshButton) {
    refreshButton.disabled = !liveDashboard;
    refreshButton.textContent = `Refresh ${meta.label}`;
  }
}

function setActiveSymbol(symbol) {
  currentSymbol = symbol.toUpperCase();
  localStorage.setItem("selectedMetal", currentSymbol);

  const meta = getSymbolMeta(currentSymbol);
  document.getElementById("heroSymbol").textContent = meta.label;
  document.getElementById("historyTitle").textContent = `${meta.name} USD historical performance`;
  updateDashboardMode(currentSymbol);

  document.querySelectorAll(".symbol-pill").forEach((button) => {
    button.classList.toggle("active", button.dataset.symbol === currentSymbol);
  });
}

function getSymbolQuery() {
  return `symbol=${encodeURIComponent(currentSymbol)}`;
}

function setTheme(isDark) {
  document.body.classList.toggle("dark-mode", isDark);
  const button = document.getElementById("themeToggle");
  if (button) {
    button.classList.toggle("dark", isDark);
    button.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  }
}

function loadTheme() {
  const savedTheme = localStorage.getItem("theme");
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
  const isDark = savedTheme ? savedTheme === "dark" : prefersDark;
  setTheme(isDark);
}

function toggleTheme() {
  const isDark = !document.body.classList.contains("dark-mode");
  setTheme(isDark);
  localStorage.setItem("theme", isDark ? "dark" : "light");
}

function updateHeroPrice(summary) {
  const latest = summary?.latest;
  const change = summary?.change || {};
  const usdOuncePrice = document.getElementById("usdOuncePrice");
  const usdOunceChange = document.getElementById("usdOunceChange");

  if (!usdOuncePrice || !usdOunceChange) {
    return;
  }

  const usdPerOunce = latest?.price_per_gram_usd != null
    ? latest.price_per_gram_usd * OUNCE_TO_GRAMS
    : null;
  const usdOunceDelta = change.usd != null
    ? change.usd * OUNCE_TO_GRAMS
    : null;

  usdOuncePrice.textContent = usdPerOunce != null ? currency.usd.format(usdPerOunce) : "--";
  usdOunceChange.innerHTML = formatChange(usdOunceDelta, currency.usd);
}

function updateRetailPrice(payload) {
  const retail24kPrice = document.getElementById("retail24kPrice");
  const retail24kMeta = document.getElementById("retail24kMeta");
  const retail22kPrice = document.getElementById("retail22kPrice");
  const retail22kMeta = document.getElementById("retail22kMeta");

  if (!retail24kPrice || !retail24kMeta || !retail22kPrice || !retail22kMeta) {
    return;
  }

  if (!payload || payload.error || !payload.item) {
    const message = payload?.error || "Retail price unavailable.";
    retail24kPrice.textContent = "--";
    retail24kMeta.textContent = message;
    retail22kPrice.textContent = "--";
    retail22kMeta.textContent = message;
    return;
  }

  retail24kPrice.textContent = currency.inr.format(payload.item.price_per_gram_inr_24k);
  retail24kMeta.textContent = `${payload.item.city} retail via NebulaAPI`;

  if (payload.item.price_per_gram_inr_22k != null) {
    retail22kPrice.textContent = currency.inr.format(payload.item.price_per_gram_inr_22k);
    retail22kMeta.textContent = `${payload.item.city} retail via NebulaAPI`;
  } else {
    retail22kPrice.textContent = "--";
    retail22kMeta.textContent = "22K retail price unavailable.";
  }
}

function hideChartTooltip() {
  const tooltip = document.getElementById("chartTooltip");
  if (!tooltip) {
    return;
  }
  tooltip.classList.remove("is-visible");
  tooltip.setAttribute("aria-hidden", "true");
}

function showChartTooltip(event) {
  const tooltip = document.getElementById("chartTooltip");
  const target = event.currentTarget;
  if (!tooltip || !target) {
    return;
  }

  tooltip.innerHTML = `
    <span class="chart-tooltip-date">${target.dataset.label || ""}</span>
    <span class="chart-tooltip-price">${target.dataset.price || ""}</span>
  `;
  tooltip.classList.add("is-visible");
  tooltip.setAttribute("aria-hidden", "false");
  tooltip.style.left = `${event.clientX + 16}px`;
  tooltip.style.top = `${event.clientY + 18}px`;
}

function bindChartTooltip(svg) {
  if (!svg) {
    return;
  }

  if (typeof activeTooltipPointCleanup === "function") {
    activeTooltipPointCleanup();
  }

  const points = Array.from(svg.querySelectorAll(".chart-hit-point"));
  const onMove = (event) => showChartTooltip(event);
  const onLeave = () => hideChartTooltip();

  points.forEach((point) => {
    point.addEventListener("mouseenter", onMove);
    point.addEventListener("mousemove", onMove);
    point.addEventListener("mouseleave", onLeave);
  });

  activeTooltipPointCleanup = () => {
    points.forEach((point) => {
      point.removeEventListener("mouseenter", onMove);
      point.removeEventListener("mousemove", onMove);
      point.removeEventListener("mouseleave", onLeave);
    });
    hideChartTooltip();
  };
}

// Draws a simple SVG line chart for history and forecast data.
function drawLineChart(svg, values, color) {
  const width = 800;
  const height = 320;
  const padX = 64;
  const padY = 28;

  if (!values.length) {
    svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#6f6257" font-size="18">No data available</text>`;
    return;
  }

  const nums = values.map((item) => item.value);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const yTicks = [0, 0.33, 0.66, 1];
  const gridLines = yTicks
    .map((ratio) => {
      const y = height - padY - ratio * (height - padY * 2);
      return `<line x1="${padX}" y1="${y}" x2="${width - padX}" y2="${y}" stroke="rgba(99,77,54,0.10)" stroke-width="1" stroke-dasharray="4 8"></line>`;
    })
    .join("");
  const yLabels = yTicks
    .map((ratio) => {
      const y = height - padY - ratio * (height - padY * 2);
      const value = min + ratio * span;
      return `<text x="${padX - 12}" y="${y + 4}" text-anchor="end" fill="#6f6257" font-size="13">${currency.usd.format(value)}</text>`;
    })
    .join("");

  const points = values.map((item, index) => {
    const x = padX + (index / Math.max(values.length - 1, 1)) * (width - padX * 2);
    const y = height - padY - ((item.value - min) / span) * (height - padY * 2);
    return `${x},${y}`;
  }).join(" ");
  const pointDots = values
    .map((item, index) => {
      const x = padX + (index / Math.max(values.length - 1, 1)) * (width - padX * 2);
      const y = height - padY - ((item.value - min) / span) * (height - padY * 2);
      const date = new Date(item.label);
      const label = Number.isNaN(date.getTime())
        ? item.label
        : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      const valueLabel = currency.usd.format(item.value);
      return `
        <circle
          cx="${x}"
          cy="${y}"
          r="8"
          fill="transparent"
          class="chart-hit-point"
          data-label="${label}"
          data-price="${valueLabel}"
        ></circle>
      `;
    })
    .join("");

  const xTickIndexes = values.length <= 6
    ? values.map((_, index) => index)
    : [0, Math.floor((values.length - 1) * 0.25), Math.floor((values.length - 1) * 0.5), Math.floor((values.length - 1) * 0.75), values.length - 1];
  const uniqueTickIndexes = [...new Set(xTickIndexes)];
  const xLabels = uniqueTickIndexes
    .map((index) => {
      const x = padX + (index / Math.max(values.length - 1, 1)) * (width - padX * 2);
      const date = new Date(values[index].label);
      const label = Number.isNaN(date.getTime())
        ? values[index].label
        : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      return `<text x="${x}" y="${height - 6}" text-anchor="middle" fill="#6f6257" font-size="13">${label}</text>`;
    })
    .join("");

  const finalPoint = values[values.length - 1];
  const finalX = padX + ((values.length - 1) / Math.max(values.length - 1, 1)) * (width - padX * 2);
  const finalY = height - padY - ((finalPoint.value - min) / span) * (height - padY * 2);

  svg.innerHTML = `
    ${gridLines}
    ${yLabels}
    <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="rgba(99,77,54,0.18)" stroke-width="1"></line>
    <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="rgba(99,77,54,0.18)" stroke-width="1"></line>
    <polyline points="${points}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
    ${pointDots}
    <circle cx="${finalX}" cy="${finalY}" r="5" fill="${color}"></circle>
    <circle cx="${finalX}" cy="${finalY}" r="10" fill="${color}" opacity="0.15"></circle>
    ${xLabels}
  `;

  bindChartTooltip(svg);
}

function renderForecastCards(items) {
  const container = document.getElementById("forecastCards");
  if (!container) {
    return;
  }

  container.innerHTML = "";

  items.slice(0, 8).forEach((item, index) => {
    const prev = index > 0 ? items[index - 1].price : null;
    const delta = prev == null ? null : item.price - prev;
    const deltaClass = delta == null ? "" : delta > 0 ? "up" : delta < 0 ? "down" : "";
    const deltaPrefix = delta != null && delta > 0 ? "+" : "";
    const deltaText = delta == null
      ? "Baseline reference"
      : `${deltaPrefix}${currency.usd.format(delta)} vs previous day`;

    const card = document.createElement("article");
    card.className = "forecast-item";
    card.innerHTML = `
      <div class="forecast-item-top">
        <span class="forecast-date">${item.date}</span>
        <span class="forecast-badge">Forecast</span>
      </div>
      <strong class="forecast-price">${currency.usd.format(item.price)}</strong>
      <div class="forecast-change ${deltaClass}">${deltaText}</div>
      <p class="forecast-note">Projected reference price for the selected forecast horizon.</p>
    `;
    container.appendChild(card);
  });
}

// Loads the top summary cards.
async function loadSummary() {
  if (!isLiveDashboardSymbol(currentSymbol)) {
    return;
  }
  const summary = await fetchJson(`/api/summary?${getSymbolQuery()}`);
  const latest = summary.latest;
  latestSummary = summary;

  updateHeroPrice(summary);
}

// Loads the historical chart and recent table data.
async function loadHistory() {
  if (!isLiveDashboardSymbol(currentSymbol)) {
    return;
  }
  const days = document.getElementById("historyWindow").value;
  const data = await fetchJson(`/api/history?days=${days}&${getSymbolQuery()}`);
  drawLineChart(
    document.getElementById("historyChart"),
    data.items.map((item) => ({ label: item.date, value: item.price_per_gram_usd })),
    "#b8860b"
  );
}

async function loadForecast() {
  const status = document.getElementById("forecastStatus");

  if (!status) {
    return;
  }

  if (!isLiveDashboardSymbol(currentSymbol)) {
    status.textContent = "Forecast will launch with this dashboard.";
    renderForecastCards([]);
    return;
  }

  status.textContent = "Forecasting will return in a later update.";
  renderForecastCards([]);
}

async function loadRetailPrice() {
  if (!isLiveDashboardSymbol(currentSymbol)) {
    return;
  }
  const retail = await fetchJson(`/api/retail?${getSymbolQuery()}`);
  updateRetailPrice(retail);
}

// Refreshes live pricing via the aggregation endpoint, then reloads the dashboard.
async function refreshAggregation() {
  if (!isLiveDashboardSymbol(currentSymbol)) {
    return;
  }
  const status = document.getElementById("refreshStatus");
  if (status) {
    const meta = getSymbolMeta(currentSymbol);
    status.textContent = `Fetching fresh ${meta.name.toLowerCase()} prices and saving them.`;
  }

  try {
    const result = await fetchJson(`/aggregate?${getSymbolQuery()}`);
    if (status) {
      status.textContent = `Saved ${result.rows} row(s). Sources: ${result.sources.join(", ") || "n/a"}.`;
    }
    await Promise.all([loadSummary(), loadHistory(), loadForecast(), loadRetailPrice()]);
  } catch (error) {
    if (status) {
      status.textContent = `Refresh failed: ${error.message}`;
    }
  }
}

// Dashboard bootstrap.
async function initDashboard() {
  loadTheme();
  setActiveSymbol(currentSymbol);

  document.getElementById("historyWindow")?.addEventListener("change", loadHistory);
  document.getElementById("refreshButton")?.addEventListener("click", refreshAggregation);
  document.getElementById("themeToggle")?.addEventListener("click", toggleTheme);

  document.querySelectorAll(".symbol-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      const symbol = pill.dataset.symbol;
      if (symbol && symbol !== currentSymbol) {
        setActiveSymbol(symbol);
        Promise.all([loadSummary(), loadHistory(), loadForecast(), loadRetailPrice()]);
      }
    });
  });

  try {
    await Promise.all([loadSummary(), loadHistory(), loadForecast(), loadRetailPrice()]);
  } catch (error) {
    const status = document.getElementById("refreshStatus");
    if (status) {
      status.textContent = `Dashboard load failed: ${error.message}`;
    }
  }
}

initDashboard();
