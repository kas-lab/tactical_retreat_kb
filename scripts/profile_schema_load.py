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

import argparse
import time
from typing import Iterable
from typing import List

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


DEFAULT_SCHEMAS = [
    '../schemas/data_structure/data_structure.tql',
    '../schemas/context_model/context_model.tql',
    '../schemas/logical_expressions/logical_expression.tql',
    '../schemas/logical_expressions/fuzzy_expression.tql',
    '../schemas/ros_model/ros_model.tql',
    '../schemas/feature_model/feature_model.tql',
    '../schemas/feature_model/feature_model_logical_expression.tql',
    '../schemas/relaxed/relaxed_model.tql',
    '../schemas/tactics_model/tactics_model.tql',
    '../schemas/discover_hypothetical_req_fulfillment/'
    'discover_hypothetical_req_fulfillment.tql',
    '../schemas/discover_tactics_model/discover_tactics_model.tql',
]


def profile_schema_load(
    address: str,
    database_name: str,
    schemas: Iterable[str],
) -> float:
    interface_init_start = time.perf_counter()
    kb_interface = TacticalRetreatInterface(
        address,
        database_name,
        [],
        [],
        force_database=True,
        force_data=True,
    )
    interface_init_s = time.perf_counter() - interface_init_start
    print(f'interface_init_no_schema={interface_init_s:.6f}s')

    total_schema_time_s = 0.0
    for schema_path in schemas:
        start = time.perf_counter()
        kb_interface.load_schema(schema_path)
        elapsed = time.perf_counter() - start
        total_schema_time_s += elapsed
        print(f'{schema_path} => {elapsed:.6f}s')

    print(f'schema_total={total_schema_time_s:.6f}s')
    return total_schema_time_s


def main():
    parser = argparse.ArgumentParser(
        description='Profile TypeDB schema loading time per schema file.'
    )
    parser.add_argument(
        '--address',
        default='localhost:1729',
        help='TypeDB address (default: localhost:1729)',
    )
    parser.add_argument(
        '--database',
        default='benchmark_schema_profile',
        help='Base database name used for profiling runs.',
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=1,
        help='Number of profiling runs (default: 1).',
    )
    parser.add_argument(
        '--schemas',
        nargs='*',
        default=DEFAULT_SCHEMAS,
        help='Schema paths to load in order (default: benchmark schema list).',
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error('--runs must be >= 1')

    run_totals: List[float] = []
    for run_idx in range(args.runs):
        run_database = (
            args.database
            if args.runs == 1
            else f'{args.database}_{run_idx + 1}'
        )
        print(f'--- run {run_idx + 1}/{args.runs} database={run_database} ---')
        run_total = profile_schema_load(
            args.address,
            run_database,
            args.schemas,
        )
        run_totals.append(run_total)

    average_total = sum(run_totals) / len(run_totals)
    print(f'schema_total_avg={average_total:.6f}s')


if __name__ == '__main__':
    main()
