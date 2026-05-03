# Bob Task Orchestrator

Turn any developer goal into AI-orchestrated, actionable tasks directly inside Bob IDE—eliminating context switching and accelerating development velocity.

## Quick Start

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open `bob-plugin/panel.html` in Bob IDE as a sidebar panel.

## Demo Goals

1. **"Add input validation and error handling to all API endpoints in this FastAPI project"**

2. **"Write unit tests for the authentication module covering login, logout and token expiry edge cases"**

3. **"Refactor the database layer to use connection pooling and add query logging for debugging"**

## Architecture

Bob Task Orchestrator uses FastAPI for the backend API, SQLite for lightweight data persistence, and IBM watsonx.ai Granite model for intelligent task decomposition. The frontend is a self-contained HTML panel that integrates seamlessly into Bob IDE's sidebar, providing real-time task tracking and execution without leaving the development environment.

## Hackathon Theme Alignment

**"Turn idea into impact faster"**

- **Zero Context Switching**: Developers describe goals and execute tasks entirely within Bob IDE—no jumping between JIRA, GitHub, or documentation
- **AI-Powered Planning**: IBM watsonx Granite automatically breaks down complex goals into 3-5 concrete, actionable tasks in seconds
- **Instant Execution**: One-click task execution generates Bob-ready prompts, eliminating the "what do I do next?" paralysis and keeping momentum high

---

**Optional**: Set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` environment variables to use IBM watsonx.ai. Otherwise, the system automatically falls back to intelligent mock task generation.
