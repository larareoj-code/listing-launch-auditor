const $ = (id) => document.getElementById(id);
const form = $('audit-form');
const dialog = $('upgrade-dialog');
const HISTORY_KEY = 'lla_pro_history_v1';
const SESSION_KEY = 'lla_stripe_session_v1';
const FREE_AUDITS_KEY = 'lla_free_audits_v1';
let latestResult = null;
let isPro = false;

const lines = (value) => value.split('\n').map((item) => item.trim()).filter(Boolean);
const event = (name, details = {}) => fetch('/api/events', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({event: name, details}),
}).catch(() => {});

function readStorage(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch (_) { return fallback; }
}

function writeStorage(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* optional storage */ }
}

function payload() {
  return {
    platform: $('platform').value, title: $('title').value.trim(),
    description: $('description').value.trim(), price: Number($('price').value),
    product_type: $('product-type').value.trim(), audience: $('audience').value.trim(),
    deliverables: lines($('deliverables').value), preview_assets: lines($('previews').value),
    refund_policy: $('refund-policy').value.trim(), support_text: $('support-text').value.trim(),
    claims: lines($('claims').value),
  };
}

function escapeHtml(value) {
  const element = document.createElement('div');
  element.textContent = value;
  return element.innerHTML;
}

function group(title, items, kind) {
  if (!items.length) return '';
  return `<section class="result-group ${kind}"><header><h3>${title}</h3><span class="count">${items.length}</span></header><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></section>`;
}

function copyFor(decision) {
  if (decision === 'launch') return 'No launch blockers found. Complete the platform checklist before publishing.';
  if (decision === 'quarantine') return 'Blocking risk detected. Do not publish until it is removed or substantiated.';
  return 'The core offer is workable, but the listing needs another editing pass.';
}

function updateCompletion() {
  const checks = [$('product-type').value.trim(), $('price').value, $('title').value.trim(), $('audience').value.trim(), $('description').value.trim(), $('deliverables').value.trim(), $('previews').value.trim(), $('refund-policy').value.trim(), $('support-text').value.trim()];
  const completed = checks.filter(Boolean).length;
  $('completion-bar').style.width = `${Math.round((completed / checks.length) * 100)}%`;
  $('completion-text').textContent = `${completed} of ${checks.length} launch fields ready`;
}

function historyItems() { return readStorage(HISTORY_KEY, []); }

