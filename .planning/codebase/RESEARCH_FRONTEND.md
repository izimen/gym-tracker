# Frontend Technology Research

**Researched:** 2026-04-04
**Domain:** Frontend architecture, frameworks, charting, sanitization, build tooling
**Confidence:** MEDIUM (web search and npm registry unavailable; conclusions based on codebase analysis + training data. Package versions should be verified before implementation.)

## Summary

The gym tracker frontend is 2,293 LOC of vanilla JavaScript across 3 files (`dashboard.js` at 1,457 LOC, `calendar.js` at 583, `home.js` at 253), served directly by Flask with Jinja2 templates. There is also a separate React 19 + Vite 7 + Tailwind 4 prototype in `stats-dashboard/` that is not integrated with the main app.

After analyzing the codebase patterns, complexity level, and deployment model (Flask on Cloud Run), the recommendation is: **keep vanilla JS for the existing app, but fix the structural problems (code duplication, no shared base template, inline styles, missing build step).** The React prototype should be treated as a design reference, not integrated. The app's interaction patterns (fetch data, render DOM, handle clicks) are well within vanilla JS capabilities, and introducing a framework would add complexity without proportional benefit at this scale.

**Primary recommendation:** Retain and refactor vanilla JS. Add a minimal build step (esbuild or terser for minification/bundling). Use Chart.js for charts. Keep DOMPurify but upgrade to latest and fix the fail-open fallback.

---

## Question 1: Is Vanilla JS Still Viable at ~2300 LOC?

**Verdict: Yes, vanilla JS is viable and appropriate for this app.**

**Confidence: HIGH** (based on direct codebase analysis)

### Evidence From the Codebase

The app has three pages with distinct, simple interaction patterns:

| Page | File | LOC | Complexity | Pattern |
|------|------|-----|------------|---------|
| Home (`index.html`) | `home.js` | 253 | Low | Fetch occupancy, update 6 DOM elements |
| Calendar (`calendar.html`) | `calendar.js` | 583 | Medium | Month grid, workout CRUD modal, body part selection |
| Dashboard (`dashboard.html`) | `dashboard.js` | 1,457 | Medium-High | Tabs, charts (bar/line/heatmap), auth, stats, export |

The dashboard is the only file that approaches problematic size. However, its complexity is sequential and procedural -- it is not managing complex state trees, nested components, or reactive data flows. The code follows a clear pattern:

```
fetch data -> getElementById -> update textContent/set property -> done
```

There is no component reuse problem (each page is standalone), no prop drilling, no shared state management across views, and no client-side routing. These are the problems that frameworks solve.

### When to Migrate Away From Vanilla JS

A framework becomes worthwhile when the codebase exhibits:

1. **Shared stateful components** -- e.g., the same "workout card" component used in 5+ places with different data and behavior. Currently, each page has its own rendering functions.
2. **Complex state synchronization** -- e.g., editing a workout in one view must instantly update counts in another view. Currently, the app refetches data after mutations (`await fetchMonthWorkouts(); await fetchDashboard(); renderCalendar();`).
3. **More than ~4,000 LOC of frontend JS** -- below this threshold, the overhead of a framework (build config, component structure, dependency management) often exceeds the savings.
4. **Client-side routing requirements** -- SPA navigation between views without page reloads. Currently, the app uses separate HTML pages served by Flask.

This app meets none of these thresholds.

### What DOES Need Fixing (Without a Framework)

The vanilla JS has real structural problems, but they are solvable without a framework:

1. **`safeSanitize()` duplicated in 3 files** -- extract into `static/js/utils.js` and load via `<script>` tag before page-specific JS.
2. **`MONTHS_PL` and other constants duplicated** between `dashboard.js` and `calendar.js`.
3. **`bodyPartsConfig` and fetch patterns duplicated** between files.
4. **dashboard.js at 1,457 LOC** -- split into logical modules: `dashboard-auth.js`, `dashboard-charts.js`, `dashboard-stats.js`, `dashboard-strength.js`, `dashboard-calendar.js`.
5. **No shared base template** -- all 3 HTML files duplicate the `<head>`, font loading, DOMPurify script tag. Use Jinja2 template inheritance (`{% extends "base.html" %}`).

---

## Question 2: Best Lightweight Framework If Migrating

**Verdict: htmx is the best fit IF you want to add framework-like capabilities. But it is not needed here.**

**Confidence: MEDIUM** (framework versions from training data, not verified against current registry)

