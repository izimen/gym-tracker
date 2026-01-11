// ============================================
// UTILS
// ============================================

// Safety wrapper for DOMPurify
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;
}

// ============================================
// STATE
// ============================================
const MONTHS_PL = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'];

let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1;
let selectedDate = null;
let selectedParts = [];
let weightData = {};  // {part: {kg, sets, reps}}
let workoutsData = {};
let bodyPartsConfig = {};
let heatmapYear = new Date().getFullYear();  // Year for heatmap navigation
let completenessData = {};  // {date: {status: 'complete'|'partial'|'missing', ...}}

// ============================================
// TAB SWITCHING
// ============================================
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');

        // Load data on first visit
        if (tab.dataset.tab === 'stats' && !document.getElementById('weeklyChart').hasChildNodes()) {
            loadStatistics();
        }
        if (tab.dataset.tab === 'strength' && !document.getElementById('recordsGrid').querySelector('.record-card')) {
            loadStrengthData();
        }
    });
});

// ============================================
// AUTHENTICATION
// ============================================
let currentUser = null;

function getStoredUser() {
    const stored = localStorage.getItem('gym_user');
    if (stored) {
        try {
            return JSON.parse(stored);
        } catch (e) {
            return null;
        }
    }
    return null;
}

function storeUser(user) {
    localStorage.setItem('gym_user', JSON.stringify(user));
    currentUser = user;
}

function clearUser() {
    localStorage.removeItem('gym_user');
    currentUser = null;
}

function showLoginOverlay() {
    document.getElementById('loginOverlay').classList.remove('hidden');
}

function hideLoginOverlay() {
    document.getElementById('loginOverlay').classList.add('hidden');
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginError').textContent = '';
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('registerError').textContent = '';
}

async function handleLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorEl = document.getElementById('loginError');

    if (!username || !password) {
        errorEl.textContent = 'Wypełnij wszystkie pola';
        return;
    }

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            storeUser({ user_id: data.user_id, username: data.username });
            hideLoginOverlay();
            updateUserBadge();
            startApp();
        } else {
            errorEl.textContent = data.error || 'Błąd logowania';
        }
    } catch (e) {
        errorEl.textContent = 'Błąd połączenia';
    }
}

async function handleRegister() {
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value;
    const errorEl = document.getElementById('registerError');

    if (!username || !password) {
        errorEl.textContent = 'Wypełnij wszystkie pola';
        return;
    }

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            storeUser({ user_id: data.user_id, username: data.username });
            hideLoginOverlay();
            updateUserBadge();
            startApp();
        } else {
            errorEl.textContent = data.error || 'Błąd rejestracji';
        }
    } catch (e) {
        errorEl.textContent = 'Błąd połączenia';
    }
}

function logout() {
    if (confirm('Czy na pewno chcesz się wylogować?')) {
        clearUser();
        location.reload();
    }
}

function updateUserBadge() {
    if (currentUser) {
        const badge = document.getElementById('userBadge');
        if (badge) {
            badge.textContent = '👤 ' + currentUser.username;
        }
    }
}

function checkAuth() {
    currentUser = getStoredUser();
    if (currentUser) {
        hideLoginOverlay();
        updateUserBadge();
        return true;
    } else {
        showLoginOverlay();
        return false;
    }
}

// Allow Enter key to submit forms
document.getElementById('loginPassword').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleLogin();
});
document.getElementById('registerPassword').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleRegister();
});

// ============================================
// INITIALIZATION
// ============================================
async function startApp() {
    // Fetch live count first (non-blocking) so counter appears immediately
    fetchLiveCount();

    await fetchDashboard();
    await Promise.all([fetchMonthWorkouts(), fetchCompleteness()]);
    renderCalendar();
    renderLegend();

    // Auto-refresh live count
    setInterval(fetchLiveCount, 60000);
}

function init() {
    if (checkAuth()) {
        startApp();
    }
}

// ============================================
// LIVE COUNTER
// ============================================
async function fetchLiveCount() {
    try {
        const response = await fetch('/api/occupancy');
        const data = await response.json();
        // Display count even if status is 'initializing' - show what we have
        if (data.entries_today !== undefined && data.entries_today !== null) {
            document.getElementById('liveCount').textContent = data.entries_today;
        }
    } catch (error) {
        console.error('Error fetching live count:', error);
    }
}

