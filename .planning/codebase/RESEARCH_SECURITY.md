# Authentication & User Management Research

**Researched:** 2026-04-04
**Domain:** Authentication, session management, password policy, rate limiting
**Confidence:** MEDIUM (based on training data through early 2025; web verification was unavailable)

**Limitation:** WebSearch, WebFetch, and Brave Search tools were all denied during this research session. All findings below come from training data (NIST SP 800-63B Revision 4 draft published 2024, OWASP guidelines updated through 2024, Firebase/bcrypt documentation through early 2025). Confidence levels are adjusted accordingly. Critical recommendations should be cross-verified against current official sources before implementation.

---

## Summary

The gym-tracker app has a functional custom auth system with several security gaps identified in the audit (CONCERNS.md: C-02, H-01, H-04, H-05). The core question is whether to fix these gaps in-place or migrate to a managed auth service like Firebase Auth.

For a hobby project already using Google Cloud Firestore, **Firebase Auth is the strongest recommendation** -- it eliminates entire categories of auth bugs (password policy, session management, account lockout, user enumeration) while integrating natively with the existing Firestore backend. However, migration has real cost: the Flask session model needs rework, existing user accounts need migration, and the auth flow changes from server-side to client-side.

If keeping custom auth (lower migration effort, full control), the key fixes are: strengthen password policy to NIST SP 800-63B standards, fix user enumeration, add account lockout, and reduce session lifetime. These are achievable in 1-2 days of focused work.

**Primary recommendation:** Migrate to Firebase Auth if planning continued development. Fix custom auth in-place if the app is feature-complete and in maintenance mode.

---

## Q1: Custom Auth vs Managed Auth Service

### The Options

| Service | Free Tier | Firestore Integration | Migration Effort | Maintained By |
|---------|-----------|----------------------|------------------|---------------|
| **Firebase Auth** | 10K MAU free (Spark plan); unlimited on Blaze PAYG with no auth charges for email/password | Native -- same project, Firestore Security Rules can reference `request.auth.uid` | MEDIUM -- client-side SDK + server verification | Google |
| **Supabase Auth** | 50K MAU free | None -- Supabase uses PostgreSQL, not Firestore | HIGH -- different ecosystem entirely | Supabase team |
| **Auth0** | 7,500 MAU free (as of 2024) | None native | HIGH -- external IdP, webhook integration | Okta |
| **Clerk** | 10K MAU free (as of 2024) | None native | HIGH -- external IdP, React SDK focused | Clerk |
| **Lucia** | N/A (library, not service) | Community adapter possible | MEDIUM -- still custom code, but structured | Open-source (archived as of March 2025) |
| **Keep custom** | Free | Already integrated | LOW -- fix in place | You |

### Recommendation

**For this project: Firebase Auth is the clear winner IF you plan continued development.**

Reasons:
1. You already use Google Cloud (Firestore, Cloud Run). Firebase Auth is part of the same project -- zero new vendor.
2. Firebase Auth's email/password provider handles: password hashing, session tokens (Firebase ID tokens, 1-hour expiry + refresh tokens), account lockout, email verification, password reset -- all things you would otherwise hand-roll.
3. Firestore Security Rules can directly reference `request.auth.uid`, enabling database-level access control (defense in depth beyond application-level checks).
4. The free tier (10K monthly active users on Spark, or no auth charges on Blaze pay-as-you-go) is more than sufficient for a hobby fitness tracker.

**If keeping custom auth is preferred** (simpler, no migration, full control), that is acceptable for a hobby project with a small known user base. But you must fix the critical gaps (C-02, H-01, H-05).

### Firebase Auth Migration Implications

| Current | After Firebase Auth |
|---------|-------------------|
| bcrypt hashing in `database.py` | Firebase handles hashing internally |
| Flask server-side sessions (cookie) | Firebase ID tokens (JWT, 1-hour expiry + refresh token) |
| `session['user_id']` in route handlers | Verify Firebase ID token server-side via `firebase_admin.auth.verify_id_token()` |
| `database.py` auth functions (create_user, authenticate_user) | Remove -- Firebase client SDK handles auth |
| Admin password reset endpoint | Firebase Admin SDK `auth.update_user()` or built-in password reset email |
| No email verification | Firebase supports it out of the box (optional to enable) |
| Username-based login | Firebase uses email-based login by default; username can be stored in Firestore user profile |