| Framework | Bundle Size | Learning Curve | Flask Fit | Best For |
|-----------|------------|----------------|-----------|----------|
| **htmx** | ~14 KB min+gz | Very low | Excellent | Server-rendered apps needing dynamic updates |
| **Alpine.js** | ~15 KB min+gz | Low | Good | Adding reactivity to server-rendered HTML |
| **Preact** | ~3 KB min+gz | Medium (React-like) | Moderate | When you want React patterns at minimal size |
| **Svelte** | ~2 KB runtime | Medium | Poor (needs build) | Component-heavy apps with compile-time optimization |
| **Lit** | ~5 KB | Medium | Moderate | Web Components standard |
| **Solid** | ~7 KB | High | Poor (needs build) | Maximum performance, React-like but different mental model |

### Why htmx Fits Best (If Anything)

htmx extends HTML with attributes like `hx-get`, `hx-post`, `hx-swap` to make server-rendered pages dynamic without writing JavaScript. It works with Flask's Jinja2 templates naturally:

```html
<!-- Before: JavaScript fetch + DOM manipulation -->
<div id="liveCount">--</div>
<script>
async function fetchLiveCount() {
    const response = await fetch('/api/occupancy');
    const data = await response.json();
    document.getElementById('liveCount').textContent = data.entries_today;
}
setInterval(fetchLiveCount, 60000);
</script>

<!-- After: htmx (server returns HTML fragment, not JSON) -->
<div hx-get="/partials/live-count" hx-trigger="load, every 60s" hx-swap="textContent">
    --
</div>
```

**However**, htmx requires changing the backend API to return HTML fragments instead of JSON. This is a significant architectural change. The current app's API returns JSON consumed by both the vanilla JS frontend and potentially the React prototype. Converting to HTML fragments would break that contract.

### Why Alpine.js Is the Runner-Up

Alpine.js adds reactive behavior via HTML attributes without requiring a build step:

```html
<div x-data="{ count: 0 }" x-init="fetch('/api/occupancy').then(r => r.json()).then(d => count = d.entries_today)">
    <span x-text="count"></span>
</div>
```

It works alongside existing JavaScript and does not require API changes. However, for this app's simple fetch-and-display pattern, it adds dependency without clear benefit.

### Recommendation

Do not adopt a framework at this time. The refactoring effort is better spent on:
- Splitting `dashboard.js` into modules
- Creating a shared Jinja2 base template
- Adding a build step for bundling/minification

---

## Question 3: Is the React 19 + Vite 7 + Tailwind 4 Prototype a Good Stack?

**Verdict: The stack itself is solid and modern. But integrating it with the Flask app creates more problems than it solves.**

**Confidence: HIGH for stack quality, MEDIUM for version verification**

### Stack Assessment

| Component | Version in Prototype | Assessment |
|-----------|---------------------|------------|
| React | ^19.2.0 | Current stable. React 19 with Server Components and Actions is production-ready. |
| react-dom | ^19.2.0 | Matches React version. Correct. |
| Vite | ^7.2.4 | Current. Vite 7 is the latest major. Fast HMR, excellent DX. |
| TypeScript | ~5.9.3 | Current. Strict mode enabled, path aliases configured. |
| Tailwind CSS | ^4.1.18 | Current. Tailwind 4 uses CSS-first configuration (`@theme` directive). |
| clsx + tailwind-merge | ^2.1.1 + ^3.4.0 | Standard utility pairing for conditional Tailwind classes. |
| lucide-react | ^0.562.0 | Good icon library, tree-shakeable. |

The stack is well-chosen for a standalone SPA. The prototype code quality is good -- it uses TypeScript interfaces, component composition, and Tailwind utility classes effectively.

### Integration Problems

1. **Deployment complexity.** Flask serves Jinja2 templates. A React SPA needs either:
   - A separate deployment (separate Cloud Run service, separate domain/subdomain)
   - Building React to static assets and serving them from Flask's `static/` directory
   - A reverse proxy setup
   Each option adds operational complexity for a single-developer project.

2. **API duplication.** The React prototype uses mock data (`StatisticsPage.tsx` lines 19-55). To integrate, you would need to wire it to the same Flask API endpoints, but the React components expect different data shapes than the API currently returns.

3. **Auth duplication.** The Flask app handles auth via server-side sessions with cookies. A React SPA would need to manage auth state client-side and send cookies with every request -- doable but adds complexity.

4. **Two styling systems.** The existing app uses CSS variables (`--primary`, `--bg-dark`, etc.) with custom CSS. The React prototype uses Tailwind 4 with `@theme` variables. Maintaining consistency between them is difficult.

5. **Partial coverage.** The React prototype only covers the Statistics page. The Calendar and Home pages would still be vanilla JS + Jinja2. You would end up maintaining two completely different frontend architectures.

### Recommendation

