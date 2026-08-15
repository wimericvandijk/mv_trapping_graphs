const DASHBOARD_SPECIES = ["Rat", "Mouse", "Possum", "Mustelid", "All Species"];
const AXIS_TICK_COLOR = "#506157";
const GRID_COLOR = "rgba(33, 48, 40, 0.12)";

const state = {
  metadata: null,
  weekly: null,
  yearlyComparison: null,
  summary: null,
  selectedSpecies: null,
  selectedPeriod: null,
  selectedYears: [],
  yearColors: {},
  weeklyChart: null,
  comparisonChart: null,
  expandedChartId: null,
  expandedChartParent: null,
  isProjectInfoOpen: false,
};

const YEAR_PALETTE = [
  "#2c7a5d",
  "#6a7c6f",
  "#2f5e90",
  "#9d6a3e",
  "#517f92",
  "#8a8458",
  "#c56b2c",
  "#7b4f9d",
];

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

function formatFriendlyDate(dateString) {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatFriendlyDateTime(dateString) {
  return new Date(dateString).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatMonthDayLabel(dateValue) {
  return dateValue.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function getPeriodDefinition(periodKey) {
  return (state.metadata.periods || []).find((period) => period.key === periodKey) || null;
}

function formatPeriodLabel(periodKey) {
  const periodDefinition = getPeriodDefinition(periodKey);
  if (periodDefinition && periodDefinition.label) {
    return periodDefinition.label;
  }
  return periodKey;
}

function getPeriodOptions(metadata) {
  if (Array.isArray(metadata.periods) && metadata.periods.length > 0) {
    return metadata.periods.map((period) => period.key);
  }
  return metadata.years.map(String);
}

function buildWeeklyWindow(periodKey, metadata) {
  const periodDefinition = (metadata.periods || []).find((period) => period.key === periodKey);
  const endDate = new Date(metadata.date_range.end);
  if (periodDefinition && periodDefinition.type === "rolling_months") {
    const startDate = new Date(endDate);
    startDate.setMonth(startDate.getMonth() - periodDefinition.months);
    return { startDate, endDate };
  }
  if (periodDefinition && periodDefinition.type === "calendar_year") {
    return {
      startDate: new Date(periodDefinition.year, 0, 1),
      endDate: new Date(periodDefinition.year, 11, 31),
    };
  }

  const year = Number(periodKey);
  return {
    startDate: new Date(year, 0, 1),
    endDate: new Date(year, 11, 31),
  };
}

function getFilteredWeeks(periodKey) {
  const { startDate, endDate } = buildWeeklyWindow(periodKey, state.metadata);
  return state.weekly.weeks.filter((week) => {
    const weekStart = new Date(week.week_start);
    return weekStart >= startDate && weekStart <= endDate;
  });
}

function getPeriodSummary(periodKey) {
  return state.summary.periods[periodKey] || null;
}

function getPeakWeek(weeks, species) {
  let peakWeek = null;
  for (const week of weeks) {
    const value = week.species[species] || 0;
    if (!peakWeek || value > peakWeek.value) {
      peakWeek = { week, value };
    }
  }
  return peakWeek;
}

function updateSummaryCards(species, periodKey, weeks) {
  const periodSummary = getPeriodSummary(periodKey);
  const total = periodSummary ? periodSummary.species_totals[species] || 0 : 0;
  const trend = periodSummary && periodSummary.trend ? periodSummary.trend[species] : null;
  const peakWeek = getPeakWeek(weeks, species);
  document.getElementById("summary-period-label").textContent = formatPeriodLabel(periodKey);

  document.getElementById("total-catches").textContent = total.toLocaleString();
  document.getElementById("total-caption").textContent = `${species} catches in ${formatPeriodLabel(periodKey).toLowerCase()}`;

  document.getElementById("trend-delta").textContent = trend ? `${trend.delta > 0 ? "+" : ""}${trend.delta}` : "-";
  document.getElementById("trend-caption").textContent = trend
    ? `${trend.direction} versus the same period 1 year prior`
    : "Trend not available for this period";

  document.getElementById("peak-week-total").textContent = peakWeek ? peakWeek.value.toLocaleString() : "0";
  document.getElementById("peak-week-caption").textContent = peakWeek
    ? `Peak week started ${formatFriendlyDate(peakWeek.week.week_start)}`
    : "No weekly data in selected period";
}

function getWeeklyChartColor(periodKey, weeks) {
  if (periodKey !== state.metadata.defaults.period) {
    return state.yearColors[periodKey] || YEAR_PALETTE[0];
  }

  if (weeks.length === 0) {
    return YEAR_PALETTE[0];
  }

  const laterYear = String(
    weeks.reduce((latestYear, week) => Math.max(latestYear, week.year), Number(weeks[0].year))
  );
  return state.yearColors[laterYear] || YEAR_PALETTE[0];
}

function buildWeeklyChart(species, weeks, periodKey) {
  const labels = weeks.map((week) => formatFriendlyDate(week.week_start));
  const values = weeks.map((week) => week.species[species] || 0);
  const ctx = document.getElementById("weekly-chart");
  const barColor = getWeeklyChartColor(periodKey, weeks);

  if (state.weeklyChart) {
    state.weeklyChart.destroy();
  }

  state.weeklyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: species,
          data: values,
          backgroundColor: barColor,
          borderRadius: 10,
          maxBarThickness: 24,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: {
          bottom: 10,
        },
      },
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: AXIS_TICK_COLOR, maxRotation: 0, autoSkip: true, maxTicksLimit: 8, padding: 14 },
          border: { color: GRID_COLOR },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { color: AXIS_TICK_COLOR, padding: 8 },
          border: { color: GRID_COLOR },
          grid: { color: GRID_COLOR },
        },
      },
    },
  });
}

