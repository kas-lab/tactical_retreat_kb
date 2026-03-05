# Schema Guide (TypeDB 3)

This file gives agents fast, practical context for `schemas/` so they can change queries/models without re-discovering domain structure each time.

## How to use this guide

- Use this as schema intent context.
- Use the dependency graph in `README.md` for load ordering.
- Validate syntax/behavior with package tests after any schema/query change.

## Schema modules and intent

### 1) `schemas/data_structure/`

Base reusable data structures used by other models.
Treat this as foundational vocabulary imported by most higher-level schemas.

### 2) `schemas/context_model/`

Environment/runtime context model (for example measurements and related interfaces).
Typical queries are in `schemas/context_model/queries/`.

### 3) `schemas/ros_model/`

ROS graph/domain entities and relations used by tactics and discovery logic.
Query helpers live in `schemas/ros_model/queries/`.

### 4) `schemas/logical_expressions/`

Core logical-expression primitives and composition patterns used by other reasoning models.

### 5) `schemas/feature_model/`

Feature-oriented model definitions.
`feature_model_logical_expression.tql` bridges feature model concepts with logical expressions.

### 6) `schemas/relaxed/`

Relaxed/graded requirement constructs used for non-binary fulfillment reasoning.
Query helpers live in `schemas/relaxed/queries/`.

### 7) `schemas/tactics_model/`

Tactics representation and related reasoning entities.
Query helpers live in `schemas/tactics_model/queries/`.

### 8) `schemas/discover_tactics_model/`

Discovery-oriented rules/queries to find tactic applicability and neighborhood effects.
Query helpers live in `schemas/discover_tactics_model/queries/`.

### 9) `schemas/discover_hypothetical_req_fulfillment/`

Model for hypothetical fulfillment analysis (what-if evaluation of requirement outcomes).

## Practical patterns for agents

- When debugging failed tests, start from the test fixture `.tql` and map referenced types/relations back to the module above.
- Keep schema edits and query edits together in one change when they are behavior-coupled.
- For deterministic tests, do not rely on fetch row order; sort in Python-side assertions/callers.
- Prefer TypeDB 3 syntax (`fetch { ... }`, `select ...; reduce ...;`), not legacy TypeDB 2 style.

## Text2TypeQL reference

Before writing new queries, search validated examples from `ros_typedb`:

```bash
cd /home/ubuntu-user/tactical_retreat_ws/src/ros_typedb
python3 scripts/find-text2typeql-examples.py "your query intent" --top-k 5 --min-score 1
```

Reference paths:

- Dataset: `src/ros_typedb/agent-data/text2typeql/dataset/`
- Guide: `src/ros_typedb/agent-data/text2typeql/CLAUDE.md`