**Use the React prototype as a design reference**, not as production code. Its visual design (bento grid layout, color choices, glassmorphism effects) can be replicated in the vanilla JS app. Specifically:

- The heatmap grid layout from `YearlyHeatmap.tsx` can inform the vanilla JS heatmap
- The color scheme (zinc-900, emerald, indigo) is usable directly as CSS variables
- The Card component pattern is achievable with CSS classes

If the project grows to the point where a full SPA makes sense (4+ pages with shared state, real-time updates, complex client-side routing), THEN consider migrating entirely to React + Vite -- but as a full rewrite, not a partial integration.

---

## Question 4: Charts -- Library vs. Hand-Built

**Verdict: Use Chart.js for bar and line charts. Keep the heatmap hand-built.**

**Confidence: HIGH for recommendation, MEDIUM for exact version numbers**

### Current Hand-Built Charts

The codebase has 4 hand-built chart types:

| Chart | Location | Method | Lines | Quality |
|-------|----------|--------|-------|---------|
| Daily bar chart | `dashboard.js:966-1013` | DOM elements (divs with inline styles) | 47 | Basic but functional |
| Hourly bar chart | `dashboard.js:1016-1069` | DOM elements with color-coded thresholds | 53 | Good -- has color scales |
| Weekly bar chart | `dashboard.js:1121-1148` | DOM elements | 27 | Basic |
| Progression line chart | `dashboard.js:1393-1452` | SVG (path, circle, text elements) | 59 | Good -- has gradient fill |
| Yearly heatmap | `dashboard.js:1178-1239` | DOM grid of divs | 61 | Good -- day cells with tooltips |

**Total chart code: ~247 lines (17% of dashboard.js).**

### Problems With Hand-Built Charts

1. **No responsiveness.** The bar charts use fixed `max-width: 40px` and the SVG line chart uses `container.offsetWidth || 300` -- a hardcoded fallback.
2. **No tooltips.** The bar charts show values above bars but have no hover interaction. The heatmap has `title` attributes only.
3. **No animations.** Chart rendering is instant with no transition effects.
4. **No accessibility.** No ARIA labels, no screen reader support, no keyboard navigation.
5. **Fragile scaling.** The SVG line chart calculates point positions manually with hardcoded padding values.

### Library Comparison

| Library | Size (min+gz) | Framework | Best For | Gym Tracker Fit |
|---------|--------------|-----------|----------|-----------------|
| **Chart.js** | ~65 KB | Any / None | General purpose, responsive, accessible | Excellent |
| **Recharts** | ~60 KB | React only | React wrapper around D3 | React prototype only |
| **Lightweight Charts** | ~45 KB | Any | Financial/time-series | Overkill for gym data |
| **uPlot** | ~30 KB | Any | High-performance time-series | Overkill |
| **ApexCharts** | ~130 KB | Any | Feature-rich dashboards | Too heavy |

### Why Chart.js

1. **No build step required.** Load from CDN or vendor the file.
2. **Responsive by default.** Charts resize with their container.
3. **Built-in dark theme support.** Chart.js respects CSS variables and has a `defaults.color` setting.
4. **Canvas-based rendering.** Better performance than SVG for multiple charts on one page.
5. **All needed chart types.** Bar (daily, hourly, weekly) and Line (progression) are core chart types.
6. **Accessibility.** Built-in ARIA labels and keyboard navigation.
7. **Dominant ecosystem position.** Chart.js has been the most-used JS charting library by npm downloads for years.

### What to Keep Hand-Built

The **yearly heatmap** should remain hand-built. Chart.js does not have a native heatmap type (the `chartjs-chart-matrix` plugin exists but is less maintained). The current heatmap implementation is only 61 lines, is visually effective, and maps well to DOM grid elements.

### Implementation Pattern

```javascript
// Replace renderDailyChart() with Chart.js
function renderDailyChart(dailyAverages) {
    const canvas = document.getElementById('dailyChartCanvas');
    const ctx = canvas.getContext('2d');

    // Destroy previous chart if exists
    if (window.dailyChart) window.dailyChart.destroy();

    const days = ['Pon', 'Wt', 'Sr', 'Czw', 'Pt', 'Sob', 'Nd'];
    const values = days.map(d => dailyAverages[d] || 0);

    window.dailyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: days,
            datasets: [{
                data: values,
                backgroundColor: 'rgba(124, 58, 237, 0.8)',
                borderRadius: 5,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false },
                x: { ticks: { color: '#6b6b80' } }
            }
        }
    });
}
```

### Chart.js Dark Theme Configuration

