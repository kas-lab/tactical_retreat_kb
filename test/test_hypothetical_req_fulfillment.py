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

import time

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import RequirementImpactDict
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def fetch_tactic_rule_dependency_fulfillment(
        self, expression_name, tactic_rule_name):
    query = f"""
            match
                $expr isa expression,
                    has expression_name '{expression_name}';
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                $tr_dependency (dependent: $expr, tactic_rule: $tr) isa tactic_rule_dependency;
            fetch
                $tr_dependency: fulfillment;
        """
    query_result = self.fetch_database(query)
    return query_result


def fetch_tactic_rule_effect_resulting_values(
        self, expression_name, tactic_rule_name):
    query = f"""
            match
                $expr isa expression,
                    has expression_name '{expression_name}';
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                $tr_dependency (dependent: $expr, tactic_rule: $tr) isa tactic_rule_dependency;
                $tr (effect: $effect) isa tactic_rule;
                $effect (measure: $measure) isa effect;
            fetch
                $effect: resulting_effect_value;
                $measure: measure_name;
        """
    query_result = self.fetch_database(query)
    return query_result


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
            'schemas/discover_hypothetical_req_fulfillment/'
            'discover_hypothetical_req_fulfillment.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['test/data/test_discover_hypothetical_req_fulfillment.tql',
         'schemas/ros_model/ros_model_example.tql',
         'schemas/tactics_model/tactics_example.tql',
         'schemas/relaxed/relaxed_mirte_example.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    kb_interface.register_method(
        'fetch_tactic_rule_dependency_fulfillment',
        fetch_tactic_rule_dependency_fulfillment)
    kb_interface.register_method(
        'fetch_tactic_rule_effect_resulting_values',
        fetch_tactic_rule_effect_resulting_values)
    yield kb_interface
    kb_interface.delete_database()


def test_tactic_rule_dependency_comparison_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_abs_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_rel_effect_measure_rhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_abs_effect_measure_rhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_abs_effect_measure_lhs_rhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal_2', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal_2', 'tactic_rule_abs_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_lhs_0_20_rhs_0_10')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 0.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_lhs_0_15_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 0.0

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'less_than_equal', 'tactic_rule_lhs_0_10_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == 0.0


def test_tactic_rule_dependency_fuzzy_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_unimodal_triangular_expression', 'tactic_rule_unimodal_meas_0_04779')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.90442)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_unimodal_gaussian_expression', 'tactic_rule_unimodal_meas_0_04779')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.89208476)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_decay_exp_expression', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.89057770)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_decay_rational_expression', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.784313725)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_ascend_sigmoid_expression', 'tactic_rule_ascend_meas_10')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.950002804)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_ascend_exp_saturation_expression', 'tactic_rule_ascend_meas_10')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.864664535)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fuzzy_ascend_blf_expression', 'tactic_rule_ascend_meas_10')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.952380952)


def test_tactic_rule_dependency_relaxed_fuzzy_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_close_expression', 'tactic_rule_as_close_as_meas_0_27221')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.97558)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_close_expression', 'tactic_rule_as_close_as_meas_0_20')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.88)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_many_as_possible', 'tactic_rule_as_many_as_meas_10')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.950002804)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_many_as_possible', 'tactic_rule_as_many_as_meas_7')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.764551865)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_few_as_possible', 'tactic_rule_as_few_as_meas_0_08')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.984127331)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'fake_as_few_as_possible', 'tactic_rule_as_few_as_meas_0_15')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.970445553)

    # Relax Mirte example
    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'velocity_as_close_expression_2', 'MIN')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.84)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'velocity_as_close_expression_2', 'MED')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'velocity_as_close_expression_2', 'MAX')
    assert len(fulfillment_query_res[0]['tr_dependency']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value'] == pytest.approx(
        0.84)


def test_tactic_rule_impacts_not_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'not_expr', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'not_expr', 'tactic_rule_lhs_0_10_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    # non-related tactic_rule
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'not_expr', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_not', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_not', 'tactic_rule_lhs_0_10_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    # non-related tactic_rule
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_not', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)


def test_tactic_rule_impacts_or_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_1', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_1', 'tactic_rule_lhs_0_10_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    # non-related tactic_rule
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_1', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_2', 'tactic_rule_as_close_as_meas_0_27221')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.97558)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_2', 'tactic_rule_as_many_as_meas_10')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.950002804)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_2', 'tactic_rule_as_few_as_meas_0_08')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.984127331)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_or_2', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.941764572)


def test_tactic_rule_impacts_and_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_1', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_1', 'tactic_rule_lhs_0_10_rhs_0_05')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    # non-related tactic_rule
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_1', 'tactic_rule_decay_meas_550')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_2', 'tactic_rule_as_close_as_meas_0_27221')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.913378192)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_2', 'tactic_rule_as_many_as_meas_10')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.92442)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_2', 'tactic_rule_as_few_as_meas_0_08')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.913378192)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fuzzy_and_2', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.913378192)


def test_tactic_rule_impacts_shall_expr_fulfillment(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fake_shall_expression', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.913378192)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'fake_shall_expression', 'tactic_rule_as_close_as_meas_0_27221')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'velocity_shall_expression_2', 'MIN')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.84)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'velocity_shall_expression_2', 'MED')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'velocity_shall_expression_2', 'MAX')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.84)


def test_tactic_impacts_requirement(kb_interface):
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'req_1', 'tactic_rule_rel_effect_measure_lhs')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.913378192)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'req_1', 'tactic_rule_as_close_as_meas_0_27221')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.0)

    # Relax Mirte example
    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.1 Velocity', 'MIN')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.68)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.1 Velocity', 'MED')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.84)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.1 Velocity', 'MAX')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.2 Velocity with obstacles', 'MIN')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.84)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.2 Velocity with obstacles', 'MED')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        1.0)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.2 Velocity with obstacles', 'MAX')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.84)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.3 Movement Power', 'MIN')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.932393864)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.3 Movement Power', 'MED')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.92867174)

    fulfillment_query_res = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'R1.3 Movement Power', 'MAX')
    assert len(fulfillment_query_res[0]['tr_impacts']['fulfillment']) == 1
    assert fulfillment_query_res[0]['tr_impacts']['fulfillment'][0]['value'] == pytest.approx(
        0.923116396)


def test_potential_requirements_fulfillment(kb_interface):
    start_time = time.time()
    result = kb_interface.get_potential_requirements_fulfillment(
        '/navigate_to_pose')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Execution time: {elapsed_time:.2f} seconds', flush=True)

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
        requirement_name='R1.2 Velocity with obstacles',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.84)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Velocity with obstacles',
        tactic_rule='MED',
        fulfillment=pytest.approx(1.0)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Velocity with obstacles',
        tactic_rule='MAX',
        fulfillment=pytest.approx(0.84)) in result

    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.3 Movement Power',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.932393864)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.3 Movement Power',
        tactic_rule='MED',
        fulfillment=pytest.approx(0.92867174)) in result
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.3 Movement Power',
        tactic_rule='MAX',
        fulfillment=pytest.approx(0.923116396)) in result

    result_with_resolution_model = kb_interface.get_potential_requirements_fulfillment(
        '/navigate_to_pose',
        resolution_model='rebetmc')
    assert len(result_with_resolution_model) == len(result)
    for impact in result:
        assert impact in result_with_resolution_model