function buildComparisonChart(species) {
  const series = state.yearlyComparison.series[species] || {};
  const weekIndex = state.yearlyComparison.week_index;
  const comparisonAxisLabels = buildComparisonAxisLabels(weekIndex);
  const datasets = Object.keys(series)
    .filter((year) => state.selectedYears.includes(year))
    .map((year) => ({
    label: year,
    data: series[year],
    borderColor: state.yearColors[year],
    backgroundColor: state.yearColors[year],
    tension: 0.25,
    pointRadius: 0,
    borderWidth: year === String(new Date().getFullYear()) ? 3 : 2,
  }));
  const ctx = document.getElementById("comparison-chart");

  if (state.comparisonChart) {
    state.comparisonChart.destroy();
  }

  state.comparisonChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: comparisonAxisLabels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
      scales: {
        x: {
          ticks: {
            color: AXIS_TICK_COLOR,
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0,
            callback(_value, index) {
              return comparisonAxisLabels[index] || "";
            },
          },
          title: { display: true, text: "Week start" },
          border: { color: GRID_COLOR },
          grid: { display: false, drawTicks: true, tickLength: 6 },
        },
        y: {
          beginAtZero: true,
          ticks: { color: AXIS_TICK_COLOR, padding: 8 },
          border: { color: GRID_COLOR },
          grid: { color: GRID_COLOR },
        },
      },
    },
  });
}

function getIsoWeekStart(year, isoWeek) {
  const januaryFourth = new Date(year, 0, 4);
  const dayOfWeek = januaryFourth.getDay() || 7;
  const firstIsoMonday = new Date(januaryFourth);
  firstIsoMonday.setDate(januaryFourth.getDate() - dayOfWeek + 1);
  const weekStart = new Date(firstIsoMonday);
  weekStart.setDate(firstIsoMonday.getDate() + (isoWeek - 1) * 7);
  return weekStart;
}

