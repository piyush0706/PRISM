"""
PRISM - AI-Powered GitHub PR Code Review Bot
FastAPI application entry point.
"""

import os

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

load_dotenv()

app = FastAPI(
    title="PRISM",
    description="An AI-powered GitHub Pull Request code review bot using Groq.",
    version="0.1.0",
)

PR_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "PRISM - PR Review Bot"}


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


async def post_github_comment(repo: str, pr_number: int, body: str) -> None:
    """
    Post a review comment on a GitHub pull request issue thread.

    Args:
        repo:       Full repository name, e.g. "username/repo".
        pr_number:  The pull request number.
        body:       Markdown-formatted comment body.

    Raises:
        HTTPException: If the GitHub API request fails.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not configured.")

    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json={"body": body})

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to post comment: {response.text}",
        )


# ---------------------------------------------------------------------------
# Groq AI helpers
# ---------------------------------------------------------------------------

REVIEW_PROMPT_TEMPLATE = """\
You are a senior code reviewer. Review this PR diff.
Find: bugs, missing validation, security issues, performance problems.
Be concise. Use bullet points.

PR DIFF:
{diff}"""


async def review_with_groq(diff: str) -> str:
    """
    Send a PR diff to Groq and return an AI-generated code review.

    Args:
        diff: Raw unified diff string from the GitHub API.

    Returns:
        Groq's review as a plain text string.

    Raises:
        HTTPException: If GROQ_API_KEY is missing or the API call fails.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": REVIEW_PROMPT_TEMPLATE.format(diff=diff)
            }
        ],
        "temperature": 0.2
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data, timeout=30.0)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Groq API error: {response.text}",
        )

    result = response.json()
    return result["choices"][0]["message"]["content"]


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
                print(f"[PRISM] Diff fetched ({len(diff)} chars). Sending to Groq...")

                review = await review_with_groq(diff)
                print(f"[PRISM] Groq review received. Posting comment...")

                await post_github_comment(repo_full_name, pr_number, review)
                print(f"[PRISM] ✅ Review posted on PR #{pr_number} in {repo_full_name}")

            except Exception as exc:
                print(f"[PRISM] ❌ Error reviewing PR #{pr_number}: {exc}")

    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
