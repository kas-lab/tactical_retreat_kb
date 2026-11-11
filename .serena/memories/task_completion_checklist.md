# Task completion checklist

Before considering work done in this repository:

- Ensure the ROS environment and workspace are sourced if the task requires runtime checks.
- Ensure a TypeDB server is running, usually at `localhost:1729`, before tests or KB-node checks.
- Run the most relevant focused tests for the module you changed instead of defaulting to the full suite; full suite setup is relatively expensive.
- Always run both mandatory style gates and make sure they pass:
  - `colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_flake8`
  - `colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_pep257`
- If you changed hot-path queries or schema/rules related to hypothetical fulfillment, compare behavior and performance with:
  - `python3 scripts/benchmark.py --runs 1 --methods get_potential_requirements_fulfillment`
  - `python3 scripts/benchmark_queries.py --profiles hyp --runs 5`
- If schema/rules changed, check row-count stability and avoid claiming gains from a single benchmark run.
- If constructor/fetch API changes were made, verify `ros_typedb` compatibility to avoid runtime `TypeError` mismatches.
- If using Docker-based validation, confirm the `tactical_retreat` container is running before `docker exec` or `scripts/run-tests-docker.sh`.
- Preserve existing user changes in the worktree; do not revert unrelated modifications.