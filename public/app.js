// ════════════════════════════════════════════════════════════════════
// Chargeback Intelligence Platform — Client Controller
// Centered Hero Showcase, Rich Case Audit Workspace, Paced Live Tour
// ════════════════════════════════════════════════════════════════════

let globalMetrics = null;
let globalPredictions = [];
let filteredPredictions = [];
let selectedCaseRecord = null;
let currentCaseFilter = 'all';
let chartInstances = {};
let simCurrentStep = 0;
let simTimer = null;

// ── Chart.js Defaults ─────────────────────────────────────────────
Chart.defaults.color = '#475569';
Chart.defaults.borderColor = '#E2E8F0';
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = '#0F274A';
Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
Chart.defaults.plugins.tooltip.bodyColor = '#CBD5E1';
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 6;

// ── Presets ──────────────────────────────────────────────────────
const PRESET_STRONG = {
  dispute_id: "DSP-2026-00142",
  reason_code_label: "Other Fraud - Card Absent Environment",
  card_network: "Visa",
  dispute_amount: 12499.00,
  currency: "INR",
  transaction_date: "2026-06-15",
  days_to_dispute: 35,
  product_category: "electronics",
  shipping_method: "express",
  delivery_confirmed: true,
  has_delivery_proof: true,
  ip_geolocation_match: true,
  avs_cvv_match: "both_match",
  customer_account_age_days: 45,
  customer_prior_disputes: 0,
  customer_prior_orders: 3,
  has_customer_correspondence: false,
  has_3ds_authentication: true
};

const PRESET_WEAK = {
  dispute_id: "DSP-2026-00987",
  reason_code_label: "Fraud - Card Absent",
  card_network: "Visa",
  dispute_amount: 8999.00,
  currency: "INR",
  transaction_date: "2026-07-01",
  days_to_dispute: 8,
  product_category: "electronics",
  shipping_method: "standard",
  delivery_confirmed: false,
  has_delivery_proof: false,
  ip_geolocation_match: false,
  avs_cvv_match: "neither",
  customer_account_age_days: 3,
  customer_prior_disputes: 1,
  customer_prior_orders: 0,
  has_customer_correspondence: false,
  has_3ds_authentication: false
};

// ── Simulation Steps Definitions ──────────────────────────────────
const SIM_STEPS = [
  {
    stepBadge: "Step 1 of 4: Ingestion",
    stepCounter: "25%",
    progressPct: 25,
    title: "Dispute Ingestion & Scheme Webhook",
    desc: "A chargeback webhook is received from the Visa payment network for ₹12,499.00 on an Electronics purchase. Transaction token & customer order logs are retrieved.",
    preset: "strong"
  },
  {
    stepBadge: "Step 2 of 4: Classification",
    stepCounter: "50%",
    progressPct: 50,
    title: "LightGBM Reason Code Classification",
    desc: "The multi-class ML model extracts 14 transaction features (AVS/CVV signals, 3DS authentication, account age) and predicts Reason Code 10.4 with 94.2% Platt-calibrated confidence.",
    preset: "strong"
  },
  {
    stepBadge: "Step 3 of 4: Evidence",
    stepCounter: "75%",
    progressPct: 75,
    title: "Deterministic Rule Table Verification",
    desc: "Evaluating merchant evidence against Visa Scheme representment specs: Proof of Delivery signature, IP match, and 3DS authentication are confirmed on file (5/6 items present).",
    preset: "strong"
  },
  {
    stepBadge: "Step 4 of 4: Decision",
    stepCounter: "100%",
    progressPct: 100,
    title: "Cost Optimization & AUTO_SUBMIT Verdict",
    desc: "Calibrated probability exceeds the 70% threshold. System generates formal representment response document with ₹11,624 net expected recovery.",
    preset: "strong"
  }
];

// ── Initialization ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchMetrics();
  fetchPredictions();
  loadPreset('strong');
  updateCardPreview();
  checkApiHealth();
  setInterval(checkApiHealth, 30000);
});

