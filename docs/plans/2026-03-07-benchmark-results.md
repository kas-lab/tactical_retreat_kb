# Benchmark Results — logical_expression.tql schema functions

## Baseline
| type          | mean (ms) | stddev (ms) | n    |
|---------------|-----------|-------------|------|
| propositional | 1.945     | 0.209       | 600  |
| comparison    | 2.166     | 0.330       | 1200 |
| not           | 1.957     | 0.295       | 400  |
| or            | 2.057     | 0.154       | 400  |
| and           | 2.296     | 0.379       | 600  |

## All Variants (final benchmark run 2026-03-07)

| variant  | propositional (ms) | comparison (ms) | not (ms) | or (ms) | and (ms) |
|----------|--------------------|-----------------|----------|---------|----------|
| baseline | 2.037              | 2.239           | 1.900    | 2.059   | 2.185    |
| A        | 0.871              | 1.048           | 0.854    | 1.002   | 1.101    |
| D        | 2.005              | 2.137           | 1.981    | 2.145   | 2.343    |
| AD       | 0.868              | 1.059           | 0.864    | 1.010   | 1.127    |

n: propositional=600, comparison=1200, not=400, or=400, and=600 (same for all variants)

## Full benchmark SUMMARY output

```
=== SUMMARY ===

Variant 'baseline':
  type             mean (ms)   stddev (ms)      n
  --------------- ----------  ------------  -----
  propositional        2.037         0.257    600
  comparison           2.239         0.369   1200
  not                  1.900         0.145    400
  or                   2.059         0.181    400
  and                  2.185         0.179    600

Variant 'A':
  type             mean (ms)   stddev (ms)      n
  --------------- ----------  ------------  -----
  propositional        0.871         0.114    600
  comparison           1.048         0.115   1200
  not                  0.854         0.069    400
  or                   1.002         0.099    400
  and                  1.101         0.124    600

Variant 'D':
  type             mean (ms)   stddev (ms)      n
  --------------- ----------  ------------  -----
  propositional        2.005         0.302    600
  comparison           2.137         0.293   1200
  not                  1.981         0.284    400
  or                   2.145         0.236    400
  and                  2.343         0.396    600

Variant 'AD':
  type             mean (ms)   stddev (ms)      n
  --------------- ----------  ------------  -----
  propositional        0.868         0.097    600
  comparison           1.059         0.107   1200
  not                  0.864         0.069    400
  or                   1.010         0.124    400
  and                  1.127         0.126    600
```

## Analysis

### D vs baseline
Variant D (resolve_value helper) was not implementable in TypeDB 3.8 — it is a stub identical to the
baseline. The benchmark confirms this: D (comparison mean 2.137 ms) is within noise of baseline
(2.239 ms), with no meaningful improvement.

### A and AD
Variant AD is identical to Variant A (the resolve_value helper cannot be added; see schema comment).
The benchmark confirms this: A (comparison 1.048 ms) and AD (comparison 1.059 ms) are within 11 µs
of each other — statistical noise, not a real difference.

### Speedup: A/AD vs baseline
- comparison: 2.239 → 1.048 ms — **~2.14× faster**
- propositional: 2.037 → 0.871 ms — **~2.34× faster**
- not: 1.900 → 0.854 ms — **~2.22× faster**
- or: 2.059 → 1.002 ms — **~2.05× faster**
- and: 2.185 → 1.101 ms — **~1.98× faster**

## Winner

**Variant A** (= Variant AD).

Primary metric (comparison type mean): A/AD at ~1.05 ms vs baseline at ~2.24 ms — roughly 2× faster.
Overall mean: all five expression types are approximately halved in latency under Variant A.
Variant D provides no benefit (identical to baseline in practice).

The win comes from consolidating 6 per-operator comparison functions into a single `comparison_valid`
dispatcher, which eliminates repeated type-dispatch overhead in the TypeDB 3 function evaluator.
