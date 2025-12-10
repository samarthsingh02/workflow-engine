from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from typing import List

class WorkflowState(BaseModel):
    """
    The shared state that flows through the graph.
    It acts like a dictionary but with type safety where needed.
    """
    input_data: Any = Field(default=None, description="Initial input for the workflow")
    # We use a flexible dict to store results from various steps
    data: Dict[str, Any] = Field(default_factory=dict)
    # Traceability is key - keep a log of what happened
    logs: List[str] = Field(default_factory=list)

    class Config:
        # Allows nodes to add new keys to the state dynamically
        extra = "allow"

    def log(self, message: str):
        """Helper to append to logs"""
        self.logs.append(message)

# --- API Models ---

class NodeConfig(BaseModel):
    name: str
    tool_name: str

class EdgeConfig(BaseModel):
    from_node: str
    to_node: str

class CreateGraphRequest(BaseModel):
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    entry_point: str

class RunGraphRequest(BaseModel):
    graph_id: str
    input_data: Any