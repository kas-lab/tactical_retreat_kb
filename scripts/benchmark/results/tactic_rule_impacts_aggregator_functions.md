# Benchmark Results: fuzzy_or, fuzzy_and, shall, may aggregator functions

Functions: `tactic_rule_impacts_fuzzy_or_fulfillment`, `tactic_rule_impacts_fuzzy_and_fulfillment`,
           `tactic_rule_impacts_shall_fulfillment`, `tactic_rule_impacts_may_fulfillment`
Groups C, C2, D, D2

## Data context

Phase 1 data gaps added to `benchmark.tql`:
- `bench_gap_fuzzy_or_leaf`: fuzzy_or with fuzzy_comparison_expression child
- `bench_gap_fuzzy_and_full`: fuzzy_and with fuzzy_not + not_expr + fuzzy_ascend + relaxed children
- `bench_gap_may_full`: may_expression with fuzzy_or_1 + fuzzy_and_1 + fuzzy_not + less_than_equal + propositional
- `bench_gap_shall_full`: shall_expression with fuzzy_not + bench_gap_may_full + less_than_equal + propositional

All benchmarks run with: `--cold-runs 5 --warm-runs 30 --all-inputs`

## V0 Baseline

| Function | cold_avg | warm_p50 | rows |
|---|---|---|---|
| `tactic_rule_impacts_fuzzy_or_fulfillment` | 182ms | 155ms | 80 |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | 146ms | 119ms | 60 |
| `tactic_rule_impacts_shall_fulfillment` | 509ms | 476ms | 120 |
| `tactic_rule_impacts_may_fulfillment` | 234ms | 207ms | 60 |

## V1 Combined: Most-Frequent-First Reordering

Applied simultaneously to fuzzy_or, fuzzy_and, may, shall:
- **fuzzy_or/and**: comparison_expression first (most frequent child type), then relaxed, logical, fuzzy_not, not_expression, fuzzy_comparison
- **shall**: relaxed_fuzzy_expression first (5 instances), then fuzzy_or (2), fuzzy_and (2), fuzzy_not (1), may (1), comparison (1), logical (1)
- **may**: relaxed_fuzzy_expression first (2-3 instances), then fuzzy_or (1), fuzzy_and (1), fuzzy_not (1), comparison (1), logical (1)

### V1 Combined Results

| Function | V0 warm_p50 | V1 warm_p50 | Delta |
|---|---|---|---|
| `tactic_rule_impacts_fuzzy_or_fulfillment` | 155ms | 195ms | **+26% WORSE** |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | 119ms | 149ms | **+25% WORSE** |
| `tactic_rule_impacts_shall_fulfillment` | 476ms | 599ms | **+26% WORSE** |
| `tactic_rule_impacts_may_fulfillment` | 207ms | 253ms | **+22% WORSE** |
| `tactic_rule_impacts_any_expression_fulfillment` | 1598ms | 1646ms | +3% worse |
| `tactic_rule_impacts_requirement_fulfillment` | 11946ms | 12072ms | +1% worse |

## Summary Table

| Variant | Description | cold_avg | warm_p50 | rows | Disq? |
|---|---|---|---|---|---|
| V0 (baseline) | Original ordering | 509ms (shall) | 476ms (shall) | 120 | No |
| V1 | Most-frequent-first reordering | 634ms (shall) | 599ms (shall) | 120 | **YES** (all worse) |

## Winner: V0 for ALL aggregator functions

Schema unchanged.

## Notable Findings

1. **Most-frequent-first heuristic FAILS for aggregate `min`/`max` functions**: TypeDB must evaluate ALL branches to compute the aggregate. Unlike `return first` dispatch functions, there is no short-circuit. Reordering branches changes the query plan execution order but not the work performed — and in this case the original plan was better.

2. **V0 ordering appears plan-optimal**: The original branch order (fuzzy_or → fuzzy_and → fuzzy_not → may → relaxed → comparison → logical for `shall_fulfillment`) aligns with how TypeDB's optimizer handles tree-shaped expression queries. Changing it consistently worsened performance.

3. **Magnitude of regression is large**: +22-26% regression across all four functions from reordering alone. This is significant — the branch order matters, but the direction is opposite to what the data-count heuristic predicts for aggregators.

4. **Interaction effects**: Since shall calls may, and may calls fuzzy_or/and, simultaneous changes to all functions amplified the regression. Individual function changes were not tested separately (given the clear directional signal from the combined test).

5. **Root cause hypothesis**: TypeDB's internal OR-branch planner appears to prefer a "narrower-type-first" plan for aggregate functions (fuzzy_or, fuzzy_and are more selective role-player constraints than comparison_expression), whereas for dispatch functions the "largest-set-first" plan wins (as confirmed in the measure_value study).