// ============================================
// DASHBOARD DATA
// ============================================
async function fetchDashboard() {
    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/workouts/dashboard${userParam}`);
        const data = await response.json();

        document.getElementById('weeklyCount').textContent = data.weekly_count || 0;
        document.getElementById('monthlyCount').textContent = data.monthly_count || 0;

        if (data.most_trained) {
            document.getElementById('mostTrained').textContent =
                data.most_trained.emoji + ' ' + data.most_trained.count;
        }

        if (data.body_parts_config) {
            bodyPartsConfig = data.body_parts_config;
        }
    } catch (error) {
        console.error('Error fetching dashboard:', error);
    }
}

// ============================================
// CALENDAR
// ============================================
async function fetchMonthWorkouts() {
    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/workouts/month/${currentYear}/${currentMonth}${userParam}`);
        const data = await response.json();

        workoutsData = {};
        if (data.workouts) {
            for (const workout of data.workouts) {
                workoutsData[workout.date] = workout;
            }
        }

        if (data.body_parts_config) {
            bodyPartsConfig = data.body_parts_config;
        }
    } catch (error) {
        console.error('Error fetching workouts:', error);
    }
}

async function fetchCompleteness() {
    try {
        const response = await fetch(`/api/analytics/completeness/${currentYear}/${currentMonth}`);
        const data = await response.json();
        if (data.days) {
            completenessData = data.days;
        }
    } catch (error) {
        console.error('Error fetching completeness:', error);
    }
}

function renderCalendar() {
    const container = document.getElementById('calendarDays');
    container.innerHTML = '';

    document.getElementById('currentMonth').textContent =
        `${MONTHS_PL[currentMonth - 1]} ${currentYear}`;

    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const totalDays = lastDay.getDate();

    let startDay = firstDay.getDay() - 1;
    if (startDay < 0) startDay = 6;

    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    const prevMonthLastDay = new Date(currentYear, currentMonth - 1, 0);
    const prevMonthDays = prevMonthLastDay.getDate();

    // Previous month days
    for (let i = startDay - 1; i >= 0; i--) {
        const day = prevMonthDays - i;
        const cell = document.createElement('div');
        cell.className = 'day other-month';
        cell.innerHTML = safeSanitize(`<div class="day-number">${day}</div>`);
        container.appendChild(cell);
    }

    // Current month days
    for (let day = 1; day <= totalDays; day++) {
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const workout = workoutsData[dateStr];

        const cell = document.createElement('div');
        cell.className = 'day';

        if (dateStr === todayStr) {
            cell.classList.add('today');
        }

        if (workout) {
            cell.classList.add('has-workout');
        }

        // Get data completeness status for this day (only for past days, not today or future)
        const dayCompleteness = completenessData[dateStr];
        let completenessClass = '';
        let completenessTitle = '';
        const isPastDay = dateStr < todayStr;  // Only show dots for completed days

        if (dayCompleteness && isPastDay) {
            if (dayCompleteness.status === 'complete') {
                completenessClass = 'data-complete';
                completenessTitle = `Pełne dane (${dayCompleteness.hours_collected}/${dayCompleteness.hours_expected}h)`;
            } else if (dayCompleteness.status === 'partial') {
                completenessClass = 'data-partial';
                completenessTitle = `Częściowe dane (${dayCompleteness.hours_collected}/${dayCompleteness.hours_expected}h)`;
            } else if (dayCompleteness.status === 'holiday') {
                completenessClass = 'data-holiday';
                completenessTitle = `Święto/skrócone godziny (${dayCompleteness.hours_collected}h)`;
            } else {
                completenessClass = 'data-missing';
                completenessTitle = `Brak danych (${dayCompleteness.hours_collected}/${dayCompleteness.hours_expected}h)`;
            }
        }

        cell.innerHTML = safeSanitize(`
                    <div class="day-number">${day}</div>
                    <div class="day-icons">${workout ? getWorkoutIcons(workout.body_parts) : ''}</div>
                    ${completenessClass ? `<span class="data-dot ${completenessClass}" title="${completenessTitle}"></span>` : ''}
                `);

        cell.onclick = () => openModal(dateStr);
        container.appendChild(cell);
    }

    // Next month days
    const totalCells = startDay + totalDays;
    const targetCells = Math.ceil(totalCells / 7) * 7;
    const nextMonthDays = targetCells - totalCells;

    for (let day = 1; day <= nextMonthDays; day++) {
        const cell = document.createElement('div');
        cell.className = 'day other-month';
        cell.innerHTML = `<div class="day-number">${day}</div>`;
        container.appendChild(cell);
    }
}

function getWorkoutIcons(parts) {
    if (!parts || !parts.length) return '';
    return parts.map(p => `<span>${bodyPartsConfig[p]?.emoji || ''}</span>`).join('');
}

function renderLegend() {
    const container = document.getElementById('legend');
    const fullLegend = document.getElementById('fullLegend');
    container.innerHTML = '';
    fullLegend.innerHTML = '';

    for (const [key, config] of Object.entries(bodyPartsConfig)) {
        const item = `<div class="legend-item"><span>${config.emoji}</span><span>${config.name}</span></div>`;
        container.innerHTML += item;
        fullLegend.innerHTML += item;
    }
}

