# CLAUDE.md

This file provides Claude Code-specific guidance. For full project documentation see [AGENTS.md](AGENTS.md) and [docs/agent-notes.md](docs/agent-notes.md).

## Primary Goal

Migrate `typedb_tactics` from TypeDB 2 to **TypeDB 3** and update it to use the new `ros_typedb` package API (composition instead of inheritance, new import paths, new fetch syntax and result format).

## Read These First

- **[AGENTS.md](AGENTS.md)** — full project overview, dependencies, common commands, Docker setup, TypeDB 3 migration notes, TypeQL pitfalls, and agent helpers.
- **[docs/agent-notes.md](docs/agent-notes.md)** — quick checklist, code style rules, common failure checks, migration-specific failure checks, and mandatory completion checks.

## Four Key Changes at a Glance

| # | What changed | Old | New |
|---|---|---|---|
| 1 | **Class design** | `TacticalRetreatInterface(TypeDBInterface)` — inheritance | Composition: `self.db = TypeDBInterface(...)` — all query calls become `self.db.fetch_database(q)` etc. |
| 2 | **Import paths** | `from ros_typedb.typedb_interface import convert_py_type_to_query_type` | `from ros_typedb.typedb_helpers import convert_py_type_to_query_type` (MatchResultDict stays in `typedb_interface`) |
| 3 | **Fetch query syntax** | `fetch $node: node_name, namespace;` | `fetch { "node_name": $node.node-name, "namespace": $node.namespace };` |
| 4 | **Fetch result format** | `result['node']['node_name'][0]['value']` | `result['node_name']` — flat native Python value |

Full details with code examples are in the `## TypeDB 3 Migration` section of [AGENTS.md](AGENTS.md).

## Working Branch

All migration work goes on a new branch, e.g. `typedb3`. The current stable code lives on `optimizations`. Do **not** commit directly to `optimizations` or `main`.

```bash
git checkout -b typedb3
```

## Before Claiming Work Is Done

Run lint + tests inside the `tactical_retreat` container and ensure all pass:

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics \
   --pytest-args -k test_flake8'

docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics \
   --pytest-args -k test_pep257'
```

Also run the functional tests relevant to any modules you changed. See [AGENTS.md](AGENTS.md) for the full test commands.
