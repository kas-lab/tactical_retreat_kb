# All Variants Tested: tactic_rule_impacts_* functions

## Campaign Summary

**Total variants tested**: 2 (V0 baseline + V1 combined)
**Winner**: V0 for all 11 functions
**Schema changes applied**: None (V0 retained)
**Tests**: 11/11 passing throughout

---

## V0 Baseline (all functions)

Schema: `schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql`
No changes from pre-campaign state.

### V0 Branch Orders

**tactic_rule_impacts_fuzzy_or_fulfillment** (return max):
1. fuzzy_not
2. comparison_expression
3. not_expression
4. relaxed_fuzzy_expression
5. fuzzy_comparison_expression
6. logical_expression (not comparison)

**tactic_rule_impacts_fuzzy_and_fulfillment** (return min):
1. fuzzy_not
2. comparison_expression
3. not_expression
4. relaxed_fuzzy_expression
5. fuzzy_comparison_expression
6. logical_expression (not comparison)

**tactic_rule_impacts_may_fulfillment** (return max):
1. fuzzy_or
2. fuzzy_and
3. fuzzy_not
4. relaxed_fuzzy_expression
5. comparison_expression
6. logical_expression (not comparison)

**tactic_rule_impacts_shall_fulfillment** (return min):
1. fuzzy_or
2. fuzzy_and
3. fuzzy_not
4. may_expression
5. relaxed_fuzzy_expression
6. comparison_expression
7. logical_expression (not comparison)

**tactic_rule_impacts_any_expression_fulfillment** (return first):
1. may_expression
2. shall_expression
3. comparison_expression
4. relaxed_fuzzy_expression
5. fuzzy_comparison_expression
6. not_expression
7. fuzzy_not
8. fuzzy_or
9. fuzzy_and
10. logical_expression (not comparison, not not_expression)

---

## V1 Combined: Most-Frequent-First Reordering

Applied simultaneously to: fuzzy_or, fuzzy_and, may, shall, any_expression

### V1 Branch Orders

**tactic_rule_impacts_fuzzy_or_fulfillment** (V1):
```typeql
fun tactic_rule_impacts_fuzzy_or_fulfillment($tr: tactic_rule, $e: fuzzy_or) -> double:
  match
    $e links (expression: $child_fo);
    { $child_fo isa comparison_expression;
      let $m_cmp_fo = tactic_rule_impacts_comparison_fulfillment($tr, $child_fo);
      let $m_fo = $m_cmp_fo; } or
    { $child_fo isa relaxed_fuzzy_expression;
      let $m_rf_fo = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $child_fo);
      let $m_fo = $m_rf_fo; } or
    { $child_fo isa logical_expression;
      not { $child_fo isa comparison_expression; };
      let $m_log_fo = logical_expression_membership($child_fo);
      let $m_fo = $m_log_fo; } or
    { $child_fo isa fuzzy_not;
      let $m_fn_fo = tactic_rule_impacts_fuzzy_not_membership($tr, $child_fo);
      let $m_fo = $m_fn_fo; } or
    { $child_fo isa not_expression;
      let $m_not_fo = tactic_rule_impacts_not_membership($tr, $child_fo);
      let $m_fo = $m_not_fo; } or
    { $child_fo isa fuzzy_comparison_expression;
      let $m_leaf_fo = tactic_rule_impacts_fuzzy_leaf_fulfillment($tr, $child_fo);
      let $m_fo = $m_leaf_fo; };
  return max($m_fo);
```

