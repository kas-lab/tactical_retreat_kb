# Baseline

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a); $eff_a links (measure: $m);
      $eff_a isa relative_effect;
      $eff_a links (effect_value: $del_a);
      (measure: $m, measurement_value: $cur_a) isa measurement, has latest true;
      $cur_a has double_value $cur_d_a; $del_a has double_value $del_d_a;
      let $v = $cur_d_a + $del_d_a;
    } or {
      $tr links (effect: $eff_b); $eff_b links (measure: $m);
      $eff_b isa absolute_effect; $eff_b links (effect_value: $abs_ev_d);
      $abs_ev_d has double_value $abs_d_raw; let $v = $abs_d_raw;
    } or {
      $tr links (effect: $eff_bi); $eff_bi links (measure: $m);
      $eff_bi isa absolute_effect; $eff_bi links (effect_value: $abs_ev_i);
      $abs_ev_i has integer_value $abs_i_raw; let $v = $abs_i_raw + 0.0;
    } or {
      not { $tr links (effect: $eff_c); $eff_c links (measure: $m); };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not { $tr links (effect: $eff_ci); $eff_ci links (measure: $m); };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 1

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a links (measure: $m, effect_value: $rel_effect_value_ent), isa relative_effect;
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr links (effect: $eff_b); $eff_b links (measure: $m);
      $eff_b isa absolute_effect; $eff_b links (effect_value: $abs_ev_d);
      $abs_ev_d has double_value $abs_d_raw; let $v = $abs_d_raw;
    } or {
      $tr links (effect: $eff_bi); $eff_bi links (measure: $m);
      $eff_bi isa absolute_effect; $eff_bi links (effect_value: $abs_ev_i);
      $abs_ev_i has integer_value $abs_i_raw; let $v = $abs_i_raw + 0.0;
    } or {
      not { $tr links (effect: $eff_c); $eff_c links (measure: $m); };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not { $tr links (effect: $eff_ci); $eff_ci links (measure: $m); };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 2

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a links (measure: $m, effect_value: $rel_effect_value_ent), isa relative_effect;
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr links (effect: $eff_b);

      $eff_b links (measure: $m, effect_value: $abs_ev_d), isa absolute_effect;
      $abs_ev_d has double_value $abs_d_raw;

      let $v = $abs_d_raw;
    } or {
      $tr links (effect: $eff_bi); $eff_bi links (measure: $m);
      $eff_bi isa absolute_effect; $eff_bi links (effect_value: $abs_ev_i);
      $abs_ev_i has integer_value $abs_i_raw; let $v = $abs_i_raw + 0.0;
    } or {
      not { $tr links (effect: $eff_c); $eff_c links (measure: $m); };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not { $tr links (effect: $eff_ci); $eff_ci links (measure: $m); };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 3

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a links (measure: $m, effect_value: $rel_effect_value_ent), isa relative_effect;
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr links (effect: $eff_b);

      $eff_b links (measure: $m, effect_value: $abs_ev_d), isa absolute_effect;
      $abs_ev_d has double_value $abs_d_raw;

      let $v = $abs_d_raw + 0.0;
    } or {
      $tr links (effect: $eff_bi);
      $eff_bi links (measure: $m, effect_value: $abs_ev_i), isa absolute_effect;
      $abs_ev_i has integer_value $abs_i_raw;
      let $v = $abs_i_raw + 0.0;
    } or {
      not {
        $tr links (effect: $eff_c);
        $eff_c links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not {
        $tr links (effect: $eff_ci);
        $eff_ci links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 4

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr links (effect: $eff_b);

      $eff_b isa absolute_effect, links (measure: $m, effect_value: $abs_ev_d);
      $abs_ev_d has double_value $abs_d_raw;

      let $v = $abs_d_raw + 0.0;
    } or {
      $tr links (effect: $eff_bi);
      $eff_bi isa absolute_effect, links (measure: $m, effect_value: $abs_ev_i);
      $abs_ev_i has integer_value $abs_i_raw;
      let $v = $abs_i_raw + 0.0;
    } or {
      not {
        $tr links (effect: $eff_c);
        $eff_c links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not {
        $tr links (effect: $eff_ci);
        $eff_ci links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 5

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
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
    }  or {
      not {
        $tr links (effect: $eff_c);
        $eff_c links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not {
        $tr links (effect: $eff_ci);
        $eff_ci links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 6

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $effect);

      {
        $effect isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
        $rel_effect_value_ent has double_value $rel_effect_value_double;
        (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
        $current_measurement has double_value $current_measurement_value;

        let $v = $current_measurement_value + $rel_effect_value_double;
      } or {
        $effect isa absolute_effect, links (measure: $m, effect_value: $effect_value_ent);
        {
          $effect_value_ent has double_value $abs_d_raw;
          let $v = $abs_d_raw;
        } or {
          $effect_value_ent has integer_value $abs_i_raw;
          let $v = $abs_i_raw + 0.0;
        };
      };
    } or {
      not {
        $tr links (effect: $eff_c);
        $eff_c links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_d) isa measurement, has latest true;
      $mv_d has double_value $vd_raw; let $v = $vd_raw;
    } or {
      not {
        $tr links (effect: $eff_ci);
        $eff_ci links (measure: $m);
      };
      (measure: $m, measurement_value: $mv_i) isa measurement, has latest true;
      $mv_i has integer_value $vi_raw; let $v = $vi_raw + 0.0;
    };
  return first $v;
```

# Variant 7

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
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
    }  or {
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

# Variant 8

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match

    {
      $tr isa tactic_rule, links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr isa tactic_rule, links (effect: $effect_absolute);
      $effect_absolute isa absolute_effect, links (measure: $m, effect_value: $effect_value_ent);
      {
        $effect_value_ent has double_value $abs_d_raw;
        let $v = $abs_d_raw;
      } or {
        $effect_value_ent has integer_value $abs_i_raw;
        let $v = $abs_i_raw + 0.0;
      };
    }  or {
      not {
        $tr isa tactic_rule, links (effect: $eff_c);
        $eff_c isa effect, links (measure: $m);
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

# Variant 9

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    $m isa Measure;
    {
      $tr isa tactic_rule, links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
      $rel_effect_value_ent has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr isa tactic_rule, links (effect: $effect_absolute);
      $effect_absolute isa absolute_effect, links (measure: $m, effect_value: $effect_value_ent);
      {
        $effect_value_ent has double_value $abs_d_raw;
        let $v = $abs_d_raw;
      } or {
        $effect_value_ent has integer_value $abs_i_raw;
        let $v = $abs_i_raw + 0.0;
      };
    }  or {
      not {
        $tr isa tactic_rule, links (effect: $eff_c);
        $eff_c isa effect, links (measure: $m);
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

# Variant 10

```
fun tactic_rule_hypothetical_measure_value($tr: tactic_rule, $m: Measure) -> double:
  match
    {
      $tr isa tactic_rule, links (effect: $eff_a);
      $eff_a isa relative_effect, links (measure: $m, effect_value: $rel_effect_value_ent);
      $rel_effect_value_ent isa ValueSingleton, has double_value $rel_effect_value_double;
      (measure: $m, measurement_value: $current_measurement) isa measurement, has latest true;
      $current_measurement isa ValueSingleton, has double_value $current_measurement_value;

      let $v = $current_measurement_value + $rel_effect_value_double;
    } or {
      $tr isa tactic_rule, links (effect: $effect_absolute);
      $effect_absolute isa absolute_effect, links (measure: $m, effect_value: $effect_value_ent);
      {
        $effect_value_ent isa ValueSingleton, has double_value $abs_d_raw;
        let $v = $abs_d_raw;
      } or {
        $effect_value_ent isa ValueSingleton, has integer_value $abs_i_raw;
        let $v = $abs_i_raw + 0.0;
      };
    }  or {
      not {
        $tr isa tactic_rule, links (effect: $eff_c);
        $eff_c isa effect, links (measure: $m);
      };

      (measure: $m, measurement_value: $measurement_value) isa measurement, has latest true;

      {
        $measurement_value isa ValueSingleton, has double_value $value_double;
        let $v = $value_double;
      } or {
        $measurement_value isa ValueSingleton, has integer_value $value_int;
        let $v = $value_int + 0.0;
      };
    };
  return first $v;
```