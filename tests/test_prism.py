import os
import shutil
import asyncio

# Override DATABASE_URL to use SQLite for verification
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# Clear any existing test database and chroma db to start clean
if os.path.exists("./test.db"):
    os.remove("./test.db")
if os.path.exists("./chroma_db"):
    shutil.rmtree("./chroma_db")

# Import TestClient and the app/endpoints/memory/database
from fastapi.testclient import TestClient
from app.main import app
from app import memory

client = TestClient(app)

print("--- Step 1: Adding 3 sample incidents via POST /incidents endpoint ---")
incidents = [
    {
        "title": "Negative Balance Bug",
        "severity": "high",
        "root_cause": "missing balance validation",
        "fix": "Check if user has sufficient funds before processing debit",
        "postmortem": "https://postmortems.internal/neg-balance",
        "affected_components": "payment-api"
    },
    {
        "title": "SQL Injection in search",
        "severity": "critical",
        "root_cause": "unsanitized user input",
        "fix": "Use parameterized queries in all search requests",
        "postmortem": "https://postmortems.internal/sql-inj",
        "affected_components": "search-service"
    },
    {
        "title": "Double Charge Bug",
        "severity": "high",
        "root_cause": "missing idempotency check",
        "fix": "Implement idempotency keys for all debit transactions",
        "postmortem": "https://postmortems.internal/double-charge",
        "affected_components": "payment-gateway"
    }
]

for idx, inc in enumerate(incidents, start=1):
    response = client.post("/incidents", json=inc)
    assert response.status_code == 200, f"Failed to post incident {idx}"
    saved = response.json()
    print(f"Added Incident {saved['id']}: {saved['title']} (Severity: {saved['severity']})")

print("\n--- Step 2: Simulating a fake PR diff that modifies a payment function ---")
fake_diff = """
diff --git a/payment.py b/payment.py
index a123456..b789012 100644
--- a/payment.py
+++ b/payment.py
@@ -10,5 +10,6 @@ def process_payment(user_id, amount):
-    balance = get_balance(user_id)
-    new_balance = balance - amount
+    # Process transaction without validation
+    new_balance = get_balance(user_id) - amount
     update_balance(user_id, new_balance)
"""
print("Fake PR diff created.")

print("\n--- Step 3: Calling search_similar_incidents() directly and printing the top matches ---")
matches = memory.search_similar_incidents(fake_diff, n_results=3)
print(f"Chroma DB search returned {len(matches)} matches:")
for idx, match in enumerate(matches, start=1):
    print(f"\nMatch {idx}:\n{match}")

print("\n--- Step 4: Calling review_with_groq() with the fake diff and matched incidents ---")
from app.main import review_with_groq

groq_key = os.getenv("GROQ_API_KEY")
# If the key is the default placeholder or not set, mock the Groq API call to avoid API authentication failure during testing
if not groq_key or "your_groq_api_key" in groq_key or groq_key == "":
    print("[TEST] Using mocked review_with_groq because no valid GROQ_API_KEY was found.")
    async def mock_review_with_groq(diff, incidents):
        return (
            "- WARNING: This PR resembles a past incident!\n"
            "- Specifically: 'Negative Balance Bug' where balance validation was missing.\n"
            "- Please add validation to ensure get_balance(user_id) - amount is not negative."
        )
    review_func = mock_review_with_groq
else:
    review_func = review_with_groq

review = asyncio.run(review_func(fake_diff, matches))
print(f"Review Output:\n{review}")

print("\n--- Step 5: Printing verification message ---")
if matches and review:
    print("PRISM memory is working!")

# Clean up database files
if os.path.exists("./test.db"):
    try:
        os.remove("./test.db")
    except Exception:
        pass
if os.path.exists("./chroma_db"):
    try:
        shutil.rmtree("./chroma_db")
    except Exception:
        pass
