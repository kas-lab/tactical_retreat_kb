# Logical Expression Function Benchmark Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Benchmark four schema variants of `logical_expression.tql` for query latency and keep the fastest.

**Architecture:** A standalone benchmark script loads each schema variant into its own TypeDB database, times `expression_valid` queries for N=200 repetitions per expression name, reports mean ± stddev per expression type, then selects the winner to overwrite `logical_expression.tql`.

**Tech Stack:** Python `time.perf_counter`, `TacticalRetreatInterface`, TypeDB 3, Docker container `tactical_retreat`.

---

## Background: What We're Testing

The current `logical_expression.tql` has these schema functions:

```
expression_valid → atomic_valid (7 OR branches: 1 propositional + 6 comparison operators)
                                → propositional_valid
                                → less_than_valid          ← these 6 each independently
                                → less_than_equal_valid       resolve lhs/rhs values via
                                → greater_than_valid          two duplicate OR branches
                                → greater_than_equal_valid    (direct has OR via measurement)
                                → equal_valid
                                → not_equal_valid
               → not_valid  → atomic_valid
               → or_valid   → atomic_valid / not_valid
               → and_valid  → atomic_valid / not_valid / or_valid
```

**Variants to benchmark:**

| Label | Change | Expected win |
|-------|--------|--------------|
| Baseline | current file | — |
| A | `comparison_valid`: merge 6 per-op functions; resolve lhs+rhs once then branch on operator type; `atomic_valid` drops from 7→2 OR branches | ~20-40% on comparison exprs |
| D | `resolve_value` helper returning `{ data_value }`; keep 6 per-op functions but call helper instead of duplicate OR blocks | depends on whether TypeDB inlines helpers |
| AD | Variant A + Variant D combined | potentially additive |

**Note on Variant D / AD:** TypeDB 3 may not support `thing` as a function parameter type, or `-> { data_value }` as a return type for abstract attributes. The plan documents fallbacks if these fail.

---

## Task 1: Write the Benchmark Script

**Files:**
- Create: `scripts/benchmark/benchmark_logical_expression.py`

The script drives all four variants in sequence. It creates a fresh DB per variant, warms up with 10 queries, then times 200 repetitions per expression name.

**Step 1: Create the script**

