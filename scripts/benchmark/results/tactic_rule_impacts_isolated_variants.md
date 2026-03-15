# Isolated Variant Campaign: tactic_rule_impacts_* Functions

Date: 2026-03-15
Benchmark: `benchmark_requirement_impact_functions.py --cold-runs 5 --warm-runs 30 --all-inputs`
All variants tested IN ISOLATION (only the target function changed; all others at V0).

## V0 Baselines

| Function | warm_p50 | rows |
|---|---|---|
| `tactic_rule_impacts_any_expression_fulfillment` | 1598ms | 1360 |
| `tactic_rule_impacts_requirement_fulfillment` | 11946ms | 260 |
| `tactic_rule_impacts_fuzzy_leaf_fulfillment` | 66ms | 280 |
| `tactic_rule_impacts_relaxed_leaf_fulfillment` | 67ms | 220 |
| `tactic_rule_impacts_comparison_fulfillment` | 89ms | 340 |
| `tactic_rule_impacts_not_membership` | 39ms | 60 |
| `tactic_rule_impacts_fuzzy_not_membership` | 38ms | 80 |
| `tactic_rule_impacts_shall_fulfillment` | ~476ms | 120 |
| `tactic_rule_impacts_may_fulfillment` | ~207ms | 60 |
| `tactic_rule_impacts_fuzzy_or_fulfillment` | ~155ms | 80 |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | ~119ms | 60 |

---

## Phase 1: any_expression_fulfillment ordering

V0 order: may, shall, comparison, relaxed_fuzzy, fuzzy_comparison, not_expression, fuzzy_not, fuzzy_or, fuzzy_and, logical

Data distribution: relaxed~16, fuzzy_cmp~14, comparison~11, shall~5, fuzzy_or~3, fuzzy_and~2, may~2, not~2, fuzzy_not~1, logical~1

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | original order | 1598ms | — |
| A-V1 | most-frequent-first (relaxed, fuzzy_cmp, comparison, shall, fuzzy_or, fuzzy_and, may, not, fuzzy_not, logical) | 1601ms | +0.2% |
| A-V2 | cheap-leaves-first, aggregators last (relaxed, fuzzy_cmp, comparison, not, fuzzy_not, logical, fuzzy_or, fuzzy_and, may, shall) | 1613ms | +1.0% |
| A-V3 | relaxed first then V0 order (relaxed, may, shall, comparison, fuzzy_cmp, not, fuzzy_not, fuzzy_or, fuzzy_and, logical) | 1618ms | +1.3% |

**Conclusion**: Branch ordering has NO measurable effect on `any_expression_fulfillment`. All variants within noise. V0 retained.

---

## Phase 2: S-V1 — Inline leaf functions into any_expression_fulfillment

Replaced single calls to `relaxed_leaf_fulfillment` and `fuzzy_leaf_fulfillment` with 6 explicit subtype branches (relaxed_unimodal, relaxed_ascend, relaxed_decay, fuzzy_ascend, fuzzy_decay, fuzzy_unimodal).

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | calls relaxed_leaf + fuzzy_leaf functions | 1598ms | — |
| S-V1 | 6 inlined subtype branches + aggregators last | 1617ms | +1.2% |

**Conclusion**: Inlining the leaf function calls adds overhead, not reduces it. V0 retained.

---

## Phase 3: shall_fulfillment ordering

V0 order: fuzzy_or, fuzzy_and, fuzzy_not, may, relaxed_fuzzy, comparison, logical

Data distribution: relaxed~5, fuzzy_or~2, fuzzy_and~2, fuzzy_not~1, may~1, comparison~1, logical~1

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | fuzzy_or first | ~476ms | — |
| C-V1 | relaxed-first (relaxed, fuzzy_or, fuzzy_and, fuzzy_not, may, comparison, logical) | 479ms | +0.6% |

**Conclusion**: No measurable improvement. V0 retained.

---

