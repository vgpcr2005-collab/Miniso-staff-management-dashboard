const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const numberMoney = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const state = { user: null, dashboard: null, rows: [], departments: [], report: null, toastTimer: null };
const pageMeta = {
  dashboard: ['PERFORMANCE OFFICE / OVERVIEW', 'Good morning', 'A clear read on this period’s performance.'],
  leaderboard: ['PERFORMANCE OFFICE / TEAM', 'Performance leaderboard', 'Compare target achievement across the team.'],
  'sales-entry': ['PERFORMANCE OFFICE / SALES', 'Record a sale', 'Your transactions update your performance automatically.'],
  people: ['PERFORMANCE OFFICE / PEOPLE', 'Staff accounts', 'Manage staff profiles and monthly targets.'],
  incentives: ['PERFORMANCE OFFICE / INCENTIVES', 'Incentive settings', 'Set transparent reward tiers for the whole team.'],
  reports: ['PERFORMANCE OFFICE / REPORTS', 'Reports & approvals', 'Review performance by month, quarter, department or staff member.']
};

init();

async function init() {
  setUpPeriods();
  $('#saleDate').value = localDateKey();
  updateCurrentDateTime();
  setInterval(updateCurrentDateTime, 1000);
  $('#loginForm').reset();
  $('#registerForm').reset();
  $('#registerForm').addEventListener('submit', register);
  $('#loginForm').addEventListener('submit', login);
  $('#showLoginBtn').addEventListener('click', showLoginPanel);
  $('#showRegisterBtn').addEventListener('click', showRegisterPanel);
  $('#demoAccounts').addEventListener('click', (event) => {
    const button = event.target.closest('[data-demo-user]');
    if (!button) return;
    $('#loginUsername').value = button.dataset.demoUser;
    $('#loginPassword').value = button.dataset.demoPassword;
    $('#loginError').hidden = true;
    $('#loginPassword').focus();
  });
  $('#logoutBtn').addEventListener('click', logout);
  $('#refreshBtn').addEventListener('click', refreshDashboard);
  $('#periodSelect').addEventListener('change', refreshDashboard);
  $('#mainNav').addEventListener('click', navigate);
  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-page-link]');
    if (link) { event.preventDefault(); navigateTo(link.dataset.pageLink); }
  });
  $('#staffSearch').addEventListener('input', renderLeaderboard);
  $('#departmentFilter').addEventListener('change', renderLeaderboard);
  $('#performanceFilter').addEventListener('change', renderLeaderboard);
  $('#salesForm').addEventListener('submit', submitSale);
  $('#staffForm').addEventListener('submit', createStaff);
  $('#rulesForm').addEventListener('submit', saveRules);
  $('#addTierBtn').addEventListener('click', () => addTierRow());
  $('#reportForm').addEventListener('submit', generateReport);
  $('#reportType').addEventListener('change', updateReportFilters);
  $('#exportCsvBtn').addEventListener('click', exportCsv);
  $('#exportPdfBtn').addEventListener('click', exportPdf);
  $('#closeProfile').addEventListener('click', () => $('#profileDialog').close());
  $('#leaderboardBody').addEventListener('click', onLeaderboardAction);
  $('#staffDirectory').addEventListener('click', onStaffAction);
  $('#approvalSummary').addEventListener('click', () => navigateTo('leaderboard'));

  try {
    const session = await api('/api/session');
    if (session.user) await enterApplication(session.user);
  } catch (error) {
    showToast(error.message, true);
  }
}

function setUpPeriods() {
  const periods = periodOptions();
  for (const select of [$('#periodSelect'), $('#reportPeriod')]) {
    select.replaceChildren(...periods.map(({ value, label }) => new Option(label, value)));
    select.value = periods[0].value;
  }
}

function periodOptions() {
  const now = new Date();
  const values = [];
  for (let offset = 0; offset < 12; offset++) {
    const month = new Date(now.getFullYear(), now.getMonth() - offset, 1);
    values.push({ value: `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}`, label: month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) });
  }
  const quarter = Math.floor(now.getMonth() / 3) + 1;
  for (let offset = 0; offset < 4; offset++) {
    let q = quarter - offset;
    let year = now.getFullYear();
    while (q <= 0) { q += 4; year--; }
    values.push({ value: `${year}-Q${q}`, label: `Q${q} ${year}` });
  }
  return values;
}

function localDateKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function updateCurrentDateTime() {
  const element = $('#currentDateTime');
  if (!element) return;
  element.textContent = new Date().toLocaleString('en-IN', { dateStyle: 'full', timeStyle: 'medium' });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/login') showLogin();
    throw new Error(data.error || 'The request could not be completed.');
  }
  return data;
}

function showRegisterPanel() {
  $('#registerPanel').hidden = false;
  $('#loginPanel').hidden = true;
  $('#loginError').hidden = true;
  $('#registerError').hidden = true;
  $('#registerName').focus();
}

function showLoginPanel() {
  $('#registerPanel').hidden = true;
  $('#loginPanel').hidden = false;
  $('#registerError').hidden = true;
  $('#loginError').hidden = true;
  $('#loginUsername').focus();
}

async function register(event) {
  event.preventDefault();
  const error = $('#registerError');
  error.hidden = true;
  const password = $('#registerPassword').value;
  if (password !== $('#registerConfirm').value) {
    error.textContent = 'The passwords do not match.';
    error.hidden = false;
    $('#registerConfirm').focus();
    return;
  }
  try {
    const result = await api('/api/register', {
      method: 'POST',
      body: JSON.stringify({ name: $('#registerName').value, username: $('#registerUsername').value, password })
    });
    $('#registerForm').reset();
    $('#loginUsername').value = result.user.username;
    $('#loginPassword').value = password;
    showToast('Account created. Sign in to open your dashboard.');
    showLoginPanel();
  } catch (failure) {
    error.textContent = failure.message;
    error.hidden = false;
  }
}

async function login(event) {
  event.preventDefault();
  const error = $('#loginError');
  error.hidden = true;
  try {
    const result = await api('/api/login', { method: 'POST', body: JSON.stringify({ username: $('#loginUsername').value, password: $('#loginPassword').value }) });
    $('#loginPassword').value = '';
    await enterApplication(result.user);
  } catch (failure) {
    error.textContent = failure.message === 'Username or password is incorrect.'
      ? 'That login did not match. Choose a demo account below or enter its username and password exactly as shown.'
      : failure.message;
    error.hidden = false;
    $('#loginPassword').focus();
  }
}

async function enterApplication(user) {
  state.user = user;
  $('#loginScreen').hidden = true;
  $('#application').hidden = false;
  $('#userName').textContent = user.name;
  $('#userRole').textContent = user.role.toUpperCase();
  $('#userAvatar').textContent = user.name.trim().charAt(0).toUpperCase();
  $$('.admin-only').forEach((element) => element.hidden = user.role !== 'admin');
  $$('.manager-only').forEach((element) => element.hidden = !['admin', 'manager'].includes(user.role));
  $$('.staff-only').forEach((element) => element.hidden = user.role !== 'staff');
  const firstPage = user.role === 'staff' ? 'sales-entry' : 'dashboard';
  navigateTo(firstPage, false);
  await loadAuxiliaryData();
  await refreshDashboard();
}

function showLogin() {
  state.user = null;
  $('#application').hidden = true;
  $('#loginScreen').hidden = false;
  $('#loginPassword').value = '';
}

async function logout() {
  try { await api('/api/logout', { method: 'POST', body: '{}' }); } catch (error) { /* Session expiry still returns to sign in. */ }
  showLogin();
}

function navigate(event) {
  const link = event.target.closest('[data-page]');
  if (!link) return;
  event.preventDefault();
  navigateTo(link.dataset.page);
}

function navigateTo(page, updateHash = true) {
  const pageId = `${page}Page`;
  if (!$("#" + pageId) || !pageAllowed(page)) page = state.user?.role === 'staff' ? 'sales-entry' : 'dashboard';
  $$('.page-content').forEach((section) => section.hidden = section.id !== `${page}Page`);
  $$('.nav-link').forEach((link) => link.classList.toggle('is-active', link.dataset.page === page));
  const [eyebrow, title, subtitle] = pageMeta[page];
  $('#pageEyebrow').textContent = eyebrow;
  $('#pageTitle').textContent = page === 'dashboard' ? `Good morning, ${state.user?.name.split(' ')[0] || ''}` : title;
  $('#pageSubtitle').textContent = subtitle;
  if (updateHash) history.replaceState(null, '', `#${page}`);
  if (page === 'leaderboard') renderLeaderboard();
  if (page === 'people') loadStaffDirectory();
  if (page === 'incentives') loadRules();
  if (page === 'reports') loadReportOptions();
}