function buildComparisonAxisLabels(weekIndex) {
  const referenceYear = Number(state.selectedYears[state.selectedYears.length - 1] || state.metadata.years[state.metadata.years.length - 1]);
  let previousMonth = null;
  return weekIndex.map((weekNumber) => {
    const weekStart = getIsoWeekStart(referenceYear, weekNumber);
    const currentMonth = weekStart.getMonth();
    if (previousMonth !== currentMonth) {
      previousMonth = currentMonth;
      return formatMonthDayLabel(weekStart);
    }
    return "";
  });
}

function buildYearColorMap() {
  const years = getAvailableYears();
  state.yearColors = {};
  years.forEach((year, index) => {
    state.yearColors[year] = YEAR_PALETTE[index % YEAR_PALETTE.length];
  });
}

function getAvailableYears() {
  return state.metadata.years.map(String);
}

function getDefaultSelectedYears() {
  const years = getAvailableYears();
  return years.slice(Math.max(0, years.length - 4));
}

function renderYearButtons() {
  const containers = [
    document.getElementById("year-toggle-group"),
    document.getElementById("overlay-year-toggle-group"),
  ].filter(Boolean);
  const years = getAvailableYears();
  containers.forEach((container) => {
    container.innerHTML = "";

    years.forEach((year) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `year-toggle${state.selectedYears.includes(year) ? " is-active" : ""}`;
      button.textContent = year;
      button.setAttribute("aria-pressed", state.selectedYears.includes(year) ? "true" : "false");
      button.addEventListener("click", () => {
        const isSelected = state.selectedYears.includes(year);
        if (isSelected && state.selectedYears.length === 1) {
          return;
        }
        state.selectedYears = isSelected
          ? state.selectedYears.filter((value) => value !== year)
          : [...state.selectedYears, year].sort();
        renderYearButtons();
        buildComparisonChart(state.selectedSpecies);
      });
      container.appendChild(button);
    });
  });
}

function updateTitles(species, periodKey, weeks) {
  document.getElementById("weekly-title").textContent = `${species} in ${formatPeriodLabel(periodKey)}`;
  if (weeks.length > 0) {
    document.getElementById("weekly-subtitle").textContent = `${formatFriendlyDate(weeks[0].week_start)} to ${formatFriendlyDate(weeks[weeks.length - 1].week_end)}`;
  } else {
    document.getElementById("weekly-subtitle").textContent = "No data in selected period";
  }
  document.getElementById("comparison-title").textContent = `${species} across all available years`;
}

function renderDashboard() {
  const species = state.selectedSpecies;
  const periodKey = state.selectedPeriod;
  const weeks = getFilteredWeeks(periodKey);
  updateTitles(species, periodKey, weeks);
  updateSummaryCards(species, periodKey, weeks);
  buildWeeklyChart(species, weeks, periodKey);
  buildComparisonChart(species);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function renderMarkdown(markdown) {
  if (!markdown || !markdown.trim()) {
    return "<p>More project background will be added here.</p>";
  }

  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraphLines = [];
  let listItems = [];

  function flushParagraph() {
    if (paragraphLines.length === 0) {
      return;
    }
    html.push(`<p>${renderInlineMarkdown(paragraphLines.join(" "))}</p>`);
    paragraphLines = [];
  }

  function flushList() {
    if (listItems.length === 0) {
      return;
    }
    html.push(`<ul>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`);
    listItems = [];
  }

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      return;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = Math.min(headingMatch[1].length + 1, 4);
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
      return;
    }

    const listMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      listItems.push(listMatch[1]);
      return;
    }

    flushList();
    paragraphLines.push(trimmed);
  });

  flushParagraph();
  flushList();
  return html.join("");
}

function openProjectInfo() {
  const overlay = document.getElementById("project-info-overlay");
  if (!overlay) {
    return;
  }
  overlay.hidden = false;
  state.isProjectInfoOpen = true;
}

