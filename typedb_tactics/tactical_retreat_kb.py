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
import json
import time
import traceback

from adapt_x_msgs.srv import FetchResolutions
from adapt_x_msgs.srv import FetchPlan
from adapt_x_msgs.srv import FetchRules
from adapt_x_msgs.srv import HypotheticalReqFulfillment
from adapt_x_msgs.srv import HypotheticalReqsFulfillment
from adapt_x_msgs.srv import RequirementsFulfillment
from adapt_x_msgs.srv import SatisfiedRule
from adapt_x_msgs.srv import UpdateHasParamValue
from adapt_x_msgs.srv import UpdateInEffect
from adapt_x_msgs.srv import UpdateRunning
from adapt_x_msgs.srv import GetState
from adapt_x_msgs.msg import RelaxedRequirement
from adapt_x_msgs.msg import RelaxedRequirements
from adapt_x_msgs.msg import SymbolicState
from adapt_x_msgs.msg import TableEntry
from adapt_x_msgs.msg import Resolution
from adapt_x_msgs.msg import TacticRule
from adapt_x_msgs.srv import FetchPolicy

from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.duration import Duration
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.qos import QoSDurabilityPolicy
from rclpy.qos import QoSHistoryPolicy
from rclpy.qos import QoSLivelinessPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy
from rebet_monitors.rebet_monitors import is_too_close
from rebet_monitors.rebet_monitors import MovementPowerDraw
from rebet_monitors.rebet_monitors import PowerBudget
from ros_monitors_functions.global_costmap_functions import GlobalCostmapChange, StableCostmap
from ros_monitors_functions.system_monitors_funtions import AverageCPULoad1min
from ros_monitors_functions.path_functions import average_curvature

from ros_monitors_functions.factory import MonitorFactory
from ros_typedb.ros_typedb_interface import ROSTypeDBInterface
from std_msgs.msg import Header
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
            f'Unsupported message type format: {msg_type_string}')

    msg_module = importlib.import_module(f'{package_name}.{msg_type}')
    return getattr(msg_module, message_name)


RELIABILITY_MAP = {
    'RELIABLE': QoSReliabilityPolicy.RELIABLE,
    'BEST_EFFORT': QoSReliabilityPolicy.BEST_EFFORT,
    'SYSTEM_DEFAULT': QoSReliabilityPolicy.SYSTEM_DEFAULT,
}

HISTORY_MAP = {
    'KEEP_LAST': QoSHistoryPolicy.KEEP_LAST,
    'KEEP_ALL': QoSHistoryPolicy.KEEP_ALL,
    'SYSTEM_DEFAULT': QoSHistoryPolicy.SYSTEM_DEFAULT,
}

DURABILITY_MAP = {
    'VOLATILE': QoSDurabilityPolicy.VOLATILE,
    'TRANSIENT_LOCAL': QoSDurabilityPolicy.TRANSIENT_LOCAL,
    'SYSTEM_DEFAULT': QoSDurabilityPolicy.SYSTEM_DEFAULT,
}

