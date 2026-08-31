// ════════════════════════════════════════════════════════════════════
// Chargeback Intelligence Platform — Client Controller
// Light theme, form-based input, explanation callouts
// ════════════════════════════════════════════════════════════════════

let globalMetrics = null;
let globalPredictions = [];
let chartInstances = {};

// ── Chart.js — Light Theme Defaults ──────────────────────────────
Chart.defaults.color = '#475467';
Chart.defaults.borderColor = '#E4E7EC';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;

// ── Presets ──────────────────────────────────────────────────────
const PRESET_STRONG = {
  dispute_id: "DSP-2026-00142",
  reason_code_label: "Other Fraud - Card Absent Environment",
  card_network: "Visa", dispute_amount: 12499.00, currency: "INR",
  transaction_date: "2026-06-15", days_to_dispute: 35,
  product_category: "electronics", shipping_method: "express",
  delivery_confirmed: true, has_delivery_proof: true,
  ip_geolocation_match: true, avs_cvv_match: "both_match",
  customer_account_age_days: 45, customer_prior_disputes: 0,
  customer_prior_orders: 3, has_customer_correspondence: false,
  has_3ds_authentication: true
};

const PRESET_WEAK = {
  dispute_id: "DSP-2026-00987",
  reason_code_label: "Fraud - Card Absent",
  card_network: "Visa", dispute_amount: 8999.00, currency: "INR",
  transaction_date: "2026-07-01", days_to_dispute: 8,
  product_category: "electronics", shipping_method: "standard",
  delivery_confirmed: false, has_delivery_proof: false,
  ip_geolocation_match: false, avs_cvv_match: "neither",
  customer_account_age_days: 3, customer_prior_disputes: 1,
  customer_prior_orders: 0, has_customer_correspondence: false,
  has_3ds_authentication: false
};

// ── Initialize ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchMetrics();
  fetchPredictions();
  loadPreset('strong');
  checkApiHealth();
  setInterval(checkApiHealth, 30000);
});

// ── Tab Switcher ────────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  event.target.closest('.tab-btn').classList.add('active');
  const panel = document.getElementById('tab-' + tabId);
  if (panel) panel.classList.add('active');
  if (tabId === 'monitoring') fetchMonitoringDrift();
}

// ── Mode Toggle (Form vs JSON) ──────────────────────────────────
function setAnalyzerMode(mode) {
  const toggleBtns = document.querySelectorAll('.mode-toggle button');
  toggleBtns.forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('form-mode').style.display = mode === 'form' ? 'block' : 'none';
  document.getElementById('json-mode').style.display = mode === 'json' ? 'block' : 'none';
}

// ── Health ──────────────────────────────────────────────────────
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health');
    document.getElementById('api-status').textContent = res.ok ? 'API Online' : 'API Error';
  } catch { document.getElementById('api-status').textContent = 'API Offline'; }
}

// ── Fetch Metrics ───────────────────────────────────────────────
async function fetchMetrics() {
  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) return;
    globalMetrics = await res.json();
    renderHeroMetrics();
    renderKPIs();
    renderOverviewCharts();
    renderPerformanceTab();
    updateCostPoint(0.70);
  } catch (e) { console.warn('Metrics fetch:', e); }
}

// ── Fetch Predictions ───────────────────────────────────────────
async function fetchPredictions() {
  try {
    const res = await fetch('/api/predictions');
    if (!res.ok) return;
    globalPredictions = await res.json();
    populateCaseDropdown();
  } catch (e) { console.warn('Predictions fetch:', e); }
}

