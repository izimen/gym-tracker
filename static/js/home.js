// Safety wrapper for DOMPurify
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;
}

let refreshCooldown = false;
let cooldownTimer = null;
const REFRESH_COOLDOWN_MS = 30000;

function updateUI(data) {
    const entriesCount = document.getElementById('entriesCount');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const updateTime = document.getElementById('updateTime');
    const errorMessage = document.getElementById('errorMessage');

    if (data.status === 'ok') {
        entriesCount.textContent = data.entries_today;
        statusDot.className = 'status-dot';
        statusText.textContent = 'Połączono';

        if (data.last_updated) {
            const time = data.last_updated.split(' ')[1];
            updateTime.textContent = 'Aktualizacja: ' + time;
        }
        errorMessage.style.display = 'none';
    } else if (data.status === 'error') {
        statusDot.className = 'status-dot error';
        statusText.textContent = 'Błąd';
        if (data.error) {
            errorMessage.textContent = data.error;
            errorMessage.style.display = 'block';
        }
    } else {
        statusDot.className = 'status-dot loading';
        statusText.textContent = 'Ładowanie...';
    }
}

function updateStats(stats) {
    if (stats.week_ago !== null) {
        document.getElementById('weekAgoValue').textContent = stats.week_ago;
    }
    if (stats.average_for_weekday !== null && stats.average_for_weekday > 0) {
        document.getElementById('averageValue').textContent = Math.round(stats.average_for_weekday);
    }
}

async function fetchData() {
    try {
        const response = await fetch('/api/occupancy');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        updateUI({ status: 'error', error: 'Brak połączenia' });
    }
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        updateStats(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function fetchWorkoutStats() {
    try {
        const response = await fetch('/api/workouts/dashboard');
        const data = await response.json();

        document.getElementById('workoutWeekly').textContent = data.weekly_count || 0;
        document.getElementById('workoutMonthly').textContent = data.monthly_count || 0;

        if (data.most_trained) {
            document.getElementById('mostTrainedEmoji').textContent = data.most_trained.emoji;
            document.getElementById('mostTrainedValue').textContent =
                `${data.most_trained.name} (${data.most_trained.count}x)`;
        }

        const neglectedCard = document.getElementById('neglectedCard');
        const tipsCard = document.getElementById('tipsCard');
        const neglectedList = document.getElementById('neglectedList');

        if (data.neglected_parts && data.neglected_parts.length > 0) {
            neglectedCard.style.display = 'block';
            tipsCard.style.display = 'none';
            neglectedList.innerHTML = safeSanitize(data.neglected_parts
                .slice(0, 4)
                .map(p => `<span class="neglected-item">${p.emoji} ${p.name} (${p.count}x)</span>`)
                .join(''));
        } else {
            neglectedCard.style.display = 'none';
            tipsCard.style.display = 'block';
        }
    } catch (error) {
        console.error('Error fetching workout stats:', error);
    }
}

function startCooldown(durationMs) {
    const btn = document.getElementById('refreshBtn');
    refreshCooldown = true;
    btn.classList.add('cooldown');

    let remaining = Math.ceil(durationMs / 1000);
    btn.innerHTML = `<span class="refresh-icon">⏳</span> ${remaining}s`;

    cooldownTimer = setInterval(() => {
        remaining--;
        if (remaining <= 0) {
            clearInterval(cooldownTimer);
            refreshCooldown = false;
            btn.classList.remove('cooldown');
            btn.innerHTML = '<span class="refresh-icon">🔄</span> Odśwież';
        } else {
            btn.innerHTML = `<span class="refresh-icon">⏳</span> ${remaining}s`;
        }
    }, 1000);
}

async function refreshData() {
    if (refreshCooldown) return;

    const btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');

    try {
        const response = await fetch('/api/refresh');
        const data = await response.json();

        if (response.status === 429 || data.rate_limited) {
            startCooldown((data.retry_after || 30) * 1000);
        } else {
            updateUI(data);
            fetchStats();
            startCooldown(REFRESH_COOLDOWN_MS);
        }
    } catch (error) {
        console.error('Error:', error);
    } finally {
        btn.classList.remove('loading');
    }
}


async function fetchBestHours() {
    try {
        const response = await fetch('/api/analytics/best-hours');
        const data = await response.json();
        renderBestHoursChart(data);
    } catch (error) {
        console.error('Error fetching best hours:', error);
    }
}

function renderBestHoursChart(data) {
    const container = document.getElementById('hourlyChart');
    const summaryContainer = document.getElementById('bestHoursSummary');

    const averages = data.hourly_averages || {};
    const bestHours = data.best_hours || [];
    const bestHourNums = bestHours.map(h => h.hour);

    // Check if we have real data
    const hasData = Object.values(averages).some(v => v > 0);

    if (!hasData) {
        container.innerHTML = safeSanitize(`
            <div class="no-data-message">
                📊 Zbieranie danych... Analiza będzie dostępna po kilku dniach.
            </div>
        `);
        summaryContainer.innerHTML = '';
        return;
    }

    // Find max value for scaling
    const maxVal = Math.max(...Object.values(averages));

    // Generate bars (6-23)
    let barsHtml = '';
    for (let h = 6; h <= 23; h++) {
        const val = averages[h] || 0; // Default to 0 if no data
        const heightPct = maxVal > 0 ? (val / maxVal * 100) : 0;

        // Determine color class
        let colorClass = 'low';
        if (val > 15) colorClass = 'high';
        else if (val > 8) colorClass = 'medium';
        if (val === 0) colorClass = 'no-data';

        const isBest = bestHourNums.includes(h);
        if (isBest) colorClass = 'best';

        // Tooltip text
        const tooltip = `Godzina ${h}:00 - Średnio ${Math.round(val)} osób`;

        barsHtml += `
            <div class="hour-bar-wrapper">
                <div class="hour-bar ${colorClass}" 
                     style="height: ${Math.max(4, heightPct)}%;"
                     title="${tooltip}">
                     ${val > 0 ? `<div class="hour-bar-value">${Math.round(val)}</div>` : ''}
                </div>
                <div class="hour-label">${h}</div>
            </div>
        `;
    }

    container.innerHTML = safeSanitize(barsHtml);

    // Render Summary Badges
    if (bestHours.length > 0) {
        const badgesHtml = bestHours.map((h, index) => {
            const medal = index === 0 ? '🥇' : (index === 1 ? '🥈' : '🥉');
            return `
                <div class="best-hour-badge">
                    <span class="medal">${medal}</span>
                    <span>${h.hour}:00 - ${h.hour + 1}:00</span>
                </div>
            `;
        }).join('');

        summaryContainer.innerHTML = safeSanitize(badgesHtml);
    }
}

// MAIN INIT
document.addEventListener('DOMContentLoaded', () => {
    // Attach Event Listeners
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    // Init data load
    fetchData();
    fetchStats();
    fetchWorkoutStats();
    fetchBestHours();

    // Intervals
    setInterval(fetchData, 30000);
    setInterval(fetchStats, 60000);
    setInterval(fetchWorkoutStats, 120000);
});