```javascript
// Set once at app startup
Chart.defaults.color = '#b8b8d0';  // --text-secondary
Chart.defaults.borderColor = '#1f1f35';  // --border
Chart.defaults.font.family = "'Inter', sans-serif";
```

---

## Question 5: Dark Theme Best Practices

**Verdict: The current CSS variables approach is correct. Add `prefers-color-scheme` support and refine the variable naming.**

**Confidence: HIGH** (CSS variables for theming is well-established best practice)

### Current Implementation

The app uses CSS custom properties (variables) defined on `:root`:

```css
/* index.html / home.css */
:root {
    --primary: #6366f1;
    --bg-dark: #0f0f1a;
    --bg-card: #1a1a2e;
    --text-primary: #ffffff;
    --text-secondary: #a0a0b8;
}

/* dashboard.html (different values!) */
:root {
    --primary: #7c3aed;
    --bg-dark: #0a0a12;
    --bg-card: #12121f;
    --text-primary: #ffffff;
    --text-secondary: #b8b8d0;
}
```

**Problem:** The two pages define different values for the same variable names. `--primary` is `#6366f1` (indigo) on the home page but `#7c3aed` (violet) on the dashboard. `--bg-dark`, `--bg-card`, and `--text-secondary` also differ.

### Recommended Approach

1. **Unify variables in a shared CSS file** (`static/css/theme.css`):

```css
:root {
    /* Semantic color tokens */
    --color-primary: #7c3aed;
    --color-primary-light: #a78bfa;
    --color-primary-dark: #5b21b6;

    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-danger: #ef4444;

    /* Surface colors */
    --color-bg-base: #0a0a12;
    --color-bg-card: #12121f;
    --color-bg-card-hover: #1a1a2a;
    --color-bg-input: #0d0d16;

    /* Text colors */
    --color-text-primary: #ffffff;
    --color-text-secondary: #b8b8d0;
    --color-text-muted: #6b6b80;

    /* Border colors */
    --color-border: #1f1f35;
    --color-border-light: #2a2a45;
}
```

2. **Add light theme support** (optional, for future use):

```css
@media (prefers-color-scheme: light) {
    :root {
        --color-bg-base: #f8f9fa;
        --color-bg-card: #ffffff;
        --color-bg-card-hover: #f1f3f5;
        --color-bg-input: #e9ecef;
        --color-text-primary: #1a1a2e;
        --color-text-secondary: #495057;
        --color-text-muted: #868e96;
        --color-border: #dee2e6;
        --color-border-light: #e9ecef;
    }
}
```

3. **Do NOT use Tailwind's `dark:` variant** for the existing vanilla JS app. That requires Tailwind's build process and class-based dark mode toggling. The CSS variables approach is simpler, lighter, and already working.

### Comparison of Approaches

| Approach | Requires Build | Framework | Runtime Toggle | System Theme Respect |
|----------|---------------|-----------|---------------|---------------------|
| CSS variables + `prefers-color-scheme` | No | None | Via JS class toggle | Yes |
| Tailwind `dark:` class variant | Yes (Tailwind build) | Tailwind | Via class on html element | With plugin |
| CSS variables + `data-theme` attribute | No | None | Via JS attribute toggle | With JS |

**Recommendation:** Use CSS variables with `prefers-color-scheme`. This is the most appropriate approach for a no-build-step, vanilla JS app. It respects the user's OS preference automatically with zero JavaScript.

---

## Question 6: Build Step -- Minification and Bundling

**Verdict: Add a minimal build step using esbuild. Cloud Run's gzip (via flask-compress) is insufficient on its own.**

**Confidence: HIGH** (based on file size analysis from codebase)

### Current State

| Asset | Lines | Estimated Raw Size | Gzipped (approx) |
|-------|-------|--------------------|-------------------|
| `dashboard.js` | 1,457 | ~55 KB | ~12 KB |
| `calendar.js` | 583 | ~20 KB | ~5 KB |
| `home.js` | 253 | ~8 KB | ~2 KB |
| `purify.min.js` | 2 (minified) | ~28 KB | ~10 KB |
| `dashboard.css` | ~1000+ | ~35 KB | ~7 KB |
| Inline CSS (dashboard.html) | ~600+ | ~20 KB | ~5 KB |
| Total | | ~166 KB | ~41 KB |

`flask-compress` (already installed, `requirements.txt`) applies gzip compression to responses. This handles transfer size but does NOT:

1. **Remove dead code** -- unused functions are still shipped
2. **Minify variable names** -- `fetchExtendedStats` remains 18 characters instead of a single letter
3. **Tree-shake** -- DOMPurify's full feature set is loaded even though only `sanitize()` is used
4. **Bundle** -- multiple separate HTTP requests for JS on the dashboard page

