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

from ros_typedb.typedb_interface import TypeDBQueryError
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/feature_model/feature_model_logical_expression.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['schemas/ros_model/ros_model_example.tql',
            'schemas/tactics_model/tactics_example.tql'],
        force_database=True,
        force_data=True)
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


@pytest.fixture(scope='module')
def kb_interface_test_model():
    kb_interface_test_model = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/logical_expressions/fuzzy_expression.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/relaxed/relaxed_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['test/data/test_tactical_retreat_interface.tql'],
        force_database=True,
        force_data=True)
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


@pytest.fixture(scope='module')
def kb_dtm_coverage():
    """Fixture for applicable_tactics branch coverage.

    Covers branches not exercised by the main ros_model+tactics_example data:
      - feature_adaptation via deactivation (not activation)
      - resolution_action targeting the host node directly (not via connected_nodes)
    """
    kb = TacticalRetreatInterface(
        'localhost:1729',
        'test_dtm_coverage',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/ros_model/ros_model.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/feature_model/feature_model_logical_expression.tql',
         'schemas/tactics_model/tactics_model.tql',
         'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['test/data/test_discover_tactics_model_branches.tql'],
        force_database=True,
        force_data=True)
    yield kb
    kb.delete_database()


def test_applicable_tactics_deactivation_branch(kb_dtm_coverage):
    """applicable_tactics: $fa links (deactivation: $feat) branch.

    COV_RULE uses a feature_adaptation with deactivation (not activation).
    The query must traverse the deactivation OR-branch to find it.
    """
    tactics = kb_dtm_coverage.get_applicable_tactics('cov_model', '/cov_action')
    assert tactics == ['COV_RULE']


def test_applicable_tactics_direct_node_branch(kb_dtm_coverage):
    """applicable_tactics: $ra links (node: $host) branch (direct, not connected_nodes).

    The resolution_action in cov_model targets cov_host directly — the same node
    that owns /cov_action — so the direct-node OR-branch must fire.
    """
    tactics = kb_dtm_coverage.get_applicable_tactics('cov_model', '/cov_action')
    assert tactics == ['COV_RULE']


@pytest.mark.parametrize(
    'method_name,args',
    [
        ('does_tactic_affect_nodes', ('any_tactic', 'any_node', '')),
        ('get_requirement_in_effect', ('any_requirement',)),
        ('get_tactic_rule_valid', ('any_rule',)),
        ('is_feature_selectable', ('any_feature',)),
        ('is_node_running', ('any_node',)),
        ('is_set_nodes_parameters_feasible', ('any_node', 'any_param')),
        ('is_set_lifecycle_state_feasible', ('any_node', 'inactive')),
        ('get_expression_satisfied', ('any_expression',)),
    ],
)
def test_decision_getters_propagate_query_error(
        method_name, args, monkeypatch, caplog):
    kb_interface = TacticalRetreatInterface.__new__(TacticalRetreatInterface)
    failing_db = type('FailingDB', (), {})()

    def _fail_fetch(_query: str):
        raise TypeDBQueryError(
            session_type='data',
            transaction_type='read',
            query_type='fetch',
            query='match $x isa thing; fetch { "x": $x; };')

    def _fail_aggregate(_query: str):
        raise TypeDBQueryError(
            session_type='data',
            transaction_type='read',
            query_type='get_aggregate',
            query='match $x isa thing; reduce $c = count;')

    monkeypatch.setattr(failing_db, 'fetch_database', _fail_fetch, raising=False)
    monkeypatch.setattr(
        failing_db, 'get_aggregate_database', _fail_aggregate, raising=False)
    kb_interface.db = failing_db

    with caplog.at_level('ERROR'):
        with pytest.raises(TypeDBQueryError):
            getattr(kb_interface, method_name)(*args)
