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
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from typing import Callable
from typing import Dict
from typing import List

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@dataclass(frozen=True)
class ProfileConfig:
    """Benchmark profile configuration."""

    name: str
    schema_paths: List[str]
    data_paths: List[str]
    resolution_model: str
    applicable_interfaces: List[str]
    potential_action: str


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent


def to_abs_paths(paths: List[str]) -> List[str]:
    """Resolve repository-relative paths to absolute paths."""
    return [str((REPO_DIR / path).resolve()) for path in paths]


def percentile(values: List[float], fraction: float) -> float:
    """Compute percentile using nearest-rank over a sorted list."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if fraction <= 0.0:
        return sorted_values[0]
    if fraction >= 1.0:
        return sorted_values[-1]
    rank = math.ceil(fraction * len(sorted_values))
    return sorted_values[rank - 1]


def benchmark_query_case(
    label: str,
    query_fn: Callable[[], List[dict]],
    runs: int,
) -> Dict[str, float | int | str | bool]:
    """Benchmark a query function with one cold run and N warm runs."""
    warm_durations_ms: List[float] = []
    row_counts: List[int] = []

    cold_start = time.perf_counter()
    cold_result = query_fn()
    cold_duration_ms = (time.perf_counter() - cold_start) * 1000.0
    row_counts.append(len(cold_result))

    for _ in range(runs):
        start = time.perf_counter()
        result = query_fn()
        warm_durations_ms.append((time.perf_counter() - start) * 1000.0)
        row_counts.append(len(result))

    warm_avg_ms = sum(warm_durations_ms) / len(warm_durations_ms)
    warm_p50_ms = percentile(warm_durations_ms, 0.50)
    warm_p95_ms = percentile(warm_durations_ms, 0.95)

    return {
        'label': label,
        'cold_ms': cold_duration_ms,
        'warm_avg_ms': warm_avg_ms,
        'warm_p50_ms': warm_p50_ms,
        'warm_p95_ms': warm_p95_ms,
        'row_count_min': min(row_counts),
        'row_count_max': max(row_counts),
        'row_count_stable': min(row_counts) == max(row_counts),
    }


def build_raw_potential_query(
    action_name: str,
    resolution_model: str,
    with_fulfillment: bool,
) -> str:
    """Build raw potential-fulfillment query shapes for diagnostics."""
    impact_line = (
        '$tactic_impact (impacted: $req, tactic_rule: $tactic_rule) '
        'isa tactic_rule_impacts_requirement_in_effect;'
    )
    fetch_lines = [
        '$tactic_rule: rule_name;',
        '$req: requirement_name;',
    ]

    if with_fulfillment:
        impact_line = (
            '$tactic_impact (impacted: $req, tactic_rule: $tactic_rule) '
            'isa tactic_rule_impacts_requirement_in_effect, has fulfillment $fulfillment;'
        )
        fetch_lines.append('$fulfillment;')

    fetch_query = '\n                '.join(fetch_lines)
    return f"""
            match
                $ros_interface isa ROSInterface, has interface_name '{action_name}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (interface: $ros_interface,
                    resolution_model: $resolution_model,
                    tactic_rule: $tactic_rule) isa applicable_tactics;
                {impact_line}
                $req isa relaxed_requirement, has in_effect true;
            fetch
                {fetch_query}
        """


def get_profiles() -> Dict[str, ProfileConfig]:
    """Return all supported benchmark profiles."""
    generated_schemas = [
        'schemas/data_structure/data_structure.tql',
        'schemas/context_model/context_model.tql',
        'schemas/logical_expressions/logical_expression.tql',
        'schemas/logical_expressions/fuzzy_expression.tql',
        'schemas/ros_model/ros_model.tql',
        'schemas/feature_model/feature_model.tql',
        'schemas/feature_model/feature_model_logical_expression.tql',
        'schemas/relaxed/relaxed_model.tql',
        'schemas/tactics_model/tactics_model.tql',
        'schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql',
        'schemas/discover_tactics_model/discover_tactics_model.tql',
    ]
    hyp_schemas = [
        'schemas/data_structure/data_structure.tql',
        'schemas/context_model/context_model.tql',
        'schemas/logical_expressions/logical_expression.tql',
        'schemas/logical_expressions/fuzzy_expression.tql',
        'schemas/ros_model/ros_model.tql',
        'schemas/feature_model/feature_model.tql',
        'schemas/relaxed/relaxed_model.tql',
        'schemas/tactics_model/tactics_model.tql',
        'schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql',
        'schemas/discover_tactics_model/discover_tactics_model.tql',
    ]

    return {
        'generated': ProfileConfig(
            name='generated',
            schema_paths=to_abs_paths(generated_schemas),
            data_paths=[str((SCRIPT_DIR / 'generated.tql').resolve())],
            resolution_model='rebet_frog',
            applicable_interfaces=[
                '/navigate_to_pose',
                '/follow_path',
                '/compute_path_to_pose',
            ],
            potential_action='/navigate_to_pose',
        ),
        'hyp': ProfileConfig(
            name='hyp',
            schema_paths=to_abs_paths(hyp_schemas),
            data_paths=to_abs_paths([
                'test/data/test_discover_hypothetical_req_fulfillment.tql',
                'schemas/ros_model/ros_model_example.tql',
                'schemas/tactics_model/tactics_example.tql',
                'schemas/relaxed/relaxed_mirte_example.tql',
            ]),
            resolution_model='rebetmc',
            applicable_interfaces=[
                '/navigate_to_pose',
                '/follow_path',
                '/compute_path_to_pose',
            ],
            potential_action='/navigate_to_pose',
        ),
    }


def benchmark_profile(
    profile: ProfileConfig,
    address: str,
    db_name: str,
    runs: int,
    infer: bool,
) -> Dict:
    """Benchmark initialization and query timings for a profile."""
    init_no_schema_start = time.perf_counter()
    kb_interface = TacticalRetreatInterface(
        address,
        db_name,
        [],
        [],
        force_database=True,
        force_data=True,
        infer=infer,
    )
    init_no_schema_s = time.perf_counter() - init_no_schema_start

    schema_timings = []
    schema_total_s = 0.0
    for path in profile.schema_paths:
        start = time.perf_counter()
        kb_interface.load_schema(path)
        elapsed_s = time.perf_counter() - start
        schema_total_s += elapsed_s
        schema_timings.append({'path': path, 'seconds': elapsed_s})

    data_timings = []
    data_total_s = 0.0
    for path in profile.data_paths:
        start = time.perf_counter()
        kb_interface.load_data(path)
        elapsed_s = time.perf_counter() - start
        data_total_s += elapsed_s
        data_timings.append({'path': path, 'seconds': elapsed_s})

    query_cases = []
    for interface_name in profile.applicable_interfaces:
        query_cases.append(benchmark_query_case(
            f'fetch_applicable_tactics[{interface_name}]',
            lambda interface_name=interface_name: kb_interface.fetch_applicable_tactics(
                profile.resolution_model, interface_name),
            runs,
        ))

    query_cases.append(benchmark_query_case(
        f'fetch_potential_requirements_fulfillment[{profile.potential_action}]',
        lambda: kb_interface.fetch_potential_requirements_fulfillment(
            profile.potential_action),
        runs,
    ))
    query_cases.append(benchmark_query_case(
        (
            'fetch_potential_requirements_fulfillment['
            f'{profile.potential_action}|{profile.resolution_model}]'
        ),
        lambda: kb_interface.fetch_potential_requirements_fulfillment(
            profile.potential_action,
            resolution_model=profile.resolution_model),
        runs,
    ))

    raw_without_fulfillment = build_raw_potential_query(
        profile.potential_action,
        profile.resolution_model,
        with_fulfillment=False,
    )
    raw_with_fulfillment = build_raw_potential_query(
        profile.potential_action,
        profile.resolution_model,
        with_fulfillment=True,
    )
    query_cases.append(benchmark_query_case(
        (
            'diagnostic_raw_potential_shape['
            f'{profile.potential_action}|{profile.resolution_model}|no-fulfillment]'
        ),
        lambda: kb_interface.fetch_database(raw_without_fulfillment),
        runs,
    ))
    query_cases.append(benchmark_query_case(
        (
            'diagnostic_raw_potential_shape['
            f'{profile.potential_action}|{profile.resolution_model}|with-fulfillment]'
        ),
        lambda: kb_interface.fetch_database(raw_with_fulfillment),
        runs,
    ))

    slowest_queries = sorted(
        query_cases,
        key=lambda item: item['warm_p50_ms'],
        reverse=True)[:3]
    slowest_schemas = sorted(
        schema_timings,
        key=lambda item: item['seconds'],
        reverse=True)[:3]

    kb_interface.delete_database()

    return {
        'profile': profile.name,
        'database_name': db_name,
        'infer': infer,
        'init': {
            'init_no_schema_s': init_no_schema_s,
            'schema_total_s': schema_total_s,
            'data_total_s': data_total_s,
            'schema_files': schema_timings,
            'data_files': data_timings,
        },
        'queries': query_cases,
        'slowest_query_cases': slowest_queries,
        'slowest_schema_files': slowest_schemas,
    }


def print_text_report(report: Dict) -> None:
    """Print a human-readable report."""
    print(f"=== profile={report['profile']} database={report['database_name']} ===")
    init = report['init']
    print(f"init_no_schema_s={init['init_no_schema_s']:.6f}")
    print(f"schema_total_s={init['schema_total_s']:.6f}")
    print(f"data_total_s={init['data_total_s']:.6f}")

    print('schema_file_timings:')
    for item in init['schema_files']:
        print(f"  - {item['path']}: {item['seconds']:.6f}s")

    print('data_file_timings:')
    for item in init['data_files']:
        print(f"  - {item['path']}: {item['seconds']:.6f}s")

    print('query_timings:')
    for case in report['queries']:
        print(
            f"  - {case['label']}: cold={case['cold_ms']:.3f}ms "
            f"warm_avg={case['warm_avg_ms']:.3f}ms "
            f"warm_p50={case['warm_p50_ms']:.3f}ms "
            f"warm_p95={case['warm_p95_ms']:.3f}ms "
            f"rows={case['row_count_min']}..{case['row_count_max']} "
            f"stable={case['row_count_stable']}"
        )

    print('top_3_slowest_query_cases_by_warm_p50:')
    for case in report['slowest_query_cases']:
        print(f"  - {case['label']}: {case['warm_p50_ms']:.3f}ms")

    print('top_3_slowest_schema_files_by_load_time:')
    for item in report['slowest_schema_files']:
        print(f"  - {item['path']}: {item['seconds']:.6f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Benchmark query and initialization bottlenecks.'
    )
    parser.add_argument(
        '--address',
        default='localhost:1729',
        help='TypeDB address (default: localhost:1729).',
    )
    parser.add_argument(
        '--profiles',
        default='generated,hyp',
        help='Comma-separated profiles to run: generated,hyp (default: both).',
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=30,
        help='Number of warm runs per query case (default: 30).',
    )
    parser.add_argument(
        '--db-prefix',
        default='benchmark_queries',
        help='Database name prefix (default: benchmark_queries).',
    )
    parser.add_argument(
        '--infer',
        action='store_true',
        default=True,
        help='Enable inference while benchmarking (default: enabled).',
    )
    parser.add_argument(
        '--no-infer',
        dest='infer',
        action='store_false',
        help='Disable inference while benchmarking.',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text).',
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error('--runs must be >= 1')

    all_profiles = get_profiles()
    requested_profiles = [x.strip() for x in args.profiles.split(',') if x.strip()]
    if not requested_profiles:
        parser.error('No profile selected. Use --profiles generated,hyp')

    invalid = [profile for profile in requested_profiles if profile not in all_profiles]
    if invalid:
        parser.error(
            f"Invalid profile(s): {', '.join(invalid)}. "
            'Supported profiles: generated,hyp'
        )

    reports = []
    for profile_name in requested_profiles:
        profile = all_profiles[profile_name]
        db_name = f'{args.db_prefix}_{profile_name}'
        report = benchmark_profile(
            profile=profile,
            address=args.address,
            db_name=db_name,
            runs=args.runs,
            infer=args.infer,
        )
        reports.append(report)

    final_report = {
        'address': args.address,
        'runs': args.runs,
        'infer': args.infer,
        'profiles': reports,
    }

    if args.format == 'json':
        print(json.dumps(final_report, indent=2))
        return

    for report in reports:
        print_text_report(report)


if __name__ == '__main__':
    main()
