# Simple in-memory storage
# In a real app, these would be database tables.

# Stores the Graph Definitions (the structure)
# Key: graph_id (str), Value: WorkflowGraph object
graphs = {}

# Stores the execution state of runs
# Key: run_id (str), Value: WorkflowState object
runs = {}