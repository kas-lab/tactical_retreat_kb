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


@pytest.fixture(scope="module")
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_ros_model',
        ['typedb/data_structure/data_structure.tql',
            'typedb/context_model/context_model.tql',
            'typedb/ros_model/ros_model.tql'],
        ['test/data/test_ros_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_ros_node_running(kb_interface):
    assert kb_interface.is_node_running('node_has_start_time') is True
    assert kb_interface.is_node_running('node_no_start_time') is False
    assert kb_interface.is_node_running('node_has_end_time') is False