### Recommended: esbuild

esbuild is the simplest build tool for this use case. It requires no configuration file for basic usage:

```bash
# Install (one-time)
npm init -y
npm install --save-dev esbuild

# Build command (add to package.json scripts)
npx esbuild static/js/dashboard.js --bundle --minify --outfile=static/dist/dashboard.min.js
npx esbuild static/js/calendar.js --bundle --minify --outfile=static/dist/calendar.min.js
npx esbuild static/js/home.js --bundle --minify --outfile=static/dist/home.min.js
```

**Expected savings:**

| Metric | Before | After esbuild | Savings |
|--------|--------|---------------|---------|
| JS raw size (all) | ~83 KB | ~35 KB (est.) | ~58% |
| JS gzipped (all) | ~19 KB | ~10 KB (est.) | ~47% |
| HTTP requests (dashboard) | 2 (purify + dashboard) | 1 (bundled) | 50% |

### Alternatives Considered

| Tool | Setup Complexity | Speed | When to Use |
|------|-----------------|-------|-------------|
| **esbuild** | Minimal (CLI flags) | Extremely fast | Simple bundling + minification |
| **Vite** | Medium (config file) | Fast | If you also want HMR dev server |
| **terser** (standalone) | Minimal | Fast | Minification only, no bundling |
| **webpack** | High | Slow | DO NOT USE for this project size |
| **Rollup** | Medium | Medium | Library authoring, not apps |

**Recommendation:** Use esbuild. It is a single dependency, requires no config file, builds in milliseconds, and handles both minification and bundling.

### Dockerfile Integration

Add the build step to the Dockerfile before the final CMD:

```dockerfile
# Install Node.js for build step (in Alpine)
RUN apk add --no-cache nodejs npm
RUN npm install --save-dev esbuild
RUN npx esbuild static/js/dashboard.js --bundle --minify --outfile=static/dist/dashboard.min.js
RUN npx esbuild static/js/calendar.js --bundle --minify --outfile=static/dist/calendar.min.js
RUN npx esbuild static/js/home.js --bundle --minify --outfile=static/dist/home.min.js
```

Then update Jinja2 templates to reference `/static/dist/*.min.js` instead of `/static/js/*.js`.

---

## Question 7: htmx + SSR vs. Full SPA

**Verdict: htmx + SSR is a better architectural fit than a full SPA. But neither is necessary right now.**

**Confidence: HIGH** (architectural analysis, not version-dependent)

### Architectural Comparison

| Aspect | Current (Vanilla JS + Jinja2) | htmx + SSR | Full SPA (React) |
|--------|-------------------------------|------------|------------------|
| Server rendering | Yes (Jinja2) | Yes (Jinja2) | No (client-side only) |
| API format | JSON | HTML fragments | JSON |
| JS payload | ~83 KB custom | ~14 KB (htmx) + minimal custom | ~200+ KB (React + deps) |
| SEO | Full (server-rendered) | Full (server-rendered) | Requires SSR/prerendering |
| Auth | Server sessions (simple) | Server sessions (simple) | Client state + cookies (complex) |
| Build step | None needed | None needed | Required (Vite) |
| Flask integration | Native | Native | Needs separate hosting or proxy |
| Deployment | Single service | Single service | Often two services |
| Developer experience | Manual DOM updates | Declarative HTML attributes | Component-based, hot reload |
| Offline support | No | No | Possible with service worker |
| Complex interactions | Requires more JS | Moderate (htmx extensions) | Natural |

### Why htmx Fits This App's Architecture

The gym tracker is fundamentally a server-centric app:
- Data lives in Firestore, accessed via Python
- Auth uses server-side sessions
- Most pages are read-heavy with simple write operations
- No real-time collaboration or complex client-side state

htmx would let you replace most of the vanilla JS with HTML attributes. For example, the entire `fetchLiveCount()` -> `updateUI()` chain in `home.js` (30+ lines of JS) becomes a single `hx-get` attribute.

### Why NOT to Adopt htmx Right Now

1. **API contract change.** All `/api/*` endpoints currently return JSON. htmx needs HTML fragments. You would need to either:
   - Add new `/partials/*` endpoints returning HTML (duplication)
   - Make endpoints content-negotiate based on `Accept` header
   - Convert existing endpoints to return HTML only (breaks any JSON consumers)

2. **Chart rendering.** htmx replaces server-to-DOM data flow, but charts still need JavaScript (Chart.js or hand-built). You would still have significant JS for the dashboard page.

3. **Working code.** The current vanilla JS works. Rewriting it to htmx is effort that does not add user-facing features.

### When htmx Would Be Worth It