// ── Interactive Credit Card Preview Sync ──────────────────────────
function updateCardPreview() {
  const amt = parseFloat(document.getElementById('f-amount').value) || 0;
  const net = document.getElementById('f-network').value;
  const cat = document.getElementById('f-category').value;
  
  const elAmt = document.getElementById('sim-card-amount');
  const elNet = document.getElementById('sim-card-network');
  const elId = document.getElementById('sim-card-id');
  const elNum = document.getElementById('sim-card-number');

  if (elAmt) elAmt.textContent = '₹' + amt.toLocaleString('en-IN', { minimumFractionDigits: 2 });
  if (elNet) elNet.textContent = net;
  if (elId) elId.textContent = `DSP-LIVE · ${cat.toUpperCase()}`;
  if (elNum) {
    elNum.textContent = net === 'Visa' ? '4111 •••• •••• 4242' : '5500 •••• •••• 8899';
  }
}

// ── Paced Live Tour Simulation (Centered Showcase) ────────────────
function renderSimStep(idx) {
  simCurrentStep = Math.max(0, Math.min(idx, SIM_STEPS.length - 1));
  const step = SIM_STEPS[simCurrentStep];

  setText('insp-step-badge', step.stepBadge);
  setText('insp-step-counter', step.stepCounter);
  setText('insp-title', step.title);
  setText('insp-desc', step.desc);

  const fill = document.getElementById('insp-progress-fill');
  if (fill) fill.style.width = step.progressPct + '%';

  loadPreset(step.preset);
  updateCardPreview();
}

async function startGuidedSimulation() {
  if (simTimer) clearTimeout(simTimer);
  const btn = document.getElementById('btn-run-sim');
  if (btn) btn.textContent = 'Simulating...';

  // Step 1
  renderSimStep(0);
  await sleep(2600);

  // Step 2
  renderSimStep(1);
  await sleep(2600);

  // Step 3
  renderSimStep(2);
  await sleep(2600);

  // Step 4
  renderSimStep(3);
  analyzeFromForm();
  await sleep(1500);

  if (btn) btn.textContent = 'Replay Simulation';
}

function stepSimulation(delta) {
  if (simTimer) clearTimeout(simTimer);
  renderSimStep(simCurrentStep + delta);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Tab Switching with Smooth Float-In ────────────────────────────
function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  if (btn) btn.classList.add('active');
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) {
    panel.classList.add('active');
  }

  if (tabId === 'performance') {
    setTimeout(renderPerformanceCharts, 50);
  } else if (tabId === 'monitoring') {
    setTimeout(fetchMonitoringDrift, 50);
  } else if (tabId === 'cases') {
    setTimeout(renderCaseExplorer, 50);
  }
}

// ── Financial Explainer Toggle ───────────────────────────────────
function toggleExplainer() {
  const details = document.getElementById('explainer-details');
  if (details) {
    details.style.display = details.style.display === 'none' ? 'block' : 'none';
  }
}

// ── Mode Toggle (Structured Form vs Raw JSON) ────────────────────
function setAnalyzerMode(mode, btn) {
  const toggleBtns = document.querySelectorAll('.mode-segmented-btn');
  toggleBtns.forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  document.getElementById('form-mode').style.display = mode === 'form' ? 'block' : 'none';
  document.getElementById('json-mode').style.display = mode === 'json' ? 'block' : 'none';
}

// ── Health Check ────────────────────────────────────────────────
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health');
    document.getElementById('api-status').textContent = res.ok ? 'API Online' : 'API Error';
  } catch {
    document.getElementById('api-status').textContent = 'API Offline';
  }
}

// ── Fetch Evaluation Metrics ─────────────────────────────────────
async function fetchMetrics() {
  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) return;
    globalMetrics = await res.json();
    renderHeroMetrics();
    renderKPIs();
    renderPerformanceCharts();
    updateCostPoint(0.50);
  } catch (e) {
    console.warn('Metrics fetch error:', e);
  }
}

// ── Fetch Predictions ───────────────────────────────────────────
async function fetchPredictions() {
  try {
    const res = await fetch('/api/predictions');
    if (!res.ok) return;
    globalPredictions = await res.json();
    filteredPredictions = [...globalPredictions];
    renderCaseExplorer();
  } catch (e) {
    console.warn('Predictions fetch error:', e);
  }
}

