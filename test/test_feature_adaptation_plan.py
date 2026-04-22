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
from typedb_tactics.utils import AdaptationPlan
from typedb_tactics.utils import names_to_transitions
from aal_msgs.msg import Adaptation
from rclpy.parameter import Parameter

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
            'schemas/tactics_model/tactics_model.tql',
            'schemas/feature_adaptation_plan/feature_adaptation_plan.tql'],
        ['test/data/test_feature_adaptation_plan.tql',
         'schemas/ros_model/ros_model_example.tql',
         'schemas/tactics_model/tactics_example.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    kb_interface.register_method(
        'get_feature_resolution_dependency', get_feature_resolution_dependency)
    yield kb_interface
    kb_interface.delete_database()

def SetLifecycleAction(node_name, transition):
    return  Adaptation(
        adaptation_target=Adaptation.STATETRANSITION,
        node_name=node_name,
        lifecycle_adaptation=names_to_transitions[transition],
    )

def SetParameterAction(node_name, param_name, param_value):
    param = Parameter(param_name, value=param_value)
    return Adaptation(
        adaptation_target=Adaptation.ROSPARAMETER,
        node_name=node_name,
        parameter_adaptation=param.to_parameter_msg()
    )

def test_feature_resolution_dependency(kb_interface):
    dependencies = kb_interface.get_feature_resolution_dependency('fa0')
    assert [('res_action_set_node_3_lc_inactive',
            'res_action_set_node_1_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa1')
    assert [('res_action_set_node_3_lc_inactive',
            'res_action_set_node_1_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa2')
    assert [('res_action_set_node_1_lc_active',
            'res_action_set_node_2_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa3')
    assert [('res_action_set_node_1_lc_inactive',
            'res_action_set_node_2_lc_active')] == dependencies

    dependencies = kb_interface.get_feature_resolution_dependency('fa4')
    assert [('res_action_set_node_1_lc_inactive',
            'res_action_set_node_2_lc_inactive')] == dependencies


def test_reconfiguration_plan(kb_interface):
    plan = kb_interface.get_reconfiguration_plan('tactic_rule_0')


    assert AdaptationPlan(
        [SetLifecycleAction('node_3', 'inactive'),
         SetLifecycleAction('node_1', 'active')]) == plan

    plan = kb_interface.get_reconfiguration_plan('tactic_rule_1')
    assert AdaptationPlan(
        [SetLifecycleAction('node_3', 'inactive'),
         SetLifecycleAction('node_1', 'active')]) == plan

    plan = kb_interface.get_reconfiguration_plan('tr_activate_req_constrained')
    assert AdaptationPlan(
        [SetLifecycleAction('node_1', 'active'),
         SetLifecycleAction('node_2', 'active')]) == plan

    plan = kb_interface.get_reconfiguration_plan('tr_activate_exc_constrained')
    assert AdaptationPlan(
        [SetLifecycleAction('node_1', 'inactive'),
         SetLifecycleAction('node_2', 'active')])

    plan = kb_interface.get_reconfiguration_plan('tr_deactivate_req_constrained')
    assert AdaptationPlan(
        [SetLifecycleAction('node_1', 'inactive'),
         SetLifecycleAction('node_2', 'inactive')]) == plan

    plan = kb_interface.get_reconfiguration_plan('tactic_rule_2')
    assert AdaptationPlan(
        [SetLifecycleAction('node_3', 'inactive'),
         SetLifecycleAction('node_1', 'active'),
         SetParameterAction('node_1', 'parameter', 0.10)]) == plan

    plan = kb_interface.get_reconfiguration_plan('MIN')
    assert AdaptationPlan([
        SetParameterAction('velocity_smoother', 'max_velocity', [0.1, 0.0, 1.0])]) \
        == plan

    plan = kb_interface.get_reconfiguration_plan('MED')
    assert AdaptationPlan([
        SetParameterAction('velocity_smoother', 'max_velocity', [0.18, 0.0, 1.0])]) \
        == plan

    plan = kb_interface.get_reconfiguration_plan('MAX')
    assert AdaptationPlan([
        SetParameterAction('velocity_smoother', 'max_velocity', [0.26, 0.0, 1.0])]) \
        == plan