**Key migration risk:** Existing users have bcrypt hashes in Firestore. Firebase Auth has a user import API (`auth.import_users()`) that supports bcrypt hashes with a known salt. This means existing users can be migrated without forcing password resets, but requires careful handling of the bcrypt hash format.

**Confidence:** MEDIUM -- Firebase Auth features and free tier are well-documented and stable. The user import API for bcrypt hashes existed as of 2024. Verify current import format before implementing.

---

## Q2: NIST SP 800-63B Password Requirements

**Source:** NIST SP 800-63B Revision 4 (draft published August 2024, building on the final Revision 3 from 2017/2020).

### Key Requirements for Memorized Secrets (Passwords)

| Requirement | NIST Guidance | Current App | Gap |
|-------------|---------------|-------------|-----|
| **Minimum length** | SHALL require minimum 8 characters | 3 characters | CRITICAL gap |
| **Maximum length** | SHALL permit at least 64 characters | 20 characters | Increase to 64+ (bcrypt truncates at 72 bytes, so 72 is the practical ceiling for bcrypt) |
| **Composition rules** | SHALL NOT require mixtures of character types (uppercase, digits, symbols) | No composition rules | Compliant (by accident) |
| **Blocklist** | SHALL check against a list of compromised/common passwords | No blocklist | Add breached password check |
| **Truncation** | SHALL NOT truncate the password | bcrypt truncates at 72 bytes silently | Document or pre-hash with SHA-256 |
| **Unicode** | SHOULD accept all Unicode characters | Only tested with ASCII | Consider, low priority |
| **Password hints** | SHALL NOT use password hints | No hints | Compliant |
| **Expiration** | SHALL NOT require periodic password changes unless compromise is suspected | No expiration | Compliant |
| **Knowledge-based questions** | SHALL NOT use security questions | No security questions | Compliant |

### NIST-Aligned Password Validation (Recommended Implementation)

```python
import re

# Breached password list -- use a small top-100K list or check via k-anonymity API
COMMON_PASSWORDS = set()  # Load from file at startup

def validate_password(password: str) -> tuple:
    """NIST SP 800-63B compliant password validation."""
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 72:
        return False, "Password must be at most 72 characters"
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a different one"
    return True, None
```

**Important NIST nuance:** NIST explicitly recommends AGAINST composition rules (requiring uppercase + digit + symbol). Research shows users respond to composition rules with predictable patterns ("Password1!") that are easier to crack than longer passphrases. The 8-character minimum + blocklist approach is more effective.

**The max-length question:** bcrypt internally truncates input to 72 bytes. Passwords longer than 72 bytes are silently truncated, meaning "aaaa...72a's...X" and "aaaa...72a's...Y" would hash identically. Options:
1. Cap at 72 characters (simple, honest)
2. Pre-hash with SHA-256 before bcrypt (allows longer passwords, but adds complexity)
3. Cap at 64 characters as NIST suggests as a minimum maximum (simplest, covers 99.9% of use cases)

**Recommendation for this project:** Cap at 72, no composition rules, add a small breached password list (top 10K most common passwords, ~100KB file).

**Confidence:** HIGH for the core requirements (min 8, no composition rules, blocklist). These have been in NIST guidance since Revision 3 (2017) and reinforced in Revision 4. MEDIUM for the specific Revision 4 details (verify the final publication status).

---

## Q3: Bcrypt Cost Factor

### Current Default

The app uses `bcrypt.gensalt()` without specifying a cost factor, which defaults to 12 in the Python `bcrypt` library.

### Recommendations by Source

| Source | Recommended Cost | Reasoning |
|--------|-----------------|-----------|
| OWASP (2024) | 10 minimum, 12+ preferred | Balance between security and UX (< 1 second target) |
| NIST SP 800-63B | Does not specify cost factor | Specifies "approved key derivation function" -- bcrypt qualifies |
| General consensus (2024-2025) | 12 for most apps, 13-14 for high-security | Hardware has gotten faster; cost 10 is now under 100ms on modern CPUs |

