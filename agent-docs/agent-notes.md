# Agent Notes

This file is a short checklist for agents working in this repo.

## Quick test entrypoint

Preferred focused run (hypothetical fulfillment tests) inside Docker:

```bash
scripts/run-tests-docker.sh -k test_hyp
```

## Code style

- Python code must pass flake8 and pep257 tests
- Add the following copyright to python files

```Python
# Copyright 2026 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

## Common failure checks

- Is TypeDB running on `localhost:1729`?
- Is the ROS + workspace environment sourced?
- Is the `tactical_retreat` container running (if using Docker)?

## Dockerfile update required

The `Dockerfile` pins TypeDB 2 and must be updated before building:

- Line 43: `typedb=2.28.3` → TypeDB 3.x apt package (check typedb.com for current install instructions)
- Line 46: `pip3 install typedb-driver==2.28.0` → `pip3 install typedb-driver` (3.x)
- Lines 50–51: TypeDB Studio 2.28.0 `.deb` → TypeDB 3 Studio version (or remove if not needed)
- `openjdk-11-jre` can be removed once confirmed — TypeDB 3 is written in Rust, no JVM needed

**All testing and execution must happen inside the `tactical_retreat` container.** The TypeDB server runs as the container entrypoint. Do not run tests on the host.

Rebuild after editing the Dockerfile:

```bash
docker build --secret id=gh_token,src=<(gh auth token) \
  --build-arg DEPS_CACHE_BUSTER=$(date +%s) -t tactical_retreat .
```

## TypeDB 3 migration failure checks

- **Fetch query returns empty list or `KeyError`** → check that fetch query uses TypeDB 3 `{ }` syntax:
  ```typeql
  # WRONG (TypeDB 2)
  fetch $node: node_name, namespace;
  # CORRECT (TypeDB 3)
  fetch { "node_name": $node.node_name, "namespace": $node.namespace };
  ```
- **Result parsing fails with `TypeError` on `[0]['value']`** → the fetch result format is now flat native Python. Replace `result['var']['attr'][0]['value']` with `result['attr']` directly.
- **Aggregate returns `None`** → check the query uses TypeDB 3 `select`/`reduce` syntax:
  ```typeql
  # WRONG (TypeDB 2)
  get $node; count;
  # CORRECT (TypeDB 3)
  select $node; reduce $c = count;
  ```
- **`AttributeError: 'TacticalRetreatInterface' object has no attribute 'sort_fetch_results'`** → `sort_fetch_results` has been removed. Remove it from the constructor and sort results in Python after fetching.
- **`TypeError` in `TacticalRetreatInterface.__init__`** → constructor signature changed. `TypeDBInterface.__init__` no longer accepts `sort_fetch_results`; remove it from all call sites.
- **`ImportError: cannot import name 'convert_py_type_to_query_type' from 'ros_typedb.typedb_interface'`** → this function moved to `ros_typedb.typedb_helpers`. Update import:
  ```python
  from ros_typedb.typedb_helpers import convert_py_type_to_query_type
  from ros_typedb.typedb_helpers import convert_query_type_to_py_type
  # MatchResultDict is still in ros_typedb.typedb_interface
  ```
- **Schema error on `sub attribute, value string`** → update to TypeDB 3 syntax: `attribute foo, value string;`

## Rule authoring reminders

- Avoid negation cycles: do not read/write the same predicate under `not {}`.
- Variables in `then` must be bound in `when` outside nested blocks.
- If you need to assign attributes to a relation, bind or create the relation first.

## Fetch + benchmark reminders

- TypeDB 3 does not guarantee result order; `sort_fetch_results` is removed. Sort results in Python after fetching when deterministic order is required for assertions.
- For quick interface-path checks: `python3 scripts/benchmark.py --runs 1 --methods get_potential_requirements_fulfillment`.
- For bottleneck decomposition: `python3 scripts/benchmark_queries.py --profiles hyp --runs 5`.
- Avoid performance conclusions from a single run; compare p50/p95 and row stability.

## Mandatory completion checks

- Always run and pass both lint/style tests before marking work as done:
  - `colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8`
  - `colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_pep257`
