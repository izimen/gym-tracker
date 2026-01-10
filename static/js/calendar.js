
// Safety wrapper for DOMPurify
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;
}

const MONTHS_PL = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'];

let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1; // 1-12
let selectedDate = null;
let selectedParts = [];
let workoutsData = {};
let bodyPartsConfig = {};

// Get stored user from localStorage (same as dashboard.js)
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
const currentUser = getStoredUser();

async function init() {
    await fetchDashboard();
    await fetchMonthWorkouts();
    renderCalendar();
    renderLegend();
}

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

function renderCalendar() {
    const container = document.getElementById('calendarDays');
    container.innerHTML = '';

    document.getElementById('currentMonth').textContent =
        `${MONTHS_PL[currentMonth - 1]} ${currentYear}`;

    // Get first day of month and total days
    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const totalDays = lastDay.getDate();

    // Monday = 0, Sunday = 6 (adjusted from JS's Sunday = 0)
    let startDay = firstDay.getDay() - 1;
    if (startDay < 0) startDay = 6;

    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    // Calculate previous month details
    const prevMonthLastDay = new Date(currentYear, currentMonth - 1, 0);
    const prevMonthDays = prevMonthLastDay.getDate();
    const prevMonth = currentMonth === 1 ? 12 : currentMonth - 1;
    const prevYear = currentMonth === 1 ? currentYear - 1 : currentYear;

    // Days from previous month (shown as transparent)
    for (let i = startDay - 1; i >= 0; i--) {
        const day = prevMonthDays - i;
        const cell = document.createElement('div');
        cell.className = 'day other-month';
        cell.innerHTML = `<div class="day-number">${day}</div>`;
        // Click to navigate to previous month
        cell.onclick = () => {
            currentMonth = prevMonth;
            currentYear = prevYear;
            fetchMonthWorkouts().then(renderCalendar);
        };
        container.appendChild(cell);
    }

    // Current month day cells
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

        cell.innerHTML = safeSanitize(`
            <div class="day-number">${day}</div>
            <div class="day-icons">${workout ? getWorkoutIcons(workout.body_parts) : ''}</div>
        `);

        cell.onclick = () => openModal(dateStr);
        container.appendChild(cell);
    }

    // Calculate how many cells we have so far
    const totalCells = startDay + totalDays;
    // We want to fill to complete rows of 7 (at least 6 rows = 42 cells)
    const targetCells = Math.ceil(totalCells / 7) * 7;
    const nextMonthDays = targetCells - totalCells;

    // Calculate next month details
    const nextMonth = currentMonth === 12 ? 1 : currentMonth + 1;
    const nextYear = currentMonth === 12 ? currentYear + 1 : currentYear;

    // Days from next month (shown as transparent)
    for (let day = 1; day <= nextMonthDays; day++) {
        const cell = document.createElement('div');
        cell.className = 'day other-month';
        cell.innerHTML = safeSanitize(`<div class="day-number">${day}</div>`);
        // Click to navigate to next month
        cell.onclick = () => {
            currentMonth = nextMonth;
            currentYear = nextYear;
            fetchMonthWorkouts().then(renderCalendar);
        };
        container.appendChild(cell);
    }
}

function getWorkoutIcons(parts) {
    if (!parts || !parts.length) return '';
    return parts.map(p => `<span>${bodyPartsConfig[p]?.emoji || ''}</span>`).join('');
}

function renderLegend() {
    const container = document.getElementById('legend');
    container.innerHTML = '';

    for (const [key, config] of Object.entries(bodyPartsConfig)) {
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = safeSanitize(`<span>${config.emoji}</span><span>${config.name}</span>`);
        container.appendChild(item);
    }
}

