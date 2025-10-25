# Copyright 2025 KAS Lab
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

import math
import pytest
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_tactics_model',
        ['typedb/ros_model/ros_model.tql',
            'typedb/tactics_model/tactics_model.tql'],
        ['test/data/test_tactics_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_measurement_latest(kb_interface):
    measurement = kb_interface.get_latest_measurement('measure')
    assert measurement == 1.2

    measurement = kb_interface.get_latest_measurement('measure_no_measurement')
    assert math.isnan(measurement)

    measurement = kb_interface.get_latest_measurement(
        'measure_no_valid_measurement')
    assert math.isnan(measurement)


def test_ineq_expression_valid(kb_interface):
    assert kb_interface.get_ineq_expression_valid('measure', '<', 1.3) is True
    assert kb_interface.get_ineq_expression_valid('measure', '<', 1.2) is False
    assert kb_interface.get_ineq_expression_valid('measure', '<', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '<', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '<', 1.0) is False

    assert kb_interface.get_ineq_expression_valid('measure', '<=', 1.3) is True
    assert kb_interface.get_ineq_expression_valid('measure', '<=', 1.2) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure', '<=', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '<=', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '<=', 1.0) is False

    assert kb_interface.get_ineq_expression_valid('measure', '>', 1.3) is False
    assert kb_interface.get_ineq_expression_valid('measure', '>', 1.2) is False
    assert kb_interface.get_ineq_expression_valid('measure', '>', 1.0) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '>', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '>', 1.0) is False

    assert kb_interface.get_ineq_expression_valid(
        'measure', '>=', 1.3) is False
    assert kb_interface.get_ineq_expression_valid('measure', '>=', 1.2) is True
    assert kb_interface.get_ineq_expression_valid('measure', '>=', 1.0) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '>=', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '>=', 1.0) is False

    assert kb_interface.get_ineq_expression_valid(
        'measure', '==', 1.3) is False
    assert kb_interface.get_ineq_expression_valid('measure', '==', 1.2) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure', '==', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '==', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '==', 1.0) is False

    assert kb_interface.get_ineq_expression_valid('measure', '!=', 1.3) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure', '!=', 1.2) is False
    assert kb_interface.get_ineq_expression_valid('measure', '!=', 1.0) is True
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_measurement', '!=', 1.0) is False
    assert kb_interface.get_ineq_expression_valid(
        'measure_no_valid_measurement', '!=', 1.0) is False


def test_get_tactic_rule_valid(kb_interface):
    assert kb_interface.get_tactic_rule_valid('tr1') is True
    assert kb_interface.get_tactic_rule_valid('tr2') is False
    assert kb_interface.get_tactic_rule_valid('tr3') is False
    assert kb_interface.get_tactic_rule_valid('tr4') is True
    assert kb_interface.get_tactic_rule_valid('tr5') is True
    assert kb_interface.get_tactic_rule_valid('tr6') is True
    assert kb_interface.get_tactic_rule_valid('tr7') is False


@pytest.fixture
def kb_interface_example():
    kb_interface_example = TacticalRetreatInterface(
        'localhost:1729',
        'test_tactics_example_model',
        ['typedb/ros_model/ros_model.tql',
            'typedb/tactics_model/tactics_model.tql',
            'typedb/feature_model/feature_model.tql'],
        ['typedb/ros_model/ros_model_example.tql',
            'typedb/tactics_model/tactics_example.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface_example
    kb_interface_example.delete_database()


def test_tactic_min_valid(kb_interface_example):
    assert kb_interface_example.get_tactic_rule_valid('MIN')
