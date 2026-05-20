// ============================================================
// MTA Pipeline — Dashboard Logic
// ============================================================

// --- Chart instances ---
let barChart = null;
let pieChart = null;
let comparisonChart = null;

// --- DOM refs ---
const modelSelector    = document.getElementById('model-selector');
const kpiSpend         = document.getElementById('kpi-total-spend');
const kpiRevenue       = document.getElementById('kpi-total-revenue');
const kpiRoas          = document.getElementById('kpi-overall-roas');
const kpiRoasStatus    = document.getElementById('kpi-roas-status');
const kpiConv          = document.getElementById('kpi-total-conv');
const optimizerBody    = document.getElementById('optimizer-table-body');
const avgRoasBadge     = document.getElementById('average-roas-badge');
const btnIngest        = document.getElementById('btn-ingest');
const btnRefresh       = document.getElementById('btn-refresh');
const loadingOverlay   = document.getElementById('loading-overlay');
const toastContainer   = document.getElementById('toast-container');
const barModelTag      = document.getElementById('bar-chart-model-tag');
const statusDot        = document.getElementById('status-dot');
const statusText       = document.getElementById('status-text');

// --- Model label map ---
const MODEL_LABELS = {
    markov:      'Markov',
    last_touch:  'Last Touch',
    first_touch: 'First Touch',
    linear:      'Linear',
};

// --- Channel color palette ---
const CHANNEL_COLORS = {
    'Google Ads':  { solid: '#0066ff', alpha: 'rgba(0, 102, 255, 0.65)' },
    'Meta Ads':    { solid: '#00aaff', alpha: 'rgba(0, 170, 255, 0.65)' },
    'TikTok Ads':  { solid: '#f43f5e', alpha: 'rgba(244, 63, 94, 0.65)' },
    'Email':       { solid: '#10b981', alpha: 'rgba(16, 185, 129, 0.65)' },
    'Organic':     { solid: '#64748b', alpha: 'rgba(100, 116, 139, 0.65)' },
};

const DEFAULT_COLOR = { solid: '#6b7280', alpha: 'rgba(107, 114, 128, 0.65)' };

function getChannelColor(ch) {
    return CHANNEL_COLORS[ch] || DEFAULT_COLOR;
}

