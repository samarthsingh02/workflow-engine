from app.engine.registry import ToolRegistry
from app.engine.graph import WorkflowGraph
from app.schemas import WorkflowState


# --- 1. Define the Tools (The Logic) ---

@ToolRegistry.register("extract_code")
def extract_code(state: WorkflowState):
    """
    Simulates parsing the code.
    Input: state.input_data (str)
    Output: updates state.data['functions']
    """
    code = state.input_data
    # Dummy logic: Split by 'def ' to find function names
    functions = [line.split("(")[0].replace("def ", "").strip()
                 for line in code.split("\n") if "def " in line]

    state.data["functions"] = functions
    state.data["review_round"] = 0
    state.log(f"Extracted {len(functions)} functions: {functions}")
    return state


@ToolRegistry.register("check_complexity")
def check_complexity(state: WorkflowState):
    """
    Simulates calculating Cyclomatic Complexity.
    Dummy Rule: If code has 'nested' keyword, it's complex.
    """
    code = state.input_data
    score = 0
    if "for" in code: score += 5
    if "if" in code: score += 5
    if "while" in code: score += 5
    if "nested" in code: score += 10

    # Simulate improvement over rounds (for the loop)
    # Each round reduces "perceived" complexity to ensure loop finishes
    current_round = state.data.get("review_round", 0)
    adjusted_score = max(0, score - (current_round * 5))

    state.data["complexity_score"] = adjusted_score
    state.log(f"Calculated complexity score: {adjusted_score} (Round {current_round})")
    return state


@ToolRegistry.register("generate_improvements")
def generate_improvements(state: WorkflowState):
    """
    Simulates an AI suggesting changes.
    """
    state.data["review_round"] += 1
    state.log("Generated improvement suggestions. Re-evaluating...")
    return state


# --- 2. Define the Routing Logic ---

def quality_gate(state: WorkflowState) -> str:
    """
    Decides if we loop back or finish.
    Threshold: Score must be < 10.
    """
    score = state.data.get("complexity_score", 100)
    if score < 10:
        return "END"
    else:
        return "improve"  # Name of the node to go to


# --- 3. Build the Graph ---

def create_code_review_graph() -> WorkflowGraph:
    graph = WorkflowGraph()

    # Register Nodes
    graph.add_node("extract", "extract_code")
    graph.add_node("analyze", "check_complexity")
    graph.add_node("improve", "generate_improvements")

    # Set Entry
    graph.set_entry_point("extract")

    # Define Flow
    graph.add_edge("extract", "analyze")

    # The Loop: Analyze -> Check Gate -> (Improve -> Analyze) OR (End)
    graph.add_conditional_edge("analyze", quality_gate)
    graph.add_edge("improve", "analyze")  # Loop back to analysis

    return graph