```python
# Copyright 2026 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...
"""Benchmark script for logical_expression.tql schema function variants.

Usage (from inside the Docker container, with ROS and install sourced):
    python3 scripts/benchmark/benchmark_logical_expression.py

Prints a per-variant, per-expression-type latency table (mean ± stddev, ms).
"""
import statistics
import time

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


BASE_SCHEMAS = [
    'schemas/data_structure/data_structure.tql',
    'schemas/context_model/context_model.tql',
]

DATA_FILES = [
    'test/data/test_logical_expression.tql',
    'test/data/test_logical_expression_compound.tql',
]

# expression name → expression type label
EXPRESSIONS = {
    # propositional
    'bool_false_prop_exp':   'propositional',
    'bool_true_prop_exp':    'propositional',
    'true_measure_prop_exp': 'propositional',
    # comparison (less_than)
    'vd_1_2_less_vd_1_3':   'comparison',
    'md_1_2_less_md_1_3':   'comparison',
    'md_1_2_less_vd_1_3':   'comparison',
    # comparison (equal)
    'vd_1_2_equal_vd_1_2':  'comparison',
    'md_1_2_equal_md_1_2':  'comparison',
    'vs_2_equal_vs_2':       'comparison',
    # not
    'not_false_expr':        'not',
    'not_true_expr':         'not',
    # or
    'or_expression_1':       'or',
    'or_expression_3':       'or',
    # and
    'and_expression_1':      'and',
    'and_expression_2':      'and',
    'and_expression_3':      'and',
}

VARIANTS = [
    ('baseline', 'schemas/logical_expressions/logical_expression.tql'),
    ('A',        'schemas/logical_expressions/logical_expression_variant_a.tql'),
    ('D',        'schemas/logical_expressions/logical_expression_variant_d.tql'),
    ('AD',       'schemas/logical_expressions/logical_expression_variant_ad.tql'),
]

N_WARMUP = 10
N_REPS   = 200


def benchmark_variant(label, schema_file):
    """Load schema, warm up, time N_REPS per expression, return results dict."""
    db_name = f'bench_logical_{label}'
    print(f'\n=== Variant {label!r} ({schema_file}) ===')
    try:
        iface = TacticalRetreatInterface(
            'localhost:1729',
            db_name,
            BASE_SCHEMAS + [schema_file],
            DATA_FILES,
            force_database=True,
            force_data=True,
        )
    except Exception as exc:
        print(f'  SKIP — failed to load schema: {exc}')
        return None

    # Warm up
    for name in list(EXPRESSIONS)[:N_WARMUP]:
        try:
            iface.get_expression_satisfied(name)
        except Exception:
            pass

    # Time
    results = {}  # expr_name → list of seconds
    for name in EXPRESSIONS:
        times = []
        for _ in range(N_REPS):
            t0 = time.perf_counter()
            iface.get_expression_satisfied(name)
            times.append(time.perf_counter() - t0)
        results[name] = times

    iface.delete_database()
    return results


def report(label, results):
    """Print per-type summary for one variant."""
    if results is None:
        print(f'  {label}: SKIPPED')
        return

    by_type = {}
    for name, times in results.items():
        t = EXPRESSIONS[name]
        by_type.setdefault(t, []).extend(times)

    print(f'\nVariant {label!r}:')
    print(f'  {"type":<15} {"mean (ms)":>10}  {"stddev (ms)":>12}  {"n":>5}')
    print(f'  {"-"*15} {"-"*10}  {"-"*12}  {"-"*5}')
    for t in ['propositional', 'comparison', 'not', 'or', 'and']:
        if t not in by_type:
            continue
        ts = [x * 1000 for x in by_type[t]]
        print(f'  {t:<15} {statistics.mean(ts):>10.3f}  {statistics.stdev(ts):>12.3f}  {len(ts):>5}')


def main():
    all_results = {}
    for label, schema_file in VARIANTS:
        all_results[label] = benchmark_variant(label, schema_file)

    print('\n\n=== SUMMARY ===')
    for label, results in all_results.items():
        report(label, results)


if __name__ == '__main__':
    main()
```

**Step 2: Verify the script is syntactically valid**

Run:
```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -c 'import ast; ast.parse(open(\"scripts/benchmark/benchmark_logical_expression.py\").read()); print(\"OK\")'"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add scripts/benchmark/benchmark_logical_expression.py
git commit -m "feat: add logical-expression function benchmark script"
```

---

## Task 2: Run Baseline Benchmark

The baseline schema is the current `logical_expression.tql`. Variant A/D/AD files don't exist yet so the script will skip them — that's fine.

**Step 1: Run the script (baseline only)**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 scripts/benchmark/benchmark_logical_expression.py 2>/dev/null"
```

**Step 2: Record baseline numbers**

Write the summary output into `docs/plans/2026-03-07-benchmark-results.md` for comparison. Format:

```markdown
# Benchmark Results

## Baseline
| type          | mean (ms) | stddev (ms) |
|---------------|-----------|-------------|
| propositional |           |             |
| comparison    |           |             |
| not           |           |             |
| or            |           |             |
| and           |           |             |
```

---

## Task 3: Implement Variant A — `comparison_valid`

**Files:**
- Create: `schemas/logical_expressions/logical_expression_variant_a.tql`

Copy the current `logical_expression.tql` and apply these changes:

1. **Remove** the six per-op comparison functions (`less_than_valid`, ..., `not_equal_valid`).

2. **Add** `comparison_valid` that resolves lhs+rhs once, then branches on operator `isa`:

```typeql
fun comparison_valid($e: comparison_expression) -> boolean:
  match
    $e links (lhs_value: $lhs); $e links (rhs_value: $rhs);
    { $lhs has data_value $l; } or {
      (measure: $lhs, measurement_value: $lmv) isa measurement, has latest true;
      $lmv has data_value $l;
    };
    { $rhs has data_value $r; } or {
      (measure: $rhs, measurement_value: $rmv) isa measurement, has latest true;
      $rmv has data_value $r;
    };
    { $e isa less_than;          $l < $r; } or
    { $e isa less_than_equal;    $l <= $r; } or
    { $e isa greater_than;       $l > $r; } or
    { $e isa greater_than_equal; $l >= $r; } or
    { $e isa equal;              $l == $r; } or
    { $e isa not_equal;          not { $l == $r; }; };
  let $ok = true; return first $ok;
