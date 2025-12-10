from typing import Dict, Any, Callable, Optional
from app.schemas import WorkflowState
from app.engine.registry import ToolRegistry


class Node:
    def __init__(self, name: str, tool_name: str):
        self.name = name
        self.tool_name = tool_name

    def run(self, state: WorkflowState) -> WorkflowState:
        """Executes the tool associated with this node."""
        func = ToolRegistry.get_tool(self.tool_name)
        # We assume tools accept the state and return a modified state or dict
        result = func(state)
        return result


class WorkflowGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, str] = {}  # Simple map: "node_a" -> "node_b"
        self.conditional_edges: Dict[str, Callable[[WorkflowState], str]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, tool_name: str):
        self.nodes[name] = Node(name, tool_name)

    def set_entry_point(self, name: str):
        self.entry_point = name

    def add_edge(self, source: str, destination: str):
        self.edges[source] = destination

    def add_conditional_edge(self, source: str, condition_func: Callable[[WorkflowState], str]):
        """
        source: The node we are leaving
        condition_func: A function that takes State and returns the name of the next node
        """
        self.conditional_edges[source] = condition_func

    def run(self, initial_payload: Any) -> WorkflowState:
        """Main execution loop"""
        if not self.entry_point:
            raise ValueError("Graph has no entry point defined.")

        # Initialize State
        state = WorkflowState(input_data=initial_payload)
        state.log(f"Workflow started with input: {initial_payload}")

        current_node_name = self.entry_point

        while current_node_name:
            if current_node_name == "END":
                state.log("Workflow reached END.")
                break

            current_node = self.nodes.get(current_node_name)
            if not current_node:
                raise ValueError(f"Node '{current_node_name}' not found.")

            # EXECUTE
            state.log(f"Executing Node: {current_node_name}")
            try:
                # Run the node logic (which runs the tool)
                # Note: Tools should modify state in place or return it
                current_node.run(state)
            except Exception as e:
                state.log(f"Error in node {current_node_name}: {str(e)}")
                raise e

            # NAVIGATE (Determine next node)
            next_node = None

            # 1. Check Conditional Edges first (priority)
            if current_node_name in self.conditional_edges:
                condition_func = self.conditional_edges[current_node_name]
                next_node = condition_func(state)
                state.log(f"Condition met. Routing to: {next_node}")

            # 2. Check Static Edges
            elif current_node_name in self.edges:
                next_node = self.edges[current_node_name]
                state.log(f"Moving to: {next_node}")

            # 3. If no edge, we stop (implicit END)
            else:
                state.log("No outgoing edge found. Stopping.")
                next_node = None

            current_node_name = next_node

        return state