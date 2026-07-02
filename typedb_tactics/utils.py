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
import logging
from typing import Any
from typing import Literal
from typing import Sequence
from typing import TypeAlias

from aal_msgs.msg import Adaptation
from ros_typedb.typedb_interface import convert_py_type_to_query_type
from ros_typedb.typedb_interface import convert_query_type_to_py_type
from lifecycle_msgs.msg import Transition
from rclpy.parameter import Parameter

logger = logging.getLogger(__name__)

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
            index_value = convert_query_type_to_py_type(entry['index'])

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
        adaptation_target=Adaptation.STATETRANSITION,
        node_name=str(node_name),
        lifecycle_adaptation=names_to_transitions[str(lifecycle_state)],
    )


def _parse_param_array(param_values_block: dict[str, Any]) -> ParamValue:
    values_with_index: list[tuple[int, Any]] = []
    for param_dict in param_values_block:
        param_index = convert_query_type_to_py_type(
            param_dict['param_index']['index'][0])
        value = convert_query_type_to_py_type(
            param_dict['value']['attribute'][0])
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
    param_name_attr = raw_action.get(
        'parameter').get('parameter_name')[0]['value']

    param_value: ParamValue
    param_array = raw_action.get('param_value_array') or []
    if param_array:
        param_value = _parse_param_array(param_array)
    else:
        param_singleton = raw_action.get('param_value_singleton')
        param_value = _parse_param_singleton(param_singleton)

    param = Parameter(str(param_name_attr), value=param_value)

    return Adaptation(
        adaptation_target=Adaptation.ROSPARAMETER,
        node_name=str(node_name),
        parameter_adaptation=param.to_parameter_msg()
    )


def _first_attr(row: dict, variable: str, attribute: str):
    """Extract `row[variable][attribute][0]['value']` with safe error handling."""
    try:
        values = row[variable][attribute]
    except KeyError:
        logger.error('_first_attr: key %r.%r not found in result row', variable, attribute)
        return None
    if not values:
        logger.warning('_first_attr: empty attribute list for %r.%r', variable, attribute)
        return None
    return values[0]['value']


def _first_value(row: dict, key: str):
    """Extract `row[key]['value']` with safe error handling."""
    try:
        entry = row[key]
    except KeyError:
        logger.error('_first_value: key %r not found in result row', key)
        return None
    return entry.get('value')


def build_value_query(
        value: str | float | int | bool | list,
        suffix: str = '') -> tuple[str, str] | tuple[None, None]:
    """
    Build a TypeQL insertion snippet and variable name for a typed value.

    :param value: the Python value to serialise
    :param suffix: appended to the scalar variable name to make it unique
    :return: (typeql_snippet, variable_name) or (None, None) on unsupported type
    """
    if isinstance(value, list):
        fragments = ['$array isa ValueArray;']
        for index, item in enumerate(value):
            item_query, item_var = build_value_query(item, str(index))
            fragments.append(
                f'{item_query}\n'
                f'(array: $array, array_value: {item_var}) isa at_index,'
                f' has index {index};'
            )
        return '\n'.join(fragments), '$array'

    variable_name = f'$value{suffix}'
    # bool must be checked before int: isinstance(True, int) is True
    if isinstance(value, bool):
        return (
            f'{variable_name} isa ValueBool,'
            f' has bool_value {convert_py_type_to_query_type(value)};',
            variable_name,
        )
    if isinstance(value, str):
        return (
            f'{variable_name} isa ValueString, has string_value "{value}";',
            variable_name,
        )
    if isinstance(value, float):
        return (
            f'{variable_name} isa ValueDouble,'
            f' has double_value {format(value, ".15f")};',
            variable_name,
        )
    if isinstance(value, int):
        return (
            f'{variable_name} isa ValueInteger, has integer_value {value};',
            variable_name,
        )

    logger.error('Unsupported type %s for value %s', type(value), value)
    return None, None