```

> **Variable naming:** `$r` is taken by the rhs value — use `$ok` for the return variable.

3. **Replace** `atomic_valid` with a 2-branch dispatcher:

```typeql
fun atomic_valid($e: logical_expression) -> boolean:
  match
    { $e isa propositional_expression; true == propositional_valid($e); } or
    { $e isa comparison_expression;    true == comparison_valid($e); };
  let $r = true; return first $r;
```

**Step 1: Create the file**

Copy baseline and apply the edits above.

**Step 2: Verify the file is syntactically consistent**

Check all referenced function names exist in the file:
```bash
grep -E "^fun " schemas/logical_expressions/logical_expression_variant_a.tql
```
Expected functions: `propositional_valid`, `comparison_valid`, `atomic_valid`, `not_valid`, `or_valid`, `and_valid`, `expression_valid`.

**Step 3: Run the correctness tests against variant A**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_logical_expression.py -v \
     --override-ini='python_files=test_*.py' \
     -p no:cacheprovider 2>&1 | tail -20"
```

> The test fixture hardcodes `schemas/logical_expressions/logical_expression.tql`. To test variant A without modifying the test, temporarily rename the file OR run a quick ad-hoc sanity check using the benchmark script (which loads variant A). If the benchmark script reports results (not SKIP), the schema loaded successfully. Full correctness validation happens in Task 9 after replacing the main file.

**Step 4: Commit**

```bash
git add schemas/logical_expressions/logical_expression_variant_a.tql
git commit -m "feat: add comparison_valid variant A for benchmarking"
```

---

## Task 4: Run Variant A Benchmark

**Step 1: Run the benchmark**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 scripts/benchmark/benchmark_logical_expression.py 2>/dev/null"
```

**Step 2: Record variant A numbers** in `docs/plans/2026-03-07-benchmark-results.md`.

---

## Task 5: Implement Variant D — `resolve_value` Helper

**Files:**
- Create: `schemas/logical_expressions/logical_expression_variant_d.tql`

Copy the current baseline and apply these changes:

1. **Add** `resolve_value` before all comparison functions:

```typeql
fun resolve_value($thing: thing) -> { data_value }:
  match
    { $thing has data_value $v; } or {
      (measure: $thing, measurement_value: $mv) isa measurement, has latest true;
      $mv has data_value $v;
    };
  return { $v };
```

> **Risk:** TypeDB 3 may reject `thing` as a parameter type or `{ data_value }` as a return type (abstract attribute). If the schema define transaction fails, see the fallback below.

2. **Replace** the duplicate lhs/rhs resolution blocks in each of the 6 per-op functions using `in`:

Example for `less_than_valid`:
```typeql
fun less_than_valid($e: less_than) -> boolean:
  match
    $e links (lhs_value: $lt_lhs); $e links (rhs_value: $lt_rhs);
    $lt_l in resolve_value($lt_lhs);
    $lt_r in resolve_value($lt_rhs);
    $lt_l < $lt_r;
  let $r = true; return first $r;
```

Apply the same pattern to `less_than_equal_valid`, `greater_than_valid`, `greater_than_equal_valid`, `equal_valid`, `not_equal_valid`. Keep `atomic_valid` with its 7 OR branches (unchanged from baseline).

> **Fallback if `thing` is rejected:** Split into two helpers:
> ```typeql
> fun resolve_measure($m: Measure) -> { data_value }:
>   match
>     { $m has data_value $v; } or {
>       (measure: $m, measurement_value: $mv) isa measurement, has latest true;
>       $mv has data_value $v;
>     };
>   return { $v };
>
> fun resolve_value_val($val: Value) -> { data_value }:
>   match
>     $val has data_value $v;
>   return { $v };
> ```
> Then the comparison functions do:
> ```typeql
>   { $lt_l in resolve_measure($lt_lhs); } or { $lt_l in resolve_value_val($lt_lhs); };
>   { $lt_r in resolve_measure($lt_rhs); } or { $lt_r in resolve_value_val($lt_rhs); };
> ```
> This may or may not be faster than the baseline; document the result either way.

**Step 1: Create the file** with `resolve_value` + updated per-op functions.

**Step 2: Check the schema loads** by running the benchmark script. If variant D shows "SKIP — failed to load schema", apply the fallback above, update the file, and re-run.

**Step 3: Commit**

```bash
git add schemas/logical_expressions/logical_expression_variant_d.tql
git commit -m "feat: add resolve_value helper variant D for benchmarking"
```

---

## Task 6: Run Variant D Benchmark

**Step 1: Run the benchmark**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 scripts/benchmark/benchmark_logical_expression.py 2>/dev/null"
```

