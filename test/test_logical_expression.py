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
         'schemas/logical_expressions/logical_expression.tql'],
        ['test/data/test_logical_expression.tql',
         'test/data/test_logical_expression_compound.tql'],
        force_database=True,
        force_data=True)
    yield kb_interface
    kb_interface.delete_database()


def test_propositional_expression_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('bool_false_prop_exp') is False
    assert kb_interface.get_expression_satisfied('bool_true_prop_exp') is True

    assert kb_interface.get_expression_satisfied('false_measure_prop_exp') is False
    assert kb_interface.get_expression_satisfied('true_measure_prop_exp') is True
    assert kb_interface.get_expression_satisfied('no_measure_prop_exp') is False


def test_not_expression_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('not_false_expr') is True
    assert kb_interface.get_expression_satisfied('not_true_expr') is False


def test_less_than_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_less_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_less_vd_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_less_vd_1_1') is False

    assert kb_interface.get_expression_satisfied('md_1_2_less_md_1_1') is False
    assert kb_interface.get_expression_satisfied('md_1_2_less_md_1_2') is False
    assert kb_interface.get_expression_satisfied('md_1_2_less_md_1_3') is True

    assert kb_interface.get_expression_satisfied('md_1_2_less_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('md_1_2_less_vd_1_2') is False
    assert kb_interface.get_expression_satisfied('md_1_2_less_vd_1_1') is False

    assert kb_interface.get_expression_satisfied('vd_1_3_less_md_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_less_md_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_1_less_md_1_2') is True

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_less_vi_3') is True
    assert kb_interface.get_expression_satisfied('vi_2_less_vi_2') is False
    assert kb_interface.get_expression_satisfied('vi_2_less_vi_1') is False

    assert kb_interface.get_expression_satisfied('mi_2_less_mi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_mi_2') is False
    assert kb_interface.get_expression_satisfied('mi_2_less_mi_1') is False

    assert kb_interface.get_expression_satisfied('mi_2_less_vi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_vi_2') is False
    assert kb_interface.get_expression_satisfied('mi_2_less_vi_1') is False

    assert kb_interface.get_expression_satisfied('vi_3_less_mi_2') is False
    assert kb_interface.get_expression_satisfied('vi_2_less_mi_2') is False
    assert kb_interface.get_expression_satisfied('vi_1_less_mi_2') is True


def test_less_than_equal_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_less_eq_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_less_eq_vd_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_less_eq_vd_1_1') is False

    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_md_1_1') is False
    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_md_1_2') is True
    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_md_1_3') is True

    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_vd_1_2') is True
    assert kb_interface.get_expression_satisfied('md_1_2_less_eq_vd_1_1') is False

    assert kb_interface.get_expression_satisfied('vd_1_3_less_eq_md_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_less_eq_md_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_1_less_eq_md_1_2') is True

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_less_eq_vi_3') is True
    assert kb_interface.get_expression_satisfied('vi_2_less_eq_vi_2') is True
    assert kb_interface.get_expression_satisfied('vi_2_less_eq_vi_1') is False

    assert kb_interface.get_expression_satisfied('mi_2_less_eq_mi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_eq_mi_2') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_eq_mi_1') is False

    assert kb_interface.get_expression_satisfied('mi_2_less_eq_vi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_eq_vi_2') is True
    assert kb_interface.get_expression_satisfied('mi_2_less_eq_vi_1') is False

    assert kb_interface.get_expression_satisfied('vi_3_less_eq_mi_2') is False
    assert kb_interface.get_expression_satisfied('vi_2_less_eq_mi_2') is True
    assert kb_interface.get_expression_satisfied('vi_1_less_eq_mi_2') is True


def test_greater_than_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_vd_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_vd_1_1') is True

    assert kb_interface.get_expression_satisfied('md_1_2_greater_md_1_1') is True
    assert kb_interface.get_expression_satisfied('md_1_2_greater_md_1_2') is False
    assert kb_interface.get_expression_satisfied('md_1_2_greater_md_1_3') is False

    assert kb_interface.get_expression_satisfied('md_1_2_greater_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('md_1_2_greater_vd_1_2') is False
    assert kb_interface.get_expression_satisfied('md_1_2_greater_vd_1_1') is True

    assert kb_interface.get_expression_satisfied('vd_1_3_greater_md_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_md_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_1_greater_md_1_2') is False

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_greater_vi_3') is False
    assert kb_interface.get_expression_satisfied('vi_2_greater_vi_2') is False
    assert kb_interface.get_expression_satisfied('vi_2_greater_vi_1') is True

    assert kb_interface.get_expression_satisfied('mi_2_greater_mi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_mi_2') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_mi_1') is True

    assert kb_interface.get_expression_satisfied('mi_2_greater_vi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_vi_2') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_vi_1') is True

    assert kb_interface.get_expression_satisfied('vi_3_greater_mi_2') is True
    assert kb_interface.get_expression_satisfied('vi_2_greater_mi_2') is False
    assert kb_interface.get_expression_satisfied('vi_1_greater_mi_2') is False


def test_greater_than_equal_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_eq_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_eq_vd_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_eq_vd_1_1') is True

    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_md_1_1') is True
    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_md_1_2') is True
    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_md_1_3') is False

    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_vd_1_2') is True
    assert kb_interface.get_expression_satisfied('md_1_2_greater_eq_vd_1_1') is True

    assert kb_interface.get_expression_satisfied('vd_1_3_greater_eq_md_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_greater_eq_md_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_1_greater_eq_md_1_2') is False

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_greater_eq_vi_3') is False
    assert kb_interface.get_expression_satisfied('vi_2_greater_eq_vi_2') is True
    assert kb_interface.get_expression_satisfied('vi_2_greater_eq_vi_1') is True

    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_mi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_mi_2') is True
    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_mi_1') is True

    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_vi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_vi_2') is True
    assert kb_interface.get_expression_satisfied('mi_2_greater_eq_vi_1') is True

    assert kb_interface.get_expression_satisfied('vi_3_greater_eq_mi_2') is True
    assert kb_interface.get_expression_satisfied('vi_2_greater_eq_mi_2') is True
    assert kb_interface.get_expression_satisfied('vi_1_greater_eq_mi_2') is False


def test_equal_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_equal_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_equal_vd_1_2') is True

    assert kb_interface.get_expression_satisfied('md_1_2_equal_md_1_3') is False
    assert kb_interface.get_expression_satisfied('md_1_2_equal_md_1_2') is True

    assert kb_interface.get_expression_satisfied('md_1_2_equal_vd_1_3') is False
    assert kb_interface.get_expression_satisfied('md_1_2_equal_vd_1_2') is True

    assert kb_interface.get_expression_satisfied('vd_1_3_equal_md_1_2') is False
    assert kb_interface.get_expression_satisfied('vd_1_2_equal_md_1_2') is True

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_equal_vi_3') is False
    assert kb_interface.get_expression_satisfied('vi_2_equal_vi_2') is True

    assert kb_interface.get_expression_satisfied('mi_2_equal_mi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_equal_mi_2') is True

    assert kb_interface.get_expression_satisfied('mi_2_equal_vi_3') is False
    assert kb_interface.get_expression_satisfied('mi_2_equal_vi_2') is True

    assert kb_interface.get_expression_satisfied('vi_3_equal_mi_2') is False
    assert kb_interface.get_expression_satisfied('vi_2_equal_mi_2') is True

    # String values
    assert kb_interface.get_expression_satisfied('vs_2_equal_vs_1') is False
    assert kb_interface.get_expression_satisfied('vs_2_equal_vs_2') is True

    assert kb_interface.get_expression_satisfied('ms_2_equal_ms_1') is False
    assert kb_interface.get_expression_satisfied('ms_2_equal_ms_2') is True

    assert kb_interface.get_expression_satisfied('ms_2_equal_vs_1') is False
    assert kb_interface.get_expression_satisfied('ms_2_equal_vs_2') is True

    assert kb_interface.get_expression_satisfied('vs_1_equal_ms_2') is False
    assert kb_interface.get_expression_satisfied('vs_2_equal_ms_2') is True

    # Bool values
    assert kb_interface.get_expression_satisfied('vb_false_equal_vb_true') is False
    assert kb_interface.get_expression_satisfied('vb_false_equal_vb_false') is True

    assert kb_interface.get_expression_satisfied('mb_false_equal_mb_true') is False
    assert kb_interface.get_expression_satisfied('mb_false_equal_mb_false') is True

    assert kb_interface.get_expression_satisfied('mb_false_equal_vb_true') is False
    assert kb_interface.get_expression_satisfied('mb_false_equal_vb_false') is True

    assert kb_interface.get_expression_satisfied('vb_true_equal_mb_false') is False
    assert kb_interface.get_expression_satisfied('vb_false_equal_mb_false') is True


def test_not_equal_satisfied(kb_interface):
    assert kb_interface.get_expression_satisfied('vd_1_2_not_equal_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_not_equal_vd_1_2') is False

    assert kb_interface.get_expression_satisfied('md_1_2_not_equal_md_1_3') is True
    assert kb_interface.get_expression_satisfied('md_1_2_not_equal_md_1_2') is False

    assert kb_interface.get_expression_satisfied('md_1_2_not_equal_vd_1_3') is True
    assert kb_interface.get_expression_satisfied('md_1_2_not_equal_vd_1_2') is False

    assert kb_interface.get_expression_satisfied('vd_1_3_not_equal_md_1_2') is True
    assert kb_interface.get_expression_satisfied('vd_1_2_not_equal_md_1_2') is False

    # Integer values
    assert kb_interface.get_expression_satisfied('vi_2_not_equal_vi_3') is True
    assert kb_interface.get_expression_satisfied('vi_2_not_equal_vi_2') is False

    assert kb_interface.get_expression_satisfied('mi_2_not_equal_mi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_not_equal_mi_2') is False

    assert kb_interface.get_expression_satisfied('mi_2_not_equal_vi_3') is True
    assert kb_interface.get_expression_satisfied('mi_2_not_equal_vi_2') is False

    assert kb_interface.get_expression_satisfied('vi_3_not_equal_mi_2') is True
    assert kb_interface.get_expression_satisfied('vi_2_not_equal_mi_2') is False

    # String values
    assert kb_interface.get_expression_satisfied('vs_2_not_equal_vs_1') is True
    assert kb_interface.get_expression_satisfied('vs_2_not_equal_vs_2') is False

    assert kb_interface.get_expression_satisfied('ms_2_not_equal_ms_1') is True
    assert kb_interface.get_expression_satisfied('ms_2_not_equal_ms_2') is False

    assert kb_interface.get_expression_satisfied('ms_2_not_equal_vs_1') is True
    assert kb_interface.get_expression_satisfied('ms_2_not_equal_vs_2') is False

    assert kb_interface.get_expression_satisfied('vs_1_not_equal_ms_2') is True
    assert kb_interface.get_expression_satisfied('vs_2_not_equal_ms_2') is False

    # Bool values
    assert kb_interface.get_expression_satisfied('vb_false_not_equal_vb_true') is True
    assert kb_interface.get_expression_satisfied('vb_false_not_equal_vb_false') is False

    assert kb_interface.get_expression_satisfied('mb_false_not_equal_mb_true') is True
    assert kb_interface.get_expression_satisfied('mb_false_not_equal_mb_false') is False

    assert kb_interface.get_expression_satisfied('mb_false_not_equal_vb_true') is True
    assert kb_interface.get_expression_satisfied('mb_false_not_equal_vb_false') is False

    assert kb_interface.get_expression_satisfied('vb_true_not_equal_mb_false') is True
    assert kb_interface.get_expression_satisfied('vb_false_not_equal_mb_false') is False


def test_or_expression(kb_interface):
    assert kb_interface.get_expression_satisfied('or_expression_1') is True
    assert kb_interface.get_expression_satisfied('or_expression_2') is True
    assert kb_interface.get_expression_satisfied('or_expression_3') is False


def test_and_expression(kb_interface):
    assert kb_interface.get_expression_satisfied('and_expression_1') is True
    assert kb_interface.get_expression_satisfied('and_expression_2') is False
    assert kb_interface.get_expression_satisfied('and_expression_3') is True
