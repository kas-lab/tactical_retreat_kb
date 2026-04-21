# Codebase structure

- `typedb_tactics/`: Python package.
- `typedb_tactics/typedb_tactical_retreat_interface.py`: main TypeDB query wrapper and helper data structures.
- `typedb_tactics/tactical_retreat_kb.py`: lifecycle ROS node exposing the interface as ROS interactions.
- `typedb_tactics/tactical_retreat_node.py`: minimal console entrypoint that starts the KB node in a multithreaded executor.
- `schemas/`: TypeDB schema modules. Top-level areas include `data_structure`, `context_model`, `feature_model`, `logical_expressions`, `relaxed`, `ros_model`, `tactics_model`, `discover_tactics_model`, `discover_hypothetical_req_fulfillment`, and `states`.
- `schemas_diagrams/`: generated schema figures such as per-schema diagrams and merged schema outputs.
- `launch/`: ROS launch files, currently `tactical_retreat_kb.launch.py`.
- `test/`: pytest-based ROS/TypeDB tests, including focused suites for feature, fuzzy, logical, relaxed, ROS, tactics, hypothetical fulfillment, interface, and style/lint checks.
- `scripts/`: helper scripts such as `run-tests-docker.sh`, `benchmark.py`, `benchmark_queries.py`, `profile_schema_load.py`, `generate_schema_diagrams.py`, and `generate_merged_schema_diagram.py`.
- `scripts/README.md`: central documentation for how to run the helper scripts.
- `docs/agent-notes.md`: concise agent checklist with common failures, style reminders, and required completion checks.
- `Dockerfile`: containerized workflow for running the package with TypeDB and ROS dependencies.
