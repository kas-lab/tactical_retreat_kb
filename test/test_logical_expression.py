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
            # 'schemas/logical_expressions/logical_expression_ext.tql'],
        # ['test/data/test_logical_expression.tql',
        #  'test/data/test_logical_expression_compound.tql',
        #  'test/data/test_logical_expression_satisfied.tql'],
        [],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_propositional_expression_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'bool_false_prop_exp')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'bool_true_prop_exp')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'false_measure_prop_exp')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'true_measure_prop_exp')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'no_measure_prop_exp')],
        'expression_satisfied')[0] is False


def test_not_expression_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'not_expression',
        [('expression_name', 'not_false_expr')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_expression',
        [('expression_name', 'not_true_expr')],
        'expression_satisfied')[0] is False


def test_less_than_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_2_less_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_2_less_vd_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_2_less_vd_1_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_md_1_1')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_md_1_3')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_vd_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'md_1_2_less_vd_1_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_3_less_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_2_less_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vd_1_1_less_md_1_2')],
        'expression_satisfied')[0] is True

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_2_less_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_2_less_vi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_2_less_vi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_mi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_mi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_vi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'mi_2_less_vi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_3_less_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_2_less_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than',
        [('expression_name', 'vi_1_less_mi_2')],
        'expression_satisfied')[0] is True


def test_less_than_equal_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_2_less_eq_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_2_less_eq_vd_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_2_less_eq_vd_1_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_md_1_1')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_md_1_3')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_vd_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'md_1_2_less_eq_vd_1_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_3_less_eq_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_2_less_eq_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vd_1_1_less_eq_md_1_2')],
        'expression_satisfied')[0] is True

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_2_less_eq_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_2_less_eq_vi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_2_less_eq_vi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_mi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_mi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_vi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'mi_2_less_eq_vi_1')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_3_less_eq_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_2_less_eq_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'less_than_equal',
        [('expression_name', 'vi_1_less_eq_mi_2')],
        'expression_satisfied')[0] is True


def test_greater_than_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_2_greater_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_2_greater_vd_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_2_greater_vd_1_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_md_1_1')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_md_1_3')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_vd_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'md_1_2_greater_vd_1_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_3_greater_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_2_greater_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vd_1_1_greater_md_1_2')],
        'expression_satisfied')[0] is False

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_2_greater_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_2_greater_vi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_2_greater_vi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_mi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_mi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_vi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'mi_2_greater_vi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_3_greater_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_2_greater_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than',
        [('expression_name', 'vi_1_greater_mi_2')],
        'expression_satisfied')[0] is False


def test_greater_than_equal_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_2_greater_eq_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_2_greater_eq_vd_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_2_greater_eq_vd_1_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_md_1_1')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_md_1_3')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_vd_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'md_1_2_greater_eq_vd_1_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_3_greater_eq_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_2_greater_eq_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vd_1_1_greater_eq_md_1_2')],
        'expression_satisfied')[0] is False

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_2_greater_eq_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_2_greater_eq_vi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_2_greater_eq_vi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_mi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_mi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_vi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'mi_2_greater_eq_vi_1')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_3_greater_eq_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_2_greater_eq_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'greater_than_equal',
        [('expression_name', 'vi_1_greater_eq_mi_2')],
        'expression_satisfied')[0] is False


def test_equal_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vd_1_2_equal_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vd_1_2_equal_vd_1_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'md_1_2_equal_md_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'md_1_2_equal_md_1_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'md_1_2_equal_vd_1_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'md_1_2_equal_vd_1_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vd_1_3_equal_md_1_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vd_1_2_equal_md_1_2')],
        'expression_satisfied')[0] is True

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vi_2_equal_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vi_2_equal_vi_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mi_2_equal_mi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mi_2_equal_mi_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mi_2_equal_vi_3')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mi_2_equal_vi_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vi_3_equal_mi_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vi_2_equal_mi_2')],
        'expression_satisfied')[0] is True

    # String values
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vs_2_equal_vs_1')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vs_2_equal_vs_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'ms_2_equal_ms_1')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'ms_2_equal_ms_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'ms_2_equal_vs_1')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'ms_2_equal_vs_2')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vs_1_equal_ms_2')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vs_2_equal_ms_2')],
        'expression_satisfied')[0] is True

    # Bool values
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vb_false_equal_vb_true')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vb_false_equal_vb_false')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mb_false_equal_mb_true')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mb_false_equal_mb_false')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mb_false_equal_vb_true')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'mb_false_equal_vb_false')],
        'expression_satisfied')[0] is True

    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vb_true_equal_mb_false')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'equal',
        [('expression_name', 'vb_false_equal_mb_false')],
        'expression_satisfied')[0] is True


