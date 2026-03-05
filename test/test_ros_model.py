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


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_ros_model',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql'],
        ['test/data/test_ros_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_ros_node_running(kb_interface):
    assert kb_interface.is_node_running('node_has_start_time') is True
    # assert kb_interface.is_node_running('node_no_start_time') is False
    assert kb_interface.is_node_running('node_has_end_time') is False


def test_get_measures_interfaces(kb_interface):
    measure_test_topic_dict = {
        'source': 'Publisher',
        'measure_name': 'measure_test_topic',
        'interface_name': '/measure_test_topic',
        'interface_type': 'std_msgs/msg/Float64',
        'measurement_function_name': 'get_data_field',
        'measurement_function_lib': 'ros_monitors_functions.monitor_functions',
        'measurement_function_args': 'data',
        'qos': {
            'reliability': 'RELIABLE',
            'history': 'KEEP_LAST',
            'depth': 10,
            'durability': 'TRANSIENT_LOCAL',
            'lifespan': 2,
            'deadline': 2,
            'liveliness': 'MANUAL_BY_TOPIC',
            'lease_duration': 2,
        }
    }

    laser_scan_dict = {
        'source': 'Publisher',
        'measure_name': 'measure_nearest_object',
        'interface_name': '/scan_filtered',
        'interface_type': 'sensor_msgs/msg/LaserScan',
        'measurement_function_name': 'get_nearest_scan_distance_in_base',
        'measurement_function_lib': 'ros_monitors_functions.laser_scan_functions',
        'measurement_function_args': 'base_link',
        'qos': {
            'reliability': 'BEST_EFFORT',
            'history': 'KEEP_LAST',
            'depth': 5,
            'durability': 'VOLATILE',
            'lifespan': 0,
            'deadline': 0,
            'liveliness': 'SYSTEM_DEFAULT',
            'lease_duration': 0,
        }}
    measures_interfaces = kb_interface.get_measures_interfaces()
    assert measure_test_topic_dict in measures_interfaces
    assert laser_scan_dict in measures_interfaces


def test_get_measures_interfaces_without_qos(kb_interface):
    measures_interfaces = kb_interface.get_measures_interfaces(include_qos=False)
    assert len(measures_interfaces) > 0
    for measure_interface in measures_interfaces:
        assert 'qos' not in measure_interface
