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
import inspect
import logging
from pathlib import Path
import uuid

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def load_benchmark_module():
    """Import the benchmark script as a Python module for direct testing."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / 'scripts'
        / 'benchmark'
        / 'benchmark.py'
    )
    spec = importlib.util.spec_from_file_location(
        'typedb_tactics_benchmark_script',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def benchmark_module():
    return load_benchmark_module()


@pytest.fixture(scope='module')
def kb_interface(benchmark_module):
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        f'test_benchmark_script_{uuid.uuid4().hex}',
        benchmark_module.DEFAULT_SCHEMAS,
        benchmark_module.DEFAULT_DATA,
        force_database=True,
        force_data=True,
    )
    yield kb_interface
    kb_interface.delete_database()


def get_method_names():
    """Return all benchmarked get_* method names from the interface."""
    return sorted(
        name for name, func in inspect.getmembers(
            TacticalRetreatInterface,
            predicate=inspect.isfunction,
        )
        if (
            name.startswith('get_')
            and func.__qualname__.startswith('TacticalRetreatInterface.')
        )
    )


def test_resolve_context_discovers_pairs(benchmark_module, kb_interface):
    context, context_errors = benchmark_module.resolve_context(kb_interface)

    assert context_errors == []
    assert context['applicable_pairs']
    assert context['effect_pairs']


def test_build_method_calls_covers_all_get_methods(benchmark_module, kb_interface):
    context, _ = benchmark_module.resolve_context(kb_interface)

    for method_name in get_method_names():
        call_specs = benchmark_module.build_method_calls(method_name, context)
        assert call_specs, method_name


def test_benchmark_get_methods_skips_no_methods(benchmark_module, kb_interface):
    context, _ = benchmark_module.resolve_context(kb_interface)

    (
        benchmark_results,
        skipped_methods,
        error_methods,
        unknown_selected_methods,
        _filtered_methods,
    ) = benchmark_module.benchmark_get_methods(
        kb_interface,
        runs=1,
        context=context,
    )

    benchmarked_methods = {
        result['method_name']
        for result in benchmark_results
    }

    assert skipped_methods == []
    assert error_methods == []
    assert unknown_selected_methods == []
    assert benchmarked_methods == set(get_method_names())


def test_invalid_probe_filtering_is_silent(
        benchmark_module, kb_interface, caplog):
    context, _ = benchmark_module.resolve_context(kb_interface)

    caplog.set_level(logging.ERROR)
    benchmark_module.benchmark_get_methods(
        kb_interface,
        runs=1,
        context=context,
    )

    noisy_records = [
        record for record in caplog.records
        if record.name in benchmark_module.PROBE_LOGGERS
    ]
    assert noisy_records == []