function pageAllowed(page) {
  if (!state.user) return false;
  if (['dashboard', 'leaderboard'].includes(page)) return true;
  if (page === 'sales-entry') return state.user.role === 'staff';
  if (['people', 'incentives'].includes(page)) return state.user.role === 'admin';
  if (page === 'reports') return ['admin', 'manager'].includes(state.user.role);
  return false;
}

async function loadAuxiliaryData() {
  try {
    const data = await api('/api/departments');
    state.departments = data.rows;
    const options = [new Option('All departments', ''), ...data.rows.map((department) => new Option(department, department))];
    $('#departmentFilter').replaceChildren(...options);
    $('#reportDepartment').replaceChildren(...data.rows.map((department) => new Option(department, department)));
  } catch (error) { showToast(error.message, true); }
}

async function refreshDashboard() {
  if (!state.user) return;
  try {
    const period = $('#periodSelect').value;
    state.dashboard = await api(`/api/dashboard?period=${encodeURIComponent(period)}`);
    state.rows = state.dashboard.rows;
    $('#periodPill').textContent = state.dashboard.periodLabel;
    renderDashboard();
  } catch (error) { showToast(error.message, true); }
}

function renderDashboard() {
  renderStats();
  renderTrend();
  renderAlerts();
  renderTopList();
  renderApprovalSummary();
  renderLeaderboard();
  renderMyPerformance();
}

function renderStats() {
  const { stats, user } = state.dashboard;
  $('#statSales').textContent = money.format(stats.sales);
  $('#statAchievement').textContent = `${stats.achievement.toFixed(1)}%`;
  $('#statIncentive').textContent = money.format(stats.incentive);
  $('#statSalesCaption').textContent = `of ${money.format(stats.target)} target`;
  $('#statSalesPct').textContent = `${stats.achievement.toFixed(1)}%`;
  $('#statTargetCaption').textContent = user.role === 'staff' ? 'of your assigned target' : 'team sales against target';
  $('#staffCount').textContent = `${stats.staff} ${stats.staff === 1 ? 'staff member' : 'staff members'}`;
  $('#qualifiedCount').textContent = `${stats.qualified} qualified`;
  $('#incentiveCaption').textContent = user.role === 'staff' ? 'your estimated incentive' : 'pending manager approval';
  const progress = Math.min(100, Math.max(0, stats.achievement));
  $('#salesProgress').style.width = `${progress}%`;
  $('#achievementProgress').style.width = `${progress}%`;
}

function renderTrend() {
  const months = state.dashboard.trend;
  const maxValue = Math.max(1, ...months.flatMap((item) => [item.sales, item.target]));
  $('#trendChart').innerHTML = months.map((item) => {
    const actualHeight = Math.max(2, item.sales / maxValue * 100);
    const targetHeight = Math.max(2, item.target / maxValue * 100);
    const label = new Date(`${item.month}-01T12:00:00`).toLocaleDateString('en-IN', { month: 'short' });
    return `<div class="chart-month"><div class="chart-columns"><i class="chart-bar" style="height:${actualHeight}%" data-value="Sales ${escapeHtml(money.format(item.sales))}" title="Sales ${escapeHtml(money.format(item.sales))}"></i><i class="chart-bar target-bar" style="height:${targetHeight}%" data-value="Target ${escapeHtml(money.format(item.target))}" title="Target ${escapeHtml(money.format(item.target))}"></i></div><span>${label}</span></div>`;
  }).join('');
}

function renderAlerts() {
  const alerts = state.dashboard.alerts;
  $('#alertCount').textContent = alerts.length;
  $('#alertsList').innerHTML = alerts.length ? alerts.map((alert) => `<div class="alert-item ${alert.tone}"><i class="alert-dot"></i><span>${escapeHtml(alert.message)}</span></div>`).join('') : '<p class="empty-note">No target alerts for this period. The team is on track.</p>';
}

