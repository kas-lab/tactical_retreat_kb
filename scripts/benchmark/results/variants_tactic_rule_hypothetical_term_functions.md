# Variant bodies: tactic_rule_hypothetical_term functions

Full TypeQL function bodies for V0–V6 of the benchmark campaign.
See `tactic_rule_hypothetical_term_functions.md` for results and winner justification.

---

## V0 — Baseline (current schema)

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    } or{
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    };
    {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    } or {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    };
  return first $q_hft;
```

---

## V1 — Stage 2 "best-guess" reorder

Stage 2 relaxed: required_value first, neither second (NOT-based), required_period last.
Stage 2 fuzzy: no-offset (NOT-based) first.

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```

---

## V2 — "Neither-first" for relaxed + no-offset-first for fuzzy

Stage 2 relaxed: NOT-based "neither" branch first.
Stage 2 fuzzy: same as V1 (no-offset first).

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    };
    {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```

---

## V3 — Stage 1 VS-first + V1 stage 2

Stage 1: VS_double first, VS_integer second, Measure last (both functions).
Stage 2: V1 ordering.

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa ValueSingleton;
      $term_rt has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    } or {
      $term_rt isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa ValueSingleton;
      $term_ft has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    } or {
      $term_ft isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```

---

## V4 — No hoisting + V1 stage 2

`$e links (term: $term)` moved inside each branch with unique variable names per branch.

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    {
      $e links (term: $term_rt_m);
      $term_rt_m isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt_m);
      let $raw_rt = $measure_value_rt;
    } or {
      $e links (term: $term_rt_d);
      $term_rt_d isa ValueSingleton;
      $term_rt_d has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $e links (term: $term_rt_i);
      $term_rt_i isa ValueSingleton;
      $term_rt_i has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    {
      $e links (term: $term_ft_m);
      $term_ft_m isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft_m);
      let $raw_ft = $measure_value_ft;
    } or {
      $e links (term: $term_ft_d);
      $term_ft_d isa ValueSingleton;
      $term_ft_d has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $e links (term: $term_ft_i);
      $term_ft_i isa ValueSingleton;
      $term_ft_i has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```

---

## V5 — `isa!` on Measure branch + V1 stage 2

Exact-type dispatch on Measure in stage 1.

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa! Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has double_value $vs_d_rt;
      let $raw_rt = $vs_d_rt;
    } or {
      $term_rt isa ValueSingleton;
      $term_rt has integer_value $vs_i_rt;
      let $raw_rt = $vs_i_rt + 0.0;
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa! Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has double_value $vs_d_ft;
      let $raw_ft = $vs_d_ft;
    } or {
      $term_ft isa ValueSingleton;
      $term_ft has integer_value $vs_i_ft;
      let $raw_ft = $vs_i_ft + 0.0;
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```

---

## V6 — V1 stage 2 + merged VS branches in stage 1

Two flat VS branches replaced by one `isa ValueSingleton` + inner OR.

```typeql
fun tactic_rule_hypothetical_relaxed_term($tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:
  match
    $e links (term: $term_rt);
    {
      $term_rt isa Measure;
      let $measure_value_rt = tactic_rule_hypothetical_measure_value($tr, $term_rt);
      let $raw_rt = $measure_value_rt;
    } or {
      $term_rt isa ValueSingleton;
      { $term_rt has double_value $vs_d_rt; let $raw_rt = $vs_d_rt; } or
      { $term_rt has integer_value $vs_i_rt; let $raw_rt = $vs_i_rt + 0.0; };
    };
    {
      $e has required_value $rv_rt;
      let $q_hrt = $raw_rt - $rv_rt;
    } or {
      not { $e has required_value $_; };
      not { $e has required_period $_; };
      let $q_hrt = $raw_rt;
    } or {
      $e has required_period $rp_rt;
      let $q_hrt = $raw_rt - $rp_rt;
    };
  return first $q_hrt;

fun tactic_rule_hypothetical_fuzzy_term($tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:
  match
    $e links (term: $term_ft);
    {
      $term_ft isa Measure;
      let $measure_value_ft = tactic_rule_hypothetical_measure_value($tr, $term_ft);
      let $raw_ft = $measure_value_ft;
    } or {
      $term_ft isa ValueSingleton;
      { $term_ft has double_value $vs_d_ft; let $raw_ft = $vs_d_ft; } or
      { $term_ft has integer_value $vs_i_ft; let $raw_ft = $vs_i_ft + 0.0; };
    };
    {
      not { $e has offset_value $_; };
      let $q_hft = $raw_ft;
    } or {
      $e has offset_value $off_ft;
      let $q_hft = $raw_ft + $off_ft;
    };
  return first $q_hft;
```
