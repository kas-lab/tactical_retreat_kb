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

import importlib.util
import logging
from pathlib import Path
import uuid

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def load_benchmark_queries_module():
    """Import the benchmark-queries script as a Python module."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / 'scripts'
        / 'benchmark'
        / 'benchmark_queries.py'
    )
    spec = importlib.util.spec_from_file_location(
        'typedb_tactics_benchmark_queries_script',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def benchmark_queries_module():
    return load_benchmark_queries_module()


def test_resolve_data_paths_supports_profiles_and_override(
        benchmark_queries_module):
    profile_name, data_paths = benchmark_queries_module.resolve_data_paths(
        'benchmark',
        None,
    )
    assert profile_name == 'benchmark'
    assert data_paths == benchmark_queries_module.DATA_PROFILES['benchmark']

    profile_name, data_paths = benchmark_queries_module.resolve_data_paths(
        'legacy',
        None,
    )
    assert profile_name == 'legacy'
    assert data_paths == benchmark_queries_module.DATA_PROFILES['legacy']

    override_path = str(
        Path(benchmark_queries_module.DATA_PROFILES['benchmark'][0]).resolve())
    profile_name, data_paths = benchmark_queries_module.resolve_data_paths(
        'legacy',
        override_path,
    )
    assert profile_name == 'custom'
    assert data_paths == [override_path]

    profile_name, data_paths = benchmark_queries_module.resolve_data_paths(
        'legacy',
        'scripts/benchmark/benchmark.tql',
    )
    assert profile_name == 'custom'
    assert data_paths == [str((
        Path(benchmark_queries_module.REPO_DIR)
        / 'scripts/benchmark/benchmark.tql').resolve())]


@pytest.fixture(params=['benchmark', 'legacy'])
def data_profile(request):
    return request.param


@pytest.fixture
def kb_interface(benchmark_queries_module, data_profile):
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        f'test_benchmark_queries_script_{data_profile}_{uuid.uuid4().hex}',
        benchmark_queries_module.DEFAULT_SCHEMAS,
        benchmark_queries_module.DATA_PROFILES[data_profile],
        force_database=True,
        force_data=True,
    )
    yield kb_interface
    kb_interface.delete_database()


@pytest.fixture
def benchmark_kb_interface(benchmark_queries_module):
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        f'test_benchmark_queries_thresholds_{uuid.uuid4().hex}',
        benchmark_queries_module.DEFAULT_SCHEMAS,
        benchmark_queries_module.DATA_PROFILES['benchmark'],
        force_database=True,
        force_data=True,
    )
    yield kb_interface
    kb_interface.delete_database()


def test_resolve_context_discovers_core_inputs(
        benchmark_queries_module, kb_interface):
    context, context_errors = benchmark_queries_module.resolve_context(kb_interface)

    assert context_errors == []
    assert context['nodes']
    assert context['resolution_models']
    assert context['interface_names']
    assert context['requirement_names']
    assert context['tactic_rule_names']
    assert context['measure_names']
    assert context['expression_names']
    assert context['applicable_pairs']
    assert context['effect_pairs']


def test_build_method_calls_covers_all_fetch_methods(
        benchmark_queries_module, kb_interface):
    context, _ = benchmark_queries_module.resolve_context(kb_interface)

    for method_name in benchmark_queries_module.get_fetch_method_names():
        call_specs = benchmark_queries_module.build_method_calls(
            method_name,
            context,
        )
        assert call_specs, method_name


def test_benchmark_fetch_methods_runs_all_methods(
        benchmark_queries_module, kb_interface):
    context, _ = benchmark_queries_module.resolve_context(kb_interface)

    (
        benchmark_results,
        skipped_methods,
        error_methods,
        unknown_selected_methods,
        _filtered_methods,
    ) = benchmark_queries_module.benchmark_fetch_methods(
        kb_interface,
        runs=1,
        context=context,
        max_combinations=1,
    )

    benchmarked_methods = {
        result['method_name']
        for result in benchmark_results
    }

    assert skipped_methods == []
    assert error_methods == []
    assert unknown_selected_methods == []
    assert benchmarked_methods == set(
        benchmark_queries_module.get_fetch_method_names())


def test_invalid_probe_filtering_is_silent(
        benchmark_queries_module, kb_interface, caplog):
    context, _ = benchmark_queries_module.resolve_context(kb_interface)

    caplog.set_level(logging.ERROR)
    benchmark_queries_module.benchmark_fetch_methods(
        kb_interface,
        runs=1,
        context=context,
        max_combinations=1,
    )

    noisy_records = [
        record for record in caplog.records
        if record.name in benchmark_queries_module.PROBE_LOGGERS
    ]
    assert noisy_records == []


def test_benchmark_profile_has_threshold_fetch_coverage(
        benchmark_queries_module, benchmark_kb_interface):
    context, context_errors = benchmark_queries_module.resolve_context(
        benchmark_kb_interface)
    assert context_errors == []

    # Methods with bounded argument space are validated via row-count.
    row_threshold_methods = {
        'fetch_all_tactic_rules',
        'fetch_in_effect_requirement_fulfillment',
        'fetch_all_requirements',
        'fetch_all_expressions',
        'fetch_measures_interfaces',
    }
    failures = []
    with benchmark_queries_module.suppress_probe_logging():
        for method_name in benchmark_queries_module.get_fetch_method_names():
            call_specs = benchmark_queries_module.build_method_calls(
                method_name,
                context,
            )
            valid_combinations = 0
            method = getattr(benchmark_kb_interface, method_name)
            for args, kwargs, _ in call_specs:
                try:
                    method(*args, **kwargs)
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
                valid_combinations += 1
                if method_name not in row_threshold_methods and valid_combinations >= 10:
                    break

            if method_name in row_threshold_methods:
                row_count = len(method())
                if row_count < 10:
                    failures.append(
                        f'{method_name}: expected >=10 rows, got {row_count}')
                continue

            if valid_combinations < 10:
                failures.append(
                    f'{method_name}: expected >=10 valid combinations, '
                    f'got {valid_combinations}')

    assert failures == []