function renderTopList() {
  const rows = state.dashboard.leaderboard;
  $('#topList').innerHTML = rows.length ? rows.map((row, index) => `<div class="top-row"><span class="rank-number">${String(index + 1).padStart(2, '0')}</span><span class="rank-person"><b>${escapeHtml(row.name)}</b><small>${escapeHtml(row.department)}</small></span><span class="rank-score">${row.achievement.toFixed(1)}%<small>${escapeHtml(row.level)}</small></span></div>`).join('') : '<p class="empty-note">No staff results for this period.</p>';
}

function renderApprovalSummary() {
  const pending = state.dashboard.rows.filter((row) => row.incentive > 0 && row.approval !== 'Approved');
  $('#approvalQueueCount').textContent = pending.length;
  $('#approvalSummary').innerHTML = `<span class="approval-number">${pending.length}</span><p>${pending.length ? `${pending.length} incentive${pending.length === 1 ? '' : 's'} waiting for review` : 'All eligible incentives have been reviewed.'}</p>${['admin', 'manager'].includes(state.user.role) ? '<a class="button button-light" href="#leaderboard" data-page-link="leaderboard">Review queue →</a>' : ''}`;
}

function renderLeaderboard() {
  if (!$('#leaderboardBody') || !state.dashboard) return;
  let rows = [...state.dashboard.rows];
  const query = ($('#staffSearch')?.value || '').trim().toLowerCase();
  const department = $('#departmentFilter')?.value || '';
  const level = $('#performanceFilter')?.value || '';
  rows.sort((a, b) => b.achievement - a.achievement || a.name.localeCompare(b.name));
  rows = rows.filter((row) => (!query || `${row.name} ${row.staffId}`.toLowerCase().includes(query)) && (!department || row.department === department) && (!level || row.level === level));
  const canApprove = ['admin', 'manager'].includes(state.user.role);
  $('#leaderboardBody').innerHTML = rows.length ? rows.map((row, index) => `<tr><td><span class="staff-cell"><span class="staff-initial">${escapeHtml(row.name.charAt(0).toUpperCase())}</span><span><button class="staff-name-button" data-action="profile" data-staff-id="${escapeHtml(row.staffId)}">${escapeHtml(row.name)}</button><small style="display:block;color:#87918b;margin-top:3px">${escapeHtml(row.staffId)}</small></span></span></td><td>${escapeHtml(row.department)}</td><td>${money.format(row.target)}</td><td>${money.format(row.sales)}</td><td class="achievement-value">${row.achievement.toFixed(1)}%</td><td><span class="badge badge-${row.level.toLowerCase().replaceAll(' ', '-')}">${escapeHtml(row.level)}</span></td><td>${money.format(row.incentive)}</td><td>${canApprove ? `<button class="approval-button" data-action="approve" data-staff-id="${escapeHtml(row.staffId)}" ${row.incentive <= 0 || row.approval === 'Approved' ? 'disabled' : ''}>${row.approval === 'Approved' ? 'Approved' : row.incentive <= 0 ? 'Not eligible' : 'Approve'}</button>` : escapeHtml(row.approval)}</td></tr>`).join('') : '<tr><td colspan="8" class="empty-note">No staff match these filters.</td></tr>';
}

async function onLeaderboardAction(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  if (button.dataset.action === 'approve') {
    if (!confirm(`Approve ${button.dataset.staffId}'s ${$('#periodSelect').selectedOptions[0].textContent} incentive?`)) return;
    try {
      await api('/api/approval', { method: 'POST', body: JSON.stringify({ staffId: button.dataset.staffId, period: $('#periodSelect').value, approved: true }) });
      showToast('Incentive approved.');
      await refreshDashboard();
    } catch (error) { showToast(error.message, true); }
  }
  if (button.dataset.action === 'profile') await showProfile(button.dataset.staffId);
}

