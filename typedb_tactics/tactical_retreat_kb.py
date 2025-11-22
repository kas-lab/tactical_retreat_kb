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

import importlib
import inspect

from ros_typedb.ros_typedb_interface import ROSTypeDBInterface

from rclpy.duration import Duration
import rclpy
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from rclpy.qos import QoSDurabilityPolicy
from rclpy.qos import QoSLivelinessPolicy
from rclpy.qos import QoSHistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy
from std_srvs.srv import Trigger

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def publish_event(event_type: str):
    """Publish event (Decorator)."""
    def _publish_event(func):
        def inner(*args, **kwargs):
            args[0].publish_data_event(event_type)
            return func(*args, **kwargs)
        return inner
    return _publish_event


def get_ros_msg_type_from_string(msg_type_string: str, msg_type='msg'):
    msg_type_list = [part for part in msg_type_string.split('/') if part]

    if len(msg_type_list) == 2:
        package_name, message_name = msg_type_list
    elif len(msg_type_list) == 3:
        package_name = msg_type_list[0]
        msg_type = msg_type_list[1]
        message_name = msg_type_list[2]
    else:
        raise ValueError(
            f"Unsupported message type format: {msg_type_string}")

    msg_module = importlib.import_module(f"{package_name}.{msg_type}")
    return getattr(msg_module, message_name)


RELIABILITY_MAP = {
    "RELIABLE": QoSReliabilityPolicy.RELIABLE,
    "BEST_EFFORT": QoSReliabilityPolicy.BEST_EFFORT,
    "SYSTEM_DEFAULT": QoSReliabilityPolicy.SYSTEM_DEFAULT,
}

HISTORY_MAP = {
    "KEEP_LAST": QoSHistoryPolicy.KEEP_LAST,
    "KEEP_ALL": QoSHistoryPolicy.KEEP_ALL,
    "SYSTEM_DEFAULT": QoSHistoryPolicy.SYSTEM_DEFAULT,
}

DURABILITY_MAP = {
    "VOLATILE": QoSDurabilityPolicy.VOLATILE,
    "TRANSIENT_LOCAL": QoSDurabilityPolicy.TRANSIENT_LOCAL,
    "SYSTEM_DEFAULT": QoSDurabilityPolicy.SYSTEM_DEFAULT,
}

LIVELINESS_MAP = {
    "AUTOMATIC": QoSLivelinessPolicy.AUTOMATIC,
    "MANUAL_BY_TOPIC": QoSLivelinessPolicy.MANUAL_BY_TOPIC,
    "SYSTEM_DEFAULT": QoSLivelinessPolicy.SYSTEM_DEFAULT,
}


def _to_duration(v):
    # Accept Duration, seconds as int/float, or a dict {"sec": int, "nanosec":
    # int}
    if isinstance(v, Duration):
        return v
    if isinstance(v, (int, float)):
        secs = int(v)
        nsec = int(round((v - secs) * 1_000_000_000))
        return Duration(seconds=secs, nanoseconds=nsec)
    raise TypeError(f"Unsupported duration value: {v!r}")


def get_qos_from_qos_dict(qos_dict: dict) -> QoSProfile:
    # depth must be provided when KEEP_LAST; default to 10
    if qos_dict is None:
        return QoSProfile(depth=10)

    qos = QoSProfile(depth=int(qos_dict.get("depth", 10)))

    # Policies
    if 'reliability' in qos_dict:
        qos.reliability = RELIABILITY_MAP[qos_dict['reliability']]
    if 'history' in qos_dict:
        qos.history = HISTORY_MAP[qos_dict['history']]
    if 'durability' in qos_dict:
        qos.durability = DURABILITY_MAP[qos_dict['durability']]
    if 'liveliness' in qos_dict:
        qos.liveliness = LIVELINESS_MAP[qos_dict['liveliness']]

    # Durations (convert to Duration)
    if 'lifespan' in qos_dict:
        qos.lifespan = _to_duration(qos_dict['lifespan'])
    if 'deadline' in qos_dict:
        qos.deadline = _to_duration(qos_dict['deadline'])

    # Lease duration (portable across distros)
    lease_input = None
    if 'lease_duration' in qos_dict:
        lease_input = qos_dict['lease_duration']
    elif 'lease-duration' in qos_dict:
        lease_input = qos_dict['lease-duration']
    elif 'liveliness_lease_duration' in qos_dict:
        lease_input = qos_dict['liveliness_lease_duration']

    if lease_input is not None:
        d = _to_duration(lease_input)
        if hasattr(qos, 'lease_duration'):
            qos.lease_duration = d                # Iron+ or backports
        else:
            qos.liveliness_lease_duration = d     # Humble

    return qos