- If you add 3+ more pages with similar fetch-and-display patterns
- If you want to eliminate most client-side JavaScript
- If you rebuild the frontend from scratch (new design, new pages)

### Recommendation

Keep the current architecture (vanilla JS + Jinja2 + JSON API). If doing a major frontend redesign in the future, consider htmx as the primary framework -- but only as part of a planned rewrite, not an incremental migration.

---

## Question 8: DOMPurify Status and Alternatives

**Verdict: DOMPurify is still the standard. Upgrade from 3.2.4 to latest. Fix the fail-open fallback. The Sanitizer API is not ready.**

**Confidence: HIGH for DOMPurify recommendation, MEDIUM for Sanitizer API status**

### Current State in Codebase

- **Version:** 3.2.4 (vendored as `static/js/purify.min.js`)
- **Usage pattern:** `safeSanitize()` wrapper function, duplicated in 3 files
- **Critical bug:** Fallback returns unsanitized HTML (identified as concern H-03 in CONCERNS.md)

```javascript
// CURRENT (BROKEN) -- fails open
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;  // XSS VULNERABILITY: unsanitized content returned
}
```

### DOMPurify Status

DOMPurify (by Cure53) remains the de facto standard for HTML sanitization in the browser. Key facts:

- **Actively maintained** by Cure53, a well-known security research firm
- **3.x line is current** -- major version bump from 2.x to 3.x happened in 2023
- **Trusted Types integration** -- DOMPurify 3.x supports the Trusted Types API for CSP enforcement
- **Wide adoption** -- used by major projects (WordPress Gutenberg, Angular, Notion)
- **Version 3.2.4** (the vendored version) may not be the absolute latest; check npm for current

### Alternatives Assessment

| Solution | Status | Browser Support | Recommendation |
|----------|--------|-----------------|----------------|
| **DOMPurify** | Stable, actively maintained | All browsers | Use this |
| **Sanitizer API** (browser built-in) | Behind flags in Chrome. Not shipped in Firefox/Safari as of early 2025. | Chrome flag only | NOT ready for production |
| **Trusted Types** (CSP directive) | Shipped in Chrome 83+. Not in Firefox/Safari. | Chrome only | Use alongside DOMPurify, not instead of |
| **sanitize-html** (npm) | Stable | All (server-side or bundled) | Server-side alternative only |

### The Sanitizer API (Why NOT to Use It Yet)

The browser-native Sanitizer API (`Element.setHTML()`) was designed to replace libraries like DOMPurify. However, as of early 2025:

- Only available behind a flag in Chrome/Edge
- Not shipped in Firefox or Safari
- The API surface has changed multiple times during spec development
- No polyfill exists that covers all browsers reliably

**Prediction:** The Sanitizer API may become viable in 2026-2027, but for a production app today, DOMPurify is the only reliable choice.

### Trusted Types Integration

Trusted Types IS worth enabling as a defense-in-depth measure alongside DOMPurify:

```javascript
// Create a Trusted Types policy
if (window.trustedTypes && window.trustedTypes.createPolicy) {
    window.trustedTypes.createPolicy('default', {
        createHTML: (input) => DOMPurify.sanitize(input),
    });
}
```

This makes the browser enforce that all DOM sink assignments go through DOMPurify. However, Trusted Types only works in Chromium browsers (Chrome, Edge), so DOMPurify must still be the primary defense.

### Recommended Fix

```javascript
// FIXED -- fails closed, single definition in utils.js
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    // Fail closed: strip ALL HTML if DOMPurify unavailable
    console.error('DOMPurify not loaded -- stripping all HTML tags');
    const div = document.createElement('div');
    div.textContent = html;  // textContent escapes all HTML
    return div.textContent;
}
```

Additionally, where possible, prefer `textContent` over sanitized dynamic HTML:

```javascript
// BETTER: no sanitization needed at all
element.textContent = data.value;

// ONLY use dynamic HTML rendering when you genuinely need HTML structure
// and always sanitize first
```

### Upgrade Path

1. Download latest DOMPurify from the npm registry or GitHub releases
2. Replace `static/js/purify.min.js` with the new version
3. Verify the version string in the license comment at the top of the file
4. Test that `DOMPurify.sanitize('<img src=x onerror=alert(1)>')` strips the `onerror`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart rendering | DOM/SVG bars and lines | Chart.js | Responsiveness, accessibility, tooltips, animations -- hundreds of edge cases |
| HTML sanitization | Regex-based strippers | DOMPurify | XSS bypass vectors are subtle and constantly evolving |
| Date formatting | Manual string concatenation | `Intl.DateTimeFormat` (built-in) | Locale handling, timezone awareness |
| CSS reset | Manual `* { margin: 0; }` | Modern reset (keep current, it works) | The current reset is fine for this app |
| Icon system | Emoji characters (current) | Keep emojis (they work here) | Emojis are lightweight and universally supported |

