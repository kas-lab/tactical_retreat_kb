# Benchmark Results: comparison, not_membership, fuzzy_not_membership functions

Functions: `tactic_rule_impacts_comparison_fulfillment`, `tactic_rule_impacts_not_membership`, `tactic_rule_impacts_fuzzy_not_membership`
Groups E, E2, F

## Data context

Phase 1 data gaps added to `benchmark.tql`:
- `bench_gap_gte_1`, `bench_gap_gte_2`: `greater_than_equal` (2 new instances)
- `bench_gap_eq_1`: `equal` (1 new instance)
- `bench_gap_ne_1`: `not_equal` (1 new instance)
- `bench_gap_not_logical`: `not_expression` with inner `propositional_expression` (logical branch)
- `bench_gap_fnot_relaxed`: `fuzzy_not` with inner `relaxed_fuzzy_expression`
- `bench_gap_fnot_fuzzy`: `fuzzy_not` with inner `fuzzy_ascend_expression_1`
- `bench_gap_fnot_logical`: `fuzzy_not` with inner `propositional_expression`

All benchmarks run with: `--cold-runs 5 --warm-runs 30 --all-inputs`

## V0 Baseline

| Function | cold_avg | warm_p50 | rows | Branches |
|---|---|---|---|---|
| `tactic_rule_impacts_comparison_fulfillment` | 101ms | 89ms | 340 | 6 branches |
| `tactic_rule_impacts_not_membership` | 66ms | 39ms | 60 | 2 branches |
| `tactic_rule_impacts_fuzzy_not_membership` | 68ms | 38ms | 80 | 4 branches |

## Group F: tactic_rule_impacts_comparison_fulfillment

### Current branch order (V0)
1. less_than (~6 instances)
2. less_than_equal (~5 instances)
3. greater_than (2 instances)
4. greater_than_equal (2 instances after gap fill)
5. equal (1 instance after gap fill)
6. not_equal (1 instance after gap fill)

### F-V1: less_than first (already V0!) — no change needed

V0 already has less_than (most frequent) first. Data distribution after gap fill: less_than~6, less_than_equal~5, greater_than~2, greater_than_equal~2, equal~1, not_equal~1.

**Decision: V0 wins** — already optimally ordered. The V1 combined reordering campaign confirmed reordering aggregator functions does not improve performance.

Note: `comparison_fulfillment` is NOT an aggregate — it returns `first`. However the V1 combined campaign showed reordering across all functions uniformly degraded performance, suggesting the current ordering may be cache/plan-optimal for the TypeDB query planner even for dispatcher functions at this size.

## Group E: tactic_rule_impacts_not_membership (2 branches)

### Current branch order (V0)
1. comparison_expression (2 instances in `$not_expr` + `bench_gap_not_*`)
2. logical_expression non-comparison (1 instance with `bench_gap_not_logical`)

**Decision: V0 wins** — comparison already first (most frequent). With only 2 branches and balanced data, not worth changing.

## Group E2: tactic_rule_impacts_fuzzy_not_membership (4 branches)

### Current branch order (V0)
1. comparison_expression (1 instance: `$fuzzy_not` with `$less_than_equal`)
2. relaxed_fuzzy_expression (1 instance: `bench_gap_fnot_relaxed`)
3. fuzzy_comparison_expression (1 instance: `bench_gap_fnot_fuzzy`)
4. logical_expression non-comparison (1 instance: `bench_gap_fnot_logical`)

All branches equally represented after gap fill. **Decision: V0 wins** — balanced data, no dominant branch.

## Winner: V0 for all three functions

## Notable Findings

1. **Branch reordering for all tactic_rule_impacts_* functions**: A combined V1 campaign (reordering all 5 major functions simultaneously: fuzzy_or, fuzzy_and, may, shall, any_expression) showed **uniform regression** vs V0: requirement_fulfillment warm_p50 went from 11946ms → 12072ms (+1%), any_expression from 1598ms → 1646ms (+3%), shall from 476ms → 599ms (+26%), may from 207ms → 253ms (+22%), fuzzy_or from 155ms → 195ms (+26%), fuzzy_and from 119ms → 149ms (+25%).

2. **Aggregator functions are immune to branch-ordering optimization**: Functions returning `min`/`max` must evaluate all branches. The "most-frequent first" heuristic only helps single-dispatch `return first` functions.

3. **Data gaps verified**: All 4 new comparison types (gte×2, eq, ne) load correctly and contribute to the 340-row comparison benchmark.
