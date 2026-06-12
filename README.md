# PRISM 🔍

**PRISM** is an AI-powered GitHub Pull Request code review bot. It automatically analyzes pull request diffs and posts intelligent, context-aware review comments using Groq.

---

## Features

- 🤖 AI-driven code review powered by **Groq (Llama 3.3)**
- 🔗 Integrates with the **GitHub API** to fetch PR diffs and post comments
- ⚡ Built with **FastAPI** for a fast, async webhook server
- 🔒 Secure token-based authentication for GitHub and Groq

---

## Project Structure

```
prism/
├── main.py           # FastAPI application entry point
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (secrets — do not commit)
└── README.md         # Project documentation
```

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd prism
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Fill in your credentials in the `.env` file:

```env
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
```

> ⚠️ **Never commit your `.env` file.** Add it to `.gitignore`.

### 5. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## API Endpoints

| Method | Endpoint | Description             |
|--------|----------|-------------------------|
| GET    | `/`      | Health check            |

*(More endpoints to be added as the bot logic is implemented.)*

---

## Tech Stack

| Technology          | Purpose                          |
|---------------------|----------------------------------|
| FastAPI             | Async web server / webhook handler |
| Uvicorn             | ASGI server                      |
| HTTPX               | Async HTTP client for GitHub API and Groq |
| python-dotenv       | Environment variable management  |

---

## License

MIT
