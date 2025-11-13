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

import time
import threading

import pytest

from lifecycle_msgs.srv import ChangeState
from lifecycle_msgs.srv import GetState

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from rclpy.qos import QoSDurabilityPolicy
from rclpy.qos import QoSLivelinessPolicy
from rclpy.qos import QoSHistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy

from std_msgs.msg import Float64
from std_srvs.srv import Empty

from typedb_tactics.tactical_retreat_kb import TacticalRetreatKB
from typedb_tactics.tactical_retreat_kb import _to_duration
from typedb_tactics.tactical_retreat_kb import get_ros_msg_type_from_string


def test_get_ros_msg_type_from_string():
    assert get_ros_msg_type_from_string('std_msgs/msg/Float64') == Float64
    assert get_ros_msg_type_from_string('std_msgs/Float64') == Float64

    assert get_ros_msg_type_from_string('std_srvs/srv/Empty') == Empty
    assert get_ros_msg_type_from_string('std_srvs/Empty', 'srv') == Empty


@pytest.fixture
def tactical_kb():
    tactical_kb = TacticalRetreatKB('tactical_kb')
    tactical_kb.init_typedb_interface(
        'localhost:1729',
        'tactical_kb',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql'],
        ['test/data/test_ros_model.tql'],
        force_database=True,
        force_data=True,
        infer=True
    )
    yield tactical_kb
    tactical_kb.destroy_node()


@pytest.fixture(scope='session', autouse=True)
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
        node.delete_database()
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

    def call_service(self, cli, request):
        if cli.wait_for_service(timeout_sec=5.0) is False:
            self.get_logger().error(
                'service not available {}'.format(cli.srv_name))
            return None
        future = cli.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if future.done() is False:
            self.get_logger().error(
                'Future not completed {}'.format(cli.srv_name))
            return None

        return future.result()

    def delete_database(self):
        self.call_service(self.delete_db_cli, Empty.Request())


def test_create_measure_topic_interface(executor, tactical_kb, test_node):
    executor.add_node(test_node)
    executor.add_node(tactical_kb)

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

    tactical_kb.create_measure_topic_interface(measure_test_topic_dict)
    assert 'measure_test_topic' in tactical_kb.measures_subscribers
    tactical_kb.create_measure_topic_interface(laser_scan_dict)
    assert 'measure_nearest_object' in tactical_kb.measures_subscribers

    pub_qos = QoSProfile(
        reliability=QoSReliabilityPolicy.RELIABLE,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=10,
        durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        lifespan=_to_duration(2.0),
        deadline=_to_duration(1.0),
        liveliness=QoSLivelinessPolicy.MANUAL_BY_TOPIC,
        liveliness_lease_duration=_to_duration(1.0)
    )

    from std_msgs.msg import Float64
    publisher = test_node.create_publisher(
        Float64,
        '/measure_test_topic',
        pub_qos
    )

    # Wait for discovery
    deadline = time.time() + 2.0
    while time.time() < deadline and publisher.get_subscription_count() == 0:
        time.sleep(0.02)

    publisher.publish(Float64(data=3.0))

    t_end = time.time() + 1.0
    while time.time() < t_end:
        time.sleep(0.1)

    measurement = tactical_kb.typedb_interface.get_latest_measurement(
        'measure_test_topic')
    assert measurement == 3.0
