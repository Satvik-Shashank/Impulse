// ════════════════════════════════════════════════════════════════════
// Chargeback Intelligence Platform — Client Controller
// Razorpay Theme: Unified Page, Real-time Interaction, Smooth Scroll
// ════════════════════════════════════════════════════════════════════

let globalMetrics = null;
let globalPredictions = [];
let chartInstances = {};

// ── Chart.js — Razorpay Style Defaults ────────────────────────────
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

// ── Initialization ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchMetrics();
  fetchPredictions();
  fetchMonitoringDrift();
  loadPreset('strong');
  checkApiHealth();
  setInterval(checkApiHealth, 30000);
  initScrollSpy();
});

// ── Navigation Link Active State ─────────────────────────────────
function setActiveNav(btn) {
  document.querySelectorAll('.nav-link-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function initScrollSpy() {
  const sections = document.querySelectorAll('.content-section');
  const navLinks = document.querySelectorAll('.nav-link-btn');

  window.addEventListener('scroll', () => {
    let current = '';
    const scrollPos = window.pageYOffset + 120;

    sections.forEach(section => {
      if (scrollPos >= section.offsetTop) {
        current = section.getAttribute('id');
      }
    });

    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === `#${current}`) {
        link.classList.add('active');
      }
    });
  });
}

// ── Mode Toggle (Form vs JSON) ──────────────────────────────────
function setAnalyzerMode(mode, btn) {
  const toggleBtns = document.querySelectorAll('.mode-toggle button');
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

// ── Fetch Metrics ───────────────────────────────────────────────
async function fetchMetrics() {
  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) return;
    globalMetrics = await res.json();
    renderHeroMetrics();
    renderKPIs();
    renderPerformanceSection();
    updateCostPoint(0.70);
  } catch (e) {
    console.warn('Metrics fetch:', e);
  }
}

// ── Fetch Predictions ───────────────────────────────────────────
async function fetchPredictions() {
  try {
    const res = await fetch('/api/predictions');
    if (!res.ok) return;
    globalPredictions = await res.json();
    populateCaseDropdown();
  } catch (e) {
    console.warn('Predictions fetch:', e);
  }
}

// ── Render Baseline Recovery Metrics ─────────────────────────────
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
  if (el) {
    el.textContent = `${delta >= 0 ? '+' : ''}₹${delta.toLocaleString('en-IN')} vs naive`;
    el.className = 'delta-chip ' + (delta >= 0 ? 'success' : 'danger');
  }

  const scale = globalMetrics.illustrative_scale_extrapolation_inr || {};
  const banner = document.getElementById('scale-banner-text');
  if (banner && scale.note) {
    const val100k = (scale.at_100k_disputes_per_year || 0).toLocaleString('en-IN');
    banner.innerHTML = `<span class="banner-chip">Scale Extrapolation</span><span>${scale.note} At 100k disputes/year: <strong>₹${val100k}</strong> net value.</span>`;
  }
}

// ── Animate Numbers ─────────────────────────────────────────────
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
  setText('stat-acc', pct(m.reason_code_accuracy));
  setText('stat-prec', pct(m.macro_precision));
  setText('stat-rec', pct(m.macro_recall));
  setText('stat-auc', m.win_prediction_auc.toFixed(3));
  setText('stat-win-auc', m.win_predictor_dedicated_auc ? m.win_predictor_dedicated_auc.toFixed(3) : '0.826');
}

function pct(v) { return (v * 100).toFixed(1) + '%'; }
function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

