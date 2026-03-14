# CLAUDE.md

Claude-specific notes for this repository.

## Canonical instructions

- Use [AGENTS.md](AGENTS.md) as the single source of truth.
- Skim [agent-docs/agent-notes.md](agent-docs/agent-notes.md) as a pre-implementation checklist.

## Scope

- Do not duplicate commands or workflow here.
- If this file conflicts with `AGENTS.md`, follow `AGENTS.md`.

## Context

- This package is migrated to **TypeDB 3**. Do not use TypeDB 2 syntax (rules, `isa!`, old driver API).
  - Exception: `isa!` **is** valid inside `fun` match bodies for exact-type dispatch in OR branches (e.g. `$x isa! FuzzySigmoid`). The restriction applies to schema *definitions*, not function bodies.

## Testing

- Test data files (`test/data/*.tql`) are single `insert` blocks; variables declared earlier in the block are reusable by later statements.
- When auditing schema function test coverage: check **every OR branch** of every `fun` has at least one test case that hits that branch. Dispatching functions like `quantified_value_fuzzy_expression` (4 branches: ValueSingleton+double/integer, Measure+double/integer) are easy to miss.
- `ROSNode` has `@card(1..1)` on `start_time` — any test data creating a `ROSNode` must include `has start_time <datetime>`.
- The benchmark-validation tests are opt-in for the default package suite. Run them directly, or set `TYPEDB_TACTICS_RUN_BENCHMARK_TESTS=1` if you intentionally want them included in a full pytest/colcon pass.

## Performance

- `neighbours()` shows **bimodal latency** (~1.8ms warm-JIT vs ~14ms cold) across fresh DB instances; both numbers are valid and unrelated to query changes. Use `scripts/benchmark/benchmark_dtm.py --repeats 3` to distinguish noise from real regressions.
- Removing redundant `isa` guards when variables are already typed by role position is safe and gives small gains (confirmed for `applicable_tactics`).
- `connected_nodes()` must recurse over `direct_neighbours()`, not `neighbours()`. The latter composes two recursive layers and caused `colcon test --packages-select typedb_tactics` to stall far beyond the normal ~45-50s runtime.
- User-facing benchmark tooling now lives under `scripts/benchmark/`. For requirement-impact work, `scripts/benchmark/benchmark_requirement_impact_functions.py` gives a per-function cold/warm breakdown and supports `-k/--function-regex` to narrow the measured functions.
