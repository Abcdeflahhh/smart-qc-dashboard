/* ============================================================
   Smart QC Dashboard - Frontend Application
   ============================================================ */

// ============================================================
// Configuration & State
// ============================================================
const API_BASE = '/api';
const state = {
  data: [],
  anomalies: new Set(),
  filteredData: [],
  currentPage: 1,
  pageSize: 25,
  statusFilter: 'all',
  searchQuery: '',
  trendChart: null,
  defectChart: null,
  isLoading: false
};

// ============================================================
// DOM Elements Cache
// ============================================================
const els = {};

// Initialize element references
function cacheElements() {
  // KPI
  els.kpiTotal = document.getElementById('kpiTotal');
  els.kpiTotalChange = document.getElementById('kpiTotalChange');
  els.kpiPassRate = document.getElementById('kpiPassRate');
  els.kpiPassCount = document.getElementById('kpiPassCount');
  els.kpiDefectRate = document.getElementById('kpiDefectRate');
  els.kpiRejectCount = document.getElementById('kpiRejectCount');
  els.kpiOEE = document.getElementById('kpiOEE');
  els.kpiOEEBreakdown = document.getElementById('kpiOEEBreakdown');

  // Charts
  els.trendChartCtx = document.getElementById('trendChart');
  els.defectChartCtx = document.getElementById('defectChart');
  els.defectLegend = document.getElementById('defectLegend');
  els.trendFreq = document.getElementById('trendFreq');

  // Table
  els.tableBody = document.getElementById('tableBody');
  els.tableInfo = document.getElementById('tableInfo');
  els.statusFilter = document.getElementById('statusFilter');
  els.searchInput = document.getElementById('searchInput');
  els.prevPage = document.getElementById('prevPage');
  els.nextPage = document.getElementById('nextPage');
  els.paginationInfo = document.getElementById('paginationInfo');

  // Buttons
  els.uploadBtn = document.getElementById('uploadBtn');
  els.fileInput = document.getElementById('fileInput');
  els.downloadBtn = document.getElementById('downloadBtn');
  els.printBtn = document.getElementById('printBtn');

  // Modals
  els.uploadModal = document.getElementById('uploadModal');
  els.modalFileInput = document.getElementById('modalFileInput');
  els.uploadPreview = document.getElementById('uploadPreview');
  els.previewContent = document.getElementById('previewContent');
  els.cancelUpload = document.getElementById('cancelUpload');
  els.confirmUpload = document.getElementById('confirmUpload');

  els.printModal = document.getElementById('printModal');
  els.printContent = document.getElementById('printContent');
  els.closePrintModal = document.getElementById('closePrintModal');
  els.closePrintBtn = document.getElementById('closePrintBtn');
  els.doPrintBtn = document.getElementById('doPrintBtn');

  // Theme
  els.themeToggle = document.getElementById('themeToggle');
  els.sunIcon = document.getElementById('sunIcon');
  els.moonIcon = document.getElementById('moonIcon');

  // Connection
  els.connectionIndicator = document.getElementById('connectionIndicator');
  els.connectionStatus = document.getElementById('connectionStatus');
}

// ============================================================
// Utility Functions
// ============================================================
function formatNumber(num) {
  return new Intl.NumberFormat('id-ID').format(num);
}