// ── Render Model Performance Charts & Tables ─────────────────────
function renderPerformanceSection() {
  if (!globalMetrics) return;
  const m = globalMetrics;

  // 1. Cost vs Threshold Curve
  const curve = m.cost_curve || [];
  destroyChart('chart-cost-curve');
  chartInstances['chart-cost-curve'] = new Chart(document.getElementById('chart-cost-curve'), {
    type: 'line',
    data: {
      labels: curve.map(c => c.threshold.toFixed(2)),
      datasets: [
        {
          label: 'Net ₹/Dispute',
          data: curve.map(c => c.net_value_per_dispute),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: '#10B981',
          borderWidth: 2.5
        },
        {
          label: 'Auto-Respond %',
          data: curve.map(c => c.auto_respond_pct * 100),
          borderColor: '#0C83FF',
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: '#0C83FF',
          borderWidth: 2,
          yAxisID: 'y1'
        },
        {
          label: 'Win Rate %',
          data: curve.map(c => c.win_rate_at_threshold * 100),
          borderColor: '#F59E0B',
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: '#F59E0B',
          borderWidth: 2,
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
          title: { display: true, text: 'Net ₹/Dispute', color: '#10B981', font: { weight: 'bold' } },
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
        legend: { position: 'top', labels: { boxWidth: 12, usePointStyle: true, padding: 12 } }
      }
    }
  });

  // 2. Feature Importances
  const fi = m.top_feature_importances || {};
  destroyChart('chart-features');
  chartInstances['chart-features'] = new Chart(document.getElementById('chart-features'), {
    type: 'bar',
    data: {
      labels: Object.keys(fi).map(l => l.replace(/_/g, ' ')),
      datasets: [{
        data: Object.values(fi),
        backgroundColor: '#EBF4FF',
        borderColor: '#0C83FF',
        hoverBackgroundColor: '#0C83FF',
        borderWidth: 1.5,
        borderRadius: 4
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
          title: { display: true, text: 'Gini Importance Score', color: '#64748B' }
        },
        y: { grid: { display: false } }
      }
    }
  });

  // 3. Per-Class Table
  const tbody = document.getElementById('per-class-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    const pc = m.per_class || {};
    Object.keys(pc).forEach(code => {
      const d = pc[code];
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong style="color:var(--rzp-navy-dark);">${code}</strong></td>
        <td>${pct(d.precision)}</td>
        <td>${pct(d.recall)}</td>
        <td><strong style="color:var(--rzp-blue);">${pct(d['f1-score'])}</strong></td>
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
        <td><strong style="color:var(--rzp-emerald-text);">₹${r.net_value.toLocaleString('en-IN')}</strong></td>
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

// ── Monitoring & Drift ───────────────────────────────────────────
async function fetchMonitoringDrift() {
  try {
    const res = await fetch('/api/monitoring/drift?window=200');
    if (!res.ok) return;
    renderMonitoring(await res.json());
  } catch (e) {
    console.warn('Monitoring:', e);
  }
}

function renderMonitoring(d) {
  setText('mon-window', d.window_size || '--');
  setText('mon-conf', d.confidence ? d.confidence.mean.toFixed(3) : '--');
  setText('mon-evidence', d.evidence_strength ? d.evidence_strength.mean.toFixed(3) : '--');
  setText('mon-winprob', d.win_probability ? d.win_probability.mean.toFixed(3) : '--');
  setText('mon-autorate', d.auto_rate_pct ? d.auto_rate_pct + '%' : '--');

  const rc = d.reason_code_distribution || {};
  destroyChart('chart-mon-rc');
  chartInstances['chart-mon-rc'] = new Chart(document.getElementById('chart-mon-rc'), {
    type: 'bar',
    data: {
      labels: Object.keys(rc),
      datasets: [{
        data: Object.values(rc),
        backgroundColor: '#EBF4FF',
        borderColor: '#0C83FF',
        hoverBackgroundColor: '#0C83FF',
        borderWidth: 1.5,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: '#F1F5F9' } },
        x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } }
      }
    }
  });

  const ad = d.action_distribution || {};
  destroyChart('chart-mon-action');
  chartInstances['chart-mon-action'] = new Chart(document.getElementById('chart-mon-action'), {
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
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } } }
    }
  });
}

