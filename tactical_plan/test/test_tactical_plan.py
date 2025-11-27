# Copyright 2025 KAS lab
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
import threading
from pathlib import Path

import launch

import launch_pytest

import launch_ros

import pytest

from lifecycle_msgs.srv import ChangeState
from lifecycle_msgs.srv import GetState

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from std_srvs.srv import Empty

from tactical_plan.tactical_retreat_plan import TacticalPlan


class HelperNode(Node):

    def __init__(self, name='test_node'):
        super().__init__(name)

        # self.delete_db_cli = self.create_client(
        #     Empty, '/tactical_kb/delete_database'
        # )

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

    def change_node_state(self, transition_id, node_name='tactical_kb'):
        cli = self.create_client(
            ChangeState, node_name + '/change_state')
        change_state_req = ChangeState.Request()
        change_state_req.transition.id = transition_id
        return self.call_service(cli, change_state_req, 60.0)

    def get_node_state(self, node_name='tactical_kb'):
        cli = self.create_client(
            GetState, node_name + '/get_state')
        get_state_req = GetState.Request()
        return self.call_service(cli, get_state_req)

    def activate_lc_node(self, node_name='tactical_kb'):
        state_req = 1
        res = self.change_node_state(state_req, node_name)
        if res.success is True:
            state_req = 3
            res = self.change_node_state(state_req, node_name)
        if res.success is False:
            self.get_logger().error(
                'State change  req error. Requested {}'.format(state_req))


TACTICAL_PLAN_NODE_NAME = 'tactical_plan'
TACTICAL_KB_NODE_NAME = 'tactical_kb'


@launch_pytest.fixture
def generate_test_description():
    # path_to_test = Path(__file__).parents[1]

    # tactical_plan_node = launch_ros.actions.Node(
    #     executable=sys.executable,
    #     arguments=[
    #         str(path_to_test / 'tactical_plan' /
    #             'tactical_plan_node.py')],
    #     additional_env={'PYTHONUNBUFFERED': '1'},
    #     name='tactical_plan',
    #     output='screen',
    # )

    path_to_pkg = Path(__file__).parents[2] / 'typedb_tactics'
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
            'database_name': 'test_tactical_plan'
        }]
    )

    return launch.LaunchDescription([
        tactical_kb,
        # tactical_plan_node,
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
def executor():
    ex = SingleThreadedExecutor()
    t = threading.Thread(target=ex.spin, daemon=True)
    t.start()
    try:
        yield ex
    finally:
        ex.shutdown()
        t.join(timeout=2.0)


@pytest.fixture
def test_node():
    node = HelperNode()
    try:
        yield node
    finally:
        node.destroy_node()


@pytest.fixture(scope='module')
def tactical_plan():
    tactical_plan = TacticalPlan(TACTICAL_PLAN_NODE_NAME)
    yield tactical_plan
    tactical_plan.destroy_node()


# @pytest.mark.launch(fixture=generate_test_description)
def test_tactical_plan_lc_states(test_node, tactical_plan, executor):
    executor.add_node(test_node)
    executor.add_node(tactical_plan)

    configure_res = test_node.change_node_state(1, TACTICAL_PLAN_NODE_NAME)
    get_inactive_state_res = test_node.get_node_state(TACTICAL_PLAN_NODE_NAME)

    activate_res = test_node.change_node_state(3, TACTICAL_PLAN_NODE_NAME)
    get_active_state_res = test_node.get_node_state(TACTICAL_PLAN_NODE_NAME)

    assert configure_res.success is True and \
        get_inactive_state_res.current_state.id == 2 and \
        activate_res.success is True and \
        get_active_state_res.current_state.id == 3

    executor.remove_node(test_node)
    executor.remove_node(tactical_plan)


@pytest.mark.launch(fixture=generate_test_description)
def test_plan_tactical_actions(test_node, tactical_plan, executor):
    executor.add_node(test_node)
    executor.add_node(tactical_plan)

    test_node.activate_lc_node(TACTICAL_KB_NODE_NAME)
    test_node.activate_lc_node(TACTICAL_PLAN_NODE_NAME)

    selected_tactics = tactical_plan.plan_tactical_actions('/navigate_to_pose')

    assert selected_tactics == 'MAX'

    executor.remove_node(test_node)
    executor.remove_node(tactical_plan)
