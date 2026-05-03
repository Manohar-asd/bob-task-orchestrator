"""
FastAPI Application for Bob Task Orchestrator (BTO)

Main API server that provides endpoints for:
- Health checks
- Goal creation and retrieval
- Task management and execution
- Integration with watsonx AI for task planning
"""

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import database functions
from db import get_all_goals, get_goal, get_tasks_by_goal, init_db, insert_goal, insert_task

# Import service functions
from executor import run_task
from planner import decompose_goal

# Import Pydantic models
from models import Goal, GoalCreate, HealthResponse, Task, TaskRunResponse


# Initialize FastAPI app
app = FastAPI(
    title="Bob Task Orchestrator API",
    description="AI-powered task management for IBM Bob IDE",
    version="1.0.0"
)

# Enable CORS for all origins (hackathon/development use)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for hackathon demo
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize the database on application startup.
    Creates tables if they don't exist.
    """
    print("🚀 Starting Bob Task Orchestrator API...")
    init_db()
    print("✅ Database initialized successfully")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint to verify API is running.
    
    Returns:
        Health status with timestamp, version, and mock mode indicator
    """
    # Check if watsonx API key is configured
    api_key = os.getenv("WATSONX_API_KEY", "").strip()
    mock_mode = not bool(api_key)
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "mock_mode": mock_mode
    }


@app.post("/goals")
async def create_goal(goal_request: GoalCreate) -> dict[str, Any]:
    """
    Create a new goal and decompose it into tasks using AI.
    
    Flow:
    1. Call AI planner to decompose goal into tasks
    2. Insert goal into database
    3. Insert all generated tasks into database
    4. Return goal with tasks
    
    Args:
        goal_request: GoalCreate model with goal text
    
    Returns:
        Dictionary with goal_id, text, and list of tasks
    
    Raises:
        HTTPException 500: If AI planning fails
    """
    try:
        # Step 1: Decompose goal into tasks using AI
        tasks_data = decompose_goal(goal_request.text)
        
        # Step 2: Insert goal into database
        goal_id = insert_goal(goal_request.text)
        
        # Step 3: Insert all tasks into database
        created_tasks = []
        for idx, task_data in enumerate(tasks_data, start=1):
            task_id = insert_task(
                goal_id=goal_id,
                title=task_data["title"],
                description=task_data["description"],
                order=idx
            )
            created_tasks.append({
                "id": task_id,
                "goal_id": goal_id,
                "title": task_data["title"],
                "description": task_data["description"],
                "order": idx,
                "status": "pending"
            })
        
        # Step 4: Return goal with tasks
        return {
            "goal_id": goal_id,
            "text": goal_request.text,
            "tasks": created_tasks
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create goal and generate tasks: {str(e)}"
        )


@app.get("/goals")
async def list_goals() -> list[dict[str, Any]]:
    """
    Retrieve all goals with task statistics.
    
    Returns:
        List of goals with task counts and completion status
    """
    return get_all_goals()


@app.get("/goals/{goal_id}/tasks")
async def get_goal_tasks(goal_id: int) -> list[dict[str, Any]]:
    """
    Retrieve all tasks for a specific goal.
    
    Args:
        goal_id: The ID of the goal
    
    Returns:
        List of tasks ordered by execution order
    
    Raises:
        HTTPException 404: If goal does not exist
    """
    # Check if goal exists
    goal = get_goal(goal_id)
    if not goal:
        raise HTTPException(
            status_code=404,
            detail=f"Goal with id {goal_id} not found"
        )
    
    # Return tasks for the goal
    return get_tasks_by_goal(goal_id)


@app.post("/tasks/{task_id}/run")
async def execute_task(task_id: int) -> dict[str, Any]:
    """
    Execute a task by marking it as running and generating a Bob prompt.
    
    Flow:
    1. Call executor to run the task
    2. If result contains error, raise HTTPException
    3. Otherwise return the result
    
    Args:
        task_id: The ID of the task to execute
    
    Returns:
        Dictionary with status, task_id, and bob_prompt
    
    Raises:
        HTTPException 400: If task execution fails
    """
    result = run_task(task_id)
    
    # Check if execution failed
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
    
    return result


# Run the application
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

# Made with Bob
