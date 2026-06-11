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
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Sequence
from typing import TypeAlias
from typing import cast
from execution_layer_msgs.msg import Adaptation
from ros_typedb.typedb_interface import convert_query_type_to_py_type
from lifecycle_msgs.msg import Transition
from rclpy.parameter import Parameter

ParamScalar: TypeAlias = str | float | int | bool
ParamValue: TypeAlias = ParamScalar | list[ParamScalar]
LifecycleState: TypeAlias = Literal[
    'active', 'inactive', 'unconfigured', 'finalized']

# TODO: Redesign, see issue #88
names_to_transitions = {
    'active': Transition(id=Transition.TRANSITION_ACTIVATE),
    'inactive': Transition(id=Transition.TRANSITION_DEACTIVATE),
    # 'unconfigured' : Transition(id=Transition.TRANSITION_ACTIVE_SHUTDOWN),
    'finalized': Transition(id=Transition.TRANSITION_ACTIVE_SHUTDOWN)
}


@dataclass(slots=True)
class AdaptationPlan:
    # A possible improvement is to make actions a graph
    actions: list[Adaptation]

    @classmethod
    def from_typedb_results(
        cls,
        raw_actions: Sequence[dict[str, Any]]
    ) -> AdaptationPlan:
        """
        Build an AdaptationPlan from the raw list returned by TypeDB fetch.

        :param raw_actions: list of action dicts that include an ``index`` entry
            plus either ``set_lifecycle_action`` or ``set_parameter_action``.
        """
        actions_with_index: list[tuple[int, Adaptation]] = []

        for entry in raw_actions:
            # cast is used to get rid of pylance type warning
            index_value = cast(int, convert_query_type_to_py_type(entry['index']))

            for lifecycle_entry in entry.get('set_lifecycle_action', []):
                actions_with_index.append(
                    (index_value, _parse_lifecycle_action(lifecycle_entry)))

            for parameter_entry in entry.get('set_parameter_action', []):
                actions_with_index.append(
                    (index_value, _parse_parameter_action(parameter_entry)))

        ordered_actions = [
            action for _, action in sorted(actions_with_index, key=lambda pair: pair[0])
        ]
        return cls(actions=ordered_actions)

    @classmethod
    def from_feature_plan_results(
        cls,
        steps_with_results: list[tuple[int, dict[str, Any]]]
    ) -> AdaptationPlan:
        """
        Build an AdaptationPlan from (execution_index, typedb_result_dict) pairs.

        :param steps_with_results: list of (index, result_dict) where result_dict
            has 'set_lifecycle_action' and/or 'set_parameter_action' keys and
            index is the execution wave from ReconfigurationStep.
        """
        actions_with_index: list[tuple[int, Adaptation]] = []
        for index_value, entry in steps_with_results:
            for lifecycle_entry in entry.get('set_lifecycle_action', []):
                actions_with_index.append(
                    (index_value, _parse_lifecycle_action(lifecycle_entry)))
            for parameter_entry in entry.get('set_parameter_action', []):
                actions_with_index.append(
                    (index_value, _parse_parameter_action(parameter_entry)))
        ordered_actions = [
            action for _, action in sorted(actions_with_index, key=lambda pair: pair[0])
        ]
        return cls(actions=ordered_actions)


def _parse_lifecycle_action(
    raw_action: dict[str, Any]
) -> Adaptation:
    node_name = raw_action['node']['node_name'][0]['value']
    lifecycle_state = raw_action['res_action']['lifecycle_state'][0]['value']

    return Adaptation(
        target_type_str='execution_layer/lifecycle',
        node_name=str(node_name),
        lifecycle_transition=names_to_transitions[str(lifecycle_state)],
    )


def _parse_param_array(param_values_block: dict[str, Any]) -> ParamValue:
    values_with_index: list[tuple[int, Any]] = []
    for param_dict in param_values_block:
        param_index = convert_query_type_to_py_type(
            param_dict['param_index']['index'][0])
        value = convert_query_type_to_py_type(param_dict['value']['attribute'][0])
        values_with_index.append((int(param_index), value))

    values_with_index.sort(key=lambda pair: pair[0])
    return [v for _, v in values_with_index]


def _parse_param_singleton(param_singleton_block: dict[str, Any]) -> ParamValue:
    param_attributes = param_singleton_block[0]['parameter_value']['attribute']
    for attr in param_attributes:
        attr_label = attr['type']['label']
        if attr_label.endswith('_value'):
            return convert_query_type_to_py_type(attr)
    return convert_query_type_to_py_type(param_attributes[0])


def _parse_parameter_action(
    raw_action: dict[str, Any],
) -> Adaptation:
    node_name = raw_action['node']['node_name'][0]['value']
    param_name_attr = raw_action.get('parameter').get('parameter_name')[0]['value']

    param_value: ParamValue
    param_array = raw_action.get('param_value_array') or []
    if param_array:
        param_value = _parse_param_array(param_array)
    else:
        param_singleton = raw_action.get('param_value_singleton')
        param_value = _parse_param_singleton(param_singleton)

    param = Parameter(str(param_name_attr), value=param_value)

    return Adaptation(
        target_type_str='execution_layer/parameter',
        node_name=str(node_name),
        parameter=param.to_parameter_msg()
    )
