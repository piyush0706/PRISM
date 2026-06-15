"""
PRISM - AI-Powered GitHub PR Code Review Bot
FastAPI application entry point.
"""

import os

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import database
import memory

load_dotenv()

app = FastAPI(

    title="PRISM",
    description="An AI-powered GitHub Pull Request code review bot using Groq.",
    version="0.1.0",
)

PR_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}

REVIEWS_COUNT = 0



@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "PRISM - PR Review Bot"}


class IncidentCreate(BaseModel):
    title: str
    severity: str
    root_cause: str
    fix: str
    postmortem: str
    affected_components: str


@app.post("/incidents")
async def create_new_incident(incident: IncidentCreate):
    """
    Accepts JSON body, saves it to PostgreSQL via database.py,
    embeds it in Chroma via memory.py, and returns the saved incident with its ID.
    """
    try:
        # Save to PostgreSQL
        saved_incident = database.create_incident(
            title=incident.title,
            severity=incident.severity,
            root_cause=incident.root_cause,
            fix=incident.fix,
            postmortem=incident.postmortem,
            affected_components=incident.affected_components
        )
        
        # Save to Chroma Vector DB
        memory.embed_incident(
            id=str(saved_incident.id),
            title=saved_incident.title,
            root_cause=saved_incident.root_cause,
            fix=saved_incident.fix,
            postmortem=saved_incident.postmortem
        )
        
        return {
            "id": saved_incident.id,
            "title": saved_incident.title,
            "severity": saved_incident.severity,
            "root_cause": saved_incident.root_cause,
            "fix": saved_incident.fix,
            "postmortem": saved_incident.postmortem,
            "affected_components": saved_incident.affected_components,
            "created_at": saved_incident.created_at
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRISM - Memory Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            
            --critical: #ef4444;
            --high: #f97316;
            --medium: #eab308;
            --low: #10b981;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(168, 85, 247, 0.1) 0px, transparent 50%);
        }
        
        header {
            padding: 2.5rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }
        
        .logo-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .logo-icon {
            font-size: 2rem;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        
        .logo-text h1 {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        
        .logo-text p {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: #34d399;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 12px #10b981;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        
        main {
            flex: 1;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            padding: 2.5rem 2rem;
            display: flex;
            flex-direction: column;
            gap: 2.5rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
        }
        
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 12px 24px -10px var(--primary-glow);
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .stat-val {
            font-size: 2.25rem;
            font-weight: 700;
            letter-spacing: -0.05em;
        }
        
        .stat-desc {
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        
        .table-section {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.75rem;
            backdrop-filter: blur(12px);
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .section-title h2 {
            font-size: 1.25rem;
            font-weight: 700;
        }
        
        .section-title p {
            font-size: 0.875rem;
            color: var(--text-muted);
        }
        
        .incidents-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        
        .incidents-table th {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
        }
        
        .incidents-table td {
            padding: 1.25rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.95rem;
        }
        
        .incidents-table tr:last-child td {
            border-bottom: none;
        }
        
        .severity-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .severity-critical { background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }
        .severity-high { background: rgba(249, 115, 22, 0.12); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.2); }
        .severity-medium { background: rgba(234, 179, 8, 0.12); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.2); }
        .severity-low { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
        
        .empty-state {
            padding: 4rem 2rem;
            text-align: center;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }
        
        .empty-icon {
            font-size: 3rem;
            opacity: 0.5;
        }
        
        footer {
            padding: 2rem;
            text-align: center;
            font-size: 0.875rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
            margin-top: auto;
        }
        
        .id-cell {
            font-family: monospace;
            color: var(--primary);
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-container">
            <div class="logo-icon">PRISM</div>
            <div class="logo-text">
                <h1>Incident Memory System</h1>
                <p>GitHub PR Risk Prevention</p>
            </div>
        </div>
        <div class="status-badge">
            <div class="status-dot"></div>
            SYSTEM ACTIVE
        </div>
    </header>
    
    <main>
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-label">Total Incidents Stored</span>
                <span class="stat-val">{total_incidents}</span>
                <span class="stat-desc">Structured & Vectorized memory size</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Pull Requests Reviewed</span>
                <span class="stat-val">{prs_reviewed}</span>
                <span class="stat-desc">Total processed since startup</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">System Memory State</span>
                <span class="stat-val" style="color: #6366f1; font-size: 1.75rem; padding-top: 0.5rem;">Synchronized</span>
                <span class="stat-desc">SQL & Chroma in-sync</span>
            </div>
        </div>
        
        <div class="table-section">
            <div class="section-header">
                <div class="section-title">
                    <h2>Logged Production Incidents</h2>
                    <p>Database of historical bugs utilized during pull request analysis</p>
                </div>
            </div>
            
            {table_content}
        </div>
    </main>
    
    <footer>
        <p>&copy; 2026 PRISM — AI Incident Memory & PR Prevention System. All rights reserved.</p>
    </footer>
</body>
</html>"""


@app.get("/dashboard")
async def get_dashboard(request: Request):
    """
    Returns statistics and a list of all logged incidents,
    as well as the total count of PRs reviewed. Served as HTML for browser,
    or JSON for programmatic queries.
    """
    try:
        # Fetch all incidents from PostgreSQL/SQLite
        all_incidents = database.get_all_incidents()
        
        # Serialize to include only id, title, severity, created_at
        incidents_list = []
        for incident in all_incidents:
            incidents_list.append({
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity,
                "created_at": incident.created_at.isoformat() if incident.created_at else None
            })
            
        global REVIEWS_COUNT
        
        accept = request.headers.get("accept", "")
        if "text/html" not in accept:
            # Return JSON for programmatic requests (like curl)
            return JSONResponse(content={
                "total_incidents": len(incidents_list),
                "incidents": incidents_list,
                "prs_reviewed": REVIEWS_COUNT,
                "reviews_message": f"PRISM has reviewed {REVIEWS_COUNT} PRs so far."
            })
            
        # Format HTML Table Content
        if incidents_list:
            rows = ""
            for inc in incidents_list:
                severity_class = f"severity-{inc['severity'].lower()}"
                rows += f"""
                <tr>
                    <td class="id-cell">#{inc['id']}</td>
                    <td><strong>{inc['title']}</strong></td>
                    <td><span class="severity-badge {severity_class}">{inc['severity']}</span></td>
                    <td>{inc['created_at'][:19].replace('T', ' ') if inc['created_at'] else 'N/A'}</td>
                </tr>
                """
            table_html = f"""
            <table class="incidents-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Incident Title</th>
                        <th>Severity</th>
                        <th>Log Date</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        else:
            table_html = """
            <div class="empty-state">
                <div class="empty-icon">📂</div>
                <p>No incidents registered yet. Log an incident to populate the memory database.</p>
            </div>
            """
            
        html_content = DASHBOARD_HTML_TEMPLATE \
            .replace("{total_incidents}", str(len(incidents_list))) \
            .replace("{prs_reviewed}", str(REVIEWS_COUNT)) \
            .replace("{table_content}", table_html)
        return HTMLResponse(content=html_content)
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))




# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"


async def get_pr_diff(repo: str, pr_number: int) -> str:
    """
    Fetch the raw unified diff for a pull request from the GitHub API.

    Args:
        repo:       Full repository name, e.g. "username/repo".
        pr_number:  The pull request number.

    Returns:
        The raw diff text as a string.

    Raises:
        HTTPException: If the GitHub API request fails.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not configured.")

    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, follow_redirects=True)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error: {response.text}",
        )

    return response.text


async def post_github_comment(repo: str, pr_number: int, review: str, similar_incidents: list[str]) -> None:
    """
    Post a formatted review comment on a GitHub pull request issue thread.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not configured.")

    # Format similar incidents list
    incidents_text = ""
    if similar_incidents:
        for incident_text in similar_incidents:
            title = "Unknown"
            root_cause = "Unknown"
            for line in incident_text.split("\n"):
                if line.startswith("Title: "):
                    title = line[len("Title: "):].strip()
                elif line.startswith("Root Cause: "):
                    root_cause = line[len("Root Cause: "):].strip()
            incidents_text += f"- **Title**: {title}\n  **Root Cause**: {root_cause}\n"
    else:
        incidents_text = "No similar incidents found"

    comment_body = (
        "## 🔍 PRISM Code Review\n\n"
        "### ⚠️ Risk Assessment\n"
        f"{review}\n\n"
        "### 📚 Similar Past Incidents\n"
        f"{incidents_text.strip()}\n\n"
        "---\n"
        "*Powered by PRISM — AI Incident Memory & PR Prevention System*"
    )

    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json={"body": comment_body})

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to post comment: {response.text}",
        )


# ---------------------------------------------------------------------------
# Groq AI helpers
# ---------------------------------------------------------------------------

async def review_with_groq(diff: str, incidents: list[str]) -> str:
    """
    Send a PR diff and memory incidents to Groq and return an AI-generated code review.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    from groq import AsyncGroq
    client = AsyncGroq(api_key=api_key)

    if incidents:
        incidents_section = "PAST INCIDENTS FROM OUR SYSTEM:\n" + "\n\n".join(incidents)
        prompt = (
            "You are a senior code reviewer with memory of past incidents.\n\n"
            f"{incidents_section}\n\n"
            "Using the above incidents as context, review this PR diff.\n"
            "Find: bugs, missing validation, security issues, performance problems.\n"
            "If this PR resembles a past incident, explicitly warn about it.\n"
            "Be concise. Use bullet points.\n\n"
            f"PR DIFF:\n{diff}"
        )
    else:
        prompt = (
            "You are a senior code reviewer with memory of past incidents.\n\n"
            "Using the above incidents as context, review this PR diff.\n"
            "Find: bugs, missing validation, security issues, performance problems.\n"
            "If this PR resembles a past incident, explicitly warn about it.\n"
            "Be concise. Use bullet points.\n\n"
            f"PR DIFF:\n{diff}"
        )

    completion = await client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )
    return completion.choices[0].message.content


@app.post("/webhook")
async def github_webhook(request: Request):
    """
    Receives GitHub webhook events and triggers AI code review.
    Handles pull_request events with actions: opened, synchronize, reopened.
    Always returns {"status": "ok"} so GitHub does not retry on errors.
    """
    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "pull_request":
        action = payload.get("action", "")
        if action in PR_TRIGGER_ACTIONS:
            pr_number = payload["pull_request"]["number"]
            repo_full_name = payload["repository"]["full_name"]
            print(f"[PRISM] PR #{pr_number} '{action}' in {repo_full_name} — starting review...")

            try:
                diff = await get_pr_diff(repo_full_name, pr_number)
                print(f"[PRISM] Diff fetched ({len(diff)} chars). Fetching memory from Chroma...")

                # Fetch similar incidents from Chroma DB
                similar_incidents = memory.search_similar_incidents(diff, n_results=3)

                print(f"[PRISM] Found {len(similar_incidents)} similar incidents. Sending to Groq...")
                review = await review_with_groq(diff, similar_incidents)

                print(f"[PRISM] Groq review received. Posting comment...")
                await post_github_comment(repo_full_name, pr_number, review, similar_incidents)
                print(f"[PRISM] ✅ Review posted on PR #{pr_number} in {repo_full_name}")

                # Increment reviewed PRs counter
                global REVIEWS_COUNT
                REVIEWS_COUNT += 1

            except Exception as exc:
                print(f"[PRISM] ❌ Error reviewing PR #{pr_number}: {exc}")

    return {"status": "ok"}



if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