**Step 2: Record variant D numbers** in `docs/plans/2026-03-07-benchmark-results.md`.

---

## Task 7: Implement Variant AD — Combined

**Files:**
- Create: `schemas/logical_expressions/logical_expression_variant_ad.tql`

Combine both changes: start from Variant A (which has `comparison_valid`) and add `resolve_value` so that `comparison_valid` uses it.

```typeql
fun resolve_value($thing: thing) -> { data_value }:
  match
    { $thing has data_value $v; } or {
      (measure: $thing, measurement_value: $mv) isa measurement, has latest true;
      $mv has data_value $v;
    };
  return { $v };

fun comparison_valid($e: comparison_expression) -> boolean:
  match
    $e links (lhs_value: $lhs); $e links (rhs_value: $rhs);
    $l in resolve_value($lhs);
    $r in resolve_value($rhs);
    { $e isa less_than;          $l < $r; } or
    { $e isa less_than_equal;    $l <= $r; } or
    { $e isa greater_than;       $l > $r; } or
    { $e isa greater_than_equal; $l >= $r; } or
    { $e isa equal;              $l == $r; } or
    { $e isa not_equal;          not { $l == $r; }; };
  let $ok = true; return first $ok;
```

> Apply the same fallback as Task 5 if `resolve_value($thing: thing)` is rejected.

**Step 1: Create the file.**

**Step 2: Check the schema loads** by running the benchmark script.

**Step 3: Commit**

```bash
git add schemas/logical_expressions/logical_expression_variant_ad.tql
git commit -m "feat: add combined comparison_valid+resolve_value variant AD for benchmarking"
```

---

## Task 8: Run Full Benchmark and Pick Winner

**Step 1: Run the full benchmark (all four variants)**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 scripts/benchmark/benchmark_logical_expression.py 2>/dev/null"
```

**Step 2: Fill in the results table** in `docs/plans/2026-03-07-benchmark-results.md`:

```markdown
## All Variants — comparison expression mean latency (ms)

| variant   | propositional | comparison | not | or | and | notes |
|-----------|--------------|------------|-----|----|-----|-------|
| baseline  |              |            |     |    |     |       |
| A         |              |            |     |    |     |       |
| D         |              |            |     |    |     |       |
| AD        |              |            |     |    |     |       |

**Winner:** [label] — [reason]
```

**Step 3: Commit results**

```bash
git add docs/plans/2026-03-07-benchmark-results.md
git commit -m "docs: record logical-expression benchmark results"
```

---

## Task 9: Apply Winner to `logical_expression.tql`

**Files:**
- Modify: `schemas/logical_expressions/logical_expression.tql`

**Step 1: Overwrite with the winning variant**

Copy the content of the winning variant file over `logical_expression.tql`:

```bash
cp schemas/logical_expressions/logical_expression_variant_<WINNER>.tql \
   schemas/logical_expressions/logical_expression.tql
```

**Step 2: Run correctness tests**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_logical_expression.py -v 2>&1 | tail -20"
```

Expected: **10/10 PASS** (all expression types, including compound).

**Step 3: Run quality checks**

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8"
```

**Step 4: Remove variant files if no longer needed**

```bash
rm schemas/logical_expressions/logical_expression_variant_{a,d,ad}.tql
```

**Step 5: Commit**

```bash
git add schemas/logical_expressions/logical_expression.tql
git add -u schemas/logical_expressions/
git commit -m "perf: apply fastest logical-expression schema variant (<WINNER>)"
```

---

## Reference: Running Tests

```bash
# Full test suite
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_logical_expression.py -v"

# One test
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_logical_expression.py::test_and_expression -v"
```