### Empirical Timing (approximate, single core, modern hardware 2024-2025)

| Cost Factor | Approximate Time | Suitable For |
|-------------|-----------------|--------------|
| 10 | ~60-80ms | Minimum acceptable |
| 12 | ~250-350ms | Default, good for most apps |
| 13 | ~500-700ms | Higher security |
| 14 | ~1-1.4s | High security, may impact UX |

### Recommendation

**Keep cost factor 12.** It is the current default in the `bcrypt` library, aligns with OWASP guidance, and provides ~250-350ms hashing time which is unnoticeable for login (happens once) but makes brute-force prohibitively slow.

For this hobby project, cost 12 is perfectly appropriate. There is no need to increase to 13 or 14 -- the bottleneck for this app's security is the 3-character minimum password, not the bcrypt cost factor. Fixing the password policy (Q2) delivers far more security than increasing the cost factor.

**Confidence:** HIGH -- bcrypt cost factor 12 has been the standard recommendation across multiple authoritative sources for several years. The `bcrypt` Python library default has been 12 since at least version 3.x.

---

## Q4: Session Management Approach

### Options Comparison

| Approach | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Server-side sessions (current)** | Flask stores session data server-side; cookie contains only session ID | Simple, server controls session state, can invalidate immediately | Stateful -- session data lost on restart (unless externalized); doesn't scale without shared storage |
| **JWT (stateless)** | Token contains claims, signed by server; client stores and sends on each request | Stateless, scales horizontally, no server-side storage | Cannot revoke without a blocklist (which re-introduces state); token size; XSS risk if stored in localStorage |
| **Firebase ID tokens** | Short-lived JWT (1 hour) + long-lived refresh token; Firebase manages issuance and refresh | Best of both -- short-lived stateless tokens, Firebase handles refresh, revocation possible via Firebase Admin SDK | Requires Firebase Auth; adds client-side complexity |
| **Hybrid (short JWT + server-side refresh)** | Short-lived access token (15-30 min) + server-side refresh token | Good security properties, revocable | Complex to implement correctly; essentially rebuilding what Firebase Auth provides |

### Current Implementation Analysis

The app uses Flask's built-in server-side sessions with:
- `session.permanent = True` (365-day lifetime)
- Secure cookie settings (HttpOnly, Secure, SameSite=Lax)
- Werkzeug's `SecureCookieSessionInterface` (default) -- this actually stores session data IN the cookie (signed but not encrypted) unless a server-side session extension is used

**Important clarification:** Flask's default session implementation is NOT truly server-side. It uses signed cookies (itsdangerous) where the session data is serialized into the cookie itself, signed with `SECRET_KEY`. This means:
- Session data is visible to the client (though tamper-proof if SECRET_KEY is strong)
- There is no server-side session storage to clear/invalidate
- "Logging out" clears the cookie, but an old cookie remains valid until expiry

This is a meaningful distinction. True server-side sessions (e.g., Flask-Session with Redis/Firestore backend) would allow server-side invalidation.

### Recommendation

**If migrating to Firebase Auth:** Use Firebase ID tokens (1-hour expiry + refresh tokens). This is the standard pattern and eliminates all session management concerns.

**If keeping custom auth:**
1. **Keep cookie-based sessions** (simplest for a monolithic Flask app)
2. **Reduce lifetime to 30 days** (see Q5)
3. **Add a session version** in the user document to enable forced logout (increment version on password change; reject sessions with old version)
4. Consider Flask-Session with Firestore backend for true server-side sessions (enables immediate invalidation)

**Confidence:** HIGH for the Flask cookie-session clarification (this is well-documented behavior). MEDIUM for the Flask-Session + Firestore recommendation (verify the `flask-session` library still supports Firestore or a compatible backend).

---

## Q5: Session Lifetime (365 Days)

### Is 365-Day Session Lifetime Acceptable?

**Short answer: No, even for a hobby fitness app.**