def test_not_equal_satisfied(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vd_1_2_not_equal_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vd_1_2_not_equal_vd_1_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'md_1_2_not_equal_md_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'md_1_2_not_equal_md_1_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'md_1_2_not_equal_vd_1_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'md_1_2_not_equal_vd_1_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vd_1_3_not_equal_md_1_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vd_1_2_not_equal_md_1_2')],
        'expression_satisfied')[0] is False

    # Integer values
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vi_2_not_equal_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vi_2_not_equal_vi_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mi_2_not_equal_mi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mi_2_not_equal_mi_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mi_2_not_equal_vi_3')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mi_2_not_equal_vi_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vi_3_not_equal_mi_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vi_2_not_equal_mi_2')],
        'expression_satisfied')[0] is False

    # String values
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vs_2_not_equal_vs_1')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vs_2_not_equal_vs_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'ms_2_not_equal_ms_1')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'ms_2_not_equal_ms_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'ms_2_not_equal_vs_1')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'ms_2_not_equal_vs_2')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vs_1_not_equal_ms_2')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vs_2_not_equal_ms_2')],
        'expression_satisfied')[0] is False

    # Bool values
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vb_false_not_equal_vb_true')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vb_false_not_equal_vb_false')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mb_false_not_equal_mb_true')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mb_false_not_equal_mb_false')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mb_false_not_equal_vb_true')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'mb_false_not_equal_vb_false')],
        'expression_satisfied')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vb_true_not_equal_mb_false')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'not_equal',
        [('expression_name', 'vb_false_not_equal_mb_false')],
        'expression_satisfied')[0] is False


def test_or_expression(kb_interface):
    def fetch_expression_satisfied(self, expression_name):
        query = f"""
            match
                $expr isa or_expression,
                    has expression_name '{expression_name}';
            fetch {{
                "expression_satisfied": $expr.expression_satisfied
            }};
        """
        query_result = self.fetch_database(query)
        return query_result

    kb_interface.register_method('fetch_expression_satisfied', fetch_expression_satisfied)

    or_expression_1 = kb_interface.fetch_expression_satisfied('or_expression_1')
    or_expression_2 = kb_interface.fetch_expression_satisfied('or_expression_2')
    or_expression_3 = kb_interface.fetch_expression_satisfied('or_expression_3')

    assert len(or_expression_1) == 1
    assert or_expression_1[0]['expression_satisfied'] is True

    assert len(or_expression_2) == 1
    assert or_expression_2[0]['expression_satisfied'] is True

    assert len(or_expression_3) == 1
    assert or_expression_3[0]['expression_satisfied'] is False


def test_and_expression(kb_interface):
    def fetch_expression_satisfied(self, expression_name):
        query = f"""
            match
                $expr isa and_expression,
                    has expression_name '{expression_name}';
            fetch {{
                "expression_satisfied": $expr.expression_satisfied
            }};
        """
        query_result = self.fetch_database(query)
        return query_result

    kb_interface.register_method('fetch_expression_satisfied', fetch_expression_satisfied)

    and_expression_1 = kb_interface.fetch_expression_satisfied('and_expression_1')
    and_expression_2 = kb_interface.fetch_expression_satisfied('and_expression_2')
    and_expression_3 = kb_interface.fetch_expression_satisfied('and_expression_3')

    assert len(and_expression_1) == 1
    assert and_expression_1[0]['expression_satisfied'] is True

    assert len(and_expression_2) == 1
    assert and_expression_2[0]['expression_satisfied'] is False

    assert len(and_expression_3) == 1
    assert and_expression_3[0]['expression_satisfied'] is True
