# 🚀 PRISM: Quickstart Demo Guide

This guide walks you through verifying and demonstrating the features of PRISM.

---

## 🌐 Option 0: View the Live Deployed App (No Setup Required)

The fastest way to evaluate PRISM is to visit the live production deployment on Render:

| Endpoint | URL |
|---|---|
| **Dashboard UI** | https://prism-ldxm.onrender.com/dashboard |
| **Health Check** | https://prism-ldxm.onrender.com/health |
| **Swagger API Docs** | https://prism-ldxm.onrender.com/docs |
| **Incidents JSON** | https://prism-ldxm.onrender.com/incidents |

The `/health` endpoint instantly confirms that the server, PostgreSQL database, Groq API, and GitHub token are all live and operational.

---

## 🛠️ Method 1: The Automated Console Test (`tests/test_prism.py`)

We have packaged a complete, isolated verification pipeline in `tests/test_prism.py`. It creates a temporary database, seeds incidents, executes vector searches, and prints the AI code review.

### How to Run:
From the project root folder, execute:
```bash
PYTHONPATH=. python3 tests/test_prism.py
```

### Expected Output Structure:
```text
--- Step 1: Adding 3 sample incidents via POST /incidents endpoint ---
Added Incident 1: Negative Balance Bug (Severity: high)
Added Incident 2: SQL Injection in search (Severity: critical)
Added Incident 3: Double Charge Bug (Severity: high)

--- Step 2: Simulating a fake PR diff that modifies a payment function ---
Fake PR diff created.

--- Step 3: Calling search_similar_incidents() directly and printing the top matches ---
Chroma DB search returned 3 matches:

Match 1:
Title: Negative Balance Bug
Root Cause: missing balance validation
Fix: Check if user has sufficient funds before processing debit
Postmortem: https://postmortems.internal/neg-balance

Match 2:
...

--- Step 4: Calling review_with_groq() with the fake diff and matched incidents ---
Review Output:
- WARNING: This PR resembles a past incident!
- Specifically: 'Negative Balance Bug' where balance validation was missing.
- Please add validation to ensure get_balance(user_id) - amount is not negative.

--- Step 5: Printing verification message ---
PRISM memory is working!
```

---

## 📊 Method 2: Live Web App & Incident Dashboard

Explore the live API and interactive memory dashboard using a local web server.

### 1. Launch the FastAPI server
```bash
python3 -m app.main
```
*The server will start running on port `8080` (`http://localhost:8080`).*

### 2. Check the Health Endpoint
Before opening the dashboard, confirm all services are running:
```bash
curl http://localhost:8080/health
```
Expected response:
```json
{
  "status": "ok",
  "database": {"status": "connected", "db_type": "SQLite"},
  "groq_configured": true,
  "github_configured": true
}
```

### 3. Open the Memory Dashboard
Open your browser and navigate to: **[http://localhost:8080/dashboard](http://localhost:8080/dashboard)**

You will see:
* **Stat Cards:** Total Reviews, Critical/High Issues, Medium Issues, and Active Incidents counters.
* **Severity Distribution Chart:** A bar chart breaking down incidents by severity level.
* **System Integration Status:** Live pinging indicators for FastAPI Server, PostgreSQL Database, and Groq Inference Engine.
* **Incidents Log Table:** Searchable grid displaying ID, Severity badge, Title, Affected Components, and timestamp.

---

### 3. Log a New Incident Live
You can simulate an engineering postmortem log entry by sending a JSON request to the incident API.

#### Using PowerShell (Windows):
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/incidents" -Method Post -ContentType "application/json" -Body '{
    "title": "Buffer Overflow in XML Parser",
    "severity": "critical",
    "root_cause": "unsafe memory allocation in raw byte streams",
    "fix": "Upgrade parser package and use bounded array reads",
    "postmortem": "https://postmortems.internal/xml-overflow",
    "affected_components": "core-parser"
}'
```

#### Using cURL (Linux/macOS):
```bash
curl -X POST http://localhost:8080/incidents \
     -H "Content-Type: application/json" \
     -d '{
         "title": "Buffer Overflow in XML Parser",
         "severity": "critical",
         "root_cause": "unsafe memory allocation in raw byte streams",
         "fix": "Upgrade parser package and use bounded array reads",
         "postmortem": "https://postmortems.internal/xml-overflow",
         "affected_components": "core-parser"
     }'
```

#### Verification:
Refresh the dashboard (`http://localhost:8080/dashboard`). You will see the **Buffer Overflow** incident added to the logs, and the **Total Incidents** counter incremented.

---

### 4. Trigger a Mock PR Webhook Review
You can simulate a GitHub pull request webhook trigger locally to watch the RAG process run.

#### Using PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/webhook" -Method Post -Headers @{"X-GitHub-Event"="pull_request"} -ContentType "application/json" -Body '{
    "action": "opened",
    "pull_request": {
        "number": 42
    },
    "repository": {
        "full_name": "test-user/payment-gateway"
    }
}'
```

#### Expected Server Console output:
Watch your terminal running the app package print the steps in real time:
```text
[PRISM] PR #42 'opened' in test-user/payment-gateway — starting review...
[PRISM] Diff fetched (341 chars). Fetching memory from Chroma...
[PRISM] Found 3 similar incidents. Sending to Groq...
[PRISM] Groq review received. Posting comment...
[PRISM] ✅ Review posted on PR #42 in test-user/payment-gateway
```
*Note: The actual posting of the GitHub comment will gracefully fail if your `GITHUB_TOKEN` is a mock placeholder, but the pipeline execution completes successfully.*
