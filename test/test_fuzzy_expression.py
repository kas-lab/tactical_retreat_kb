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
            'schemas/logical_expressions/fuzzy_expression.tql'],
        ['test/data/test_fuzzy_expression.tql'],
        force_database=True,
        force_data=True)
    yield kb_interface
    kb_interface.delete_database()


def test_fuzzy_logical_expressions(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree(
        'bool_false_prop_exp') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'bool_true_prop_exp') == pytest.approx(1.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'false_measure_prop_exp') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'true_measure_prop_exp') == pytest.approx(1.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'md_0_10_less_v_0_18') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'md_0_20_less_v_0_18') == pytest.approx(0.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'not_false_expr') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'not_true_expr') == pytest.approx(0.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'or_expression_1') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'or_expression_2') == pytest.approx(0.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'and_expression_1') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'and_expression_2') == pytest.approx(0.0)


def test_fuzzy_ascend(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_sigmoid_expression') == pytest.approx(0.913378192)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_exp_saturation_expression') == pytest.approx(0.834700912)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_blf_expression') == pytest.approx(0.947368421)


def test_fuzzy_unimodal(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_triangular_expression') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_gaussian_expression') == pytest.approx(0.931085511)


def test_fuzzy_decay(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_decay_exp_expression') == pytest.approx(0.900009528)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_decay_rational_expression') == pytest.approx(0.8)


def test_fuzzy_membership_offset(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_offset_triangular_expression') == pytest.approx(0.92442)


def test_fuzzy_not(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_0') == pytest.approx(0.086621808)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_1') == pytest.approx(0.2)

    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_2') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_3') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_4') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_not_5') == pytest.approx(1.0)

    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_not_less_than_negated_true') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_not_less_than_negated_false') == pytest.approx(1.0)


def test_fuzzy_or(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_0') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_1') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_2') == pytest.approx(0.947368421)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_3') == pytest.approx(0.2)

    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_4') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_5') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_6') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_or_7') == pytest.approx(0.931085511)


def test_fuzzy_and(kb_interface):
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_0') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_1') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_2') == pytest.approx(0.8)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_3') == pytest.approx(0.086621808)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_4') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_5') == pytest.approx(0.2)

    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_6') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_7') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_8') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_9') == pytest.approx(0.0)

    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_10') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree('fuzzy_and_11') == pytest.approx(0.931085511)


def test_quantified_value_singleton_double_term(kb_interface):
    """ValueSingleton+double_value branch of quantified_value_fuzzy_expression."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_sigmoid_vs_double_expression') == pytest.approx(0.913378192)


def test_quantified_value_singleton_integer_term(kb_interface):
    """ValueSingleton+integer_value branch of quantified_value_fuzzy_expression."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_sigmoid_vs_integer_expression') == pytest.approx(0.913378192)


def test_quantified_value_measure_integer_term(kb_interface):
    """Measure+integer_value branch of quantified_value_fuzzy_expression."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_decay_rational_int_measure_expression') == pytest.approx(0.8)


def test_fuzzy_triangular_out_of_range(kb_interface):
    """Triangular membership below (x<a) and above (x>c) range branches."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_triangular_below_expression') == pytest.approx(0.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_triangular_above_expression') == pytest.approx(0.0)


def test_fuzzy_triangular_peak(kb_interface):
    """Triangular and Gaussian membership at peak (x=b=center=0.0)."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_triangular_peak_expression') == pytest.approx(1.0)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_unimodal_gaussian_peak_expression') == pytest.approx(1.0)


def test_fuzzy_membership_offset_ascend(kb_interface):
    """offset_value on fuzzy_ascend_expression shifts the quantified input."""
    # exponent=0.2, x=9.0, offset=-4.0 → quantified=5.0
    # m = 1 - e^(-0.2*5.0) = 1 - e^(-1.0) ≈ 0.632120559
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_ascend_exp_sat_offset_expression') == pytest.approx(0.632120559)


def test_fuzzy_membership_offset_decay(kb_interface):
    """offset_value on fuzzy_decay_expression shifts the quantified input."""
    # curvature=2000, x=500, offset=1500 → quantified=2000
    # m = 2000 / (2000 + 2000) = 0.5
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_decay_rational_offset_expression') == pytest.approx(0.5)


def test_fuzzy_not_unimodal(kb_interface):
    """fuzzy_not wrapping fuzzy_unimodal_expression (triangular and gaussian)."""
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_not_unimodal_triangular') == pytest.approx(0.07558)
    assert kb_interface.get_fuzzy_membership_degree(
        'fuzzy_not_unimodal_gaussian') == pytest.approx(0.068914489)
