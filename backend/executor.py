"""
Task Execution Service for Bob Task Orchestrator (BTO)

This module handles task execution logic:
- Marks tasks as running
- Generates Bob-ready prompts with project context
- Simulates task execution
- Updates task and goal statuses
- Handles errors gracefully
"""

import os
import time
from pathlib import Path
from typing import Any

from db import get_task, get_tasks_by_goal, update_goal_status, update_task


def _get_project_context() -> str:
    """
    Get project context by reading recent Python files from the workspace.
    
    Looks for Python files in the current working directory and one level up,
    reads up to 3 most recently modified files, and returns their content
    (first 50 lines each) to provide context for Bob.
    
    Returns:
        Formatted string with project file contents, or empty string if none found
    """
    try:
        # Get current working directory
        cwd = Path(os.getcwd())
        
        # Collect Python files from current directory and one level up
        python_files = []
        
        # Search current directory
        if cwd.exists():
            python_files.extend(cwd.glob("*.py"))
            # Search subdirectories one level deep
            for subdir in cwd.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('.'):
                    python_files.extend(subdir.glob("*.py"))
        
        # Search parent directory
        parent = cwd.parent
        if parent.exists():
            python_files.extend(parent.glob("*.py"))
        
        # Filter out __pycache__ and other unwanted files
        python_files = [
            f for f in python_files 
            if f.is_file() 
            and '__pycache__' not in str(f)
            and not f.name.startswith('.')
        ]
        
        if not python_files:
            return ""
        
        # Sort by modification time (most recent first)
        python_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Take up to 3 most recent files
        recent_files = python_files[:3]
        
        # Build context string
        context_parts = []
        for file_path in recent_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:50]  # First 50 lines
                    content = ''.join(lines)
                    
                    # Get relative path for cleaner display
                    try:
                        rel_path = file_path.relative_to(cwd)
                    except ValueError:
                        rel_path = file_path.name
                    
                    context_parts.append(f"File: {rel_path}\n```python\n{content}\n```")
            except Exception as e:
                # Skip files that can't be read
                continue
        
        if not context_parts:
            return ""
        
        return "\n\n".join(context_parts)
    
    except Exception as e:
        # Never crash - just return empty context
        return ""


def _generate_bob_prompt(title: str, description: str) -> str:
    """
    Generate a formatted prompt for Bob IDE to execute a task.
    Includes project context from existing Python files to help Bob
    understand the codebase structure and style.
    
    Args:
        title: Task title
        description: Task description
    
    Returns:
        Formatted prompt string ready for Bob with project context
    """
    context = _get_project_context()
    
    prompt = f"""## Bob Task: {title}

### What to implement:
{description}

### Your project context:
{context if context else "No project files found — implement from scratch."}

### Instructions:
Implement the above task based on the project context shown.
Write clean, well-commented code that fits the existing codebase style.
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
    4. Generate Bob prompt with project context
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
        
        # Step 4: Generate Bob prompt from task details with project context
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
