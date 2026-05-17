/* ============================================================
   AI English Coach - Admin Dashboard JavaScript
   ============================================================ */

const API_BASE = '/api/v1';
let authToken = localStorage.getItem('admin_token') || '';
let currentPage = 1;
let searchTimeout = null;
let refreshInterval = null;
let chartInstances = {};

// ============================================================
// AUTH
// ============================================================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const btn = document.getElementById('loginBtn');
    const err = document.getElementById('loginError');

    btn.querySelector('.btn-text').style.display = 'none';
    btn.querySelector('.btn-loader').style.display = 'inline';
    err.style.display = 'none';

    try {
        const form = new URLSearchParams();
        form.append('username', email);
        form.append('password', password);

        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form.toString()
        });

        if (!res.ok) throw new Error('Email hoặc mật khẩu không đúng');
        const data = await res.json();
        authToken = data.access_token;
        localStorage.setItem('admin_token', authToken);

        // Verify admin
        const me = await apiFetch('/auth/me');
        if (!me.is_admin) {
            localStorage.removeItem('admin_token');
            throw new Error('Tài khoản không có quyền Admin');
        }
        document.getElementById('adminName').textContent = me.full_name || me.email;
        showDashboard();
    } catch (error) {
        err.textContent = error.message;
        err.style.display = 'block';
    } finally {
        btn.querySelector('.btn-text').style.display = 'inline';
        btn.querySelector('.btn-loader').style.display = 'none';
    }
    return false;
}

function handleLogout() {
    localStorage.removeItem('admin_token');
    authToken = '';
    if (refreshInterval) clearInterval(refreshInterval);
    document.getElementById('dashboardApp').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'flex';
}

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json', ...options.headers }
    });
    if (res.status === 401 || res.status === 403) { handleLogout(); throw new Error('Unauthorized'); }
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
}

// ============================================================
// DASHBOARD INIT
// ============================================================
function showDashboard() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('dashboardApp').style.display = 'flex';
    loadOverview();
    refreshInterval = setInterval(loadCurrentSection, 30000);
}

function loadCurrentSection() {
    const active = document.querySelector('.nav-item.active');
    if (active) switchSection(active.dataset.section, active, true);
}

// ============================================================
// NAVIGATION
// ============================================================
const sectionTitles = {
    'overview': 'Tổng quan', 'users': 'Quản lý Users', 'lessons': 'Lesson Analytics',
    'ai-usage': 'AI Usage Analytics', 'subscriptions': 'Subscription Analytics',
    'retention': 'Retention Analytics', 'speaking': 'Speaking Statistics'
};

function switchSection(name, el, silent) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    if (el) el.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const section = document.getElementById(`section-${name}`);
    if (section) section.classList.add('active');
    document.getElementById('sectionTitle').textContent = sectionTitles[name] || name;

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');

    const loaders = {
        'overview': loadOverview, 'users': loadUsers, 'lessons': loadLessons,
        'ai-usage': loadAIUsage, 'subscriptions': loadSubscriptions,
        'retention': loadRetention, 'speaking': loadSpeaking
    };
    if (loaders[name]) loaders[name]();
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function getDays() { return document.getElementById('dateRange').value; }
function onDateRangeChange() { loadCurrentSection(); }
function formatNum(n) { return n >= 1000 ? (n/1000).toFixed(1) + 'K' : String(n); }

// ============================================================
// CHART HELPERS
// ============================================================
function destroyChart(id) {
    if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

function createLineChart(canvasId, labels, datasets, opts = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: datasets.map(ds => ({
            ...ds, tension: 0.4, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
            fill: ds.fill !== false,
            backgroundColor: ds.bgColor || 'rgba(0,212,255,0.08)',
            borderColor: ds.color || '#00d4ff'
        }))},
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: datasets.length > 1, labels: { color: '#8888aa', font: { size: 11 } } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#55557a', font: { size: 10 }, maxTicksLimit: 8 } },
                y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#55557a', font: { size: 10 } }, beginAtZero: true }
            },
            interaction: { intersect: false, mode: 'index' },
            ...opts
        }
    });
}

function createBarChart(canvasId, labels, data, colors) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ data, backgroundColor: colors || 'rgba(0,212,255,0.6)', borderRadius: 6, borderSkipped: false }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#55557a', font: { size: 10 } } },
                y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#55557a', font: { size: 10 } }, beginAtZero: true }
            }
        }
    });
}

function createDoughnutChart(canvasId, labels, data, colors) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }] },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '65%',
            plugins: { legend: { position: 'bottom', labels: { color: '#8888aa', font: { size: 11 }, padding: 16 } } }
        }
    });
}

