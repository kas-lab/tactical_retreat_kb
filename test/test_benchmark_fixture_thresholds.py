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
from pathlib import Path
import uuid

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


ROW_THRESHOLD_METHODS = {
    'fetch_all_expressions',
    'fetch_all_requirements',
    'fetch_all_tactic_rules',
    'fetch_in_effect_requirement_fulfillment',
    'fetch_measures_interfaces',
}
MINIMUM_VALID_COMBINATIONS = 10
MINIMUM_RESULT_ROWS = 10


def load_benchmark_queries_module():
    """Import the benchmark-queries script as a Python module."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / 'scripts'
        / 'benchmark'
        / 'benchmark_queries.py'
    )
    spec = importlib.util.spec_from_file_location(
        'typedb_tactics_benchmark_queries_thresholds',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_benchmark_fixture_meets_fetch_thresholds():
    benchmark_queries_module = load_benchmark_queries_module()
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        f'test_benchmark_fixture_thresholds_{uuid.uuid4().hex}',
        benchmark_queries_module.DEFAULT_SCHEMAS,
        benchmark_queries_module.DATA_PROFILES['benchmark'],
        force_database=True,
        force_data=True,
    )
    try:
        context, context_errors = benchmark_queries_module.resolve_context(
            kb_interface)
        assert context_errors == []

        for method_name in benchmark_queries_module.get_fetch_method_names():
            method = getattr(kb_interface, method_name)
            call_specs = benchmark_queries_module.build_method_calls(
                method_name,
                context,
            )

            valid_combinations = 0
            valid_row_counts = []
            with benchmark_queries_module.suppress_probe_logging():
                for args, kwargs, _call_description in call_specs:
                    try:
                        result = method(*args, **kwargs)
                    except Exception:  # pylint: disable=broad-exception-caught
                        continue

                    valid_combinations += 1
                    valid_row_counts.append(len(result))

                    if (
                        method_name not in ROW_THRESHOLD_METHODS
                        and valid_combinations >= MINIMUM_VALID_COMBINATIONS
                    ):
                        break

            if method_name in ROW_THRESHOLD_METHODS:
                assert valid_row_counts, method_name
                assert all(
                    row_count >= MINIMUM_RESULT_ROWS
                    for row_count in valid_row_counts
                ), f'{method_name}: row_counts={valid_row_counts}'
                continue

            assert (
                valid_combinations >= MINIMUM_VALID_COMBINATIONS
            ), f'{method_name}: valid_combinations={valid_combinations}'
    finally:
        kb_interface.delete_database()
