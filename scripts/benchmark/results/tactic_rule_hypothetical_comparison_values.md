# Benchmark Results: `tactic_rule_hypothetical_comparison_lhs_value` and `tactic_rule_hypothetical_comparison_rhs_value`

## Setup

- **Schema file**: `schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql` (lines 38–72)
- **Benchmark data**: `scripts/benchmark/benchmark.tql`
- **Input mode**: all-inputs (all tactic_rules × all comparison_expressions)
- **Rows per query**: 260 (20 tactic_rules × 13 comparison_expressions)
- **Short run**: `--cold-runs 5 --warm-runs 30 --all-inputs`
- **Long run**: `--cold-runs 10 --warm-runs 100 --all-inputs`

## Phase 0.5: Data Distribution Balancing

Original benchmark data had biased distribution:
- lhs: 7/7 expressions had Measure lhs (0 ValueSingleton) — all inputs hit branch 1
- rhs: 1/7 Measure + 6/7 VS_double — limited VS_integer coverage

Added 6 new comparison expressions + 2 integer ValueSingleton entities to `benchmark.tql`:
- `$int_singleton_5` (integer_value 5), `$int_singleton_10` (integer_value 10)
- 2 VS_double lhs expressions: `expr_lhs_vs_d_1`, `expr_lhs_vs_d_2`
- 2 VS_integer lhs expressions: `expr_lhs_vs_i_1`, `expr_lhs_vs_i_2`
- 2 VS_integer rhs expressions: `expr_rhs_vs_i_1`, `expr_rhs_vs_i_2`

**Final distribution (13 expressions):**
- lhs: 9/13 Measure (69%), 2/13 VS_double (15%), 2/13 VS_integer (15%)
- rhs: 3/13 Measure (23%), 8/13 VS_double (62%), 2/13 VS_integer (15%)

## V1 Finding: [CEX18] Compile Error

Attempting to eliminate the double-`let` pattern in the Measure branch:
```typeql
# Attempted (V1):
$lhs_term isa Measure;
let $v_cmp_lhs = tactic_rule_hypothetical_measure_value($tr, $lhs_term);
```
TypeDB raises `[CEX18] The variable 'v_cmp_lhs' cannot be assigned to, as it was already assigned in a previous stage.`

**Finding**: When a function-call return is bound directly to a cross-OR-branch variable, TypeDB 3 treats the function invocation as a "stage" and considers the variable already assigned. The double-`let` pattern (intermediate variable + alias) is required.

## Short Benchmark Results (5 cold / 30 warm)

### V0 — Baseline

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=48.337ms, cold_p50=48.755ms, cold_p95=48.968ms
  warm_avg=38.228ms, warm_p50=38.195ms, warm_p95=38.728ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=32.131ms, cold_p50=31.878ms, cold_p95=33.645ms
  warm_avg=21.345ms, warm_p50=21.280ms, warm_p95=21.716ms, rows=260
```

### V1 — Eliminate intermediate `let` in Measure branch

```
[CEX18] compile error — not runnable
```

### V2 — Merge ValueSingleton branches (nested OR)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=48.184ms, cold_p50=48.206ms, cold_p95=48.794ms
  warm_avg=37.679ms, warm_p50=37.793ms, warm_p95=38.142ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=33.362ms, cold_p50=33.451ms, cold_p95=33.589ms
  warm_avg=22.900ms, warm_p50=22.805ms, warm_p95=23.672ms, rows=260
```

### V3 — V1 + V2 combined

```
Not achievable — depends on V1 which triggers [CEX18]
```

### V4 — No hoisting (links inside each branch, unique var names)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=49.465ms, cold_p50=49.151ms, cold_p95=50.928ms
  warm_avg=39.048ms, warm_p50=39.113ms, warm_p95=39.408ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=34.290ms, cold_p50=34.190ms, cold_p95=34.980ms
  warm_avg=23.734ms, warm_p50=23.689ms, warm_p95=24.689ms, rows=260