// ============================================================
// OVERVIEW
// ============================================================
async function loadOverview() {
    try {
        const [overview, growth, activity] = await Promise.all([
            apiFetch('/admin/overview'),
            apiFetch(`/admin/analytics/users?days=${getDays()}`),
            apiFetch(`/admin/analytics/activity?days=${getDays()}`)
        ]);

        document.getElementById('kpiTotalUsers').textContent = formatNum(overview.total_users);
        document.getElementById('kpiActiveToday').textContent = formatNum(overview.active_users_today);
        document.getElementById('kpiConversations').textContent = formatNum(overview.total_conversations);
        document.getElementById('kpiSpeaking').textContent = formatNum(overview.total_speaking_sessions);
        document.getElementById('kpiAvgScore').textContent = overview.avg_pronunciation_score.toFixed(1);
        document.getElementById('kpiTotalXP').textContent = formatNum(overview.total_xp_earned);
        document.getElementById('kpiMessages').textContent = formatNum(overview.total_messages);
        document.getElementById('kpiSubscriptions').textContent = formatNum(overview.active_subscriptions);

        // User Growth Chart
        const growthLabels = growth.daily_signups.map(d => d.date.slice(5));
        createLineChart('chartUserGrowth', growthLabels, [
            { label: 'Daily Signups', data: growth.daily_signups.map(d => d.value), color: '#00d4ff', bgColor: 'rgba(0,212,255,0.08)' },
            { label: 'Cumulative', data: growth.cumulative_users.map(d => d.value), color: '#7c3aed', bgColor: 'rgba(124,58,237,0.08)', fill: false }
        ]);

        // Activity Chart
        const actLabels = activity.daily_activities.map(d => d.date.slice(5));
        createLineChart('chartActivities', actLabels, [
            { label: 'Activities', data: activity.daily_activities.map(d => d.value), color: '#10b981', bgColor: 'rgba(16,185,129,0.08)' }
        ]);
    } catch (e) { console.error('Overview error:', e); }
}

// ============================================================
// USERS
// ============================================================
function debounceSearch() {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { currentPage = 1; loadUsers(); }, 400);
}

async function loadUsers() {
    try {
        const search = document.getElementById('userSearch').value;
        const status = document.getElementById('userStatusFilter').value;
        let url = `/admin/users?page=${currentPage}&page_size=15`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status) url += `&status=${status}`;

        const data = await apiFetch(url);
        const tbody = document.getElementById('usersTableBody');

        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="loading-cell">Không tìm thấy user nào</td></tr>';
        } else {
            tbody.innerHTML = data.users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.email}</td>
                    <td>${u.full_name || '—'}</td>
                    <td>${u.level || 'A1'}</td>
                    <td>${formatNum(u.total_xp)}</td>
                    <td>🔥 ${u.current_streak}</td>
                    <td><span class="plan-badge ${u.subscription_plan}">${u.subscription_plan}</span></td>
                    <td><span class="status-badge ${u.is_active ? 'active' : 'banned'}">${u.is_active ? '✅ Active' : '🚫 Banned'}</span></td>
                    <td>
                        <button class="btn-action" onclick="viewUser(${u.id})">👁️</button>
                        ${u.is_active
                            ? `<button class="btn-action danger" onclick="toggleUserStatus(${u.id}, false)">🚫</button>`
                            : `<button class="btn-action success" onclick="toggleUserStatus(${u.id}, true)">✅</button>`}
                    </td>
                </tr>
            `).join('');
        }

        // Pagination
        const totalPages = Math.ceil(data.total / data.page_size);
        const pag = document.getElementById('usersPagination');
        let pagHtml = `<button onclick="goToPage(${currentPage-1})" ${currentPage<=1?'disabled':''}>← Prev</button>`;
        for (let i = 1; i <= Math.min(totalPages, 5); i++) {
            pagHtml += `<button class="${i===currentPage?'active':''}" onclick="goToPage(${i})">${i}</button>`;
        }
        pagHtml += `<button onclick="goToPage(${currentPage+1})" ${currentPage>=totalPages?'disabled':''}>Next →</button>`;
        pag.innerHTML = pagHtml;
    } catch (e) { console.error('Users error:', e); }
}

function goToPage(p) { currentPage = p; loadUsers(); }

async function viewUser(id) {
    document.getElementById('userDetailModal').style.display = 'flex';
    const body = document.getElementById('userDetailBody');
    body.innerHTML = '<div class="loading-cell">Đang tải...</div>';
    try {
        const u = await apiFetch(`/admin/users/${id}`);
        body.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item"><div class="detail-label">Email</div><div class="detail-value">${u.email}</div></div>
                <div class="detail-item"><div class="detail-label">Tên</div><div class="detail-value">${u.full_name||'—'}</div></div>
                <div class="detail-item"><div class="detail-label">Level</div><div class="detail-value">${u.level}</div></div>
                <div class="detail-item"><div class="detail-label">XP</div><div class="detail-value">${formatNum(u.total_xp)}</div></div>
                <div class="detail-item"><div class="detail-label">Streak</div><div class="detail-value">🔥 ${u.current_streak}</div></div>
                <div class="detail-item"><div class="detail-label">Plan</div><div class="detail-value">${u.subscription_plan}</div></div>
                <div class="detail-item"><div class="detail-label">Conversations</div><div class="detail-value">${u.total_conversations}</div></div>
                <div class="detail-item"><div class="detail-label">Messages</div><div class="detail-value">${u.total_messages}</div></div>
                <div class="detail-item"><div class="detail-label">Speaking Sessions</div><div class="detail-value">${u.total_speaking_sessions}</div></div>
                <div class="detail-item"><div class="detail-label">Avg Score</div><div class="detail-value">${u.avg_pronunciation_score}</div></div>
                <div class="detail-item"><div class="detail-label">Achievements</div><div class="detail-value">${u.achievements_count}</div></div>
                <div class="detail-item"><div class="detail-label">Weak Points</div><div class="detail-value">${u.weak_points_count}</div></div>
                ${u.skill_levels ? `<div class="detail-item full-width"><div class="detail-label">Skills</div><div class="detail-value">
                    Vocab: ${u.skill_levels.vocabulary} | Grammar: ${u.skill_levels.grammar} | Pron: ${u.skill_levels.pronunciation} | Listen: ${u.skill_levels.listening} | Fluency: ${u.skill_levels.fluency}
                </div></div>` : ''}
                <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${u.is_active?'✅ Active':'🚫 Banned'}</div></div>
                <div class="detail-item"><div class="detail-label">Created</div><div class="detail-value">${u.created_at ? new Date(u.created_at).toLocaleDateString('vi-VN') : '—'}</div></div>
            </div>`;
    } catch (e) { body.innerHTML = '<div class="loading-cell">Lỗi tải dữ liệu</div>'; }
}

