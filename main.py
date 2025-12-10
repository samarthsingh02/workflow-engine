import uuid
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.schemas import (
    CreateGraphRequest, RunGraphRequest,
    WorkflowState, DBGraphDefinition, DBWorkflowRun,
    RunGraphResponse
)
from app.engine.graph import WorkflowGraph
from app.db_session import engine, Base, get_db, SessionLocal
from app.workflows.code_review import create_code_review_graph

# --- INITIAL SETUP ---
app = FastAPI(title="Workflow Engine API")


# Create database tables on startup
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    print(">>> Database tables created/checked.")

    # Initialize the demo graph if it doesn't exist
    db = SessionLocal()
    if not db.query(DBGraphDefinition).filter(DBGraphDefinition.id == "demo-review").first():
        demo_graph = create_code_review_graph()

        # We need to reconstruct the graph definition into a storable format
        def_data = {
            "nodes": [{"name": n.name, "tool_name": n.tool_name} for n in demo_graph.nodes.values()],
            "edges": [{"from_node": src, "to_node": dest} for src, dest in demo_graph.edges.items()],
            "entry_point": demo_graph.entry_point,
            "name": "Code Review Agent Demo"  # Include name in JSON for consistency
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


# --- WORKER FUNCTIONS ---

def load_graph_from_db_definition(graph_definition: str) -> WorkflowGraph:
    """Helper function to instantiate WorkflowGraph from stored JSON."""
    data = json.loads(graph_definition)
    graph = WorkflowGraph()

    for node_data in data.get("nodes", []):
        graph.add_node(node_data['name'], node_data['tool_name'])

    for edge_data in data.get("edges", []):
        graph.add_edge(edge_data['from_node'], edge_data['to_node'])

    graph.set_entry_point(data['entry_point'])

    # CRITICAL: Re-attach conditional logic for the demo graph.
    # In a real system, you might map these by name from a registry.
    if data.get("name") == "Code Review Agent Demo":
        from app.workflows.code_review import quality_gate
        graph.add_conditional_edge("analyze", quality_gate)

    return graph


def _execution_worker(run_id: str):
    """The background worker that runs the workflow engine."""
    # Create a new DB session for this background thread
    worker_db = SessionLocal()
    try:
        db_run = worker_db.query(DBWorkflowRun).filter(DBWorkflowRun.id == run_id).one_or_none()
        if not db_run:
            print(f"Worker failed: Run {run_id} not found in DB.")
            return

        # Fetch the Graph Definition
        db_graph_def = worker_db.query(DBGraphDefinition).filter(DBGraphDefinition.id == db_run.graph_id).one()

        # 1. Build the Graph Object
        graph = load_graph_from_db_definition(db_graph_def.definition)

        # 2. Load Initial State
        # We convert the JSON dict back into a Pydantic model
        initial_state = WorkflowState(**db_run.state_json)

        # 3. RUN EXECUTION (Blocking)
        final_state = graph.run(initial_state.input_data)

        # 4. Save Final State
        db_run.state_json = final_state.dict()
        db_run.status = "COMPLETED"
        worker_db.commit()

    except Exception as e:
        # Handle exceptions during execution and log to DB
        if db_run:
            # We need to load the current state to append the log safely
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

    # Validate that we can actually build this graph
    try:
        # We dump the request to JSON string to simulate how it will be stored
        # and see if our loader accepts it
        request_json = request.json()
        load_graph_from_db_definition(request_json)
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
    """Runs a workflow asynchronously. State is managed in the database."""

    # 1. Verify Graph Exists
    db_graph_def = db.query(DBGraphDefinition).filter(DBGraphDefinition.id == request.graph_id).one_or_none()
    if not db_graph_def:
        raise HTTPException(status_code=404, detail="Graph not found")

    run_id = str(uuid.uuid4())

    # 2. Create Initial State
    initial_state = WorkflowState(input_data=request.input_data)
    initial_state.log("Run initialized, waiting for execution...")

    # 3. Create DB Entry
    db_run = DBWorkflowRun(
        id=run_id,
        graph_id=request.graph_id,
        state_json=initial_state.dict(),
        status="SUBMITTED"
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    # 4. Dispatch Background Task
    background_tasks.add_task(_execution_worker, run_id)

    return RunGraphResponse(run_id=run_id, status=db_run.status)


@app.get("/graph/state/{run_id}", response_model=WorkflowState)
def get_run_state(run_id: str, db: Session = Depends(get_db)):
    """Check the status/logs of a specific run."""

    db_run = db.query(DBWorkflowRun).filter(DBWorkflowRun.id == run_id).one_or_none()

    if not db_run:
        raise HTTPException(status_code=404, detail="Run ID not found")

    # Convert JSON from DB back to Pydantic model
    return WorkflowState(**db_run.state_json)