**tactic_rule_impacts_fuzzy_and_fulfillment** (V1):
```typeql
fun tactic_rule_impacts_fuzzy_and_fulfillment($tr: tactic_rule, $e: fuzzy_and) -> double:
  match
    $e links (expression: $child_fa);
    { $child_fa isa comparison_expression;
      let $m_cmp_fa = tactic_rule_impacts_comparison_fulfillment($tr, $child_fa);
      let $m_fa = $m_cmp_fa; } or
    { $child_fa isa relaxed_fuzzy_expression;
      let $m_rf_fa = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $child_fa);
      let $m_fa = $m_rf_fa; } or
    { $child_fa isa logical_expression;
      not { $child_fa isa comparison_expression; };
      let $m_log_fa = logical_expression_membership($child_fa);
      let $m_fa = $m_log_fa; } or
    { $child_fa isa fuzzy_not;
      let $m_fn_fa = tactic_rule_impacts_fuzzy_not_membership($tr, $child_fa);
      let $m_fa = $m_fn_fa; } or
    { $child_fa isa not_expression;
      let $m_not_fa = tactic_rule_impacts_not_membership($tr, $child_fa);
      let $m_fa = $m_not_fa; } or
    { $child_fa isa fuzzy_comparison_expression;
      let $m_leaf_fa = tactic_rule_impacts_fuzzy_leaf_fulfillment($tr, $child_fa);
      let $m_fa = $m_leaf_fa; };
  return min($m_fa);
```

**tactic_rule_impacts_may_fulfillment** (V1):
```typeql
fun tactic_rule_impacts_may_fulfillment($tr: tactic_rule, $e: may_expression) -> double:
  match
    $e links (expression: $may_m);
    { $may_m isa relaxed_fuzzy_expression;
      let $may_rf = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $may_m);
      let $may_val = $may_rf; } or
    { $may_m isa fuzzy_or;
      let $may_or = tactic_rule_impacts_fuzzy_or_fulfillment($tr, $may_m);
      let $may_val = $may_or; } or
    { $may_m isa fuzzy_and;
      let $may_and = tactic_rule_impacts_fuzzy_and_fulfillment($tr, $may_m);
      let $may_val = $may_and; } or
    { $may_m isa fuzzy_not;
      let $may_not = tactic_rule_impacts_fuzzy_not_membership($tr, $may_m);
      let $may_val = $may_not; } or
    { $may_m isa comparison_expression;
      let $may_cmp = tactic_rule_impacts_comparison_fulfillment($tr, $may_m);
      let $may_val = $may_cmp; } or
    { $may_m isa logical_expression;
      not { $may_m isa comparison_expression; };
      let $may_log = logical_expression_membership($may_m);
      let $may_val = $may_log; };
  return max($may_val);
```

**tactic_rule_impacts_shall_fulfillment** (V1):
```typeql
fun tactic_rule_impacts_shall_fulfillment($tr: tactic_rule, $e: shall_expression) -> double:
  match
    $e links (expression: $shall_m);
    { $shall_m isa relaxed_fuzzy_expression;
      let $sh_rf = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $shall_m);
      let $sh_val = $sh_rf; } or
    { $shall_m isa fuzzy_or;
      let $sh_or = tactic_rule_impacts_fuzzy_or_fulfillment($tr, $shall_m);
      let $sh_val = $sh_or; } or
    { $shall_m isa fuzzy_and;
      let $sh_and = tactic_rule_impacts_fuzzy_and_fulfillment($tr, $shall_m);
      let $sh_val = $sh_and; } or
    { $shall_m isa fuzzy_not;
      let $sh_not = tactic_rule_impacts_fuzzy_not_membership($tr, $shall_m);
      let $sh_val = $sh_not; } or
    { $shall_m isa may_expression;
      let $sh_may = tactic_rule_impacts_may_fulfillment($tr, $shall_m);
      let $sh_val = $sh_may; } or
    { $shall_m isa comparison_expression;
      let $sh_cmp = tactic_rule_impacts_comparison_fulfillment($tr, $shall_m);
      let $sh_val = $sh_cmp; } or
    { $shall_m isa logical_expression;
      not { $shall_m isa comparison_expression; };
      let $sh_log = logical_expression_membership($shall_m);
      let $sh_val = $sh_log; };
  return min($sh_val);
```

