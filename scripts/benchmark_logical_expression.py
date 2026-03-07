# Copyright 2026 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Benchmark script for logical_expression.tql schema function variants.

Usage (from inside the Docker container, with ROS and install sourced):
    python3 scripts/benchmark_logical_expression.py

Prints a per-variant, per-expression-type latency table (mean ± stddev, ms).
"""

import os
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

# expression name -> expression type label
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
N_REPS = 200


def benchmark_variant(label, schema_file):
    """Load schema, warm up, time N_REPS per expression, return results dict."""
    db_name = f'bench_logical_{label}'
    print(f'\n=== Variant {label!r} ({schema_file}) ===')
    if not os.path.exists(schema_file):
        print(f'  SKIP — schema file not found: {schema_file}')
        return None
    try:
        iface = TacticalRetreatInterface(
            'localhost:1729',
            db_name,
            BASE_SCHEMAS + [schema_file],
            DATA_FILES,
            force_database=True,
            force_data=True,
        )
    except Exception as exc:  # noqa: B902
        print(f'  SKIP — failed to load schema: {exc}')
        return None

    # Warm up: N_WARMUP full passes over all expressions
    for _ in range(N_WARMUP):
        for name in EXPRESSIONS:
            try:
                iface.get_expression_satisfied(name)
            except Exception:  # noqa: B902
                pass

    # Time
    results = {}  # expr_name -> list of seconds
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
        print(f'  {label}: SKIP')
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
        print(
            f'  {t:<15} {statistics.mean(ts):>10.3f}  {statistics.stdev(ts):>12.3f}  {len(ts):>5}'
        )


def main():
    """Run benchmark across all schema variants and print summary."""
    all_results = {}
    for label, schema_file in VARIANTS:
        all_results[label] = benchmark_variant(label, schema_file)

    print('\n\n=== SUMMARY ===')
    for label, results in all_results.items():
        report(label, results)


if __name__ == '__main__':
    main()
