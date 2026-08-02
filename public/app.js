// ============================================================
// Since0Bot — Telegram Mini App
// Countdown Timers + Habit Tracker
// ============================================================

const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// ---- API Layer ----
const API_BASE = window.location.origin + '/api/miniapp.py';
const INIT_DATA = tg.initData || '';

async function apiRequest(action, method = 'GET', body = null, extraParams = {}) {
    const params = new URLSearchParams({ action, ...extraParams });
    const url = `${API_BASE}?${params.toString()}`;

    const options = {
        method,
        headers: {
            'Authorization': `tma ${INIT_DATA}`,
            'Content-Type': 'application/json'
        }
    };

    if (body && (method === 'POST' || method === 'DELETE')) {
        options.body = JSON.stringify(body);
    }

    const res = await fetch(url, options);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
    }
    return res.json();
}

const API = {
    getUser: () => apiRequest('user'),
    getCountdowns: () => apiRequest('countdowns'),
    createCountdown: (data) => apiRequest('countdowns', 'POST', data),
    deleteCountdown: (id) => apiRequest('countdowns', 'DELETE', null, { id }),
    getHabits: () => apiRequest('habits'),
    createHabit: (data) => apiRequest('habits', 'POST', data),
    deleteHabit: (id) => apiRequest('habits', 'DELETE', null, { id }),
    getHabitLogs: (habitId, start, end) => apiRequest('habit_logs', 'GET', null, { habit_id: habitId, start, end }),
    logHabit: (habitId, date, status) => apiRequest('habit_logs', 'POST', { habit_id: habitId, date, status }),
    updateTimezone: (tz) => apiRequest('timezone', 'POST', { timezone: tz })
};

// ---- Theme ----
function applyTheme() {
    const p = tg.themeParams;
    if (p && p.bg_color) {
        const root = document.documentElement;
        root.style.setProperty('--bg-color', p.bg_color);
        root.style.setProperty('--secondary-bg-color', p.secondary_bg_color || '#FFFFFF');
        root.style.setProperty('--text-color', p.text_color || '#000000');
        root.style.setProperty('--hint-color', p.hint_color || '#8E8E93');
        root.style.setProperty('--link-color', p.link_color || '#007AFF');
        root.style.setProperty('--button-color', p.button_color || '#007AFF');
        root.style.setProperty('--button-text-color', p.button_text_color || '#FFFFFF');
    }
}
applyTheme();
tg.onEvent('themeChanged', applyTheme);

// ---- State ----
const state = {
    user: null,
    countdowns: [],
    habits: [],
    activeTab: 'countdown',
    selectedHabit: null,
    habitLogs: {},   // { habitId: [{ date, status }] }
    intervals: []
};

// ---- Initialization ----
async function initApp() {
    const initUser = tg.initDataUnsafe?.user;
    document.getElementById('userGreeting').textContent =
        `Привет, ${initUser?.first_name || 'друг'}!`;

    // Populate timezone selector
    populateTimezones();

    try {
        // Load user data from backend
        const userData = await API.getUser();
        state.user = userData;

        // Update premium UI
        updatePremiumUI();

        // Update timezone selector
        if (state.user.timezone) {
            const tzSelect = document.getElementById('timezoneSelect');
            tzSelect.value = state.user.timezone;
        }

        // Load countdowns and habits in parallel
        const [countdowns, habits] = await Promise.all([
            API.getCountdowns(),
            API.getHabits()
        ]);

        state.countdowns = Array.isArray(countdowns) ? countdowns : [];
        state.habits = Array.isArray(habits) ? habits : [];

        // Preload habit logs (last 6 months)
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
        const startDate = sixMonthsAgo.toISOString().split('T')[0];
        const endDate = new Date().toISOString().split('T')[0];

        for (const habit of state.habits) {
            try {
                const logs = await API.getHabitLogs(habit.id, startDate, endDate);
                state.habitLogs[habit.id] = Array.isArray(logs) ? logs : [];
            } catch {
                state.habitLogs[habit.id] = [];
            }
        }

        renderCountdowns();
        renderHabits();

    } catch (e) {
        console.error('Init error:', e);
        tg.showAlert('Ошибка загрузки данных. Попробуйте перезагрузить.');
    } finally {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }
}

// ---- Premium UI ----
function updatePremiumUI() {
    const text = document.getElementById('premiumStatusText');
    if (state.user?.is_premium) {
        text.textContent = '⭐ Premium аккаунт. Безлимитные таймеры и привычки.';
    } else {
        text.textContent = 'Бесплатный аккаунт. Лимиты: 3 таймера, 1 привычка.';
    }
}

