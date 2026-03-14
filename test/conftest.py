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

import os
from pathlib import Path

import pytest


BENCHMARK_TEST_FILES = {
    'test_benchmark_fixture_thresholds.py',
    'test_benchmark_queries_script.py',
    'test_benchmark_script.py',
}


def pytest_collection_modifyitems(config, items):
    """Keep benchmark validation tests out of the default package test run."""
    benchmark_items = [
        item for item in items
        if Path(str(item.fspath)).name in BENCHMARK_TEST_FILES
    ]
    if not benchmark_items:
        return

    benchmark_marker = pytest.mark.benchmark_slow
    for item in benchmark_items:
        item.add_marker(benchmark_marker)

    run_benchmark_tests = (
        os.environ.get('TYPEDB_TACTICS_RUN_BENCHMARK_TESTS', '') == '1'
    )
    benchmark_only_run = len(benchmark_items) == len(items)
    if run_benchmark_tests or benchmark_only_run:
        return

    skip_marker = pytest.mark.skip(
        reason=(
            'benchmark validation tests are opt-in for the default package '
            'suite; run the benchmark test files directly or set '
            'TYPEDB_TACTICS_RUN_BENCHMARK_TESTS=1'
        )
    )
    for item in benchmark_items:
        item.add_marker(skip_marker)