// ── Hero KPI Values ─────────────────────────────────────────────
function renderHeroMetrics() {
  if (!globalMetrics) return;
  const b = globalMetrics.baselines_inr || {};
  const fe = b.fight_everything_net_value || 0;
  const fn = b.fight_nothing_net_value || 0;
  const sb = b.system_best_net_value || 0;
  animateValue('val-fight-everything', fe, '₹');
  animateValue('val-fight-nothing', fn, '₹');
  animateValue('val-system-best', sb, '₹');
  const delta = sb - fe;
  const el = document.getElementById('val-delta');
  el.textContent = `${delta >= 0 ? '+' : ''}₹${delta.toLocaleString('en-IN')} vs naive`;
  el.className = 'delta-chip ' + (delta >= 0 ? 'success' : 'danger');

  const scale = globalMetrics.illustrative_scale_extrapolation_inr || {};
  const banner = document.getElementById('scale-banner-text');
  if (scale.note) {
    const val100k = (scale.at_100k_disputes_per_year || 0).toLocaleString('en-IN');
    banner.innerHTML = `<span class="banner-chip">Illustrative</span><span>${scale.note} At 100k disputes/year: ₹${val100k}.</span>`;
  }
}

// ── Animate Counter ─────────────────────────────────────────────
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

// ── KPI Tiles ───────────────────────────────────────────────────
function renderKPIs() {
  if (!globalMetrics) return;
  const m = globalMetrics;
  setText('stat-acc',  pct(m.reason_code_accuracy));
  setText('stat-prec', pct(m.macro_precision));
  setText('stat-rec',  pct(m.macro_recall));
  setText('stat-auc',  m.win_prediction_auc.toFixed(3));
  setText('stat-win-auc', m.win_predictor_dedicated_auc ? m.win_predictor_dedicated_auc.toFixed(3) : 'N/A');
}

function pct(v) { return (v * 100).toFixed(1) + '%'; }
function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