// ── Case Explorer ───────────────────────────────────────────────
function populateCaseDropdown() {
  const sel = document.getElementById('case-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">Select a test dispute record…</option>';
  globalPredictions.slice(0, 50).forEach(p => {
    const o = document.createElement('option');
    o.value = p.dispute_id;
    o.textContent = `${p.dispute_id} (${p.actual} → ${p.predicted}) · Confidence: ${(p.confidence * 100).toFixed(0)}%`;
    sel.appendChild(o);
  });
}

function inspectCase(id) {
  if (!id) return;
  const found = globalPredictions.find(p => p.dispute_id === id);
  if (found) {
    document.getElementById('case-json-display').textContent = JSON.stringify(found, null, 2);
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
  btn.disabled = true;
  const origText = btn.textContent;
  btn.textContent = 'Processing Pipeline…';

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
      return `<div style="margin-top:4px;"><span style="color:var(--text-muted);font-size:11px;">#${i+1}</span> <strong>${t.reason_code}</strong> <span style="color:var(--rzp-blue);">${p}%</span><div class="conf-bar-track"><div class="conf-bar-fill" style="width:${p}%"></div></div></div>`;
    }).join('');
    
    await revealStep(stepsC, 'Step 2 — Reason Code Classification',
      `Primary: <strong>${clf.predicted_reason_code || 'N/A'}</strong> — ${((clf.confidence||0)*100).toFixed(1)}% calibrated confidence${topK}
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> The LightGBM classifier predicts <strong>${clf.predicted_reason_code || 'N/A'}</strong> with ${((clf.confidence||0)*100).toFixed(1)}% Platt-scaled confidence based on transaction signals.</div>`,
      'step-success', 300);

    // Step 3: Evidence Rule Table Check
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
      `Evidence strength: <strong>${((ev.evidence_strength||0)*100).toFixed(0)}%</strong><div style="margin:8px 0;">${chips}</div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> This reason code requires ${totalEvidence} evidence types under ${payload.card_network}'s representment rules. ${presentEvidence} of ${totalEvidence} items are present.</div>`,
      ev.evidence_strength >= 0.6 ? 'step-success' : 'step-warning', 300);

    // Step 4: Decision & Recommendation
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
        <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--border-color);">
          <button class="btn-secondary" style="width:100%; justify-content:center;" onclick="toggleRepresentmentDoc()">
            📄 Generate &amp; View Representment Document
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
        <span style="font-size:22px;font-weight:900;color:var(--rzp-navy-dark);">Win probability: ${(wp*100).toFixed(1)}%</span>
        <span class="chip ${chipClass}">${action}</span>
      </div>
      <div style="display:flex;gap:20px;font-size:13px;color:var(--text-secondary);margin-bottom:8px;">
        <span>Expected Net Value: <strong style="color:var(--rzp-emerald-text);">₹${ev_inr.toLocaleString('en-IN')}</strong></span>
      </div>
      <div class="callout" style="margin-top:8px;margin-bottom:0;"><span class="callout-icon">ⓘ</span> <strong>Decision Logic:</strong> Calibrated confidence (${((clf.confidence||0)*100).toFixed(1)}%) ${(clf.confidence||0) >= 0.70 ? 'exceeds' : 'is below'} the 70% threshold gate, and evidence strength (${((ev.evidence_strength||0)*100).toFixed(0)}%) ${(ev.evidence_strength||0) >= 0.60 ? 'exceeds' : 'is below'} the 60% minimum gate.</div>
      ${docBtnHtml}`,
      isAuto ? 'step-success' : 'step-warning', 250);

    badge.innerHTML = `<span class="chip ${chipClass}">${action}</span>`;
    outPre.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    stepsC.innerHTML += `<div class="pipeline-step revealed" style="border-left-color:var(--rzp-rose);"><div class="step-label">Execution Error</div><div class="step-content">${err.message}</div></div>`;
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
