/**
 * QuantFrame Dashboard — Interactive App Logic
 * Chart.js + Fetch API + dynamic tab/panel management
 */

'use strict';

// ──────────────────────────────────────────────
// Constants & State
// ──────────────────────────────────────────────

const STRATEGY_COLORS = {
  rolling_straddle:   { line: '#00e5a0', fill: 'rgba(0,229,160,0.08)'  },
  buy_hold_futures:   { line: '#4db8ff', fill: 'rgba(77,184,255,0.08)' },
  hold_straddle:      { line: '#c084fc', fill: 'rgba(192,132,252,0.08)'},
};

const COLOR_FALLBACKS = [
  { line: '#fbbf24', fill: 'rgba(251,191,36,0.08)' },
  { line: '#f472b6', fill: 'rgba(244,114,182,0.08)'},
  { line: '#34d399', fill: 'rgba(52,211,153,0.08)' },
];

function stratColor(name, idx = 0) {
  return STRATEGY_COLORS[name] ?? COLOR_FALLBACKS[idx % COLOR_FALLBACKS.length];
}

const state = {
  symbol:   'NIFTY',
  strategy: 'rolling_straddle',
  pnlFreq:  '1min',
  tradesPage: 1,
  tradesPerPage: 50,
  tradesTotalPages: 1,
  tradeSearch: '',
  tradeAction: '',
  allTrades: [],
  availableCombos: [],
};

// Chart instances
const charts = {};

// ──────────────────────────────────────────────
// Chart.js Global Defaults
// ──────────────────────────────────────────────

Chart.defaults.color = '#8a95aa';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.tooltip.backgroundColor = '#141b2d';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.12)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.titleColor = '#e8edf5';
Chart.defaults.plugins.tooltip.bodyColor = '#8a95aa';
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;

// ──────────────────────────────────────────────
// Utilities
// ──────────────────────────────────────────────

function fmt(v, decimals = 2) {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  const sign = n >= 0 ? '+' : '';
  return sign + n.toFixed(decimals);
}

function fmtPnL(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toFixed(2);
}

async function apiFetch(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

function showLoading(msg = 'Loading…') {
  document.getElementById('loading-text').textContent = msg;
  document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

function setStatus(online) {
  const dot = document.getElementById('status-dot');
  dot.className = 'status-dot ' + (online ? 'online' : 'offline');
  dot.title = online ? 'API Online' : 'API Offline';
}

function setSrStatus(msg) {
  document.getElementById('sr-status').textContent = msg;
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

// ──────────────────────────────────────────────
// Tab Navigation
// ──────────────────────────────────────────────

function initTabs() {
  document.getElementById('header-tabs').addEventListener('click', e => {
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    const tab = btn.dataset.tab;

    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
    });
    document.querySelectorAll('.tab-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tab}`);
    });

    if (tab === 'pnl')     loadPnlDetailTab();
    if (tab === 'trades')  loadTradesTab();
    if (tab === 'compare') loadCompareTab();
  });
}

// ──────────────────────────────────────────────
// Global Selectors
// ──────────────────────────────────────────────

function initSelectors() {
  document.getElementById('global-symbol').addEventListener('change', e => {
    state.symbol = e.target.value;
    refreshOverview();
  });
  document.getElementById('global-strategy').addEventListener('change', e => {
    state.strategy = e.target.value;
    refreshOverview();
  });
}

// ──────────────────────────────────────────────
// Populate Strategy / Symbol dropdowns
// ──────────────────────────────────────────────

async function loadStrategies() {
  const data = await apiFetch('/api/strategies');
  state.availableCombos = data.combinations || [];

  const stratSel = document.getElementById('global-strategy');
  stratSel.innerHTML = '';
  (data.strategies || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    stratSel.appendChild(opt);
  });

  const symSel = document.getElementById('global-symbol');
  symSel.innerHTML = '';
  (data.symbols || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    symSel.appendChild(opt);
  });

  // Set initial state
  if (data.strategies?.length) state.strategy = data.strategies[0];
  if (data.symbols?.length)    state.symbol    = data.symbols[0];
}

// ──────────────────────────────────────────────
// KPI Cards
// ──────────────────────────────────────────────

