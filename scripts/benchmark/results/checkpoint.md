# Benchmark Optimization Campaign Checkpoint

**Date**: 2026-03-14
**Status**: COMPLETE — all phases done

## Phase 0: Pre-flight Test
- Result: 11/11 PASS
- Command: `colcon test --packages-select typedb_tactics --pytest-args -k test_hypothetical_req_fulfillment`

## Phase 1: Data Gaps Added to benchmark.tql

Added before `# END BENCHMARK COMBO EXPANSION` marker (line 1763 → now ~1838):

| Variable | Type | Purpose |
|---|---|---|
| `bench_gap_gte_1`, `bench_gap_gte_2` | `greater_than_equal` | comparison_fulfillment branch coverage |
| `bench_gap_eq_1` | `equal` | comparison_fulfillment branch coverage |
| `bench_gap_ne_1` | `not_equal` | comparison_fulfillment branch coverage |
| `bench_gap_not_logical` | `not_expression` (inner: propositional) | not_membership logical branch |
| `bench_gap_fnot_relaxed` | `fuzzy_not` (inner: relaxed) | fuzzy_not_membership relaxed branch |
| `bench_gap_fnot_fuzzy` | `fuzzy_not` (inner: fuzzy_ascend) | fuzzy_not_membership fuzzy_comparison branch |
| `bench_gap_fnot_logical` | `fuzzy_not` (inner: propositional) | fuzzy_not_membership logical branch |
| `bench_gap_fuzzy_or_leaf` | `fuzzy_or` (child: fuzzy_ascend + relaxed) | fuzzy_or fuzzy_comparison branch |
| `bench_gap_fuzzy_and_full` | `fuzzy_and` (fuzzy_not + not_expr + fuzzy_ascend + relaxed) | fuzzy_and all branches |
| `bench_gap_may_full` | `may_expression` (fuzzy_or_1 + fuzzy_and_1 + fuzzy_not + less_than_equal + propositional) | may_fulfillment all branches |
| `bench_gap_shall_full` | `shall_expression` (fuzzy_not + bench_gap_may_full + less_than_equal + propositional) | shall_fulfillment all branches |
| `bench_gap_req_may` | `relaxed_requirement` → `bench_gap_may_full` | requirement_fulfillment may branch |
| `bench_gap_req_relaxed` | `relaxed_requirement` → `fake_as_close_expression` | requirement_fulfillment relaxed_fuzzy branch |

**Correction**: Initial draft used `bench_gap_req_comparison` with `$less_than_equal` — this caused `[INF6]/[QUA1]` error because `comparison_expression` cannot play `relaxed_requirement:expression`. Fixed to `bench_gap_req_relaxed` using a `relaxed_fuzzy_expression`.

## Phase 2: V0 Baseline

Short benchmark (5 cold, 30 warm, all-inputs):

| Function | cold_avg | warm_p50 | rows |
|---|---|---|---|
| `tactic_rule_impacts_requirement_fulfillment` | 10927ms | 11946ms | 260 |
| `tactic_rule_impacts_any_expression_fulfillment` | 1632ms | 1598ms | 1360 |
| `tactic_rule_impacts_shall_fulfillment` | 509ms | 476ms | 120 |
| `tactic_rule_impacts_may_fulfillment` | 234ms | 207ms | 60 |
| `tactic_rule_impacts_fuzzy_or_fulfillment` | 182ms | 155ms | 80 |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | 146ms | 119ms | 60 |
| `tactic_rule_impacts_comparison_fulfillment` | 101ms | 89ms | 340 |
| `tactic_rule_impacts_relaxed_leaf_fulfillment` | 79ms | 67ms | 220 |
| `tactic_rule_impacts_fuzzy_leaf_fulfillment` | 79ms | 66ms | 280 |
| `tactic_rule_impacts_not_membership` | 66ms | 39ms | 60 |
| `tactic_rule_impacts_fuzzy_not_membership` | 68ms | 38ms | 80 |

## Phase 3: Variants Tested

### V1 Combined: Most-Frequent-First Reordering
Applied to: fuzzy_or, fuzzy_and, may, shall, any_expression simultaneously.

**Result: UNIFORMLY WORSE** — +22-26% regression on aggregator functions (shall, may, fuzzy_or, fuzzy_and), +3% on any_expression, +1% on requirement_fulfillment.

**All individual groups (A, B, C, C2, D, D2, E, E2, F, G, G2): V0 wins.**

Key finding: The "most-frequent-first" heuristic works for single-dispatch functions (`return first`) but FAILS for aggregate functions (`return min`/`max`). TypeDB evaluates all branches for aggregates; there is no early-exit, and V0's original ordering is plan-optimal.

## Phase 4: Selection
V0 selected for all functions (no variants beat V0).

## Phase 5: Schema Changes Applied
**None** — V0 retained for all functions.

Tests after campaign: 11/11 PASS.

## Phase 6: Result Files Written

| File | Coverage |
|---|---|
| `tactic_rule_impacts_leaf_functions.md` | Groups G, G2 |
| `tactic_rule_impacts_comparison_not_functions.md` | Groups E, E2, F |
| `tactic_rule_impacts_aggregator_functions.md` | Groups C, C2, D, D2 |
| `tactic_rule_impacts_top_level_functions.md` | Groups A, B + S-V1 discussion |
| `variants_tactic_rule_impacts_all.md` | All variant TypeQL bodies + full result tables |

## Phase 7: Commit
Files committed:
- `scripts/benchmark/benchmark.tql` (data gaps added)
- `scripts/benchmark/results/` (5 result files + this checkpoint)

Schema file NOT committed (no changes from V0).

## Critical New Knowledge

1. **Aggregate `min`/`max` functions resist branch-ordering optimization**: V0 wins for all 11 impacts functions. Do NOT apply most-frequent-first to `return min/max` functions.

2. **relaxed_requirement:expression role constraint**: Only `relaxed_expression` subtypes can play this role. `comparison_expression` (logical subtype) cannot.

3. **Data gap correction**: Initial benchmark.tql data gap for `bench_gap_req_comparison` used wrong expression type — fixed to `bench_gap_req_relaxed` using `relaxed_fuzzy_expression`.

## Previously Completed (pre-campaign)
- `tactic_rule_hypothetical_measure_value` — V24 applied (NOT-first, −37%)
- `tactic_rule_hypothetical_comparison_lhs_value` — V0 wins
- `tactic_rule_hypothetical_comparison_rhs_value` — V0 wins
- `tactic_rule_hypothetical_relaxed_term` — V0 wins
- `tactic_rule_hypothetical_fuzzy_term` — V0 wins
