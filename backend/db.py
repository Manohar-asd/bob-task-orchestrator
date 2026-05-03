"""
SQLite database layer for Bob Task Orchestrator (BTO)

This module provides all database operations using Python's built-in sqlite3.
No external dependencies or ORM - just pure SQLite operations.

Database schema:
- goals: Stores high-level objectives
- tasks: Stores actionable steps for each goal
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


# Database file path - stored in the backend directory
DB_PATH = Path(__file__).parent / "bto.db"


@contextmanager
def get_conn():
    """
    Context manager for database connections.
    Automatically commits on success and rolls back on error.
    Sets row_factory to sqlite3.Row for dict-like access.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Initialize the database by creating tables if they don't exist.
    Safe to call multiple times - will not recreate existing tables.
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        
        # Create goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create tasks table with foreign key to goals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                ord INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                bob_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)
        
        # Create index on goal_id for faster task lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_goal_id 
            ON tasks(goal_id)
        """)


def insert_goal(text: str) -> int:
    """
    Insert a new goal into the database.
    
    Args:
        text: The goal description (1-500 characters)
    
    Returns:
        The ID of the newly created goal
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO goals (text, status) VALUES (?, ?)",
            (text, "pending")
        )
        # lastrowid is guaranteed to be an int after INSERT with AUTOINCREMENT
        assert cursor.lastrowid is not None
        return cursor.lastrowid


def get_goal(goal_id: int) -> Optional[dict]:
    """
    Retrieve a single goal by ID.
    
    Args:
        goal_id: The ID of the goal to retrieve
    
    Returns:
        Dictionary with goal data, or None if not found
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, text, status, created_at FROM goals WHERE id = ?",
            (goal_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_goals() -> list[dict]:
    """
    Retrieve all goals, ordered by creation date (newest first).
    Includes task count and completed task count for each goal.
    
    Returns:
        List of dictionaries with goal data and task statistics
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                g.id,
                g.text,
                g.status,
                g.created_at,
                COUNT(t.id) as task_count,
                COALESCE(SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END), 0) as completed_tasks
            FROM goals g
            LEFT JOIN tasks t ON g.id = t.goal_id
            GROUP BY g.id
            ORDER BY g.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def insert_task(goal_id: int, title: str, description: str, order: int) -> int:
    """
    Insert a new task into the database.
    
    Args:
        goal_id: ID of the parent goal
        title: Task title
        description: Detailed task description
        order: Execution order (1-based)
    
    Returns:
        The ID of the newly created task
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (goal_id, title, description, ord, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (goal_id, title, description, order, "pending", now, now)
        )
        # lastrowid is guaranteed to be an int after INSERT with AUTOINCREMENT
        assert cursor.lastrowid is not None
        return cursor.lastrowid


def get_task(task_id: int) -> Optional[dict]:
    """
    Retrieve a single task by ID.
    
    Args:
        task_id: The ID of the task to retrieve
    
    Returns:
        Dictionary with task data, or None if not found
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, goal_id, title, description, ord, status, 
                   bob_prompt, created_at, updated_at
            FROM tasks 
            WHERE id = ?
            """,
            (task_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_tasks_by_goal(goal_id: int) -> list[dict]:
    """
    Retrieve all tasks for a specific goal, ordered by execution order.
    
    Args:
        goal_id: The ID of the parent goal
    
    Returns:
        List of dictionaries with task data, ordered by ord field
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, goal_id, title, description, ord, status,
                   bob_prompt, created_at, updated_at
            FROM tasks
            WHERE goal_id = ?
            ORDER BY ord ASC
            """,
            (goal_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_task(task_id: int, status: str, bob_prompt: Optional[str] = None) -> None:
    """
    Update a task's status and optionally its Bob prompt.
    Also updates the updated_at timestamp.
    
    Args:
        task_id: The ID of the task to update
        status: New status (pending, running, done, failed)
        bob_prompt: Optional Bob prompt to set (if provided)
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cursor = conn.cursor()
        
        if bob_prompt is not None:
            cursor.execute(
                """
                UPDATE tasks 
                SET status = ?, bob_prompt = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, bob_prompt, now, task_id)
            )
        else:
            cursor.execute(
                """
                UPDATE tasks 
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, now, task_id)
            )


def update_goal_status(goal_id: int, status: str) -> None:
    """
    Update a goal's status.
    
    Args:
        goal_id: The ID of the goal to update
        status: New status (pending, done)
    """
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE goals SET status = ? WHERE id = ?",
            (status, goal_id)
        )

# Made with Bob
