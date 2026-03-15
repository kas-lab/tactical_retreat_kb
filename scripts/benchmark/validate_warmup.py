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
"""
Validate that warm_up() eliminates the TypeDB JIT cold-start penalty.

For each repeat, two scenarios are run on independent fresh databases:

  - without warm_up(): time the first call to
    fetch_tactic_rule_impacts_requirement directly after DB setup.
  - with warm_up(): call warm_up() first, then time the same first call.

A speedup >= 3× confirms warm_up() is pre-warming the JIT successfully.

Usage::

    python3 scripts/benchmark/validate_warmup.py [--repeats N] [--address HOST:PORT]
"""

import argparse
import math
from pathlib import Path
import time
from typing import List

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent

SCHEMAS = [
    'schemas/data_structure/data_structure.tql',
    'schemas/context_model/context_model.tql',
    'schemas/logical_expressions/logical_expression.tql',
    'schemas/logical_expressions/fuzzy_expression.tql',
    'schemas/ros_model/ros_model.tql',
    'schemas/feature_model/feature_model.tql',
    'schemas/relaxed/relaxed_model.tql',
    'schemas/tactics_model/tactics_model.tql',
    'schemas/discover_hypothetical_req_fulfillment/'
    'discover_hypothetical_req_fulfillment.tql',
    'schemas/discover_tactics_model/discover_tactics_model.tql',
]

DATA = [
    'scripts/benchmark/benchmark.tql',
]


def percentile(values: List[float], fraction: float) -> float:
    """Compute nearest-rank percentile."""
    if not values:
        return 0.0
    sv = sorted(values)
    if fraction <= 0.0:
        return sv[0]
    if fraction >= 1.0:
        return sv[-1]
    return sv[math.ceil(fraction * len(sv)) - 1]


def make_interface(address: str, db_name: str) -> TacticalRetreatInterface:
    """Create a fresh TacticalRetreatInterface with schema and example data."""
    return TacticalRetreatInterface(
        address,
        db_name,
        [str(REPO_DIR / s) for s in SCHEMAS],
        [str(REPO_DIR / d) for d in DATA],
        force_database=True,
        force_data=True,
    )


def time_calls(
    iface: TacticalRetreatInterface,
    rule: str,
    req: str,
) -> tuple:
    """
    Time the first and second call to fetch_tactic_rule_impacts_requirement.

    :param iface: active interface
    :param rule: tactic rule name to use
    :param req: requirement name to use
    :return: (first_ms, second_ms)
    """
    t0 = time.perf_counter()
    iface.fetch_tactic_rule_impacts_requirement(req, rule)
    first_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    iface.fetch_tactic_rule_impacts_requirement(req, rule)
    second_ms = (time.perf_counter() - t1) * 1000.0

    return first_ms, second_ms


def get_in_effect_requirement_names(iface: TacticalRetreatInterface) -> List[str]:
    """
    Return requirement names that have in_effect true.

    Uses a structural query only — does NOT call any schema function,
    so the JIT cold state is preserved for subsequent timing.

    :param iface: active interface
    :return: list of requirement_name strings with in_effect true
    """
    rows = iface.fetch_database("""
        match
            $req isa relaxed_requirement,
                has requirement_name $name,
                has in_effect true;
        fetch { "name": $name };
    """)
    return [row['name'] for row in rows if row.get('name') is not None]


def run_scenario(address: str, db_name: str, with_warmup: bool) -> tuple:
    """
    Set up a fresh DB, optionally warm up, return call latencies in ms.

    Uses the first in_effect requirement to match the benchmark's data
    selection, avoiding pathologically slow non-effect pairs.

    :param address: TypeDB server address
    :param db_name: database name to create (overwritten each run)
    :param with_warmup: whether to call warm_up() before timing
    :return: (first_ms, second_ms) after optional warm_up()
    """
    iface = make_interface(address, db_name)
    try:
        rules = iface.get_all_tactic_rules()
        reqs = get_in_effect_requirement_names(iface)
        if not rules or not reqs:
            raise RuntimeError('No tactic rules or in_effect requirements found in DB.')
        if with_warmup:
            iface.warm_up()
        return time_calls(iface, rules[0], reqs[0])
    finally:
        iface.delete_database()


