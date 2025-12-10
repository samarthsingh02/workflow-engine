import uuid
import json
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.schemas import (
    CreateGraphRequest, RunGraphRequest,
    WorkflowState, DBGraphDefinition, DBWorkflowRun,
    RunGraphResponse
)
from app.engine.graph import WorkflowGraph
from app.engine.registry import ToolRegistry
from app.db_session import engine, Base, get_db, SessionLocal
from app.workflows.code_review import create_code_review_graph


# --- LIFESPAN MANAGER (Replaces startup_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    Base.metadata.create_all(bind=engine)
    print(">>> Database tables created/checked.")

    db = SessionLocal()
    # Check if demo graph exists
    if not db.query(DBGraphDefinition).filter(DBGraphDefinition.id == "demo-review").first():
        demo_graph = create_code_review_graph()

        # Serialize the graph (including conditional edges)
        conditional_edges_data = []
        for src, func in demo_graph.conditional_edges.items():
            func_name = ToolRegistry.get_condition_name(func)
            if func_name:
                conditional_edges_data.append({
                    "from_node": src,
                    "condition_function": func_name
                })

        def_data = {
            "name": "Code Review Agent Demo",
            "nodes": [{"name": n.name, "tool_name": n.tool_name} for n in demo_graph.nodes.values()],
            "edges": [{"from_node": src, "to_node": dest} for src, dest in demo_graph.edges.items()],
            "conditional_edges": conditional_edges_data,
            "entry_point": demo_graph.entry_point
        }

        db_graph = DBGraphDefinition(
            id="demo-review",
            name="Code Review Agent Demo",
            definition=json.dumps(def_data)
        )
        db.add(db_graph)
        db.commit()
        print(">>> Startup: Loaded 'demo-review' graph into DB.")
    db.close()

    yield  # The application runs here

    # --- SHUTDOWN LOGIC (Optional) ---
    print(">>> Shutting down...")


# --- INITIAL SETUP ---
app = FastAPI(title="Workflow Engine API", lifespan=lifespan)


# --- WORKER FUNCTIONS ---

def load_graph_from_db_definition(graph_definition: str) -> WorkflowGraph:
    """Helper function to instantiate WorkflowGraph from stored JSON."""
    data = json.loads(graph_definition)
    graph = WorkflowGraph()

    # 1. Add Nodes
    for node_data in data.get("nodes", []):
        graph.add_node(node_data['name'], node_data['tool_name'])

    # 2. Add Standard Edges
    for edge_data in data.get("edges", []):
        graph.add_edge(edge_data['from_node'], edge_data['to_node'])

    # 3. Add Conditional Edges (Dynamic!)
    for cond_data in data.get("conditional_edges", []):
        src = cond_data['from_node']
        func_name = cond_data['condition_function']
        try:
            # Look up the logic in the registry
            condition_func = ToolRegistry.get_condition(func_name)
            graph.add_conditional_edge(src, condition_func)
        except ValueError:
            print(f"WARNING: Condition function '{func_name}' not found in registry. Skipping edge from {src}.")

    graph.set_entry_point(data['entry_point'])
    return graph


def _execution_worker(run_id: str):
    """The background worker that runs the workflow engine."""
    worker_db = SessionLocal()
    db_run = None  # <--- FIX: Initialize variable here to silence IDE warning

    try:
        db_run = worker_db.query(DBWorkflowRun).filter(DBWorkflowRun.id == run_id).one_or_none()
        if not db_run:
            return

        db_graph_def = worker_db.query(DBGraphDefinition).filter(DBGraphDefinition.id == db_run.graph_id).one()

        graph = load_graph_from_db_definition(db_graph_def.definition)
        initial_state = WorkflowState(**db_run.state_json)

        final_state = graph.run(initial_state.input_data)

        db_run.state_json = final_state.dict()
        db_run.status = "COMPLETED"
        worker_db.commit()

    except Exception as e:
        if db_run:
            current_state = WorkflowState(**db_run.state_json)
            current_state.log(f"CRITICAL ERROR: {str(e)}")
            db_run.state_json = current_state.dict()
            db_run.status = "FAILED"
            worker_db.commit()
        print(f"Worker Error: {e}")
    finally:
        worker_db.close()


# --- API ENDPOINTS ---

@app.post("/graph/create")
def create_graph(request: CreateGraphRequest, db: Session = Depends(get_db)):
    """Allows creating a custom graph via JSON and saves to DB."""

    # Validation
    try:
        load_graph_from_db_definition(request.json())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid graph definition: {str(e)}")

    graph_id = str(uuid.uuid4())
    db_graph = DBGraphDefinition(
        id=graph_id,
        name=request.name,
        definition=request.json()
    )

    try:
        db.add(db_graph)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Graph with this name likely already exists.")

    return {"graph_id": graph_id, "message": f"Graph '{request.name}' created successfully"}


@app.post("/graph/run", response_model=RunGraphResponse)
def run_workflow(request: RunGraphRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_graph_def = db.query(DBGraphDefinition).filter(DBGraphDefinition.id == request.graph_id).one_or_none()
    if not db_graph_def:
        raise HTTPException(status_code=404, detail="Graph not found")

    run_id = str(uuid.uuid4())
    initial_state = WorkflowState(input_data=request.input_data)
    initial_state.log("Run initialized, waiting for execution...")

    db_run = DBWorkflowRun(
        id=run_id,
        graph_id=request.graph_id,
        state_json=initial_state.dict(),
        status="SUBMITTED"
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    background_tasks.add_task(_execution_worker, run_id)
    return RunGraphResponse(run_id=run_id, status=db_run.status)


@app.get("/graph/state/{run_id}", response_model=WorkflowState)
def get_run_state(run_id: str, db: Session = Depends(get_db)):
    db_run = db.query(DBWorkflowRun).filter(DBWorkflowRun.id == run_id).one_or_none()
    if not db_run:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return WorkflowState(**db_run.state_json)


# --- ENTRY POINT FOR PYCHARM ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)