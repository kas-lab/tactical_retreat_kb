# Variants: `tactic_rule_hypothetical_comparison_lhs_value` and `tactic_rule_hypothetical_comparison_rhs_value`

Full TypeQL bodies for each variant tested. Both functions are always modified together (same variant index = same structural change).

---

## V0 — Baseline (unchanged)

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (lhs_value: $lhs_term);
    {
      $lhs_term isa Measure;
      let $lhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
      let $v_cmp_lhs = $lhs_measure_value;
    } or {
      $lhs_term isa ValueSingleton;
      $lhs_term has double_value $lhs_d;
      let $v_cmp_lhs = $lhs_d;
    } or {
      $lhs_term isa ValueSingleton;
      $lhs_term has integer_value $lhs_i;
      let $v_cmp_lhs = $lhs_i + 0.0;
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    } or {
      $rhs_term isa ValueSingleton;
      $rhs_term has double_value $rhs_d;
      let $v_cmp_rhs = $rhs_d;
    } or {
      $rhs_term isa ValueSingleton;
      $rhs_term has integer_value $rhs_i;
      let $v_cmp_rhs = $rhs_i + 0.0;
    };
  return first $v_cmp_rhs;
```

---

## V1 — Eliminate intermediate `let` in Measure branch

**Status: [CEX18] compile error — not achievable**

Attempted to inline the function-call result directly to the cross-branch variable:
```typeql
# This triggers [CEX18]:
$lhs_term isa Measure;
let $v_cmp_lhs = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
```
TypeDB 3 error: `[CEX18] The variable 'v_cmp_lhs' cannot be assigned to, as it was already assigned in a previous stage.`

The double-`let` pattern is required when a function-call result needs to be aliased into a cross-OR-branch output variable.

---

## V2 — Merge ValueSingleton branches (nested OR)

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (lhs_value: $lhs_term);
    {
      $lhs_term isa Measure;
      let $lhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
      let $v_cmp_lhs = $lhs_measure_value;
    } or {
      $lhs_term isa ValueSingleton;
      {
        $lhs_term has double_value $lhs_d;
        let $v_cmp_lhs = $lhs_d;
      } or {
        $lhs_term has integer_value $lhs_i;
        let $v_cmp_lhs = $lhs_i + 0.0;
      };
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    } or {
      $rhs_term isa ValueSingleton;
      {
        $rhs_term has double_value $rhs_d;
        let $v_cmp_rhs = $rhs_d;
      } or {
        $rhs_term has integer_value $rhs_i;
        let $v_cmp_rhs = $rhs_i + 0.0;
      };
    };
  return first $v_cmp_rhs;
```

---

## V3 — V1 + V2 combined

**Status: Not achievable — depends on V1 which triggers [CEX18]**

---