function prevMonth() {
    currentMonth--;
    if (currentMonth < 1) {
        currentMonth = 12;
        currentYear--;
    }
    Promise.all([fetchMonthWorkouts(), fetchCompleteness()]).then(renderCalendar);
}

function nextMonth() {
    currentMonth++;
    if (currentMonth > 12) {
        currentMonth = 1;
        currentYear++;
    }
    Promise.all([fetchMonthWorkouts(), fetchCompleteness()]).then(renderCalendar);
}

// ============================================
// MODAL
// ============================================
function renderBodyPartsGrid() {
    const container = document.getElementById('bodyPartsGrid');
    container.innerHTML = '';

    for (const [key, config] of Object.entries(bodyPartsConfig)) {
        const isSelected = selectedParts.includes(key);
        const wd = weightData[key] || { kg: '', sets: '', reps: '' };

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 12px 14px;
                    background: ${isSelected ? 'rgba(124, 58, 237, 0.15)' : 'var(--bg-input)'};
                    border: 2px solid ${isSelected ? 'var(--primary)' : 'var(--border)'};
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                `;

        // Checkbox area
        const checkArea = document.createElement('div');
        checkArea.style.cssText = 'display: flex; align-items: center; gap: 10px; min-width: 120px;';
        checkArea.innerHTML = safeSanitize(`
                    <div style="width: 20px; height: 20px; border: 2px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}; border-radius: 5px; display: flex; align-items: center; justify-content: center; background: ${isSelected ? 'var(--primary)' : 'transparent'};">
                        ${isSelected ? '<span style="color: white; font-size: 0.7rem;">✓</span>' : ''}
                    </div>
                    <span style="font-size: 1.3rem;">${config.emoji}</span>
                    <span style="font-size: 0.85rem; font-weight: 500;">${config.name}</span>
                `);
        checkArea.onclick = () => togglePart(key);
        wrapper.appendChild(checkArea);

        // Spacer
        const spacer = document.createElement('div');
        spacer.style.flex = '1';
        wrapper.appendChild(spacer);

        // Weight inputs (always visible, but disabled if not selected)
        const inputsArea = document.createElement('div');
        inputsArea.style.cssText = 'display: flex; align-items: center; gap: 6px;';
        inputsArea.innerHTML = safeSanitize(`
                    <input type="text" inputmode="numeric" placeholder="kg" value="${wd.kg}" 
                        ${isSelected ? '' : 'disabled'}
                        onchange="updateWeight('${key}', 'kg', this.value)"
                        onclick="event.stopPropagation()"
                        style="width: 45px; padding: 8px 4px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary); font-size: 0.8rem; text-align: center; opacity: ${isSelected ? '1' : '0.4'};">
                    <span style="font-size: 0.7rem; color: var(--text-muted);">×</span>
                    <input type="text" inputmode="numeric" placeholder="ser" value="${wd.sets}"
                        ${isSelected ? '' : 'disabled'}
                        onchange="updateWeight('${key}', 'sets', this.value)"
                        onclick="event.stopPropagation()"
                        style="width: 35px; padding: 8px 4px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary); font-size: 0.8rem; text-align: center; opacity: ${isSelected ? '1' : '0.4'};">
                    <span style="font-size: 0.7rem; color: var(--text-muted);">×</span>
                    <input type="text" inputmode="numeric" placeholder="powt" value="${wd.reps}"
                        ${isSelected ? '' : 'disabled'}
                        onchange="updateWeight('${key}', 'reps', this.value)"
                        onclick="event.stopPropagation()"
                        style="width: 40px; padding: 8px 4px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary); font-size: 0.8rem; text-align: center; opacity: ${isSelected ? '1' : '0.4'};">
                `);
        wrapper.appendChild(inputsArea);

        container.appendChild(wrapper);
    }
}

function updateWeight(part, field, value) {
    if (!weightData[part]) {
        weightData[part] = { kg: '', sets: '', reps: '' };
    }
    weightData[part][field] = value ? parseInt(value) : '';
}

function togglePart(part) {
    const idx = selectedParts.indexOf(part);
    if (idx > -1) {
        selectedParts.splice(idx, 1);
        delete weightData[part];
    } else {
        selectedParts.push(part);
    }
    renderBodyPartsGrid();
}

function openModal(dateStr) {
    selectedDate = dateStr;
    const workout = workoutsData[dateStr];
    selectedParts = workout ? [...workout.body_parts] : [];
    weightData = workout && workout.weight_data ? { ...workout.weight_data } : {};

    document.getElementById('modalTitle').textContent =
        workout ? `Edytuj trening (${dateStr})` : `Dodaj trening (${dateStr})`;
    document.getElementById('deleteBtn').style.display = workout ? 'block' : 'none';

    renderBodyPartsGrid();
    document.getElementById('modalOverlay').classList.add('show');
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('show');
    selectedDate = null;
    selectedParts = [];
    weightData = {};
}

async function saveWorkout() {
    if (!selectedDate || selectedParts.length === 0) {
        alert('Wybierz przynajmniej jedną partię ciała!');
        return;
    }

    try {
        const response = await fetch('/api/workout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: selectedDate,
                body_parts: selectedParts,
                weight_data: weightData,
                user_id: currentUser ? currentUser.user_id : null
            })
        });

        if (response.ok) {
            closeModal();
            await fetchMonthWorkouts();
            await fetchDashboard();
            renderCalendar();
        } else {
            const data = await response.json();
            alert('Błąd: ' + (data.error || 'Nieznany błąd'));
        }
    } catch (error) {
        console.error('Error saving workout:', error);
        alert('Błąd połączenia');
    }
}

async function deleteWorkout() {
    if (!selectedDate) return;
    if (!confirm('Czy na pewno chcesz usunąć ten trening?')) return;

    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/workout/${selectedDate}${userParam}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            closeModal();
            await fetchMonthWorkouts();
            await fetchDashboard();
            renderCalendar();
        }
    } catch (error) {
        console.error('Error deleting workout:', error);
    }
}

// Close modal on overlay click
document.getElementById('modalOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'modalOverlay') closeModal();
});

// ============================================
// STATISTICS
// ============================================
function isGymOpen() {
    const now = new Date();
    const day = now.getDay();
    const hour = now.getHours();

    // Monday (1) to Friday (5)
    if (day >= 1 && day <= 5) {
        return hour >= 6 && hour < 23;
    }
    // Saturday (6) and Sunday (0)
    else {
        return hour >= 8 && hour < 20;
    }
}

function updateGymStatusUI() {
    if (!isGymOpen()) {
        const ids = ['statsAvgWeekday', 'statsWeekdayHour', 'statsAvgHour', 'statsLiveNow'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = 'Zamknięte';
                el.style.fontSize = '1rem';
                el.style.color = 'var(--text-muted)';
            }
        });
    }
}

async function loadStatistics() {
    await Promise.all([
        fetchExtendedStats(),
        fetchNewYearStats(),
        fetchWeeklyChart(),
        fetchYearlyHeatmap(),
        fetchComparison()
    ]);
}

async function fetchExtendedStats() {
    try {
        const [extendedRes, liveRes] = await Promise.all([
            fetch('/api/analytics/extended'),
            fetch('/api/occupancy')
        ]);
        const data = await extendedRes.json();
        const live = await liveRes.json();

        // Average for today's weekday (MAX daily)
        document.getElementById('statsAvgWeekday').textContent =
            data.today_avg ? Math.round(data.today_avg) : '--';
        document.getElementById('statsWeekdayLabel').textContent =
            data.weekday_name_full ? `Śr. ${data.weekday_name_full}` : 'Śr. dziś';

        // Average for today's weekday at this hour (NEW)
        document.getElementById('statsWeekdayHour').textContent =
            data.today_hour_avg !== undefined ? Math.round(data.today_hour_avg) : '--';
        document.getElementById('statsWeekdayHourLabel').textContent =
            data.weekday_name_full ? `Śr. ${data.weekday_name_full} o tej porze` : 'Śr. dziś o tej porze';

        // Average for current hour (all days)
        document.getElementById('statsAvgHour').textContent =
            data.current_hour_avg ? Math.round(data.current_hour_avg) : '--';

        // Live count
        if (live.entries_today !== undefined) {
            document.getElementById('statsLiveNow').textContent = live.entries_today;
        }

        // Render charts
        renderDailyChart(data.daily_averages || {});
        renderHourlyChart(data.hourly_averages || {});
        renderBestWorstTimes(data.best_times || [], data.worst_times || []);

        // Override with "Zamknięte" if gym is closed
        updateGymStatusUI();

    } catch (error) {
        console.error('Error fetching extended stats:', error);
    }
}

async function fetchNewYearStats() {
    try {
        const response = await fetch('/api/analytics/new-year');
        const data = await response.json();

        if (!data.has_data) {
            // Show card with placeholder text (fallback if server doesn't send sample data)
            document.getElementById('newYearCard').style.display = 'block';
            document.getElementById('newYearMainChange').textContent = 'Zbieranie danych...';
            document.getElementById('newYearMainChange').style.fontSize = '0.85rem';
            document.getElementById('newYearWeekday').textContent = 'Porównanie pojawi się w styczniu';
            document.getElementById('newYearPeak').textContent = data.reason || 'Brak wystarczających danych';

            // Show right column with placeholder
            document.getElementById('newYearTrend').style.display = 'block';
            document.getElementById('newYearWeeklyTrend').textContent = 'Wykres dostępny po 7 stycznia';
            document.getElementById('newYearWeeklyTrend').style.color = 'var(--text-muted)';
            document.getElementById('newYearDecay').style.display = 'none';
            return;
        }

        // Show the card
        const card = document.getElementById('newYearCard');
        card.style.display = 'block';

        // Set title
        const titleEl = document.querySelector('#newYearCard > div:first-child');
        titleEl.innerHTML = '🎆 EFEKT NOWOROCZNY';

        // Main percentage change
        const change = data.overall_change;
        const sign = change >= 0 ? '+' : '';
        document.getElementById('newYearMainChange').textContent =
            `${sign}${change}% więcej osób niż w grudniu`;
        document.getElementById('newYearMainChange').style.fontSize = '0.9rem';

        // Today's weekday comparison
        const weekdayChange = data.current_weekday_change;
        const weekdaySign = weekdayChange >= 0 ? '+' : '';
        document.getElementById('newYearWeekday').textContent =
            `Dzisiaj (${data.current_weekday_name}): ${weekdaySign}${weekdayChange}% vs śr. ${data.current_weekday_name.substring(0, 3)}. gru.`;

        // Peak day (safer parsing)
        if (data.january && data.january.peak_day) {
            const peak = data.january.peak_day;
            // peak.date is YYYY-MM-DD
            const parts = peak.date.split('-');
            const day = parseInt(parts[2], 10);
            const monthIdx = parseInt(parts[1], 10) - 1;

            const months = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
                'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];

            document.getElementById('newYearPeak').textContent =
                `Szczyt: ${day} ${months[monthIdx]} (${peak.occupancy} osób)`;
        }

        // Weekly trend - show if we have at least 1 week of data
        if (data.weekly_trend && data.weekly_trend.length >= 1) {
            document.getElementById('newYearTrend').style.display = 'block';

            // Build trend string: W1: +42% | W2: +38% ↓ | ...
            const trendParts = data.weekly_trend.map((w, i) => {
                const percentChange = Math.round(w.percent - 100 + data.overall_change);
                const sign = percentChange >= 0 ? '+' : '';
                const arrow = i > 0 && w.change < 0 ? ' ↓' : (i > 0 && w.change > 0 ? ' ↑' : '');
                return `W${w.week}: ${sign}${percentChange}%${arrow}`;
            });
            document.getElementById('newYearWeeklyTrend').textContent = trendParts.join(' | ');
            document.getElementById('newYearWeeklyTrend').style.color = 'var(--text-primary)';

            // Decay rate - only show if we have at least 2 weeks
            if (data.avg_weekly_decay !== 0 && data.weekly_trend.length >= 2) {
                document.getElementById('newYearDecay').style.display = 'flex';
                const decay = data.avg_weekly_decay;
                const label = decay < 0 ? 'Spadek' : 'Wzrost';
                const absValue = Math.abs(decay);
                document.getElementById('newYearDecayText').textContent =
                    `${label} ${absValue}%/tydzień`;
            } else {
                document.getElementById('newYearDecay').style.display = 'none';
            }
        } else {
            document.getElementById('newYearTrend').style.display = 'none';
        }

    } catch (error) {
        console.error('Error fetching new year stats:', error);
        // Show placeholder on error
        document.getElementById('newYearCard').style.display = 'block';
        document.getElementById('newYearMainChange').textContent = 'Zbieranie danych...';
        document.getElementById('newYearWeekday').textContent = 'Błąd pobierania danych';
        document.getElementById('newYearPeak').textContent = '';
        document.getElementById('newYearTrend').style.display = 'none';
    }
}

function renderDailyChart(dailyAverages) {
    const container = document.getElementById('dailyChart');
    if (!container) return;
    container.innerHTML = '';

    const days = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nd'];
    const values = days.map(d => dailyAverages[d] || 0);
    const maxVal = Math.max(...values, 1);

    const hasData = values.some(v => v > 0);
    if (!hasData) {
        container.innerHTML = `<div style="text-align: center; width: 100%; color: var(--text-muted);">Zbieranie danych...</div>`;
        return;
    }

    days.forEach((day, i) => {
        const val = values[i];
        const heightPercent = val > 0 ? (val / maxVal) * 100 : 5;

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%;';

        wrapper.innerHTML = `
                    <div style="
                        width: 100%;
                        max-width: 40px;
                        background: linear-gradient(180deg, var(--primary), var(--primary-dark));
                        border-radius: 5px 5px 0 0;
                        height: ${heightPercent}%;
                        min-height: 4px;
                        position: relative;
                        transition: all 0.3s;
                    ">
                        <span style="
                            position: absolute;
                            top: -20px;
                            left: 50%;
                            transform: translateX(-50%);
                            font-size: 0.7rem;
                            font-weight: 600;
                            color: var(--text-primary);
                        ">${val > 0 ? Math.round(val) : ''}</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 6px; font-weight: 500;">${day}</div>
                `;

        container.appendChild(wrapper);
    });
}

function renderHourlyChart(hourlyAverages) {
    const container = document.getElementById('hourlyChart');
    if (!container) return;
    container.innerHTML = '';

    const hours = [];
    for (let h = 6; h <= 22; h++) hours.push(h);

    const values = hours.map(h => hourlyAverages[h] || 0);
    const maxVal = Math.max(...values, 1);

    const hasData = values.some(v => v > 0);
    if (!hasData) {
        container.innerHTML = `<div style="text-align: center; padding: 50px; width: 100%; color: var(--text-muted); font-size: 0.9rem;">📊 Zbieranie danych...<br><span style="font-size: 0.75rem; opacity: 0.7;">Statystyki pojawią się po kilku dniach</span></div>`;
        return;
    }

    // Calculate thresholds for colors (33% and 66% of max)
    const lowThreshold = maxVal * 0.33;
    const highThreshold = maxVal * 0.66;

    hours.forEach((hour, i) => {
        const val = values[i];
        const heightPercent = val > 0 ? Math.max((val / maxVal) * 100, 8) : 5;

        const wrapper = document.createElement('div');
        wrapper.className = 'hour-bar-wrapper';

        // Determine color class based on value
        let barClass = 'hour-bar';
        if (val <= 0) {
            barClass += ' low';  // Green for 0 entries (best time!)
        } else if (val <= lowThreshold) {
            barClass += ' low';  // Green - few people
        } else if (val <= highThreshold) {
            barClass += ' medium';  // Yellow - medium
        } else {
            barClass += ' high';  // Red - many people
        }

        // Add hour label on the left edge of this slot - always show value (even 0)
        // For the last bar, also add the end label (23) inside the wrapper
        const isLast = i === hours.length - 1;
        wrapper.innerHTML = `
                    <div class="${barClass}" style="height: ${heightPercent}%;" title="${hour}:00-${hour + 1}:00 — średnio ${Math.round(val)} wejść">
                        <span class="hour-bar-value">${Math.round(val)}</span>
                    </div>
                    <div class="hour-label">${hour}</div>
                    ${isLast ? `<div class="hour-label-end">${hour + 1}</div>` : ''}
                `;

        container.appendChild(wrapper);
    });
}




function renderBestWorstTimes(bestTimes, worstTimes) {
    const bestContainer = document.getElementById('bestTimesList');
    const worstContainer = document.getElementById('worstTimesList');

    const medals = ['🥇', '🥈', '🥉'];

    if (bestContainer) {
        if (bestTimes.length === 0) {
            bestContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">Brak danych</div>';
        } else {
            bestContainer.innerHTML = bestTimes.map((t, i) => `
                        <div style="display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: rgba(16, 185, 129, 0.15); border-radius: 8px;">
                            <span style="font-size: 1rem;">${medals[i] || '⭐'}</span>
                            <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">${t.label}</span>
                            <span style="font-size: 0.7rem; color: var(--success); margin-left: auto;">~${Math.round(t.avg)} os.</span>
                        </div>
                    `).join('');
        }
    }

    if (worstContainer) {
        if (worstTimes.length === 0) {
            worstContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">Brak danych</div>';
        } else {
            worstContainer.innerHTML = worstTimes.map((t, i) => `
                        <div style="display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: rgba(239, 68, 68, 0.15); border-radius: 8px;">
                            <span style="font-size: 1rem;">${medals[i] || '💀'}</span>
                            <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">${t.label}</span>
                            <span style="font-size: 0.7rem; color: var(--danger); margin-left: auto;">~${Math.round(t.avg)} os.</span>
                        </div>
                    `).join('');
        }
    }
}

async function fetchWeeklyChart() {
    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/analytics/weekly${userParam}`);
        const data = await response.json();
        if (data.weeks) {
            renderWeeklyChart(data.weeks);
        }
    } catch (error) {
        console.error('Error fetching weekly chart:', error);
    }
}

