# 📖 PRISM: Project Overview & Vision

> **Incident-Memory PR Prevention System** — Bridging the gap between production telemetry, postmortems, and pull request reviews.

---

## 🚨 The Problem: The "Memory Loss" in Modern Software Teams

Every engineering team has experienced this nightmare: **A critical bug is deployed to production, resolved, and documented in a postmortem. A few weeks later, a different developer writes similar code, and the exact same bug is redeployed.** 

This happens because:
* **Knowledge Silos:** Postmortem logs, incident tickets, and Jira boards live in isolated systems. Developers rarely read them before submitting pull requests.
* **Review Blindness:** Code reviewers evaluate incoming code diffs statically. They might spot syntax issues or minor style violations, but they miss domain-specific logical risks.
* **LLM Shortcomings:** Standard AI code review bots (like generic ChatGPT integrations) read code in a vacuum. They are trained on open-source code but know absolutely nothing about your team's historical bugs, legacy API quirks, or past operational failures.

---

## 💡 The Solution: PRISM's Incident Memory

**PRISM** (Pull Request Incident Semantic Memory) solves this problem by giving your code review bot **long-term memory**.

PRISM works as a digital guardian that bridges the gap between post-incident analysis and pre-deployment code review:

```
[Production Incident] ──> [Logged to PRISM Database] ──> [Vectorized in ChromaDB]
                                                                │
                                                                ▼
[New Pull Request] ───────> [Semantic Memory Search] ───> [AI Context Review] ───> [PR Warning]
```

### 1. Unified Incident Logging
When an incident is resolved, the team logs it via PRISM's REST API or Web Dashboard. The log captures:
* The **Root Cause** of the incident.
* The **Fix** applied.
* The internal **Postmortem Link** and **Affected Components**.

### 2. Semantic Indexing (Vector DB)
The incident's technical details are compiled into a dense text representation and embedded using vector embeddings. This is indexed inside **ChromaDB**, an open-source vector database.

### 3. Contextual Retrieval-Augmented Generation (RAG)
When a developer opens or updates a Pull Request:
1. PRISM's FastAPI webhook is triggered by GitHub.
2. PRISM fetches the raw PR unified diff.
3. PRISM queries ChromaDB using the **raw code diff** as a semantic query to find up to 3 similar historical incidents.
4. If similar incidents are found, their details (including root cause and fix) are injected directly into the LLM context.
5. **Groq Llama-3-70B** reviews the code, specifically instructed: *"If this PR resembles a past incident, explicitly warn the developer."*
6. PRISM posts the detailed assessment directly as a comment on the GitHub PR thread.

---

## ✨ Why PRISM is Different (USPs)

| Feature | Standard AI Reviewers | Static Analysis (Linters) | PRISM |
| :--- | :--- | :--- | :--- |
| **Code Structure Checks** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Domain-Specific Logic** | ❌ No | ❌ No | ✅ Yes (Learns from logs) |
| **Historical Bug Memory** | ❌ No | ❌ No | ✅ Yes (Semantic Vector RAG) |
| **Telemetry & Postmortem Link**| ❌ No | ❌ No | ✅ Yes (Direct link references) |
| **Zero-Config Local Testing** | ❌ No | ⚠️ Varies | ✅ Yes (SQLite/Chroma local fallback)|

---

## 💡 Key Innovations

1. **Diff-to-Incident Vector RAG:** Instead of searching text-to-text, PRISM performs **code-to-incident semantic search**. It matches structural changes in git diffs against natural language descriptions of incident root causes.
2. **Double-Store Synchronization:** By pairing **PostgreSQL** (relational database for audit logs and tabular metrics) with **ChromaDB** (vector search engine), PRISM guarantees robust reporting alongside intelligent semantic retrieval.
3. **Groq-Accelerated Reviews:** By running on the Groq Inference Engine (`llama3-70b-8192`), PRISM generates reviews in seconds, ensuring CI/CD pipelines are not delayed.

---

## 🔮 Future Scope & Roadmap

PRISM is built as a modular framework designed to scale. Our roadmap includes:

* **🔌 Automated Sentry & PagerDuty Connectors:** Automatically populate PRISM's incident memory when an alert is triggered in Sentry or PagerDuty, eliminating manual entry.
* **🛠️ Self-Healing PRs:** Enable PRISM to write a suggested git patch resolving the risk, allowing developers to commit the fix with a single click.
* **📈 Multi-Repo Context Sharing:** Share incident memory across microservices. If Service A has a thread-safety issue, Service B's PR reviews will automatically benefit from that learning.
* **🔒 On-Premise LLM Support:** Support offline vector databases and local LLM models (e.g., Llama-3 running on Ollama) for companies with strict code privacy requirements.