function formatDateTime(isoString) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('id-ID', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(date);
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('id-ID', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(date);
}

function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

function showToast(title, message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <svg class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
      ${type === 'success' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />' : ''}
      ${type === 'error' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 3h.01M12 3a9 9 0 100 18 9 9 0 000-18z" />' : ''}
      ${type === 'warning' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 3h.01M12 3a9 9 0 100 18 9 9 0 000-18z" />' : ''}
      ${type === 'info' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />' : ''}
    </svg>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" aria-label="Close">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  `;

  toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
  container.appendChild(toast);

  setTimeout(() => toast.remove(), 5000);
}

function setLoading(loading) {
  state.isLoading = loading;
  els.uploadBtn.disabled = loading;
  els.downloadBtn.disabled = loading;
  els.printBtn.disabled = loading;
  if (loading) {
    els.uploadBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Memuat...
    `;
  } else {
    els.uploadBtn.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      <span>Upload CSV</span>
    `;
  }
}

// ============================================================
// API Functions
// ============================================================
async function apiGet(endpoint, params = {}) {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiPost(endpoint, body) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiUploadFile(endpoint, file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiDownloadFile(endpoint, params = {}) {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition');
  let filename = 'report.csv';
  if (disposition) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match) filename = match[1];
  }
  const url_ = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url_;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url_);
}

// ============================================================
// Data Loading
// ============================================================
async function loadSummary() {
  try {
    const data = await apiGet('/summary');
    els.kpiTotal.textContent = formatNumber(data.total_inspections);
    els.kpiTotalChange.textContent = `${data.unique_batches} batch • ${data.unique_lines} line`;
    els.kpiPassRate.textContent = `${data.pass_rate_pct.toFixed(1)}%`;
    els.kpiPassCount.textContent = `${formatNumber(data.pass_count)} unit lolos`;
    els.kpiDefectRate.textContent = `${data.defect_rate_pct.toFixed(1)}%`;
    els.kpiRejectCount.textContent = `${formatNumber(data.reject_count)} unit cacat`;
    els.kpiOEE.textContent = `${data.oee_score.toFixed(2)}%`;
    els.kpiOEEBreakdown.textContent = `A: ${data.availability_pct.toFixed(1)}% | P: ${data.performance_pct.toFixed(1)}% | Q: ${data.quality_pct.toFixed(1)}%`;
  } catch (e) {
    console.error('Failed to load summary:', e);
    showToast('Error', 'Gagal memuat ringkasan KPI', 'error');
  }
}

async function loadAnomalies() {
  try {
    const data = await apiGet('/anomalies', { limit: 1000 });
    state.anomalies.clear();
    data.anomalies.forEach(a => {
      if (a.is_anomaly) state.anomalies.add(a.index);
    });
    return data;
  } catch (e) {
    console.error('Failed to load anomalies:', e);
    return { anomalies: [], summary: {} };
  }
}

async function loadTrends(freq = 'h') {
  try {
    return await apiGet('/trends', { freq });
  } catch (e) {
    console.error('Failed to load trends:', e);
    showToast('Error', 'Gagal memuat data tren', 'error');
    return { data: [], freq };
  }
}

async function loadAllData() {
  setLoading(true);
  try {
    // Load all in parallel
    const [summary, anomalies, trends] = await Promise.all([
      apiGet('/summary'),
      apiGet('/anomalies', { limit: 1000 }),
      apiGet('/trends', { freq: 'h' })
    ]);

    // Process anomalies
    state.anomalies.clear();
    anomalies.anomalies.forEach(a => {
      if (a.is_anomaly) state.anomalies.add(a.index);
    });

    // We need full inspection data for table - fetch via anomalies endpoint with all rows
    const allData = await apiGet('/anomalies', { limit: 1000, only_anomalies: false });
    state.data = allData.anomalies.map((a, idx) => ({
      ...a,
      // Add computed fields
      isAnomaly: a.is_anomaly,
      anomalyReasons: a.anomaly_reasons || []
    }));

    applyFilters();
    renderTrendChart(trends);
    renderDefectChart(state.data);
    updateConnectionStatus(true);

    showToast('Berhasil', 'Data dimuat dari server', 'success');
  } catch (e) {
    console.error('Failed to load data:', e);
    showToast('Error', 'Gagal memuat data dari server', 'error');
    updateConnectionStatus(false);
  } finally {
    setLoading(false);
  }
}

// ============================================================
// Chart Rendering
// ============================================================
function renderTrendChart(trendsData) {
  const ctx = els.trendChartCtx.getContext('2d');

  if (state.trendChart) state.trendChart.destroy();

  const labels = trendsData.data.map(d => {
    const date = new Date(d.timestamp);
    return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  });

  state.trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Pass Rate (%)',
          data: trendsData.data.map(d => d.pass_rate_pct),
          borderColor: '#14b8a6',
          backgroundColor: 'rgba(20, 184, 166, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#14b8a6',
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        },
        {
          label: 'Defect Rate (%)',
          data: trendsData.data.map(d => d.defect_rate_pct),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#ef4444',
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f9fafb',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          displayColors: true,
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 12, color: '#6b7280', font: { size: 11 } }
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(209, 213, 219, 0.3)' },
          ticks: { color: '#6b7280', font: { size: 11 }, callback: v => `${v}%` }
        }
      }
    }
  });
}