function renderWeeklyChart(weeks) {
    const container = document.getElementById('weeklyChart');
    container.innerHTML = '';

    const maxCount = Math.max(...weeks.map(w => w.count), 1);

    weeks.forEach(week => {
        const wrapper = document.createElement('div');
        wrapper.className = 'chart-bar-wrapper';

        const heightPercent = (week.count / maxCount) * 100;
        const barHeight = Math.max(heightPercent, 3);

        // Parse dates for label (e.g., "9-15")
        const startDay = week.start_date ? new Date(week.start_date).getDate() : '';
        const endDay = week.end_date ? new Date(week.end_date).getDate() : '';
        const label = startDay && endDay ? `${startDay}-${endDay}` : week.week.split('-W')[1];

        wrapper.innerHTML = `
                    <div class="chart-bar" style="height: ${barHeight}%;">
                        <span class="chart-bar-value">${week.count}</span>
                    </div>
                    <div class="chart-bar-label">${label}</div>
                `;

        container.appendChild(wrapper);
    });
}

async function fetchYearlyHeatmap(year = null) {
    try {
        const targetYear = year || heatmapYear;
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/analytics/heatmap/${targetYear}${userParam}`);
        const data = await response.json();
        renderHeatmap(data, targetYear);
    } catch (error) {
        console.error('Error fetching heatmap:', error);
    }
}

function prevHeatmapYear() {
    if (heatmapYear > 2025) {
        heatmapYear--;
        document.getElementById('heatmapYear').textContent = heatmapYear;
        fetchYearlyHeatmap(heatmapYear);
    }
}

function nextHeatmapYear() {
    const maxYear = new Date().getFullYear() + 1;
    if (heatmapYear < maxYear) {
        heatmapYear++;
        document.getElementById('heatmapYear').textContent = heatmapYear;
        fetchYearlyHeatmap(heatmapYear);
    }
}

function renderHeatmap(data, year) {
    const container = document.getElementById('faceitHeatmap');
    if (!container) return;
    container.innerHTML = '';

    // Update year display
    document.getElementById('heatmapYear').textContent = year;

    const heatmapData = data.data || {};
    const monthNames = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];
    const workoutColor = '#10b981'; // Green for workout days
    const emptyColor = 'var(--bg-input)';

    const today = new Date();

    // Show all 12 months for the selected year
    for (let month = 0; month < 12; month++) {
        const monthDiv = document.createElement('div');
        monthDiv.style.cssText = 'flex: 1; min-width: 100px;';

        // Month label
        const label = document.createElement('div');
        label.textContent = monthNames[month];
        label.style.cssText = 'font-size: 0.7rem; color: var(--text-muted); margin-bottom: 8px; text-align: center;';
        monthDiv.appendChild(label);

        // Days grid (7 cols x ~5 rows)
        const grid = document.createElement('div');
        grid.style.cssText = 'display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;';

        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay();
        const startOffset = firstDay === 0 ? 6 : firstDay - 1; // Monday = 0

        // Empty cells for offset
        for (let i = 0; i < startOffset; i++) {
            const empty = document.createElement('div');
            empty.style.cssText = 'aspect-ratio: 1; width: 100%;';
            grid.appendChild(empty);
        }

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const hasWorkout = heatmapData[dateStr] && heatmapData[dateStr] > 0;
            const isFuture = new Date(year, month, day) > today;

            const cell = document.createElement('div');
            cell.style.cssText = `
                        aspect-ratio: 1; width: 100%;
                        background: ${hasWorkout ? workoutColor : emptyColor}; 
                        border-radius: 2px;
                        opacity: ${isFuture ? '0.3' : '1'};
                    `;
            if (hasWorkout) cell.title = `${day}.${month + 1}.${year} - trening`;
            grid.appendChild(cell);
        }

        monthDiv.appendChild(grid);
        container.appendChild(monthDiv);
    }
}


async function fetchComparison() {
    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/analytics/comparison${userParam}`);
        const data = await response.json();
        renderComparison(data);
    } catch (error) {
        console.error('Error fetching comparison:', error);
    }
}

