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

import math
import threading
import time

from nav_msgs.msg import Odometry

import pytest

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy
from rclpy.qos import QoSHistoryPolicy
from rclpy.qos import QoSLivelinessPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy

from std_msgs.msg import Float64

from std_srvs.srv import Empty

from typedb_tactics.tactical_retreat_kb import _to_duration
from typedb_tactics.tactical_retreat_kb import get_ros_msg_type_from_string
from typedb_tactics.tactical_retreat_kb import TacticalRetreatKB


def test_get_ros_msg_type_from_string():
    assert get_ros_msg_type_from_string('std_msgs/msg/Float64') == Float64
    assert get_ros_msg_type_from_string('std_msgs/Float64') == Float64

    assert get_ros_msg_type_from_string('std_srvs/srv/Empty') == Empty
    assert get_ros_msg_type_from_string('std_srvs/Empty', 'srv') == Empty


@pytest.fixture(scope='module')
def tactical_kb():
    tactical_kb = TacticalRetreatKB('tactical_kb')
    tactical_kb.init_typedb_interface(
        'localhost:1729',
        'tactical_kb',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/logical_expressions/fuzzy_expression.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/feature_model/feature_model_logical_expression.tql',
            'schemas/relaxed/relaxed_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_hypothetical_req_fulfillment/'
            'discover_hypothetical_req_fulfillment.tql',
            'schemas/states/states.tql'],
        ['test/data/test_ros_model.tql'],
        force_database=True,
        force_data=True,
        infer=True
    )
    yield tactical_kb
    tactical_kb.typedb_interface.delete_database()
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


@pytest.fixture(scope='module')
def test_node():
    node = HelperNode()
    try:
        yield node
    finally:
        node.destroy_node()


@pytest.fixture(scope='module')
def executor(tactical_kb, test_node):
    ex = MultiThreadedExecutor()
    t = threading.Thread(target=ex.spin, daemon=True)
    t.start()
    try:
        ex.add_node(tactical_kb)
        ex.add_node(test_node)
        yield ex
    finally:
        ex.shutdown()
        t.join(timeout=2.0)


class HelperNode(Node):

    def __init__(self, name='test_node'):
        super().__init__(name)

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