function renderBodyPartsGrid() {
    const container = document.getElementById('bodyPartsGrid');
    container.innerHTML = '';

    for (const [key, config] of Object.entries(bodyPartsConfig)) {
        const btn = document.createElement('button');
        btn.className = 'body-part-btn' + (selectedParts.includes(key) ? ' selected' : '');
        btn.innerHTML = safeSanitize(`
            <span class="body-part-emoji">${config.emoji}</span>
            <span class="body-part-name">${config.name}</span>
        `);
        btn.onclick = () => togglePart(key);
        container.appendChild(btn);
    }
}

function togglePart(part) {
    const idx = selectedParts.indexOf(part);
    if (idx > -1) {
        selectedParts.splice(idx, 1);
    } else {
        selectedParts.push(part);
    }
    renderBodyPartsGrid();
}

function openModal(dateStr) {
    selectedDate = dateStr;
    const workout = workoutsData[dateStr];
    selectedParts = workout ? [...workout.body_parts] : [];

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

function prevMonth() {
    currentMonth--;
    if (currentMonth < 1) {
        currentMonth = 12;
        currentYear--;
    }
    fetchMonthWorkouts().then(renderCalendar);
}

function nextMonth() {
    currentMonth++;
    if (currentMonth > 12) {
        currentMonth = 1;
        currentYear++;
    }
    fetchMonthWorkouts().then(renderCalendar);
}

// =============================================================================
// ANALYTICS FUNCTIONS
// =============================================================================

let analyticsLoaded = false;

function showCalendar() {
    document.getElementById('calendarSection').classList.remove('hide');
    document.getElementById('analyticsSection').classList.remove('show');
    document.getElementById('toggleCalendar').classList.add('active');
    document.getElementById('toggleAnalytics').classList.remove('active');
}

function showAnalytics() {
    document.getElementById('calendarSection').classList.add('hide');
    document.getElementById('analyticsSection').classList.add('show');
    document.getElementById('toggleCalendar').classList.remove('active');
    document.getElementById('toggleAnalytics').classList.add('active');

    if (!analyticsLoaded) {
        loadAnalytics();
        analyticsLoaded = true;
    }
}

async function loadAnalytics() {
    await Promise.all([
        fetchWeeklyChart(),
        fetchYearlyHeatmap(),
        fetchComparison()
    ]);
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
    if (!container) return;
    container.innerHTML = '';

    const maxCount = Math.max(...weeks.map(w => w.count), 1);

    weeks.forEach((week, index) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'chart-bar-wrapper';

        const heightPercent = (week.count / maxCount) * 100;
        const barHeight = Math.max(heightPercent, 3); // Minimum 3% height

        // Get week label (just week number)
        const weekNum = week.week.split('-W')[1];

        wrapper.innerHTML = `
            <div class="chart-bar" style="height: ${barHeight}%;">
                <span class="chart-bar-value">${week.count}</span>
            </div>
            <div class="chart-bar-label">W${weekNum}</div>
        `;

        container.appendChild(wrapper);
    });
}

async function fetchYearlyHeatmap() {
    try {
        const year = new Date().getFullYear();
        const userParam = currentUser ? `?user_id=${currentUser.user_id}` : '';
        const response = await fetch(`/api/analytics/heatmap/${year}${userParam}`);
        const data = await response.json();
        renderHeatmap(data);
    } catch (error) {
        console.error('Error fetching heatmap:', error);
    }
}