function renderComparison(data) {
    document.getElementById('prevMonthName').textContent = data.previous.month_name;
    document.getElementById('prevMonthCount').textContent = data.previous.count;
    document.getElementById('currMonthName').textContent = data.current.month_name;
    document.getElementById('currMonthCount').textContent = data.current.count;

    const changeEl = document.getElementById('comparisonChange');
    const change = data.change_percent;

    if (change > 0) {
        changeEl.textContent = `+${change}%`;
        changeEl.className = 'comparison-change positive';
    } else if (change < 0) {
        changeEl.textContent = `${change}%`;
        changeEl.className = 'comparison-change negative';
    } else {
        changeEl.textContent = '0%';
        changeEl.className = 'comparison-change neutral';
    }
}

// ============================================
// EXPORT
// ============================================
async function downloadBackup() {
    try {
        const response = await fetch('/api/export/full');
        const data = await response.json();
        downloadJSON(data, 'gym_tracker_backup.json');
    } catch (error) {
        console.error('Error downloading backup:', error);
        alert('Błąd pobierania backupu');
    }
}

async function downloadWorkouts() {
    try {
        const response = await fetch('/api/export/workouts');
        const data = await response.json();
        downloadJSON(data, 'workouts_backup.json');
    } catch (error) {
        console.error('Error downloading workouts:', error);
        alert('Błąd pobierania treningów');
    }
}

function downloadJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// STRENGTH TAB
// ============================================
async function loadStrengthData() {
    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/strength${userParam}`);
        const data = await response.json();

        // Records
        renderRecords(data.records);

        // Populate dropdown
        populateProgressionSelect(data.body_parts_config);
    } catch (error) {
        console.error('Error loading strength data:', error);
    }
}

function renderRecords(records) {
    const container = document.getElementById('recordsGrid');

    if (!records || Object.keys(records).length === 0) {
        container.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 30px; color: var(--text-muted);">
                        Brak rekordów. Dodaj treningi z ciężarami!
                    </div>
                `;
        return;
    }

    container.innerHTML = '';

    for (const [part, record] of Object.entries(records)) {
        const card = document.createElement('div');
        card.className = 'record-card';
        card.style.cssText = `
                    background: var(--bg-input);
                    border-radius: 12px;
                    padding: 14px;
                    text-align: center;
                `;
        card.innerHTML = `
                    <div style="font-size: 0.85rem; font-weight: 600; color: var(--primary-light); margin-bottom: 6px; text-transform: uppercase;">${record.name}</div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary);">${record.kg} kg</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${record.sets}×${record.reps}</div>
                    <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 4px;">${record.date}</div>
                `;
        container.appendChild(card);
    }
}