```

### V5 — `isa!` exact-type + merged VS branches, Measure-first

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=48.613ms, cold_p50=48.767ms, cold_p95=49.555ms
  warm_avg=37.407ms, warm_p50=37.201ms, warm_p95=38.261ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=33.598ms, cold_p50=33.371ms, cold_p95=35.128ms
  warm_avg=23.173ms, warm_p50=23.028ms, warm_p95=24.153ms, rows=260
```

### V6 — VS-first ordering (both functions)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=49.097ms, cold_p50=48.980ms, cold_p95=50.317ms
  warm_avg=38.421ms, warm_p50=38.221ms, warm_p95=39.591ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=31.800ms, cold_p50=31.770ms, cold_p95=32.071ms
  warm_avg=20.966ms, warm_p50=20.988ms, warm_p95=21.211ms, rows=260
```

### V7 — No hoisting + merged VS, Measure-first

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=48.515ms, cold_p50=47.902ms, cold_p95=52.418ms
  warm_avg=37.470ms, warm_p50=37.484ms, warm_p95=38.099ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=31.861ms, cold_p50=31.870ms, cold_p95=32.231ms
  warm_avg=22.028ms, warm_p50=21.975ms, warm_p95=23.175ms, rows=260
```

### V8 — Asymmetric: lhs=V0, rhs=VS-first flat

```
tactic_rule_hypothetical_comparison_lhs_value (unchanged):
  cold_avg=47.689ms, cold_p50=47.463ms, cold_p95=48.542ms
  warm_avg=37.440ms, warm_p50=37.287ms, warm_p95=38.304ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value (VS-first):
  cold_avg=31.874ms, cold_p50=32.037ms, cold_p95=32.327ms
  warm_avg=21.019ms, warm_p50=20.987ms, warm_p95=21.303ms, rows=260
```

### V9 — lhs with `isa!` Measure-first, rhs VS-first flat

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=47.559ms, cold_p50=47.272ms, cold_p95=48.684ms
  warm_avg=38.217ms, warm_p50=38.215ms, warm_p95=39.054ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=32.477ms, cold_p50=32.603ms, cold_p95=32.988ms
  warm_avg=21.520ms, warm_p50=21.481ms, warm_p95=22.070ms, rows=260
```

## Phase 3: Short Run Summary Table

| Variant | Description | lhs cold_avg | lhs warm_p50 | rhs cold_avg | rhs warm_p50 | Disq? |
|---------|-------------|-------------|-------------|-------------|-------------|-------|
| V0 | baseline (Measure-first, flat, hoisted) | 48.337 | 38.195 | 32.131 | 21.280 | |
| V1 | remove double-let | [CEX18] | — | [CEX18] | — | compile error |
| V2 | merged VS branches | 48.184 | 37.793 | 33.362 | 22.805 | |
| V3 | V1+V2 | not achievable | — | not achievable | — | compile error |
| V4 | no hoisting, flat | 49.465 | 39.113 | 34.290 | 23.689 | |
| V5 | isa! + merged VS, Measure-first | 48.613 | 37.201 | 33.598 | 23.028 | |
| V6 | VS-first, flat (both) | 49.097 | 38.221 | 31.800 | **20.988** | |
| V7 | no hoisting + merged VS | 48.515 | 37.484 | 31.861 | 21.975 | |
| V8 | lhs=V0, rhs=VS-first | 47.689 | 37.287* | 31.874 | **20.987** | |
| V9 | lhs=isa! Measure-first, rhs=VS-first | 47.559 | 38.215 | 32.477 | 21.481 | |

*V8 lhs is structurally identical to V0; warm_p50 difference is run-to-run noise (~1ms).

**avg_cold (lhs)**: 48.432ms → threshold 55.7ms — no disqualifications
**avg_cold (rhs)**: 32.674ms → threshold 37.6ms — no disqualifications

**Top 3 by combined warm_p50 (sum lhs+rhs):**
1. V8: 37.287+20.987 = 58.274ms (but lhs unchanged, so effectively rhs-only improvement)
2. V6: 38.221+20.988 = 59.209ms (rhs improvement offset by lhs regression)
3. V5: 37.201+23.028 = 60.229ms (lhs improvement, rhs regression)

## Phase 3: Long Benchmark Results (10 cold / 100 warm)

### V0 — Baseline (long)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=47.923ms, cold_p50=47.696ms, cold_p95=48.737ms
  warm_avg=37.104ms, warm_p50=36.897ms, warm_p95=38.281ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=31.852ms, cold_p50=31.784ms, cold_p95=32.457ms
  warm_avg=21.486ms, warm_p50=21.385ms, warm_p95=22.090ms, rows=260
```