function renderHeatmap(data) {
    const container = document.getElementById('yearlyHeatmap');
    const monthsContainer = document.getElementById('heatmapMonths');
    if (!container || !monthsContainer) return;

    container.innerHTML = '';
    monthsContainer.innerHTML = '';

    const year = data.year;
    const heatmapData = data.data || {};

    // Render month labels
    const monthNames = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];
    monthNames.forEach(month => {
        const span = document.createElement('span');
        span.textContent = month;
        monthsContainer.appendChild(span);
    });

    // Generate all days of the year
    const startDate = new Date(year, 0, 1);
    const endDate = new Date(year, 11, 31);

    // Adjust to start from Monday
    let currentDate = new Date(startDate);
    const startDayOfWeek = currentDate.getDay(); // 0 = Sunday
    const mondayOffset = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;

    // Create 7 rows (one for each day of week)
    const rows = [[], [], [], [], [], [], []];

    // Fill in empty cells before Jan 1
    for (let i = 0; i < mondayOffset; i++) {
        rows[i].push(null);
    }

    // Fill in all days
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    while (currentDate <= endDate) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const dayOfWeek = currentDate.getDay();
        const rowIndex = dayOfWeek === 0 ? 6 : dayOfWeek - 1;

        rows[rowIndex].push({
            date: dateStr,
            count: heatmapData[dateStr] || 0,
            isFuture: currentDate > today
        });

        currentDate.setDate(currentDate.getDate() + 1);
    }

    // Render the grid column by column
    const numWeeks = Math.max(...rows.map(r => r.length));

    for (let week = 0; week < numWeeks; week++) {
        for (let day = 0; day < 7; day++) {
            const cell = document.createElement('div');
            cell.className = 'heatmap-day';

            const dayData = rows[day][week];

            if (dayData === null || dayData === undefined) {
                cell.style.visibility = 'hidden';
            } else if (dayData.isFuture) {
                cell.style.opacity = '0.3';
            } else if (dayData.count > 0) {
                // Level based on count
                let level = 1;
                if (dayData.count >= 2) level = 2;
                if (dayData.count >= 4) level = 3;
                if (dayData.count >= 6) level = 4;
                cell.classList.add(`level-${level}`);
                cell.title = `${dayData.date}: ${dayData.count} partii ciała`;
            }

            container.appendChild(cell);
        }
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
    const prevMonthNameEl = document.getElementById('prevMonthName');
    if (prevMonthNameEl) {
        prevMonthNameEl.textContent = data.previous.month_name;
        document.getElementById('prevMonthCount').textContent = data.previous.count;

        // Current month
        document.getElementById('currMonthName').textContent = data.current.month_name;
        document.getElementById('currMonthCount').textContent = data.current.count;

        // Change percentage
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
}

// =============================================================================
// EXPORT / BACKUP FUNCTIONS
// =============================================================================

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
// EVENT LISTENERS (Strict CSP)
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Navigation (prev/next month)
    const btnPrevMonth = document.getElementById('btnPrevMonth');
    if (btnPrevMonth) btnPrevMonth.addEventListener('click', prevMonth);

    const btnNextMonth = document.getElementById('btnNextMonth');
    if (btnNextMonth) btnNextMonth.addEventListener('click', nextMonth);

    // View Toggles
    const toggleCalendar = document.getElementById('toggleCalendar');
    if (toggleCalendar) toggleCalendar.addEventListener('click', showCalendar);

    const toggleAnalytics = document.getElementById('toggleAnalytics');
    if (toggleAnalytics) toggleAnalytics.addEventListener('click', showAnalytics);

    // Modal Actions
    const btnCloseModal = document.getElementById('btnCloseModal');
    if (btnCloseModal) btnCloseModal.addEventListener('click', closeModal);

    const btnSaveWorkout = document.getElementById('btnSaveWorkout');
    if (btnSaveWorkout) btnSaveWorkout.addEventListener('click', saveWorkout);

    const btnDeleteWorkout = document.getElementById('deleteBtn');
    if (btnDeleteWorkout) btnDeleteWorkout.addEventListener('click', deleteWorkout);

    // Modal overlay close
    const modalOverlay = document.getElementById('modalOverlay');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target.id === 'modalOverlay') closeModal();
        });
    }

    // Backup buttons
    const btnBackup = document.getElementById('btnBackup');
    if (btnBackup) btnBackup.addEventListener('click', downloadBackup);

    const btnBackupWorkouts = document.getElementById('btnBackupWorkouts');
    if (btnBackupWorkouts) btnBackupWorkouts.addEventListener('click', downloadWorkouts);

    // Initialize app
    init();
});
