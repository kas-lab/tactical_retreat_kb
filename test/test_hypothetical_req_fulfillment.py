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

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import RequirementImpactDict
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_hypothetical_req_fulfillment',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/logical_expressions/fuzzy_expression.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/relaxed/relaxed_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql',
            'schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql'],
        ['schemas/ros_model/ros_model_example.tql',
            'schemas/tactics_model/tactics_example.tql',
            'schemas/relaxed/relaxed_mirte_example.tql',
            'test/data/test_tactics_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


# def test_get_requirement_measure_dependency(kb_interface):
#     measures = kb_interface.get_requirement_measure_dependency('R1.1 Velocity')
#     assert 'velocity_measure' in measures

#     measures = kb_interface.get_requirement_measure_dependency('R1.2 Movement Power')
#     assert 'movement_power_measure' in measures

#     measures = kb_interface.get_requirement_measure_dependency('R1.3 Liquid intake')
#     assert 'liquid_intake_measure' in measures
#     assert 'minimum_liquid_intake_measure' in measures

def test_tactic_impacts_requirement(kb_interface):
    requirements = kb_interface.get_tactic_impacts_requirement('MIN')
    assert 'R1.1 Velocity' in requirements
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('MED')
    assert 'R1.1 Velocity' in requirements
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('MAX')
    assert 'R1.1 Velocity' in requirements
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('tr_variant_resolution_feasible')
    assert len(requirements) == 0


def test_get_resulting_effect_value(kb_interface):
    effect_value = kb_interface.get_resulting_effect_value('MIN', 'movement_power_measure')
    assert effect_value == 0.3 + 0.05

    effect_value = kb_interface.get_resulting_effect_value('MED', 'movement_power_measure')
    assert effect_value == 0.3 + 0.07

    effect_value = kb_interface.get_resulting_effect_value('MAX', 'movement_power_measure')
    assert effect_value == 0.3 + 0.10


def test_get_relaxed_requirement_hypothetical_fulfillment(kb_interface):
    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.1 Velocity', 'MIN')
    assert fulfillment == pytest.approx(0.68)

    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.1 Velocity', 'MED')
    assert fulfillment == pytest.approx(0.84)

    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.1 Velocity', 'MAX')
    assert fulfillment == pytest.approx(1.0)

    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.2 Movement Power', 'MIN')
    assert fulfillment == pytest.approx(0.932393864)

    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.2 Movement Power', 'MED')
    assert fulfillment == pytest.approx(0.92867174)

    fulfillment = kb_interface.get_relaxed_requirement_hypothetical_fulfillment(
        'Mirte', 'R1.2 Movement Power', 'MAX')
    assert fulfillment == pytest.approx(0.923116396)


def test_potential_requirements_fulfillment(kb_interface):
    result = kb_interface.get_potential_requirements_fulfillment('/navigate_to_pose')

    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.68)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MED',
        fulfillment=pytest.approx(0.84)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MAX',
        fulfillment=pytest.approx(1.0)) in result

    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.932393864)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MED',
        fulfillment=pytest.approx(0.92867174)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MAX',
        fulfillment=pytest.approx(0.923116396)) in result
