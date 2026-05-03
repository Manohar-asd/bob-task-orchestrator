"""
Pydantic models for Bob Task Orchestrator (BTO)

This module defines the data models used throughout the application:
- Goal: Represents a high-level objective that will be decomposed into tasks
- Task: Represents an actionable step toward completing a goal
- Status enums: Define valid states for goals and tasks
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    """Valid status values for a goal"""
    PENDING = "pending"
    DONE = "done"


class TaskStatus(str, Enum):
    """Valid status values for a task"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class GoalCreate(BaseModel):
    """Input model for creating a new goal"""
    text: str = Field(..., min_length=1, max_length=500, description="Goal description")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Build a REST API for user management with FastAPI, including endpoints for CRUD operations on users, authentication and authorization"
            }
        }


class Goal(BaseModel):
    """Complete goal model with all fields"""
    id: Optional[int] = Field(default=None, description="Unique goal identifier (set by database)")
    text: str = Field(..., min_length=1, max_length=500)
    status: GoalStatus = Field(default=GoalStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional fields for API responses
    task_count: Optional[int] = Field(default=0, description="Number of tasks for this goal")
    completed_tasks: Optional[int] = Field(default=0, description="Number of completed tasks")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "text": "Build a REST API for user management with FastAPI",
                "status": "pending",
                "created_at": "2026-05-01T21:00:00Z",
                "task_count": 5,
                "completed_tasks": 2
            }
        }


class TaskCreate(BaseModel):
    """Input model for creating a new task"""
    goal_id: int = Field(..., description="ID of the parent goal")
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(..., min_length=1, description="Detailed task description")
    order: int = Field(..., ge=1, description="Execution order (1-based)")

    class Config:
        json_schema_extra = {
            "example": {
                "goal_id": 1,
                "title": "Set up FastAPI project structure",
                "description": "Create project directories, initialize virtual environment, and install FastAPI dependencies",
                "order": 1
            }
        }


class Task(BaseModel):
    """Complete task model with all fields"""
    id: Optional[int] = Field(default=None, description="Unique task identifier (set by database)")
    goal_id: int = Field(..., description="ID of the parent goal")
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    order: int = Field(..., ge=1, description="Execution order (1-based)")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    bob_prompt: Optional[str] = Field(default=None, description="Generated prompt for Bob IDE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "goal_id": 1,
                "title": "Set up FastAPI project structure",
                "description": "Create project directories, initialize virtual environment, and install FastAPI dependencies",
                "order": 1,
                "status": "pending",
                "bob_prompt": None,
                "created_at": "2026-05-01T21:00:00Z",
                "updated_at": "2026-05-01T21:00:00Z"
            }
        }


class TaskRunResponse(BaseModel):
    """Response model when running a task"""
    task_id: int
    status: TaskStatus
    bob_prompt: str = Field(..., description="Detailed prompt for Bob to execute this task")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": 1,
                "status": "running",
                "bob_prompt": "You are Bob, a highly skilled software engineer...\n\nTask: Set up FastAPI project structure\n\nSteps:\n1. Create the following directory structure..."
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-05-01T21:00:00Z",
                "version": "1.0.0"
            }
        }

# Made with Bob
