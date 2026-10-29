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

from ros_typedb.typedb_interface import TypeDBInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TypeDBInterface(
        'localhost:1729',
        'test_symbolic_tactic_rule_antecedent',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/ros_model/ros_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/tactics_model/tactics_model.tql',
         'schemas/states/symbolic_states.tql',
         'schemas/states/symbolic_tactic_rule_antecedent.tql'],
        ['test/data/test_symbolic_tactic_rule_antecedent.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
    yield kb_interface
    kb_interface.delete_database()


def test_symbolic_label_can_drive_tactic_rule_validity(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'medium')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'high')],
        'symbolic_active')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'tactic_rule',
        [('rule_name', 'symbolic-medium-rule')],
        'rule_valid')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'tactic_rule',
        [('rule_name', 'symbolic-high-rule')],
        'rule_valid')[0] is False
