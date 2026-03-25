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


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_tactics_model',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/feature_model/feature_model_logical_expression.tql',
            'schemas/tactics_model/tactics_model.tql'],
        ['test/data/test_tactics_model.tql',
         'schemas/ros_model/ros_model_example.tql',
            'schemas/tactics_model/tactics_example.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
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


def test_get_tactic_rule_valid(kb_interface):
    assert kb_interface.get_tactic_rule_valid('tr1') is True
    assert kb_interface.get_tactic_rule_valid('tr2') is False
    assert kb_interface.get_tactic_rule_valid('tr3') is False
    assert kb_interface.get_tactic_rule_valid('tr4') is True
    assert kb_interface.get_tactic_rule_valid('tr5') is True
    assert kb_interface.get_tactic_rule_valid('tr6') is True
    assert kb_interface.get_tactic_rule_valid('tr7') is False

    assert kb_interface.get_tactic_rule_valid('tr_consequent_feasible') is True
    assert kb_interface.get_tactic_rule_valid('tr_consequent_unfeasible') is False

    assert kb_interface.get_tactic_rule_valid('tr_variant_resolution_feasible') is True
    assert kb_interface.get_tactic_rule_valid('tr_variant_resolution_unfeasible_1') is False
    assert kb_interface.get_tactic_rule_valid('tr_variant_resolution_unfeasible_2') is False


def test_set_nodes_parameters_feasible(kb_interface):
    assert kb_interface.is_set_nodes_parameters_feasible(
        'node_running', 'parameter') is True
    assert kb_interface.is_set_nodes_parameters_feasible(
        'node_not_running', 'parameter') is False


def test_set_lifecycle_state_feasible(kb_interface):
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_active', 'active') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_active', 'inactive') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_active', 'unconfigured') is False
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_active', 'finalized') is True

    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_inactive', 'active') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_inactive', 'inactive') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_inactive', 'unconfigured') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_inactive', 'finalized') is True

    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_unconfigured', 'active') is False
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_unconfigured', 'inactive') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_unconfigured', 'unconfigured') is True
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_unconfigured', 'finalized') is True

    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_finalized', 'active') is False
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_finalized', 'inactive') is False
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_finalized', 'unconfigured') is False
    assert kb_interface.is_set_lifecycle_state_feasible(
        'lifecycle_node_finalized', 'finalized') is True


def test_tactic_min_valid(kb_interface):
    assert kb_interface.get_tactic_rule_valid('MIN')


def test_get_resulting_effect_value(kb_interface):
    effect_value = kb_interface.get_resulting_effect_value('MIN', 'movement_power_measure')
    assert effect_value == 0.3 + 0.05

    effect_value = kb_interface.get_resulting_effect_value('MED', 'movement_power_measure')
    assert effect_value == 0.3 + 0.07

    effect_value = kb_interface.get_resulting_effect_value('MAX', 'movement_power_measure')
    assert effect_value == 0.3 + 0.10
