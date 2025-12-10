from app.workflows.code_review import create_code_review_graph

# Sample Python code that is "complex" (has 'for' and 'if')
# It should loop a few times before passing.
BAD_CODE = """
def process_data(data):
    for item in data:
        if item > 10:
            print("Complex logic here")
            nested = True
"""


def test_run():
    print(">>> Initializing Code Review Graph...")
    graph = create_code_review_graph()

    print(">>> Running Workflow...")
    final_state = graph.run(initial_payload=BAD_CODE)

    print("\n>>> Execution Logs:")
    for log in final_state.logs:
        print(f" - {log}")

    print(f"\n>>> Final Complexity Score: {final_state.data['complexity_score']}")
    assert final_state.data['complexity_score'] < 10
    print(">>> SUCCESS: Workflow completed and passed quality gate.")


if __name__ == "__main__":
    test_run()