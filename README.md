# Workflow Orchestration Engine (AI Engineering Internship Assignment)

A lightweight, graph-based workflow engine built with Python and FastAPI. It allows you to define, execute, and monitor stateful agent workflows with branching, looping, and persistence.

**Current Status:** Phase 4 Complete (Persistence & Async Execution).

## Core Features

| Feature | Description | Status   |
| :--- | :--- |:---------|
| **Graph Engine** | Define workflows as Nodes (functions) and Edges (linear or conditional). | Complete |
| **State Management** | Shared `WorkflowState` object (Pydantic) flows through the graph. | Complete |
| **Branching & Looping** | Supports cyclic graphs (e.g., "retry until quality > threshold"). | Complete |
| **Persistence** | **SQLite & SQLAlchemy** integration. Workflows and runs survive server restarts. | Complete |
| **Async Execution** | Non-blocking execution using FastAPI BackgroundTasks. | Complete |
| **Tool Registry** | Decoupled tool logic registered via decorators. | Complete |

---

## Project Structure

The project separates core engine logic from API and database layers.

```text
workflow-engine/
├── app/
│   ├── engine/          
│   │   ├── graph.py     # The core Execution Engine (Nodes, Loops, Transitions)
│   │   └── registry.py  # Tool Registry (maps string names to functions)
│   ├── workflows/       
│   │   └── code_review.py # Example Implementation: Code Review Agent
│   ├── db_session.py    # Database connection (SQLite + SQLAlchemy)
│   └── schemas.py       # Pydantic Schemas & SQLAlchemy ORM Models
├── main.py              # FastAPI Application & Endpoints
└── requirements.txt     # Dependencies
```


## Setup & Run

1. **Clone the repository:**

   ```bash
   git clone https://github.com/samarthsingh02/workflow-engine.git
   cd workflow-engine
   ```

2. **Install dependencies:**

   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic uuid
   ```

3. **Start the Server:**

   ```bash
   uvicorn main:app --reload
   ```

   *On first run, this will create a `workflow.db` file in your root directory and load the demo graph.*

4. **Access Docs:**
   Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to use the Swagger UI.

---

## Usage Example: Code Review Agent

The system comes pre-loaded with a `Code Review Agent Demo` (Graph ID: `demo-review`). This workflow loops until the code complexity score is acceptable.

### 1. Trigger a Run

**POST** `/graph/run`

```json
{
  "graph_id": "demo-review",
  "input_data": "def messy_function():\n    if x:\n        for i in list:\n            while True:\n                nested=True"
}
```

*Returns a `run_id` immediately.*

### 2. Check Status

**GET** `/graph/state/{run_id}`

```json
{
  "status": "COMPLETED",
  "logs": [
    "Executing Node: extract",
    "Executing Node: analyze",
    "Calculated complexity score: 20 (Round 0)",
    "Condition met. Routing to: improve",
    "Executing Node: improve",
    "Executing Node: analyze",
    "Calculated complexity score: 15 (Round 1)",
    "...",
    "Workflow reached END."
  ],
  "data": { "complexity_score": 5, "review_round": 3 }
}
```

---

## Database

The project uses **SQLite**.

* **File:** `workflow.db` (created automatically in the root folder).
* **Tables:**
    * `graph_definitions`: Stores the structure (nodes/edges) of workflows.
    * `workflow_runs`: Stores the execution history, state, and logs of every run.

