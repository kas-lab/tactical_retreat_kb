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
		["typedb/ros_model.tql"],
		["typedb/ros_model_example.tql"],
		force_database=True,
		force_data=True,
		infer=True
	)
	return kb_interface

def test_request_action(kb_interface):
    subnodes = kb_interface.get_subnodes('bt_navigator')
    assert len(subnodes) == 2
    assert subnodes[0]['namespace'] == ''
    assert subnodes[0]['node_name'] == 'bt_navigator_navigate_through_poses_rclcpp'
    assert subnodes[1]['namespace'] == ''
    assert subnodes[1]['node_name'] == 'bt_navigator_navigate_to_pose_rclcpp'
