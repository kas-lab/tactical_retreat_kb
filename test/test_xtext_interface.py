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

import logging
import os

import pytest
from tactical_retreat_kb.xtext_tactical_retreat_interface import TacticalRetreatInterface as XTextInterface
from aal_msgs.msg import Adaptation
from rclpy.parameter import Parameter
from lifecycle_msgs.msg import Transition

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def model_path(name):
    # Absolute paths are required: the resolution scope provider resolves its
    # relative imports against the resource URI, which fails for relative URIs.
    return os.path.join(MODELS_DIR, name)


@pytest.fixture(scope='module')
def kb_interface():
    logger = logging.getLogger(__name__)
    kb_interface = XTextInterface(
        model_path("test.resolution"),
        model_path("test.var"),
        model_path("test.context"),
        model_path("test.reqs"),
        [model_path("test.ros"),model_path("lifecycle_msgs.ros")],
        model_path("test.ros2"),
        model_path("test.rossystem"),
        model_path("test.tactics"),
        require_nodes_running=False,
        verify_parameters=False,
        logger=logger,
        )
    yield kb_interface
    # kb_interface.delete_database()


def test_get_valid_tactics(kb_interface):
    # global tactic
    kb_interface.add_measurements({"test_context_var" : 0.70})
    tactic_names = ["TEST_RULE"]
    satisfied = kb_interface.get_valid_tactics(tactic_names, "")
    assert satisfied == [True]
    kb_interface.add_measurements({"test_context_var" : 0.10})
    satisfied = kb_interface.get_valid_tactics(tactic_names, "")
    assert satisfied == [False]

    #action-tactic
    kb_interface.add_measurements({"test_context_var" : 0.70})
    satisfied = kb_interface.get_valid_tactics(["TEST_ACTION_RULE"], "TestAction")
    assert satisfied == [True]
    satisfied = kb_interface.get_valid_tactics(["TEST_ACTION_RULE"], "")
    assert satisfied == []
    satisfied = kb_interface.get_valid_tactics(["TEST_RULE"], "TestAction")
    assert satisfied == []

def test_get_applicable_tactics(kb_interface):
    tactics = kb_interface.get_applicable_tactics("test_resolution","TestAction")
    assert tactics == {("TEST_ACTION_RULE","None") : ["SEL_RootChild"],
                       ("TEST_REQ_RULE", "TestRequirement") : ["SEL_RootChild"]}
    tactics = kb_interface.get_applicable_tactics("test_resolution","")
    assert tactics == {("TEST_RULE","None") : ["SEL_RootChild"],
                       ("TEST_RULE_TWO","None") : ["SEL_SecondRootChild"]}

def test_similar_requirements(kb_interface):
    similar_to_dic = kb_interface.similar_requirements("TestAction")
    assert similar_to_dic == {"TestRequirement" : ["TestRequirementTwo"]}

def test_get_valid_ranked_tactics(kb_interface):
    kb_interface.add_measurements({"test_context_var" : 0.70})

    tactic_names = ["TEST_RULE"]
    _, ranked = kb_interface.get_valid_ranked_tactics(tactic_names,"TestAction")

    assert ranked == {"TestRequirement" : ["TEST_REQ_RULE"], "none" : ["TEST_ACTION_RULE"]}

def test_get_resolution_adaptations(kb_interface):
    resolutions = kb_interface.get_resolution_adaptations()
    
    sp_adaptation = Adaptation(adaptation_target=Adaptation.ROSPARAMETER,
                            node_name='/test_node',
                            parameter_adaptation=Parameter("test_parameter", value=0.3).to_parameter_msg())
    
    sp_adaptation_one = Adaptation(adaptation_target=Adaptation.ROSPARAMETER,
                            node_name='/test_node',
                            parameter_adaptation=Parameter("test_parameter", value=0.7).to_parameter_msg())

    lc_adaptation = Adaptation(adaptation_target=Adaptation.STATETRANSITION,
                              node_name="/test_node",
                              lifecycle_adaptation=Transition(id=Transition.TRANSITION_ACTIVATE))
    assert resolutions == {"sp_test_parameter" : [sp_adaptation],
                           "sp_test_parameter_1" : [sp_adaptation_one],
                           "slc__slash_test_node_active" : [lc_adaptation]}

def test_change_configuration(kb_interface):
    pass

def test_reconfiguration(kb_interface):
    resolutions = kb_interface.get_resolution_adaptations() # causes the names to be as in test_get_resolution_adaptations

    configuration_changes = kb_interface.reconfiguration(["SEL_RootChild"])
    assert configuration_changes == []
    configuration_changes = kb_interface.reconfiguration(["SEL_SecondRootChild"])
    assert configuration_changes == ['slc__slash_test_node_active']
    configuration_changes = kb_interface.reconfiguration(["SEL_SecondRootChild"])
    assert configuration_changes == []
    configuration_changes = kb_interface.reconfiguration(["SEL_ThirdRootChild"])
    assert configuration_changes == ['sp_test_parameter_1']

def test_get_in_effect_requirement_fulfillment(kb_interface):
    kb_interface.add_measurements({"test_context_var" : 0.22221})
    reqs = kb_interface.get_in_effect_requirement_fulfillment()
    for req in reqs:
        if(req['requirement_name'] == 'TestRequirement'):
            assert req['fulfillment'] == pytest.approx(0.92442)
        elif(req['requirement_name'] == 'TestRequirementTwo'):
            assert req['fulfillment'] == pytest.approx(0.44442)
        else:
            assert True == False

def test_new_tactic(kb_interface):
    new_tactic, _ = kb_interface.new_tactic("TEST_RULE_TWO","TestRequirement","TestAction")
    reconfs = kb_interface._reconfs(new_tactic.getTactics().toArray()[0])
    assert reconfs == ["SEL_SecondRootChild"]