// ── Overview Charts ─────────────────────────────────────────────
function renderOverviewCharts() {
  if (!globalMetrics) return;
  const b = globalMetrics.baselines_inr || {};
  destroyChart('chart-baseline');
  chartInstances['chart-baseline'] = new Chart(document.getElementById('chart-baseline'), {
    type: 'bar',
    data: {
      labels: ['Fight Everything', 'Fight Nothing', 'This System'],
      datasets: [{
        data: [b.fight_everything_net_value, b.fight_nothing_net_value, b.system_best_net_value],
        backgroundColor: ['#FEE4E2', '#F2F4F7', '#D1FADF'],
        borderColor: ['#F04438', '#98A2B3', '#12B76A'],
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: '#F2F4F7' }, ticks: { callback: v => '₹' + v.toLocaleString('en-IN') } },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Performance Tab ─────────────────────────────────────────────
function renderPerformanceTab() {
  if (!globalMetrics) return;
  const m = globalMetrics;
  setText('perf-acc', pct(m.reason_code_accuracy));
  setText('perf-f1', pct(m.macro_f1 || 0));
  setText('perf-win-auc', m.win_predictor_dedicated_auc ? m.win_predictor_dedicated_auc.toFixed(3) : 'N/A');

  // Per-class table
  const tbody = document.getElementById('per-class-tbody');
  tbody.innerHTML = '';
  const pc = m.per_class || {};
  Object.keys(pc).forEach(code => {
    const d = pc[code];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><strong>${code}</strong></td><td>${pct(d.precision)}</td><td>${pct(d.recall)}</td><td>${pct(d['f1-score'])}</td><td>${d.support}</td>`;
    tbody.appendChild(tr);
  });

  // Cost curve chart
  const curve = m.cost_curve || [];
  destroyChart('chart-cost-curve');
  chartInstances['chart-cost-curve'] = new Chart(document.getElementById('chart-cost-curve'), {
    type: 'line',
    data: {
      labels: curve.map(c => c.threshold.toFixed(2)),
      datasets: [
        { label: 'Net ₹/Dispute', data: curve.map(c => c.net_value_per_dispute), borderColor: '#12B76A', backgroundColor: 'rgba(18,183,106,0.08)', fill: true, tension: 0.3, pointRadius: 4 },
        { label: 'Auto-Respond %', data: curve.map(c => c.auto_respond_pct * 100), borderColor: '#2563EB', tension: 0.3, pointRadius: 3, yAxisID: 'y1' },
        { label: 'Win Rate %', data: curve.map(c => c.win_rate_at_threshold * 100), borderColor: '#F59E0B', tension: 0.3, pointRadius: 3, yAxisID: 'y1' }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      scales: {
        y: { title: { display: true, text: 'Net ₹/Dispute' }, grid: { color: '#F2F4F7' } },
        y1: { position: 'right', title: { display: true, text: '%' }, grid: { display: false } },
        x: { title: { display: true, text: 'Threshold' }, grid: { color: '#F2F4F7' } }
      },
      plugins: { legend: { labels: { boxWidth: 10 } } }
    }
  });

  // Feature importances
  const fi = m.top_feature_importances || {};
  destroyChart('chart-features');
  chartInstances['chart-features'] = new Chart(document.getElementById('chart-features'), {
    type: 'bar',
    data: {
      labels: Object.keys(fi).map(l => l.replace(/_/g, ' ')),
      datasets: [{ data: Object.values(fi), backgroundColor: '#D6E4FF', borderColor: '#2563EB', borderWidth: 1, borderRadius: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { grid: { color: '#F2F4F7' }, title: { display: true, text: 'Importance' } }, y: { grid: { display: false } } }
    }
  });

  // Cost curve table
  const ct = document.getElementById('cost-curve-tbody');
  ct.innerHTML = '';
  curve.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.threshold.toFixed(2)}</td><td>${pct(r.auto_respond_pct)}</td><td>${pct(r.win_rate_at_threshold)}</td><td>${r.tp}</td><td>${r.fp}</td><td>${r.fn}</td><td>₹${r.net_value.toLocaleString('en-IN')}</td><td>₹${r.net_value_per_dispute.toFixed(0)}</td>`;
    ct.appendChild(tr);
  });
}

// ── Cost Point Slider ───────────────────────────────────────────
function updateCostPoint(val) {
  const t = parseFloat(val);
  setText('threshold-val', t.toFixed(2));
  if (!globalMetrics || !globalMetrics.cost_curve) return;
  const row = globalMetrics.cost_curve.find(c => Math.abs(c.threshold - t) < 0.01) || globalMetrics.cost_curve[0];
  setText('cost-auto-pct', pct(row.auto_respond_pct));
  setText('cost-win-rate', pct(row.win_rate_at_threshold));
  setText('cost-net-dispute', '₹' + row.net_value_per_dispute.toFixed(0));
}

// ── Monitoring ──────────────────────────────────────────────────
async function fetchMonitoringDrift() {
  try {
    const res = await fetch('/api/monitoring/drift?window=200');
    if (!res.ok) return;
    renderMonitoring(await res.json());
  } catch (e) { console.warn('Monitoring:', e); }
}

function renderMonitoring(d) {
  setText('mon-window', d.window_size || '--');
  setText('mon-conf', d.confidence ? d.confidence.mean.toFixed(3) : '--');
  setText('mon-evidence', d.evidence_strength ? d.evidence_strength.mean.toFixed(3) : '--');
  setText('mon-winprob', d.win_probability ? d.win_probability.mean.toFixed(3) : '--');
  setText('mon-autorate', d.auto_rate_pct ? d.auto_rate_pct + '%' : '--');

  const rc = d.reason_code_distribution || {};
  const muted = ['#D6E4FF','#D1FADF','#FEF0C7','#FECDCA','#E9D5FF','#D3F8DF','#FDE68A','#FCE7F3','#CCFBF1','#FED7AA'];
  const borders = ['#2563EB','#12B76A','#F59E0B','#F04438','#7C3AED','#059669','#D97706','#DB2777','#0D9488','#EA580C'];
  destroyChart('chart-mon-rc');
  chartInstances['chart-mon-rc'] = new Chart(document.getElementById('chart-mon-rc'), {
    type: 'bar',
    data: { labels: Object.keys(rc), datasets: [{ data: Object.values(rc), backgroundColor: muted, borderColor: borders, borderWidth: 1, borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#F2F4F7' } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } } } }
  });

  const ad = d.action_distribution || {};
  destroyChart('chart-mon-action');
  chartInstances['chart-mon-action'] = new Chart(document.getElementById('chart-mon-action'), {
    type: 'doughnut',
    data: { labels: Object.keys(ad), datasets: [{ data: Object.values(ad), backgroundColor: ['#D1FADF', '#FEF0C7'], borderColor: ['#12B76A', '#F59E0B'], borderWidth: 1 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10 } } } }
  });
}

// ── Case Explorer ───────────────────────────────────────────────
function populateCaseDropdown() {
  const sel = document.getElementById('case-select');
  sel.innerHTML = '<option value="">Select a dispute ID…</option>';
  globalPredictions.slice(0, 50).forEach(p => {
    const o = document.createElement('option');
    o.value = p.dispute_id;
    o.textContent = `${p.dispute_id} (${p.actual} → ${p.predicted})`;
    sel.appendChild(o);
  });
}

function inspectCase(id) {
  if (!id) return;
  const found = globalPredictions.find(p => p.dispute_id === id);
  if (found) document.getElementById('case-json-display').textContent = JSON.stringify(found, null, 2);
}

// ── Presets ──────────────────────────────────────────────────────
function loadPreset(type) {
  const p = type === 'strong' ? PRESET_STRONG : PRESET_WEAK;
  // Fill form
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
  document.querySelectorAll('input[name="avs"]').forEach(r => { r.checked = r.value === p.avs_cvv_match; });
  // Fill JSON textarea
  document.getElementById('dispute-json-input').value = JSON.stringify(p, null, 2);
}

// ── Build payload from form ─────────────────────────────────────
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
      errDiv.innerHTML = `<span class="chip chip-danger">Missing fields: ${missing.join(', ')}</span>`;
      errDiv.style.display = 'block';
      return;
    }
    runPipeline(payload, document.getElementById('run-json-btn'));
  } catch (e) {
    errDiv.innerHTML = `<span class="chip chip-danger">Invalid JSON: ${e.message}</span>`;
    errDiv.style.display = 'block';
  }
}

// ── Run Pipeline with Step Reveal ───────────────────────────────
async function runPipeline(payload, btn) {
  const stepsC = document.getElementById('pipeline-steps');
  const outPre = document.getElementById('demo-result-output');
  const badge = document.getElementById('action-badge-container');
  stepsC.innerHTML = '';
  outPre.textContent = '';
  badge.innerHTML = '<span class="spinner"></span>';
  btn.disabled = true;
  const origText = btn.textContent;
  btn.textContent = 'Processing…';

  try {
    await revealStep(stepsC, 'Step 1 — Input Received',
      `Dispute <strong>${payload.dispute_id || 'N/A'}</strong> · ₹${(payload.dispute_amount || 0).toLocaleString('en-IN')} · ${payload.card_network || 'Unknown'}`, '', 250);

    const res = await fetch('/api/disputes', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'API Error'); }
    const data = await res.json();

    // Step 2
    const clf = data.classification || {};
    const topK = (clf.top_k_predictions || []).map((t,i) => {
      const p = (t.confidence * 100).toFixed(1);
      return `<div style="margin-top:4px;"><span style="color:var(--color-text-tertiary);font-size:11px;">#${i+1}</span> <strong>${t.reason_code}</strong> ${p}%<div class="conf-bar-track"><div class="conf-bar-fill" style="width:${p}%"></div></div></div>`;
    }).join('');
    await revealStep(stepsC, 'Step 2 — Reason Code Classification',
      `Primary: <strong>${clf.predicted_reason_code || 'N/A'}</strong> — ${((clf.confidence||0)*100).toFixed(1)}% confidence${topK}
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> The model is ${((clf.confidence||0)*100).toFixed(1)}% confident this is the correct reason code, based on similar disputes it saw during training.</div>`,
      'step-success', 350);

    // Step 3
    const ev = data.evidence || {};
    const evPkg = ev.evidence_package || {};
    const chips = [
      ...(evPkg.compelling||[]).map(e => `<span class="chip chip-success">✓ ${e.field}</span>`),
      ...(evPkg.supporting||[]).map(e => `<span class="chip chip-success">✓ ${e.field}</span>`),
      ...(evPkg.missing||[]).map(m => `<span class="chip chip-danger">✗ ${m}</span>`)
    ].join(' ');
    const totalEvidence = (evPkg.compelling||[]).length + (evPkg.supporting||[]).length + (evPkg.missing||[]).length;
    const presentEvidence = (evPkg.compelling||[]).length + (evPkg.supporting||[]).length;
    await revealStep(stepsC, 'Step 3 — Evidence Retrieved',
      `Evidence strength: <strong>${((ev.evidence_strength||0)*100).toFixed(0)}%</strong><div style="margin:6px 0;">${chips}</div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> This reason code requires ${totalEvidence} evidence types under the card network's representment rules. ${presentEvidence} of ${totalEvidence} are present.</div>`,
      ev.evidence_strength >= 0.6 ? 'step-success' : 'step-warning', 350);

    // Step 4
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
        <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--color-border);">
          <button class="btn-secondary" style="width:100%; justify-content:center;" onclick="toggleRepresentmentDoc()">
            📄 Generate &amp; View Representment Document
          </button>
          <div id="representment-doc-panel" style="display:none; margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:var(--color-text-tertiary); text-transform:uppercase;">Rendered Visa/Mastercard Evidence Letter</span>
              <button class="btn-secondary" style="padding:2px 8px; font-size:11px;" onclick="copyRepresentmentDoc()">Copy Letter</button>
            </div>
            <pre class="code-block" style="max-height:220px; white-space:pre-wrap; background:#FFFFFF; color:var(--color-text-primary); border:1px solid var(--color-border-strong); font-size:11px;">${escapeHtml(responseText)}</pre>
          </div>
        </div>
      `;
    }

    await revealStep(stepsC, 'Step 4 — Recommendation',
      `<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-size:20px;font-weight:800;">Win probability: ${(wp*100).toFixed(1)}%</span>
        <span class="chip ${chipClass}">${action}</span>
      </div>
      <div style="display:flex;gap:20px;font-size:13px;color:var(--color-text-secondary);margin-bottom:8px;">
        <span>Expected recovery: <strong>₹${ev_inr.toLocaleString('en-IN')}</strong></span>
      </div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> <strong>Why:</strong> confidence (${((clf.confidence||0)*100).toFixed(1)}%) ${(clf.confidence||0) >= 0.70 ? 'exceeds' : 'is below'} the 70% auto-respond threshold, and evidence strength (${((ev.evidence_strength||0)*100).toFixed(0)}%) ${(ev.evidence_strength||0) >= 0.60 ? 'exceeds' : 'is below'} the 60% minimum gate. Both conditions must hold for auto-submit — see Guardrails tab.</div>
      ${docBtnHtml}`,
      isAuto ? 'step-success' : 'step-warning', 300);

    badge.innerHTML = `<span class="chip ${chipClass}">${action}</span>`;
    outPre.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    stepsC.innerHTML += `<div class="pipeline-step revealed" style="border-left-color:#B42318;"><div class="step-label">Error</div><div class="step-content">${err.message}</div></div>`;
    badge.innerHTML = '';
    outPre.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = origText;
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

function destroyChart(id) { if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; } }

function toggleRepresentmentDoc() {
  const p = document.getElementById('representment-doc-panel');
  if (p) {
    p.style.display = p.style.display === 'none' ? 'block' : 'none';
  }
}

function copyRepresentmentDoc() {
  if (window.lastResponseText) {
    navigator.clipboard.writeText(window.lastResponseText).then(() => {
      alert('Representment document copied to clipboard!');
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

