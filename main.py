import uuid
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from app.schemas import CreateGraphRequest, RunGraphRequest, WorkflowState
from app.engine.graph import WorkflowGraph
from app.db import graphs, runs
from app.workflows.code_review import create_code_review_graph

app = FastAPI(title="Workflow Engine API")


# --- 1. Setup Pre-defined Graphs ---
@app.on_event("startup")
def startup_event():
    # We pre-load the Code Review workflow so it's always available
    # ID is hardcoded for easy testing
    review_graph = create_code_review_graph()
    graphs["demo-review"] = review_graph
    print(">>> Startup: Loaded 'demo-review' graph.")


# --- 2. Endpoints ---

@app.post("/graph/create")
def create_graph(request: CreateGraphRequest):
    """
    Allows creating a custom graph via JSON.
    """
    new_graph = WorkflowGraph()

    # Add Nodes
    for node in request.nodes:
        try:
            new_graph.add_node(node.name, node.tool_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Add Edges
    for edge in request.edges:
        new_graph.add_edge(edge.from_node, edge.to_node)

    new_graph.set_entry_point(request.entry_point)

    # Save to DB
    graph_id = str(uuid.uuid4())
    graphs[graph_id] = new_graph

    return {"graph_id": graph_id, "message": "Graph created successfully"}


@app.post("/graph/run")
def run_workflow(request: RunGraphRequest, background_tasks: BackgroundTasks):
    """
    Runs a workflow asynchronously.
    Returns a run_id immediately; logic runs in background.
    """
    if request.graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[request.graph_id]
    run_id = str(uuid.uuid4())

    # Initialize empty state in DB so /state works immediately
    runs[run_id] = WorkflowState(input_data=request.input_data)
    runs[run_id].log("Run initialized, waiting for execution...")

    # Define the background worker
    def _execution_worker(g, rid, inp):
        try:
            # Run the engine (this is blocking, so we put it in a thread/bg task)
            final_state = g.run(inp)
            runs[rid] = final_state  # Update DB with final result
        except Exception as e:
            # Log failure
            runs[rid].log(f"CRITICAL ERROR: {str(e)}")

    # Dispatch to background
    background_tasks.add_task(_execution_worker, graph, run_id, request.input_data)

    return {"run_id": run_id, "status": "submitted"}


@app.get("/graph/state/{run_id}")
def get_run_state(run_id: str):
    """
    Check the status/logs of a specific run.
    """
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run ID not found")

    return runs[run_id]