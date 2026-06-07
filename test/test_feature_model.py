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

from ros_typedb.typedb_interface import convert_py_type_to_query_type
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def fetch_siblings(self, feature_name):
    query = f"""
        match
            $f isa Feature, has feature_name '{feature_name}';
            $siblings (sibling:$f, sibling:$f_sibling) isa feature_siblings;
        fetch
            $f_sibling : feature_name;
    """
    query_result = self.fetch_database(query)
    return [q['f_sibling']['feature_name'][0]['value'] for q in query_result]


def update_feature_selected(self, feature_name: str, selected: bool):
    selected_tql_type = convert_py_type_to_query_type(selected)

    query = f"""
        match
            $f isa Feature, has feature_name "{feature_name}", has selected $sel;
        delete
            $f has $sel;
        insert
            $f has selected {selected_tql_type};
    """
    query_result = self.update_database(query)
    return query_result


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_feature_model',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/feature_model/feature_model_logical_expression.tql'],
        ['test/data/test_feature_model.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
    yield kb_interface
    kb_interface.delete_database()

def test_feature_as_proposition_expression(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'true_feature_prop_exp')],
        'expression_satisfied')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'false_feature_prop_exp')],
        'expression_satisfied')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'propositional_expression',
        [('expression_name', 'false_feature_prop_exp_2')],
        'expression_satisfied')[0] is False


def test_feature_siblings(kb_interface):
    kb_interface.register_method('fetch_siblings', fetch_siblings)
    siblings = kb_interface.fetch_siblings('f_alternative_child_1')
    assert 'f_alternative_child_2' in siblings
    assert 'f_alternative_child_3' in siblings