function closeProjectInfo() {
  const overlay = document.getElementById("project-info-overlay");
  if (!overlay) {
    return;
  }
  overlay.hidden = true;
  state.isProjectInfoOpen = false;
}

function openChartOverlay(chartId) {
  const chartFrame = document.getElementById(chartId);
  const overlay = document.getElementById("chart-overlay");
  const overlayHost = document.getElementById("overlay-chart-host");
  const overlayTitle = document.getElementById("overlay-title");
  const overlayWeeklyToolbar = document.getElementById("overlay-weekly-toolbar");
  const overlayComparisonToolbar = document.getElementById("overlay-comparison-toolbar");
  if (!chartFrame || !overlay || !overlayHost) {
    return;
  }

  state.expandedChartId = chartId;
  state.expandedChartParent = chartFrame.parentElement;
  overlayTitle.textContent = chartId === "weekly-panel" ? document.getElementById("weekly-title").textContent : document.getElementById("comparison-title").textContent;
  if (overlayWeeklyToolbar) {
    overlayWeeklyToolbar.hidden = chartId !== "weekly-panel";
  }
  if (overlayComparisonToolbar) {
    overlayComparisonToolbar.hidden = chartId !== "comparison-panel";
  }
  overlay.hidden = false;
  overlayHost.appendChild(chartFrame);
  chartFrame.classList.add("is-expanded");
  renderYearButtons();
  if (state.weeklyChart) {
    state.weeklyChart.resize();
  }
  if (state.comparisonChart) {
    state.comparisonChart.resize();
  }
}

function closeChartOverlay() {
  const overlay = document.getElementById("chart-overlay");
  const overlayWeeklyToolbar = document.getElementById("overlay-weekly-toolbar");
  const overlayComparisonToolbar = document.getElementById("overlay-comparison-toolbar");
  if (!state.expandedChartId || !state.expandedChartParent || !overlay) {
    return;
  }

  const chartFrame = document.getElementById(state.expandedChartId);
  state.expandedChartParent.appendChild(chartFrame);
  chartFrame.classList.remove("is-expanded");
  overlay.hidden = true;
  if (overlayWeeklyToolbar) {
    overlayWeeklyToolbar.hidden = true;
  }
  if (overlayComparisonToolbar) {
    overlayComparisonToolbar.hidden = true;
  }
  state.expandedChartId = null;
  state.expandedChartParent = null;
  renderYearButtons();
  if (state.weeklyChart) {
    state.weeklyChart.resize();
  }
  if (state.comparisonChart) {
    state.comparisonChart.resize();
  }
}

function bindChartOverlayControls() {
  document.querySelectorAll(".chart-expand-button[data-chart-target]").forEach((button) => {
    button.addEventListener("click", () => {
      openChartOverlay(button.dataset.chartTarget);
    });
  });

  document.getElementById("overlay-close").addEventListener("click", closeChartOverlay);
  document.querySelector("[data-close-overlay='true']").addEventListener("click", closeChartOverlay);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeChartOverlay();
      closeProjectInfo();
    }
  });
}

function bindProjectInfoControls() {
  const openButton = document.getElementById("project-info-button");
  const closeButton = document.getElementById("project-info-close");
  const backdrop = document.querySelector("[data-close-project-info='true']");

  if (openButton) {
    openButton.addEventListener("click", openProjectInfo);
  }
  if (closeButton) {
    closeButton.addEventListener("click", closeProjectInfo);
  }
  if (backdrop) {
    backdrop.addEventListener("click", closeProjectInfo);
  }
}