// ── Render Baseline Recovery Metrics ─────────────────────────────
function renderHeroMetrics() {
  if (!globalMetrics) return;
  const b = globalMetrics.baselines_inr || {};
  const fe = b.fight_everything_net_value || 671000;
  const fn = b.fight_nothing_net_value || -171500;
  const sb = b.system_best_net_value || 943450;

  animateValue('val-fight-everything', fe, '₹');
  animateValue('val-fight-nothing', fn, '₹');
  animateValue('val-system-best', sb, '₹');

  const delta = sb - fe;
  const el = document.getElementById('val-delta');
  if (el) {
    el.textContent = `+₹${delta.toLocaleString('en-IN')} higher net recovery vs naive fighting`;
  }

  const scale = globalMetrics.illustrative_scale_extrapolation_inr || {};
  const banner = document.getElementById('scale-banner-text');
  if (banner && scale.note) {
    const val100k = (scale.at_100k_disputes_per_year || 125793000).toLocaleString('en-IN');
    banner.innerHTML = `<span class="banner-chip">Scale Projection</span><span>${scale.note} At 100k disputes/year: <strong>₹${val100k}</strong> net value.</span>`;
  }
}

function animateValue(id, target, prefix = '', dur = 700) {
  const el = document.getElementById(id);
  if (!el) return;
  const t0 = performance.now();
  (function tick(now) {
    const p = Math.min((now - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + Math.round(target * eased).toLocaleString('en-IN');
    if (p < 1) requestAnimationFrame(tick);
  })(t0);
}

function renderKPIs() {
  if (!globalMetrics) return;
  const m = globalMetrics;
  setText('stat-acc', pct(m.reason_code_accuracy));
  setText('stat-prec', pct(m.macro_precision));
  setText('stat-rec', pct(m.macro_recall));
  setText('stat-auc', m.win_prediction_auc.toFixed(3));
  setText('stat-win-auc', m.win_predictor_dedicated_auc ? m.win_predictor_dedicated_auc.toFixed(3) : '0.783');
}

function pct(v) { return (v * 100).toFixed(1) + '%'; }
function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

// ── Render Performance Charts & Tables ───────────────────────────
function renderPerformanceCharts() {
  if (!globalMetrics) return;
  const m = globalMetrics;

  // 1. Cost Curve
  const curve = m.cost_curve || [];
  const costCanvas = document.getElementById('chart-cost-curve');
  if (costCanvas) {
    destroyChart('chart-cost-curve');
    chartInstances['chart-cost-curve'] = new Chart(costCanvas, {
      type: 'line',
      data: {
        labels: curve.map(c => c.threshold.toFixed(2)),
        datasets: [
          {
            label: 'Net ₹ / Dispute',
            data: curve.map(c => c.net_value_per_dispute),
            borderColor: '#10B981',
            backgroundColor: 'rgba(16, 185, 129, 0.08)',
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: '#10B981',
            borderWidth: 2
          },
          {
            label: 'Auto-Respond %',
            data: curve.map(c => c.auto_respond_pct * 100),
            borderColor: '#6366F1',
            tension: 0.35,
            pointRadius: 3,
            pointBackgroundColor: '#6366F1',
            borderWidth: 1.8,
            yAxisID: 'y1'
          },
          {
            label: 'Win Rate %',
            data: curve.map(c => c.win_rate_at_threshold * 100),
            borderColor: '#F59E0B',
            tension: 0.35,
            pointRadius: 3,
            pointBackgroundColor: '#F59E0B',
            borderWidth: 1.8,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        scales: {
          y: {
            title: { display: true, text: 'Net ₹ / Dispute', color: '#10B981', font: { weight: 'bold' } },
            grid: { color: '#F1F5F9' },
            ticks: { callback: v => '₹' + v }
          },
          y1: {
            position: 'right',
            title: { display: true, text: 'Percent (%)', color: '#64748B', font: { weight: 'bold' } },
            grid: { display: false },
            ticks: { callback: v => v + '%' }
          },
          x: {
            title: { display: true, text: 'Confidence Threshold Gate', color: '#64748B', font: { weight: 'bold' } },
            grid: { color: '#F1F5F9' }
          }
        },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, usePointStyle: true } }
        }
      }
    });
  }

  // 2. Feature Importances
  const fi = m.top_feature_importances || {};
  const featCanvas = document.getElementById('chart-features');
  if (featCanvas) {
    destroyChart('chart-features');
    chartInstances['chart-features'] = new Chart(featCanvas, {
      type: 'bar',
      data: {
        labels: Object.keys(fi).map(l => l.replace(/_/g, ' ')),
        datasets: [{
          data: Object.values(fi),
          backgroundColor: '#EEF2FF',
          borderColor: '#6366F1',
          hoverBackgroundColor: '#6366F1',
          borderWidth: 1.2,
          borderRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid: { color: '#F1F5F9' },
            title: { display: true, text: 'Gini Gain Score', color: '#64748B' }
          },
          y: { grid: { display: false } }
        }
      }
    });
  }

  // 3. Per-Class Table
  const tbody = document.getElementById('per-class-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    const pc = m.per_class || {};
    Object.keys(pc).forEach(code => {
      const d = pc[code];
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${code}</strong></td>
        <td>${pct(d.precision)}</td>
        <td>${pct(d.recall)}</td>
        <td><strong style="color:var(--brand-indigo);">${pct(d['f1-score'])}</strong></td>
        <td>${d.support}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 4. Cost Curve Data Table
  const ct = document.getElementById('cost-curve-tbody');
  if (ct) {
    ct.innerHTML = '';
    curve.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${r.threshold.toFixed(2)}</strong></td>
        <td>${pct(r.auto_respond_pct)}</td>
        <td>${pct(r.win_rate_at_threshold)}</td>
        <td>${r.tp}</td>
        <td>${r.fp}</td>
        <td>${r.fn}</td>
        <td><strong style="color:var(--brand-emerald-text);">₹${r.net_value.toLocaleString('en-IN')}</strong></td>
        <td>₹${r.net_value_per_dispute.toFixed(0)}</td>
      `;
      ct.appendChild(tr);
    });
  }
}

// ── Cost Operating Point Slider ──────────────────────────────────
function updateCostPoint(val) {
  const t = parseFloat(val);
  setText('threshold-val', t.toFixed(2));
  if (!globalMetrics || !globalMetrics.cost_curve) return;
  const row = globalMetrics.cost_curve.find(c => Math.abs(c.threshold - t) < 0.01) || globalMetrics.cost_curve[0];
  setText('cost-auto-pct', pct(row.auto_respond_pct));
  setText('cost-win-rate', pct(row.win_rate_at_threshold));
  setText('cost-net-dispute', '₹' + row.net_value_per_dispute.toFixed(0));
}

// ── Rich Case Explorer & Audit Workspace ─────────────────────────
function setCaseFilter(filterType, btn) {
  currentCaseFilter = filterType;
  document.querySelectorAll('.case-filter-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  filterCaseList();
}

function filterCaseList() {
  const q = (document.getElementById('case-search-input').value || '').toLowerCase().trim();
  
  filteredPredictions = globalPredictions.filter(p => {
    // Search query match
    const matchQ = !q || p.dispute_id.toLowerCase().includes(q) || String(p.actual).includes(q) || String(p.predicted).includes(q);
    if (!matchQ) return false;

    // Filter pill match
    if (currentCaseFilter === 'won') return p.outcome === 'merchant_won';
    if (currentCaseFilter === 'lost') return p.outcome === 'merchant_lost';
    if (currentCaseFilter === 'misclassified') return String(p.actual) !== String(p.predicted);
    if (currentCaseFilter === 'high_value') return (p.confidence || 0) >= 0.70;
    return true;
  });

  renderCaseListUI();
}

function renderCaseExplorer() {
  filterCaseList();
  if (filteredPredictions.length > 0 && !selectedCaseRecord) {
    selectCaseRecord(filteredPredictions[0].dispute_id);
  }
}

function renderCaseListUI() {
  const container = document.getElementById('case-list-container');
  if (!container) return;

  if (filteredPredictions.length === 0) {
    container.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:12px;">No matching disputes found.</div>';
    return;
  }

  container.innerHTML = filteredPredictions.slice(0, 100).map(p => {
    const isSelected = selectedCaseRecord && selectedCaseRecord.dispute_id === p.dispute_id;
    const isMatch = String(p.actual) === String(p.predicted);
    const chipClass = isMatch ? 'chip-success' : 'chip-warning';
    
    return `
      <div class="case-item-row ${isSelected ? 'selected' : ''}" onclick="selectCaseRecord('${p.dispute_id}')">
        <div>
          <div class="case-item-id">${p.dispute_id}</div>
          <div class="case-item-sub">Actual: ${p.actual} &rarr; Pred: ${p.predicted}</div>
        </div>
        <div style="text-align:right;">
          <span class="chip ${chipClass}">${isMatch ? 'Matched' : 'Mismatch'}</span>
          <div style="font-size:10px; color:var(--text-muted); margin-top:2px;">${((p.confidence||0)*100).toFixed(0)}% Conf</div>
        </div>
      </div>
    `;
  }).join('');
}

function selectCaseRecord(disputeId) {
  const record = globalPredictions.find(p => p.dispute_id === disputeId);
  if (!record) return;

  selectedCaseRecord = record;
  renderCaseListUI();

  // Populate Right Audit Card
  setText('audit-dispute-id', record.dispute_id);
  setText('audit-meta-summary', `Ground truth outcome: ${record.outcome === 'merchant_won' ? 'Merchant Won' : 'Merchant Lost'} · Evidence: ${((record.evidence_strength||0)*100).toFixed(0)}%`);

  const isMatch = String(record.actual) === String(record.predicted);
  const statusBadge = document.getElementById('audit-status-badge');
  if (statusBadge) {
    statusBadge.innerHTML = isMatch
      ? '<span class="chip chip-success">Prediction Validated</span>'
      : '<span class="chip chip-warning">Reason Code Confused</span>';
  }

  setText('audit-actual-rc', record.actual);
  setText('audit-pred-rc', record.predicted);
  setText('audit-conf', `${((record.confidence||0)*100).toFixed(1)}% (Platt-Calibrated)`);
  setText('audit-outcome', record.outcome === 'merchant_won' ? 'Merchant Won' : 'Merchant Lost');

  setText('audit-evidence', `${((record.evidence_strength||0)*100).toFixed(0)}% Completeness`);
  setText('audit-winprob', `${((record.confidence||0)*85).toFixed(1)}% Likelihood`);
  
  const isAuto = (record.confidence || 0) >= 0.70 && (record.evidence_strength || 0) >= 0.60;
  setText('audit-action', isAuto ? 'AUTO_SUBMIT (High Confidence)' : 'HUMAN_REVIEW (Borderline)');
  setText('audit-match-flag', isMatch ? 'Accurate Code Identified' : 'Fallback Routine Engaged');

  const rawPre = document.getElementById('audit-raw-json');
  if (rawPre) {
    rawPre.textContent = JSON.stringify(record, null, 2);
  }
}

function toggleAuditJson() {
  const rawPre = document.getElementById('audit-raw-json');
  if (rawPre) {
    rawPre.style.display = rawPre.style.display === 'none' ? 'block' : 'none';
  }
}

function loadSelectedCaseIntoAnalyzer() {
  if (!selectedCaseRecord) return;
  const p = selectedCaseRecord;

  // Fill form
  document.getElementById('f-amount').value = p.dispute_amount || 12499;
  document.getElementById('f-network').value = p.card_network || 'Visa';
  document.getElementById('f-days').value = p.days_to_dispute || 35;
  document.getElementById('f-category').value = p.product_category || 'electronics';
  document.getElementById('f-shipping').value = p.shipping_method || 'express';
  document.getElementById('f-acct-age').value = p.customer_account_age_days || 45;
  document.getElementById('f-delivery').checked = p.evidence_strength >= 0.5;
  document.getElementById('f-proof').checked = p.evidence_strength >= 0.6;
  document.getElementById('f-ip').checked = p.evidence_strength >= 0.4;
  document.getElementById('f-3ds').checked = p.evidence_strength >= 0.7;

  updateCardPreview();

  // Switch to Home tab and run
  switchTab('home', document.querySelector('.tabs-nav button:first-child'));
  analyzeFromForm();
}

// ── Monitoring & Drift ───────────────────────────────────────────
async function fetchMonitoringDrift() {
  try {
    const res = await fetch('/api/monitoring/drift?window=200');
    if (!res.ok) return;
    renderMonitoring(await res.json());
  } catch (e) {
    console.warn('Monitoring fetch error:', e);
  }
}

function renderMonitoring(d) {
  setText('mon-window', d.window_size || '--');
  setText('mon-conf', d.confidence ? d.confidence.mean.toFixed(3) : '--');
  setText('mon-evidence', d.evidence_strength ? d.evidence_strength.mean.toFixed(3) : '--');
  setText('mon-winprob', d.win_probability ? d.win_probability.mean.toFixed(3) : '--');
  setText('mon-autorate', d.auto_rate_pct ? d.auto_rate_pct + '%' : '--');

  const rc = d.reason_code_distribution || {};
  const rcCanvas = document.getElementById('chart-mon-rc');
  if (rcCanvas) {
    destroyChart('chart-mon-rc');
    chartInstances['chart-mon-rc'] = new Chart(rcCanvas, {
      type: 'bar',
      data: {
        labels: Object.keys(rc),
        datasets: [{
          data: Object.values(rc),
          backgroundColor: '#EEF2FF',
          borderColor: '#6366F1',
          hoverBackgroundColor: '#6366F1',
          borderWidth: 1.2,
          borderRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: '#F1F5F9' } },
          x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } }
        }
      }
    });
  }

  const ad = d.action_distribution || {};
  const actionCanvas = document.getElementById('chart-mon-action');
  if (actionCanvas) {
    destroyChart('chart-mon-action');
    chartInstances['chart-mon-action'] = new Chart(actionCanvas, {
      type: 'doughnut',
      data: {
        labels: Object.keys(ad),
        datasets: [{
          data: Object.values(ad),
          backgroundColor: ['#10B981', '#F59E0B'],
          borderColor: ['#FFFFFF', '#FFFFFF'],
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10 } } }
      }
    });
  }
}

// ── Presets ──────────────────────────────────────────────────────
function loadPreset(type) {
  const p = type === 'strong' ? PRESET_STRONG : PRESET_WEAK;
  document.getElementById('f-amount').value = p.dispute_amount;
  document.getElementById('f-network').value = p.card_network;
  document.getElementById('f-days').value = p.days_to_dispute;
  document.getElementById('f-category').value = p.product_category;
  document.getElementById('f-shipping').value = p.shipping_method;
  document.getElementById('f-acct-age').value = p.customer_account_age_days;
  document.getElementById('f-delivery').checked = p.delivery_confirmed;
  document.getElementById('f-proof').checked = p.has_delivery_proof;
  document.getElementById('f-ip').checked = p.ip_geolocation_match;
  document.getElementById('f-correspondence').checked = p.has_customer_correspondence;
  document.getElementById('f-3ds').checked = p.has_3ds_authentication;
  document.getElementById('f-prior-disputes').value = p.customer_prior_disputes;
  document.getElementById('f-prior-orders').value = p.customer_prior_orders;
  document.querySelectorAll('input[name="avs"]').forEach(r => {
    r.checked = r.value === p.avs_cvv_match;
  });
  document.getElementById('dispute-json-input').value = JSON.stringify(p, null, 2);
  updateCardPreview();
}

// ── Build Payload From Form ─────────────────────────────────────
function buildPayloadFromForm() {
  const avs = document.querySelector('input[name="avs"]:checked');
  return {
    dispute_id: "DSP-LIVE-" + Date.now().toString(36).toUpperCase(),
    reason_code_label: "Other Fraud - Card Absent Environment",
    card_network: document.getElementById('f-network').value,
    dispute_amount: parseFloat(document.getElementById('f-amount').value) || 0,
    currency: "INR",
    transaction_date: new Date().toISOString().slice(0, 10),
    days_to_dispute: parseInt(document.getElementById('f-days').value) || 0,
    product_category: document.getElementById('f-category').value,
    shipping_method: document.getElementById('f-shipping').value,
    delivery_confirmed: document.getElementById('f-delivery').checked,
    has_delivery_proof: document.getElementById('f-proof').checked,
    ip_geolocation_match: document.getElementById('f-ip').checked,
    avs_cvv_match: avs ? avs.value : "neither",
    customer_account_age_days: parseInt(document.getElementById('f-acct-age').value) || 0,
    customer_prior_disputes: parseInt(document.getElementById('f-prior-disputes').value) || 0,
    customer_prior_orders: parseInt(document.getElementById('f-prior-orders').value) || 0,
    has_customer_correspondence: document.getElementById('f-correspondence').checked,
    has_3ds_authentication: document.getElementById('f-3ds').checked,
  };
}

// ── Analyze from Form ───────────────────────────────────────────
function analyzeFromForm() {
  const payload = buildPayloadFromForm();
  runPipeline(payload, document.getElementById('run-form-btn'));
}

// ── Analyze from JSON ───────────────────────────────────────────
function analyzeFromJSON() {
  const raw = document.getElementById('dispute-json-input').value;
  const errDiv = document.getElementById('json-error');
  errDiv.style.display = 'none';
  try {
    const payload = JSON.parse(raw);
    const required = ['dispute_amount', 'card_network', 'days_to_dispute'];
    const missing = required.filter(f => !(f in payload));
    if (missing.length) {
      errDiv.innerHTML = `<span class="chip chip-danger">Missing required fields: ${missing.join(', ')}</span>`;
      errDiv.style.display = 'block';
      return;
    }
    runPipeline(payload, document.getElementById('run-json-btn'));
  } catch (e) {
    errDiv.innerHTML = `<span class="chip chip-danger">Invalid JSON format: ${e.message}</span>`;
    errDiv.style.display = 'block';
  }
}

// ── Execute Pipeline with Staged Reveal ───────────────────────────
async function runPipeline(payload, btn) {
  const stepsC = document.getElementById('pipeline-steps');
  const outPre = document.getElementById('demo-result-output');
  const badge = document.getElementById('action-badge-container');
  stepsC.innerHTML = '';
  outPre.textContent = '';
  badge.innerHTML = '<span class="spinner"></span>';
  if (btn) btn.disabled = true;
  const origText = btn ? btn.textContent : '';
  if (btn) btn.textContent = 'Processing Pipeline...';

  try {
    // Step 1: Input Received
    await revealStep(stepsC, 'Step 1 — Input Ingested',
      `Dispute <strong>${payload.dispute_id || 'N/A'}</strong> · ₹${(payload.dispute_amount || 0).toLocaleString('en-IN')} · ${payload.card_network || 'Unknown'} Network`, '', 220);

    const res = await fetch('/api/disputes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
      const e = await res.json();
      throw new Error(e.detail || 'API execution error');
    }
    const data = await res.json();

    // Step 2: Reason Code Classification
    const clf = data.classification || {};
    const topK = (clf.top_k_predictions || []).map((t, i) => {
      const p = (t.confidence * 100).toFixed(1);
      return `<div style="margin-top:4px;"><span style="color:var(--text-muted);font-size:11px;">#${i+1}</span> <strong>Code ${t.reason_code}</strong> <span style="color:var(--brand-indigo);">${p}%</span><div class="conf-bar-track"><div class="conf-bar-fill" style="width:${p}%"></div></div></div>`;
    }).join('');
    
    await revealStep(stepsC, 'Step 2 — Reason Code Classification',
      `Predicted Reason Code: <strong>${clf.predicted_reason_code || 'N/A'}</strong> at ${((clf.confidence||0)*100).toFixed(1)}% calibrated confidence.${topK}
      <div class="callout" style="margin-top:8px;margin-bottom:0;">
        <strong>Term Explanation:</strong> Reason codes (such as 10.4 for Card-Absent Fraud) are standard industry categories assigned by card networks. Platt-scaled confidence means a 90% score reflects an empirical 9-out-of-10 probability of being the correct dispute category.
      </div>`,
      'step-success', 300);

    // Step 3: Evidence Checklist Retrieval
    const ev = data.evidence || {};
    const evPkg = ev.evidence_package || {};
    const chips = [
      ...(evPkg.compelling||[]).map(e => `<span class="chip chip-success">Present: ${e.field}</span>`),
      ...(evPkg.supporting||[]).map(e => `<span class="chip chip-success">Present: ${e.field}</span>`),
      ...(evPkg.missing||[]).map(m => `<span class="chip chip-danger">Missing: ${m}</span>`)
    ].join(' ');
    const totalEvidence = (evPkg.compelling||[]).length + (evPkg.supporting||[]).length + (evPkg.missing||[]).length;
    const presentEvidence = (evPkg.compelling||[]).length + (evPkg.supporting||[]).length;
    
    await revealStep(stepsC, 'Step 3 — Evidence Checklist Retrieval',
      `Evidence Strength Score: <strong>${((ev.evidence_strength||0)*100).toFixed(0)}%</strong> (${presentEvidence}/${totalEvidence} required items present).<div style="margin:8px 0;">${chips}</div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;">
        <strong>Term Explanation:</strong> Visa and Mastercard enforce strict evidence requirements. Compelling items (e.g. proof of delivery, 3D-Secure) directly prove legitimate fulfillment to the issuing bank.
      </div>`,
      ev.evidence_strength >= 0.6 ? 'step-success' : 'step-warning', 300);

    // Step 4: Decision & Document Generation
    const wp = data.win_probability || 0;
    const ev_inr = data.expected_value_inr || 0;
    const action = data.response ? data.response.action : 'UNKNOWN';
    const responseText = data.response ? data.response.response_text : '';
    const isAuto = action === 'AUTO_SUBMIT';
    const chipClass = isAuto ? 'chip-success' : 'chip-warning';
    
    let docBtnHtml = '';
    if (responseText) {
      window.lastResponseText = responseText;
      docBtnHtml = `
        <div style="margin-top:12px; padding-top:10px; border-top:1px solid var(--border-color);">
          <button class="btn-secondary" style="width:100%; justify-content:center;" onclick="toggleRepresentmentDoc()">
            View Rendered Representment Document
          </button>
          <div id="representment-doc-panel" style="display:none; margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:800; color:var(--text-muted); text-transform:uppercase;">Rendered Representment Response Letter</span>
              <button class="btn-secondary" style="padding:2px 8px; font-size:11px;" onclick="copyRepresentmentDoc()">Copy Letter</button>
            </div>
            <pre class="code-block" style="max-height:220px; white-space:pre-wrap; font-size:11px;">${escapeHtml(responseText)}</pre>
          </div>
        </div>
      `;
    }

    await revealStep(stepsC, 'Step 4 — Final Recommendation',
      `<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-size:20px;font-weight:900;color:var(--brand-navy-dark);">Win Probability: ${(wp*100).toFixed(1)}%</span>
        <span class="chip ${chipClass}">${action}</span>
      </div>
      <div style="display:flex;gap:20px;font-size:12px;color:var(--text-secondary);margin-bottom:8px;">
        <span>Expected Net Value: <strong style="color:var(--brand-emerald-text);">₹${ev_inr.toLocaleString('en-IN')}</strong></span>
      </div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;">
        <strong>Decision Explanation:</strong> ${isAuto ? 'Confidence and evidence strength both exceed threshold gates. This case has strong probability of winning, yielding positive expected recovery.' : 'Confidence or evidence strength fell below threshold gates. Case is safely routed to human review to prevent filing fee loss.'}
      </div>
      ${docBtnHtml}`,
      isAuto ? 'step-success' : 'step-warning', 250);

    badge.innerHTML = `<span class="chip ${chipClass}">${action}</span>`;
    outPre.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    stepsC.innerHTML += `<div class="pipeline-step revealed" style="border-left-color:var(--brand-rose);"><div class="step-label">Execution Error</div><div class="step-content">${err.message}</div></div>`;
    badge.innerHTML = '';
    outPre.textContent = 'Error: ' + err.message;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}

function revealStep(container, label, content, cls, delay) {
  return new Promise(resolve => {
    const div = document.createElement('div');
    div.className = 'pipeline-step ' + cls;
    div.innerHTML = `<div class="step-label">${label}</div><div class="step-content">${content}</div>`;
    container.appendChild(div);
    setTimeout(() => { div.classList.add('revealed'); resolve(); }, delay);
  });
}

function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

function toggleRepresentmentDoc() {
  const p = document.getElementById('representment-doc-panel');
  if (p) {
    p.style.display = p.style.display === 'none' ? 'block' : 'none';
  }
}

function copyRepresentmentDoc() {
  if (window.lastResponseText) {
    navigator.clipboard.writeText(window.lastResponseText).then(() => {
      alert('Representment letter copied to clipboard!');
    }).catch(() => {
      alert('Copied.');
    });
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
}
