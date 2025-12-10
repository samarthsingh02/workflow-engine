# Workflow Orchestration Engine (AI Engineering Internship Assignment)

This project implements a minimal, graph-based backend workflow engine using Python and FastAPI. It demonstrates fundamental concepts in system architecture, state management, asynchronous programming, and API design.

The engine is designed to define, execute, and monitor a sequence of logical steps (Nodes) connected by defined transitions (Edges), maintaining a shared state throughout the execution.

## Core Features

| Feature | Description | Status |
| :--- | :--- | :--- |
| **Minimal Graph Engine** | Supports defining Nodes (tools/functions) and Edges (linear flow) | **Complete** |
| **State Management** | Uses a shared `WorkflowState` (Pydantic model) that flows between nodes. | **Complete** |
| **Branching & Looping** | Implemented using a conditional edge function (`quality_gate`) to route execution back (loop) or forward (end). | **Complete** |
| **Tool Registry** | Tools are decoupled and registered in a central registry, allowing nodes to reference them by string name. | **Complete** |
| **FastAPI Endpoints** | Provides a RESTful API for graph creation, execution, and status monitoring. | **Complete** |
| **Async Execution** | Workflow runs are executed asynchronously using FastAPI `BackgroundTasks`, ensuring the API remains responsive. | **Complete (Optional Requirement)** |

---

## Code Structure

The project is structured to separate the core engine logic from the application (FastAPI) and the specific workflow implementation.

```text
workflow-engine/
├── app/
│   ├── engine/          # The core Graph and Registry logic
│   │   ├── graph.py     # Defines Node, WorkflowGraph, and the execution loop
│   │   └── registry.py  # Decorator-based tool registration
│   ├── workflows/       # Implementation of specific agents
│   │   └── code_review.py # Option A (Code Review Agent) logic
│   ├── db.py            # Simple in-memory storage for graphs and active runs
│   └── schemas.py       # Pydantic models for State and API I/O validation
├── main.py              # FastAPI application entry point
└── requirements.txt     # List of project dependencies
```

---

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/samarthsingh02/workflow-engine.git
cd workflow-engine
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn pydantic uuid
# Or, if you have generated it:
# pip install -r requirements.txt
```

### 3. Start the Server

```bash
uvicorn main:app --reload
```

### 4. Access Docs

Open your browser to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to use the automatically generated Swagger UI.

---

## Example Agent Workflow Implementation

To demonstrate the engine's capabilities, the **Code Review Mini-Agent** (Option A) is implemented and pre-loaded with the ID `demo-review`.

This workflow defines a loop: 

**extract → analyze → (If score is bad: improve → analyze) → (If score is good: END)**

### 1. Start a Run

Use the `POST /graph/run` endpoint.

| Parameter | Value |
| :--- | :--- |
| `graph_id` | `demo-review` |
| `input_data` | Any string of code (e.g., a multi-line Python function) |

**Example Request Body:**

```json
{
  "graph_id": "demo-review",
  "input_data": "def foo():\n    if x:\n        for i in list:\n            nested=True"
}
```

The response will immediately return a `run_id` and `status: submitted`.

### 2. Check Run Status and Logs

Use the `GET /graph/state/{run_id}` endpoint, replacing `{run_id}` with the ID obtained from the previous step.

The output will show the `logs` array, demonstrating the execution path, including the multiple loops through the `analyze` and `improve` steps until the `complexity_score` drops below the threshold of 10.