function populateFilters() {
  const speciesGroup = document.getElementById("species-radio-group");
  const periodSelect = document.getElementById("period-select");
  const overlayPeriodSelect = document.getElementById("overlay-period-select");

  speciesGroup.innerHTML = "";
  state.metadata.species.forEach((species) => {
    const label = document.createElement("label");
    label.className = `species-option${species === state.selectedSpecies ? " is-active" : ""}`;

    const input = document.createElement("input");
    input.type = "radio";
    input.name = "species";
    input.value = species;
    input.checked = species === state.selectedSpecies;

    const text = document.createElement("span");
    text.textContent = species;

    input.addEventListener("change", () => {
      if (!input.checked) {
        return;
      }
      state.selectedSpecies = species;
      populateFilters();
      renderYearButtons();
      renderDashboard();
    });

    label.appendChild(input);
    label.appendChild(text);
    speciesGroup.appendChild(label);
  });

  const periodOptions = getPeriodOptions(state.metadata);

  function populatePeriodSelect(selectElement) {
    if (!selectElement) {
      return;
    }
    selectElement.innerHTML = "";
    periodOptions.forEach((periodKey) => {
      const option = document.createElement("option");
      option.value = periodKey;
      option.textContent = formatPeriodLabel(periodKey);
      if (periodKey === state.selectedPeriod) {
        option.selected = true;
      }
      selectElement.appendChild(option);
    });
  }

  populatePeriodSelect(periodSelect);
  populatePeriodSelect(overlayPeriodSelect);

  function handlePeriodChange(value) {
    state.selectedPeriod = value;
    if (periodSelect && periodSelect.value !== value) {
      periodSelect.value = value;
    }
    if (overlayPeriodSelect && overlayPeriodSelect.value !== value) {
      overlayPeriodSelect.value = value;
    }
    renderDashboard();
  }

  periodSelect.onchange = () => {
    handlePeriodChange(periodSelect.value);
  };

  if (overlayPeriodSelect) {
    overlayPeriodSelect.onchange = () => {
      handlePeriodChange(overlayPeriodSelect.value);
    };
  }
}

function populateMeta() {
  const projectName = state.metadata.project && state.metadata.project.name
    ? state.metadata.project.name
    : state.metadata.source.project;
  const about = state.metadata.project && state.metadata.project.about
    ? state.metadata.project.about
    : {};
  const aboutContent = document.getElementById("project-info-content");
  const aboutTitle = document.getElementById("project-info-title");
  const infoButton = document.getElementById("project-info-button");

  document.getElementById("hero-project-name").textContent = projectName;
  document.getElementById("hero-title").textContent = `Trapping trends ${formatFriendlyDate(state.metadata.date_range.start)} to ${formatFriendlyDate(state.metadata.date_range.end)}`;
  document.getElementById("hero-published").textContent = `Published ${formatFriendlyDateTime(state.metadata.generated_at)}`;

  if (aboutTitle) {
    aboutTitle.textContent = `About ${projectName}`;
  }

  if (aboutContent) {
    aboutContent.innerHTML = renderMarkdown(about.content_markdown || about.summary || "");
  }
  if (infoButton) {
    infoButton.hidden = !about.content_markdown && !about.summary;
  }
}

async function init() {
  try {
    const [metadata, weekly, yearlyComparison, summary] = await Promise.all([
      loadJson("data/metadata.json"),
      loadJson("data/weekly.json"),
      loadJson("data/yearly_comparison.json"),
      loadJson("data/summary.json"),
    ]);
    state.metadata = metadata;
    state.weekly = weekly;
    state.yearlyComparison = yearlyComparison;
    state.summary = summary;
    state.selectedSpecies = metadata.defaults.species;
    state.selectedPeriod = getPeriodOptions(metadata).includes(metadata.defaults.period)
      ? metadata.defaults.period
      : getPeriodOptions(metadata)[0];
    state.selectedYears = getDefaultSelectedYears();
    buildYearColorMap();

    populateMeta();
    populateFilters();
    renderYearButtons();
    bindChartOverlayControls();
    bindProjectInfoControls();
    renderDashboard();
  } catch (error) {
    document.body.innerHTML = `<div style="padding:24px;font-family:IBM Plex Sans,sans-serif;color:#213028;">Failed to load dashboard data: ${error.message}</div>`;
  }
}

init();