async function loadKPIs() {
  const data = await apiFetch(`/api/metrics?strategy=${state.strategy}&symbol=${state.symbol}`);

  const pnl = data.total_pnl ?? 0;
  const el = document.getElementById('val-total-pnl');
  el.textContent = fmtPnL(pnl);
  el.className = 'kpi-value ' + (pnl >= 0 ? 'kpi-value--positive' : 'kpi-value--negative');

  document.getElementById('val-max-dd').textContent = fmt(data.max_dd ?? 0);
  document.getElementById('val-sharpe').textContent = fmt(data.sharpe ?? 0);

  const wr = data.win_rate ?? 0;
  document.getElementById('val-win-rate').textContent = wr.toFixed(1) + '%';
  document.getElementById('sub-win-rate').textContent =
    `${data.win_days ?? 0} / ${data.total_days ?? 0} days`;

  document.getElementById('val-trades').textContent =
    (data.num_trades ?? 0).toLocaleString();

  setSrStatus(`KPIs loaded: PnL ${fmtPnL(pnl)}, Sharpe ${fmt(data.sharpe)}`);
}

// ──────────────────────────────────────────────
// Cumulative PnL Chart (Overview)
// ──────────────────────────────────────────────

async function loadPnLChart(freq = '1min') {
  const data = await apiFetch(`/api/pnl?strategy=${state.strategy}&symbol=${state.symbol}&freq=${freq}`);
  const labels = data.labels ?? [];
  const values = data.pnl   ?? [];

  const color = stratColor(state.strategy);
  destroyChart('pnl');

  const ctx = document.getElementById('chart-pnl').getContext('2d');

  // Gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, 240);
  grad.addColorStop(0, color.line + '33');
  grad.addColorStop(1, color.line + '00');

  charts['pnl'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: `${state.symbol} PnL`,
        data: values,
        borderColor: color.line,
        backgroundColor: grad,
        borderWidth: 1.5,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          ticks: { maxTicksLimit: 8, maxRotation: 0 },
          grid: { display: false },
        },
        y: {
          ticks: {
            callback: v => (v >= 0 ? '+' : '') + v.toFixed(0),
            maxTicksLimit: 6,
          },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` PnL: ${fmtPnL(ctx.raw)}`,
          },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Daily PnL Bar Chart
// ──────────────────────────────────────────────

async function loadDailyChart() {
  const data = await apiFetch(`/api/daily?strategy=${state.strategy}&symbol=${state.symbol}`);
  const dates   = data.dates        ?? [];
  const changes = data.daily_change ?? [];

  destroyChart('daily');
  const ctx = document.getElementById('chart-daily').getContext('2d');

  charts['daily'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dates,
      datasets: [{
        label: 'Daily PnL',
        data: changes,
        backgroundColor: changes.map(v => v >= 0 ? 'rgba(0,229,160,0.7)' : 'rgba(255,77,106,0.7)'),
        borderColor:     changes.map(v => v >= 0 ? '#00e5a0' : '#ff4d6a'),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 45 } },
        y: {
          ticks: { callback: v => (v >= 0 ? '+' : '') + v.toFixed(0) },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` PnL: ${fmtPnL(ctx.raw)}` },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Drawdown Chart
// ──────────────────────────────────────────────

async function loadDrawdownChart() {
  const data = await apiFetch(`/api/pnl?strategy=${state.strategy}&symbol=${state.symbol}&freq=1min`);
  const pnl = data.pnl ?? [];
  const labels = data.labels ?? [];

  // Compute drawdown series
  let peak = -Infinity;
  const dd = pnl.map(v => {
    if (v > peak) peak = v;
    return -(peak - v);  // Negative drawdown
  });

  destroyChart('drawdown');
  const ctx = document.getElementById('chart-drawdown').getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 240);
  grad.addColorStop(0, 'rgba(255,77,106,0.3)');
  grad.addColorStop(1, 'rgba(255,77,106,0)');

  charts['drawdown'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Drawdown',
        data: dd,
        borderColor: '#ff4d6a',
        backgroundColor: grad,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0 } },
        y: {
          ticks: { callback: v => v.toFixed(0), maxTicksLimit: 6 },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` DD: ${ctx.raw.toFixed(2)}` } },
      },
    },
  });
}

// ──────────────────────────────────────────────
// PnL Detail Tab (zoomable)
// ──────────────────────────────────────────────

async function loadPnlDetailTab() {
  const data = await apiFetch(`/api/pnl?strategy=${state.strategy}&symbol=${state.symbol}&freq=${state.pnlFreq}`);
  const color = stratColor(state.strategy);

  destroyChart('pnl-detail');
  const ctx = document.getElementById('chart-pnl-detail').getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 380);
  grad.addColorStop(0, color.line + '22');
  grad.addColorStop(1, color.line + '00');

  charts['pnl-detail'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels ?? [],
      datasets: [{
        label: `${state.strategy} — ${state.symbol}`,
        data: data.pnl ?? [],
        borderColor: color.line,
        backgroundColor: grad,
        borderWidth: 1.5,
        pointRadius: 0,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 12, maxRotation: 0 } },
        y: {
          ticks: { callback: v => (v >= 0 ? '+' : '') + v.toFixed(0), maxTicksLimit: 8 },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { display: true },
        tooltip: { callbacks: { label: ctx => ` PnL: ${fmtPnL(ctx.raw)}` } },
        zoom: {
          pan:  { enabled: true, mode: 'x' },
          zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
        },
      },
    },
  });

  // Distribution + Donut also need data
  loadDistributionChart(data.pnl ?? []);
  loadDonutChart();

  // Wire freq chips
  document.querySelectorAll('#panel-pnl .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#panel-pnl .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.pnlFreq = chip.dataset.freq;
      loadPnlDetailTab();
    });
  });

  // Reset zoom button
  document.getElementById('btn-reset-zoom')?.addEventListener('click', () => {
    charts['pnl-detail']?.resetZoom();
  });
}