## V4 — No hoisting (links inside each branch, unique variable names)

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    {
      $e links (lhs_value: $lhs_term_m);
      $lhs_term_m isa Measure;
      let $lhs_measure_value_m = tactic_rule_hypothetical_measure_value($tr, $lhs_term_m);
      let $v_cmp_lhs = $lhs_measure_value_m;
    } or {
      $e links (lhs_value: $lhs_term_d);
      $lhs_term_d isa ValueSingleton;
      $lhs_term_d has double_value $lhs_d;
      let $v_cmp_lhs = $lhs_d;
    } or {
      $e links (lhs_value: $lhs_term_i);
      $lhs_term_i isa ValueSingleton;
      $lhs_term_i has integer_value $lhs_i;
      let $v_cmp_lhs = $lhs_i + 0.0;
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    {
      $e links (rhs_value: $rhs_term_m);
      $rhs_term_m isa Measure;
      let $rhs_measure_value_m = tactic_rule_hypothetical_measure_value($tr, $rhs_term_m);
      let $v_cmp_rhs = $rhs_measure_value_m;
    } or {
      $e links (rhs_value: $rhs_term_d);
      $rhs_term_d isa ValueSingleton;
      $rhs_term_d has double_value $rhs_d;
      let $v_cmp_rhs = $rhs_d;
    } or {
      $e links (rhs_value: $rhs_term_i);
      $rhs_term_i isa ValueSingleton;
      $rhs_term_i has integer_value $rhs_i;
      let $v_cmp_rhs = $rhs_i + 0.0;
    };
  return first $v_cmp_rhs;
```

---

## V5 — `isa!` exact-type dispatch + merged VS branches, Measure-first

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (lhs_value: $lhs_term);
    {
      $lhs_term isa! Measure;
      let $lhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
      let $v_cmp_lhs = $lhs_measure_value;
    } or {
      $lhs_term isa! ValueSingleton;
      {
        $lhs_term has double_value $lhs_d;
        let $v_cmp_lhs = $lhs_d;
      } or {
        $lhs_term has integer_value $lhs_i;
        let $v_cmp_lhs = $lhs_i + 0.0;
      };
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa! Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    } or {
      $rhs_term isa! ValueSingleton;
      {
        $rhs_term has double_value $rhs_d;
        let $v_cmp_rhs = $rhs_d;
      } or {
        $rhs_term has integer_value $rhs_i;
        let $v_cmp_rhs = $rhs_i + 0.0;
      };
    };
  return first $v_cmp_rhs;
```

---

## V6 — VS-first ordering (both functions)

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (lhs_value: $lhs_term);
    {
      $lhs_term isa ValueSingleton;
      $lhs_term has double_value $lhs_d;
      let $v_cmp_lhs = $lhs_d;
    } or {
      $lhs_term isa ValueSingleton;
      $lhs_term has integer_value $lhs_i;
      let $v_cmp_lhs = $lhs_i + 0.0;
    } or {
      $lhs_term isa Measure;
      let $lhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
      let $v_cmp_lhs = $lhs_measure_value;
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa ValueSingleton;
      $rhs_term has double_value $rhs_d;
      let $v_cmp_rhs = $rhs_d;
    } or {
      $rhs_term isa ValueSingleton;
      $rhs_term has integer_value $rhs_i;
      let $v_cmp_rhs = $rhs_i + 0.0;
    } or {
      $rhs_term isa Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    };
  return first $v_cmp_rhs;
```

---

## V7 — No hoisting + merged VS branches, Measure-first

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    {
      $e links (lhs_value: $lhs_term_m);
      $lhs_term_m isa Measure;
      let $lhs_measure_value_m = tactic_rule_hypothetical_measure_value($tr, $lhs_term_m);
      let $v_cmp_lhs = $lhs_measure_value_m;
    } or {
      $e links (lhs_value: $lhs_term_vs);
      $lhs_term_vs isa ValueSingleton;
      {
        $lhs_term_vs has double_value $lhs_d;
        let $v_cmp_lhs = $lhs_d;
      } or {
        $lhs_term_vs has integer_value $lhs_i;
        let $v_cmp_lhs = $lhs_i + 0.0;
      };
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    {
      $e links (rhs_value: $rhs_term_m);
      $rhs_term_m isa Measure;
      let $rhs_measure_value_m = tactic_rule_hypothetical_measure_value($tr, $rhs_term_m);
      let $v_cmp_rhs = $rhs_measure_value_m;
    } or {
      $e links (rhs_value: $rhs_term_vs);
      $rhs_term_vs isa ValueSingleton;
      {
        $rhs_term_vs has double_value $rhs_d;
        let $v_cmp_rhs = $rhs_d;
      } or {
        $rhs_term_vs has integer_value $rhs_i;
        let $v_cmp_rhs = $rhs_i + 0.0;
      };
    };
  return first $v_cmp_rhs;
```

---

## V8 — Asymmetric: lhs=V0 (unchanged), rhs=VS-first flat

lhs function is identical to V0.

```typeql
fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa ValueSingleton;
      $rhs_term has double_value $rhs_d;
      let $v_cmp_rhs = $rhs_d;
    } or {
      $rhs_term isa ValueSingleton;
      $rhs_term has integer_value $rhs_i;
      let $v_cmp_rhs = $rhs_i + 0.0;
    } or {
      $rhs_term isa Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    };
  return first $v_cmp_rhs;
```

---

## V9 — lhs with `isa!` Measure-first (flat), rhs=VS-first flat

```typeql
fun tactic_rule_hypothetical_comparison_lhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (lhs_value: $lhs_term);
    {
      $lhs_term isa! Measure;
      let $lhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
      let $v_cmp_lhs = $lhs_measure_value;
    } or {
      $lhs_term isa ValueSingleton;
      $lhs_term has double_value $lhs_d;
      let $v_cmp_lhs = $lhs_d;
    } or {
      $lhs_term isa ValueSingleton;
      $lhs_term has integer_value $lhs_i;
      let $v_cmp_lhs = $lhs_i + 0.0;
    };
  return first $v_cmp_lhs;

fun tactic_rule_hypothetical_comparison_rhs_value($tr: tactic_rule, $e: comparison_expression) -> double:
  match
    $e links (rhs_value: $rhs_term);
    {
      $rhs_term isa ValueSingleton;
      $rhs_term has double_value $rhs_d;
      let $v_cmp_rhs = $rhs_d;
    } or {
      $rhs_term isa ValueSingleton;
      $rhs_term has integer_value $rhs_i;
      let $v_cmp_rhs = $rhs_i + 0.0;
    } or {
      $rhs_term isa Measure;
      let $rhs_measure_value = tactic_rule_hypothetical_measure_value($tr, $rhs_term);
      let $v_cmp_rhs = $rhs_measure_value;
    };
  return first $v_cmp_rhs;
```