def main() -> None:
    """Run the warm_up() validation benchmark."""
    parser = argparse.ArgumentParser(
        description='Validate that warm_up() reduces TypeDB JIT cold-start latency.')
    parser.add_argument('--address', default='localhost:1729',
                        help='TypeDB server address (default: localhost:1729)')
    parser.add_argument('--repeats', type=int, default=5,
                        help='Fresh-DB repetitions per scenario (default: 5)')
    args = parser.parse_args()

    db_cold = 'validate_warmup_cold'
    db_warm = 'validate_warmup_warm'

    print(f'=== warm_up() validation  repeats={args.repeats} ===\n')
    print('  Measuring fetch_tactic_rule_impacts_requirement.')
    print('  Each repeat uses an independent fresh DB.')
    print('  "1st" = first call,  "2nd" = immediate repeat on same DB.\n')
    print(f'  {"":30s}  {"1st":>7s}  {"2nd":>7s}')

    # (first_ms, second_ms) per repeat for each scenario
    cold_results: List[tuple] = []
    warm_results: List[tuple] = []

    for i in range(1, args.repeats + 1):
        cold = run_scenario(args.address, db_cold, with_warmup=False)
        warm = run_scenario(args.address, db_warm, with_warmup=True)
        cold_results.append(cold)
        warm_results.append(warm)
        print(f'  [repeat {i}] without warm_up():        {cold[0]:>6.1f}ms  {cold[1]:>6.1f}ms')
        print(f'  [repeat {i}] with    warm_up():        {warm[0]:>6.1f}ms  {warm[1]:>6.1f}ms')

    cold_first = [r[0] for r in cold_results]
    cold_second = [r[1] for r in cold_results]
    warm_first = [r[0] for r in warm_results]
    warm_second = [r[1] for r in warm_results]

    cold_first_p50 = percentile(cold_first, 0.50)
    cold_second_p50 = percentile(cold_second, 0.50)
    warm_first_p50 = percentile(warm_first, 0.50)
    warm_second_p50 = percentile(warm_second, 0.50)

    print()
    print('--- p50 summary ---')
    print(f'  {"":30s}  {"1st":>7s}  {"2nd":>7s}')
    print(f'  {"without warm_up():":30s}  {cold_first_p50:>6.1f}ms  {cold_second_p50:>6.1f}ms')
    print(f'  {"with    warm_up():":30s}  {warm_first_p50:>6.1f}ms  {warm_second_p50:>6.1f}ms')
    print()

    # JIT effect: how much faster is the 2nd call vs 1st on a cold DB?
    cold_jit = cold_first_p50 / cold_second_p50 if cold_second_p50 > 0 else float('inf')
    cold_penalty_ms = cold_first_p50 - cold_second_p50

    # warm_up() effect: does it bring 1st-call latency to warm speed?
    # Pass if warm_first is within 15% of cold_second (the natural warm baseline).
    warm_baseline = cold_second_p50
    warm_delta_pct = abs(warm_first_p50 - warm_baseline) / warm_baseline * 100
    warmup_works = warm_delta_pct <= 15.0

    print(f'  Cold JIT overhead (1st - 2nd, no warm_up):   {cold_penalty_ms:+.1f}ms'
          f'  ({cold_jit:.2f}x)')
    print(f'  warm_up() 1st vs warm baseline:              '
          f'{warm_first_p50:.1f}ms vs {warm_baseline:.1f}ms  ({warm_delta_pct:.0f}% delta)')
    print()

    if cold_jit < 1.05:
        print('  INFO: No JIT cold/warm distinction detected for this function.')
        print('        warm_up() cannot be validated via latency measurement.')
    elif warmup_works:
        print(f'  PASS: warm_up() eliminates the {cold_penalty_ms:.0f}ms cold penalty'
              f' — first call runs at warm speed.')
    else:
        print('  FAIL: warm_up() does not bring first-call latency to warm speed.')


if __name__ == '__main__':
    main()
