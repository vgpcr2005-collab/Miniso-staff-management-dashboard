const STORAGE_KEY = 'miniso-performance-dashboard';
const ACCOUNTS_KEY = 'miniso-dashboard-accounts';
const SESSION_KEY = 'miniso-dashboard-session';
const PASSWORD_HASH_ITERATIONS = 120000;
const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0
});

function currentMonth() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
}

function localDateString(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function createInitialState() {
  const month = currentMonth();
  const monthStart = `${month}-01`;
  return {
    staff: [
      { id: 'S001', name: 'Ravi Kumar', department: 'Sales', status: 'Active', defaultTarget: 100000 },
      { id: 'S002', name: 'Priya Sharma', department: 'Sales', status: 'Active', defaultTarget: 120000 },
      { id: 'S003', name: 'Arun Kumar', department: 'Sales', status: 'Active', defaultTarget: 90000 }
    ],
    targets: [
      { staffId: 'S001', month, amount: 100000 },
      { staffId: 'S002', month, amount: 120000 },
      { staffId: 'S003', month, amount: 90000 }
    ],
    sales: [
      { id: 'SALE001', staffId: 'S001', date: monthStart, product: 'Product A', quantity: 1, amount: 5000, paymentStatus: 'Completed' },
      { id: 'SALE002', staffId: 'S001', date: monthStart, product: 'Product B', quantity: 1, amount: 8000, paymentStatus: 'Completed' },
      { id: 'SALE003', staffId: 'S001', date: monthStart, product: 'Travel Bag', quantity: 1, amount: 72000, paymentStatus: 'Completed' },
      { id: 'SALE004', staffId: 'S002', date: monthStart, product: 'Product C', quantity: 1, amount: 10000, paymentStatus: 'Completed' },
      { id: 'SALE005', staffId: 'S002', date: monthStart, product: 'Beauty Kit', quantity: 2, amount: 120000, paymentStatus: 'Completed' },
      { id: 'SALE006', staffId: 'S003', date: monthStart, product: 'Storage Box', quantity: 1, amount: 40000, paymentStatus: 'Completed' }
    ],
    rules: [
      { threshold: 80, reward: 1000 },
      { threshold: 100, reward: 2000 },
      { threshold: 110, reward: 3000 },
      { threshold: 120, reward: 5000 }
    ]
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadState() {
  const serialized = localStorage.getItem(STORAGE_KEY);
  if (!serialized) return createInitialState();

  try {
    const saved = JSON.parse(serialized);
    if (Array.isArray(saved.staff) && Array.isArray(saved.sales)) {
      return migrateState(saved);
    }
    throw new Error('Saved dashboard data has an unsupported format.');
  } catch (error) {
    console.error('Could not load saved dashboard data.', error);
    window.alert('Saved dashboard data could not be read. Demo data has been loaded instead.');
    return createInitialState();
  }
}

function migrateState(saved) {
  const month = currentMonth();
  const daysInMonth = new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0).getDate();
  const staff = saved.staff.map((person) => ({
    id: String(person.id),
    name: String(person.name || ''),
    department: String(person.department || 'Sales'),
    status: person.status === 'Inactive' ? 'Inactive' : 'Active',
    defaultTarget: Number(person.defaultTarget ?? person.target ?? 0) * (person.defaultTarget == null && person.target != null ? daysInMonth : 1)
  }));
  let targets = Array.isArray(saved.targets) ? saved.targets : [];
  if (!targets.length) {
    targets = saved.staff
      .filter((person) => Number(person.target) > 0)
      .map((person) => ({
        staffId: String(person.id),
        month,
        amount: Number(person.target) * (person.defaultTarget == null ? daysInMonth : 1)
      }));
  }

  const sales = saved.sales.map((sale, index) => ({
    id: String(sale.id || `SALE${String(index + 1).padStart(3, '0')}`),
    staffId: String(sale.staffId),
    date: String(sale.date || `${month}-01`),
    product: String(sale.product || 'Legacy sale'),
    quantity: Math.max(1, Number(sale.quantity) || 1),
    amount: Number(sale.amount) || 0,
    paymentStatus: ['Completed', 'Pending', 'Refunded'].includes(sale.paymentStatus) ? sale.paymentStatus : 'Completed'
  }));
  const initialRules = createInitialState().rules;
  const rules = Array.isArray(saved.rules) && saved.rules.length === 4
      && saved.rules.every((rule) => Number.isFinite(Number(rule.threshold)) && Number.isFinite(Number(rule.reward)))
    ? saved.rules
    : initialRules;

  return {
    staff,
    targets: targets.map((target) => ({
      staffId: String(target.staffId),
      month: String(target.month),
      amount: Number(target.amount) || 0
    })),
    sales,
    rules: rules.map((rule) => ({ threshold: Number(rule.threshold), reward: Number(rule.reward) }))
  };
}

let state = loadState();

const $ = (id) => document.getElementById(id);
const staffForm = $('staffForm');
const targetForm = $('targetForm');
const salesForm = $('salesForm');
const rulesForm = $('rulesForm');
const reportMonthInput = $('reportMonth');

initialize();

function initialize() {
  reportMonthInput.value = currentMonth();
  $('targetMonth').value = currentMonth();
  $('saleDate').value = localDateString();
  updateCurrentDateTime();
  window.setInterval(updateCurrentDateTime, 1000);

  staffForm.addEventListener('submit', handleStaffSubmit);
  targetForm.addEventListener('submit', handleTargetSubmit);
  salesForm.addEventListener('submit', handleSalesSubmit);
  rulesForm.addEventListener('submit', handleRulesSubmit);
  $('salesStaffId').addEventListener('change', updateSalesStaffName);
  $('targetStaffId').addEventListener('change', updateTargetStaffName);
  $('targetMonth').addEventListener('change', updateTargetStaffName);
  reportMonthInput.addEventListener('change', renderDashboard);
  $('trendView').addEventListener('change', renderSalesChart);
  $('resetDataBtn').addEventListener('click', resetData);
  $('exportBtn').addEventListener('click', exportMonthlyCsv);
  $('loginForm').addEventListener('submit', handleLogin);
  $('registerForm').addEventListener('submit', handleRegistration);
  $('showRegisterBtn').addEventListener('click', showRegistrationForm);
  $('showLoginBtn').addEventListener('click', showLoginForm);
  $('logoutBtn').addEventListener('click', handleLogout);

  populateRuleFields();
  renderStaffOptions();
  renderDashboard();
  restoreSession();
}

function showRegistrationForm() {
  $('loginForm').hidden = true;
  $('registerForm').hidden = false;
  $('loginError').hidden = true;
  $('registerError').hidden = true;
  $('registerName').focus();
}

function showLoginForm() {
  $('registerForm').hidden = true;
  $('loginForm').hidden = false;
  $('loginError').hidden = true;
  $('registerError').hidden = true;
  $('loginUsername').focus();
}

function readAccounts() {
  const serialized = localStorage.getItem(ACCOUNTS_KEY);
  if (!serialized) return [];
  const accounts = JSON.parse(serialized);
  if (!Array.isArray(accounts) || accounts.some((account) =>
    typeof account.username !== 'string'
    || typeof account.name !== 'string'
    || typeof account.salt !== 'string'
    || typeof account.passwordHash !== 'string'
  )) {
    throw new Error('Saved account data is invalid. Clear this browser’s account storage and register again.');
  }
  return accounts;
}

function restoreSession() {
  try {
    const username = sessionStorage.getItem(SESSION_KEY);
    if (!username) return;
    const account = readAccounts().find((item) => item.username === username);
    if (account) openDashboard(account);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch (error) {
    showAuthError('loginError', error.message);
  }
}

async function handleRegistration(event) {
  event.preventDefault();
  const name = $('registerName').value.trim();
  const username = $('registerUsername').value.trim().toLowerCase();
  const password = $('registerPassword').value;
  const error = $('registerError');
  error.hidden = true;

  if (name.length < 2) {
    showAuthError('registerError', 'Enter your full name.');
    return;
  }
  if (!/^[a-z0-9_-]{3,40}$/.test(username)) {
    showAuthError('registerError', 'Username must be 3–40 characters and use letters, numbers, _ or -.');
    return;
  }
  if (password.length < 8) {
    showAuthError('registerError', 'Password must contain at least 8 characters.');
    return;
  }
  if (password !== $('registerConfirm').value) {
    showAuthError('registerError', 'The passwords do not match.');
    return;
  }

  try {
    const accounts = readAccounts();
    if (accounts.some((account) => account.username === username)) {
      showAuthError('registerError', 'That username is already registered in this browser.');
      return;
    }
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const passwordHash = await hashPassword(password, salt);
    accounts.push({
      name,
      username,
      salt: bytesToHex(salt),
      passwordHash
    });
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
    sessionStorage.setItem(SESSION_KEY, username);
    $('registerForm').reset();
    openDashboard({ name, username });
  } catch (failure) {
    showAuthError('registerError', failure.message || 'Unable to create the account in this browser.');
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = $('loginUsername').value.trim().toLowerCase();
  const password = $('loginPassword').value;
  $('loginError').hidden = true;

  try {
    const account = readAccounts().find((item) => item.username === username);
    if (!account) {
      showAuthError('loginError', 'Username or password is incorrect.');
      return;
    }
    const candidate = await hashPassword(password, hexToBytes(account.salt));
    if (!constantTimeEqual(candidate, account.passwordHash)) {
      showAuthError('loginError', 'Username or password is incorrect.');
      return;
    }
    sessionStorage.setItem(SESSION_KEY, username);
    $('loginForm').reset();
    openDashboard(account);
  } catch (failure) {
    showAuthError('loginError', failure.message || 'Unable to sign in with browser storage.');
  }
}

async function hashPassword(password, salt) {
  if (!crypto.subtle) throw new Error('Secure password hashing is unavailable in this browser. Open this dashboard in a modern browser.');
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({
    name: 'PBKDF2',
    salt,
    iterations: PASSWORD_HASH_ITERATIONS,
    hash: 'SHA-256'
  }, key, 256);
  return bytesToHex(new Uint8Array(bits));
}

function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function hexToBytes(hex) {
  if (!/^(?:[0-9a-f]{2})+$/i.test(hex)) throw new Error('Saved account security data is invalid.');
  return new Uint8Array(hex.match(/.{2}/g).map((byte) => Number.parseInt(byte, 16)));
}

function constantTimeEqual(left, right) {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function openDashboard(account) {
  $('authScreen').hidden = true;
  $('dashboardApp').hidden = false;
  $('signedInUser').textContent = account.name;
  renderDashboard();
}

function handleLogout() {
  sessionStorage.removeItem(SESSION_KEY);
  $('dashboardApp').hidden = true;
  $('authScreen').hidden = false;
  $('loginForm').reset();
  showLoginForm();
}

function showAuthError(id, message) {
  const element = $(id);
  element.textContent = message;
  element.hidden = false;
}

function handleStaffSubmit(event) {
  event.preventDefault();
  const name = $('staffName').value.trim();
  const department = $('department').value.trim();
  const target = Number($('target').value);
  const status = $('staffStatus').value;
  if (!name || !department || !Number.isFinite(target) || target <= 0) {
    window.alert('Enter a staff name, department, and monthly target greater than zero.');
    return;
  }
  if (state.staff.some((person) => person.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    window.alert('A staff member with that name already exists.');
    return;
  }

  const id = generateStaffId();
  state.staff.push({ id, name, department, status, defaultTarget: target });
  upsertTarget(id, reportMonthInput.value, target);
  persistState();
  staffForm.reset();
  $('staffStatus').value = 'Active';
  renderStaffOptions();
  renderDashboard();
}

function handleTargetSubmit(event) {
  event.preventDefault();
  const staffId = $('targetStaffId').value;
  const month = $('targetMonth').value;
  const amount = Number($('targetAmount').value);
  if (!staffId || !month || !Number.isFinite(amount) || amount <= 0) {
    window.alert('Choose a staff member and month, and enter a target greater than zero.');
    return;
  }

  upsertTarget(staffId, month, amount);
  const person = state.staff.find((item) => item.id === staffId);
  if (person && month === reportMonthInput.value) person.defaultTarget = amount;
  persistState();
  targetForm.reset();
  $('targetMonth').value = reportMonthInput.value;
  renderDashboard();
}

function handleSalesSubmit(event) {
  event.preventDefault();
  const staffId = $('salesStaffId').value;
  const date = $('saleDate').value;
  const product = $('product').value.trim();
  const quantity = Number($('quantity').value);
  const amount = Number($('salesAmount').value);
  if (!state.staff.some((person) => person.id === staffId && person.status === 'Active')) {
    window.alert('Select an active staff member before recording a sale.');
    return;
  }
  if (!date || !product || !Number.isInteger(quantity) || quantity <= 0 || !Number.isFinite(amount) || amount <= 0) {
    window.alert('Enter a valid date, product, quantity, and sale amount.');
    return;
  }
  if (date.slice(0, 7) !== reportMonthInput.value) {
    window.alert('Sale date must be in the selected reporting month.');
    return;
  }

  state.sales.push({
    id: generateSaleId(),
    staffId,
    date,
    product,
    quantity,
    amount,
    paymentStatus: $('paymentStatus').value
  });
  persistState();
  salesForm.reset();
  $('saleDate').value = localDateString();
  $('quantity').value = '1';
  $('paymentStatus').value = 'Completed';
  renderStaffOptions();
  renderDashboard();
}

function handleRulesSubmit(event) {
  event.preventDefault();
  const rules = [];
  for (let index = 1; index <= 4; index += 1) {
    rules.push({
      threshold: Number($(`tier${index}Threshold`).value),
      reward: Number($(`tier${index}Reward`).value)
    });
  }
  const valid = rules.every((rule) => Number.isFinite(rule.threshold) && rule.threshold > 0
      && Number.isFinite(rule.reward) && rule.reward >= 0)
    && rules.every((rule, index) => index === 0 || rule.threshold > rules[index - 1].threshold);
  if (!valid) {
    window.alert('Enter non-negative rewards and strictly increasing achievement thresholds.');
    return;
  }
  state.rules = rules;
  persistState();
  renderDashboard();
}

function renderDashboard() {
  renderStats();
  renderPerformanceTable();
  renderStaffTable();
  renderSalesTable();
  renderAttentionList();
  renderSalesChart();
  renderReport();
}

function getSelectedMonth() {
  return reportMonthInput.value || currentMonth();
}

function getActiveStaff() {
  return state.staff.filter((person) => person.status === 'Active');
}

function getTarget(staffId, month = getSelectedMonth()) {
  const target = state.targets.find((item) => item.staffId === staffId && item.month === month);
  return target ? target.amount : 0;
}

function getSales(staffId, month = getSelectedMonth()) {
  return state.sales.filter((sale) => sale.staffId === staffId
    && sale.date.slice(0, 7) === month
    && sale.paymentStatus !== 'Refunded');
}

function getSalesTotal(staffId, month = getSelectedMonth()) {
  return getSales(staffId, month).reduce((total, sale) => total + sale.amount, 0);
}

function getAchievement(sales, target) {
  return target > 0 ? (sales / target) * 100 : 0;
}

function calculateIncentive(achievement) {
  const eligible = state.rules.filter((rule) => achievement >= rule.threshold);
  return eligible.length ? eligible[eligible.length - 1].reward : 0;
}

function getPerformance(staff) {
  const target = getTarget(staff.id);
  const sales = getSalesTotal(staff.id);
  const achievement = getAchievement(sales, target);
  return { target, sales, achievement, gap: target - sales, incentive: calculateIncentive(achievement) };
}

function renderStats() {
  const activeStaff = getActiveStaff();
  const monthlyTarget = activeStaff.reduce((total, person) => total + getTarget(person.id), 0);
  const totalSales = activeStaff.reduce((total, person) => total + getSalesTotal(person.id), 0);
  const achieved = activeStaff.filter((person) => getAchievement(getSalesTotal(person.id), getTarget(person.id)) >= 100).length;
  const incentive = activeStaff.reduce((total, person) => total + getPerformance(person).incentive, 0);
  $('totalSales').textContent = formatCurrency(totalSales);
  $('monthlyTarget').textContent = formatCurrency(monthlyTarget);
  $('achievement').textContent = `${getAchievement(totalSales, monthlyTarget).toFixed(1)}%`;
  $('totalIncentive').textContent = formatCurrency(incentive);
  $('staffOnTarget').textContent = `${achieved} / ${activeStaff.length}`;
}

function renderPerformanceTable() {
  const body = $('performanceTableBody');
  body.replaceChildren();
  const staff = getActiveStaff();
  if (!staff.length) {
    appendMessageRow(body, 8, 'No active staff members. Add staff to see performance.');
    return;
  }

  staff.forEach((person) => {
    const performance = getPerformance(person);
    const row = document.createElement('tr');
    appendCell(row, person.id);
    appendCell(row, person.name);
    appendCell(row, formatCurrency(performance.target));
    appendCell(row, formatCurrency(performance.sales));
    const achievementCell = appendCell(row, `${performance.achievement.toFixed(1)}%`);
    achievementCell.append(createProgress(performance.achievement));
    appendCell(row, performance.gap > 0
      ? `${formatCurrency(performance.gap)} remaining`
      : `${formatCurrency(Math.abs(performance.gap))} above target`);
    appendCell(row, formatCurrency(performance.incentive));
    const statusCell = appendCell(row, '');
    const status = document.createElement('span');
    status.className = `status-badge ${getStatusClass(performance.achievement)}`;
    status.textContent = getStatusLabel(performance.achievement);
    statusCell.append(status);
    body.append(row);
  });
}

function renderStaffTable() {
  const body = $('staffTableBody');
  body.replaceChildren();
  if (!state.staff.length) {
    appendMessageRow(body, 4, 'No staff members have been added.');
    return;
  }
  state.staff.forEach((person) => {
    const row = document.createElement('tr');
    appendCell(row, person.id);
    appendCell(row, person.name);
    appendCell(row, person.department);
    appendCell(row, person.status);
    body.append(row);
  });
}

function renderSalesTable() {
  const body = $('salesTableBody');
  body.replaceChildren();
  const month = getSelectedMonth();
  const monthSales = state.sales
    .filter((sale) => sale.date.slice(0, 7) === month)
    .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  if (!monthSales.length) {
    appendMessageRow(body, 8, 'No sales recorded for this month.');
    return;
  }
  monthSales.forEach((sale) => {
    const person = state.staff.find((item) => item.id === sale.staffId);
    const row = document.createElement('tr');
    appendCell(row, sale.id);
    appendCell(row, formatDate(sale.date));
    appendCell(row, sale.staffId);
    appendCell(row, person ? person.name : 'Unknown staff');
    appendCell(row, sale.product);
    appendCell(row, String(sale.quantity));
    appendCell(row, formatCurrency(sale.amount));
    const paymentCell = appendCell(row, sale.paymentStatus);
    if (sale.paymentStatus === 'Refunded') paymentCell.classList.add('muted-row');
    body.append(row);
  });
}

function renderAttentionList() {
  const container = $('attentionList');
  container.replaceChildren();
  const active = getActiveStaff().map((person) => ({ person, ...getPerformance(person) }));
  const needsAttention = active.filter((item) => item.achievement < 80)
    .sort((a, b) => a.achievement - b.achievement);
  const topPerformer = active.filter((item) => item.achievement >= 120)
    .sort((a, b) => b.achievement - a.achievement)[0];

  needsAttention.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'attention-item attention-warning';
    const heading = document.createElement('strong');
    heading.textContent = `${item.person.name} — ${item.person.id}`;
    const details = document.createElement('p');
    details.textContent = `${item.achievement.toFixed(1)}% achieved · ${formatCurrency(Math.max(0, item.gap))} remaining`;
    const note = document.createElement('small');
    note.textContent = 'Behind target. Review progress and offer support.';
    card.append(heading, details, note);
    container.append(card);
  });

  if (topPerformer) {
    const card = document.createElement('article');
    card.className = 'attention-item attention-success';
    const heading = document.createElement('strong');
    heading.textContent = `Top performer: ${topPerformer.person.name} — ${topPerformer.person.id}`;
    const details = document.createElement('p');
    details.textContent = `${topPerformer.achievement.toFixed(1)}% achieved · ${formatCurrency(Math.abs(topPerformer.gap))} above target`;
    card.append(heading, details);
    container.append(card);
  }

  if (!needsAttention.length && !topPerformer) {
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = active.length ? 'No staff require attention right now.' : 'Add active staff to see performance alerts.';
    container.append(message);
  }
}

function renderSalesChart() {
  const chart = $('salesChart');
  chart.replaceChildren();
  const month = getSelectedMonth();
  const view = $('trendView').value;
  const buckets = view === 'daily' ? dailyBuckets(month)
    : view === 'weekly' ? weeklyBuckets(month)
      : monthlyBuckets(month);
  const max = Math.max(1, ...buckets.flatMap((bucket) => [bucket.sales, bucket.target]));
  buckets.forEach((bucket) => {
    const item = document.createElement('div');
    item.className = 'chart-column';
    const values = document.createElement('div');
    values.className = 'chart-bars';
    const targetBar = document.createElement('div');
    targetBar.className = 'chart-bar target-bar';
    targetBar.style.height = `${Math.max(2, (bucket.target / max) * 100)}%`;
    targetBar.title = `Target: ${formatCurrency(bucket.target)}`;
    const salesBar = document.createElement('div');
    salesBar.className = 'chart-bar sales-bar';
    salesBar.style.height = `${Math.max(2, (bucket.sales / max) * 100)}%`;
    salesBar.title = `Sales: ${formatCurrency(bucket.sales)}`;
    values.append(targetBar, salesBar);
    const label = document.createElement('span');
    label.className = 'chart-label';
    label.textContent = bucket.label;
    const total = document.createElement('small');
    total.className = 'chart-total';
    total.textContent = formatCompactCurrency(bucket.sales);
    item.append(values, label, total);
    chart.append(item);
  });
  const legend = document.createElement('div');
  legend.className = 'chart-legend';
  legend.innerHTML = '<span><i class="legend-swatch sales-swatch"></i>Actual sales</span><span><i class="legend-swatch target-swatch"></i>Target</span>';
  chart.append(legend);
}

function dailyBuckets(month) {
  const [year, monthNumber] = month.split('-').map(Number);
  const dayCount = new Date(year, monthNumber, 0).getDate();
  const staff = getActiveStaff();
  return Array.from({ length: dayCount }, (_, index) => {
    const date = `${month}-${String(index + 1).padStart(2, '0')}`;
    return {
      label: String(index + 1),
      sales: staff.reduce((total, person) => total + state.sales
        .filter((sale) => sale.staffId === person.id && sale.date === date && sale.paymentStatus !== 'Refunded')
        .reduce((sum, sale) => sum + sale.amount, 0), 0),
      target: staff.reduce((total, person) => total + getTarget(person.id, month), 0) / dayCount
    };
  });
}

function weeklyBuckets(month) {
  const [year, monthNumber] = month.split('-').map(Number);
  const dayCount = new Date(year, monthNumber, 0).getDate();
  const staff = getActiveStaff();
  const buckets = [];
  for (let firstDay = 1; firstDay <= dayCount; firstDay += 7) {
    const lastDay = Math.min(firstDay + 6, dayCount);
    const start = `${month}-${String(firstDay).padStart(2, '0')}`;
    const end = `${month}-${String(lastDay).padStart(2, '0')}`;
    buckets.push({
      label: `W${buckets.length + 1}`,
      sales: staff.reduce((total, person) => total + state.sales
        .filter((sale) => sale.staffId === person.id && sale.date >= start && sale.date <= end && sale.paymentStatus !== 'Refunded')
        .reduce((sum, sale) => sum + sale.amount, 0), 0),
      target: (staff.reduce((total, person) => total + getTarget(person.id, month), 0) * (lastDay - firstDay + 1)) / dayCount
    });
  }
  return buckets;
}

function monthlyBuckets(month) {
  const [year, monthNumber] = month.split('-').map(Number);
  const staff = getActiveStaff();
  return Array.from({ length: 6 }, (_, index) => {
    const date = new Date(year, monthNumber - 1 - (5 - index), 1);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    return {
      label: date.toLocaleString('en-IN', { month: 'short' }),
      sales: staff.reduce((total, person) => total + getSalesTotal(person.id, key), 0),
      target: staff.reduce((total, person) => total + getTarget(person.id, key), 0)
    };
  });
}

function renderReport() {
  const month = getSelectedMonth();
  const active = getActiveStaff();
  const target = active.reduce((total, person) => total + getTarget(person.id, month), 0);
  const sales = active.reduce((total, person) => total + getSalesTotal(person.id, month), 0);
  const lines = [
    `MINISO STAFF PERFORMANCE REPORT — ${month}`,
    '================================================',
    `Team sales: ${formatCurrency(sales)}`,
    `Monthly target: ${formatCurrency(target)}`,
    `Achievement: ${getAchievement(sales, target).toFixed(1)}%`,
    `Incentives: ${formatCurrency(active.reduce((total, person) => total + getPerformance(person).incentive, 0))}`,
    '',
    'STAFF PERFORMANCE'
  ];
  active.forEach((person) => {
    const result = getPerformance(person);
    lines.push(`${person.id} | ${person.name} | Target ${formatCurrency(result.target)} | Sales ${formatCurrency(result.sales)} | ${result.achievement.toFixed(1)}% | Incentive ${formatCurrency(result.incentive)}`);
  });
  $('reportOutput').value = lines.join('\n');
}

function renderStaffOptions() {
  const activeStaff = getActiveStaff();
  populateStaffSelect($('salesStaffId'), activeStaff, 'No active staff — add staff first');
  populateStaffSelect($('targetStaffId'), state.staff, 'Add staff first');
  updateSalesStaffName();
  updateTargetStaffName();
  $('saleIdPreview').value = generateSaleId();
}

function populateStaffSelect(select, people, emptyText) {
  const previous = select.value;
  select.replaceChildren();
  if (!people.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = emptyText;
    select.append(option);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  people.forEach((person) => {
    const option = document.createElement('option');
    option.value = person.id;
    option.textContent = `${person.id} — ${person.name}`;
    select.append(option);
  });
  if (people.some((person) => person.id === previous)) select.value = previous;
}

function updateSalesStaffName() {
  const person = state.staff.find((item) => item.id === $('salesStaffId').value);
  $('salesStaffName').value = person ? person.name : '';
}

function updateTargetStaffName() {
  const person = state.staff.find((item) => item.id === $('targetStaffId').value);
  $('targetStaffName').value = person ? person.name : '';
  const existing = state.targets.find((target) => target.staffId === $('targetStaffId').value
    && target.month === $('targetMonth').value);
  $('targetAmount').value = existing ? existing.amount : '';
}

function populateRuleFields() {
  state.rules.forEach((rule, index) => {
    $(`tier${index + 1}Threshold`).value = rule.threshold;
    $(`tier${index + 1}Reward`).value = rule.reward;
  });
}

function upsertTarget(staffId, month, amount) {
  const existing = state.targets.find((target) => target.staffId === staffId && target.month === month);
  if (existing) existing.amount = amount;
  else state.targets.push({ staffId, month, amount });
}

function generateStaffId() {
  const maxId = state.staff.reduce((max, person) => {
    const match = /^S(\d+)$/.exec(person.id);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);
  return `S${String(maxId + 1).padStart(3, '0')}`;
}

function generateSaleId() {
  const maxId = state.sales.reduce((max, sale) => {
    const match = /^SALE(\d+)$/.exec(sale.id);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);
  return `SALE${String(maxId + 1).padStart(3, '0')}`;
}

function createProgress(achievement) {
  const progress = document.createElement('progress');
  progress.max = 100;
  progress.value = Math.min(100, Math.max(0, achievement));
  progress.setAttribute('aria-label', `${achievement.toFixed(1)} percent achieved`);
  return progress;
}

function getStatusLabel(achievement) {
  if (achievement >= 100) return 'On Track';
  if (achievement >= 80) return 'Needs Attention';
  return 'Behind Target';
}

function getStatusClass(achievement) {
  if (achievement >= 100) return 'status-good';
  if (achievement >= 80) return 'status-warning';
  return 'status-danger';
}

function appendCell(row, text) {
  const cell = document.createElement('td');
  cell.textContent = text;
  row.append(cell);
  return cell;
}

function appendMessageRow(body, columnCount, message) {
  const row = document.createElement('tr');
  const cell = appendCell(row, message);
  cell.colSpan = columnCount;
  cell.classList.add('empty-cell');
  body.append(row);
}

function formatCurrency(amount) {
  return currencyFormatter.format(Number.isFinite(amount) ? amount : 0);
}

function formatCompactCurrency(amount) {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
  return `₹${Math.round(amount)}`;
}

function formatDate(value) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function updateCurrentDateTime() {
  $('currentDateTime').textContent = new Date().toLocaleString('en-IN', { dateStyle: 'full', timeStyle: 'medium' });
}

function persistState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function exportMonthlyCsv() {
  const month = getSelectedMonth();
  const headings = ['Sale ID', 'Date', 'Staff ID', 'Staff Name', 'Product', 'Quantity', 'Amount', 'Payment Status'];
  const rows = state.sales
    .filter((sale) => sale.date.slice(0, 7) === month)
    .map((sale) => {
      const person = state.staff.find((item) => item.id === sale.staffId);
      return [sale.id, sale.date, sale.staffId, person ? person.name : '', sale.product, sale.quantity, sale.amount, sale.paymentStatus];
    });
  const csv = [headings, ...rows].map((row) => row.map(escapeCsv).join(',')).join('\r\n');
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `miniso-sales-${month}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function escapeCsv(value) {
  const text = String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function resetData() {
  if (!window.confirm('Reset all saved dashboard data to the demo data?')) return;
  state = createInitialState();
  persistState();
  populateRuleFields();
  $('targetMonth').value = currentMonth();
  renderStaffOptions();
  renderDashboard();
}
