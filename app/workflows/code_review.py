from app.engine.registry import ToolRegistry
from app.engine.graph import WorkflowGraph
from app.schemas import WorkflowState


# --- 1. Define the Tools ---

@ToolRegistry.register("extract_code")
def extract_code(state: WorkflowState):
    """Simulates parsing the code."""
    code = state.input_data
    functions = [line.split("(")[0].replace("def ", "").strip()
                 for line in code.split("\n") if "def " in line]
    state.data["functions"] = functions
    state.data["review_round"] = 0
    state.log(f"Extracted {len(functions)} functions: {functions}")
    return state


@ToolRegistry.register("check_complexity")
def check_complexity(state: WorkflowState):
    """Simulates calculating Cyclomatic Complexity."""
    code = state.input_data
    score = 0
    if "for" in code: score += 5
    if "if" in code: score += 5
    if "while" in code: score += 5
    if "nested" in code: score += 10

    # Simulate improvement over rounds
    current_round = state.data.get("review_round", 0)
    adjusted_score = max(0, score - (current_round * 5))

    state.data["complexity_score"] = adjusted_score
    state.log(f"Calculated complexity score: {adjusted_score} (Round {current_round})")
    return state


@ToolRegistry.register("generate_improvements")
def generate_improvements(state: WorkflowState):
    """Simulates an AI suggesting changes."""
    state.data["review_round"] += 1
    state.log("Generated improvement suggestions. Re-evaluating...")
    return state


# --- 2. Define the Routing Logic ---

@ToolRegistry.register_condition("quality_gate")
def quality_gate(state: WorkflowState) -> str:
    """
    Decides if we loop back or finish.
    Threshold: Score must be < 10.
    """
    score = state.data.get("complexity_score", 100)
    if score < 10:
        return "END"
    else:
        return "improve"


# --- 3. Build the Graph ---

def create_code_review_graph() -> WorkflowGraph:
    graph = WorkflowGraph()

    graph.add_node("extract", "extract_code")
    graph.add_node("analyze", "check_complexity")
    graph.add_node("improve", "generate_improvements")

    graph.set_entry_point("extract")

    graph.add_edge("extract", "analyze")
    graph.add_edge("improve", "analyze")

    # The condition is now registered, so it will be serialized correctly by main.py
    graph.add_conditional_edge("analyze", quality_gate)

    return graph