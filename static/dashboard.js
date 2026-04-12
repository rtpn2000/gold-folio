const currency = {
  usd: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }),
  inr: new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }),
};

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

function updateHeroPrice(summary) {
  const latest = summary?.latest;
  const change = summary?.change || {};
  const usdPrice = document.getElementById("usdPrice");
  const usdChange = document.getElementById("usdChange");
  const inrPrice = document.getElementById("inrPrice");
  const inrChange = document.getElementById("inrChange");

  if (!usdPrice || !usdChange || !inrPrice || !inrChange) {
    return;
  }

  usdPrice.textContent = latest ? currency.usd.format(latest.price_per_gram_usd) : "--";
  usdChange.innerHTML = formatChange(change.usd, currency.usd);
  inrPrice.textContent = latest && latest.price_per_gram_inr != null ? currency.inr.format(latest.price_per_gram_inr) : "--";
  inrChange.innerHTML = formatChange(change.inr, currency.inr);
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
  const summary = await fetchJson("/api/summary");
  const latest = summary.latest;
  latestSummary = summary;

  updateHeroPrice(summary);
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
}

async function loadForecast() {
  const result = await fetchJson("/api/forecast?days=30");
  const status = document.getElementById("forecastStatus");

  if (!status) {
    return;
  }

  if (result.error) {
    status.textContent = result.error;
    renderForecastCards([]);
    return;
  }

  status.textContent = "Short-term projected prices from the current forecasting model.";
  renderForecastCards(result.items || []);
}

// Refreshes live pricing via the aggregation endpoint, then reloads the dashboard.
async function refreshAggregation() {
  const status = document.getElementById("refreshStatus");
  if (status) {
    status.textContent = "Fetching fresh gold prices and saving them.";
  }

  try {
    const result = await fetchJson("/aggregate");
    if (status) {
      status.textContent = `Saved ${result.rows} row(s). Sources: ${result.sources.join(", ") || "n/a"}.`;
    }
    await Promise.all([loadSummary(), loadHistory(), loadForecast()]);
  } catch (error) {
    if (status) {
      status.textContent = `Refresh failed: ${error.message}`;
    }
  }
}

// Dashboard bootstrap.
async function initDashboard() {
  await Promise.all([loadSummary(), loadHistory(), loadForecast()]);

  document.getElementById("historyWindow").addEventListener("change", loadHistory);
  document.getElementById("refreshButton").addEventListener("click", refreshAggregation);
}

initDashboard().catch((error) => {
  const status = document.getElementById("refreshStatus");
  if (status) {
    status.textContent = `Dashboard load failed: ${error.message}`;
  }
});