| Consideration | Impact |
|---------------|--------|
| **Stolen cookie** | An attacker who obtains the session cookie (via XSS, shared computer, network interception) has 365 days to use it |
| **Shared device** | If a user logs in on a shared computer and forgets to log out, the session persists for a year |
| **No forced logout** | Since Flask default sessions are signed cookies (not server-side), there is NO way to invalidate an old cookie |
| **Credential rotation** | If the user changes their password, old sessions should be invalidated; with 365-day cookies and no session versioning, old sessions remain valid |

### Industry Comparison

| App Type | Typical Session Lifetime | Notes |
|----------|------------------------|-------|
| Banking | 15-30 minutes | Re-auth on each sensitive action |
| Email (Gmail) | 30 days (with re-auth prompts) | "Remember me" extends this |
| Social media | 30-90 days | Persistent login is standard |
| Fitness apps (Strava, MyFitnessPal) | 30-90 days | Long-lived but not a full year |
| Hobby/personal projects | 7-30 days | Lower risk tolerance due to fewer security controls |

### Recommendation

**Reduce to 30 days.** This provides a good balance:
- Users of a fitness tracker log in frequently (daily/weekly workout logging), so 30 days rarely causes friction
- Limits the window of exposure for stolen cookies
- Aligns with industry norms for low-sensitivity personal data apps

```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
```

If users complain about re-authentication friction, 90 days is an acceptable compromise. Never exceed 90 days without true server-side sessions and session versioning.

**Confidence:** HIGH -- session lifetime guidance is consistent across OWASP, NIST, and industry practice.

---

## Q6: Password Reset (Email vs Admin-Only)

### Current State

The app has an admin-only password reset endpoint (`/api/admin/reset-password`) protected by `ADMIN_SECRET`. There is no self-service password reset. Users who forget their password must contact the admin.

### Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **Admin-only reset (current)** | Simple, no email infrastructure needed, sufficient for 2-5 known users | Doesn't scale; admin must be available; no audit trail; admin sees/sets the new password |
| **Email-based reset (token)** | Self-service, standard UX, audit trail | Requires email sending capability (SMTP or service like SendGrid/Firebase); token generation/expiry logic; adds complexity |
| **Firebase Auth password reset** | Self-service, fully managed, secure by default | Requires Firebase Auth migration; Firebase sends the emails |

### Recommendation

**For a hobby project with < 10 known users: Admin-only is acceptable.** But make these improvements:
1. Generate a random temporary password rather than accepting one in the API request (the admin should not choose the password)
2. Log password resets (who, when) for audit trail
3. Force the user to change their password on next login after a reset (set a `must_change_password` flag in the user document)

**If user base grows beyond "people you know":** Add email-based password reset. If on Firebase Auth, this is built-in. For custom auth, use a time-limited signed token (e.g., `itsdangerous.URLSafeTimedSerializer`, 1-hour expiry) and send via a transactional email service.

**If on Firebase Auth:** Use Firebase's built-in `sendPasswordResetEmail()`. Zero custom code needed.

**Confidence:** HIGH -- admin reset patterns and email reset token patterns are well-established.

---

## Q7: Account Lockout Strategy

### Current State

No account lockout exists (audit finding H-05). The only protection is rate limiting: 10 login attempts per minute per IP.

### OWASP Recommended Strategy

OWASP recommends a multi-layered approach:

| Layer | Mechanism | Threshold | Behavior |
|-------|-----------|-----------|----------|
| 1. Rate limiting | Per-IP request throttling | 10-20/minute | Return 429 Too Many Requests |
| 2. Temporary lockout | Per-account failed attempt tracking | 5 consecutive failures | Lock account for 15-30 minutes |
| 3. Permanent lockout | Accumulated failures | 10-20 failures in 24 hours | Lock until admin reset or email verification |
| 4. CAPTCHA | Challenge after suspicious activity | After 3 failures | Require human verification |

### Recommended Implementation for This Project

**Simple approach (no CAPTCHA, no email):**

