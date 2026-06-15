"""
=========================================================
PRISM - Database Seed Script
=========================================================
Populates the database with realistic demo incidents so
the dashboard looks impressive for judges and demos.

Usage (local):
    python seed.py

Usage (against live deployed app):
    python seed.py --url https://prism-ldxm.onrender.com
=========================================================
"""

import sys
import httpx

# ─────────────────────────────────────────
# Target URL — default to local, override via CLI
# ─────────────────────────────────────────
BASE_URL = sys.argv[2] if len(sys.argv) > 2 else (
    sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "http://localhost:8080"
)
if "--url" in sys.argv:
    idx = sys.argv.index("--url")
    BASE_URL = sys.argv[idx + 1]

BASE_URL = BASE_URL.rstrip("/")

# ─────────────────────────────────────────
# Realistic Demo Incidents
# ─────────────────────────────────────────
DEMO_INCIDENTS = [
    {
        "title": "SQL Injection in User Login Endpoint",
        "severity": "critical",
        "root_cause": (
            "The login handler directly interpolated user-supplied username into a raw SQL "
            "query string without sanitization: `SELECT * FROM users WHERE username = '{input}'`. "
            "An attacker could inject `' OR '1'='1` to bypass authentication entirely."
        ),
        "fix": (
            "Replace raw string interpolation with SQLAlchemy parameterized queries: "
            "`db.query(User).filter(User.username == username).first()`. "
            "Never use f-strings or .format() to build SQL queries."
        ),
        "postmortem": "https://postmortems.internal/prism/sql-injection-login",
        "affected_components": "auth-service, user-api",
    },
    {
        "title": "Hardcoded AWS Secret Key in Payment Module",
        "severity": "critical",
        "root_cause": (
            "A developer committed AWS credentials directly into `payment/processor.py` as "
            "plaintext string constants (`AWS_SECRET_KEY = 'AKIAIOSFODNN7EXAMPLE...'`). "
            "The key was live and had S3 full-access permissions. Detected via PR diff scan."
        ),
        "fix": (
            "Remove the hardcoded credentials immediately and rotate the AWS key. "
            "Use environment variables (`os.getenv('AWS_SECRET_KEY')`) and add a "
            "pre-commit hook with `detect-secrets` to prevent future occurrences. "
            "Add `*.env` and secret patterns to `.gitignore`."
        ),
        "postmortem": "https://postmortems.internal/prism/hardcoded-aws-secret",
        "affected_components": "payment/processor.py, s3-client",
    },
    {
        "title": "Missing Balance Validation Causes Negative Account Balance",
        "severity": "high",
        "root_cause": (
            "The debit transaction handler subtracted the amount from the account balance "
            "without first checking if the balance was sufficient. `new_balance = balance - amount` "
            "was executed unconditionally, allowing accounts to go negative on concurrent requests."
        ),
        "fix": (
            "Add an explicit balance check before processing: "
            "`if balance < amount: raise InsufficientFundsError()`. "
            "Also implement a database-level CHECK constraint: "
            "`CHECK (balance >= 0)` to enforce integrity at the DB layer."
        ),
        "postmortem": "https://postmortems.internal/prism/negative-balance",
        "affected_components": "payment-api, accounts-service",
    },
    {
        "title": "Race Condition in Idempotency Key Validation",
        "severity": "high",
        "root_cause": (
            "The idempotency check (`SELECT` then `INSERT`) was not atomic. Under high concurrency, "
            "two simultaneous requests with the same idempotency key both passed the SELECT check "
            "before either INSERT completed, resulting in duplicate charges to customers."
        ),
        "fix": (
            "Use a database-level unique constraint on the `idempotency_key` column combined with "
            "an `INSERT ... ON CONFLICT DO NOTHING` pattern. Alternatively, use a Redis `SET NX` "
            "lock to serialize requests with the same key before they reach the database."
        ),
        "postmortem": "https://postmortems.internal/prism/idempotency-race",
        "affected_components": "payment-gateway, redis-cache",
    },
    {
        "title": "Unhandled Exception Exposes Internal Stack Trace to Client",
        "severity": "medium",
        "root_cause": (
            "A missing try/except block in the profile update endpoint allowed unhandled "
            "SQLAlchemy exceptions to propagate to the HTTP response body as raw Python "
            "tracebacks, exposing database schema details and file paths to end users."
        ),
        "fix": (
            "Wrap all database operations in try/except blocks. Register a global FastAPI "
            "exception handler: `@app.exception_handler(Exception)` that returns a generic "
            "`500 Internal Server Error` without leaking stack traces. Enable structured "
            "logging to capture full tracebacks server-side."
        ),
        "postmortem": "https://postmortems.internal/prism/stacktrace-leak",
        "affected_components": "user-profile-api, error-handler",
    },
]


def wake_up_server():
    """Ping the server repeatedly until it responds (handles Render cold starts)."""
    print("⏳ Waking up server (Render free tier may need ~60s to start)...")
    for attempt in range(1, 13):  # try for up to 60 seconds
        try:
            res = httpx.get(f"{BASE_URL}/incidents", timeout=30)
            if res.status_code in (200, 307, 404):
                print(f"✅ Server is awake! (attempt {attempt})")
                return True
        except Exception:
            pass
        import time
        print(f"   Still waking up... ({attempt}/12)")
        time.sleep(5)
    print("❌ Server did not respond after 60 seconds. Check Render logs.")
    return False


def seed():
    print(f"\n{'='*55}")
    print(f"  PRISM Database Seeder")
    print(f"  Target: {BASE_URL}")
    print(f"{'='*55}\n")

    # Wake up the server first (important for Render free tier)
    if not wake_up_server():
        sys.exit(1)

    # Check existing incidents
    try:
        existing_res = httpx.get(f"{BASE_URL}/incidents", timeout=30)
        if existing_res.status_code == 200:
            existing_count = len(existing_res.json().get("incidents", []))
            if existing_count > 0:
                print(f"ℹ️  Database already has {existing_count} incidents.")
                confirm = input("   Seed additional demo incidents anyway? (y/N): ").strip().lower()
                if confirm != "y":
                    print("Seeding skipped.")
                    return
    except Exception:
        pass  # proceed anyway

    print(f"\nSeeding {len(DEMO_INCIDENTS)} demo incidents...\n")

    success = 0
    for i, incident in enumerate(DEMO_INCIDENTS, 1):
        try:
            res = httpx.post(
                f"{BASE_URL}/incidents",
                json=incident,
                timeout=60
            )
            if res.status_code == 200:
                saved = res.json()
                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(incident["severity"], "⚪")
                print(f"  {sev_icon} [{i}/{len(DEMO_INCIDENTS)}] #{saved['id']} — {saved['title']}")
                success += 1
            else:
                print(f"  ❌ [{i}/{len(DEMO_INCIDENTS)}] Failed ({res.status_code}): {incident['title']}")
        except Exception as e:
            print(f"  ❌ [{i}/{len(DEMO_INCIDENTS)}] Error: {e}")

    print(f"\n{'='*55}")
    print(f"  ✅ Seeded {success}/{len(DEMO_INCIDENTS)} incidents successfully!")
    print(f"  🌐 View dashboard: {BASE_URL}/dashboard")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    seed()