// ============================================================
// Toast Notification System
// ============================================================
function showToast(message, type = 'info', duration = 4000) {
    const icons = { success: 'bxs-check-circle', error: 'bxs-x-circle', info: 'bx-info-circle' };
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `<i class="bx ${icons[type]}"></i><span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast--hide');
        toast.addEventListener('animationend', () => toast.remove());
    }, duration);
}

// ============================================================
// Pipeline Status Indicator
// ============================================================
function setStatus(state, message) {
    const classes = { idle: 'status-dot--idle', loading: 'status-dot--loading', success: 'status-dot--success', error: 'status-dot--error' };
    statusDot.className = `status-dot ${classes[state] || classes.idle}`;
    statusText.textContent = message;
}

// ============================================================
// Currency Formatter
// ============================================================
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}

function formatNumber(value) {
    return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value);
}

// ============================================================
// KPI Animated Counter
// ============================================================
function animateValue(element, start, end, formatter, duration = 700) {
    const startTime = performance.now();
    const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
        const current = start + (end - start) * eased;
        element.textContent = formatter(current);
        if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
}

// ============================================================
// KPI Cards entrance animation
// ============================================================
function animateKpiCards() {
    const cards = document.querySelectorAll('.kpi-card');
    cards.forEach((card, i) => {
        card.style.transitionDelay = `${i * 80}ms`;
        card.classList.add('visible');
    });
}

// ============================================================
// Update KPI Cards
// ============================================================
function updateKPIs(summary, totalConversions) {
    animateValue(kpiSpend, 0, summary.total_spend, formatCurrency);
    animateValue(kpiRevenue, 0, summary.total_revenue_attributed, formatCurrency);
    animateValue(kpiRoas, 0, summary.overall_roas, (v) => `${v.toFixed(2)}x`);
    animateValue(kpiConv, 0, totalConversions, (v) => formatNumber(Math.round(v)));

    // ROAS status badge
    if (summary.overall_roas >= 4.0) {
        kpiRoasStatus.className = 'trend-positive';
        kpiRoasStatus.innerHTML = `<i class='bx bxs-smile'></i> ROAS excelente`;
    } else if (summary.overall_roas >= 2.0) {
        kpiRoasStatus.className = 'trend-neutral';
        kpiRoasStatus.style.color = 'var(--color-warning)';
        kpiRoasStatus.innerHTML = `<i class='bx bxs-meh'></i> Retorno moderado`;
    } else {
        kpiRoasStatus.className = 'trend-negative';
        kpiRoasStatus.innerHTML = `<i class='bx bxs-sad'></i> ROAS abaixo da meta`;
    }
}

// ============================================================
// Shared Chart Defaults
// ============================================================
const CHART_DEFAULTS = {
    color: '#94a3b8',
    font: { family: 'Outfit', size: 12 },
};

function applyChartDefaults() {
    Chart.defaults.color = CHART_DEFAULTS.color;
    Chart.defaults.font.family = CHART_DEFAULTS.font.family;
}

// ============================================================
// Bar Chart — Revenue vs Spend
// ============================================================
function renderBarChart(data) {
    if (barChart) barChart.destroy();

    const channels = data.map(d => d.channel);
    const revenues = data.map(d => d.revenue_attributed);
    const spends   = data.map(d => d.spend);
    const solidColors = channels.map(ch => getChannelColor(ch).solid);
    const alphaColors = channels.map(ch => getChannelColor(ch).alpha);

    const ctx = document.getElementById('chart-attribution-bars').getContext('2d');
    barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: channels,
            datasets: [
                {
                    label: 'Investimento de Mídia',
                    data: spends,
                    backgroundColor: 'rgba(255,255,255,0.06)',
                    borderColor: 'rgba(255,255,255,0.18)',
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Receita Atribuída',
                    data: revenues,
                    backgroundColor: alphaColors,
                    borderColor: solidColors,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 600, easing: 'easeOutQuart' },
            plugins: {
                legend: {
                    labels: { padding: 20, boxWidth: 12, boxHeight: 12 },
                },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#64748b' },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#64748b',
                        callback: v => `R$ ${(v / 1000).toFixed(0)}k`,
                    },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ============================================================
// Pie/Doughnut Chart — Revenue Mix
// ============================================================
function renderPieChart(data) {
    if (pieChart) pieChart.destroy();

    const channels = data.map(d => d.channel);
    const revenues = data.map(d => d.revenue_attributed);
    const solidColors = channels.map(ch => getChannelColor(ch).solid);

    const ctx = document.getElementById('chart-attribution-pie').getContext('2d');
    pieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: channels,
            datasets: [{
                data: revenues,
                backgroundColor: solidColors,
                borderColor: '#070b12',
                borderWidth: 3,
                hoverOffset: 10,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            animation: { duration: 700, easing: 'easeOutQuart' },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, boxWidth: 11, boxHeight: 11, font: { size: 11 } },
                },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((ctx.parsed / total) * 100).toFixed(1);
                            return `${ctx.label}: ${formatCurrency(ctx.parsed)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

// ============================================================
// Model Comparison Chart (Radar / Grouped Bar)
// ============================================================
async function renderComparisonChart() {
    const models = ['markov', 'last_touch', 'first_touch', 'linear'];
    const modelColors = {
        markov:      { solid: '#00d2ff', alpha: 'rgba(0, 210, 255, 0.65)' },
        last_touch:  { solid: '#10b981', alpha: 'rgba(16, 185, 129, 0.65)' },
        first_touch: { solid: '#f59e0b', alpha: 'rgba(245, 158, 11, 0.65)' },
        linear:      { solid: '#3b82f6', alpha: 'rgba(59, 130, 246, 0.65)' },
    };

    try {
        const results = await Promise.all(
            models.map(m => fetch(`/attribution?model=${m}`).then(r => r.json()))
        );

        // Extract channels from first result
        const channels = results[0].data?.map(d => d.channel) || [];
        if (!channels.length) return;

        const datasets = models.map((m, i) => {
            const roasValues = results[i].data?.map(d => d.roas) || [];
            const mc = modelColors[m];
            return {
                label: MODEL_LABELS[m],
                data: roasValues,
                backgroundColor: mc.alpha,
                borderColor: mc.solid,
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
            };
        });

        if (comparisonChart) comparisonChart.destroy();

        const ctx = document.getElementById('chart-model-comparison').getContext('2d');
        comparisonChart = new Chart(ctx, {
            type: 'bar',
            data: { labels: channels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 700, easing: 'easeOutQuart' },
                plugins: {
                    legend: {
                        labels: { padding: 20, boxWidth: 12, boxHeight: 12 },
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}x ROAS`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.03)' },
                        ticks: { color: '#64748b' },
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.04)' },
                        ticks: {
                            color: '#64748b',
                            callback: v => `${v.toFixed(1)}x`,
                        },
                        title: {
                            display: true,
                            text: 'ROAS por Modelo',
                            color: '#64748b',
                            font: { size: 11 },
                        },
                        beginAtZero: true,
                    },
                },
            },
        });
    } catch (e) {
        console.warn('Comparação de modelos indisponível:', e.message);
    }
}

// ============================================================
// Optimizer Table
// ============================================================
function updateOptimizerTable(optData) {
    avgRoasBadge.textContent = `ROAS Médio Pago: ${optData.average_paid_roas?.toFixed(2) ?? '—'}x`;
    optimizerBody.innerHTML = '';

    if (!optData.recommendations?.length) {
        optimizerBody.innerHTML = `
            <tr>
                <td colspan="7" class="loading-row">
                    <i class='bx bx-info-circle' style="font-size:1.5rem; display:block; margin-bottom:8px;"></i>
                    Sem dados de otimização disponíveis para este modelo.
                </td>
            </tr>`;
        return;
    }

    optData.recommendations.forEach((rec, i) => {
        const isUp      = rec.suggested_budget_change_pct > 0;
        const isDown    = rec.suggested_budget_change_pct < 0;
        const badgeClass = isUp ? 'badge-excellent' : isDown ? 'badge-low' : 'badge-neutral';
        const actionClass = isUp ? 'action-increase' : isDown ? 'action-decrease' : 'action-keep';
        const budgetClass = isUp ? 'budget-pill--up' : isDown ? 'budget-pill--down' : 'budget-pill--neutral';
        const budgetIcon  = isUp ? "bx-trending-up" : isDown ? "bx-trending-down" : "bx-minus";
        const budgetLabel = rec.suggested_budget_change_pct !== 0
            ? `${isUp ? '+' : ''}${rec.suggested_budget_change_pct}%`
            : 'Manter';

        const chColor = getChannelColor(rec.channel).solid;

        const tr = document.createElement('tr');
        tr.style.animationDelay = `${i * 60}ms`;
        tr.innerHTML = `
            <td>
                <span class="channel-pill">
                    <span class="channel-dot" style="background:${chColor};box-shadow:0 0 6px ${chColor}55;"></span>
                    ${rec.channel}
                </span>
            </td>
            <td>${formatCurrency(rec.current_spend)}</td>
            <td class="bold">${rec.roas.toFixed(2)}x</td>
            <td>
                <span class="status-badge ${badgeClass}">${rec.channel_status}</span>
            </td>
            <td class="${actionClass}">${rec.recommended_action}</td>
            <td>
                <span class="budget-pill ${budgetClass}">
                    <i class="bx ${budgetIcon}"></i> ${budgetLabel}
                </span>
            </td>
            <td style="color:var(--text-muted); font-size:0.82rem; max-width:300px; line-height:1.5;">
                ${rec.rationale}
            </td>`;
        optimizerBody.appendChild(tr);
    });
}

// ============================================================
// Main Data Loader
// ============================================================
async function loadDashboardData(showSpinner = false) {
    const model = modelSelector.value;
    const modelLabel = MODEL_LABELS[model] || model;

    if (barModelTag) barModelTag.textContent = modelLabel;
    setStatus('loading', 'Carregando dados...');

    // Mini-refresh spinner
    btnRefresh.classList.add('spinning');

    try {
        const [attRes, optRes] = await Promise.all([
            fetch(`/attribution?model=${model}`),
            fetch(`/optimize?model=${model}`),
        ]);

        if (!attRes.ok) throw new Error(`Atribuição: ${attRes.status}`);
        if (!optRes.ok) throw new Error(`Otimização: ${optRes.status}`);

        const attData = await attRes.json();
        const optData = await optRes.json();

        // Check for data
        if (!attData.data || attData.data.length === 0) {
            setStatus('error', 'Sem dados no banco');
            showToast('Nenhum dado encontrado. Execute a ingestão primeiro.', 'error');
            return;
        }

        // Total conversions across channels
        const totalConv = attData.data.reduce((sum, d) => sum + (d.conversions_attributed || 0), 0);

        updateKPIs(attData.overall_summary, totalConv);
        renderBarChart(attData.data);
        renderPieChart(attData.data);
        updateOptimizerTable(optData);

        setStatus('success', `Modelo: ${modelLabel}`);
        animateKpiCards();

    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
        setStatus('error', 'Falha na conexão');
        showToast(`Falha ao carregar dados: ${error.message}`, 'error');

        optimizerBody.innerHTML = `
            <tr>
                <td colspan="7" class="loading-row">
                    <i class='bx bxs-error-circle' style="font-size:1.75rem; color:var(--color-danger); display:block; margin-bottom:10px;"></i>
                    Servidor indisponível ou banco de dados não populado.<br>
                    <small style="color:var(--text-muted);">Certifique-se que o FastAPI está rodando e que os dados foram ingeridos.</small>
                </td>
            </tr>`;
    } finally {
        btnRefresh.classList.remove('spinning');
    }
}

// ============================================================
// Ingest Button
// ============================================================
btnIngest.addEventListener('click', async () => {
    if (!confirm('Isso irá gerar novos dados sintéticos (30 dias / 5.000 usuários) e reenviar ao Supabase. Confirmar?')) return;

    loadingOverlay.classList.remove('hidden');
    btnIngest.disabled = true;
    setStatus('loading', 'Ingerindo dados...');

    const icon = document.getElementById('ingest-icon');
    icon.classList.add('bx-spin');

    try {
        const res = await fetch('/ingest');
        const data = await res.json();

        if (data.status === 'success') {
            showToast('Pipeline executado com sucesso! Dados atualizados no Supabase.', 'success');
            await loadDashboardData();
            await renderComparisonChart();
        } else {
            showToast(`Erro no pipeline: ${data.detail}`, 'error');
            setStatus('error', 'Falha na ingestão');
        }
    } catch (e) {
        showToast(`Erro de rede: ${e.message}`, 'error');
        setStatus('error', 'Erro de rede');
    } finally {
        loadingOverlay.classList.add('hidden');
        btnIngest.disabled = false;
        icon.classList.remove('bx-spin');
    }
});

// ============================================================
// Refresh Button
// ============================================================
btnRefresh.addEventListener('click', () => loadDashboardData());

// ============================================================
// Model Selector Change
// ============================================================
modelSelector.addEventListener('change', () => loadDashboardData());

// ============================================================
// Sidebar Nav — smooth scroll highlight
// ============================================================
document.querySelectorAll('.sidebar-nav .nav-item[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        document.querySelectorAll('.sidebar-nav .nav-item').forEach(i => i.classList.remove('active'));
        link.classList.add('active');
    });
});

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
    applyChartDefaults();
    await loadDashboardData();
    await renderComparisonChart();
});
