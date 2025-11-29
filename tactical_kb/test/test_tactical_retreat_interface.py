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
from tactical_kb.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope="module")
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['schemas/ros_model/ros_model_example.tql',
            'schemas/tactics_model/tactics_example.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_get_subnodes(kb_interface):
    subnodes = kb_interface.get_subnodes('bt_navigator')
    assert len(subnodes) == 2
    assert subnodes[0]['namespace'] == ''
    assert subnodes[0]['node_name'] == 'bt_navigator_navigate_through_poses_rclcpp'
    assert subnodes[1]['namespace'] == ''
    assert subnodes[1]['node_name'] == 'bt_navigator_navigate_to_pose_rclcpp'


def test_get_action_server_nodes(kb_interface):
    servers = kb_interface.get_action_server_nodes('/navigate_to_pose')
    assert len(servers) == 1
    assert servers[0]['namespace'] == ''
    assert servers[0]['node_name'] == 'bt_navigator'


def test_get_action_clients_names(kb_interface):
    action_clients = kb_interface.get_action_clients_names(
        'bt_navigator_navigate_to_pose_rclcpp')
    assert len(action_clients) == 2
    assert action_clients[0]['action_name'] == '/compute_path_to_pose'
    assert action_clients[0]['action_type'] == 'nav2_msgs/action/ComputePathToPose'
    assert action_clients[1]['action_name'] == '/follow_path'
    assert action_clients[1]['action_type'] == 'nav2_msgs/action/FollowPath'


def test_get_connect_action_server_nodes(kb_interface):
    action_server_nodes = kb_interface.get_connected_action_server_nodes(
        'bt_navigator_navigate_to_pose_rclcpp')
    assert len(action_server_nodes) == 2
    assert action_server_nodes[0]['namespace'] == ''
    assert action_server_nodes[0]['node_name'] == 'controller_server'
    assert action_server_nodes[1]['namespace'] == ''
    assert action_server_nodes[1]['node_name'] == 'planner_server'


def test_get_connected_subscriber_nodes(kb_interface):
    subscriber_nodes = kb_interface.get_connected_subscriber_nodes(
        'controller_server')
    assert len(subscriber_nodes) == 1
    assert subscriber_nodes[0]['namespace'] == ''
    assert subscriber_nodes[0]['node_name'] == 'velocity_smoother'


def test_get_neighbours(kb_interface):
    neighbours = kb_interface.get_neighbours('bt_navigator')
    assert len(neighbours) == 4
    assert neighbours[0]['namespace'] == ''
    assert neighbours[0]['node_name'] == 'bt_navigator_navigate_through_poses_rclcpp'
    assert neighbours[1]['namespace'] == ''
    assert neighbours[1]['node_name'] == 'bt_navigator_navigate_to_pose_rclcpp'
    assert neighbours[2]['namespace'] == ''
    assert neighbours[2]['node_name'] == 'controller_server'
    assert neighbours[3]['namespace'] == ''
    assert neighbours[3]['node_name'] == 'planner_server'

    neighbours = kb_interface.get_neighbours(
        'bt_navigator_navigate_through_poses_rclcpp')
    assert len(neighbours) == 1
    assert neighbours[0]['namespace'] == ''
    assert neighbours[0]['node_name'] == 'controller_server'

    neighbours = kb_interface.get_neighbours(
        'bt_navigator_navigate_to_pose_rclcpp')
    assert len(neighbours) == 2
    assert neighbours[0]['namespace'] == ''
    assert neighbours[0]['node_name'] == 'controller_server'
    assert neighbours[1]['namespace'] == ''
    assert neighbours[1]['node_name'] == 'planner_server'

    neighbours = kb_interface.get_neighbours('controller_server')
    assert len(neighbours) == 1
    assert neighbours[0]['namespace'] == ''
    assert neighbours[0]['node_name'] == 'velocity_smoother'

    neighbours = kb_interface.get_neighbours('velocity_smoother')
    assert len(neighbours) == 3
    assert neighbours[0]['namespace'] == ''
    assert neighbours[0]['node_name'] == 'behavior_server'
    assert neighbours[1]['namespace'] == ''
    assert neighbours[1]['node_name'] == 'controller_server'
    assert neighbours[2]['namespace'] == ''
    assert neighbours[2]['node_name'] == 'relay_node_cmd_vel'


def test_get_connected_nodes(kb_interface):
    connected_nodes = kb_interface.get_connected_nodes(
        'bt_navigator', '')
    assert len(connected_nodes) == 8
    assert connected_nodes[0]['node_name'] == 'behavior_server'
    assert connected_nodes[0]['namespace'] == ''
    assert connected_nodes[1]['node_name'] == 'bt_navigator'
    assert connected_nodes[1]['namespace'] == ''
    assert connected_nodes[2]['node_name'] == 'bt_navigator_navigate_through_poses_rclcpp'
    assert connected_nodes[2]['namespace'] == ''
    assert connected_nodes[3]['node_name'] == 'bt_navigator_navigate_to_pose_rclcpp'
    assert connected_nodes[3]['namespace'] == ''
    assert connected_nodes[4]['node_name'] == 'controller_server'
    assert connected_nodes[4]['namespace'] == ''
    assert connected_nodes[5]['node_name'] == 'planner_server'
    assert connected_nodes[5]['namespace'] == ''
    assert connected_nodes[6]['node_name'] == 'relay_node_cmd_vel'
    assert connected_nodes[6]['namespace'] == ''
    assert connected_nodes[7]['node_name'] == 'velocity_smoother'
    assert connected_nodes[7]['namespace'] == ''


def test_get_tactics(kb_interface):
    tactics = kb_interface.get_tactics('rebetmc')
    assert len(tactics) == 1
    assert tactics[0] == 'MaxSpeedInternal'


def test_does_tactic_affect_nodes(kb_interface):
    assert kb_interface.does_tactic_affect_nodes(
        'MaxSpeedInternal', 'velocity_smoother', '')
    assert kb_interface.does_tactic_affect_nodes(
        'MaxSpeedInternal', 'planner_server', '') is False


def test_get_applicable_tactics(kb_interface):
    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', '/navigate_to_pose')
    assert len(tactics) == 3
    assert tactics[0] == 'MAX'
    assert tactics[1] == 'MED'
    assert tactics[2] == 'MIN'

    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', '/follow_path')
    assert len(tactics) == 3
    assert tactics[0] == 'MAX'
    assert tactics[1] == 'MED'
    assert tactics[2] == 'MIN'

    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', '/compute_path_to_pose')
    assert len(tactics) == 0

    # service server
    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', '~/change_state')
    assert len(tactics) == 3
    assert tactics[0] == 'MAX'
    assert tactics[1] == 'MED'
    assert tactics[2] == 'MIN'

    # publisher
    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', '~/transition_event')
    assert len(tactics) == 3
    assert tactics[0] == 'MAX'
    assert tactics[1] == 'MED'
    assert tactics[2] == 'MIN'

    # subscriber
    tactics = kb_interface.get_applicable_tactics(
        'rebetmc', 'odom')
    assert len(tactics) == 0


@pytest.fixture(scope="module")
def kb_interface_test_model():
    kb_interface_test_model = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['test/data/test_tactical_retreat_interface.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface_test_model
    kb_interface_test_model.delete_database()


def test_add_measurement(kb_interface_test_model):
    kb_interface_test_model.add_measurement('measure_string', 'iamstring')
    assert kb_interface_test_model.get_latest_measurement(
        'measure_string') == 'iamstring'

    kb_interface_test_model.add_measurement('measure_double', 99.9)
    assert kb_interface_test_model.get_latest_measurement(
        'measure_double') == 99.9

    kb_interface_test_model.add_measurement('measure_integer', 1)
    assert kb_interface_test_model.get_latest_measurement(
        'measure_integer') == 1

    kb_interface_test_model.add_measurement('measure_bool', True)
    assert kb_interface_test_model.get_latest_measurement('measure_bool')

    kb_interface_test_model.add_measurement(
        'measure_string_array', [
            'iamstring', 'noiamnot'])
    assert kb_interface_test_model.get_latest_measurement(
        'measure_string_array') == ['iamstring', 'noiamnot']

    kb_interface_test_model.add_measurement(
        'measure_double_array', [99.9, 42.0])
    assert kb_interface_test_model.get_latest_measurement(
        'measure_double_array') == [99.9, 42.0]

    kb_interface_test_model.add_measurement('measure_integer_array', [1, 2, 3])
    assert kb_interface_test_model.get_latest_measurement(
        'measure_integer_array') == [1, 2, 3]

    kb_interface_test_model.add_measurement(
        'measure_bool_array', [True, True, False])
    assert kb_interface_test_model.get_latest_measurement(
        'measure_bool_array') == [True, True, False]