function populateProgressionSelect(config) {
    const select = document.getElementById('progressionSelect');
    select.innerHTML = '<option value="">Wybierz partię ciała...</option>';

    for (const [key, part] of Object.entries(config || bodyPartsConfig)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = `${part.emoji} ${part.name}`;
        select.appendChild(option);
    }
}

async function fetchProgression(part) {
    if (!part) {
        document.getElementById('progressionChart').innerHTML = `
                    <div style="text-align: center; width: 100%; color: var(--text-muted); font-size: 0.85rem;">
                        Wybierz partię ciała aby zobaczyć progresję
                    </div>
                `;
        return;
    }

    try {
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/progression/${part}${userParam}`);
        const data = await response.json();
        renderProgression(data.data || []);
    } catch (error) {
        console.error('Error fetching progression:', error);
    }
}

function renderProgression(data) {
    const container = document.getElementById('progressionChart');

    if (!data || data.length === 0) {
        container.innerHTML = `
                    <div style="text-align: center; width: 100%; color: var(--text-muted); font-size: 0.85rem;">
                        Brak danych dla tej partii ciała
                    </div>
                `;
        return;
    }

    const maxKg = Math.max(...data.map(d => d.kg), 1);
    const chartHeight = 120;
    const chartWidth = container.offsetWidth || 300;
    const padding = 30;

    // Calculate points for line
    const points = data.map((entry, i) => {
        const x = padding + (i * ((chartWidth - padding * 2) / Math.max(data.length - 1, 1)));
        const y = chartHeight - padding - ((entry.kg / maxKg) * (chartHeight - padding * 2));
        return { x, y, kg: entry.kg, date: entry.date };
    });

    // Create SVG line chart
    const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

    // Create gradient area path
    const areaPath = pathData + ` L ${points[points.length - 1].x} ${chartHeight - padding} L ${points[0].x} ${chartHeight - padding} Z`;

    let svg = `
                <svg width="100%" height="${chartHeight + 30}" viewBox="0 0 ${chartWidth} ${chartHeight + 30}" style="overflow: visible;">
                    <defs>
                        <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color: var(--primary); stop-opacity: 0.3"/>
                            <stop offset="100%" style="stop-color: var(--primary); stop-opacity: 0"/>
                        </linearGradient>
                    </defs>
                    
                    <!-- Area fill -->
                    <path d="${areaPath}" fill="url(#lineGradient)" />
                    
                    <!-- Line -->
                    <path d="${pathData}" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                    
                    <!-- Points and labels -->
                    ${points.map(p => {
        const dateObj = new Date(p.date);
        const label = `${dateObj.getDate()}.${dateObj.getMonth() + 1}`;
        return `
                            <circle cx="${p.x}" cy="${p.y}" r="5" fill="var(--primary)" stroke="var(--bg-card)" stroke-width="2"/>
                            <text x="${p.x}" y="${p.y - 12}" text-anchor="middle" fill="var(--text-primary)" font-size="11" font-weight="600">${p.kg}</text>
                            <text x="${p.x}" y="${chartHeight + 15}" text-anchor="middle" fill="var(--text-muted)" font-size="10">${label}</text>
                        `;
    }).join('')}
                </svg>
            `;

    container.innerHTML = svg;
}

// ============================================
// START
// ============================================
init();
