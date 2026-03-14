# Benchmark: tactic_rule_hypothetical_term functions

## Campaign summary

Functions benchmarked:
- `tactic_rule_hypothetical_fuzzy_term($tr, $e: fuzzy_comparison_expression) -> double`
- `tactic_rule_hypothetical_relaxed_term($tr, $e: relaxed_fuzzy_expression) -> double`

### Setup

- **Short benchmark**: 5 cold runs, 30 warm runs, all-inputs mode
- **Long benchmark** (top 3 + V0): 10 cold runs, 100 warm runs, all-inputs mode
- **Input counts**: fuzzy=280 pairs (20 rules × 14 expressions), relaxed=220 pairs (20 rules × 11 expressions)
- **Phase 0.5b**: Balanced benchmark data added to `benchmark.tql` to cover VS_double terms, VS_integer terms, `offset_value`-bearing expressions (fuzzy), and `required_period`-bearing expressions via `freq_as_close_as_possible_expression` (relaxed).

---

## Short benchmark results (5 cold / 30 warm)

| Variant | fuzzy cold_avg | fuzzy warm_p50 | relaxed cold_avg | relaxed warm_p50 | combined warm_p50 | Disq? |
|---------|---------------|---------------|-----------------|-----------------|-------------------|-------|
| V0 | 57.751ms | 47.576ms | 59.990ms | 49.398ms | 96.974ms | No |
| V1 | 57.522ms | 46.412ms | 60.202ms | 49.794ms | 96.206ms | No |
| V2 | 57.242ms | 46.521ms | 62.157ms | 48.386ms | 94.907ms | No |
| V3 | 58.085ms | 47.996ms | 59.964ms | 49.985ms | 97.981ms | No |
| V4 | 61.001ms | 50.669ms | 62.972ms | 52.568ms | 103.237ms | No |
| V5 | 57.954ms | 47.585ms | 60.216ms | 50.016ms | 97.601ms | No |
| V6 | 58.330ms | 48.313ms | 59.960ms | 48.909ms | 97.222ms | No |

avg_cold (for disqualification threshold × 1.15):
- fuzzy avg_cold = 58.269ms → threshold = 67.009ms (no variants disqualified)
- relaxed avg_cold = 60.780ms → threshold = 69.897ms (no variants disqualified)

Short-run ranking by combined warm_p50: V2 (94.907) < V1 (96.206) < V0 (96.974) < V6 (97.222)

**Selected for long benchmark: V2, V1, V0**

---

## Long benchmark results (10 cold / 100 warm)

| Variant | fuzzy cold_avg | fuzzy warm_p50 | relaxed cold_avg | relaxed warm_p50 | combined warm_p50 |
|---------|---------------|---------------|-----------------|-----------------|-------------------|
| V0 | 58.810ms | **47.449ms** | 60.315ms | **49.017ms** | **96.466ms** |
| V1 | 57.911ms | 47.929ms | 60.040ms | 49.506ms | 97.435ms |
| V2 | 57.909ms | 47.801ms | 60.012ms | 49.955ms | 97.756ms |

---

## Winner: V0 (baseline)

**V0 wins** with combined warm_p50 = 96.466ms, vs V1 = 97.435ms (+1.0ms) and V2 = 97.756ms (+1.3ms).

The short-run apparent advantages for V1 and V2 (−0.8ms and −2.1ms respectively) did not survive the 100-warm-run long benchmark. All differences are within the ~1ms noise floor for functions in the 47–50ms range. The schema is left unchanged at V0.

---

## Notable findings

1. **No-hoisting (V4) is significantly slower**: Moving `$e links (term: $term)` inside each OR branch added ~3ms to both functions (fuzzy +3.1ms, relaxed +3.2ms warm_p50). Hoisting the `links` constraint before the OR block is confirmed beneficial.

2. **Stage 2 reordering (V1, V2) shows noise-floor effects**: Short-run data suggested neither-first (V2) was the winner (−2ms), but 100-warm runs converged to within 1ms of V0. The benefit of putting the NOT-branch first is not statistically significant for these functions at this input scale.

3. **VS-first stage 1 (V3) is neutral-to-worse**: Putting VS branches before Measure in stage 1 gave no benefit. Since ~80% of inputs use Measure terms, putting Measure first (V0) is correct.

4. **`isa!` on Measure branch (V5) is neutral**: Exact-type dispatch did not improve performance. Measure has no subtypes in this schema.

5. **Merged VS branches (V6) gives mixed results**: Slight improvement for relaxed (−0.5ms) but slight regression for fuzzy (+0.7ms). No net benefit.

6. **Schema constraint**: `required_period` is only owned by `freq_as_close_as_possible_expression` (not `as_many_as_possible_expression` or `as_few_as_possible_expression`). The benchmark data required inserting `freq_as_close_as_possible_expression` instances to cover that branch. Benchmark data for `offset_value` required using actual `fuzzy_expression` subtypes (which inherit `offset_value` from `fuzzy_expression`).

7. **OR branch ordering contrast with measure_value function**: The −37% gain from NOT-branch-first in `tactic_rule_hypothetical_measure_value` does not replicate here. That function had ~420 pairs with sparse effects; these functions have structurally different sparsity patterns and the NOT-branch covers fewer total pairs.
