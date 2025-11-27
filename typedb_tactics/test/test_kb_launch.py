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

import sys
from dataclasses import fields
from pathlib import Path

import launch

import launch_pytest

import launch_ros

from lifecycle_msgs.srv import ChangeState
from lifecycle_msgs.srv import GetState


import pytest

import rclpy
from rclpy.node import Node

from std_srvs.srv import Empty


@launch_pytest.fixture(scope='module')
def generate_test_description():
    path_to_pkg = Path(__file__).parents[1]
    path_schemas = path_to_pkg / 'schemas'
    path_test_data = path_to_pkg / 'test' / 'data'

    tactical_kb = launch_ros.actions.Node(
        executable=sys.executable,
        arguments=[
            str(path_to_pkg / 'typedb_tactics' / 'tactical_retreat_node.py')],
        additional_env={'PYTHONUNBUFFERED': '1'},
        name='tactical_kb',
        output='screen',
        parameters=[{
            'schema_path': [
                str(path_schemas / 'data_structure/data_structure.tql'),
                str(path_schemas / 'context_model/context_model.tql'),
                str(path_schemas / 'ros_model/ros_model.tql'),
                str(path_schemas / 'feature_model/feature_model.tql'),
                str(path_schemas / 'relaxed/relaxed_model.tql'),
                str(path_schemas / 'tactics_model/tactics_model.tql'),
                str(path_schemas / 'discover_tactics_model/discover_tactics_model.tql'),
                str(path_schemas / 'tactics_model/discover_hypothetical_req_fulfillment.tql')],
            'data_path': [
                str(path_schemas / 'ros_model/ros_model_example.tql'),
                str(path_schemas / 'tactics_model/tactics_example.tql'),
                str(path_schemas / 'relaxed/relaxed_mirte_example.tql'),
                str(path_test_data / 'test_tactics_model.tql'),
                str(path_test_data / 'test_ros_model.tql')],
            'database_name': 'test_tactical_kb'
        }]
    )

    return launch.LaunchDescription([
        tactical_kb,
    ])


@pytest.fixture(scope='module', autouse=True)
def rclpy_runtime():
    if not rclpy.ok():
        rclpy.init()
    try:
        yield
    finally:
        if rclpy.ok():
            rclpy.shutdown()


@pytest.fixture
def test_node():
    node = HelperNode()
    try:
        yield node
    finally:
        node.destroy_node()


class HelperNode(Node):

    def __init__(self, name='test_node'):
        super().__init__(name)

        self.change_state_cli = self.create_client(
            ChangeState, '/tactical_kb/change_state'
        )

        self.get_state_cli = self.create_client(
            GetState, '/tactical_kb/get_state'
        )

        self.delete_db_cli = self.create_client(
            Empty, '/tactical_kb/delete_database'
        )

    def call_service(self, cli, request, timeout_sec=5.0):
        if cli.wait_for_service(timeout_sec=5.0) is False:
            self.get_logger().error(
                'service not available {}'.format(cli.srv_name))
            return None
        future = cli.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if future.done() is False:
            self.get_logger().error(
                'Future not completed {}'.format(cli.srv_name))
            return None

        return future.result()

    def change_node_state(self, transition_id):
        change_state_req = ChangeState.Request()
        change_state_req.transition.id = transition_id
        return self.call_service(self.change_state_cli, change_state_req, 60.0)

    def get_node_state(self):
        get_state_req = GetState.Request()
        return self.call_service(self.get_state_cli, get_state_req)

    def activate_tactical_kb(self):
        if self.get_node_state().current_state.id == 3:
            return
        state_req = 1
        res = self.change_node_state(state_req)
        if res.success is True:
            state_req = 3
            res = self.change_node_state(state_req)
        if res.success is False:
            self.get_logger().error(
                'State change  req error. Requested {}'.format(state_req))


@pytest.mark.launch(fixture=generate_test_description)
def test_tactical_kb_lc_states(test_node):
    configure_res = test_node.change_node_state(1)
    get_inactive_state_res = test_node.get_node_state()

    activate_res = test_node.change_node_state(3)
    get_active_state_res = test_node.get_node_state()

    assert configure_res.success is True and \
        get_inactive_state_res.current_state.id == 2 and \
        activate_res.success is True and \
        get_active_state_res.current_state.id == 3


def dataclass_from_msg(dc_type, msg):
    """
    Construct a dataclass instance from a ROS 2 message.

    Assumes dc_type fields have the same names as the msg attributes.
    """
    kwargs = {
        f.name: getattr(msg, f.name)
        for f in fields(dc_type)
    }
    return dc_type(**kwargs)


@pytest.mark.launch(fixture=generate_test_description)
def test_srv_potential_requirements_fulfillment(test_node):
    test_node.activate_tactical_kb()

    from tactical_msgs.srv import PotentialRequirementFulfillment
    test_node.potential_requirements_fulfillment_srv = test_node.create_client(
        PotentialRequirementFulfillment,
        '/tactical_kb/potential_requirements_fulfillment'
    )

    from typedb_tactics.utils import RequirementImpactDict
    request = PotentialRequirementFulfillment.Request()
    request.action_name = '/navigate_to_pose'
    result = test_node.call_service(
        test_node.potential_requirements_fulfillment_srv, request, 10.0)

    requirements_impact = [
        dataclass_from_msg(RequirementImpactDict, r) for r in result.requirements_impact
    ]

    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.68)) in requirements_impact
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MED',
        fulfillment=pytest.approx(0.84)) in requirements_impact
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.1 Velocity',
        tactic_rule='MAX',
        fulfillment=pytest.approx(1.0)) in requirements_impact

    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MIN',
        fulfillment=pytest.approx(0.932393864)) in requirements_impact
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MED',
        fulfillment=pytest.approx(0.92867174)) in requirements_impact
    assert RequirementImpactDict(
        action_name='/navigate_to_pose',
        requirement_name='R1.2 Movement Power',
        tactic_rule='MAX',
        fulfillment=pytest.approx(0.923116396)) in requirements_impact
