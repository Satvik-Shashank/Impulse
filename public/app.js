// ════════════════════════════════════════════════════════════════════
// Chargeback Intelligence Platform — Client Controller
// Vanilla JS with Chart.js for interactive dashboard
// ════════════════════════════════════════════════════════════════════

let globalMetrics = null;
let globalPredictions = [];
let chartInstances = {};

// ── Presets ────────────────────────────────────────────────────────
const PRESET_STRONG = {
  "dispute_id": "DSP-2026-00142",
  "reason_code_label": "Other Fraud - Card Absent Environment",
  "card_network": "Visa",
  "dispute_amount": 12499.00,
  "currency": "INR",
  "transaction_date": "2026-06-15",
  "days_to_dispute": 35,
  "product_category": "electronics",
  "shipping_method": "express",
  "delivery_confirmed": true,
  "has_delivery_proof": true,
  "ip_geolocation_match": true,
  "avs_cvv_match": "both_match",
  "customer_account_age_days": 45,
  "customer_prior_disputes": 0,
  "customer_prior_orders": 3,
  "has_customer_correspondence": false,
  "has_3ds_authentication": true
};

const PRESET_WEAK = {
  "dispute_id": "DSP-2026-00987",
  "reason_code_label": "Fraud - Card Absent",
  "card_network": "Visa",
  "dispute_amount": 8999.00,
  "currency": "INR",
  "transaction_date": "2026-07-01",
  "days_to_dispute": 8,
  "product_category": "electronics",
  "shipping_method": "standard",
  "delivery_confirmed": false,
  "has_delivery_proof": false,
  "ip_geolocation_match": false,
  "avs_cvv_match": "neither",
  "customer_account_age_days": 3,
  "customer_prior_disputes": 1,
  "customer_prior_orders": 0,
  "has_customer_correspondence": false,
  "has_3ds_authentication": false
};

// ── Chart.js Global Config ────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;

// ── Initialize ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchMetrics();
  fetchPredictions();
  loadPreset('strong');
  checkApiHealth();
  setInterval(checkApiHealth, 30000);
});

// ── Tab Switcher ──────────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
  event.target.classList.add('active');
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) panel.classList.add('active');

  // Lazy-load monitoring data
  if (tabId === 'monitoring') fetchMonitoringDrift();
}

// ── API Health Check ──────────────────────────────────────────────
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      document.getElementById('api-status').textContent = 'API Online';
    } else {
      document.getElementById('api-status').textContent = 'API Error';
    }
  } catch {
    document.getElementById('api-status').textContent = 'API Offline';
  }
}

// ── Fetch Metrics ─────────────────────────────────────────────────
async function fetchMetrics() {
  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) throw new Error('Metrics not ready');
    globalMetrics = await res.json();
    renderHeroMetrics();
    renderClassifierStats();
    updateCostPoint(0.70);
    renderOverviewCharts();
    renderPerformanceCharts();
  } catch (err) {
    console.warn('Metrics fetch:', err);
  }
}

// ── Fetch Predictions ─────────────────────────────────────────────
async function fetchPredictions() {
  try {
    const res = await fetch('/api/predictions');
    if (!res.ok) return;
    globalPredictions = await res.json();
    populateCaseDropdown();
  } catch (err) {
    console.warn('Predictions fetch:', err);
  }
}

// ── Render Hero KPIs ──────────────────────────────────────────────
function renderHeroMetrics() {
  if (!globalMetrics) return;
  const baselines = globalMetrics.baselines_inr || {};
  const fe = baselines.fight_everything_net_value || 0;
  const fn = baselines.fight_nothing_net_value || 0;
  const sb = baselines.system_best_net_value || 0;
  const delta = sb - fe;

  animateValue('val-fight-everything', fe, '₹');
  animateValue('val-fight-nothing', fn, '₹');
  animateValue('val-system-best', sb, '₹');

  const deltaEl = document.getElementById('val-delta');
  deltaEl.textContent = `${delta >= 0 ? '+' : ''}₹${delta.toLocaleString('en-IN')} vs naive`;

  const scale = globalMetrics.illustrative_scale_extrapolation_inr || {};
  const bannerText = scale.note
    ? `⚠️ ${scale.note} Illustration at 100k disputes/year: ₹${(scale.at_100k_disputes_per_year || 0).toLocaleString('en-IN')}.`
    : '';
  document.getElementById('scale-banner-text').innerHTML = bannerText;
}

