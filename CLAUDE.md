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

## Dockerfile Must Be Updated

The `Dockerfile` hardcodes TypeDB 2 (`typedb=2.28.3`, `typedb-driver==2.28.0`). **Update it before building** — see the "Change 0: Dockerfile" entry in the TypeDB 3 Migration section of [AGENTS.md](AGENTS.md) for the exact lines to change.

**All testing and execution must happen inside the `tactical_retreat` container**, not on the host. The TypeDB server runs as the container's entrypoint. Start the container before running any tests or queries.

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

## TypeDB 3: No `rule` Support — Use `fun` Instead

TypeDB 3.8 removed the `rule` keyword entirely. Any `define` block containing `rule`
causes `[TSV7] Query parsing failed`. All rules must be ported to TypeDB 3 `fun` functions:

```typeql
define
fun my_fun($arg: SomeType, $x: double) -> { double }:
    match $arg has some_attr $val; let $result = $val * $x;
    return { $result };
```

Docs: https://typedb.com/docs/typeql-reference/functions/

Key difference: `fun` returns values, not inferred attribute instances. Queries must
explicitly call the function instead of matching `has computed_attr $v`.

## TypeDB 3 Schema Loading Fix (ros_typedb)

`transaction.query(schema).resolve()` raises `[TSV7]` for schemas with rules.
Without `.resolve()`, non-rule `define` queries still commit correctly.
Fix applied in `ros_typedb` `typedb_interface.py`: removed `.resolve()` from the `define` path.

## TypeDB 3 Multi-Player Roles Need `@card(0..)`

`relates some_role` defaults to `@card(0..1)` in TypeDB 3. Any role that can have
more than one player must be annotated: `relates some_role @card(0..)`.
Violations produce `[CNT5] Constraint '@card(0..1)' has been violated`.

## Multi-Stage Pipeline Pattern (avoids [REP1])

In a single INSERT block you cannot create a named relation `$r` AND use it as a role
player. Fix: make `$r` anonymous, give it an `expression_name` key attribute, then
match it in a separate pipeline stage:

```typeql
# Stage 1 INSERT – anonymous leaf with key
(role: $x) isa some_type, has expression_name 'my_key';
# Stage 2 match+insert
match $s1 isa some_type, has expression_name 'my_key';
insert (role2: $s1) isa other_type;
```

Use unique variable names across stages to avoid `[INF11]` type conflicts ($s1_e, $s2_e, …).

## Container File Sync

The host (`~/ros_workspaces/tactical_retreat_3_ws/`) and container (`/home/ubuntu-user/tactical_retreat_ws/`) are **not bind-mounted**. After editing on the host, sync with:
```bash
docker cp <host_path> tactical_retreat:<container_path>
```
For Python packages, also rebuild: `docker exec tactical_retreat bash -lc '... colcon build --packages-select <pkg>'`

## TypeDB Data Corruption Recovery

If TypeDB fails to start (permission/WAL errors on data files):
```bash
docker exec -u root tactical_retreat bash -c 'rm -rf /opt/typedb/core/server/data/test_*'
# If still failing:
docker exec -u root tactical_retreat bash -c 'rm -rf /opt/typedb/core/server/data/*'
docker restart tactical_retreat
```
