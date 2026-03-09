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

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/logical_expressions/fuzzy_expression.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/relaxed/relaxed_model.tql'],
        ['schemas/ros_model/ros_model_example.tql',  # required for relax_mirte_example
         'schemas/tactics_model/tactics_example.tql',  # required for relax_mirte_example
         'schemas/relaxed/relaxed_mirte_example.tql',
         'schemas/relaxed/relaxed_paper_example.tql',
         'test/data/test_relaxed_model.tql'],
        force_database=True,
        force_data=True)
    yield kb_interface
    kb_interface.delete_database()


def test_get_relaxed_expr_fulfillment(kb_interface):
    fulfillment_array = kb_interface.fetch_relaxed_expression_fulfillment(
        'fake_may_expression')
    assert len(fulfillment_array) == 1

    fulfillment = kb_interface.get_relaxed_expression_fulfillment(
        'fake_may_expression')
    assert fulfillment == pytest.approx(0.92442)

    fulfillment_array = kb_interface.fetch_relaxed_expression_fulfillment(
        'fake_shall_expression')
    assert len(fulfillment_array) == 1

    fulfillment = kb_interface.get_relaxed_expression_fulfillment(
        'fake_shall_expression')
    assert fulfillment == pytest.approx(0.900009528)

    # Mirte model
    fulfillment_array = kb_interface.fetch_relaxed_expression_fulfillment(
        'velocity_shall_expression')
    assert len(fulfillment_array) == 1

    fulfillment = kb_interface.get_relaxed_expression_fulfillment(
        'velocity_shall_expression')
    assert fulfillment == pytest.approx(0.92442)

    fulfillment_array = kb_interface.fetch_relaxed_expression_fulfillment(
        'velocity_as_close_expression_2')
    assert len(fulfillment_array) == 1

    fulfillment = kb_interface.get_relaxed_expression_fulfillment(
        'velocity_as_close_expression_2')
    assert fulfillment == pytest.approx(0.91558)

    fulfillment_array = kb_interface.fetch_relaxed_expression_fulfillment(
        'velocity_shall_expression_2')
    assert len(fulfillment_array) == 1

    fulfillment = kb_interface.get_relaxed_expression_fulfillment(
        'velocity_shall_expression_2')
    assert fulfillment == pytest.approx(0.91558)


def test_get_requirement_fulfillment_test_model(kb_interface):

    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'system', 'req_1')
    assert fulfillment == pytest.approx(0.92442)


def test_get_requirement_fulfillment_mirte(kb_interface):
    # Mirte example model
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'R1.1 Velocity')
    assert fulfillment == pytest.approx(0.92442)

    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'R1.2 Velocity with obstacles')
    assert fulfillment == pytest.approx(0.91558)

    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'R1.3 Movement Power')
    assert fulfillment == pytest.approx(0.941764572)


def test_get_requirement_fulfillment_relax_paper(kb_interface):
    # RELAX paper example model
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Smart House', 'R1.1 As many food as possible')
    assert fulfillment == pytest.approx(0.913378192)

    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Smart House', 'R1.2 Dietplan')
    assert fulfillment == pytest.approx(0.980198686)

    # fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
    #     'Smart House', 'R1.3 Liquid intake')
    # assert fulfillment == pytest.approx(0.980198686)

    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Smart House', 'R1.4 Energy comsumption')
    assert fulfillment == pytest.approx(0.900009528)


def test_get_in_effect_requirement_fulfillment(kb_interface):
    req_fulfillment_array = kb_interface.get_in_effect_requirement_fulfillment()

    assert req_fulfillment_array[0]['requirement_name'] == 'R1.1 Velocity'
    assert req_fulfillment_array[0]['fulfillment'] == pytest.approx(0.92442)


def test_set_requirement_in_effect(kb_interface):
    assert kb_interface.get_requirement_in_effect('fake_req') is False
    kb_interface.set_requirement_in_effect('fake_req', True)
    assert kb_interface.get_requirement_in_effect('fake_req') is True
    kb_interface.set_requirement_in_effect('fake_req', False)
    assert kb_interface.get_requirement_in_effect('fake_req') is False