function closeUserModal() { document.getElementById('userDetailModal').style.display = 'none'; }

async function toggleUserStatus(id, active) {
    if (!confirm(`${active ? 'Kích hoạt' : 'Khóa'} user #${id}?`)) return;
    try {
        await apiFetch(`/admin/users/${id}/status`, {
            method: 'PUT', body: JSON.stringify({ is_active: active })
        });
        loadUsers();
    } catch (e) { alert('Lỗi: ' + e.message); }
}

// ============================================================
// LESSONS
// ============================================================
async function loadLessons() {
    try {
        const data = await apiFetch(`/admin/analytics/activity?days=${getDays()}`);

        document.getElementById('avgDailyActivities').textContent = data.avg_daily_activities;
        document.getElementById('peakHour').textContent = `${data.peak_hour}:00`;

        // Activity by type
        const types = Object.keys(data.activity_by_type);
        const typeVals = Object.values(data.activity_by_type);
        const typeColors = ['#00d4ff', '#7c3aed', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];
        if (types.length > 0) {
            createDoughnutChart('chartActivityTypes', types, typeVals, typeColors.slice(0, types.length));
        } else {
            createDoughnutChart('chartActivityTypes', ['No data'], [1], ['#333']);
        }

        // Activity trend
        const labels = data.daily_activities.map(d => d.date.slice(5));
        createLineChart('chartActivityTrend', labels, [
            { label: 'Activities', data: data.daily_activities.map(d => d.value), color: '#7c3aed', bgColor: 'rgba(124,58,237,0.08)' }
        ]);
    } catch (e) { console.error('Lessons error:', e); }
}

// ============================================================
// AI USAGE
// ============================================================
async function loadAIUsage() {
    try {
        const data = await apiFetch(`/admin/analytics/ai-usage?days=${getDays()}`);

        document.getElementById('aiConversations').textContent = formatNum(data.total_conversations);
        document.getElementById('aiMessages').textContent = formatNum(data.total_messages);
        document.getElementById('aiAvgMsgs').textContent = data.avg_messages_per_conversation;
        document.getElementById('aiMemories').textContent = formatNum(data.total_ai_memories);

        createLineChart('chartDailyConversations',
            data.daily_conversations.map(d => d.date.slice(5)),
            [{ label: 'Conversations', data: data.daily_conversations.map(d => d.value), color: '#00d4ff', bgColor: 'rgba(0,212,255,0.08)' }]
        );
        createLineChart('chartDailyMessages',
            data.daily_messages.map(d => d.date.slice(5)),
            [{ label: 'Messages', data: data.daily_messages.map(d => d.value), color: '#f59e0b', bgColor: 'rgba(245,158,11,0.08)' }]
        );

        const topicsList = document.getElementById('popularTopicsList');
        topicsList.innerHTML = data.popular_topics.length > 0
            ? data.popular_topics.map(t => `<div class="topic-tag">${t.topic} <span class="topic-count">${t.count}</span></div>`).join('')
            : '<span style="color:var(--text-muted)">Chưa có dữ liệu</span>';
    } catch (e) { console.error('AI Usage error:', e); }
}