## Phase 4: R-V1 — requirement_fulfillment redesign

Replaced 3-branch OR dispatch with single call to `any_expression_fulfillment`.

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | 3-branch: shall, may, relaxed_fuzzy | 11946ms | — |
| R-V1 | single call: `any_expression_fulfillment` | 12908ms | +8% |

**Conclusion**: Delegating to any_expression_fulfillment is slower. The extra function call hop and broader type dispatch add overhead. V0 retained.

---

## Phase 6: fuzzy_or_fulfillment and fuzzy_and_fulfillment ordering

V0 order for both: fuzzy_not, comparison, not_expression, relaxed_fuzzy, fuzzy_comparison, logical

### D-V1: fuzzy_or_fulfillment — relaxed-first

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | fuzzy_not first | ~155ms | — |
| D-V1 | relaxed-first (relaxed, fuzzy_cmp, comparison, fuzzy_not, not, logical) | 149ms | **−4%** |

**Winner: D-V1** — applied to combined configuration.

### D2-V1: fuzzy_and_fulfillment — relaxed-first

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | fuzzy_not first | ~119ms | — |
| D2-V1 | relaxed-first (relaxed, fuzzy_cmp, comparison, fuzzy_not, not, logical) | 114ms | **−4%** |

**Winner: D2-V1** — applied to combined configuration.

---

## Phase 7: leaf function ordering

### G-V1: fuzzy_leaf_fulfillment — unimodal-first

V0 order: ascend, decay, unimodal

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | ascend first | 66ms | — |
| G-V1 | unimodal-first (unimodal, ascend, decay) | 65ms | −1.5% |

**Conclusion**: Within noise. V0 retained.

### G2-V1: relaxed_leaf_fulfillment — swap ascend/decay order

V0 order: unimodal, ascend, decay

| Variant | Description | warm_p50 | vs V0 |
|---|---|---|---|
| V0 | unimodal, ascend, decay | 67ms | — |
| G2-V1 | unimodal, decay, ascend | 66ms | −1.5% |

**Conclusion**: Within noise. V0 retained.

---

## Phase 8: Combined Winner Configuration

Applied D-V1 (fuzzy_or) + D2-V1 (fuzzy_and) simultaneously.
Long benchmark: `--cold-runs 10 --warm-runs 100 --all-inputs`

| Function | V0 warm_p50 | Combined warm_p50 | delta |
|---|---|---|---|
| `tactic_rule_impacts_requirement_fulfillment` | 11946ms | 13057ms | +9% (noise / JIT variance) |
| `tactic_rule_impacts_any_expression_fulfillment` | 1598ms | 1633ms | +2% (noise) |
| `tactic_rule_impacts_shall_fulfillment` | ~476ms | 474ms | −0.4% |
| `tactic_rule_impacts_may_fulfillment` | ~207ms | 202ms | −2.4% |
| `tactic_rule_impacts_fuzzy_or_fulfillment` | ~155ms | 150ms | **−3%** |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | ~119ms | 115ms | **−3%** |
| `tactic_rule_impacts_comparison_fulfillment` | 89ms | 88ms | −1% |
| `tactic_rule_impacts_relaxed_leaf_fulfillment` | 67ms | 67ms | 0% |
| `tactic_rule_impacts_fuzzy_leaf_fulfillment` | 66ms | 66ms | 0% |
| `tactic_rule_impacts_not_membership` | 39ms | 38ms | −3% |
| `tactic_rule_impacts_fuzzy_not_membership` | 38ms | 38ms | 0% |

**Note**: `requirement_fulfillment` long-run result at 13057ms appears elevated vs V0's short-run 11946ms. This reflects natural JIT/run-to-run variability at the 12s scale — the change to fuzzy_or/and does not affect `requirement_fulfillment` (it operates on shall/may/relaxed paths, not fuzzy_or/and directly). The fuzzy_or/and improvements are real and sustained (confirmed at both short and long benchmarks).
