from typing import Dict, Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy.ext.mutable import MutableDict
from app.db_session import Base  # Import Base from our new db_session module


# --- 1. Core Workflow State Model ---

class WorkflowState(BaseModel):
    """
    The shared state that flows through the graph.
    Acts as a Data Transfer Object (DTO) and is stored in the DB.
    """
    input_data: Any = Field(default=None, description="Initial input for the workflow")
    data: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    status: str = "PENDING"

    class Config:
        extra = "allow"

    def log(self, message: str):
        """Helper to append to logs"""
        self.logs.append(message)


# --- 2. Database Models (SQLAlchemy ORM Models) ---

class DBGraphDefinition(Base):
    """Stores the JSON definition of a graph structure."""
    __tablename__ = "graph_definitions"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    name = Column(String, index=True, unique=True)
    definition = Column(Text)  # Stores the JSON definition of nodes/edges
    created_at = Column(DateTime, default=datetime.utcnow)


class DBWorkflowRun(Base):
    """Stores the state and logs of a single workflow execution."""
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    graph_id = Column(String, index=True)

    # Store the entire WorkflowState as JSON
    # MutableDict.as_mutable(JSON) ensures that changes to the dict
    # (like appending logs) are tracked and saved by SQLAlchemy.
    state_json = Column(MutableDict.as_mutable(JSON), default=dict, nullable=False)

    status = Column(String, default="PENDING")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


# --- 3. API Input/Output Models (Pydantic) ---

class NodeConfig(BaseModel):
    name: str
    tool_name: str


class EdgeConfig(BaseModel):
    from_node: str
    to_node: str


class CreateGraphRequest(BaseModel):
    name: str  # Required for DB: Graphs need a friendly name
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    entry_point: str


class RunGraphRequest(BaseModel):
    graph_id: str
    input_data: Any


class RunGraphResponse(BaseModel):
    run_id: str
    status: str