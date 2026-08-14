const DASHBOARD_SPECIES = ["Rat", "Mouse", "Possum", "Mustelid", "All Species"];
const PERIOD_LAST_SIX_MONTHS = "last_6_months";
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

function formatMonthDayLabel(dateValue) {
  return dateValue.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function formatPeriodLabel(periodKey) {
  if (periodKey === PERIOD_LAST_SIX_MONTHS) {
    return "Last 6 months";
  }
  return periodKey;
}

function getPeriodOptions(metadata) {
  return [PERIOD_LAST_SIX_MONTHS, ...metadata.years.map(String)];
}

function buildWeeklyWindow(periodKey, metadata) {
  const endDate = new Date(metadata.date_range.end);
  if (periodKey === PERIOD_LAST_SIX_MONTHS) {
    const startDate = new Date(endDate);
    startDate.setMonth(startDate.getMonth() - 6);
    return { startDate, endDate };
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

  document.getElementById("total-catches").textContent = total.toLocaleString();
  document.getElementById("total-caption").textContent = `${species} catches in ${formatPeriodLabel(periodKey).toLowerCase()}`;

  document.getElementById("trend-delta").textContent = trend ? `${trend.delta > 0 ? "+" : ""}${trend.delta}` : "-";
  document.getElementById("trend-caption").textContent = trend
    ? `${trend.direction} versus previous equivalent period`
    : "Trend not available for this period";

  document.getElementById("peak-week-total").textContent = peakWeek ? peakWeek.value.toLocaleString() : "0";
  document.getElementById("peak-week-caption").textContent = peakWeek
    ? `Peak week started ${formatFriendlyDate(peakWeek.week.week_start)}`
    : "No weekly data in selected period";
}

function getWeeklyChartColor(periodKey, weeks) {
  if (periodKey !== PERIOD_LAST_SIX_MONTHS) {
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
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: AXIS_TICK_COLOR, maxRotation: 0, autoSkip: true, maxTicksLimit: 8, padding: 10 },
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
  const container = document.getElementById("year-toggle-group");
  const years = getAvailableYears();
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

function populateFilters() {
  const speciesSelect = document.getElementById("species-select");
  const periodSelect = document.getElementById("period-select");

  speciesSelect.innerHTML = "";
  state.metadata.species.forEach((species) => {
    const option = document.createElement("option");
    option.value = species;
    option.textContent = species;
    if (species === state.metadata.defaults.species) {
      option.selected = true;
    }
    speciesSelect.appendChild(option);
  });

  periodSelect.innerHTML = "";
  getPeriodOptions(state.metadata).forEach((periodKey) => {
    const option = document.createElement("option");
    option.value = periodKey;
    option.textContent = formatPeriodLabel(periodKey);
    if (periodKey === state.metadata.defaults.period) {
      option.selected = true;
    }
    periodSelect.appendChild(option);
  });

  speciesSelect.addEventListener("change", () => {
    state.selectedSpecies = speciesSelect.value;
    state.selectedYears = getDefaultSelectedYears();
    renderYearButtons();
    renderDashboard();
  });

  periodSelect.addEventListener("change", () => {
    state.selectedPeriod = periodSelect.value;
    renderDashboard();
  });
}

function populateMeta() {
  document.getElementById("dataset-range").textContent = `${formatFriendlyDate(state.metadata.date_range.start)} to ${formatFriendlyDate(state.metadata.date_range.end)}`;
  document.getElementById("dataset-generated").textContent = `Published ${formatFriendlyDate(state.metadata.generated_at)}`;
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
    state.selectedPeriod = metadata.defaults.period;
    state.selectedYears = getDefaultSelectedYears();
    buildYearColorMap();

    populateMeta();
    populateFilters();
    renderYearButtons();
    renderDashboard();
  } catch (error) {
    document.body.innerHTML = `<div style="padding:24px;font-family:IBM Plex Sans,sans-serif;color:#213028;">Failed to load dashboard data: ${error.message}</div>`;
  }
}

init();