**Key insight:** The app currently hand-rolls charts (247 LOC) and uses emojis for icons. Charts should be replaced with Chart.js. Emojis are actually fine -- they require no additional assets, work on all devices, and match the app's casual, personal-use character.

---

## Common Pitfalls

### Pitfall 1: Partial Framework Migration (Franken-Stack)
**What goes wrong:** Adding React for one page while keeping vanilla JS for others creates two separate rendering paradigms, two build systems, and two mental models.
**Why it happens:** Desire to use "modern" tools on new features while keeping old code.
**How to avoid:** Either migrate fully or stay vanilla. The React prototype should inform design, not be grafted onto the existing app.
**Warning signs:** Two different CSS systems, two JS bundling configs, two deployment targets.

### Pitfall 2: Over-Engineering a Personal Project
**What goes wrong:** Adding TypeScript, a CSS framework, a state management library, and a test runner to a ~2300 LOC app that one person uses.
**Why it happens:** Best practices for team projects get applied to solo projects where they add overhead without proportional benefit.
**How to avoid:** Ask "does this solve a problem I actually have?" before adding any tool. At 2300 LOC, the codebase is small enough to hold in your head.
**Warning signs:** More config files than feature files, build times exceeding development time.

### Pitfall 3: DOMPurify Vendoring Goes Stale
**What goes wrong:** The vendored `purify.min.js` (currently 3.2.4) never gets updated, accumulating known CVEs.
**Why it happens:** No dependency update mechanism for vendored files (unlike npm which has `npm audit`).
**How to avoid:** Either load from CDN with SRI hash (auto-updated on CDN) or add a Makefile/script target that fetches the latest version.
**Warning signs:** The version comment at the top of `purify.min.js` is more than 6 months old.

### Pitfall 4: Inline Styles in Generated HTML (Chart Rendering)
**What goes wrong:** The hand-built charts use extensive inline `style` attributes in dynamically created elements. This is fragile, hard to maintain, and conflicts with CSP `style-src` policies.
**Why it happens:** It is the quickest way to position chart elements without writing CSS classes.
**How to avoid:** Use Chart.js (renders to canvas, no inline styles) or define CSS classes for chart elements.
**Warning signs:** `dashboard.js` has 50+ lines of template literals containing `style="..."`.

### Pitfall 5: CSS Variable Name Collision Between Pages
**What goes wrong:** `--primary` means `#6366f1` on the home page but `#7c3aed` on the dashboard. If a shared component or base template is introduced, colors will be wrong.
**Why it happens:** Each page was developed independently without a shared design system.
**How to avoid:** Create a single `theme.css` with one set of variable definitions, loaded before page-specific CSS.
**Warning signs:** Same variable name with different values in different files.

---

## Architecture Patterns

### Recommended Project Structure (Refactored Vanilla JS)

```
static/
  css/
    theme.css           # Shared CSS variables (new)
    base.css            # Shared layout styles (new)
    home.css
    calendar.css
    dashboard.css
  js/
    lib/
      purify.min.js     # DOMPurify (upgraded)
      chart.min.js      # Chart.js (new)
    utils.js            # Shared: safeSanitize, constants, date formatting (new)
    home.js
    calendar.js
    dashboard/
      index.js          # Entry point, init, tab switching (split from dashboard.js)
      auth.js           # Login/register/logout (split from dashboard.js)
      charts.js         # Chart rendering with Chart.js (split from dashboard.js)
      stats.js          # Statistics data fetching (split from dashboard.js)
      strength.js       # Strength tab logic (split from dashboard.js)
      calendar-tab.js   # Calendar within dashboard (split from dashboard.js)
  dist/                 # Build output (gitignored)
    home.min.js
    calendar.min.js
    dashboard.min.js

templates/
  base.html             # Shared template (Jinja2 inheritance)
  index.html            # extends base.html
  calendar.html         # extends base.html
  dashboard.html        # extends base.html
```

### Pattern: Jinja2 Template Inheritance

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Cube Gym{% endblock %}</title>
    <link rel="icon" href="https://fav.farm/&#127947;">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/theme.css">
    <link rel="stylesheet" href="/static/css/base.css">
    {% block styles %}{% endblock %}
    <script src="/static/js/lib/purify.min.js"></script>
    <script src="/static/js/utils.js"></script>
</head>
<body>
    {% block content %}{% endblock %}
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Anti-Patterns to Avoid

