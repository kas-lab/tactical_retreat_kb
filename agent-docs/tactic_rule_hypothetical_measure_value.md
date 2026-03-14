# tactic_rule_hypothetical_measure_value — Phase 5 Benchmark Results

## Definitive Benchmark (100 warm runs, 15 cold runs)

| Variant | cold_avg (ms) | warm_avg (ms) | warm_p50 (ms) | rows | Notes |
|---------|--------------|--------------|--------------|------|-------|
| V7      | 10.043       | 0.770        | 0.733        | 1    | Baseline (current schema state) |
| V16     |  9.339       | 0.702        | 0.704        | 1    | Branch 1 reordered: `$eff_a links (measure: $m)` first, then `isa relative_effect`, then `links (effect_value:...)`; NOT branch drops `isa effect` |
| V18     | 10.051       | 0.710        | 0.702        | 1    | Branch 3: measurement lookup hoisted before `not {}` |
| V8      | 10.262       | 0.721        | 0.699        | 1    | `$tr isa tactic_rule` added explicitly in branches 1 and 2 |
| V12     |  9.455       | 0.715        | 0.707        | 1    | Branch 1 reordered (like V16), NOT branch drops `isa effect` |

## Selection Criteria Applied

1. **avg_cold** across 5 variants = 9.830 ms; disqualification threshold (×1.10) = 10.813 ms.
2. **No variants disqualified** — all cold_avg values are below threshold.
3. **Rank by warm_avg** (ascending): V16 (0.702) > V18 (0.710) > V12 (0.715) > V8 (0.721) > V7 (0.770).
4. **Tiebreak check** between V16 and V18: warm_avg diff = 1.14% (< 2% → tiebreak applies); cold_avg diff = 7.62% (> 2%) → prefer lower cold_avg → **V16 wins** (cold_avg 9.339 vs 10.051).

## Winner: V16

**warm_avg = 0.702 ms** (vs V7 baseline 0.770 ms; **−8.8% improvement**)
**cold_avg = 9.339 ms** (vs V7 baseline 10.043 ms; **−7.0% improvement**)

### V16 body (to apply in Phase 6)

```typeql
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a links (measure: $m);
      $eff_a isa relative_effect;
      $eff_a links (effect_value: $rel_effect_value_ent);
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;
      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr links (effect: $effect_absolute);
      $effect_absolute isa absolute_effect, links (measure: $m, effect_value: $effect_value_ent);
      {
        $effect_value_ent has double_value $abs_d_raw;
        let $v = $abs_d_raw;
      } or {
        $effect_value_ent has integer_value $abs_i_raw;
        let $v = $abs_i_raw + 0.0;
      };
    } or {
      not {
        $tr links (effect: $eff_c);
        $eff_c links (measure: $m);
      };
      (measure: $m, measurement_value: $measurement_value) isa measurement, has latest true;
      {
        $measurement_value has double_value $value_double;
        let $v = $value_double;
      } or {
        $measurement_value has integer_value $value_int;
        let $v = $value_int + 0.0;
      };
    };
  return first $v;
```

### Key differences from V7 baseline

- **Branch 1**: `$eff_a links (measure: $m)` is checked first (before `isa relative_effect`), then `$eff_a links (effect_value: ...)` is a separate constraint — TypeDB can prune by measure match early.
- **Branch 3 NOT body**: drops `$eff_c isa effect` guard (redundant since `links (measure: $m)` already constrains to effect subtypes).

## Schema file state after Phase 5

`schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql` is restored to **V7** (as required). V16 will be applied in Phase 6.
