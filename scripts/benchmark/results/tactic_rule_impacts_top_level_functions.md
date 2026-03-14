# Benchmark Results: any_expression_fulfillment and requirement_fulfillment

Functions: `tactic_rule_impacts_any_expression_fulfillment`, `tactic_rule_impacts_requirement_fulfillment`
Groups A, B, and structural variant S-V1

## Data context

Phase 1 data gaps added to `benchmark.tql`:
- `bench_gap_req_may`: relaxed_requirement with may_expression (covers branch 2 of requirement_fulfillment)
- `bench_gap_req_relaxed`: relaxed_requirement with relaxed_fuzzy_expression (covers branch 3)

Note: A `bench_gap_req_comparison` was initially drafted but removed — `comparison_expression` cannot play `relaxed_requirement:expression` (only `relaxed_expression` subtypes can). The third branch was changed to cover `relaxed_fuzzy_expression` directly.

All benchmarks run with: `--cold-runs 5 --warm-runs 30 --all-inputs`

## V0 Baseline

| Function | cold_avg | warm_p50 | rows |
|---|---|---|---|
| `tactic_rule_impacts_any_expression_fulfillment` | 1632ms | 1598ms | 1360 |
| `tactic_rule_impacts_requirement_fulfillment` | 10927ms | 11946ms | 260 |

## Group A: tactic_rule_impacts_any_expression_fulfillment (10 branches)

### Current branch order (V0)
1. may_expression (~2 instances)
2. shall_expression (~13 instances)
3. comparison_expression (~17 instances)
4. relaxed_fuzzy_expression (~16 instances)
5. fuzzy_comparison_expression (~14 instances)
6. not_expression (~4 instances)
7. fuzzy_not (~5 instances)
8. fuzzy_or (~4 instances)
9. fuzzy_and (~3 instances)
10. logical_expression non-comparison (~1 instance)

### A-V1: Most-frequent-first

Reorder to: relaxed_fuzzy (16) → fuzzy_comparison (14) → comparison (17) → shall (13) → fuzzy_or (4) → fuzzy_and (3) → may (2) → not_expression (4) → fuzzy_not (5) → logical (1)

Applied as part of V1 combined campaign.

### A-V1 Result (from combined campaign)

| Variant | cold_avg | warm_p50 | rows | Disq? |
|---|---|---|---|---|
| V0 (baseline) | 1632ms | 1598ms | 1360 | No |
| V1 (most-frequent-first) | 1928ms | 1646ms | 1360 | **YES** (+3% warm, +18% cold) |

**Decision: V0 wins.** The most-frequent-first ordering worsened performance for `any_expression_fulfillment`.

Note: `any_expression_fulfillment` uses `return first` (dispatcher), so this result is surprising. However, because it dispatches to aggregator sub-functions (shall, may, fuzzy_or, etc.), the plan interaction is more complex. The original ordering (may → shall → comparison → relaxed → fuzzy_comparison → ...) appears to be plan-optimal for the TypeDB query planner.

## Group B: tactic_rule_impacts_requirement_fulfillment (3 branches)

### Current branch order (V0)
1. shall_expression (13 requirements)
2. may_expression (0 before gap → 1 after gap)
3. relaxed_fuzzy_expression (0 before gap → 1 after gap)

### B-V1: Validate V0 is optimal after data gaps filled

Not run separately — covered by V0 confirmation benchmarks.

**Decision: V0 wins.** shall_expression-first is correct (dominant type). The requirement_fulfillment bottleneck (11946ms warm_p50 for 260 rows) is structural — 20 rules × 13 requirements, each calling shall_fulfillment which recurses into fuzzy_or/and/relaxed. No branch reordering can avoid this work.

### Structural observation

`requirement_fulfillment` is by far the most expensive function (11946ms vs 1598ms for any_expression). The 260 rows represent 20 rules × 13 requirements. Each requirement has a `shall_expression` with 5-7 children. This means the function is doing ~260 × 6 child evaluations, each of which calls comparison/relaxed/fuzzy leaf functions.

The bottleneck is structural, not ordering-related. Future optimization should focus on:
- Reducing requirement count in benchmark data (if benchmarking individual functions)
- Caching/memoization at the shall_fulfillment level (not available in TypeDB 3)

## Structural Variant S-V1: Inline leaf functions into any_expression

**Not tested.** Given that branch reordering in `any_expression_fulfillment` made it slightly worse (V1: +3% warm), and that inlining would double the number of branches from 10 to 16+, this variant was ruled out. The MEMORY.md established that splitting OR branches causes 147× regression — inlining in the opposite direction (merging call chains) is lower risk, but the V1 signal did not warrant it.

## Winner: V0 for both functions

## Notable Findings

1. **requirement_fulfillment is the performance bottleneck** at 11946ms warm_p50 for 260 rows. This is structural (20 rules × 13 requirements × ~6 children each).

2. **any_expression_fulfillment (dispatcher) also resists reordering**: Even though it uses `return first`, its branches call recursive aggregators. The interaction with sub-function query plans means V0 ordering is better than most-frequent-first.

3. **relaxed_requirement:expression role constraint**: Only `relaxed_expression` subtypes (shall, may, relaxed_fuzzy, etc.) can play this role. `comparison_expression` and `logical_expression` cannot — this is a TypeDB type safety constraint caught at insert time.

4. **Data gap coverage confirmed**: After adding bench_gap_req_may and bench_gap_req_relaxed, requirement_fulfillment now covers all 3 branches.