function renderHistory() {
  if (!isPro) return;
  const items = historyItems();
  $('history-empty').hidden = items.length > 0;
  $('clear-history').hidden = items.length === 0;
  $('history-list').innerHTML = items.map((item, index) => {
    const date = new Date(item.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'});
    return `<li><button type="button" data-history-index="${index}"><span><strong>${escapeHtml(item.request.title)}</strong><small>${escapeHtml(item.request.platform)} - ${date}</small></span><b>${item.result.readiness_score}</b></button></li>`;
  }).join('');
}

function updateProUi() {
  $('plan-status').textContent = isPro ? 'Pro active' : '1 free audit';
  $('plan-status').classList.toggle('pro-active', isPro);
  $('upgrade-top').hidden = isPro;
  $('upgrade-result').hidden = isPro;
  $('pro-card').hidden = isPro;
  $('history-panel').hidden = !isPro;
  $('export-csv').classList.toggle('locked', !isPro);
  $('print-report').classList.toggle('locked', !isPro);
  $('export-csv').title = isPro ? 'Export audit as CSV' : 'Available with Pro';
  $('print-report').title = isPro ? 'Print or save PDF' : 'Available with Pro';
  renderHistory();
}

function saveHistory(request, result) {
  if (!isPro) return;
  const items = historyItems();
  items.unshift({request, result, created_at: new Date().toISOString()});
  writeStorage(HISTORY_KEY, items.slice(0, 25));
  renderHistory();
}

function restoreRequest(request) {
  $('platform').value = request.platform; $('product-type').value = request.product_type;
  $('price').value = request.price; $('title').value = request.title; $('audience').value = request.audience;
  $('description').value = request.description; $('deliverables').value = request.deliverables.join('\n');
  $('previews').value = request.preview_assets.join('\n'); $('refund-policy').value = request.refund_policy;
  $('support-text').value = request.support_text; $('claims').value = request.claims.join('\n');
  $('description').dispatchEvent(new Event('input'));
  updateCompletion();
}

function render(result, previousScore = null) {
  latestResult = result;
  $('empty-state').hidden = true; $('result-state').hidden = false;
  $('score').textContent = result.readiness_score;
  $('decision').textContent = result.decision[0].toUpperCase() + result.decision.slice(1);
  $('decision-copy').textContent = copyFor(result.decision);
  const delta = previousScore === null ? null : result.readiness_score - previousScore;
  $('score-change').textContent = delta === null ? '' : `${delta >= 0 ? '+' : ''}${delta} vs previous audit`;
  const color = result.decision === 'quarantine' ? 'var(--red)' : result.decision === 'revise' ? 'var(--amber)' : 'var(--green)';
  $('score-ring').style.background = `conic-gradient(${color} ${result.readiness_score * 3.6}deg, #e2e7e4 0deg)`;
  $('checks-passed').textContent = `${result.checks_passed} of ${result.checks_total} checks passed`;
  $('ruleset').textContent = `Ruleset ${result.ruleset_version}`;
  $('blocker-count').textContent = result.blocking_issues.length; $('warning-count').textContent = result.warnings.length; $('missing-count').textContent = result.missing_assets.length;
  $('platform-name').textContent = $('platform').value;
  $('platform-checklist').innerHTML = result.platform_checklist.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  $('result-groups').innerHTML = group('Launch blockers', result.blocking_issues, 'blocking') + group('Warnings', result.warnings, 'warning') + group('Missing assets', result.missing_assets, 'info') + group('Recommended edits', result.recommendations, 'good') + group('Compliance notes', result.compliance_flags, 'info');
  $('decision').focus({preventScroll: true});
  window.scrollTo({top: 0, behavior: 'smooth'});
}

function openUpgrade(source = 'header') {
  $('billing-note').textContent = 'Choose a plan to continue to secure Stripe Checkout.';
  event('upgrade_clicked', {source});
  dialog.showModal();
}

async function refreshEntitlement(sessionId) {
  if (!sessionId) return false;
  try {
    const response = await fetch(`/api/entitlement?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    if (response.ok && data.active) {
      writeStorage(SESSION_KEY, sessionId); isPro = true; updateProUi(); return true;
    }
  } catch (_) { /* keep the free experience available */ }
  return false;
}

form.addEventListener('submit', async (eventObject) => {
  eventObject.preventDefault(); $('form-error').textContent = '';
  if (!isPro && readStorage(FREE_AUDITS_KEY, 0) >= 1) {
    $('form-error').textContent = 'Your free audit is complete. Upgrade to run another listing.';
    openUpgrade('free_limit'); return;
  }
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true; button.setAttribute('aria-busy', 'true'); button.querySelector('span').textContent = 'Auditing...';
  try {
    const request = payload(); const prior = historyItems()[0];
    const response = await fetch('/api/audit', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Audit failed.');
    render(data, prior ? prior.result.readiness_score : null); saveHistory(request, data);
    if (!isPro) writeStorage(FREE_AUDITS_KEY, 1);
    event('audit_completed', {platform: request.platform, decision: data.decision, score: data.readiness_score});
  } catch (error) { $('form-error').textContent = error.message; }
  finally { button.disabled = false; button.removeAttribute('aria-busy'); button.querySelector('span').textContent = 'Run launch audit'; }
});

form.addEventListener('input', updateCompletion);
$('description').addEventListener('input', () => $('word-count').textContent = `${$('description').value.trim().split(/\s+/).filter(Boolean).length} words`);
$('load-sample').addEventListener('click', () => {
  restoreRequest({platform: 'Fourthwall', product_type: 'Resource bundle', price: 39, title: 'AI Creator Workflow Bundle', audience: 'Creators and independent service providers', description: 'A three-product digital resource bundle for creators and independent service providers building practical AI-assisted workflows. It includes client intake and automation mapping templates, podcast repurposing workflows, and micro-course production checklists. Files are provided for personal or internal business use. No income promises; results depend on your market, offer, and execution.', deliverables: ['Client intake workflow kit (ZIP)', 'Podcast repurposing workflow kit (ZIP)', 'Micro-course production kit (ZIP)'], preview_assets: ['Square product cover', 'Interior workflow preview'], refund_policy: 'Because this is a digital download, refund requests are reviewed individually when a file is defective or materially different from the listing.', support_text: 'Use the storefront contact form for product support. Replies are normally sent within two business days.', claims: []});
  event('sample_loaded');
});
$('run-again').addEventListener('click', () => $('audit-heading').scrollIntoView({behavior: 'smooth'}));
$('print-report').addEventListener('click', () => isPro ? (event('print_report'), window.print()) : openUpgrade('print_locked'));
$('export-csv').addEventListener('click', () => {
  if (!isPro) return openUpgrade('export_locked');
  if (!latestResult) return;
  const rows = [['field', 'value'], ...Object.entries(latestResult).flatMap(([key, value]) => Array.isArray(value) ? value.map((item) => [key, item]) : [[key, value]])];
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([csv], {type: 'text/csv'})); link.download = 'listing-audit.csv'; link.click(); URL.revokeObjectURL(link.href); event('export_csv');
});
$('history-list').addEventListener('click', (eventObject) => {
  const button = eventObject.target.closest('[data-history-index]'); if (!button) return;
  const item = historyItems()[Number(button.dataset.historyIndex)]; if (!item) return;
  restoreRequest(item.request); render(item.result);
});
$('clear-history').addEventListener('click', () => { if (window.confirm('Clear saved audit history from this browser?')) { writeStorage(HISTORY_KEY, []); renderHistory(); } });
$('upgrade-top').addEventListener('click', () => openUpgrade('header')); $('upgrade-result').addEventListener('click', () => openUpgrade('results'));
$('close-dialog').addEventListener('click', () => dialog.close()); $('notify-pro').addEventListener('click', () => dialog.close());
document.querySelectorAll('[data-plan]').forEach((button) => button.addEventListener('click', async () => {
  const plan = button.dataset.plan; const original = button.querySelector('small').textContent;
  button.disabled = true; button.querySelector('small').textContent = 'Opening checkout...'; $('billing-note').textContent = 'Preparing secure checkout...';
  try {
    const response = await fetch('/api/checkout', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({plan})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Checkout could not be started.');
    event('checkout_started', {plan}); window.location.assign(data.url);
  } catch (error) { $('billing-note').textContent = error.message; }
  finally { button.disabled = false; button.querySelector('small').textContent = original; }
}));

async function init() {
  const params = new URLSearchParams(window.location.search);
  const verified = await refreshEntitlement(params.get('session_id') || readStorage(SESSION_KEY, ''));
  if (params.get('checkout') === 'success') {
    $('checkout-message').textContent = verified ? 'Pro is active. Audit history and exports are unlocked in this browser.' : 'Payment received. Pro verification is still processing; refresh in a moment.';
    $('checkout-message').hidden = false;
  } else if (params.get('checkout') === 'cancelled') {
    $('checkout-message').textContent = 'Checkout was cancelled. No charge was made.'; $('checkout-message').hidden = false;
  }
  if (params.has('checkout')) window.history.replaceState({}, '', window.location.pathname);
  updateProUi(); updateCompletion(); event('app_opened', {pro: isPro});
}

init();