// ── Animate Counter ───────────────────────────────────────────────
function animateValue(elementId, target, prefix = '', duration = 800) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = Math.round(start + (target - start) * eased);
    el.textContent = `${prefix}${current.toLocaleString('en-IN')}`;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// ── Render Classifier Stats ───────────────────────────────────────
function renderClassifierStats() {
  if (!globalMetrics) return;
  document.getElementById('stat-acc').textContent = `${(globalMetrics.reason_code_accuracy * 100).toFixed(1)}%`;
  document.getElementById('stat-prec').textContent = `${(globalMetrics.macro_precision * 100).toFixed(1)}%`;
  document.getElementById('stat-rec').textContent = `${(globalMetrics.macro_recall * 100).toFixed(1)}%`;
  document.getElementById('stat-auc').textContent = globalMetrics.win_prediction_auc.toFixed(3);

  const winAuc = globalMetrics.win_predictor_dedicated_auc;
  document.getElementById('stat-win-auc').textContent = winAuc ? winAuc.toFixed(3) : 'N/A';

  // Per-class table
  const tbody = document.getElementById('per-class-tbody');
  tbody.innerHTML = '';
  const perClass = globalMetrics.per_class || {};
  Object.keys(perClass).forEach(code => {
    const item = perClass[code];
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${code}</strong></td>
      <td>${(item.precision * 100).toFixed(1)}%</td>
      <td>${(item.recall * 100).toFixed(1)}%</td>
      <td>${(item['f1-score'] * 100).toFixed(1)}%</td>
      <td>${item.support}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Cost Operating Point ──────────────────────────────────────────
function updateCostPoint(val) {
  const threshold = parseFloat(val);
  document.getElementById('threshold-val').textContent = threshold.toFixed(2);
  if (!globalMetrics || !globalMetrics.cost_curve) return;

  const row = globalMetrics.cost_curve.find(c => Math.abs(c.threshold - threshold) < 0.01) || globalMetrics.cost_curve[0];
  document.getElementById('cost-auto-pct').textContent = `${(row.auto_respond_pct * 100).toFixed(1)}%`;
  document.getElementById('cost-win-rate').textContent = `${(row.win_rate_at_threshold * 100).toFixed(1)}%`;
  document.getElementById('cost-net-dispute').textContent = `₹${row.net_value_per_dispute.toFixed(0)}`;
}

// ── Overview Charts ───────────────────────────────────────────────
function renderOverviewCharts() {
  if (!globalMetrics) return;

  // Reason Code Distribution (from per_class support)
  const perClass = globalMetrics.per_class || {};
  const rcLabels = Object.keys(perClass);
  const rcData = rcLabels.map(k => perClass[k].support || 0);
  const rcColors = ['#6366f1', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

  destroyChart('chart-rc-dist');
  chartInstances['chart-rc-dist'] = new Chart(document.getElementById('chart-rc-dist'), {
    type: 'doughnut',
    data: {
      labels: rcLabels,
      datasets: [{
        data: rcData,
        backgroundColor: rcColors.slice(0, rcLabels.length),
        borderWidth: 0,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, padding: 8, font: { size: 10 } } },
      }
    }
  });

  // Baseline Comparison Bar Chart
  const baselines = globalMetrics.baselines_inr || {};
  destroyChart('chart-baseline');
  chartInstances['chart-baseline'] = new Chart(document.getElementById('chart-baseline'), {
    type: 'bar',
    data: {
      labels: ['Fight Everything', 'Fight Nothing', 'This System'],
      datasets: [{
        data: [baselines.fight_everything_net_value, baselines.fight_nothing_net_value, baselines.system_best_net_value],
        backgroundColor: ['rgba(244, 63, 94, 0.7)', 'rgba(100, 116, 139, 0.5)', 'rgba(16, 185, 129, 0.7)'],
        borderColor: ['#f43f5e', '#64748b', '#10b981'],
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.04)' } },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Performance Charts ────────────────────────────────────────────
function renderPerformanceCharts() {
  if (!globalMetrics) return;

  // Cost Curve
  const curve = globalMetrics.cost_curve || [];
  destroyChart('chart-cost-curve');
  chartInstances['chart-cost-curve'] = new Chart(document.getElementById('chart-cost-curve'), {
    type: 'line',
    data: {
      labels: curve.map(c => c.threshold.toFixed(2)),
      datasets: [
        {
          label: 'Net ₹/Dispute',
          data: curve.map(c => c.net_value_per_dispute),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointHoverRadius: 7,
        },
        {
          label: 'Auto-Respond %',
          data: curve.map(c => c.auto_respond_pct * 100),
          borderColor: '#3b82f6',
          tension: 0.3,
          pointRadius: 4,
          yAxisID: 'y1',
        },
        {
          label: 'Win Rate %',
          data: curve.map(c => c.win_rate_at_threshold * 100),
          borderColor: '#f59e0b',
          tension: 0.3,
          pointRadius: 4,
          yAxisID: 'y1',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      scales: {
        y: { title: { display: true, text: 'Net ₹/Dispute' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y1: { position: 'right', title: { display: true, text: 'Percent' }, grid: { display: false } },
        x: { title: { display: true, text: 'Confidence Threshold' }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { labels: { boxWidth: 12 } } }
    }
  });

  // Feature Importances
  const fi = globalMetrics.top_feature_importances || {};
  const fiLabels = Object.keys(fi);
  const fiData = Object.values(fi);
  destroyChart('chart-features');
  chartInstances['chart-features'] = new Chart(document.getElementById('chart-features'), {
    type: 'bar',
    data: {
      labels: fiLabels.map(l => l.replace(/_/g, ' ')),
      datasets: [{
        data: fiData,
        backgroundColor: 'rgba(99, 102, 241, 0.6)',
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, title: { display: true, text: 'Importance' } },
        y: { grid: { display: false } }
      }
    }
  });

  // Cost curve table
  const tbody = document.getElementById('cost-curve-tbody');
  tbody.innerHTML = '';
  curve.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.threshold.toFixed(2)}</td>
      <td>${(row.auto_respond_pct * 100).toFixed(1)}%</td>
      <td>${(row.win_rate_at_threshold * 100).toFixed(1)}%</td>
      <td>${row.tp}</td>
      <td>${row.fp}</td>
      <td>${row.fn}</td>
      <td>₹${row.net_value.toLocaleString('en-IN')}</td>
      <td>₹${row.net_value_per_dispute.toFixed(0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Monitoring Drift ──────────────────────────────────────────────
async function fetchMonitoringDrift() {
  try {
    const res = await fetch('/api/monitoring/drift?window=200');
    if (!res.ok) return;
    const data = await res.json();
    renderMonitoringData(data);
  } catch (err) {
    console.warn('Monitoring fetch:', err);
  }
}

function renderMonitoringData(data) {
  document.getElementById('mon-window').textContent = data.window_size || '--';
  document.getElementById('mon-conf').textContent = data.confidence ? data.confidence.mean.toFixed(3) : '--';
  document.getElementById('mon-evidence').textContent = data.evidence_strength ? data.evidence_strength.mean.toFixed(3) : '--';
  document.getElementById('mon-winprob').textContent = data.win_probability ? data.win_probability.mean.toFixed(3) : '--';
  document.getElementById('mon-autorate').textContent = data.auto_rate_pct ? `${data.auto_rate_pct}%` : '--';

  // RC Distribution chart
  const rcDist = data.reason_code_distribution || {};
  const rcLabels = Object.keys(rcDist);
  const rcData = Object.values(rcDist);
  const rcColors = ['#6366f1', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

  destroyChart('chart-mon-rc');
  chartInstances['chart-mon-rc'] = new Chart(document.getElementById('chart-mon-rc'), {
    type: 'bar',
    data: {
      labels: rcLabels,
      datasets: [{
        data: rcData,
        backgroundColor: rcColors.slice(0, rcLabels.length).map(c => c + 'aa'),
        borderColor: rcColors.slice(0, rcLabels.length),
        borderWidth: 1,
        borderRadius: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.04)' } },
        x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } }
      }
    }
  });

  // Action Distribution
  const actionDist = data.action_distribution || {};
  destroyChart('chart-mon-action');
  chartInstances['chart-mon-action'] = new Chart(document.getElementById('chart-mon-action'), {
    type: 'doughnut',
    data: {
      labels: Object.keys(actionDist),
      datasets: [{
        data: Object.values(actionDist),
        backgroundColor: ['rgba(16, 185, 129, 0.7)', 'rgba(245, 158, 11, 0.7)'],
        borderWidth: 0,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }
    }
  });
}

// ── Case Explorer ─────────────────────────────────────────────────
function populateCaseDropdown() {
  const select = document.getElementById('case-select');
  select.innerHTML = '<option value="">Select a dispute ID...</option>';
  globalPredictions.slice(0, 50).forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.dispute_id;
    opt.textContent = `${item.dispute_id} (Actual: ${item.actual} → Pred: ${item.predicted})`;
    select.appendChild(opt);
  });
}

function inspectCase(id) {
  if (!id) return;
  const found = globalPredictions.find(p => p.dispute_id === id);
  if (found) {
    document.getElementById('case-json-display').textContent = JSON.stringify(found, null, 2);
  }
}

// ── Demo Presets ──────────────────────────────────────────────────
function loadPreset(type) {
  const payload = type === 'strong' ? PRESET_STRONG : PRESET_WEAK;
  document.getElementById('dispute-json-input').value = JSON.stringify(payload, null, 2);
}

// ── Process Dispute with Step-Reveal ──────────────────────────────
async function processCustomDispute() {
  const raw = document.getElementById('dispute-json-input').value;
  const outPre = document.getElementById('demo-result-output');
  const badgeContainer = document.getElementById('action-badge-container');
  const stepsContainer = document.getElementById('pipeline-steps');
  const runBtn = document.getElementById('run-pipeline-btn');

  // Reset
  stepsContainer.innerHTML = '';
  outPre.textContent = '';
  badgeContainer.innerHTML = '<span class="spinner"></span>';
  runBtn.disabled = true;
  runBtn.textContent = '⏳ Processing...';

  try {
    const payload = JSON.parse(raw);

    // Step 1: Show input received
    await revealStep(stepsContainer, 'Step 1 — Input Received', `Dispute <strong>${payload.dispute_id || 'N/A'}</strong> · ₹${(payload.dispute_amount || 0).toLocaleString('en-IN')} ${payload.currency || 'INR'} · ${payload.card_network || 'Unknown'} network`, '', 300);

    // Make the API call
    const res = await fetch('/api/disputes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'API Error');
    }

    const data = await res.json();

    // Step 2: Classification
    const clf = data.classification || {};
    const topK = clf.top_k_predictions || [];
    let topKHtml = topK.map((tk, i) => {
      const pct = (tk.confidence * 100).toFixed(1);
      return `<div style="margin-top:4px;"><span style="color:var(--text-tertiary);font-size:0.78rem;">#${i+1}</span> <strong>${tk.reason_code}</strong> <span style="color:var(--accent-indigo);">${pct}%</span>
        <div class="confidence-bar-track"><div class="confidence-bar-fill" style="width:${pct}%"></div></div></div>`;
    }).join('');
    await revealStep(stepsContainer, 'Step 2 — Reason Code Classification',
      `Primary: <strong>${clf.predicted_reason_code || 'N/A'}</strong> at ${((clf.confidence || 0) * 100).toFixed(1)}% confidence${topKHtml}`,
      'step-success', 400);

    // Step 3: Evidence retrieval
    const ev = data.evidence || {};
    const evPkg = ev.evidence_package || {};
    const compellingList = (evPkg.compelling || []).map(e => `✅ ${e.field}`).join(', ') || 'None';
    const supportingList = (evPkg.supporting || []).map(e => `✅ ${e.field}`).join(', ') || 'None';
    const missingList = (evPkg.missing || []).map(m => `❌ ${m}`).join(', ') || 'None';
    await revealStep(stepsContainer, 'Step 3 — Evidence Retrieval',
      `Strength: <strong>${((ev.evidence_strength || 0) * 100).toFixed(0)}%</strong> · Compelling: ${compellingList} · Supporting: ${supportingList} · Missing: ${missingList}`,
      ev.evidence_strength >= 0.6 ? 'step-success' : 'step-warning', 400);

    // Step 4: Win probability
    const winProb = data.win_probability || 0;
    await revealStep(stepsContainer, 'Step 4 — Win Probability',
      `<div class="gauge-container" style="padding:0.5rem;"><div class="gauge-value" id="gauge-win-prob">0%</div><div class="gauge-label">Merchant Win Probability</div></div>`,
      winProb >= 0.5 ? 'step-success' : 'step-warning', 200);
    animateGauge('gauge-win-prob', winProb * 100);

    // Step 5: Expected value
    const expVal = data.expected_value_inr || 0;
    await revealStep(stepsContainer, 'Step 5 — Business Value',
      `Expected Recovery: <strong>₹${expVal.toLocaleString('en-IN')}</strong> per dispute`,
      expVal > 0 ? 'step-success' : 'step-danger', 400);

    // Step 6: Decision
    const action = data.response ? data.response.action : 'UNKNOWN';
    const isAuto = action === 'AUTO_SUBMIT';
    await revealStep(stepsContainer, 'Step 6 — Decision',
      `<span style="font-size:1.1rem; font-weight:800;">${isAuto ? '🟢 AUTO_SUBMIT' : '🟡 HUMAN_REVIEW'}</span>`,
      isAuto ? 'step-success' : 'step-warning', 300);

    // Badge
    badgeContainer.innerHTML = `<span class="action-badge ${isAuto ? 'auto-submit' : 'human-review'}">${isAuto ? '🟢 AUTO_SUBMIT' : '🟡 HUMAN_REVIEW'}</span>`;

    // Full output
    outPre.textContent = JSON.stringify(data, null, 2);

  } catch (err) {
    stepsContainer.innerHTML += `<div class="pipeline-step revealed step-danger"><div class="step-label">Error</div><div class="step-content">${err.message}</div></div>`;
    badgeContainer.innerHTML = '';
    outPre.textContent = `Error: ${err.message}`;
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = '⚡ Run AI Pipeline';
  }
}

// ── Step Reveal Helper ────────────────────────────────────────────
function revealStep(container, label, content, extraClass, delay) {
  return new Promise(resolve => {
    const div = document.createElement('div');
    div.className = `pipeline-step ${extraClass}`;
    div.innerHTML = `<div class="step-label">${label}</div><div class="step-content">${content}</div>`;
    container.appendChild(div);

    setTimeout(() => {
      div.classList.add('revealed');
      resolve();
    }, delay);
  });
}

// ── Gauge Animation ───────────────────────────────────────────────
function animateGauge(elementId, target) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const duration = 800;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = (target * eased).toFixed(1);
    el.textContent = `${current}%`;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// ── Utility ───────────────────────────────────────────────────────
function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}
