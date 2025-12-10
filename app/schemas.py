from typing import Dict, Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy.ext.mutable import MutableDict
from app.db_session import Base

# --- 1. Core Workflow State Model ---

class WorkflowState(BaseModel):
    """
    The shared state that flows through the graph.
    """
    input_data: Any = Field(default=None, description="Initial input for the workflow")
    data: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    status: str = "PENDING"

    class Config:
        extra = "allow"

    def log(self, message: str):
        self.logs.append(message)


# --- 2. Database Models ---

class DBGraphDefinition(Base):
    __tablename__ = "graph_definitions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    definition = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class DBWorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, index=True)
    graph_id = Column(String, index=True)
    state_json = Column(MutableDict.as_mutable(JSON), default=dict, nullable=False)
    status = Column(String, default="PENDING")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


# --- 3. API Input/Output Models ---

class NodeConfig(BaseModel):
    name: str
    tool_name: str

class EdgeConfig(BaseModel):
    from_node: str
    to_node: str

class ConditionalEdgeConfig(BaseModel):
    """Defines a branch in the flow controlled by a registered condition function."""
    from_node: str
    condition_function: str

class CreateGraphRequest(BaseModel):
    name: str
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    # Allows defining dynamic branching logic
    conditional_edges: List[ConditionalEdgeConfig] = []
    entry_point: str

class RunGraphRequest(BaseModel):
    graph_id: str
    input_data: Any

class RunGraphResponse(BaseModel):
    run_id: str
    status: str