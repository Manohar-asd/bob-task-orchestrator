"""
Task Execution Service for Bob Task Orchestrator (BTO)

This module handles task execution logic:
- Marks tasks as running
- Generates Bob-ready prompts
- Simulates task execution
- Updates task and goal statuses
- Handles errors gracefully
"""

import time
from typing import Any

from db import get_task, get_tasks_by_goal, update_goal_status, update_task


def _generate_bob_prompt(title: str, description: str) -> str:
    """
    Generate a formatted prompt for Bob IDE to execute a task.
    
    Args:
        title: Task title
        description: Task description
    
    Returns:
        Formatted prompt string ready for Bob
    """
    prompt = f"""## Bob Task: {title}

{description}

### Instructions for Bob IDE:
Please implement the above task. Write clean, well-commented code.
After completing, mark this task as done in the BTO panel."""
    
    return prompt


def run_task(task_id: int) -> dict[str, Any]:
    """
    Execute a task by marking it as running, generating a Bob prompt,
    and updating its status to done.
    
    Flow:
    1. Fetch task from database
    2. Validate task is in pending state
    3. Mark task as running
    4. Generate Bob prompt
    5. Simulate work (1 second delay)
    6. Mark task as done with the prompt
    7. Check if all tasks for the goal are done
    8. If all done, mark goal as done
    9. Return success response
    
    Args:
        task_id: The ID of the task to execute
    
    Returns:
        Dictionary with status, task_id, and bob_prompt on success
        Dictionary with error message on failure
    """
    try:
        # Step 1: Fetch task from database
        task = get_task(task_id)
        if not task:
            return {"error": "Task not found"}
        
        # Step 2: Validate task status
        if task["status"] != "pending":
            return {"error": "Task is not in pending state"}
        
        # Step 3: Mark task as running immediately
        update_task(task_id, status="running")
        
        # Step 4: Generate Bob prompt from task details
        bob_prompt = _generate_bob_prompt(task["title"], task["description"])
        
        # Step 5: Simulate work (in real scenario, this would be actual processing)
        time.sleep(1)
        
        # Step 6: Mark task as done with the generated prompt
        update_task(task_id, status="done", bob_prompt=bob_prompt)
        
        # Step 7: Check if all tasks for this goal are done
        goal_id = task["goal_id"]
        all_tasks = get_tasks_by_goal(goal_id)
        
        # Count how many tasks are done
        all_done = all(t["status"] == "done" for t in all_tasks)
        
        # Step 8: If all tasks are done, mark the goal as done
        if all_done:
            update_goal_status(goal_id, status="done")
        
        # Step 9: Return success response
        return {
            "status": "done",
            "task_id": task_id,
            "bob_prompt": bob_prompt
        }
    
    except Exception as e:
        # On any error, mark task as failed and return error
        try:
            update_task(task_id, status="failed")
        except Exception:
            pass  # If we can't update status, just continue with error response
        
        return {
            "status": "failed",
            "error": str(e)
        }

# Made with Bob