function renderMyPerformance() {
  if (state.user.role !== 'staff') return;
  const row = state.dashboard.rows[0];
  if (!row) { $('#myPerformance').innerHTML = '<p class="empty-note">Your profile is not active. Contact your manager.</p>'; return; }
  const months = state.dashboard.trend;
  const max = Math.max(1, ...months.map((item) => item.sales));
  $('#myPerformance').innerHTML = `<div class="my-performance-content"><div><span class="section-index">${escapeHtml(state.dashboard.periodLabel.toUpperCase())}</span><div class="my-score">${row.achievement.toFixed(1)}%</div><span class="my-score-caption">${escapeHtml(row.level)} · ${money.format(row.sales)} sales</span></div><div class="progress-track"><i style="width:${Math.min(100, row.achievement)}%"></i></div><div class="my-kpis"><div><span>MONTHLY TARGET</span><b>${money.format(row.target)}</b></div><div><span>INCENTIVE</span><b>${money.format(row.incentive)}</b></div></div><div><p class="section-index">SALES TREND</p><div class="mini-trend">${months.map((item) => `<div class="mini-trend-column"><i style="height:${Math.max(2,item.sales/max*64)}px"></i><span>${new Date(`${item.month}-01T12:00:00`).toLocaleDateString('en-IN',{month:'short'})}</span></div>`).join('')}</div></div></div>`;
}

async function submitSale(event) {
  event.preventDefault();
  const error = $('#salesError'); error.hidden = true;
  try {
    await api('/api/sales', { method: 'POST', body: JSON.stringify({ product: $('#saleProduct').value.trim(), quantity: Number($('#saleQuantity').value), amount: Number($('#saleAmount').value), date: $('#saleDate').value }) });
    $('#salesForm').reset(); $('#saleQuantity').value = 1; $('#saleDate').value = localDateKey();
    showToast('Sale recorded. Performance has been updated.');
    await refreshDashboard();
  } catch (failure) { error.textContent = failure.message; error.hidden = false; }
}

async function loadStaffDirectory() {
  try {
    const data = await api(`/api/staff?month=${encodeURIComponent($('#periodSelect').value)}`);
    $('#directoryCount').textContent = data.rows.length;
    $('#staffDirectory').innerHTML = data.rows.length ? data.rows.map((row) => `<tr><td><span class="staff-cell"><span class="staff-initial">${escapeHtml(row.name.charAt(0))}</span><span><b>${escapeHtml(row.name)}</b><small style="display:block;color:#87918b;margin-top:3px">${escapeHtml(row.staff_id)}</small></span></span></td><td>${escapeHtml(row.department)}</td><td>${escapeHtml(row.username)}</td><td>${money.format(row.target)}</td><td><button class="approval-button" data-set-target="${escapeHtml(row.staff_id)}" data-current-target="${row.target}">Set daily target</button> <button class="approval-button" data-remove-staff="${escapeHtml(row.staff_id)}">Remove</button></td></tr>`).join('') : '<tr><td colspan="5" class="empty-note">No staff accounts found.</td></tr>';
  } catch (error) { showToast(error.message, true); }
}

async function createStaff(event) {
  event.preventDefault();
  const error = $('#staffError'); error.hidden = true;
  const body = { name: $('#newStaffName').value, department: $('#newStaffDepartment').value, target: Number($('#newStaffTarget').value), username: $('#newStaffUsername').value, password: $('#newStaffPassword').value, phone: $('#newStaffPhone').value, email: $('#newStaffEmail').value };
  try {
    await api('/api/staff', { method: 'POST', body: JSON.stringify(body) });
    $('#staffForm').reset(); showToast('Staff account created.'); await loadStaffDirectory(); await loadAuxiliaryData(); await refreshDashboard();
  } catch (failure) { error.textContent = failure.message; error.hidden = false; }
}

async function onStaffAction(event) {
  const targetButton = event.target.closest('[data-set-target]');
  if (targetButton) {
    const target = Number(prompt(`Daily target for ${targetButton.dataset.setTarget}:`, targetButton.dataset.currentTarget));
    if (!Number.isFinite(target) || target <= 0) return;
    try {
      await api('/api/target', { method: 'POST', body: JSON.stringify({ staffId: targetButton.dataset.setTarget, target }) });
      showToast('Daily target updated.'); await loadStaffDirectory(); await refreshDashboard();
    } catch (error) { showToast(error.message, true); }
    return;
  }
  const button = event.target.closest('[data-remove-staff]');
  if (!button) return;
  if (!confirm(`Remove ${button.dataset.removeStaff}? Their sale history will also be removed.`)) return;
  try { await api(`/api/staff/${encodeURIComponent(button.dataset.removeStaff)}`, { method: 'DELETE' }); showToast('Staff account removed.'); await loadStaffDirectory(); await loadAuxiliaryData(); await refreshDashboard(); }
  catch (error) { showToast(error.message, true); }
}

