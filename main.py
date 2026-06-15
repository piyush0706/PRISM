"""
=========================================================
PRISM
AI-Powered PR Reviewer with Organizational Memory

Core Features:
- GitHub Webhook Integration
- Incident Storage Layer
- ChromaDB Memory Retrieval
- Groq-Powered Risk Analysis
- Dashboard & Analytics

Built for OSC AI Build 1.0
=========================================================
"""

import os

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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



@app.get("/")
async def root():
    """Redirect to the dashboard by default."""
    return RedirectResponse(url="/dashboard")


# =========================================
# Health Check Endpoint
# Verifies server + database connectivity
# =========================================
@app.get("/health")
async def health_check():
    """
    Returns the live health status of PRISM and its dependencies.
    Useful for judges, Render health checks, and uptime monitors.
    """
    db_status = database.get_db_status()
    return JSONResponse(content={
        "status": "ok",
        "service": "PRISM AI Code Review Bot",
        "version": "1.0.0",
        "database": db_status,
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "github_configured": bool(os.getenv("GITHUB_TOKEN")),
    })

# =========================================
# Incident Storage Layer
# Stores production incidents and postmortems
# =========================================
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


@app.get("/incidents")
async def get_all_incidents_endpoint():
    """
    Fetches all incidents from PostgreSQL and returns them as a JSON list.
    """
    try:
        all_incidents = database.get_all_incidents()
        incidents_list = []
        for incident in all_incidents:
            incidents_list.append({
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity,
                "root_cause": incident.root_cause,
                "fix": incident.fix,
                "postmortem": incident.postmortem,
                "affected_components": incident.affected_components,
                "created_at": incident.created_at.isoformat() if incident.created_at else None
            })
        return {"incidents": incidents_list}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/incidents/{incident_id}")
async def delete_incident_endpoint(incident_id: int):
    """
    Deletes an incident from PostgreSQL and the Chroma DB collection by ID.
    """
    try:
        deleted = database.delete_incident(incident_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Also remove from Chroma DB
        memory.delete_incident(str(incident_id))
        
        return {"status": "success", "message": f"Incident {incident_id} successfully deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# =========================================
# Dashboard & Analytics Layer
# Visualizes incident memory and review stats
# =========================================
@app.get("/dashboard")
async def get_dashboard(request: Request):
    """
    Serves the premium HTML dashboard template from templates/dashboard.html.
    If programmatic client accepts JSON, returns stats and list of incidents.
    """
    try:
        accept = request.headers.get("accept", "")
        if "text/html" not in accept:
            all_incidents = database.get_all_incidents()
            incidents_list = []
            for incident in all_incidents:
                incidents_list.append({
                    "id": incident.id,
                    "title": incident.title,
                    "severity": incident.severity,
                    "root_cause": incident.root_cause,
                    "fix": incident.fix,
                    "postmortem": incident.postmortem,
                    "affected_components": incident.affected_components,
                    "created_at": incident.created_at.isoformat() if incident.created_at else None
                })
            
        global_reviews = database.get_counter("prs_reviewed")
            return JSONResponse(content={
                "total_incidents": len(incidents_list),
                "incidents": incidents_list,
                "prs_reviewed": global_reviews,
                "reviews_message": f"PRISM has reviewed {global_reviews} PRs so far."
            })

        template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))




# =========================================
# GitHub Integration Layer
# Fetches PR diffs and posts AI reviews
# =========================================
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