**tactic_rule_impacts_any_expression_fulfillment** (V1):
```typeql
fun tactic_rule_impacts_any_expression_fulfillment($tr: tactic_rule, $e: expression) -> double:
  match
    { $e isa relaxed_fuzzy_expression;
      let $m_ae_rf = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $e);
      let $m_ae = $m_ae_rf; } or
    { $e isa fuzzy_comparison_expression;
      let $m_ae_f = tactic_rule_impacts_fuzzy_leaf_fulfillment($tr, $e);
      let $m_ae = $m_ae_f; } or
    { $e isa comparison_expression;
      let $m_ae_cmp = tactic_rule_impacts_comparison_fulfillment($tr, $e);
      let $m_ae = $m_ae_cmp; } or
    { $e isa shall_expression;
      let $m_ae_shall = tactic_rule_impacts_shall_fulfillment($tr, $e);
      let $m_ae = $m_ae_shall; } or
    { $e isa fuzzy_or;
      let $m_ae_fo = tactic_rule_impacts_fuzzy_or_fulfillment($tr, $e);
      let $m_ae = $m_ae_fo; } or
    { $e isa fuzzy_and;
      let $m_ae_fa = tactic_rule_impacts_fuzzy_and_fulfillment($tr, $e);
      let $m_ae = $m_ae_fa; } or
    { $e isa may_expression;
      let $m_ae_may = tactic_rule_impacts_may_fulfillment($tr, $e);
      let $m_ae = $m_ae_may; } or
    { $e isa not_expression;
      let $m_ae_not = tactic_rule_impacts_not_membership($tr, $e);
      let $m_ae = $m_ae_not; } or
    { $e isa fuzzy_not;
      let $m_ae_fn = tactic_rule_impacts_fuzzy_not_membership($tr, $e);
      let $m_ae = $m_ae_fn; } or
    { $e isa logical_expression;
      not { $e isa comparison_expression; };
      not { $e isa not_expression; };
      let $m_ae_log = logical_expression_membership($e);
      let $m_ae = $m_ae_log; };
  return first $m_ae;
```

---

## Full Benchmark Results

### V0 (Baseline)

| Function | cold_avg | warm_p50 | rows |
|---|---|---|---|
| `tactic_rule_impacts_requirement_fulfillment` | 11824ms | 14412ms* | 260 |
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

*First V0 run showed 14412ms warm_p50 for requirement_fulfillment; subsequent runs stabilized at ~11946ms (JIT warm-up variation).

### V1 Combined (Most-Frequent-First)

| Function | cold_avg | warm_p50 | rows | vs V0 |
|---|---|---|---|---|
| `tactic_rule_impacts_requirement_fulfillment` | 11121ms | 12072ms | 260 | -15% cold, +1% warm |
| `tactic_rule_impacts_any_expression_fulfillment` | 1928ms | 1646ms | 1360 | +18% cold, +3% warm |
| `tactic_rule_impacts_shall_fulfillment` | 634ms | 599ms | 120 | +25% cold, +26% warm |
| `tactic_rule_impacts_may_fulfillment` | 290ms | 253ms | 60 | +24% cold, +22% warm |
| `tactic_rule_impacts_fuzzy_or_fulfillment` | 223ms | 195ms | 80 | +23% cold, +26% warm |
| `tactic_rule_impacts_fuzzy_and_fulfillment` | 181ms | 149ms | 60 | +24% cold, +25% warm |
| `tactic_rule_impacts_comparison_fulfillment` | 116ms | 100ms | 340 | +15% cold, +12% warm |
| `tactic_rule_impacts_relaxed_leaf_fulfillment` | 90ms | 76ms | 220 | +14% cold, +13% warm |
| `tactic_rule_impacts_fuzzy_leaf_fulfillment` | 89ms | 76ms | 280 | +13% cold, +15% warm |
| `tactic_rule_impacts_not_membership` | 77ms | 48ms | 60 | +17% cold, +24% warm |
| `tactic_rule_impacts_fuzzy_not_membership` | 79ms | 47ms | 80 | +16% cold, +22% warm |

---

## Key Conclusion

**V0 wins for all 11 functions.** The "most-frequent-first" heuristic, which yielded −37% all-rules gain for `tactic_rule_hypothetical_measure_value`, does NOT apply to `tactic_rule_impacts_*` functions. The fundamental difference:

- `measure_value` is a **single-dispatch** function: it finds ONE matching branch, computes a scalar, returns it. Most-common-first enables early-exit.
- `impacts_*` functions are **aggregators**: they compute `min`/`max` across ALL matching children. ALL branches are always evaluated. Branch order affects query plan generation, not computation shortcutting.

For aggregate functions, the original TypeDB-generated or manually-tuned ordering appears plan-optimal.