async function loadRules() {
  try {
    const data = await api('/api/rules');
    $('#tierRows').replaceChildren();
    data.rows.forEach((rule) => addTierRow(rule.minAchievement, rule.incentive));
  } catch (error) { showToast(error.message, true); }
}

function addTierRow(minimum = '', reward = '') {
  const row = document.createElement('div');
  row.className = 'tier-row';
  row.innerHTML = `<label><span class="section-index">FROM</span><input aria-label="Minimum achievement percent" type="number" min="0" step="0.01" value="${escapeHtml(String(minimum))}" required /></label><label><span class="section-index">FIXED REWARD ₹</span><input aria-label="Incentive reward in rupees" type="number" min="0" step="0.01" value="${escapeHtml(String(reward))}" required /></label><button class="remove-tier" type="button" aria-label="Remove incentive tier">×</button>`;
  row.querySelector('.remove-tier').addEventListener('click', () => row.remove());
  $('#tierRows').appendChild(row);
}

async function saveRules(event) {
  event.preventDefault();
  const error = $('#rulesError'); error.hidden = true;
  const rules = $$('.tier-row').map((row) => ({ minAchievement: Number(row.querySelectorAll('input')[0].value), incentive: Number(row.querySelectorAll('input')[1].value) }));
  if (!rules.length) { error.textContent = 'Add at least one tier.'; error.hidden = false; return; }
  try { await api('/api/rules', { method: 'POST', body: JSON.stringify({ rules }) }); showToast('Incentive rules saved.'); await refreshDashboard(); }
  catch (failure) { error.textContent = failure.message; error.hidden = false; }
}

async function loadReportOptions() {
  try {
    const data = await api('/api/staff');
    $('#reportStaff').replaceChildren(...data.rows.map((row) => new Option(`${row.name} · ${row.staff_id}`, row.staff_id)));
    $('#reportPeriod').value = $('#periodSelect').value;
  } catch (error) { showToast(error.message, true); }
  updateReportFilters();
}

function updateReportFilters() {
  const type = $('#reportType').value;
  $('#reportDepartmentWrap').hidden = type !== 'department';
  $('#reportStaffWrap').hidden = type !== 'individual';
}

async function generateReport(event) {
  event.preventDefault();
  const error = $('#reportError'); error.hidden = true;
  const type = $('#reportType').value;
  const params = new URLSearchParams({ period: $('#reportPeriod').value, scope: type });
  if (type === 'department') params.set('department', $('#reportDepartment').value);
  if (type === 'individual') params.set('staffId', $('#reportStaff').value);
  try {
    state.report = await api(`/api/report?${params}`);
    renderReportResult();
  } catch (failure) { error.textContent = failure.message; error.hidden = false; }
}

function renderReportResult() {
  const report = state.report;
  $('#reportTitle').textContent = `${report.periodLabel} · ${report.type[0].toUpperCase()}${report.type.slice(1)} report`;
  const values = [['Staff', report.summary.staff], ['Total sales', money.format(report.summary.sales)], ['Target', money.format(report.summary.target)], ['Achievement', `${report.summary.achievement.toFixed(2)}%`], ['Incentive', money.format(report.summary.incentive)]];
  $('#reportStats').innerHTML = values.map(([label, value]) => `<span>${label}<b>${value}</b></span>`).join('');
  $('#reportBody').innerHTML = report.rows.length ? report.rows.map((row) => `<tr><td>${escapeHtml(row.name)} · ${escapeHtml(row.staffId)}</td><td>${escapeHtml(row.department)}</td><td>${money.format(row.target)}</td><td>${money.format(row.sales)}</td><td>${row.achievement.toFixed(2)}%</td><td><span class="badge badge-${row.level.toLowerCase().replaceAll(' ', '-')}">${escapeHtml(row.level)}</span></td><td>${money.format(row.incentive)}</td></tr>`).join('') : '<tr><td colspan="7" class="empty-note">No results for this period.</td></tr>';
  $('#reportResult').hidden = false;
}