```python
# In database.py -- track failed attempts in user document

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def authenticate_user(username: str, password: str) -> dict:
    if not username or not password:
        return {'success': False, 'error': 'Invalid username or password'}

    db = get_db()
    username_lower = username.lower()
    docs = db.collection('users').where('username_lower', '==', username_lower).limit(1).stream()

    user_doc = None
    doc_ref = None
    for doc in docs:
        user_doc = doc.to_dict()
        doc_ref = doc.reference
        break

    # Prevent user enumeration -- same error for missing user
    if not user_doc:
        # Constant-time dummy check to prevent timing attacks
        verify_password(password, "$2b$12$LJ3m4ys3Lge9MiGMBMYJdOKXNjJPYMFGnXNOcGlBeJCGnMdSCZ4bG")
        return {'success': False, 'error': 'Invalid username or password'}

    # Check lockout
    failed_attempts = user_doc.get('failed_login_attempts', 0)
    last_failed = user_doc.get('last_failed_login')
    if failed_attempts >= MAX_FAILED_ATTEMPTS and last_failed:
        lockout_until = last_failed + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        if datetime.now(tz) < lockout_until:
            return {'success': False, 'error': 'Account temporarily locked. Try again later.'}
        # Lockout expired -- reset counter
        doc_ref.update({'failed_login_attempts': 0})

    if not verify_password(password, user_doc.get('password_hash', '')):
        # Increment failed attempts
        doc_ref.update({
            'failed_login_attempts': firestore.Increment(1),
            'last_failed_login': datetime.now(tz)
        })
        return {'success': False, 'error': 'Invalid username or password'}

    # Success -- reset failed attempts
    doc_ref.update({'failed_login_attempts': 0, 'last_failed_login': None})
    return {
        'success': True,
        'user_id': user_doc['user_id'],
        'username': user_doc['username']
    }
```

**Key design decisions:**
1. Lockout is temporary (15 minutes), not permanent -- prevents denial-of-service by locking other users' accounts
2. Same error message for all failure modes -- prevents user enumeration (fixes H-01)
3. Dummy bcrypt check when user not found -- prevents timing-based enumeration
4. Counter stored in Firestore user document -- survives server restarts, works across Cloud Run instances
5. Counter resets on successful login and after lockout expiry

**Confidence:** HIGH -- account lockout patterns are well-documented in OWASP and have been stable for years.

---

## Q8: Firebase Auth + Firestore Integration

### How It Works

Firebase Auth and Firestore are both Firebase services within the same Google Cloud project. They integrate as follows:

1. **Client-side:** Firebase Auth SDK handles login/registration UI or API calls. Returns a Firebase ID token (JWT).
2. **Server-side (Flask):** `firebase_admin.auth.verify_id_token(id_token)` validates the JWT and returns the user's UID.
3. **Firestore Security Rules:** Can reference `request.auth.uid` to enforce per-user access at the database level (defense in depth).
4. **User management:** Firebase Admin SDK provides `auth.create_user()`, `auth.update_user()`, `auth.delete_user()`, `auth.list_users()`.

### What Firebase Auth Gives You for Free

| Feature | Custom Auth (Current) | Firebase Auth |
|---------|----------------------|---------------|
| Password hashing | You manage bcrypt | Firebase manages internally (scrypt) |
| Password policy | You implement validation | Firebase enforces minimum 6 chars (configurable via Identity Platform) |
| Session management | Flask cookies, 365 days | ID tokens (1-hour) + refresh tokens |
| Account lockout | Not implemented | Built-in (blocks after too many failed attempts) |
| Password reset | Admin endpoint only | Built-in email-based reset |
| Email verification | Not implemented | Built-in |
| User enumeration protection | Leaks via error messages | Configurable (can return generic errors) |
| OAuth/social login | Not implemented | Google, GitHub, Facebook, Apple, etc. -- add with config |
| Multi-factor auth | Not implemented | TOTP and SMS MFA available |
| Session revocation | Not possible (signed cookies) | `auth.revoke_refresh_tokens(uid)` |

### Migration Path

1. **Add `firebase-admin` to `requirements.txt`** (server-side token verification)
2. **Add Firebase Auth JS SDK to frontend** (client-side auth)
3. **Migrate existing users:**
   - Use Firebase Admin SDK's `auth.import_users()` with `UserImportHash.bcrypt()`
   - Each user's bcrypt hash from Firestore can be imported directly
   - Users keep their existing passwords -- no forced reset needed
4. **Update Flask middleware:**
   - Replace `session['user_id']` checks with `verify_id_token()` checks
   - Extract `uid` from the verified token instead of from session
