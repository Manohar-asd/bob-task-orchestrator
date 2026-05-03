"""
AI Planning Service for Bob Task Orchestrator (BTO)

This module handles goal decomposition using IBM watsonx.ai Granite model.
Falls back to mock task generation if API credentials are not available.

No dependencies on other project files - can be used standalone.
"""

import json
import os
import re
from typing import Any

_token_cache = None


def _strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences from JSON response.
    Handles both ```json and ``` patterns.
    
    Args:
        text: Raw text that may contain markdown fences
    
    Returns:
        Cleaned text without fences
    """
    # Remove ```json or ``` at start and ``` at end
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()


def _get_iam_token(api_key: str) -> str:
    import httpx
    import time
    global _token_cache
    now = time.time()
    if _token_cache and now - _token_cache["ts"] < 3000:
        return _token_cache["token"]
    resp = httpx.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey",
              "apikey": api_key},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache = {"token": token, "ts": now}
    return token


def _call_watsonx_api(goal_text: str, api_key: str, project_id: str) -> list[dict[str, str]]:
    import httpx
    
    url = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_iam_token(api_key)}"
    }
    
    body = {
        "model_id": "ibm/granite-4-h-small",
        "project_id": project_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""You are an expert software project planner. Break down the following goal into exactly 4 specific, actionable development tasks.

Goal: {goal_text}

Return ONLY a JSON array with exactly 4 tasks. Each task must have:
- "title": A concise task name (max 100 chars)
- "description": Detailed steps and requirements (2-3 sentences)

Return ONLY the JSON array, no other text, no markdown fences.
Example:
[
  {{"title": "Task title", "description": "Task description here."}}
]"""
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1
    }
    
    response = httpx.post(url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    generated_text = result["choices"][0]["message"]["content"]
    cleaned_text = _strip_markdown_fences(generated_text)
    tasks = json.loads(cleaned_text)
    
    if not isinstance(tasks, list):
        raise ValueError("Response is not a JSON array")
    
    for task in tasks:
        if not isinstance(task, dict) or "title" not in task or "description" not in task:
            raise ValueError("Invalid task structure in response")
    
    return tasks


def _generate_mock_tasks(goal_text: str) -> list[dict[str, str]]:
    """
    Generate realistic mock tasks based on the goal text.
    Used as fallback when watsonx API is not available.
    
    Args:
        goal_text: The goal description
    
    Returns:
        List of 4 task dictionaries with 'title' and 'description' keys
    """
    # Extract key terms from goal to make tasks more relevant
    goal_lower = goal_text.lower()
    
    # Determine project type based on keywords
    is_api = any(word in goal_lower for word in ["api", "rest", "endpoint", "backend"])
    is_frontend = any(word in goal_lower for word in ["ui", "frontend", "interface", "web", "react", "vue"])
    is_database = any(word in goal_lower for word in ["database", "db", "data", "storage"])
    is_auth = any(word in goal_lower for word in ["auth", "login", "user", "authentication"])
    
    # Generate contextual tasks
    tasks = []
    
    # Task 1: Setup/Planning
    if is_api:
        tasks.append({
            "title": "Set up project structure and dependencies",
            "description": "Initialize the project repository, set up virtual environment, install required packages (FastAPI, SQLAlchemy, etc.), and create the basic directory structure for the API."
        })
    elif is_frontend:
        tasks.append({
            "title": "Initialize frontend project and tooling",
            "description": "Set up the frontend framework, configure build tools (Vite/Webpack), install UI libraries, and establish the component structure and routing."
        })
    else:
        tasks.append({
            "title": "Project initialization and setup",
            "description": "Create project structure, initialize version control, set up development environment, and install necessary dependencies and tools."
        })
    
    # Task 2: Core Implementation
    if is_database:
        tasks.append({
            "title": "Design and implement database schema",
            "description": "Create database models, define relationships, set up migrations, and implement CRUD operations with proper indexing and constraints."
        })
    elif is_auth:
        tasks.append({
            "title": "Implement authentication system",
            "description": "Set up user registration and login endpoints, implement JWT token generation and validation, add password hashing, and create middleware for protected routes."
        })
    else:
        tasks.append({
            "title": "Implement core business logic",
            "description": "Develop the main functionality according to requirements, create necessary classes/functions, implement data processing logic, and ensure proper error handling."
        })
    
    # Task 3: Integration/Features
    if is_api:
        tasks.append({
            "title": "Create API endpoints and documentation",
            "description": "Implement RESTful endpoints for all CRUD operations, add request validation, set up automatic API documentation (Swagger/OpenAPI), and implement proper HTTP status codes."
        })
    elif is_frontend:
        tasks.append({
            "title": "Build user interface components",
            "description": "Create reusable UI components, implement forms with validation, add responsive design, integrate with backend API, and ensure accessibility standards."
        })
    else:
        tasks.append({
            "title": "Integrate components and add features",
            "description": "Connect different modules together, implement additional features, add configuration management, and ensure proper communication between components."
        })
    
    # Task 4: Testing/Deployment
    tasks.append({
        "title": "Testing, documentation, and deployment",
        "description": "Write unit and integration tests, create comprehensive documentation (README, API docs), set up CI/CD pipeline, and prepare deployment configuration for production environment."
    })
    
    return tasks


def decompose_goal(text: str) -> list[dict[str, str]]:
    """
    Decompose a high-level goal into actionable tasks.
    
    Attempts to use IBM watsonx.ai Granite API if credentials are available.
    Falls back to mock task generation if:
    - WATSONX_API_KEY or WATSONX_PROJECT_ID environment variables are missing/empty
    - API call fails (with one retry)
    
    Args:
        text: The goal description to decompose
    
    Returns:
        List of 4 task dictionaries, each with 'title' and 'description' keys
    """
    # Check for API credentials
    api_key = os.getenv("WATSONX_API_KEY", "").strip()
    project_id = os.getenv("WATSONX_PROJECT_ID", "").strip()
    
    # Use mock if credentials are missing
    if not api_key or not project_id:
        print("⚠️  watsonx credentials not found, using mock task generator")
        return _generate_mock_tasks(text)
    
    # Try watsonx API with one retry
    for attempt in range(2):
        try:
            print(f"🤖 Calling watsonx Granite API (attempt {attempt + 1}/2)...")
            tasks = _call_watsonx_api(text, api_key, project_id)
            print(f"✅ Successfully generated {len(tasks)} tasks from watsonx")
            return tasks
        except Exception as e:
            print(f"❌ watsonx API error (attempt {attempt + 1}/2): {e}")
            if attempt == 1:  # Last attempt failed
                print("⚠️  Falling back to mock task generator")
                return _generate_mock_tasks(text)
    
    # Should never reach here, but just in case
    return _generate_mock_tasks(text)

# Made with Bob