# =========================================
# AI Review Engine
# Memory-Augmented Risk Analysis using Groq
# =========================================
async def review_with_groq(diff: str, incidents: list[str]) -> str:
    """
    Send a PR diff and memory incidents to Groq and return an AI-generated code review.
    Instructs the AI to output critical incidents inside a <prism_incident> XML tag.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    from groq import AsyncGroq
    client = AsyncGroq(api_key=api_key)

    incidents_section = ""
    if incidents:
        incidents_section = "PAST INCIDENTS FROM OUR SYSTEM:\n" + "\n\n".join(incidents) + "\n\n"

    prompt = (
        "You are a senior code reviewer with memory of past incidents.\n\n"
        f"{incidents_section}"
        "Using any past incidents as context, review this PR diff.\n"
        "Find: bugs, missing validation, security issues, performance problems.\n"
        "If this PR resembles a past incident, explicitly warn about it.\n"
        "Be concise. Use bullet points.\n\n"
        "CRITICAL AUTO-LOGGING REQUIREMENT:\n"
        "If and only if you find any CRITICAL or HIGH severity security vulnerabilities, data leaks, or fatal bugs in the PR diff, "
        "you must output a structured JSON block wrapped inside '<prism_incident>' and '</prism_incident>' tags at the very bottom of your response. "
        "Otherwise, do not include the tag.\n"
        "The JSON block must have this format:\n"
        "{\n"
        "  \"title\": \"Short clear title of the vulnerability/bug found\",\n"
        "  \"severity\": \"critical\" or \"high\",\n"
        "  \"root_cause\": \"Technical cause of the issue\",\n"
        "  \"fix\": \"Specific recommended code fix\",\n"
        "  \"postmortem\": \"Actionable prevention advice to avoid this in the future\",\n"
        "  \"affected_components\": \"Comma-separated names of files or modules affected\"\n"
        "}\n\n"
        f"PR DIFF:\n{diff}"
    )

    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )
    return completion.choices[0].message.content

# =========================================
# Webhook Processing Pipeline
# Entry point for GitHub Pull Requests
# =========================================
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
                review_content = await review_with_groq(diff, similar_incidents)

                # Parse and extract structured incident if present
                incident_data = None
                clean_review = review_content
                if "<prism_incident>" in review_content and "</prism_incident>" in review_content:
                    try:
                        start_idx = review_content.find("<prism_incident>") + len("<prism_incident>")
                        end_idx = review_content.find("</prism_incident>")
                        json_str = review_content[start_idx:end_idx].strip()
                        
                        import json
                        incident_data = json.loads(json_str)
                        
                        # Strip the tag from the posted comment so the user doesn't see raw JSON
                        clean_review = review_content[:review_content.find("<prism_incident>")].strip()
                    except Exception as parse_err:
                        print(f"[PRISM] ⚠️ Failed to parse auto-incident JSON: {parse_err}")

                print(f"[PRISM] Groq review received. Posting comment...")
                await post_github_comment(repo_full_name, pr_number, clean_review, similar_incidents)
                print(f"[PRISM] ✅ Review posted on PR #{pr_number} in {repo_full_name}")

                # If an incident was detected, save it!
                if incident_data:
                    try:
                        saved_inc = database.create_incident(
                            title=incident_data.get("title", "AI Auto-Logged Incident"),
                            severity=incident_data.get("severity", "high"),
                            root_cause=incident_data.get("root_cause", ""),
                            fix=incident_data.get("fix", ""),
                            postmortem=incident_data.get("postmortem", ""),
                            affected_components=incident_data.get("affected_components", "")
                        )
                        # Also embed it in Chroma
                        memory.embed_incident(
                            id=str(saved_inc.id),
                            title=saved_inc.title,
                            root_cause=saved_inc.root_cause,
                            fix=saved_inc.fix,
                            postmortem=saved_inc.postmortem
                        )
                        print(f"[PRISM] 🤖 Automatically logged critical incident #{saved_inc.id} to DB & Chroma!")
                    except Exception as db_err:
                        print(f"[PRISM] ❌ Failed to auto-log incident: {db_err}")

                # Increment reviewed PRs counter (persisted in PostgreSQL)
                database.increment_counter("prs_reviewed")

            except Exception as exc:
                print(f"[PRISM] ❌ Error reviewing PR #{pr_number}: {exc}")

    return {"status": "ok"}

# =========================================
# Application Entry Point
# =========================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