function renderDefectChart(data) {
  const ctx = els.defectChartCtx.getContext('2d');
  const legendContainer = els.defectLegend;

  // Count defect types
  const defectCounts = {};
  data.forEach(row => {
    if (row.defect_type && row.defect_type !== 'NONE') {
      defectCounts[row.defect_type] = (defectCounts[row.defect_type] || 0) + 1;
    }
  });

  // Sort by count descending
  const sortedEntries = Object.entries(defectCounts).sort((a, b) => b[1] - a[1]);
  const labels = sortedEntries.map(e => e[0]);
  const values = sortedEntries.map(e => e[1]);

  // Colors for each defect type
  const colors = [
    '#ef4444', '#f97316', '#f59e0b', '#eab308',
    '#84cc16', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6'
  ];

  if (state.defectChart) state.defectChart.destroy();

  state.defectChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f9fafb',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: ctx => `${ctx.label}: ${ctx.parsed} (${((ctx.parsed / values.reduce((a,b)=>a+b,0))*100).toFixed(1)}%)`
          }
        }
      }
    }
  });

  // Custom legend
  const total = values.reduce((a, b) => a + b, 0);
  legendContainer.innerHTML = labels.map((label, i) => `
    <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
      <span class="w-3 h-3 rounded-full" style="background: ${colors[i]}"></span>
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">${label.toLowerCase()}</span>
      <span class="text-sm text-gray-500 dark:text-gray-400 ml-auto">${values[i]} (${total > 0 ? ((values[i]/total)*100).toFixed(1) : 0}%)</span>
    </div>
  `).join('');
}

// ============================================================
// Table Rendering & Filtering
// ============================================================
function applyFilters() {
  let filtered = [...state.data];

  // Status filter
  if (state.statusFilter === 'PASS') {
    filtered = filtered.filter(r => r.status === 'PASS');
  } else if (state.statusFilter === 'REJECT') {
    filtered = filtered.filter(r => r.status === 'REJECT');
  } else if (state.statusFilter === 'ANOMALY') {
    filtered = filtered.filter(r => r.isAnomaly);
  }

  // Search filter
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(r =>
      (r.batch_id && r.batch_id.toLowerCase().includes(q)) ||
      (r.line_id && r.line_id.toLowerCase().includes(q)) ||
      (r.defect_type && r.defect_type.toLowerCase().includes(q)) ||
      (r.timestamp && r.timestamp.toLowerCase().includes(q))
    );
  }

  state.filteredData = filtered;
  state.currentPage = 1;
  renderTable();
  renderPagination();
}