5. **Update frontend auth flow:**
   - Replace custom login/register overlay with Firebase Auth calls
   - Send ID token with each API request (Authorization: Bearer header)
6. **Remove from codebase:**
   - `database.py` auth functions (create_user, authenticate_user, hash_password, verify_password, validate_password)
   - Flask session configuration for auth
   - Admin password reset endpoint (use Firebase Admin SDK instead)

### Firebase Auth Flask Integration Pattern

```python
# Server-side verification in Flask
import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase Admin (on Cloud Run, uses default service account)
firebase_admin.initialize_app()

def require_login():
    """Verify Firebase ID token from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, (jsonify({'error': 'Not authenticated'}), 401)
    
    id_token = auth_header.split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid'], None
    except Exception:
        return None, (jsonify({'error': 'Invalid or expired token'}), 401)
```

```javascript
// Client-side (frontend)
import { getAuth, signInWithEmailAndPassword } from "firebase/auth";

const auth = getAuth();

async function authFetch(url, options = {}) {
    const user = auth.currentUser;
    if (!user) { showLoginOverlay(); return; }
    
    const token = await user.getIdToken();
    const headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
    
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        showLoginOverlay();
        return;
    }
    return response;
}
```

### Cost Implications

Firebase Auth itself has no per-authentication charges for email/password on the Blaze (pay-as-you-go) plan. On the Spark (free) plan, the limit is 10,000 monthly active users for email/password. For a hobby gym tracker, this is effectively free.

The only cost consideration: Firebase Auth's `verify_id_token()` call checks the token signature locally using cached public keys -- it does NOT make a network call for each verification. So there is no added latency or cost per API request.

### Username vs Email Login

Firebase Auth is email-centric. The current app uses username-based login. Options:
1. **Switch to email login:** Cleanest integration, but changes UX
2. **Store username as displayName in Firebase Auth:** Users log in with email, see their username in the UI
3. **Username-to-email mapping:** Store `{username -> email}` in Firestore, look up email from username before calling Firebase Auth. Adds complexity but preserves current UX.

**Recommendation:** Switch to email login. For a fitness tracker, email is more natural than a username (users tend to forget usernames more than emails). Store username as a display name in a Firestore user profile document.

**Confidence:** MEDIUM -- Firebase Auth features are well-documented and stable. The bcrypt import API and Flask integration patterns are based on training data through early 2025. Verify the current Firebase Admin Python SDK version and import API before implementing.

---

## Q9: Rate Limiting Best Practices for Auth Endpoints

### Current State

| Endpoint | Current Limit | Storage |
|----------|--------------|---------|
| `/api/auth/login` | 10/minute per IP | In-memory |
| `/api/auth/register` | 5/minute per IP | In-memory |
| Global default | 1000/day, 150/hour per IP | In-memory |

### Problems with Current Approach

1. **In-memory storage resets on deploy/restart** (audit finding L-02)
2. **Cloud Run scaling creates separate counters per instance** -- multiple instances means multiplicative bypass
3. **IP-only limiting is bypassable** with multiple IPs (proxies, VPNs, botnets)
4. **No per-account limiting** -- attacker can try 10 passwords/minute against ANY account from a single IP

### Recommended Rate Limiting Architecture

| Layer | What | Limit | Purpose |
|-------|------|-------|---------|
| **Per-IP on login** | IP address | 10/minute, 100/hour | Slow down single-source attacks |
| **Per-account on login** | Username | 5 consecutive failures, then 15-min lockout | Prevent targeted brute-force (see Q7) |
| **Per-IP on register** | IP address | 3/hour | Prevent bulk account creation |
| **Global on register** | All sources | 20/hour | Absolute cap on new accounts |

### Storage Recommendation

For this project (single Cloud Run instance in practice, hobby scale):
- **In-memory is acceptable for IP-based rate limiting** -- the risk is acknowledged and accepted for a hobby project
- **Firestore for per-account lockout** -- this must survive restarts and work across instances (see Q7 implementation)

If you need robust IP-based limiting in the future:
- **Redis** via Cloud Memorystore (adds ~$30/month minimum)
- **Cloud Run's built-in rate limiting** via Cloud Armor (free tier available, but configuration is more complex)