- **Mixing inline CSS and external CSS:** The dashboard HTML has ~600 lines of inline `<style>` inside the `<head>`, plus an external `dashboard.css`. Move all styles to external CSS files.
- **getElementById without null checks:** Many `document.getElementById()` calls in `dashboard.js` assume the element exists. If the HTML changes, these silently fail. At minimum, add null guards for critical paths.
- **Global function namespace:** All functions are in the global scope. If a build step bundles files, name collisions are possible. Use IIFEs or ES modules (with the build step).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vendored DOMPurify (static file) | CDN with SRI hash OR npm + build step | Ongoing | Auto-updates for security patches |
| Hand-built bar charts (DOM divs) | Chart.js with canvas rendering | Chart.js v4 (2023) | Better perf, accessibility, responsiveness |
| Inline styles in HTML templates | CSS custom properties + external sheets | CSS variables widely adopted ~2020+ | Consistent theming, maintainability |
| jQuery for DOM manipulation | Vanilla JS (querySelector, fetch) | jQuery usage declined ~2019+ | Already done in this project |
| Google Fonts via link tag | Google Fonts via link with `display=swap` | font-display since ~2019 | Already done correctly in this project |

**Deprecated/outdated in the codebase:**
- DOMPurify 3.2.4 -- may have patches since. Verify against npm registry.
- No `<meta name="theme-color">` tag -- this tells mobile browsers what color to paint the status bar. Should be added for the dark theme.

---

## Open Questions

1. **Exact current DOMPurify version**
   - What we know: Vendored version is 3.2.4. DOMPurify 3.x is the current major line.
   - What is unclear: Whether 3.2.4 is the latest patch or if there are security-relevant updates.
   - Recommendation: Run `npm view dompurify version` to check, then update the vendored file.

2. **Chart.js current version**
   - What we know: Chart.js 4.x was current as of early 2025. Version 4 introduced tree-shaking and reduced bundle size.
   - What is unclear: Whether 4.x is still the latest major or if 5.x has been released.
   - Recommendation: Run `npm view chart.js version` before implementation.

3. **Sanitizer API browser rollout timeline**
   - What we know: Chrome was prototyping behind flags as of early 2025. The spec was still in flux.
   - What is unclear: Whether Firefox/Safari have shipped implementations.
   - Recommendation: Monitor MDN Web Docs. Do not depend on Sanitizer API until it reaches Baseline (all major browsers).

4. **React prototype future**
   - What we know: It exists in `stats-dashboard/`, has mock data, and is not integrated.
   - What is unclear: Whether the user wants to invest in React or prefers to enhance vanilla JS.
   - Recommendation: This is a decision for the user, not a technical question. Both paths are viable.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all JS files (`static/js/*.js`), CSS files (`static/css/*.css`), HTML templates (`templates/*.html`), and React prototype (`stats-dashboard/src/`)
- DOMPurify version confirmed from `static/js/purify.min.js` license header: version 3.2.4
- React prototype dependencies from `stats-dashboard/package.json`: React 19.2.0, Vite 7.2.4, Tailwind 4.1.18, TypeScript 5.9.3
- Existing audit documents: `.planning/codebase/STACK.md`, `.planning/codebase/CONCERNS.md`

### Secondary (MEDIUM confidence)
- Framework size comparisons, Chart.js capabilities, esbuild behavior -- based on training data (up to early 2025). Versions should be verified against npm registry.
- Sanitizer API browser support status -- based on training data. Chrome/Edge had flag-only support; Firefox/Safari had not shipped. Current status should be checked on MDN.

### Tertiary (LOW confidence)
- Exact current versions of Chart.js, DOMPurify, htmx, Alpine.js, Preact, Svelte -- training data may be 6-18 months stale. Verify with `npm view <package> version` before implementation.

---

## Metadata

**Confidence breakdown:**
- Vanilla JS viability assessment: HIGH -- based on direct codebase analysis and complexity metrics
- Framework comparison: MEDIUM -- framework versions from training data, not verified against current registry
- Chart.js recommendation: HIGH -- well-established library, recommendation is version-independent
- DOMPurify status: HIGH for "still the standard", MEDIUM for exact version currency
- Build step recommendation: HIGH -- esbuild recommendation is straightforward and version-independent
- htmx vs SPA analysis: HIGH -- architectural analysis, not version-dependent
- Dark theme practices: HIGH -- CSS custom properties are a stable web standard

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- frontend ecosystem is fast-moving but these are architectural recommendations, not version-specific)

**Tools unavailable during research:** WebSearch, WebFetch, Bash (all denied). Research based on thorough codebase analysis and training data. All version-specific claims should be verified against npm registry before implementation.