// ---- Timezone ----
function populateTimezones() {
    const tzSelect = document.getElementById('timezoneSelect');
    const timezones = [
        { value: 'UTC-12', label: 'UTC-12 (Baker Island)' },
        { value: 'UTC-11', label: 'UTC-11 (Samoa)' },
        { value: 'UTC-10', label: 'UTC-10 (Hawaii)' },
        { value: 'UTC-9', label: 'UTC-9 (Alaska)' },
        { value: 'UTC-8', label: 'UTC-8 (Los Angeles)' },
        { value: 'UTC-7', label: 'UTC-7 (Denver)' },
        { value: 'UTC-6', label: 'UTC-6 (Chicago)' },
        { value: 'UTC-5', label: 'UTC-5 (New York)' },
        { value: 'UTC-4', label: 'UTC-4 (Atlantic)' },
        { value: 'UTC-3', label: 'UTC-3 (Buenos Aires)' },
        { value: 'UTC-2', label: 'UTC-2' },
        { value: 'UTC-1', label: 'UTC-1 (Azores)' },
        { value: 'UTC', label: 'UTC (London)' },
        { value: 'UTC+1', label: 'UTC+1 (Berlin)' },
        { value: 'UTC+2', label: 'UTC+2 (Kyiv)' },
        { value: 'UTC+3', label: 'UTC+3 (Moscow)' },
        { value: 'UTC+4', label: 'UTC+4 (Dubai)' },
        { value: 'UTC+5', label: 'UTC+5 (Tashkent)' },
        { value: 'UTC+5:30', label: 'UTC+5:30 (Mumbai)' },
        { value: 'UTC+6', label: 'UTC+6 (Almaty)' },
        { value: 'UTC+7', label: 'UTC+7 (Bangkok)' },
        { value: 'UTC+8', label: 'UTC+8 (Beijing)' },
        { value: 'UTC+9', label: 'UTC+9 (Tokyo)' },
        { value: 'UTC+10', label: 'UTC+10 (Sydney)' },
        { value: 'UTC+11', label: 'UTC+11' },
        { value: 'UTC+12', label: 'UTC+12 (Auckland)' },
        { value: 'UTC+13', label: 'UTC+13 (Tonga)' },
        { value: 'UTC+14', label: 'UTC+14 (Kiribati)' }
    ];

    tzSelect.innerHTML = '';
    timezones.forEach(tz => {
        const opt = document.createElement('option');
        opt.value = tz.value;
        opt.textContent = tz.label;
        tzSelect.appendChild(opt);
    });
}

// ---- Timer Utilities ----
function clearTimers() {
    state.intervals.forEach(clearInterval);
    state.intervals = [];
}

