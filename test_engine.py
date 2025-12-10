from app.engine.registry import ToolRegistry
from app.engine.graph import WorkflowGraph
from app.schemas import WorkflowState

# --- 1. Define dummy tools ---
@ToolRegistry.register("start_step")
def start(state: WorkflowState):
    state.data["status"] = "started"
    state.data["count"] = 0
    return state

@ToolRegistry.register("increment")
def increment(state: WorkflowState):
    state.data["count"] += 1
    return state

@ToolRegistry.register("check_value")
def check(state: WorkflowState):
    # This tool doesn't change state, just logs
    print(f"Current count is {state.data['count']}")
    return state

# --- 2. Define Condition Logic ---
def check_threshold(state: WorkflowState) -> str:
    if state.data["count"] < 3:
        return "step_2" # Loop back
    return "END"

# --- 3. Build Graph ---
graph = WorkflowGraph()

# Add Nodes
graph.add_node("step_1", "start_step")
graph.add_node("step_2", "increment")
graph.add_node("step_3", "check_value")

# Set Entry
graph.set_entry_point("step_1")

# Add Edges
graph.add_edge("step_1", "step_2") # Start -> Inc
graph.add_edge("step_2", "step_3") # Inc -> Check
# Check -> Loop back OR End
graph.add_conditional_edge("step_3", check_threshold)

# --- 4. Run ---
print(">>> Running Workflow...")
final_state = graph.run(initial_payload="Test Run")
print("\n>>> Final Logs:")
for log in final_state.logs:
    print(log)
print("\n>>> Final Data:", final_state.data)