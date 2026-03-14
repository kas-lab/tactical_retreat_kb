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
- **OR branch ordering is the dominant `fun` performance lever for batch/all-rules queries.** Put the branch matching the *most* inputs first. In `tactic_rule_hypothetical_measure_value`, moving the "no effect" NOT-branch to first position gave −37% all-rules latency (59ms vs 95ms for 420 pairs); the same gain was invisible on single-rule benchmarks. Always benchmark with an all-inputs query, not just a single representative case.
- `links` before `isa` in an OR branch narrows candidates before the type check; small single-rule gain (~1%), moderate all-rules gain (~12%) — worth doing when the role link is selective.
- `links` constraints **can** be hoisted before the outer `{ } or { }` block in a `fun` match body (e.g. `$e links (role: $term);`) — valid and faster. However, `isa` constraints before the outer OR block cause a TypeDB parse error; keep those inside branches.
- Named relation variable in `fun` body: use `$r isa T, links (role: $x);` — NOT `$r (role: $x) isa T;` (the latter triggers [REP1] even in `fun` match context).
- **[CEX18]**: Cannot bind a function-call result directly to a cross-OR-branch variable (`let $out = func(...)`). Use an intermediate: `let $tmp = func(...); let $out = $tmp;`
- **Benchmark noise floor**: `fun` benchmarks have ~1ms run-to-run noise at the 35–40ms scale. Use `--warm-runs 100` (not 30) before declaring a winner — short runs can produce misleading rankings.
- Benchmark variant results for `tactic_rule_hypothetical_measure_value` (V0–V24): `scripts/benchmark/results/tactic_rule_hypothetical_measure_value.md`.
- Benchmark variant results for `tactic_rule_hypothetical_comparison_lhs/rhs_value` (V0–V9, V0 wins): `scripts/benchmark/results/tactic_rule_hypothetical_comparison_values.md`.
