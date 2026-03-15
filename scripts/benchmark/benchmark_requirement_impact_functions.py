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

"""Benchmark discover_hypothetical_req_fulfillment functions individually."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import logging
import math
from pathlib import Path
import re
import time
from typing import Callable
from typing import List
from typing import Optional

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


SCRIPT_DIR = Path(__file__).resolve().parent
NOISY_LOGGERS = (
    'ros_typedb.typedb_interface',
    'typedb_tactics.typedb_tactical_retreat_interface',
)


def load_benchmark_queries_module():
    """Import benchmark_queries.py to reuse the benchmark profile defaults."""
    module_path = SCRIPT_DIR / 'benchmark_queries.py'
    spec = importlib.util.spec_from_file_location(
        'typedb_tactics_benchmark_queries_functions',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def suppress_probe_logging():
    """Silence expected TypeDB errors while probing representative cases."""
    loggers = [logging.getLogger(name) for name in NOISY_LOGGERS]
    previous_states = [(logger, logger.disabled) for logger in loggers]
    for logger in loggers:
        logger.disabled = True
    try:
        yield
    finally:
        for logger, disabled in previous_states:
            logger.disabled = disabled


def percentile(values: List[float], fraction: float) -> float:
    """Compute nearest-rank percentile on a sorted list."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if fraction <= 0.0:
        return sorted_values[0]
    if fraction >= 1.0:
        return sorted_values[-1]
    rank = math.ceil(fraction * len(sorted_values))
    return sorted_values[rank - 1]


def escape_string(value: str) -> str:
    """Escape a Python string for single-quoted TypeQL literals."""
    return value.replace('\\', '\\\\').replace("'", "\\'")


def quote(value: str) -> str:
    """Return a TypeQL-safe single-quoted string literal."""
    return f"'{escape_string(value)}'"


def query_first_row(
    kb_interface: TacticalRetreatInterface,
    query: str,
) -> Optional[dict]:
    """Run a fetch query and return the first row, if any."""
    rows = kb_interface.fetch_database(query)
    if not rows:
        return None
    return rows[0]


