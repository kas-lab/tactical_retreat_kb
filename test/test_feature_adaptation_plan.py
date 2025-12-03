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


def get_feature_resolution_dependency(self, name):
    query = f"""
        match
            $fa isa feature_adaptation, has feature_adaptation_name '{name}';
            $fd (feature_adaptation:$fa,
                 dependent: $action_dependent,
                 dependency: $action_dependency) isa feature_resolution_dependency;
            $action_dependency (node: $node) isa resolution_action;
        fetch
            $action_dependency: action_name;
            $action_dependent: action_name;
    """
    query_result = self.fetch_database(query)
    return [(r['action_dependency']['action_name'][0]['value'],
             r['action_dependent']['action_name'][0]['value']) for r in query_result]


def get_feature_adaptation_plan(self, tactic_rule: str):
    query = f"""
        match
            (tactic:$t, consequent:$fa) isa tactic_rule, has rule_name '{tactic_rule}';
            $plan (feature_adaptation: $fa) isa feature_adaptation_plan;
            (plan:$plan, action: $action) isa plan_action_indexed, has action_index $index;
        fetch
            $action: action_name;
            $index;
        sort $index;
    """
    query_result = self.fetch_database(query)
    print(query_result)
    return [(r['action']['action_name'][0]['value'],
             r['index']['value']) for r in query_result]


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_tactics_model',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/feature_adaptation_plan/feature_adaptation_plan.tql'],
        ['test/data/test_feature_adaptation_plan.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    kb_interface.register_method(
        'get_feature_resolution_dependency', get_feature_resolution_dependency)
    kb_interface.register_method(
        'get_feature_adaptation_plan', get_feature_adaptation_plan)
    yield kb_interface
    kb_interface.delete_database()


def test_feature_resolution_dependency(kb_interface):
    dependencies = kb_interface.get_feature_resolution_dependency('fa1')
    assert [('res_action_set_node_3_lc_inactive',
            'res_action_set_node_1_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa2')
    assert [('res_action_set_node_1_lc_active',
            'res_action_set_node_2_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa3')
    assert [('res_action_set_node_1_lc_inactive',
            'res_action_set_node_2_lc_active')] == dependencies


def test_feature_adaptation_plan(kb_interface):
    plan = kb_interface.get_feature_adaptation_plan('tactic_rule_1')
    assert [('res_action_set_node_3_lc_inactive', 0),
            ('res_action_set_node_1_lc_active', 1)] == plan

    plan = kb_interface.get_feature_adaptation_plan('tr_activate_req_constrained')
    assert [('res_action_set_node_1_lc_active', 0),
            ('res_action_set_node_2_lc_active', 1)] == plan

    plan = kb_interface.get_feature_adaptation_plan('tr_activate_exc_constrained')
    assert [('res_action_set_node_1_lc_inactive', 0),
            ('res_action_set_node_2_lc_active', 1)] == plan