// ──────────────────────────────────────────────
// PnL Distribution Histogram
// ──────────────────────────────────────────────

function loadDistributionChart(pnlSeries) {
  if (!pnlSeries.length) return;

  // Compute daily returns (diff of last-per-minute grouped per day)
  // Approximate: diff of series values
  const diffs = pnlSeries.slice(1).map((v, i) => v - pnlSeries[i]);

  const min = Math.min(...diffs), max = Math.max(...diffs);
  const bins = 20;
  const step = (max - min) / bins;
  const counts = new Array(bins).fill(0);
  const labels = [];
  for (let i = 0; i < bins; i++) {
    labels.push((min + i * step).toFixed(1));
    diffs.forEach(d => { if (d >= min + i * step && d < min + (i+1) * step) counts[i]++; });
  }

  destroyChart('dist');
  const ctx = document.getElementById('chart-dist').getContext('2d');
  charts['dist'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Frequency',
        data: counts,
        backgroundColor: counts.map((_, i) => {
          const val = min + i * step;
          return val >= 0 ? 'rgba(0,229,160,0.6)' : 'rgba(255,77,106,0.6)';
        }),
        borderWidth: 0,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 6, maxRotation: 45 } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// ──────────────────────────────────────────────
// Win/Loss Donut
// ──────────────────────────────────────────────

async function loadDonutChart() {
  const data = await apiFetch(`/api/metrics?strategy=${state.strategy}&symbol=${state.symbol}`);
  const win = data.win_days ?? 0;
  const lose = (data.total_days ?? 0) - win;

  destroyChart('donut');
  const ctx = document.getElementById('chart-donut').getContext('2d');
  charts['donut'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Winning Days', 'Losing Days'],
      datasets: [{
        data: [win, lose],
        backgroundColor: ['rgba(0,229,160,0.8)', 'rgba(255,77,106,0.8)'],
        borderColor:     ['#00e5a0', '#ff4d6a'],
        borderWidth: 2,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'bottom' },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} days` } },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Trades Table
// ──────────────────────────────────────────────

async function loadTradesTab() {
  const url = `/api/trades?strategy=${state.strategy}&symbol=${state.symbol}&page=${state.tradesPage}&per_page=${state.tradesPerPage}`;
  const data = await apiFetch(url);

  state.tradesTotalPages = data.total_pages ?? 1;
  state.allTrades = data.trades ?? [];

  renderTrades(state.allTrades);
  document.getElementById('trade-count').textContent =
    `${(data.total ?? 0).toLocaleString()} trades total`;
  document.getElementById('page-info').textContent =
    `Page ${data.page ?? 1} / ${data.total_pages ?? 1}`;

  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  prevBtn.disabled = (data.page ?? 1) <= 1;
  nextBtn.disabled = (data.page ?? 1) >= (data.total_pages ?? 1);

  prevBtn.onclick = () => { state.tradesPage--; loadTradesTab(); };
  nextBtn.onclick = () => { state.tradesPage++; loadTradesTab(); };

  // Search
  document.getElementById('trade-search').addEventListener('input', filterTrades);
  document.getElementById('trade-action-filter').addEventListener('change', filterTrades);
}

function filterTrades() {
  const q = document.getElementById('trade-search').value.toLowerCase();
  const action = document.getElementById('trade-action-filter').value;
  state.tradeSearch = q;
  state.tradeAction = action;

  const filtered = state.allTrades.filter(t => {
    const matchSearch = !q || Object.values(t).some(v => String(v).toLowerCase().includes(q));
    const matchAction = !action || t.Action === action;
    return matchSearch && matchAction;
  });
  renderTrades(filtered);
}

function renderTrades(trades) {
  const tbody = document.getElementById('trades-body');
  if (!trades.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-row">No trades found.</td></tr>`;
    return;
  }

  tbody.innerHTML = trades.map((t, i) => `
    <tr>
      <td>${(state.tradesPage - 1) * state.tradesPerPage + i + 1}</td>
      <td>${t.Time ?? '—'}</td>
      <td><span class="badge badge--${(t.Action ?? '').toLowerCase()}">${t.Action ?? '—'}</span></td>
      <td><span class="symbol-code">${t.Symbol ?? '—'}</span></td>
      <td>${t.Qty ?? '—'}</td>
      <td class="${(parseFloat(t.Price) >= 0) ? '' : 'pnl-negative'}">${parseFloat(t.Price ?? 0).toFixed(2)}</td>
    </tr>
  `).join('');
}

// ──────────────────────────────────────────────
// Compare Tab
// ──────────────────────────────────────────────

async function loadCompareTab() {
  showLoading('Loading comparison data…');
  try {
    const rows = await apiFetch('/api/compare');

    // Build table
    const tbody = document.getElementById('compare-body');
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="loading-row">No comparison data available.</td></tr>`;
    } else {
      let stratIdx = 0;
      const stratColorMap = {};
      tbody.innerHTML = rows.map(r => {
        if (!stratColorMap[r.strategy]) {
          stratColorMap[r.strategy] = stratColor(r.strategy, stratIdx++).line;
        }
        const color = stratColorMap[r.strategy];
        const pnlClass = r.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        return `<tr>
          <td>
            <span class="strat-label">
              <span class="strat-dot" style="background:${color}"></span>
              ${r.strategy.replace(/_/g, ' ')}
            </span>
          </td>
          <td>${r.symbol}</td>
          <td class="${pnlClass}">${fmtPnL(r.total_pnl)}</td>
          <td>${r.max_dd?.toFixed(2) ?? '—'}</td>
          <td>${r.win_rate?.toFixed(1) ?? '—'}%</td>
          <td class="${r.sharpe >= 0 ? 'pnl-positive' : 'pnl-negative'}">${r.sharpe?.toFixed(2) ?? '—'}</td>
          <td>${r.num_trades?.toLocaleString() ?? '—'}</td>
        </tr>`;
      }).join('');
    }

    // Build multi-series overlay chart
    await loadCompareChart(rows);
  } finally {
    hideLoading();
  }
}

async function loadCompareChart(metricsRows) {
  // Fetch PnL series for each unique (strategy, symbol)
  const seen = new Set();
  const datasets = [];
  let labelsRef = null;
  let colorIdx = 0;

  for (const row of metricsRows) {
    const key = `${row.strategy}__${row.symbol}`;
    if (seen.has(key)) continue;
    seen.add(key);

    try {
      const data = await apiFetch(`/api/pnl?strategy=${row.strategy}&symbol=${row.symbol}&freq=5min`);
      if (!labelsRef) labelsRef = data.labels ?? [];

      const color = stratColor(row.strategy, colorIdx++);
      datasets.push({
        label: `${row.strategy.replace(/_/g,' ')} — ${row.symbol}`,
        data: data.pnl ?? [],
        borderColor: color.line,
        backgroundColor: color.fill,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      });
    } catch (_) { /* skip missing combinations */ }
  }

  destroyChart('compare');
  if (!datasets.length) return;

  const ctx = document.getElementById('chart-compare').getContext('2d');
  charts['compare'] = new Chart(ctx, {
    type: 'line',
    data: { labels: labelsRef ?? [], datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, maxRotation: 0 } },
        y: {
          ticks: { callback: v => (v >= 0 ? '+' : '') + v.toFixed(0), maxTicksLimit: 8 },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmtPnL(ctx.raw)}` } },
        zoom: {
          pan:  { enabled: true, mode: 'x' },
          zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Overview Refresh + Freq Chips
// ──────────────────────────────────────────────

async function refreshOverview() {
  showLoading('Loading data…');
  try {
    await Promise.all([
      loadKPIs(),
      loadPnLChart(state.pnlFreq),
      loadDailyChart(),
      loadDrawdownChart(),
    ]);
    setStatus(true);
  } catch (err) {
    console.error('Failed to load overview:', err);
    setStatus(false);
  } finally {
    hideLoading();
  }
}

function initFreqChips() {
  document.querySelectorAll('#panel-overview .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#panel-overview .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.pnlFreq = chip.dataset.freq;
      loadPnLChart(state.pnlFreq);
    });
  });
}

// ──────────────────────────────────────────────
// Boot
// ──────────────────────────────────────────────

async function init() {
  showLoading('Connecting to API…');
  try {
    await loadStrategies();
    setStatus(true);
  } catch (err) {
    setStatus(false);
    document.getElementById('loading-text').textContent = 'Failed to connect to API. Is app.py running?';
    return;
  }

  initTabs();
  initSelectors();
  initFreqChips();

  await refreshOverview();
}

document.addEventListener('DOMContentLoaded', init);