// ---- Tab Navigation ----
function switchTab(tabName) {
    try { tg.HapticFeedback.impactOccurred('light'); } catch {}
    state.activeTab = tabName;

    document.querySelectorAll('.tab-item').forEach(el => {
        el.classList.toggle('active', el.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(el => {
        el.classList.toggle('active', el.id === `${tabName}Tab`);
    });
    document.querySelector('.app-title').textContent =
        tabName === 'countdown' ? 'Таймеры' : 'Привычки';

    // Hide detail view
    document.getElementById('habitDetailView').classList.add('hidden');
    state.selectedHabit = null;
}

// ============================================================
// COUNTDOWN TAB
// ============================================================

function renderCountdowns() {
    const list = document.getElementById('countdownList');
    const empty = document.getElementById('countdownEmpty');
    clearTimers();

    if (state.countdowns.length === 0) {
        list.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');
    list.innerHTML = '';

    state.countdowns.forEach(cd => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="cd-header">
                <div class="cd-title">${escapeHtml(cd.title)}</div>
                ${cd.frequency > 0 ? `<div class="badge">Раз в ${cd.frequency} дн.</div>` : ''}
            </div>
            <button class="cd-delete" data-id="${cd.id}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18"></path>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
            <div class="cd-timer" id="timer-${cd.id}">
                <div class="cd-unit"><div class="cd-val d">--</div><div class="cd-label">ДНЕЙ</div></div>
                <div class="cd-unit"><div class="cd-val h">--</div><div class="cd-label">ЧАСОВ</div></div>
                <div class="cd-unit"><div class="cd-val m">--</div><div class="cd-label">МИНУТ</div></div>
                <div class="cd-unit"><div class="cd-val s pulsing">--</div><div class="cd-label">СЕК</div></div>
            </div>
        `;
        list.appendChild(card);

        // Live timer
        const targetDate = cd.target_date;
        updateTimerUI(cd.id, targetDate);
        const interval = setInterval(() => updateTimerUI(cd.id, targetDate), 1000);
        state.intervals.push(interval);
    });

    // Delete button handlers
    document.querySelectorAll('.cd-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleDeleteCountdown(parseInt(btn.dataset.id));
        });
    });
}

function updateTimerUI(id, targetDate) {
    const el = document.getElementById(`timer-${id}`);
    if (!el) return;

    const now = Date.now();
    // target_date is a DATE (YYYY-MM-DD), interpret as end-of-day target
    const target = new Date(targetDate + 'T00:00:00').getTime();
    const diff = target - now;

    if (diff <= 0) {
        el.innerHTML = '<div style="color: var(--ios-green); font-weight: 600; text-align: center; width: 100%; font-size: 20px;">🎉 Событие наступило!</div>';
        return;
    }

    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);

    el.querySelector('.d').textContent = d.toString().padStart(2, '0');
    el.querySelector('.h').textContent = h.toString().padStart(2, '0');
    el.querySelector('.m').textContent = m.toString().padStart(2, '0');
    el.querySelector('.s').textContent = s.toString().padStart(2, '0');
}

async function handleDeleteCountdown(id) {
    tg.showConfirm('Удалить таймер?', async (confirmed) => {
        if (!confirmed) return;
        showLoading();
        try {
            await API.deleteCountdown(id);
            state.countdowns = state.countdowns.filter(c => c.id !== id);
            renderCountdowns();
            try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
        } catch (e) {
            tg.showAlert('Ошибка удаления');
        } finally {
            hideLoading();
        }
    });
}

// ============================================================
// HABITS TAB
// ============================================================

function renderHabits() {
    const list = document.getElementById('habitsList');
    const empty = document.getElementById('habitsEmpty');

    if (state.habits.length === 0) {
        list.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');
    list.innerHTML = '';

    state.habits.forEach(habit => {
        const card = document.createElement('div');
        card.className = 'card habit-card';
        card.dataset.id = habit.id;

        // 28-day mini grid
        const logs = state.habitLogs[habit.id] || [];
        let gridHtml = '';
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let i = 27; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(d.getDate() - i);
            const dateStr = formatDate(d);
            const log = logs.find(l => l.date === dateStr);
            const cssClass = log ? log.status : '';
            gridHtml += `<div class="mini-cell ${cssClass}"></div>`;
        }

        card.innerHTML = `
            <div class="habit-header">
                <div class="habit-icon">📋</div>
                <div class="habit-title">${escapeHtml(habit.title)}</div>
            </div>
            <div class="habit-mini-grid">${gridHtml}</div>
        `;

        card.addEventListener('click', () => openHabitDetail(habit.id));
        list.appendChild(card);
    });
}

async function openHabitDetail(id) {
    try { tg.HapticFeedback.impactOccurred('light'); } catch {}
    const habit = state.habits.find(h => h.id === id);
    if (!habit) return;

    state.selectedHabit = habit;

    document.getElementById('detailHabitTitle').textContent = habit.title;
    document.getElementById('habitDetailView').classList.remove('hidden');
    document.querySelector('.app-title').textContent = 'Статистика';

    // Load logs if not cached
    if (!state.habitLogs[id] || state.habitLogs[id].length === 0) {
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
        try {
            const logs = await API.getHabitLogs(
                id,
                formatDate(sixMonthsAgo),
                formatDate(new Date())
            );
            state.habitLogs[id] = Array.isArray(logs) ? logs : [];
        } catch {
            state.habitLogs[id] = [];
        }
    }

    renderCalendar(habit);
    updateHabitButtons(habit);
}

function closeHabitDetail() {
    try { tg.HapticFeedback.impactOccurred('light'); } catch {}
    document.getElementById('habitDetailView').classList.add('hidden');
    document.querySelector('.app-title').textContent = 'Привычки';
    state.selectedHabit = null;
    renderHabits();
}

function renderCalendar(habit) {
    const container = document.getElementById('habitCalendar');
    container.innerHTML = '';

    const logs = state.habitLogs[habit.id] || [];
    const logMap = {};
    logs.forEach(l => { logMap[l.date] = l.status; });

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = formatDate(today);

    const createdDate = new Date(habit.created_at);
    createdDate.setHours(0, 0, 0, 0);

    // Generate ~26 weeks (6 months) of data
    // Find the Monday 26 weeks ago
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - (26 * 7) - today.getDay() + 1);

    let currentDate = new Date(startDate);
    let currentMonth = -1;

    // Month labels row
    const monthRow = document.createElement('div');
    monthRow.style.display = 'flex';
    monthRow.style.gap = '4px';
    monthRow.style.marginBottom = '4px';

    const monthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];

    // Build grid columns (each column = 1 week)
    const totalWeeks = 27;
    for (let w = 0; w < totalWeeks; w++) {
        const col = document.createElement('div');
        col.className = 'cal-col';

        // Check if this week starts a new month
        const weekStart = new Date(startDate);
        weekStart.setDate(weekStart.getDate() + w * 7);

        if (weekStart.getMonth() !== currentMonth) {
            currentMonth = weekStart.getMonth();
            const label = document.createElement('div');
            label.className = 'cal-month-label';
            label.textContent = monthNames[currentMonth];
            col.prepend(label);
        }

        for (let d = 0; d < 7; d++) {
            const cellDate = new Date(startDate);
            cellDate.setDate(startDate.getDate() + w * 7 + d);
            cellDate.setHours(0, 0, 0, 0);
            const dateStr = formatDate(cellDate);

            const cell = document.createElement('div');
            cell.className = 'cal-cell';

            if (cellDate > today) {
                cell.classList.add('future');
            } else if (cellDate < createdDate) {
                // Before habit creation — gray (default)
            } else if (logMap[dateStr]) {
                cell.classList.add(logMap[dateStr]); // 'green' or 'red'
            }
            // Past days without log stay gray — NOT auto-red

            if (dateStr === todayStr) {
                cell.classList.add('today');
            }

            cell.title = dateStr;
            col.appendChild(cell);
        }
        container.appendChild(col);
    }

    // Auto-scroll to the right (most recent)
    setTimeout(() => {
        const scrollCont = document.querySelector('.calendar-scroll-container');
        if (scrollCont) scrollCont.scrollLeft = scrollCont.scrollWidth;
    }, 50);
}

function updateHabitButtons(habit) {
    const todayStr = formatDate(new Date());
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = formatDate(yesterday);

    const logs = state.habitLogs[habit.id] || [];
    const todayLog = logs.find(l => l.date === todayStr);
    const yestLog = logs.find(l => l.date === yesterdayStr);

    const markTodayBtn = document.getElementById('markTodayBtn');
    const markYestBtn = document.getElementById('markYesterdayBtn');

    if (todayLog && todayLog.status === 'green') {
        markTodayBtn.textContent = 'Сегодня отмечено 🟩';
        markTodayBtn.classList.add('completed');
        markTodayBtn.disabled = true;
    } else {
        markTodayBtn.textContent = 'Отметить сегодня ✅';
        markTodayBtn.classList.remove('completed');
        markTodayBtn.disabled = false;
    }

    const createdDate = new Date(habit.created_at);
    createdDate.setHours(0, 0, 0, 0);
    if (!yestLog && yesterday >= createdDate) {
        markYestBtn.classList.remove('hidden');
        markYestBtn.textContent = 'Отметить вчера ✅';
        markYestBtn.disabled = false;
    } else if (yestLog && yestLog.status === 'green') {
        markYestBtn.classList.remove('hidden');
        markYestBtn.textContent = 'Вчера отмечено 🟩';
        markYestBtn.disabled = true;
    } else {
        markYestBtn.classList.add('hidden');
    }
}

async function markHabit(dateStr) {
    if (!state.selectedHabit) return;
    try { tg.HapticFeedback.impactOccurred('medium'); } catch {}

    const habitId = state.selectedHabit.id;

    // Optimistic UI update
    if (!state.habitLogs[habitId]) state.habitLogs[habitId] = [];
    const existing = state.habitLogs[habitId].findIndex(l => l.date === dateStr);
    if (existing >= 0) {
        state.habitLogs[habitId][existing].status = 'green';
    } else {
        state.habitLogs[habitId].push({ date: dateStr, status: 'green' });
    }

    renderCalendar(state.selectedHabit);
    updateHabitButtons(state.selectedHabit);

    try {
        await API.logHabit(habitId, dateStr, 'green');
        try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
    } catch (e) {
        // Rollback
        const idx = state.habitLogs[habitId].findIndex(l => l.date === dateStr);
        if (idx >= 0) state.habitLogs[habitId].splice(idx, 1);
        renderCalendar(state.selectedHabit);
        updateHabitButtons(state.selectedHabit);
        tg.showAlert('Ошибка сохранения. Попробуйте ещё раз.');
    }
}

// ============================================================
// MODALS
// ============================================================

function openModal(modalId) {
    try { tg.HapticFeedback.impactOccurred('light'); } catch {}
    document.getElementById('modalOverlay').classList.add('show');
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById('modalOverlay').classList.remove('show');
    if (modalId) {
        document.getElementById(modalId).classList.remove('show');
    } else {
        document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
    }
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

// ============================================================
// UTILITIES
// ============================================================

function formatDate(date) {
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// EVENT LISTENERS
// ============================================================

// Tab navigation
document.querySelectorAll('.tab-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// FAB button
document.getElementById('fab').addEventListener('click', () => {
    if (state.activeTab === 'countdown') {
        if (!state.user?.is_premium && state.countdowns.length >= 3) {
            tg.showAlert('Достигнут лимит (3 таймера). Используйте /premium в боте для безлимита.');
            return;
        }
        openModal('createCountdownModal');
    } else {
        if (!state.user?.is_premium && state.habits.length >= 1) {
            tg.showAlert('Достигнут лимит (1 привычка). Используйте /premium в боте для безлимита.');
            return;
        }
        openModal('createHabitModal');
    }
});

// Modal close buttons
document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.modal));
});
document.getElementById('modalOverlay').addEventListener('click', () => closeModal());

// Settings
document.getElementById('settingsBtn').addEventListener('click', () => openModal('settingsModal'));

// Timezone change
document.getElementById('timezoneSelect').addEventListener('change', async (e) => {
    const tz = e.target.value;
    try {
        await API.updateTimezone(tz);
        if (state.user) state.user.timezone = tz;
        try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
    } catch {
        tg.showAlert('Ошибка сохранения часового пояса');
    }
});

// Create Countdown form
document.getElementById('createCountdownForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = document.getElementById('cdTitle').value.trim();
    const dateVal = document.getElementById('cdDate').value;
    const freq = parseInt(document.getElementById('cdFreq').value) || 0;
    const notifyHour = parseInt(document.getElementById('cdNotifyHour').value) || 9;

    if (!title || !dateVal) {
        tg.showAlert('Заполните название и дату');
        return;
    }

    try { tg.HapticFeedback.impactOccurred('medium'); } catch {}
    closeModal('createCountdownModal');
    showLoading();

    try {
        const res = await API.createCountdown({
            title,
            target_date: dateVal,
            frequency: freq,
            notify_hour: notifyHour
        });

        if (res.error) {
            if (res.error === 'Limit reached') {
                tg.showAlert('Достигнут лимит. Используйте /premium в боте.');
            } else {
                tg.showAlert(res.error);
            }
        } else {
            state.countdowns.push(res);
            renderCountdowns();
            try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
        }
    } catch (err) {
        tg.showAlert('Ошибка создания таймера');
    } finally {
        hideLoading();
        e.target.reset();
    }
});

// Create Habit form
document.getElementById('createHabitForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = document.getElementById('hbTitle').value.trim();
    if (!title) {
        tg.showAlert('Введите название привычки');
        return;
    }

    try { tg.HapticFeedback.impactOccurred('medium'); } catch {}
    closeModal('createHabitModal');
    showLoading();

    try {
        const res = await API.createHabit({ title });

        if (res.error) {
            if (res.error === 'Limit reached') {
                tg.showAlert('Достигнут лимит. Используйте /premium в боте.');
            } else {
                tg.showAlert(res.error);
            }
        } else {
            state.habits.push(res);
            state.habitLogs[res.id] = [];
            renderHabits();
            try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
        }
    } catch (err) {
        tg.showAlert('Ошибка создания привычки');
    } finally {
        hideLoading();
        e.target.reset();
    }
});

// Delete habit
document.getElementById('deleteHabitBtn').addEventListener('click', () => {
    if (!state.selectedHabit) return;
    tg.showConfirm('Удалить привычку и всю историю?', async (confirmed) => {
        if (!confirmed) return;
        showLoading();
        try {
            await API.deleteHabit(state.selectedHabit.id);
            delete state.habitLogs[state.selectedHabit.id];
            state.habits = state.habits.filter(h => h.id !== state.selectedHabit.id);
            closeHabitDetail();
            try { tg.HapticFeedback.notificationOccurred('success'); } catch {}
        } catch {
            tg.showAlert('Ошибка удаления');
        } finally {
            hideLoading();
        }
    });
});

// Habit detail navigation
document.getElementById('backToHabitsBtn').addEventListener('click', closeHabitDetail);

// Mark today/yesterday
document.getElementById('markTodayBtn').addEventListener('click', () => {
    markHabit(formatDate(new Date()));
});

document.getElementById('markYesterdayBtn').addEventListener('click', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    markHabit(formatDate(yesterday));
});

// ---- Start the app ----
initApp();