function renderTable() {
  const start = (state.currentPage - 1) * state.pageSize;
  const end = start + state.pageSize;
  const pageData = state.filteredData.slice(start, end);

  if (pageData.length === 0) {
    els.tableBody.innerHTML = `
      <tr>
        <td colspan="9" class="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>Tidak ada data yang cocok</p>
        </td>
      </tr>
    `;
    els.tableInfo.textContent = `Menampilkan 0 dari ${state.filteredData.length} baris`;
    return;
  }

  els.tableBody.innerHTML = pageData.map((row, idx) => {
    const globalIdx = start + idx;
    const isAnomaly = state.anomalies.has(row.index);
    const isReject = row.status === 'REJECT';
    const rowClass = isAnomaly ? 'anomaly-row' : (isReject ? 'reject-row' : '');

    return `
      <tr class="${rowClass}" data-index="${row.index}">
        <td class="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white whitespace-nowrap">${formatDateTime(row.timestamp)}</td>
        <td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">${row.batch_id}</td>
        <td class="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
          <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">${row.line_id}</span>
        </td>
        <td class="px-4 py-3 text-sm text-right font-mono ${row.temperature_c > 240 || row.temperature_c < 200 ? 'text-danger-600 dark:text-danger-400 font-semibold' : 'text-gray-900 dark:text-white'}">${row.temperature_c?.toFixed(1) ?? '—'}</td>
        <td class="px-4 py-3 text-sm text-right font-mono ${row.pressure_bar > 100 || row.pressure_bar < 70 ? 'text-danger-600 dark:text-danger-400 font-semibold' : 'text-gray-900 dark:text-white'}">${row.pressure_bar?.toFixed(1) ?? '—'}</td>
        <td class="px-4 py-3 text-sm text-right font-mono ${row.dimension_mm > 50.3 || row.dimension_mm < 49.7 ? 'text-danger-600 dark:text-danger-400 font-semibold' : 'text-gray-900 dark:text-white'}">${row.dimension_mm?.toFixed(3) ?? '—'}</td>
        <td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
          ${row.defect_type && row.defect_type !== 'NONE'
            ? `<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-300">${row.defect_type}</span>`
            : '<span class="text-gray-400 dark:text-gray-500 italic">—</span>'}
        </td>
        <td class="px-4 py-3 text-center">
          <span class="status-badge ${row.status === 'PASS' ? 'status-pass' : 'status-reject'}">${row.status}</span>
        </td>
        <td class="px-4 py-3 text-center">
          <span class="anomaly-indicator ${isAnomaly ? 'anomaly-yes' : 'anomaly-no'}" title="${isAnomaly ? (row.anomalyReasons?.join('; ') || 'Terdeteksi anomali') : 'Normal'}">
            ${isAnomaly ? '!' : '✓'}
          </span>
        </td>
      </tr>
    `;
  }).join('');

  els.tableInfo.textContent = `Menampilkan ${start + 1}–${Math.min(end, state.filteredData.length)} dari ${state.filteredData.length} baris`;
}

function renderPagination() {
  const totalPages = Math.ceil(state.filteredData.length / state.pageSize);
  els.paginationInfo.textContent = `Halaman ${state.currentPage} dari ${totalPages || 1}`;
  els.prevPage.disabled = state.currentPage <= 1;
  els.nextPage.disabled = state.currentPage >= totalPages;
}

function goToPage(page) {
  const totalPages = Math.ceil(state.filteredData.length / state.pageSize);
  if (page < 1 || page > totalPages) return;
  state.currentPage = page;
  renderTable();
  renderPagination();
}

// ============================================================
// Upload CSV
// ============================================================
let pendingUploadFile = null;

function openUploadModal() {
  els.uploadModal.classList.remove('hidden');
  els.modalFileInput.value = '';
  els.uploadPreview.classList.add('hidden');
  els.confirmUpload.disabled = true;
  pendingUploadFile = null;
  els.modalFileInput.focus();
}

function closeUploadModal() {
  els.uploadModal.classList.add('hidden');
  pendingUploadFile = null;
}

function handleFileSelect(file) {
  if (!file || !file.name.endsWith('.csv')) {
    showToast('Error', 'File harus berformat CSV', 'error');
    return;
  }

  pendingUploadFile = file;
  els.uploadPreview.classList.remove('hidden');
  els.confirmUpload.disabled = false;

  // Show preview
  const reader = new FileReader();
  reader.onload = e => {
    const text = e.target.result;
    const lines = text.split('\n').slice(0, 6); // header + 5 rows
    els.previewContent.textContent = lines.join('\n');
  };
  reader.readAsText(file);
}

async function confirmUpload() {
  if (!pendingUploadFile) return;

  closeUploadModal();
  setLoading(true);

  try {
    const result = await apiUploadFile('/upload-csv', pendingUploadFile);
    showToast('Berhasil', `${result.message} (${result.rows} baris)`, 'success');
    await loadAllData(); // Reload all data
  } catch (e) {
    console.error('Upload failed:', e);
    showToast('Error', `Gagal upload: ${e.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

// ============================================================
// Download Report
// ============================================================
async function downloadReport() {
  try {
    els.downloadBtn.disabled = true;
    els.downloadBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Menyiapkan...
    `;
    await apiDownloadFile('/export-csv', { format: 'csv', include_anomalies: true, include_trends: true });
    showToast('Berhasil', 'Laporan CSV diunduh', 'success');
  } catch (e) {
    console.error('Download failed:', e);
    showToast('Error', `Gagal unduh laporan: ${e.message}`, 'error');
  } finally {
    els.downloadBtn.disabled = false;
    els.downloadBtn.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
      <span>Download Laporan</span>
    `;
  }
}

// ============================================================
// Print Report
// ============================================================
function generatePrintReport() {
  const summary = {
    total: state.data.length,
    pass: state.data.filter(r => r.status === 'PASS').length,
    reject: state.data.filter(r => r.status === 'REJECT').length,
    passRate: state.data.length ? (state.data.filter(r => r.status === 'PASS').length / state.data.length * 100).toFixed(1) : 0,
    defectRate: state.data.length ? (state.data.filter(r => r.status === 'REJECT').length / state.data.length * 100).toFixed(1) : 0,
    anomalies: state.anomalies.size,
    batches: [...new Set(state.data.map(r => r.batch_id))].length,
    lines: [...new Set(state.data.map(r => r.line_id))].length,
    dateRange: state.data.length ? {
      start: formatDate(state.data[0].timestamp),
      end: formatDate(state.data[state.data.length - 1].timestamp)
    } : { start: '—', end: '—' }
  };

  // Defect type breakdown
  const defectCounts = {};
  state.data.forEach(r => {
    if (r.defect_type && r.defect_type !== 'NONE') {
      defectCounts[r.defect_type] = (defectCounts[r.defect_type] || 0) + 1;
    }
  });

  // Anomaly details
  const anomalyRows = state.data.filter(r => state.anomalies.has(r.index));

  let html = `
    <div class="print-report">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1>Laporan Inspeksi Quality Control</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Generated: ${new Date().toLocaleString('id-ID')}</p>
        </div>
        <div class="w-20 h-20 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
      </div>

      <h2>Ringkasan Eksekutif</h2>
      <div class="meta-grid">
        <div class="meta-item"><div class="meta-label">Total Inspeksi</div><div class="meta-value">${formatNumber(summary.total)}</div></div>
        <div class="meta-item"><div class="meta-label">Lolos (PASS)</div><div class="meta-value">${formatNumber(summary.pass)} (${summary.passRate}%)</div></div>
        <div class="meta-item"><div class="meta-label">Cacat (REJECT)</div><div class="meta-value">${formatNumber(summary.reject)} (${summary.defectRate}%)</div></div>
        <div class="meta-item"><div class="meta-label">Anomali Terdeteksi</div><div class="meta-value">${summary.anomalies}</div></div>
        <div class="meta-item"><div class="meta-label">Batch Unik</div><div class="meta-value">${summary.batches}</div></div>
        <div class="meta-item"><div class="meta-label">Line Produksi</div><div class="meta-value">${summary.lines}</div></div>
        <div class="meta-item"><div class="meta-label">Periode Data</div><div class="meta-value">${summary.dateRange.start} – ${summary.dateRange.end}</div></div>
      </div>

      <h2>Distribusi Jenis Cacat</h2>
      <table>
        <thead><tr><th>Jenis Cacat</th><th>Jumlah</th><th>Persentase</th></tr></thead>
        <tbody>
          ${Object.entries(defectCounts).sort((a,b)=>b[1]-a[1]).map(([type, count]) => `
            <tr><td>${type}</td><td>${formatNumber(count)}</td><td>${((count/summary.reject)*100).toFixed(1)}%</td></tr>
          `).join('') || '<tr><td colspan="3" class="text-center py-4">Tidak ada cacat</td></tr>'}
        </tbody>
      </table>

      <h2>Anomali Terdeteksi (${anomalyRows.length})</h2>
      ${anomalyRows.length > 0 ? `
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Batch</th><th>Line</th><th>Parameter</th><th>Alasan</th></tr>
          </thead>
          <tbody>
            ${anomalyRows.map(r => `
              <tr class="anomaly-row">
                <td>${formatDateTime(r.timestamp)}</td>
                <td>${r.batch_id}</td>
                <td>${r.line_id}</td>
                <td>${(r.anomaly_params || []).join(', ')}</td>
                <td class="max-w-xs truncate">${(r.anomalyReasons || []).join('; ')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      ` : '<p class="text-gray-500 dark:text-gray-400 italic">Tidak ada anomali terdeteksi</p>'}

      <h2>Data Inspeksi Terbaru (100 baris pertama)</h2>
      <table>
        <thead>
          <tr><th>Timestamp</th><th>Batch</th><th>Line</th><th>Temp (°C)</th><th>Pressure (bar)</th><th>Dim (mm)</th><th>Defect</th><th>Status</th><th>Anomali</th></tr>
        </thead>
        <tbody>
          ${state.data.slice(0, 100).map(r => {
            const isAnomaly = state.anomalies.has(r.index);
            const isReject = r.status === 'REJECT';
            const rowClass = isAnomaly ? 'anomaly-row' : (isReject ? 'reject-row' : '');
            return `
              <tr class="${rowClass}">
                <td>${formatDateTime(r.timestamp)}</td>
                <td>${r.batch_id}</td>
                <td>${r.line_id}</td>
                <td>${r.temperature_c?.toFixed(1) ?? '—'}</td>
                <td>${r.pressure_bar?.toFixed(1) ?? '—'}</td>
                <td>${r.dimension_mm?.toFixed(3) ?? '—'}</td>
                <td>${r.defect_type && r.defect_type !== 'NONE' ? r.defect_type : '—'}</td>
                <td>${r.status}</td>
                <td>${isAnomaly ? 'YA' : 'TIDAK'}</td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>

      <div class="footer-note">
        Smart QC Dashboard — Laporan otomatis. Data bersumber dari sistem inspeksi produksi.
      </div>
    </div>
  `;

  return html;
}

function openPrintModal() {
  els.printContent.innerHTML = generatePrintReport();
  els.printModal.classList.remove('hidden');
}

function closePrintModal() {
  els.printModal.classList.add('hidden');
}

function doPrint() {
  window.print();
}

// ============================================================
// Theme Toggle
// ============================================================
function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  if (saved === 'dark') document.documentElement.classList.add('dark');
  updateThemeIcons();
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons();
}

function updateThemeIcons() {
  const isDark = document.documentElement.classList.contains('dark');
  els.sunIcon.classList.toggle('hidden', !isDark);
  els.sunIcon.classList.toggle('block', isDark);
  els.moonIcon.classList.toggle('hidden', isDark);
  els.moonIcon.classList.toggle('block', !isDark);
}

// ============================================================
// Connection Status
// ============================================================
function updateConnectionStatus(connected) {
  els.connectionIndicator.classList.toggle('connected', connected);
  els.connectionStatus.textContent = connected ? 'Connected' : 'Disconnected';
  els.connectionStatus.className = `text-sm font-medium ${connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`;
}

// ============================================================
// Event Listeners
// ============================================================
function bindEvents() {
  // Theme
  els.themeToggle.addEventListener('click', toggleTheme);

  // Filters
  els.statusFilter.addEventListener('change', e => {
    state.statusFilter = e.target.value;
    applyFilters();
  });

  els.searchInput.addEventListener('input', debounce(e => {
    state.searchQuery = e.target.value.trim();
    applyFilters();
  }, 300));

  // Pagination
  els.prevPage.addEventListener('click', () => goToPage(state.currentPage - 1));
  els.nextPage.addEventListener('click', () => goToPage(state.currentPage + 1));

  // Trend frequency
  els.trendFreq.addEventListener('change', async e => {
    const data = await loadTrends(e.target.value);
    renderTrendChart(data);
  });

  // Upload
  els.uploadBtn.addEventListener('click', openUploadModal);
  els.fileInput.addEventListener('change', e => {
    if (e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
      openUploadModal();
    }
  });
  els.modalFileInput.addEventListener('change', e => {
    if (e.target.files[0]) handleFileSelect(e.target.files[0]);
  });
  els.cancelUpload.addEventListener('click', closeUploadModal);
  els.confirmUpload.addEventListener('click', confirmUpload);

  // Download
  els.downloadBtn.addEventListener('click', downloadReport);

  // Print
  els.printBtn.addEventListener('click', openPrintModal);
  els.closePrintModal.addEventListener('click', closePrintModal);
  els.closePrintBtn.addEventListener('click', closePrintModal);
  els.doPrintBtn.addEventListener('click', doPrint);

  // Modal backdrop clicks
  els.uploadModal.addEventListener('click', e => {
    if (e.target === els.uploadModal) closeUploadModal();
  });
  els.printModal.addEventListener('click', e => {
    if (e.target === els.printModal) closePrintModal();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeUploadModal();
      closePrintModal();
    }
    if (e.key === 'u' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      openUploadModal();
    }
    if (e.key === 'p' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      openPrintModal();
    }
  });
}

// ============================================================
// Initialize
// ============================================================
async function init() {
  cacheElements();
  initTheme();
  bindEvents();
  await loadAllData();
}

// Start when DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for debugging
window.QCDashboard = { state, loadAllData, showToast };