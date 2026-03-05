# Agent Guide

This file is for agents implementing and validating changes in this repository.
This is the single source of truth for agent workflow and commands.

## Agent docs location

- Keep agent process/checklist docs in `agent-docs/`.
- Schema intent/reference for agents lives in `agent-docs/schema-guide.md`.
- `doc/` and `docs/` are project/user documentation.
- Do not load `doc/` or `docs/` unless explicitly requested.

## Project layout

- `typedb_tactics/typedb_tactical_retreat_interface.py`: main TypeDB query interface.
- `typedb_tactics/tactical_retreat_kb.py`: ROS lifecycle KB node.
- `launch/tactical_retreat_kb.launch.py`: KB launch entrypoint.
- `schemas/`: TypeDB schemas.
- `test/`: package tests.
- `scripts/run-tests-docker.sh`: standard Docker test entrypoint.

## Development environment

Use Docker container `tactical_retreat` for build/test/run validation.

Start container with TypeDB server:

```bash
docker run -d --rm --name tactical_retreat \
  -v /etc/localtime:/etc/localtime:ro \
  -v $HOME/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics \
  -v $HOME/ros_workspaces/tactical_retreat_3_ws/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors \
  tactical_retreat typedb server
```

If you are also changing `ros_typedb`, add:
`-v $HOME/ros_workspaces/tactical_retreat_3_ws/src/ros_typedb:/home/ubuntu-user/tactical_retreat_ws/src/ros_typedb`

## Required workflow for code changes

1. Build package in container:

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon build --symlink-install --packages-select typedb_tactics"
```

2. Run relevant feature tests (focused or full):

```bash
scripts/run-tests-docker.sh
scripts/run-tests-docker.sh -k test_hyp
```

3. Run mandatory quality checks:

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8"

docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_pep257"
```

4. Final report must include:
- commands executed
- pass/fail summary
- blockers (if any)

## Code style and file header requirements

- All Python files must comply with `flake8` and `pep257`.
- For new or edited Python source files, keep the Apache 2.0 copyright header:

```python
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

## Testing commands

Run full package tests:

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics"
```

Run one test pattern:

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_ros_model"
```

## Implementation notes

- TypeDB target is 3.x.
- `TacticalRetreatInterface` composes `TypeDBInterface` (no inheritance).
- `infer` was removed from launch/interface constructors and must not be reintroduced.
- Query failures should remain explicit (`TypeDBQueryError`), not silently hidden.

## TypeDB 3 query/schema essentials

- Use TypeDB 3 query syntax (not TypeDB 2 syntax).
- For project schema/module intent, read `agent-docs/schema-guide.md` first.
- Fetch projections should use map/object form:

```typeql
match
  $node isa ROSNode;
fetch {
  "node_name": $node.node_name,
  "namespace": $node.namespace
};
```

- Aggregations should use `select` + `reduce`:

```typeql
match
  $n isa ROSNode;
select $n; reduce $c = count;
```

- TypeDB 3 does not guarantee fetch order; sort in Python if deterministic order is required by tests.
- Be careful with relation role cardinalities in schemas. If a role can have multiple players, annotate it explicitly (for example `@card(0..)`), otherwise commits can fail with constraint errors.

## Text2TypeQL reference (recommended)

Before writing/rewriting TypeQL, search the local validated examples in `ros_typedb`:

```bash
cd /home/ubuntu-user/tactical_retreat_ws/src/ros_typedb
python3 scripts/find-text2typeql-examples.py "your query intent" --top-k 5 --min-score 1
```

Additional references:

- Dataset: `src/ros_typedb/agent-data/text2typeql/dataset/`
- Guide: `src/ros_typedb/agent-data/text2typeql/CLAUDE.md`

## Helper scripts

- `scripts/run-tests-docker.sh`
- `scripts/benchmark.py`
- `scripts/benchmark_queries.py`
