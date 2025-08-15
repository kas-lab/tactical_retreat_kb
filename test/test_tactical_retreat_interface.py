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
# from rosa_kb.typedb_model_interface \
#     import convert_component_parameter_value_to_py_type
# from datetime import datetime

@pytest.fixture
def kb_interface():
	kb_interface = TacticalRetreatInterface(
		"localhost:1729",
		"test_model_interface",
		["typedb/ros_model.tql", "typedb/schema_tactics_resolution.tql", "typedb/feature_model.tql"],
		["typedb/ros_model_example.tql", "typedb/tactics_example.tql"],
		force_database=True,
		force_data=True,
		infer=True
	)
	return kb_interface

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
    action_clients = kb_interface.get_action_clients_names('bt_navigator_navigate_to_pose_rclcpp')
    assert len(action_clients) == 2
    assert action_clients[0]['action_name'] == '/compute_path_to_pose'
    assert action_clients[0]['action_type'] == 'nav2_msgs/action/ComputePathToPose'
    assert action_clients[1]['action_name'] == '/follow_path'
    assert action_clients[1]['action_type'] == 'nav2_msgs/action/FollowPath'

def test_get_connect_action_server_nodes(kb_interface):
    action_server_nodes = kb_interface.get_connected_action_server_nodes('bt_navigator_navigate_to_pose_rclcpp')
    assert len(action_server_nodes) == 2
    assert action_server_nodes[0]['namespace'] == ''
    assert action_server_nodes[0]['node_name'] == 'planner_server'
    assert action_server_nodes[1]['namespace'] == ''
    assert action_server_nodes[1]['node_name'] == 'controller_server'

def test_get_connected_subscriber_nodes(kb_interface):
    subscriber_nodes = kb_interface.get_connected_subscriber_nodes('controller_server')
    assert len(subscriber_nodes) == 1
    assert subscriber_nodes[0]['namespace'] == ''
    assert subscriber_nodes[0]['node_name'] == 'velocity_smoother'

def test_get_active_neighbours(kb_interface):
    active_neighbours = kb_interface.get_active_neighbours('bt_navigator')
    assert len(active_neighbours) == 4
    assert active_neighbours[0]['namespace'] == ''
    assert active_neighbours[0]['node_name'] == 'bt_navigator_navigate_through_poses_rclcpp'
    assert active_neighbours[1]['namespace'] == ''
    assert active_neighbours[1]['node_name'] == 'bt_navigator_navigate_to_pose_rclcpp'
    assert active_neighbours[2]['namespace'] == ''
    assert active_neighbours[2]['node_name'] == 'controller_server'
    assert active_neighbours[3]['namespace'] == ''
    assert active_neighbours[3]['node_name'] == 'planner_server'

    active_neighbours = kb_interface.get_active_neighbours('bt_navigator_navigate_through_poses_rclcpp')
    assert len(active_neighbours) == 1
    assert active_neighbours[0]['namespace'] == ''
    assert active_neighbours[0]['node_name'] == 'controller_server'

    active_neighbours = kb_interface.get_active_neighbours('bt_navigator_navigate_to_pose_rclcpp')
    assert len(active_neighbours) == 2
    assert active_neighbours[0]['namespace'] == ''
    assert active_neighbours[0]['node_name'] == 'controller_server'
    assert active_neighbours[1]['namespace'] == ''
    assert active_neighbours[1]['node_name'] == 'planner_server'

    active_neighbours = kb_interface.get_active_neighbours('controller_server')
    assert len(active_neighbours) == 1
    assert active_neighbours[0]['namespace'] == ''
    assert active_neighbours[0]['node_name'] == 'velocity_smoother'

    active_neighbours = kb_interface.get_active_neighbours('velocity_smoother')
    assert len(active_neighbours) == 2
    assert active_neighbours[0]['namespace'] == ''
    assert active_neighbours[0]['node_name'] == 'behavior_server'
    assert active_neighbours[1]['namespace'] == ''
    assert active_neighbours[1]['node_name'] == 'relay_node_cmd_vel'

def test_connected_active_connected_nodes(kb_interface):
    nodes = [{'node_name': 'bt_navigator', 'namespace': ''}]
    connected_nodes = kb_interface.get_active_connected_nodes(nodes)
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
    assert kb_interface.does_tactic_affect_nodes('MaxSpeedInternal', 'velocity_smoother', '')
    assert kb_interface.does_tactic_affect_nodes('MaxSpeedInternal', 'planner_server', '') is False