LIVELINESS_MAP = {
    'AUTOMATIC': QoSLivelinessPolicy.AUTOMATIC,
    'MANUAL_BY_TOPIC': QoSLivelinessPolicy.MANUAL_BY_TOPIC,
    'SYSTEM_DEFAULT': QoSLivelinessPolicy.SYSTEM_DEFAULT,
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
    raise TypeError(f'Unsupported duration value: {v!r}')


def get_qos_from_qos_dict(qos_dict: dict) -> QoSProfile:
    # depth must be provided when KEEP_LAST; default to 10
    if qos_dict is None:
        return QoSProfile(depth=1)

    # qos = QoSProfile(depth=int(qos_dict.get('depth', 1)))
    qos = QoSProfile(depth=1)

    # Policies
    if 'reliability' in qos_dict:
        qos.reliability = RELIABILITY_MAP[qos_dict['reliability']]
    if 'history' in qos_dict:
        qos.history = HISTORY_MAP['KEEP_LAST']  # change back
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
        self.measures_services = {}  # For proxies
        self.context_dict = {
            'nearest_object': 'unknown',
            'power_draw': 'unknown',
            'current_velocity': 'unknown'
        }
        self.measurements = {}
        # Create all possible combinations of contexts
        self.context_combinations = self._generate_context_combinations()
        self.monitor = MonitorFactory()
        self.monitor.register_monitor(
            'MovementPowerDraw', MovementPowerDraw)
        self.monitor.register_monitor(
            'PowerBudget', PowerBudget)
        self.monitor.register_monitor(
            'is_too_close', is_too_close
        )
        self.monitor.register_monitor(
            'GlobalCostmapChange', GlobalCostmapChange
        )
        self.monitor.register_monitor(
            'StableCostmap', StableCostmap
        )
        self.monitor.register_monitor(
            'AverageCPULoad1min', AverageCPULoad1min
        )
        self.monitor.register_monitor(
            'average_curvature', average_curvature
        )
        self.declare_parameter("do_states", True)

    def create_header(self):
        return Header(stamp=self.get_clock().now().to_msg())

    def _generate_context_combinations(self):
        """Generate all possible context combinations and assign indices."""
        nearest_object_states = ['near', 'there', 'far']
        power_draw_states = ['off', 'drain']
        current_velocity_states = ['slow', 'fast']

        combinations = {}
        idx = 0
        for nearest in nearest_object_states:
            for power in power_draw_states:
                for velocity in current_velocity_states:
                    combinations[(nearest, power, velocity)] = idx
                    idx += 1
        return combinations

    def _get_context_combination_id(self):
        """Get the current context combination ID."""
        current_combo = (
            self.context_dict['nearest_object'],
            self.context_dict['power_draw'],
            self.context_dict['current_velocity']
        )
        return self.context_combinations.get(current_combo, -1)

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        super().get_logger().info(self.get_name() + ': on_activate() is called.')

        self.active = True
        self.get_logger().info(
            self.get_name() + ': on_activate() is not yet completed.')

        self.doing_states = self.get_parameter("do_states").value

        self.get_logger().info(f": are we doing states? {self.doing_states}")
        pub_qos = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                             history=QoSHistoryPolicy.KEEP_LAST,
                             depth=3)
        self.reqs_publisher = self.create_publisher(
            RelaxedRequirements, 'requirements', qos_profile=pub_qos)

        self.prev_state = None
        # self.create_measures_interfaces()

        def _create_measures_cb(_, res):
            try:
                self.get_logger().info('Creating measures interfaces...')
                self.create_measures_interfaces()
                self.get_logger().info('Measures interfaces created.')
                res.success = True
            except Exception as e:
                self.get_logger().error(
                    f'Error creating measures interfaces: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_applicable_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching applicable tactics...')
                result = self.typedb_interface.get_applicable_tactics(
                    req.resolution_model, req.interface_name)

                res.tactic_rules = [TacticRule(name=rule_name, reconfigurations=fa_list)
                                    for rule_name, fa_list in result.items()]
                elapsed_time = time.perf_counter() - start_time
                res.success = True

                self.get_logger().info(
                    f'Applicable tactics fetched {str(res)}')

                self.get_logger().info(
                    f'Applicable tactics fetched in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching applicable tactics: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_satisfied_tactic_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching satisfied tactics...')
                result = self.typedb_interface.get_satisfied_tactics(
                    req.tactic_rules)
                res.satisfied = result
                res.success = True
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'Satisfied tactics fetched in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching Satisfied tactics : {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_actions_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching all resolution actions...')
                x = self.typedb_interface.get_resolution_adaptations()
                res.resolutions = []
                for name, adaptations in x.items():
                    res.resolutions.append(
                        Resolution(resolution_action_name=name, adaptations=adaptations))

                elapsed_time = time.perf_counter() - start_time
                res.success = True
                self.get_logger().info(
                    f'Tactic actions fetched in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching tactic actions: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_reconfiguration_plan_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching tactic actions...')
                # res.adaptations = self.typedb_interface.get_reconfiguration_plan(req.tactic_name).actions
                vation = "activation" if req.activation else "deactivation"
                x = self.typedb_interface.get_reconfiguration_plan_compact(req.feature_name, vation)
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'Tactic actions {x} fetched in {elapsed_time:.4f} seconds.')
                res.resolution_actions = x
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching tactic actions: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
            return res

        # TODO: Implement properly.

        def _fetch_all_measurements_cb(_, res):
            pass

        def _update_running_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Updating running nodes...')
                self.typedb_interface.manual_running_nodes(req.node_names)
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'Running nodes updated in {elapsed_time:.4f} seconds.')
                res.success = True
            except Exception as e:
                self.get_logger().error(
                    f'Error updating running nodes: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_req_fullfillment_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching requirements fulfillment...')

                fulfillments = self.typedb_interface.get_relaxed_requirements_fulfillment(
                    req.system_name, *req.requirement_names)

                res.fulfillment_values = fulfillments
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'Requirements fulfillment fetched in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching requirements fulfillment: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
            return res

        def _fetch_req_hyp_req_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Fetching hypothetical requirement fulfillment...')

                interface = self.typedb_interface
                fulfillment = interface.get_relaxed_requirement_hypothetical_fulfillment(
                    req.system_name, req.requirement_name, req.rule_name)

                res.fulfillment_value = float(fulfillment)
                res.success = True
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    'Requirements hypothetical fulfillment fetched in '
                    f'{elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching requirements fulfillment: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
            return res

        def _fetch_req_hyp_reqs_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info(
                    '\n\nFetching hypothetical requirements fulfillment...'
                    f'{str(req.rule_names)}')

                interface = self.typedb_interface
                fulfillment = interface.get_relaxed_requirements_hypothetical_fulfillment(
                    req.rule_names, req.system_name)

                res.fulfillment_dict = json.dumps(fulfillment)
                res.success = True
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    'Requirements hypothetical fulfillment fetched in '
                    f'{elapsed_time:.4f} seconds.\n\n')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching requirements fulfillment: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
            return res
        # def _fetch_req_fullfillment_ineffect_cb(self, req, res):
        #     try:
        #         start_time = time.perf_counter()
        #         self.get_logger().info('Fetching requirements with in_effect fulfillment...')

        #         fulfillments = self.typedb_interface.get_in_effect_requirement_fulfillment()

        #         res.fulfillment_values = [ful['fulfillment'] for ful in fulfillments]
        #         elapsed_time = time.perf_counter() - start_time
        #         self.get_logger().info(
        #             f'Requirements fulfillment fetched in effect {elapsed_time:.4f} seconds.')
        #     except Exception as e:
        #         self.get_logger().error(
        #             f'Error fetching requirements fulfillment: {e}')
        #         self.get_logger().error("Traceback:\n" + traceback.format_exc())
        #     return res

        def _update_in_effect_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Updating in-effect requirements...')
                self.typedb_interface.update_requirements_in_effect(
                    req.requirement_names, req.all_requirements)
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'In-effect requirements updated in {elapsed_time:.4f} seconds.')
                res.success = True
            except Exception as e:
                self.get_logger().error(
                    f'Error updating in-effect requirements: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _update_has_param_value_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Updating has_param_value...')
                query_res = self.typedb_interface.update_feature_selected_by_param_value(
                    req.feature_name)
                self.get_logger().info(
                    f'update_feature_selected_by_param_value result: {query_res}')
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'has_param_value updated in {elapsed_time:.4f} seconds.')
                res.success = True
            except Exception as e:
                self.get_logger().error(
                    f'Error updating has_param_value: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_current_state_cb(_, res):
            try:
                start_time = time.perf_counter()
                # self.get_logger().info('Getting current state...')
                current_state_string = self.typedb_interface.get_current_state()
                # self.get_logger().info(
                #     f'current_state result: {current_state_string}')
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'current_state retrieved in {elapsed_time:.4f} seconds.')
                res.success = True
                res.message = current_state_string
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching state: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_current_state_action_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Getting current state...')
                current_state_string = self.typedb_interface.get_current_state_action(req.action_name)
                res.success = False
                if (current_state_string is not None):
                    res.current_state = SymbolicState(state_name=str(current_state_string),
                                                      header=self.create_header())
                    res.success = True
                self.get_logger().info(
                    f'current_state result: {current_state_string}')
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f'current_state retrieved in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error fetching state: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        def _fetch_policy_cb(req, res):
            try:
                start_time = time.perf_counter()
                self.get_logger().info('Getting rules for action...')
                state_dict, table, reconfigurations = self.typedb_interface.get_fetch_policy(req.action_name)
                entries = []

                for (fa, s), r in table.items():
                    t = TableEntry(state=SymbolicState(state_name=s),
                                   feature_adaptation=fa, rule_name=r)
                    entries.append(t)

                states = [SymbolicState(state_name=p[0])
                          for p in state_dict.items()]
                res.table_entries = entries
                res.states = states
                res.reconfigurations = reconfigurations
                res.success = True
                elapsed_time = time.perf_counter() - start_time
                self.get_logger().info(
                    f' " retrieved in {elapsed_time:.4f} seconds.')
            except Exception as e:
                self.get_logger().error(
                    f'Error getting rules fpr action: {e}')
                self.get_logger().error('Traceback:\n' + traceback.format_exc())
                res.success = False
            return res

        # create service with a lambda calling the create_measures_interfaces
        # function
        self.measures_service = self.create_service(
            Trigger,
            self.get_name() + '/create_measures',
            _create_measures_cb,
            callback_group=self.query_cb_group
        )

        self.applicable_tactics_service = self.create_service(
            FetchRules,
            self.get_name() + '/fetch_rules',
            _fetch_applicable_cb,
            callback_group=self.query_cb_group
        )

        self.get_state = self.create_service(
            GetState,
            self.get_name() + '/get_state',
            _fetch_current_state_action_cb,
            callback_group=self.query_cb_group
        )

        # self.requirements_fulfillment_service = self.create_service(
        #     RequirementsFulfillment,
        #     self.get_name() + '/fetch_requirements_fulfillment',
        #     _fetch_req_fullfillment_cb
        # )

        # self.requirements_fulfillment_ineffect_service = self.create_service(
        #     RequirementsFulfillment,
        #     self.get_name() + '/fetch_requirements_fulfillment_ineffect',
        #     lambda req, res: _fetch_req_fullfillment_ineffect_cb(self, req, res)
        # )

        self.hyp_requirements_fulfillment_service = self.create_service(
            HypotheticalReqFulfillment,
            self.get_name() + '/fetch_hyp_requirement',
            _fetch_req_hyp_req_cb,
            callback_group=self.query_cb_group
        )

        # self.current_state_service = self.create_service(
        #     Trigger,
        #     self.get_name() + '/get_current_state',
        #     _fetch_current_state_cb,
        #     callback_group=self.query_cb_group
        # )

        self.hyp_requirements_fulfillment_service = self.create_service(
            HypotheticalReqsFulfillment,
            self.get_name() + '/fetch_hyp_requirements',
            _fetch_req_hyp_reqs_cb,
            callback_group=self.query_cb_group
        )

        self.satisfied_tactic_service = self.create_service(
            SatisfiedRule,
            self.get_name() + '/satisfied_tactic',
            _fetch_satisfied_tactic_cb,
            callback_group=self.query_cb_group
        )

        self.tactic_actions_service = self.create_service(
            FetchResolutions,
            self.get_name() + '/fetch_resolutions',
            _fetch_actions_cb,
            callback_group=self.query_cb_group
        )

        self.adaptation_plan_service = self.create_service(
            FetchPlan,
            self.get_name() + '/fetch_plan',
            _fetch_reconfiguration_plan_cb,
            callback_group=self.query_cb_group
        )

        self.update_running_service = self.create_service(
            UpdateRunning,
            self.get_name() + '/update_running',
            _update_running_cb,
            callback_group=self.query_cb_group
        )

        self.update_in_effect_service = self.create_service(
            UpdateInEffect,
            self.get_name() + '/update_in_effect',
            _update_in_effect_cb,
            callback_group=self.query_cb_group
        )

        self.update_has_param_value_service = self.create_service(
            UpdateHasParamValue,
            self.get_name() + '/update_has_param_value',
            _update_has_param_value_cb,
            callback_group=self.query_cb_group
        )

        # self.all_measurements_service = self.create_service(
        #     Trigger,
        #     self.get_name() + '/fetch_all_measurements',
        #     _fetch_all_measurements_cb
        # )

        self.fetch_rules_for_action_service = self.create_service(
            FetchPolicy,
            self.get_name() + '/fetch_policy',
            _fetch_policy_cb,
            callback_group=self.query_cb_group
        )

        self.get_logger().info(
            self.get_name() + ': on_activate() is completing.')

        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('on_deactivate() is called.')
        self.active = False
        self.destroy_service(self.measures_service)
        return super().on_deactivate(state)

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """
        Configure TacticalRetreatKB when the configure transition is called.

        :return: transition result
        """
        config_res = super().on_configure(state)
        super().get_logger().info('I have arisen')
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

        measurement_qos = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                                     history=QoSHistoryPolicy.KEEP_LAST,
                                     depth=3)
        # get_qos_from_qos_dict(interface.get('qos', {}))

        # function_lib_name = (interface.get('measurement_function_lib')
        #                      or 'ros_monitors_functions.monitor_functions')
        function_name = (interface.get('measurement_function_name')
                         or 'get_data_field')

        function_args_str = interface.get('measurement_function_args')
        function_args = [arg.strip() for arg in function_args_str.split(
            ',')] if function_args_str else []

        # function_lib = self.monitor[function_lib_name]
        # importlib.import_module(function_lib_name)
        measure_function = self.monitor[function_name]
        # getattr(function_lib, function_name)

        # Support both stateless functions and stateful callables (classes with
        # __call__).
        if inspect.isclass(measure_function):
            # Instantiate once so state is preserved across callbacks.
            measure_callable = measure_function(*function_args)
            callable_args = []
        else:
            measure_callable = measure_function
            callable_args = function_args

        if (interface.get('source') == 'Publisher'):
            topic_type = get_ros_msg_type_from_string(ros_msg_type_str, 'msg')
            super().get_logger().info(
                f'Making a subscription for measure: {measure_name}')

            def topic_cb(msg, _node=super(), _measure_name=measure_name,
                         _measure_callable=measure_callable,
                         _function_args=callable_args):
                res = _measure_callable(self, msg, *_function_args)
                # self.typedb_interface.add_measurement(
                #     _measure_name, res)
                # _node.get_logger().info(
                #     f"measure_name called: {_measure_name}",
                #     throttle_duration_sec=1)
                self.measurements[_measure_name] = res

                # I want to consider the unique combination of each category as
                # a unique context, so I will publish an event with the current
                # context whenever a measure is updated.

                # current_context_msg = String()
                # combo_id = self._get_context_combination_id()
                # current_context = (
                #     self.context_dict["nearest_object"],
                #     self.context_dict["power_draw"],
                #     self.context_dict["current_velocity"])
                # # _node.get_logger().info(
                #     f"Current context: {current_context}, combo_id: {combo_id}",
                #     throttle_duration_sec=2)
                # current_context_msg.data = str(combo_id)
                # self.context_publisher.publish(current_context_msg)

            self.measures_subscribers[measure_name] = self.create_subscription(
                topic_type,
                interface_name,
                topic_cb,
                measurement_qos,
                callback_group=self.query_cb_group
            )
        if (interface.get('source') == 'ServiceServer'):
            service_type = get_ros_msg_type_from_string(
                ros_msg_type_str, 'srv')
            if (interface.get('measurement_proxy') is not True):
                super().get_logger().info(
                    f'Creating service client for: {interface_name}')
                service_request_kwargs_str = interface.get(
                    'service_request_kwargs')
                service_request_kwargs = {}
                if service_request_kwargs_str:
                    for kwarg in service_request_kwargs_str.split(','):
                        key, value = kwarg.split('=')
                        service_request_kwargs[key.strip()] = value.strip()
                if (interface.get('measurement_period')):
                    self.measures_clients[measure_name] = self.create_client(
                        service_type,
                        interface_name,
                        callback_group=MutuallyExclusiveCallbackGroup()
                    )

                    def srv_cb(_measure_name=measure_name,
                               _measure_callable=measure_callable,
                               _function_args=callable_args):
                        if (self.measures_clients[_measure_name].wait_for_service(
                           timeout_sec=10.0)):
                            request = service_type.Request(
                                **service_request_kwargs)

                            def _on_done(
                                    future,
                                    _measure_name=_measure_name,
                                    _measure_callable=_measure_callable,
                                    _function_args=_function_args,
                                    _measurements=self.measurements):
                                _measurements[_measure_name] = _measure_callable(
                                    self,
                                    future.result(),
                                    *_function_args
                                )

                            self.measures_clients[_measure_name].call_async(
                                request).add_done_callback(_on_done)
                    self.measures_timers[measure_name] = self.create_timer(
                        interface['measurement_period'],
                        srv_cb)
            else:
                super().get_logger().info(
                    f'Creating proxy service for: {interface_name}')
                self.measures_clients[measure_name] = self.create_client(
                    service_type,
                    interface_name,
                    callback_group=self.query_cb_group
                    # callback_group=MutuallyExclusiveCallbackGroup()
                )

                async def _cb(request, response, _measure_name=measure_name,
                              _measure_callable=measure_callable,
                              _function_args=callable_args):
                    if (self.measures_clients[measure_name].wait_for_service(
                            timeout_sec=10.0)):
                        proxied_response = await self.measures_clients[
                            measure_name].call_async(request)
                        self.measurements[_measure_name] = _measure_callable(
                            self,
                            proxied_response,
                            *_function_args)
                        return proxied_response
                    return response

                self.measures_services[measure_name] = self.create_service(
                    service_type,
                    'proxy_' + interface_name,
                    _cb)  # The proxy service

    def create_measures_interfaces(self):
        try:
            measures_interfaces = self.typedb_interface.get_measures_interfaces()
            if (len(measures_interfaces) == 0):
                raise Exception('No measures interfaces to create.')

            for interface in measures_interfaces:
                super().get_logger().info(
                    f'Creating measure interface: {interface}')
                self.create_measure_interface(interface)

            self.create_timer(
                1.0,
                self.measurement_processing,
                callback_group=self.query_cb_group)
            self.create_timer(2.0, self.publish_fulfillments,
                              callback_group=self.query_cb_group)

        except Exception as e:
            raise e

    def measurement_processing(self):
        if self.measurements:
            self.get_logger().info(f"measurements {str(self.measurements)}", throttle_duration_sec=5)
            filtered_measurements = {k: v for (k, v) in self.measurements.items() if v is not None}
            if (filtered_measurements):
                self.typedb_interface.add_measurements(filtered_measurements, self.get_logger())
                return
        self.get_logger().info("No measurements to process", throttle_duration_sec=10)

    def publish_fulfillments(self):
        reqs = self.typedb_interface.get_in_effect_requirement_fulfillment()
        if (reqs):
            reqs_msgs = []
            for req in reqs:
                if (req["fulfillment"] is not None):

                    req_msg = RelaxedRequirement(name=req['requirement_name'],
                                                 fulfillment=req["fulfillment"],
                                                 system_name=req["system"])
                    reqs_msgs.append(req_msg)

            if (len(reqs_msgs) > 0):
                reqs_msg = RelaxedRequirements(header=self.create_header(), requirements=reqs_msgs)
                # self.get_logger().info("publishing reqs")
                self.reqs_publisher.publish(reqs_msg)
                return
        self.get_logger().info("No fulfillments to published", throttle_duration_sec=10)