function exportCsv() {
  if (!state.report) return;
  const columns = ['Staff ID', 'Name', 'Department', 'Target', 'Sales', 'Achievement %', 'Performance', 'Incentive', 'Approval'];
  const lines = [columns, ...state.report.rows.map((row) => [row.staffId, row.name, row.department, row.target, row.sales, row.achievement.toFixed(2), row.level, row.incentive, row.approval])];
  const csv = '\ufeff' + lines.map((line) => line.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n');
  download(new Blob([csv], { type: 'text/csv;charset=utf-8' }), `miniso-${state.report.period}-report.csv`);
}

function exportPdf() {
  if (!state.report) return;
  const printWindow = window.open('', '_blank');
  if (!printWindow) { showToast('Allow pop-ups to open the print-ready report.', true); return; }
  printWindow.opener = null;
  printWindow.addEventListener('load', () => printWindow.print(), { once: true });
  const rows = state.report.rows.map((row) => `<tr><td>${escapeHtml(row.staffId)}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.department)}</td><td>${money.format(row.target)}</td><td>${money.format(row.sales)}</td><td>${row.achievement.toFixed(2)}%</td><td>${escapeHtml(row.level)}</td><td>${money.format(row.incentive)}</td></tr>`).join('');
  printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>MINISO ${escapeHtml(state.report.periodLabel)} report</title><style>body{font:12px Arial;color:#1c2924;padding:36px}h1{font-size:23px;margin-bottom:5px}.muted{color:#67746b;font-size:11px}table{border-collapse:collapse;width:100%;margin-top:24px}th,td{border-bottom:1px solid #ddd;padding:9px;text-align:left}th{font-size:9px;background:#f3f5f0}.summary{display:flex;gap:24px;margin-top:22px}.summary b{display:block;margin-top:5px}</style></head><body><p class="muted">MINISO PERFORMANCE OFFICE</p><h1>${escapeHtml(state.report.periodLabel)} · ${escapeHtml(state.report.type)} report</h1><p class="muted">Generated ${new Date().toLocaleString()}</p><div class="summary"><span>Staff<b>${state.report.summary.staff}</b></span><span>Sales<b>${money.format(state.report.summary.sales)}</b></span><span>Target<b>${money.format(state.report.summary.target)}</b></span><span>Achievement<b>${state.report.summary.achievement.toFixed(2)}%</b></span><span>Incentives<b>${money.format(state.report.summary.incentive)}</b></span></div><table><thead><tr><th>ID</th><th>Staff</th><th>Department</th><th>Target</th><th>Sales</th><th>Achievement</th><th>Level</th><th>Incentive</th></tr></thead><tbody>${rows}</tbody></table></body></html>`);
  printWindow.document.close();
}

async function showProfile(staffId) {
  try {
    const profile = await api(`/api/profile/${encodeURIComponent(staffId)}?period=${encodeURIComponent($('#periodSelect').value)}`);
    const row = profile.current;
    $('#profileContent').innerHTML = `<p class="section-index">STAFF PERFORMANCE PROFILE</p><div class="profile-header"><span class="staff-initial">${escapeHtml(row.name.charAt(0))}</span><div><h2>${escapeHtml(row.name)}</h2><p>${escapeHtml(row.staffId)} · ${escapeHtml(row.department)}</p></div><span class="badge badge-${row.level.toLowerCase().replaceAll(' ', '-')}">${escapeHtml(row.level)}</span></div><div class="profile-summary"><div><span>Monthly target</span><b>${money.format(row.target)}</b></div><div><span>Sales this period</span><b>${money.format(row.sales)}</b></div><div><span>Achievement</span><b>${row.achievement.toFixed(1)}%</b></div><div><span>Incentive</span><b>${money.format(row.incentive)}</b></div><div><span>Approval</span><b>${escapeHtml(row.approval)}</b></div></div><p class="section-index">MONTHLY HISTORY</p><div class="profile-history">${profile.history.map((item) => `<div class="profile-history-row"><span>${escapeHtml(item.label)}</span><span>${money.format(item.sales)}</span><b>${item.achievement.toFixed(1)}%</b></div>`).join('')}</div>`;
    $('#profileDialog').showModal();
  } catch (error) { showToast(error.message, true); }
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}

function showToast(message, isError = false) {
  const toast = $('#toast'); toast.textContent = message; toast.classList.toggle('is-error', isError); toast.classList.add('is-visible');
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 3200);
}