// ============================================================
// SUBSCRIPTIONS
// ============================================================
async function loadSubscriptions() {
    try {
        const data = await apiFetch(`/admin/analytics/subscriptions?days=${getDays()}`);

        document.getElementById('subActive').textContent = data.active_subscriptions;
        document.getElementById('subMRR').textContent = `$${data.mrr}`;
        document.getElementById('subChurn').textContent = `${data.churn_rate}%`;
        document.getElementById('subTotal').textContent = data.total_subscriptions;
        document.getElementById('subRevenueMonthly').textContent = `$${data.revenue_monthly}`;
        document.getElementById('subRevenueYearly').textContent = `$${data.revenue_yearly}`;

        const planNames = Object.keys(data.plan_distribution);
        const planVals = Object.values(data.plan_distribution);
        const planColors = { free: '#55557a', basic: '#00d4ff', premium: '#7c3aed', enterprise: '#f59e0b' };
        createDoughnutChart('chartPlanDistribution', planNames, planVals,
            planNames.map(n => planColors[n] || '#888'));

        createLineChart('chartNewSubs',
            data.daily_new_subscriptions.map(d => d.date.slice(5)),
            [{ label: 'New Subs', data: data.daily_new_subscriptions.map(d => d.value), color: '#10b981', bgColor: 'rgba(16,185,129,0.08)' }]
        );
    } catch (e) { console.error('Subs error:', e); }
}

// ============================================================
// RETENTION
// ============================================================
async function loadRetention() {
    try {
        const data = await apiFetch(`/admin/analytics/retention?days=${getDays()}`);

        document.getElementById('retDAU').textContent = data.dau;
        document.getElementById('retWAU').textContent = data.wau;
        document.getElementById('retMAU').textContent = data.mau;
        document.getElementById('retRatio').textContent = `${data.dau_mau_ratio}%`;
        document.getElementById('retChurn').textContent = `${data.churn_rate}%`;
        document.getElementById('retAvgDuration').textContent = `${data.avg_session_duration_minutes}m`;
        document.getElementById('retReturning').textContent = `${data.returning_users_rate}%`;

        createLineChart('chartRetention',
            data.daily_retention.map(d => d.date.slice(5)),
            [{ label: 'DAU', data: data.daily_retention.map(d => d.value), color: '#ec4899', bgColor: 'rgba(236,72,153,0.08)' }]
        );
    } catch (e) { console.error('Retention error:', e); }
}

// ============================================================
// SPEAKING
// ============================================================
async function loadSpeaking() {
    try {
        const data = await apiFetch(`/admin/analytics/speaking?days=${getDays()}`);

        document.getElementById('spkTotal').textContent = data.total_sessions;
        document.getElementById('spkAvg').textContent = data.avg_overall_score;
        document.getElementById('spkFluency').textContent = data.avg_fluency;
        document.getElementById('spkIntonation').textContent = data.avg_intonation;

        // Score distribution
        const distLabels = Object.keys(data.score_distribution);
        const distVals = Object.values(data.score_distribution);
        createBarChart('chartScoreDistribution', distLabels, distVals,
            ['#ef4444', '#f59e0b', '#eab308', '#10b981', '#00d4ff']);

        createLineChart('chartDailySpeaking',
            data.daily_sessions.map(d => d.date.slice(5)),
            [{ label: 'Sessions', data: data.daily_sessions.map(d => d.value), color: '#7c3aed', bgColor: 'rgba(124,58,237,0.08)' }]
        );

        // Top performers
        const topBody = document.getElementById('topPerformersBody');
        topBody.innerHTML = data.top_performers.length > 0
            ? data.top_performers.map((p, i) => `
                <tr>
                    <td>${['🥇','🥈','🥉','4️⃣','5️⃣'][i]}</td>
                    <td>${p.name}</td>
                    <td>${p.avg_score}</td>
                    <td>${p.sessions}</td>
                </tr>`).join('')
            : '<tr><td colspan="4" class="loading-cell">Chưa có dữ liệu</td></tr>';
    } catch (e) { console.error('Speaking error:', e); }
}

// ============================================================
// AUTO LOGIN CHECK
// ============================================================
(async function init() {
    if (authToken) {
        try {
            const me = await apiFetch('/auth/me');
            if (me.is_admin) {
                document.getElementById('adminName').textContent = me.full_name || me.email;
                showDashboard();
                return;
            }
        } catch (e) { localStorage.removeItem('admin_token'); }
    }
    document.getElementById('loginScreen').style.display = 'flex';
})();
