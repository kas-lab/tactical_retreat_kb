# Benchmark Results: tactic_rule_impacts leaf functions

Functions: `tactic_rule_impacts_fuzzy_leaf_fulfillment`, `tactic_rule_impacts_relaxed_leaf_fulfillment`
Groups G (fuzzy_leaf) and G2 (relaxed_leaf)

## Data context

All benchmarks run with: `--cold-runs 5 --warm-runs 30 --all-inputs`
Database: `benchmark_requirement_functions` (fresh per run)
Benchmark data: `scripts/benchmark/benchmark.tql` (with Phase 1 data gaps added)

## V0 Baseline (confirmed, 2 independent runs)

| Function | cold_avg | warm_p50 | rows |
|---|---|---|---|
| `tactic_rule_impacts_fuzzy_leaf_fulfillment` | 79ms | 66ms | 280 |
| `tactic_rule_impacts_relaxed_leaf_fulfillment` | 79ms | 67ms | 220 |

## Group G: tactic_rule_impacts_fuzzy_leaf_fulfillment

### Current branch order (V0)
1. fuzzy_ascend_expression (5 instances in benchmark data)
2. fuzzy_decay_expression (3 instances)
3. fuzzy_unimodal_expression (6 instances)

### G-V1: unimodal-first (6), ascend (5), decay (3) last

**Decision: NOT TESTED explicitly** — The V1 combined reordering campaign showed branch reordering for aggregate `min`/`max` functions consistently worsens performance vs V0. V0 wins.

**Reasoning**: For aggregator functions that evaluate ALL branches (return `min`/`max`), TypeDB evaluates every matching child across all branches. The ordering does not short-circuit like a single-dispatch function. The overhead from changing branch order appears to come from query plan recompilation and candidate enumeration order — which V0 was already tuned to handle.

## Group G2: tactic_rule_impacts_relaxed_leaf_fulfillment

### Current branch order (V0)
1. relaxed_unimodal_expression (7 instances — unimodal already first, optimal)
2. relaxed_ascend_expression (2 instances)
3. relaxed_decay_expression (4 instances)

V0 already has the most-frequent type first. G2-V1 (swap decay/ascend order) was not tested since the V1 combined campaign showed reordering does not help these aggregator-style functions.

## Winner: V0 for both functions

## Notable Findings

- **Aggregator functions** (`return min/max`) are fundamentally different from dispatcher functions (`return first`): since ALL matching branches must be evaluated to compute the aggregate, branch ordering does not provide early-exit savings.
- V0 ordering was already reasonable; no improvement found via reordering.
- fuzzy_leaf and relaxed_leaf contribute ~66-67ms warm_p50 for 280/220 rows respectively — these are called as sub-functions from shall/may/fuzzy_or/fuzzy_and.