class TacticalRetreatKB(ROSTypeDBInterface):
    """ROS lifecycle node implementing TacticalRetreat's KB."""

    def __init__(self, node_name, **kwargs):
        """Create RosaKB node, inherits from :class:`ROSTypeDBInterface`."""
        self.active = False
        super().__init__(node_name, **kwargs)
        self.typedb_interface_class = TacticalRetreatInterface
        self.measures_subscribers = {}
        self.measures_clients = {}
        self.measures_timers = {}
        self.measures_services = {} # For proxies

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(self.get_name() + ': on_activate() is called.')
        self.active = True
        self.get_logger().info(
            self.get_name() + ': on_activate() is completed.')

        # self.create_measures_interfaces()
        def _create_measures_cb(_, res):
            try:
                self.get_logger().info("Creating measures interfaces...")
                self.create_measures_interfaces()
                self.get_logger().info("Measures interfaces created.")
                res.success = True
            except Exception as e:
                self.get_logger().error(
                    f"Error creating measures interfaces: {e}")
                res.success = False
            return res

        # TODO: pass the measure name as a string argument to fetch specific measurements
        def _fetch_all_measurements_cb(_, res):
            try:
                self.get_logger().info("Creating measures interfaces...")
                x = self.typedb_interface.fetch_all_measurements("current_velocity")
                self.get_logger().info("Measures interfaces created.")
                res.success = True
                res.message = str(x)
            except Exception as e:
                self.get_logger().error(
                    f"Error creating measures interfaces: {e}")
                res.success = False
            return res

        # create service with a lambda calling the create_measures_interfaces
        # function
        self.measures_service = self.create_service(
            Trigger,
            self.get_name() + '/create_measures',
            _create_measures_cb
        )

        self.all_measurements_service = self.create_service(
            Trigger,
            self.get_name() + '/fetch_all_measurements',
            _fetch_all_measurements_cb
        )

        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("on_deactivate() is called.")
        self.active = False
        self.destroy_service(self.measures_service)
        return super().on_deactivate(state)

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """
        Configure TacticalRetreatKB when the configure transition is called.

        :return: transition result
        """
        config_res = super().on_configure(state)
        return config_res

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """
        Cleanup TacticalRetreatKB when the cleanup transition is called.

        :return: transition result
        """
        self.active = False
        return super().on_cleanup(state)

    def create_measure_interface(self, interface):
        """
        Create a subscription for a measure topic using details in `topic_interface`.

        Expected keys:
        - 'measure_name' (str)
        - 'measurement_interface_name' (str)
        - 'measurement_interface_type' (str ROS msg type)
        - optional: 'measurement_function_lib' (str, module path)
        - optional: 'measurement_function_name' (str, callable name)
        - optional: 'measurement_function_args' (str, comma-separated args)
        - optional: 'qos' (dict for QoSProfile construction)
        """
        measure_name = interface['measure_name']
        interface_name = interface['interface_name']
        ros_msg_type_str = interface['interface_type']

        measurement_qos = get_qos_from_qos_dict(interface.get('qos', {}))

        function_lib_name = (interface.get('measurement_function_lib')
                             or 'ros_monitors_functions.monitor_functions')
        function_name = (interface.get('measurement_function_name')
                         or 'get_data_field')

        function_args_str = interface.get('measurement_function_args')
        function_args = [arg.strip() for arg in function_args_str.split(
            ',')] if function_args_str else []

        function_lib = importlib.import_module(function_lib_name)
        measure_function = getattr(function_lib, function_name)

        # Support both stateless functions and stateful callables (classes with __call__).
        if inspect.isclass(measure_function):
            # Instantiate once so state is preserved across callbacks.
            measure_callable = measure_function(*function_args)
            callable_args = []
        else:
            measure_callable = measure_function
            callable_args = function_args

        if (interface.get('source') == "Publisher"):
            topic_type = get_ros_msg_type_from_string(ros_msg_type_str, 'msg')

            def _cb(msg,
                    _measure_name=measure_name,
                    _measure_callable=measure_callable,
                    _function_args=callable_args):
                self.typedb_interface.add_measurement(
                    _measure_name, _measure_callable(
                        self, msg, *_function_args))

            self.measures_subscribers[measure_name] = self.create_subscription(
                topic_type,
                interface_name,
                _cb,
                measurement_qos,
                callback_group=self.query_cb_group
            )
        if (interface.get('source') == "Service"):
            service_type = get_ros_msg_type_from_string(ros_msg_type_str, 'srv')
            if (interface.get('measurement_proxy') is not True):
                service_request_kwargs_str = interface.get('service_request_kwargs')
                service_request_kwargs = {}
                if service_request_kwargs_str:
                    for kwarg in service_request_kwargs_str.split(','):
                        key, value = kwarg.split('=')
                        service_request_kwargs[key.strip()] = value.strip()
                if (interface.get('measurement_period')):
                    self.measures_clients[measure_name] = self.create_client(
                        service_type,
                        interface_name,
                        callback_group=self.query_cb_group
                    )

                    def _cb(_measure_name=measure_name,
                            _measure_callable=measure_callable,
                            _function_args=callable_args):
                        if (self.measures_clients[measure_name].wait_for_service(timeout_sec=10.0)):
                            request = service_type.Request(**service_request_kwargs)
                            self.measures_clients[measure_name].call_async(request).add_done_callback(
                                lambda future, _measure_name=_measure_name,
                                _measure_callable=_measure_callable,
                                _function_args=_function_args:
                                self.typedb_interface.add_measurement(
                                    _measure_name,
                                    _measure_callable(self, future.result(), *_function_args)))

                    self.measures_timers[measure_name] = self.create_timer(
                        interface['measurement_period'],
                        _cb)
            else:
                self.measures_clients[measure_name] = self.create_client(
                    service_type,
                    interface_name,
                    callback_group=self.query_cb_group
                )

                def _cb(request, response, _measure_name=measure_name,
                        _measure_callable=measure_callable,
                        _function_args=callable_args):
                    if (self.measures_clients[measure_name].wait_for_service(timeout_sec=10.0)):
                        future = self.measures_clients[measure_name].call_async(request)
                        # wait for future
                        rclpy.spin_until_future_complete(self, future)
                        self.typedb_interface.add_measurement(_measure_name, _measure_callable(
                            self,
                            future.result(),
                            *_function_args))
                        response = future.result()
                        return response

                self.measures_services[measure_name] = self.create_service(
                    service_type,
                    "proxy_" + interface_name,
                    _cb)  # The proxy service

    def create_measures_interfaces(self):
        try:
            measures_interfaces = self.typedb_interface.get_measures_interfaces()
            if (len(measures_interfaces) == 0):
                raise Exception("No measures interfaces to create.")

            for interface in measures_interfaces:
                self.get_logger().info(
                    f"Creating measure interface: {interface}")
                self.create_measure_interface(interface)

        except Exception as e:
            raise e
