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
import logging
from dataclasses import dataclass
from typing import List
from typing import TypedDict

from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import convert_py_type_to_query_type

logger = logging.getLogger(__name__)


@dataclass
class RequirementImpactDict():
    """Dataclass for requirement impact information."""

    action_name: str  #: name of the action
    requirement_name: str  #: name of the requirement
    tactic_rule: str  #: name of the tactic rule
    fulfillment: float  #: fulfillment value


class ROSActionResultDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    action_name: str  #: action name
    action_type: str  #: action type


class RuntimeNodeDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    namespace: str  #: node namespace
    node_name: str  #: node name


def create_value_query(value, suffix=''):
    if not isinstance(value, (str, float, int, bool, list)):
        logger.error(
            'Unsupported type %s for value %s',
            type(value),
            value)
        return None

    variable_name = f'$value{suffix}'

    value_query = ''
    if isinstance(value, str):
        value_query = f'{variable_name} isa ValueString, has string_value "{value}";'
    elif isinstance(value, float):
        value_query = f'{variable_name} isa ValueDouble, has double_value {value};'
    elif isinstance(value, bool):
        value_query = f"""{variable_name} isa ValueBool,
            has bool_value {convert_py_type_to_query_type(value)};"""
    elif isinstance(value, int):
        value_query = f'{variable_name} isa ValueInteger, has integer_value {value};'
    return value_query, variable_name


def node_query_to_node_dict(
        query_result: List[dict[str, MatchResultDict]],
        node_variable: str = 'node') -> List[RuntimeNodeDict]:
    node_dict = list()
    for result in query_result:
        node = result.get(node_variable)
        if len(node['namespace']) > 1:
            logger.error(
                'In node_query_to_node_dict: '
                'runtime node has more than 1 namespace')
            return node_dict
        if len(node['node_name']) > 1:
            logger.error(
                'In node_query_to_node_dict: '
                'runtime node has more than 1 node_name')
            return node_dict
        node_dict.append({
            'node_name': node['node_name'][0]['value'],
            'namespace': node['namespace'][0]['value'],
        }
        )
    # Sort list to guarantee deterministic list order
    node_dict.sort(key=lambda d: (d['node_name'], d['namespace']))
    return node_dict