def test_leaf_fulfillment_branches(kb_interface):
    # triangular descending branch: q=0.3 ∈ (b=0, c=0.5] → (0.5-0.3)/0.5 = 0.4
    assert kb_interface.get_relaxed_expression_fulfillment(
        'acap_tri_descending') == pytest.approx(0.4)

    # triangular below branch: q=-1.0 < a=-0.5 → 0.0
    assert kb_interface.get_relaxed_expression_fulfillment(
        'acap_tri_below') == pytest.approx(0.0, abs=1e-9)

    # triangular above branch: q=1.0 > c=0.5 → 0.0
    assert kb_interface.get_relaxed_expression_fulfillment(
        'acap_tri_above') == pytest.approx(0.0, abs=1e-9)

    # ValueSingleton+integer term with required_value offset
    # q = 0 - 0.25 = -0.25, ascending branch → (−0.25−(−0.5))/(0−(−0.5)) = 0.5
    assert kb_interface.get_relaxed_expression_fulfillment(
        'acap_vs_int') == pytest.approx(0.5)

    # freq_as_close_as_possible_expression with required_period offset
    # q = 0.6 − 0.5 = 0.1 ∈ (0,1] → (1−0.1)/1 = 0.9
    assert kb_interface.get_relaxed_expression_fulfillment(
        'fcap_triangular_expr') == pytest.approx(0.9)

    # as_many_as_possible_expression + FuzzyExponentialSaturation
    # q=1.0, m = 1 − 2.71828^(−2) ≈ 0.86466
    assert kb_interface.get_relaxed_expression_fulfillment(
        'amap_expsat_expr') == pytest.approx(0.86466, rel=1e-3)

    # as_many_as_possible_expression + FuzzyBoundedLinearFraction + Measure+integer
    # q=7.0, m = 7/(7+3) = 0.7
    assert kb_interface.get_relaxed_expression_fulfillment(
        'amap_blf_expr') == pytest.approx(0.7)

    # as_late_as_possible_expression + FuzzySigmoid
    # q=2.0, m = 1/(1 + 2.71828^(−2)) ≈ 0.88080
    assert kb_interface.get_relaxed_expression_fulfillment(
        'alap_sigmoid_expr') == pytest.approx(0.88080, rel=1e-3)

    # as_early_as_possible_expression + FuzzyExponentialDecay
    # q=1.0, m = 2.71828^(−1) ≈ 0.36788
    assert kb_interface.get_relaxed_expression_fulfillment(
        'aeap_expdecay_expr') == pytest.approx(0.36788, rel=1e-3)

    # as_few_as_possible_expression + FuzzyRationalDecay + ValueSingleton+integer
    # q=6.0, m = 4/(6+4) = 0.4
    assert kb_interface.get_relaxed_expression_fulfillment(
        'afap_rational_expr') == pytest.approx(0.4)


def test_compound_expression_branches(kb_interface):
    # shall_expression with fuzzy_not member (relaxed_fuzzy_expression inner)
    # relaxed_fuzzy_not_fulfillment branch 1 + shall branch 4
    # 1.0 − 0.92442 = 0.07558
    assert kb_interface.get_relaxed_expression_fulfillment(
        'shall_not_expr') == pytest.approx(0.07558, rel=1e-3)

    # shall_expression with may_expression member — shall branch 5
    # may_expression_fulfillment(fake_may_expression) = 0.92442
    assert kb_interface.get_relaxed_expression_fulfillment(
        'shall_with_may_expr') == pytest.approx(0.92442)

    # may_expression with logical_expression member — may branch 2
    # logical_expression_membership(bool_prop_expr) = 1.0
    assert kb_interface.get_relaxed_expression_fulfillment(
        'may_with_logical_expr') == pytest.approx(1.0)