### Flask-Limiter Configuration

```python
# Tighten auth endpoint limits
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")   # per-IP
@limiter.limit("100 per hour")    # per-IP sustained
def login_user():
    ...

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("3 per hour")      # tighter than current 5/minute
def register_user():
    ...
```

**Confidence:** HIGH -- rate limiting patterns are well-established. The in-memory vs Redis tradeoff for Cloud Run is specific to GCP architecture.

---

## Decision Matrix: Custom Auth Fix vs Firebase Auth Migration

| Factor | Fix Custom Auth | Migrate to Firebase Auth |
|--------|----------------|------------------------|
| **Effort** | 1-2 days | 3-5 days |
| **Password policy** | Manual implementation | Partially managed (configurable with Identity Platform) |
| **Account lockout** | Manual implementation | Built-in |
| **Password reset** | Manual (email infra needed) | Built-in |
| **Session management** | Still Flask cookies | ID tokens + refresh tokens |
| **User enumeration** | Manual fix | Configurable |
| **OAuth/social login** | Not feasible | Config-only addition |
| **Future maintenance** | You maintain auth code | Google maintains auth infra |
| **Vendor lock-in** | None | Moderate (Firebase-specific) |
| **Existing user migration** | Not needed | Required (bcrypt import API) |
| **Username-based login** | Keep as-is | Needs email transition or mapping layer |
| **Learning curve** | None | Firebase Auth SDK, ID token flow |

### Verdict by Scenario

**Scenario A -- "Fix and forget" (app is done, just hardening):**
Go with custom auth fixes. Implement: NIST password policy, unified error messages, account lockout with Firestore tracking, reduce session lifetime to 30 days. Total: ~1 day of work.

**Scenario B -- "Continued development" (adding features, growing users):**
Migrate to Firebase Auth. The upfront cost (3-5 days) pays off by eliminating ongoing auth maintenance. You get password reset, email verification, session revocation, and OAuth for free. Every future auth-related feature is configuration rather than code.

---

## Common Pitfalls

### Pitfall 1: User Enumeration via Error Messages
**What goes wrong:** Different error messages for "user not found" vs "wrong password" let attackers enumerate valid accounts.
**Why it happens:** Developers want helpful error messages during development and forget to genericize for production.
**How to avoid:** Always return "Invalid username or password" for any auth failure. Add a dummy bcrypt check when user is not found to prevent timing-based enumeration.
**Warning signs:** Different error strings in login failure paths.
**Status in this app:** Present (H-01). Fix is straightforward.

### Pitfall 2: bcrypt 72-Byte Truncation
**What goes wrong:** Passwords longer than 72 bytes are silently truncated, meaning two passwords sharing the first 72 bytes hash identically.
**Why it happens:** bcrypt's internal Blowfish key schedule only processes 72 bytes. Most bcrypt libraries do not warn about this.
**How to avoid:** Either cap password length at 72 characters, or pre-hash with SHA-256 and feed the hash to bcrypt (this is what Dropbox does).
**Warning signs:** Max password length > 72 without pre-hashing.
**Status in this app:** Current max is 20 chars, so no immediate risk. If raising the max, address this.

### Pitfall 3: Flask Default Sessions Are Signed Cookies, Not Server-Side
**What goes wrong:** Developers assume `session.clear()` invalidates the session. It only clears the server-side dict -- old cookies remain valid until expiry because the session data IS the cookie.
**Why it happens:** Flask's `SecureCookieSessionInterface` stores session data in a signed cookie. There is no server-side session store by default.
**How to avoid:** Use Flask-Session with a server-side backend (Redis, Firestore, filesystem) for true session invalidation. Or, for custom auth, add a session version to user documents and validate it on each request.
**Warning signs:** `session.clear()` being treated as "force logout this user from all devices."
**Status in this app:** Present. Logout clears the current cookie but cannot invalidate other copies of the cookie.

