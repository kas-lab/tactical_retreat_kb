# typedb_tactics agent guide

## Current architecture

`typedb_tactics` contains both the older TypeDB-backed implementation and the newer
Xtext-model implementation used by the current SUAVE/Tactical Retreat workflow.

- `typedb_tactics/tactical_retreat_kb_xtext.py` and
  `typedb_tactics/xtext_tactical_retreat_interface.py` operate directly over the
  Xtext/Java models. Do not assume these two files read or write TypeDB.
- `typedb_tactics/tactical_retreat_kb.py` and
  `typedb_tactics/typedb_tactical_retreat_interface.py` are the TypeDB-backed
  implementation. The conceptual models are mostly shared with the Xtext path,
  but runtime behavior and dependencies differ.
- Schemas under `schemas/` and data under `test/data/` are primarily for the
  TypeDB path and tests.

## Editable scope

This package is editable. Preserve user changes and avoid broad refactors unless
requested. Be especially careful with the Xtext files, which may have active
experimental edits.

## Dependencies

Expected runtime is ROS 2 Humble in the `suave_tactical_retreat` workspace/container.
The Xtext path also depends on the Java/JPype model bridge from `adapt_x`.
The older TypeDB path depends on TypeDB 2.x and the Python TypeDB driver.

Source the workspace before running ROS-dependent commands:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Docker check pattern from the workspace root:

```bash
docker exec suave_tactical_retreat bash -lc 'cd /home/ubuntu-user/suave_ws && source /opt/ros/humble/setup.bash && source install/setup.bash && <command>'
```

## Common checks

From the workspace root:

```bash
python3 scripts/focused_test.py --package typedb_tactics
```

Or select a specific test with `--test PATH`.
Use `--dry-run` to inspect Docker/source-overlay setup first. This does not
start TypeDB or build the workspace; package-wide tests need their dependencies.

Prefer focused checks for changed files/tests:

```bash
python3 -m py_compile typedb_tactics/<changed_file>.py
colcon test --packages-select typedb_tactics --event-handlers console_direct+
```

For lint-only package checks:

```bash
colcon test --packages-select typedb_tactics --pytest-args -k test_flake8
colcon test --packages-select typedb_tactics --pytest-args -k test_pep257
```

TypeDB-dependent tests require a TypeDB server on `localhost:1729`. If TypeDB is
not running, either skip TypeDB-specific tests or report that they could not be
run.

## Runtime/model notes

- Xtext model assets for the SUAVE/Tactical Retreat use case live mainly under
  `src/suave_rebetmc/models/`.
- SUAVE context variables may map multiple measurements to the same ROS topic
  (for example `/diagnostics`). A non-matching diagnostics message can produce
  `None`; do not treat that as a valid replacement for an existing measurement
  unless the requested behavior explicitly requires clearing it.
- Check the active implementation before applying guidance from other branches;
  do not assume compact planner or proxy batching APIs exist in this checkout.
- Feature `selected` state persistence should happen only after adaptation
  execution succeeds. Planning is not proof of successful runtime execution.
- In the Xtext path, `_current_configuration()` uses
  `fmConfiguration.getSelectedFeatures()` and reads each feature's name.
  FeatureIDE's `getSelectedFeatureNames()` returns a HashSet and loses order.
- `configuration_delta()` preserves input feature order with feature-level
  uniqueness only. Deselections precede selections, each in model order.
  Do not deduplicate resolution actions or impose action-type sorting.
- `reconfiguration()` and `change_configuration()` must pass ordered iterables
  to the delta method, not sets. The latter preserves its supplied target order.
- Extracted FeatureIDE sources live in `src/adapt_x/extracted_featureide/`;
  verify they match the runtime JAR before making library-version claims.

## TypeDB-specific cautions

When editing schemas/rules:

- Do not create a relation and assign attributes to it in the same `then` clause.
- Variables used in `then` must be bound in `when` outside nested patterns.
- Avoid negation cycles where a rule reads and writes the same predicate under
  `not {}`.
- Prefer minimal schema edits over parallel relation hierarchies.

## Benchmarking TypeDB queries

Use only when changing TypeDB query/schema performance paths:

```bash
python3 scripts/benchmark.py --runs 1 --methods get_potential_requirements_fulfillment
python3 scripts/benchmark_queries.py --profiles hyp --runs 5
```