### V6 — VS-first (both) (long)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=47.950ms, cold_p50=48.007ms, cold_p95=49.121ms
  warm_avg=38.443ms, warm_p50=38.305ms, warm_p95=39.552ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=31.699ms, cold_p50=31.744ms, cold_p95=32.043ms
  warm_avg=21.238ms, warm_p50=21.121ms, warm_p95=22.290ms, rows=260
```

### V8 — lhs=V0, rhs=VS-first (long)

```
tactic_rule_hypothetical_comparison_lhs_value (unchanged):
  cold_avg=47.728ms, cold_p50=47.379ms, cold_p95=48.761ms
  warm_avg=37.804ms, warm_p50=37.573ms, warm_p95=38.703ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value (VS-first):
  cold_avg=31.947ms, cold_p50=31.617ms, cold_p95=32.971ms
  warm_avg=21.287ms, warm_p50=21.290ms, warm_p95=22.136ms, rows=260
```

### V5 — isa! + merged VS (long)

```
tactic_rule_hypothetical_comparison_lhs_value:
  cold_avg=48.585ms, cold_p50=48.322ms, cold_p95=51.172ms
  warm_avg=38.262ms, warm_p50=38.217ms, warm_p95=38.856ms, rows=260

tactic_rule_hypothetical_comparison_rhs_value:
  cold_avg=33.557ms, cold_p50=33.506ms, cold_p95=34.572ms
  warm_avg=22.804ms, warm_p50=22.713ms, warm_p95=23.314ms, rows=260
```

## Long Run Summary Table

| Variant | lhs warm_p50 | rhs warm_p50 | combined | vs V0 combined |
|---------|-------------|-------------|---------|----------------|
| **V0** | **36.897** | 21.385 | **58.282** | — |
| V6 | 38.305 | **21.121** | 59.426 | +1.144ms (worse) |
| V8 | 37.573 | 21.290 | 58.863 | +0.581ms (worse) |
| V5 | 38.217 | 22.713 | 60.930 | +2.648ms (worse) |

## Winner: V0 (Baseline)

**V0 is the winner. No variant yields a reliable improvement.**

Key findings:
1. **[CEX18] constraint** (new finding): A function-call return cannot be bound directly to a cross-OR-branch variable. The double-`let` pattern (`let $tmp = func(...); let $out = $tmp;`) is required. This eliminates V1 and V3.
2. **VS-first for rhs** (V6/V8) gives a small but consistent rhs improvement (~0.26ms, ~1.2%) in both short and long runs. However, this comes with an lhs regression in long runs (~1.4ms for V6 where lhs is also VS-first). V8 isolates the rhs change, but the rhs-only improvement (~0.09ms in long run) is within measurement noise.
3. **No-hoisting** (V4, V7) is consistently slower — the hoisted `links` before the OR block is beneficial.
4. **Merged VS branches** (V2) adds overhead rather than saving it — flat 3-branch structure is faster.
5. **`isa!` exact-type** (V5) degrades performance, likely due to different TypeDB 3 type-dispatch path.
6. **Noise floor**: ~1ms run-to-run variability for lhs (38ms function), ~0.5ms for rhs (21ms function). The short-run winner (V5 lhs=37.201ms) reversed in the long run (38.217ms), highlighting that short runs can mislead.

## Conclusion

V0 (baseline) retained. The functions' bottleneck is the `tactic_rule_hypothetical_measure_value` sub-call for Measure inputs — no structural reorganization of the dispatch branches can avoid that cost.