### Pitfall 4: Rate Limiting on Cloud Run with In-Memory Storage
**What goes wrong:** Each Cloud Run instance has its own rate limit counter. Auto-scaling or cold starts reset counters. An attacker can burst requests that land on different instances.
**Why it happens:** `storage_uri="memory://"` is per-process.
**How to avoid:** Accept the limitation for a hobby project, or switch to Redis/Memorystore backend for flask-limiter.
**Warning signs:** Rate limiting that seems ineffective under load.
**Status in this app:** Present (L-02). Acceptable for hobby scale.

### Pitfall 5: Admin Secret in Query Strings
**What goes wrong:** Admin secrets passed via `?secret=VALUE` are logged in server access logs, browser history, CDN logs, and Cloud Run request logs.
**Why it happens:** Convenience during development.
**How to avoid:** Accept secrets only via request headers (`X-Admin-Secret`).
**Warning signs:** `request.args.get('secret')` in admin endpoint code.
**Status in this app:** Present (H-02). Fix by removing `request.args.get('secret')`.

---

## Specific Recommendations Summary

### Must-Fix (regardless of custom vs Firebase decision)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Password minimum 8 chars, max 72, add blocklist | 30 min | Fixes C-02 |
| 2 | Generic error messages on login failure + dummy bcrypt | 15 min | Fixes H-01 |
| 3 | Remove `request.args.get('secret')` from admin endpoints | 15 min | Fixes H-02 |
| 4 | Add account lockout (5 failures, 15-min cooldown) | 1 hour | Fixes H-05 |
| 5 | Reduce session lifetime to 30 days | 5 min | Reduces cookie theft window |

### Should-Fix (if keeping custom auth)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 6 | Add CSRF protection (custom header validation for JSON API) | 30 min | Fixes H-04 |
| 7 | Add session versioning for forced logout on password change | 1 hour | Enables session invalidation |
| 8 | Tighten registration rate limit to 3/hour | 5 min | Reduces spam accounts |

### Nice-to-Have (if continued development)

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 9 | Firebase Auth migration | 3-5 days | Eliminates auth maintenance |
| 10 | Email verification | Built-in with Firebase | Validates user identity |
| 11 | Self-service password reset | Built-in with Firebase | Removes admin burden |

---

## Sources

### Primary (HIGH confidence for core claims)
- NIST SP 800-63B Revision 3 (2017/2020) and Revision 4 Draft (August 2024) -- password policy requirements. Training data covers the published revisions. The Revision 4 final may have been published by April 2026; verify current status.
- OWASP Authentication Cheat Sheet (updated through 2024 in training data) -- account lockout, session management, user enumeration prevention.
- OWASP Password Storage Cheat Sheet (2024) -- bcrypt cost factor recommendations.
- Python `bcrypt` library documentation -- default cost factor of 12, 72-byte truncation behavior.
- Flask documentation -- `SecureCookieSessionInterface` behavior, session configuration.

### Secondary (MEDIUM confidence)
- Firebase Auth documentation (through early 2025 in training data) -- features, pricing, user import API, Firestore integration. Verify current pricing and API changes.
- Firebase Admin Python SDK documentation -- `verify_id_token()`, `import_users()`, `UserImportHash.bcrypt()`.

### Tertiary (LOW confidence -- verify before implementing)
- Firebase Auth free tier limits (10K MAU on Spark plan) -- may have changed by April 2026.
- Lucia auth library status -- was archived in March 2025 per community reports in training data; verify current status.
- Firebase Identity Platform password policy configuration -- this was a feature available on the paid Identity Platform tier as of 2024; verify if it has been brought to the free Firebase Auth tier.

---

## Metadata

**Confidence breakdown:**
- Password policy (NIST): HIGH -- core requirements stable since 2017, reinforced in 2024 draft
- bcrypt cost factor: HIGH -- industry consensus stable for years
- Session management: HIGH -- well-documented Flask behavior and OWASP guidance
- Account lockout: HIGH -- standard patterns, no ambiguity
- Firebase Auth features: MEDIUM -- based on early 2025 training data, may have API/pricing changes
- Firebase Auth migration path: MEDIUM -- bcrypt import API existed as of 2024, verify current state
- Rate limiting on Cloud Run: HIGH -- architectural behavior is well-understood

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- auth best practices are slow-changing, but Firebase pricing/features should be re-verified)
**Limitation:** No live web verification was possible. All recommendations from training data.