def test_create_measure_topic_interface(executor, tactical_kb, test_node):

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

    tactical_kb.create_measure_interface(measure_test_topic_dict)
    assert 'measure_test_topic' in tactical_kb.measures_subscribers

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

    tactical_kb.create_measure_interface(laser_scan_dict)
    assert 'measure_nearest_object' in tactical_kb.measures_subscribers

    odom_dict = {
        'source': 'Publisher',
        'measure_name': 'measure_mean_velocity',
        'interface_name': '/odom',
        'interface_type': 'nav_msgs/msg/Odometry',
        'measurement_function_name': 'MeanLinearVelocity',
        'measurement_function_lib': 'ros_monitors_functions.odom_functions',
        'measurement_function_args': '5.0',
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

    tactical_kb.create_measure_interface(odom_dict)
    assert 'measure_mean_velocity' in tactical_kb.measures_subscribers

    tactical_kb.create_timer(
        1.0,
        tactical_kb.measurement_processing,
        callback_group=tactical_kb.query_cb_group
    )

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

    deadline = time.time() + 5.0
    measurement = float('nan')

    while time.time() < deadline:
        measurement = tactical_kb.typedb_interface.get_latest_measurement(
            'measure_test_topic')
        if measurement == 3.0:
            break
        time.sleep(0.05)

    assert measurement == 3.0

    odom_publisher = test_node.create_publisher(
        Odometry,
        '/odom',
        pub_qos
    )

    # Wait for discovery
    deadline = time.time() + 2.0
    while time.time() < deadline and odom_publisher.get_subscription_count() == 0:
        time.sleep(0.02)

    # Simulate odom messages at different timestamps
    timestamps = [1.0, 1.5, 2.0, 3.0, 4.0]  # in seconds
    linear_x_values = [0.0, 0.01, 0.02, 0.03, 0.04]
    linear_y_values = [0.0, 0.01, 0.02, 0.03, 0.04]
    # mean_velocities = [0.0, 0.00707105, 0.014142136, 0.021213203, 0.028284271]

    for ts, lx, ly in zip(timestamps, linear_x_values, linear_y_values):
        odom_msg = Odometry()
        odom_msg.header.stamp.sec = int(ts)
        odom_msg.header.stamp.nanosec = int((ts - int(ts)) * 1e9)
        odom_msg.twist.twist.linear.x = lx
        odom_msg.twist.twist.linear.y = ly

        # mean_velocity = mean_vel_monitor(None, odom_msg)
        odom_publisher.publish(odom_msg)

        # Manually compute expected mean velocity over the window
        window_start = ts - 5.0
        relevant_speeds = [
            math.hypot(abs(lx_val), abs(ly_val))
            for t, lx_val, ly_val in zip(timestamps, linear_x_values, linear_y_values)
            if t >= window_start and t <= ts
        ]
        expected_mean = sum(relevant_speeds) / len(relevant_speeds) if relevant_speeds else 0.0

        deadline = time.time() + 5.0
        measurement = float('nan')

        while time.time() < deadline:
            measurement = tactical_kb.typedb_interface.get_latest_measurement(
                'measure_mean_velocity')
            if measurement == pytest.approx(expected_mean):
                break
            time.sleep(0.05)

        assert measurement == pytest.approx(expected_mean)


def test_create_measure_interface_service(executor, tactical_kb, test_node):

    from std_srvs.srv import Trigger

    def _cb(_, response):
        response.success = True
        response.message = 'Test message'
        return response

    _ = test_node.create_service(
        Trigger,
        '/measure_test_service',
        _cb
    )

    measure_test_service_dict = {
        'source': 'ServiceServer',
        'measure_name': 'measure_test_service',
        'interface_name': '/measure_test_service',
        'interface_type': 'std_srvs/srv/Trigger',
        'measurement_function_name': 'get_data_field',
        'measurement_function_lib': 'ros_monitors_functions.monitor_functions',
        'measurement_function_args': 'success',
        'measurement_proxy': False,
        'measurement_period': 1,
    }

    tactical_kb.create_measure_interface(measure_test_service_dict)
    assert 'measure_test_service' in tactical_kb.measures_clients

    tactical_kb.create_timer(
        1.0,
        tactical_kb.measurement_processing,
        callback_group=tactical_kb.query_cb_group
    )

    deadline = time.time() + 5.0
    service_result = False
    while time.time() < deadline:
        service_result = tactical_kb.typedb_interface.get_latest_measurement(
            'measure_test_service')
        if service_result is True:
            break
        time.sleep(0.05)
    assert service_result is True


def test_create_proxy(executor, tactical_kb, test_node):

    from std_srvs.srv import Trigger

    def _cb(_, response):
        response.success = True
        response.message = 'Test message'
        return response

    _ = test_node.create_service(
        Trigger,
        '/measure_test_service',
        _cb
    )  # this is the original service that will be proxied

    measure_test_service_dict = {
        'source': 'ServiceServer',
        'measure_name': 'measure_test_service',
        'interface_name': '/measure_test_service',
        'interface_type': 'std_srvs/srv/Trigger',
        'measurement_function_name': 'get_data_field',
        'measurement_function_lib': 'ros_monitors_functions.monitor_functions',
        'measurement_function_args': 'message',
        'measurement_proxy': True,
        'measurement_period': 1,
    }

    tactical_kb.create_measure_interface(measure_test_service_dict)
    assert 'measure_test_service' in tactical_kb.measures_clients

    tactical_kb.create_timer(
        1.0,
        tactical_kb.measurement_processing,
        callback_group=tactical_kb.query_cb_group
    )

    service_client = test_node.create_client(
        Trigger,
        'proxy_' + measure_test_service_dict['interface_name']
    )

    assert service_client.wait_for_service(timeout_sec=5.0)
    request = Trigger.Request()
    future = service_client.call_async(request)
    rclpy.spin_until_future_complete(test_node, future, timeout_sec=5.0)
    assert future.done()

    expected_msg = future.result().message

    deadline = time.time() + 5.0
    service_result = False
    while time.time() < deadline:
        service_result = tactical_kb.typedb_interface.get_latest_measurement(
            'measure_test_service')
        if service_result == expected_msg:
            break
        time.sleep(0.05)
    assert service_result == expected_msg
