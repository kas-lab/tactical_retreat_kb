#!/usr/bin/env python3
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
"""Focused benchmark for discover_tactics_model.tql functions.

Benchmarks neighbours(), connected_nodes(), and applicable_tactics()
using the working ros_model_example + tactics_example data.
Run with --label to tag variants (e.g. v0, v1v2).
"""

import argparse
import math
import time
from pathlib import Path
from typing import Callable, Dict, List

from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB  # noqa: E501

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent

SCHEMAS = [
    'schemas/data_structure/data_structure.tql',
    'schemas/context_model/context_model.tql',
    'schemas/logical_expressions/logical_expression.tql',
    'schemas/ros_model/ros_model.tql',
    'schemas/feature_model/feature_model.tql',
    'schemas/feature_model/feature_model_logical_expression.tql',
    'schemas/tactics_model/tactics_model.tql',
    'schemas/discover_tactics_model/discover_tactics_model.tql',
]

DATA = [
    'schemas/ros_model/ros_model_example.tql',
    'schemas/tactics_model/tactics_example.tql',
]


def abs_path(rel: str) -> str:
    return str((REPO_DIR / rel).resolve())


def percentile(values: List[float], fraction: float) -> float:
    if not values:
        return 0.0
    sv = sorted(values)
    if fraction <= 0.0:
        return sv[0]
    if fraction >= 1.0:
        return sv[-1]
    return sv[math.ceil(fraction * len(sv)) - 1]


def bench(label: str, fn: Callable[[], list], runs: int) -> Dict:
    cold_t = time.perf_counter()
    cold_r = fn()
    cold_ms = (time.perf_counter() - cold_t) * 1000.0

    warm: List[float] = []
    counts: List[int] = [len(cold_r)]
    for _ in range(runs):
        t = time.perf_counter()
        r = fn()
        warm.append((time.perf_counter() - t) * 1000.0)
        counts.append(len(r))

    return {
        'label': label,
        'cold_ms': cold_ms,
        'avg_ms': sum(warm) / len(warm),
        'p50_ms': percentile(warm, 0.50),
        'p95_ms': percentile(warm, 0.95),
        'rows': f'{min(counts)}..{max(counts)}',
    }


def fetch(driver, db_name: str, query: str) -> list:
    with driver.transaction(db_name, TransactionType.READ) as tx:
        return list(tx.query(query).resolve())


def load_schema(driver, db_name: str, path: str) -> None:
    content = Path(path).read_text()
    with driver.transaction(db_name, TransactionType.SCHEMA) as tx:
        tx.query(content).resolve()
        tx.commit()


def load_data(driver, db_name: str, path: str) -> None:
    content = Path(path).read_text()
    with driver.transaction(db_name, TransactionType.WRITE) as tx:
        tx.query(content).resolve()
        tx.commit()


def setup_db(driver, db_name: str) -> None:
    if driver.databases.contains(db_name):
        driver.databases.get(db_name).delete()
    driver.databases.create(db_name)
    for rel_path in SCHEMAS:
        load_schema(driver, db_name, abs_path(rel_path))
    for rel_path in DATA:
        load_data(driver, db_name, abs_path(rel_path))


QUERY_CASES = [
    (
        'neighbours[bt_navigator]',
        'match $node isa ROSNode, has node_name "bt_navigator";'
        ' let $nb in neighbours($node);'
        ' fetch { "node_name": $nb.node_name };',
    ),
    (
        'connected_nodes[bt_navigator]',
        'match $node isa ROSNode, has node_name "bt_navigator";'
        ' let $conn in connected_nodes($node);'
        ' fetch { "node_name": $conn.node_name };',
    ),
    (
        'applicable_tactics[/navigate_to_pose|rebetmc]',
        'match $iface isa ROSInterface,'
        ' has interface_name "/navigate_to_pose";'
        ' $rm isa resolution_model,'
        ' has resolution_model_name "rebetmc";'
        ' let $tr in applicable_tactics($iface, $rm);'
        ' fetch { "rule_name": $tr.rule_name };',
    ),
]


def run_repeat(address: str, db_name: str, runs: int, repeat_idx: int) -> List[Dict]:
    """One full benchmark repeat: fresh driver + fresh DB + warm runs."""
    driver = TypeDB.driver(
        address,
        Credentials('admin', 'password'),
        DriverOptions(is_tls_enabled=False),
    )
    try:
        print(f'  [repeat {repeat_idx}] setting up DB...', flush=True)
        setup_db(driver, db_name)
        cases = [
            bench(label, lambda q=query: fetch(driver, db_name, q), runs)
            for label, query in QUERY_CASES
        ]
        driver.databases.get(db_name).delete()
        return cases
    finally:
        driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark discover_tactics_model functions.')
    parser.add_argument('--address', default='localhost:1729')
    parser.add_argument('--runs', type=int, default=30, help='Warm runs per repeat')
    parser.add_argument('--repeats', type=int, default=3,
                        help='Independent full repeats (fresh driver+DB each time)')
    parser.add_argument('--label', default='current', help='Variant label (e.g. v0, v1v2)')
    parser.add_argument('--db', default='benchmark_dtm')
    args = parser.parse_args()

    print(f'=== variant={args.label!r} runs={args.runs} repeats={args.repeats} ===\n')

    # Collect per-repeat results: list of list of dicts
    all_repeats: List[List[Dict]] = []
    for i in range(1, args.repeats + 1):
        result = run_repeat(args.address, args.db, args.runs, i)
        all_repeats.append(result)
        print(f'  [repeat {i}] raw p50s: '
              + '  '.join(f"{c['label'].split('[')[0]}={c['p50_ms']:.1f}ms" for c in result))

    # Aggregate across repeats
    n_cases = len(QUERY_CASES)
    print(f'\n--- Summary across {args.repeats} repeats ---')
    for ci in range(n_cases):
        label = all_repeats[0][ci]['label']
        p50s = [all_repeats[ri][ci]['p50_ms'] for ri in range(args.repeats)]
        p95s = [all_repeats[ri][ci]['p95_ms'] for ri in range(args.repeats)]
        cold_ms = all_repeats[0][ci]['cold_ms']  # first repeat cold
        rows = all_repeats[0][ci]['rows']
        med_p50 = percentile(p50s, 0.50)
        min_p50 = min(p50s)
        max_p50 = max(p50s)
        med_p95 = percentile(p95s, 0.50)
        print(
            f'  {label}:\n'
            f'    cold={cold_ms:.1f}ms  '
            f'p50: min={min_p50:.1f} med={med_p50:.1f} max={max_p50:.1f}ms  '
            f'p95(med)={med_p95:.1f}ms  rows={rows}'
        )


if __name__ == '__main__':
    main()