@dataclass(frozen=True)
class BenchmarkCase:
    """One representative function benchmark case."""

    function_name: str
    query: str
    input_description: str


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing summary for one representative function call."""

    function_name: str
    input_description: str
    row_count: int
    cold_runs: int          # relative cold: fresh DB + discovery warmup before each
    cold_avg_ms: float
    cold_p50_ms: float
    cold_p95_ms: float
    true_cold_runs: int     # true cold: fresh DB, no warmup (0 = not measured)
    true_cold_avg_ms: float
    true_cold_p50_ms: float
    true_cold_p95_ms: float
    warm_avg_ms: float
    warm_p50_ms: float
    warm_p95_ms: float


FUNCTION_ORDER = [
    'tactic_rule_hypothetical_measure_value',
    'tactic_rule_hypothetical_comparison_lhs_value',
    'tactic_rule_hypothetical_comparison_rhs_value',
    'tactic_rule_impacts_comparison_fulfillment',
    'tactic_rule_hypothetical_fuzzy_term',
    'tactic_rule_impacts_fuzzy_leaf_fulfillment',
    'tactic_rule_hypothetical_relaxed_term',
    'tactic_rule_impacts_relaxed_leaf_fulfillment',
    'tactic_rule_impacts_not_membership',
    'tactic_rule_impacts_fuzzy_not_membership',
    'tactic_rule_impacts_fuzzy_or_fulfillment',
    'tactic_rule_impacts_fuzzy_and_fulfillment',
    'tactic_rule_impacts_may_fulfillment',
    'tactic_rule_impacts_shall_fulfillment',
    'tactic_rule_impacts_any_expression_fulfillment',
    'tactic_rule_impacts_requirement_fulfillment',
]


def requirement_pair_query(rule_name: Optional[str] = None) -> str:
    """Discovery query for a valid (tactic_rule, requirement) pair."""
    rule_filter = ''
    if rule_name is not None:
        rule_filter = f',\n                has rule_name {quote(rule_name)}'
    return f"""
        match
            $tr isa tactic_rule{rule_filter};
            $req isa relaxed_requirement,
                has requirement_name $requirement_name,
                has in_effect true;
            let $value = tactic_rule_impacts_requirement_fulfillment($tr, $req);
        fetch {{
            "rule_name": $tr.rule_name,
            "requirement_name": $requirement_name,
            "value": $value
        }};
    """


def expression_case_query(
    function_name: str,
    expression_type: str,
    rule_name: Optional[str] = None,
) -> str:
    """Build a discovery query for one expression-accepting function."""
    rule_filter = ''
    if rule_name is not None:
        rule_filter = f',\n                has rule_name {quote(rule_name)}'
    return f"""
        match
            $tr isa tactic_rule{rule_filter};
            $e isa {expression_type},
                has expression_name $expression_name;
            let $value = {function_name}($tr, $e);
        fetch {{
            "rule_name": $tr.rule_name,
            "expression_name": $expression_name,
            "value": $value
        }};
    """


def measure_case_query(rule_name: Optional[str] = None) -> str:
    """Discovery query for the hypothetical measure helper."""
    rule_filter = ''
    if rule_name is not None:
        rule_filter = f',\n                has rule_name {quote(rule_name)}'
    return f"""
        match
            $tr isa tactic_rule{rule_filter};
            $m isa Measure,
                has measure_name $measure_name;
            let $value = tactic_rule_hypothetical_measure_value($tr, $m);
        fetch {{
            "rule_name": $tr.rule_name,
            "measure_name": $measure_name,
            "value": $value
        }};
    """


def build_function_query(
    function_name: str,
    rule_name: str,
    attribute_name: str,
    attribute_value: str,
    variable_type: str,
    variable_name: str = 'arg',
) -> str:
    """Build the final benchmark query for one representative function."""
    return f"""
        match
            $tr isa tactic_rule,
                has rule_name {quote(rule_name)};
            ${variable_name} isa {variable_type},
                has {attribute_name} {quote(attribute_value)};
            let $value = {function_name}($tr, ${variable_name});
        fetch {{
            "value": $value
        }};
    """


def discover_requirement_pair(
    kb_interface: TacticalRetreatInterface,
) -> Optional[dict]:
    """Discover one valid tactic-rule/requirement pair for the final query."""
    with suppress_probe_logging():
        return query_first_row(kb_interface, requirement_pair_query())


def discover_expression_case(
    kb_interface: TacticalRetreatInterface,
    function_name: str,
    expression_type: str,
    preferred_rule_name: Optional[str],
) -> Optional[dict]:
    """Discover one valid expression case, preferring the representative rule."""
    with suppress_probe_logging():
        if preferred_rule_name is not None:
            row = query_first_row(
                kb_interface,
                expression_case_query(
                    function_name,
                    expression_type,
                    rule_name=preferred_rule_name,
                ),
            )
            if row is not None:
                return row
        return query_first_row(
            kb_interface,
            expression_case_query(function_name, expression_type),
        )


def discover_measure_case(
    kb_interface: TacticalRetreatInterface,
    preferred_rule_name: Optional[str],
) -> Optional[dict]:
    """Discover one valid measure-helper case, preferring the representative rule."""
    with suppress_probe_logging():
        if preferred_rule_name is not None:
            row = query_first_row(
                kb_interface,
                measure_case_query(rule_name=preferred_rule_name),
            )
            if row is not None:
                return row
        return query_first_row(kb_interface, measure_case_query())


def build_cases(
    kb_interface: TacticalRetreatInterface,
    selected_function_names: Optional[set[str]] = None,
    all_inputs: bool = False,
) -> tuple[List[BenchmarkCase], Optional[str]]:
    """
    Build one benchmark case per function.

    When all_inputs=False (default), each case uses a single representative
    (tactic_rule, input) pair — fast, good for warm-latency profiling.

    When all_inputs=True, each case queries all valid (tactic_rule, input)
    combinations — shows real throughput across the full data distribution.
    """
    requirement_row = discover_requirement_pair(kb_interface)
    if requirement_row is None:
        return [], None

    if selected_function_names is None:
        selected_function_names = set(FUNCTION_ORDER)

    representative_rule = requirement_row['rule_name']
    requirement_name = requirement_row['requirement_name']

    cases: List[BenchmarkCase] = []
    if 'tactic_rule_impacts_requirement_fulfillment' in selected_function_names:
        if all_inputs:
            req_query = requirement_pair_query()
            req_description = 'all tactic_rules × all relaxed_requirements'
        else:
            req_query = build_function_query(
                'tactic_rule_impacts_requirement_fulfillment',
                representative_rule,
                'requirement_name',
                requirement_name,
                'relaxed_requirement',
            )
            req_description = (
                f'rule={representative_rule}, requirement={requirement_name}'
            )
        cases.append(
            BenchmarkCase(
                function_name='tactic_rule_impacts_requirement_fulfillment',
                query=req_query,
                input_description=req_description,
            ),
        )

    if 'tactic_rule_hypothetical_measure_value' in selected_function_names:
        if all_inputs:
            cases.append(
                BenchmarkCase(
                    function_name='tactic_rule_hypothetical_measure_value',
                    query=measure_case_query(),
                    input_description='all tactic_rules × all Measures',
                )
            )
        else:
            measure_row = discover_measure_case(kb_interface, representative_rule)
            if measure_row is not None:
                measure_rule_name = measure_row['rule_name']
                measure_name = measure_row['measure_name']
                cases.append(
                    BenchmarkCase(
                        function_name='tactic_rule_hypothetical_measure_value',
                        query=build_function_query(
                            'tactic_rule_hypothetical_measure_value',
                            measure_rule_name,
                            'measure_name',
                            measure_name,
                            'Measure',
                        ),
                        input_description=(
                            f'rule={measure_rule_name}, measure={measure_name}'
                        ),
                    )
                )

    expression_types = {
        'tactic_rule_hypothetical_comparison_lhs_value': 'comparison_expression',
        'tactic_rule_hypothetical_comparison_rhs_value': 'comparison_expression',
        'tactic_rule_impacts_comparison_fulfillment': 'comparison_expression',
        'tactic_rule_hypothetical_fuzzy_term': 'fuzzy_comparison_expression',
        'tactic_rule_impacts_fuzzy_leaf_fulfillment': 'fuzzy_comparison_expression',
        'tactic_rule_hypothetical_relaxed_term': 'relaxed_fuzzy_expression',
        'tactic_rule_impacts_relaxed_leaf_fulfillment': 'relaxed_fuzzy_expression',
        'tactic_rule_impacts_not_membership': 'not_expression',
        'tactic_rule_impacts_fuzzy_not_membership': 'fuzzy_not',
        'tactic_rule_impacts_fuzzy_or_fulfillment': 'fuzzy_or',
        'tactic_rule_impacts_fuzzy_and_fulfillment': 'fuzzy_and',
        'tactic_rule_impacts_may_fulfillment': 'may_expression',
        'tactic_rule_impacts_shall_fulfillment': 'shall_expression',
        'tactic_rule_impacts_any_expression_fulfillment': 'expression',
    }
    for function_name in FUNCTION_ORDER:
        if function_name not in selected_function_names:
            continue
        expression_type = expression_types.get(function_name)
        if expression_type is None:
            continue
        if all_inputs:
            cases.append(
                BenchmarkCase(
                    function_name=function_name,
                    query=expression_case_query(function_name, expression_type),
                    input_description=f'all tactic_rules × all {expression_type}',
                )
            )
        else:
            row = discover_expression_case(
                kb_interface,
                function_name,
                expression_type,
                representative_rule,
            )
            if row is None:
                continue
            row_rule_name = row['rule_name']
            expression_name = row['expression_name']
            cases.append(
                BenchmarkCase(
                    function_name=function_name,
                    query=build_function_query(
                        function_name,
                        row_rule_name,
                        'expression_name',
                        expression_name,
                        expression_type,
                        variable_name='e',
                    ),
                    input_description=(
                        f'rule={row_rule_name}, expression={expression_name}'
                    ),
                )
            )

    ordered_cases = sorted(
        cases,
        key=lambda case: FUNCTION_ORDER.index(case.function_name),
    )
    return ordered_cases, representative_rule


def benchmark_case(
    make_interface: Callable[[], TacticalRetreatInterface],
    warmup_fn: Callable[[TacticalRetreatInterface], None],
    case: BenchmarkCase,
    cold_runs: int,
    true_cold_runs: int,
    warm_runs: int,
    _shared_interface: Optional[TacticalRetreatInterface] = None,
) -> BenchmarkResult:
    """
    Benchmark one function case with relative cold, true cold, and warm runs.

    Relative cold runs (cold_runs):
      Each measurement is taken on a fresh DB that has first been warmed by
      re-running the discovery queries, reproducing the state TypeDB is in
      right after schema load in production.  When cold_runs == 1 and
      _shared_interface is provided, the already-warmed discovery DB is reused
      directly (no extra DB creation).

    True cold runs (true_cold_runs):
      Each measurement is taken on a completely fresh DB with no prior queries,
      representing the absolute worst-case first-query latency.

    Warm runs (warm_runs):
      Repeated queries on the surviving relative-cold DB after all cold
      measurements, representing steady-state latency.
    """
    # --- Relative cold measurements ---
    cold_values: List[float] = []
    row_count = 0

    if _shared_interface is not None:
        # cold_runs == 1: reuse the caller-owned discovery DB (old behavior).
        main_interface = _shared_interface
        cold_start = time.perf_counter()
        cold_rows = main_interface.fetch_database(case.query)
        cold_values.append((time.perf_counter() - cold_start) * 1000.0)
        row_count = len(cold_rows)
        owns_main = False
    else:
        # cold_runs >= 2: fresh DB + warmup for every cold run.
        main_interface = None
        for i in range(cold_runs):
            iface = make_interface()
            warmup_fn(iface)
            cold_start = time.perf_counter()
            cold_rows = iface.fetch_database(case.query)
            cold_values.append((time.perf_counter() - cold_start) * 1000.0)
            row_count = len(cold_rows)
            if i < cold_runs - 1:
                iface.delete_database()
            else:
                main_interface = iface
        owns_main = True

    assert main_interface is not None

    # --- Warm measurements on the surviving relative-cold DB ---
    warm_values: List[float] = []
    for _ in range(warm_runs):
        start = time.perf_counter()
        rows = main_interface.fetch_database(case.query)
        warm_values.append((time.perf_counter() - start) * 1000.0)
        row_count = len(rows)

    if owns_main:
        main_interface.delete_database()

    # --- True cold measurements (independent fresh DBs, no warmup) ---
    true_cold_values: List[float] = []
    for _ in range(true_cold_runs):
        tc_iface = make_interface()
        cold_start = time.perf_counter()
        tc_rows = tc_iface.fetch_database(case.query)
        true_cold_values.append((time.perf_counter() - cold_start) * 1000.0)
        row_count = len(tc_rows)
        tc_iface.delete_database()

    return BenchmarkResult(
        function_name=case.function_name,
        input_description=case.input_description,
        row_count=row_count,
        cold_runs=cold_runs,
        cold_avg_ms=sum(cold_values) / len(cold_values),
        cold_p50_ms=percentile(cold_values, 0.50),
        cold_p95_ms=percentile(cold_values, 0.95),
        true_cold_runs=true_cold_runs,
        true_cold_avg_ms=(
            sum(true_cold_values) / len(true_cold_values) if true_cold_values else 0.0),
        true_cold_p50_ms=percentile(true_cold_values, 0.50) if true_cold_values else 0.0,
        true_cold_p95_ms=percentile(true_cold_values, 0.95) if true_cold_values else 0.0,
        warm_avg_ms=sum(warm_values) / len(warm_values),
        warm_p50_ms=percentile(warm_values, 0.50),
        warm_p95_ms=percentile(warm_values, 0.95),
    )


def print_report(
    results: List[BenchmarkResult],
    representative_rule: Optional[str],
    cold_runs: int,
    true_cold_runs: int,
    warm_runs: int,
    regex_filter: Optional[str],
    all_inputs: bool = False,
) -> None:
    """Print a compact function-level contribution report."""
    print(
        f'Relative cold runs per function: {cold_runs}'
        ' (fresh DB warmed by discovery queries)'
    )
    if true_cold_runs > 0:
        print(
            f'True cold runs per function: {true_cold_runs}'
            ' (fresh DB, no warmup)'
        )
    print(f'Warm runs per function: {warm_runs}')
    if all_inputs:
        print('Input mode: all inputs (all tactic_rules × all valid inputs per function)')
    elif representative_rule is not None:
        print(f'Representative tactic rule: {representative_rule}')
    if regex_filter is not None:
        print(f'Function filter regex: {regex_filter}')
    print('')

    if not results:
        print('No benchmarkable function cases were discovered.')
        return

    final_result = next(
        (
            result for result in results
            if result.function_name == 'tactic_rule_impacts_requirement_fulfillment'
        ),
        None,
    )
    final_warm_p50 = final_result.warm_p50_ms if final_result is not None else None

    if final_result is None:
        print('Function timings sorted by warm p50 (final function not selected)')
    else:
        print(
            'Function timings sorted by warm p50 '
            '(relative percentages use the final requirement function as 100%)'
        )
    for index, result in enumerate(
        sorted(results, key=lambda item: item.warm_p50_ms, reverse=True),
        start=1,
    ):
        relative = ''
        if final_warm_p50 is not None and final_warm_p50 > 0.0:
            relative = (
                f', warm_p50_vs_final={100.0 * result.warm_p50_ms / final_warm_p50:.1f}%'
            )
        true_cold_str = ''
        if result.true_cold_runs > 0:
            true_cold_str = (
                f'true_cold_avg={result.true_cold_avg_ms:.3f}ms, '
                f'true_cold_p50={result.true_cold_p50_ms:.3f}ms, '
                f'true_cold_p95={result.true_cold_p95_ms:.3f}ms, '
            )
        print(
            f'{index:>2}. {result.function_name}: '
            f'cold_avg={result.cold_avg_ms:.3f}ms, '
            f'cold_p50={result.cold_p50_ms:.3f}ms, '
            f'cold_p95={result.cold_p95_ms:.3f}ms, '
            f'{true_cold_str}'
            f'warm_avg={result.warm_avg_ms:.3f}ms, '
            f'warm_p50={result.warm_p50_ms:.3f}ms, '
            f'warm_p95={result.warm_p95_ms:.3f}ms, '
            f'rows={result.row_count}{relative}'
        )
        print(f'    inputs: {result.input_description}')


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            'Benchmark each discover_hypothetical_req_fulfillment function '
            'with one representative case from the benchmark profile.'
        )
    )
    parser.add_argument(
        '--address',
        default='localhost:1729',
        help='TypeDB address (default: localhost:1729).',
    )
    parser.add_argument(
        '--db-name',
        default='benchmark_requirement_functions',
        help='Database name for the benchmark run (default: benchmark_requirement_functions).',
    )
    parser.add_argument(
        '--cold-runs',
        type=int,
        default=1,
        help=(
            'Number of relative cold runs per function. Each run uses a fresh DB '
            'pre-warmed by re-running discovery queries, reproducing the state '
            'TypeDB is in right after schema load in production. Default: 1.'
        ),
    )
    parser.add_argument(
        '--true-cold-runs',
        type=int,
        default=0,
        help=(
            'Number of true cold runs per function. Each run uses a completely '
            'fresh DB with no prior queries, representing worst-case first-query '
            'latency. Default: 0 (disabled).'
        ),
    )
    parser.add_argument(
        '--warm-runs',
        type=int,
        default=5,
        help='Number of warm runs per function after cold runs (default: 5).',
    )
    parser.add_argument(
        '-k',
        '--function-regex',
        default=None,
        help=(
            'Optional regex to select which functions to benchmark. '
            'Example: -k tactic_rule_hypothetical_measure_'
        ),
    )
    parser.add_argument(
        '--all-inputs',
        action='store_true',
        default=False,
        help=(
            'Benchmark each function across all valid (tactic_rule, input) '
            'combinations instead of a single representative pair. '
            'Shows real throughput across the full data distribution. '
            'row_count reflects the total number of results returned.'
        ),
    )
    args = parser.parse_args()

    if args.cold_runs < 1:
        parser.error('--cold-runs must be >= 1')
    if args.true_cold_runs < 0:
        parser.error('--true-cold-runs must be >= 0')
    if args.warm_runs < 1:
        parser.error('--warm-runs must be >= 1')

    selected_function_names = None
    if args.function_regex is not None:
        try:
            pattern = re.compile(args.function_regex)
        except re.error as err:
            parser.error(f'Invalid --function-regex: {err}')
        selected_function_names = {
            function_name
            for function_name in FUNCTION_ORDER
            if pattern.search(function_name)
        }
        if not selected_function_names:
            parser.error(
                'No functions matched --function-regex '
                f'{quote(args.function_regex)}'
            )

    benchmark_queries_module = load_benchmark_queries_module()

    def make_interface() -> TacticalRetreatInterface:
        return TacticalRetreatInterface(
            args.address,
            args.db_name,
            benchmark_queries_module.DEFAULT_SCHEMAS,
            benchmark_queries_module.DATA_PROFILES['benchmark'],
            force_database=True,
            force_data=True,
        )

    kb_interface = make_interface()
    cases, representative_rule = build_cases(
        kb_interface,
        selected_function_names=selected_function_names,
        all_inputs=args.all_inputs,
    )

    def warmup_fn(iface: TacticalRetreatInterface) -> None:
        build_cases(
            iface,
            selected_function_names=selected_function_names,
            all_inputs=args.all_inputs,
        )

    if args.cold_runs == 1:
        # Single relative cold run: reuse the discovery DB directly so the
        # warmup state is identical to what it was before --cold-runs existed.
        try:
            results = [
                benchmark_case(
                    make_interface, warmup_fn, case,
                    args.cold_runs, args.true_cold_runs, args.warm_runs,
                    _shared_interface=kb_interface,
                )
                for case in cases
            ]
        finally:
            kb_interface.delete_database()
    else:
        # Multiple relative cold runs: discard the discovery DB and let
        # benchmark_case create fresh DBs (each warmed by warmup_fn).
        kb_interface.delete_database()
        results = [
            benchmark_case(
                make_interface, warmup_fn, case,
                args.cold_runs, args.true_cold_runs, args.warm_runs,
            )
            for case in cases
        ]

    print_report(
        results,
        representative_rule,
        args.cold_runs,
        args.true_cold_runs,
        args.warm_runs,
        args.function_regex,
        all_inputs=args.all_inputs,
    )


if __name__ == '__main__':
    main()
