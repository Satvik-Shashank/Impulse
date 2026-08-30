// Client-side Javascript for Vercel Web Dashboard

let globalMetrics = null;
let globalPredictions = [];

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

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  fetchMetrics();
  fetchPredictions();
  loadPreset('strong');
});

// Tab Switcher
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

  event.target.classList.add('active');
  const targetPanel = document.getElementById(`tab-${tabId}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
}

// Fetch Metrics from API
async function fetchMetrics() {
  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) throw new Error('API Metrics not ready');
    globalMetrics = await res.json();
    renderHeroMetrics();
    renderClassifierStats();
    updateCostPoint(0.70);
  } catch (err) {
    console.warn("Using fallback/local data check:", err);
  }
}

// Fetch Predictions from API
async function fetchPredictions() {
  try {
    const res = await fetch('/api/predictions');
    if (!res.ok) return;
    globalPredictions = await res.json();
    populateCaseDropdown();
  } catch (err) {
    console.warn("Predictions endpoint warning:", err);
  }
}

// Render Hero Section Metrics
function renderHeroMetrics() {
  if (!globalMetrics) return;

  const baselines = globalMetrics.baselines_inr || {};
  const fightEverything = baselines.fight_everything_net_value || 0;
  const fightNothing = baselines.fight_nothing_net_value || 0;
  const systemBest = baselines.system_best_net_value || 0;
  const delta = systemBest - fightEverything;

  document.getElementById('val-fight-everything').innerText = `₹${fightEverything.toLocaleString('en-IN')}`;
  document.getElementById('val-fight-nothing').innerText = `₹${fightNothing.toLocaleString('en-IN')}`;
  document.getElementById('val-system-best').innerText = `₹${systemBest.toLocaleString('en-IN')}`;

  const deltaEl = document.getElementById('val-delta');
  deltaEl.innerText = `${delta >= 0 ? '+' : ''}₹${delta.toLocaleString('en-IN')} vs naive`;

  // Scale banner
  const scale = globalMetrics.illustrative_scale_extrapolation_inr || {};
  const bannerText = scale.note ? `⚠️ ${scale.note} Illustration at 100k disputes/year: ₹${(scale.at_100k_disputes_per_year || 0).toLocaleString('en-IN')}.` : '';
  document.getElementById('scale-banner-text').innerHTML = bannerText;
}

// Render Classifier Metrics Tab
function renderClassifierStats() {
  if (!globalMetrics) return;

  document.getElementById('stat-acc').innerText = `${(globalMetrics.reason_code_accuracy * 100).toFixed(1)}%`;
  document.getElementById('stat-prec').innerText = `${(globalMetrics.macro_precision * 100).toFixed(1)}%`;
  document.getElementById('stat-rec').innerText = `${(globalMetrics.macro_recall * 100).toFixed(1)}%`;
  document.getElementById('stat-auc').innerText = globalMetrics.win_prediction_auc.toFixed(3);

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

// Cost Operating Point Selector
function updateCostPoint(val) {
  const threshold = parseFloat(val);
  document.getElementById('threshold-val').innerText = threshold.toFixed(2);

  if (!globalMetrics || !globalMetrics.cost_curve) return;

  const row = globalMetrics.cost_curve.find(c => Math.abs(c.threshold - threshold) < 0.01) || globalMetrics.cost_curve[0];

  document.getElementById('cost-auto-pct').innerText = `${(row.auto_respond_pct * 100).toFixed(1)}%`;
  document.getElementById('cost-win-rate').innerText = `${(row.win_rate_at_threshold * 100).toFixed(1)}%`;
  document.getElementById('cost-net-dispute').innerText = `₹${row.net_value_per_dispute.toFixed(0)}`;
}

// Populate Case Dropdown
function populateCaseDropdown() {
  const select = document.getElementById('case-select');
  select.innerHTML = '<option value="">Select a dispute ID...</option>';
  globalPredictions.slice(0, 50).forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.dispute_id;
    opt.innerText = `${item.dispute_id} (Actual: ${item.actual} → Pred: ${item.predicted})`;
    select.appendChild(opt);
  });
}

function inspectCase(id) {
  if (!id) return;
  const found = globalPredictions.find(p => p.dispute_id === id);
  if (found) {
    document.getElementById('case-json-display').innerText = JSON.stringify(found, null, 2);
  }
}

// Demo Presets
function loadPreset(type) {
  const payload = type === 'strong' ? PRESET_STRONG : PRESET_WEAK;
  document.getElementById('dispute-json-input').value = JSON.stringify(payload, null, 2);
}

// Process Custom Dispute via API
async function processCustomDispute() {
  const raw = document.getElementById('dispute-json-input').value;
  const outPre = document.getElementById('demo-result-output');
  const badgeContainer = document.getElementById('action-badge-container');

  outPre.innerText = "Processing dispute through LightGBM + Jinja2 pipeline...";
  badgeContainer.innerHTML = "";

  try {
    const payload = JSON.parse(raw);
    const res = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'API Error');
    }

    const data = await res.json();
    outPre.innerText = JSON.stringify(data, null, 2);

    const action = data.response ? data.response.action : 'UNKNOWN';
    const isAuto = action === 'AUTO_SUBMIT';
    badgeContainer.innerHTML = `<span class="action-badge ${isAuto ? 'auto-submit' : 'human-review'}">${isAuto ? '🟢 AUTO_SUBMIT' : '🟡 HUMAN_REVIEW'}</span>`;

  } catch (err) {
    outPre.innerText = `Error: ${err.message}`;
  }
}
