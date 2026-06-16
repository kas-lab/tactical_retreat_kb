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
from dataclasses import dataclass
from datetime import datetime
import inspect
import logging
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypedDict
from typing import Union

from ros_typedb.typedb_interface import convert_py_type_to_query_type
from ros_typedb.typedb_interface import convert_query_type_to_py_type
from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import TypeDBInterface
from typedb_tactics.utils import AdaptationPlan

from typedb.driver import ConceptMap

logger = logging.getLogger(__name__)


@dataclass
class RequirementImpactDict():
    """Dataclass for requirement impact information."""

    action_name: str  #: name of the action
    requirement_name: str  #: name of the requirement
    tactic_rule: str  #: name of the tactic rule
    fulfillment: float  #: fulfillment value


def create_value_query(value, suffix=''):
    if not isinstance(value, (str, float, int, bool, list)):
        logger.error(
            'Unsupported type %s for value %s',
            type(value),
            value)
        return None, None

    variable_name = f'$value{suffix}'

    value_query = ''
    if isinstance(value, str):
        value_query = f'{variable_name} isa ValueString, has string_value "{value}";'
    elif isinstance(value, float):
        formatted = format(value, '.15f')
        value_query = f'{variable_name} isa ValueDouble, has double_value {formatted};'
    elif isinstance(value, bool):
        value_query = f"""{variable_name} isa ValueBool,
            has bool_value {convert_py_type_to_query_type(value)};"""
    elif isinstance(value, int):
        value_query = f'{variable_name} isa ValueInteger, has integer_value {value};'
    return value_query, variable_name


class ROSActionResultDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    action_name: str  #: action name
    action_type: str  #: action type


class RuntimeNodeDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    namespace: str  #: node namespace
    node_name: str  #: node name


def node_query_to_node_dict(
        query_result: List[dict[str, MatchResultDict]],
        node_variable: str = 'node') -> List[RuntimeNodeDict]:
    node_dict = []
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



class TacticalRetreatInterface(TypeDBInterface):
    """Class to interact with the TacticalRetreat knowledge model in typeDB."""

    def __init__(
            self,
            address: str,
            database_name: str,
            schema_path: Optional[list[str] | str] = None,
            data_path: Optional[list[str] | str] = None,
            force_database: Optional[bool] = False,
            force_data: Optional[bool] = False,
            infer: Optional[bool] = False,
            sort_fetch_results: Optional[bool] = False,
            driver_timeout_s: Optional[float] = 10.0) -> None:
        self._sort_fetch_results = bool(sort_fetch_results)
        super_init = inspect.signature(TypeDBInterface.__init__)
        if 'sort_fetch_results' in super_init.parameters:
            super().__init__(
                address,
                database_name,
                schema_path,
                data_path,
                force_database,
                force_data,
                infer,
                sort_fetch_results,
                driver_timeout_s
            )
        else:
            super().__init__(
                address,
                database_name,
                schema_path,
                data_path,
                force_database,
                force_data,
                infer,
                driver_timeout_s=driver_timeout_s
            )

    def fetch_database(
            self,
            query: str,
            sort_result: Optional[bool] = None) -> List[dict[str, MatchResultDict]]:
        """Perform fetch query using interface-level default ordering policy."""
        should_sort = self._sort_fetch_results if sort_result is None else sort_result
        try:
            return super().fetch_database(query, sort_result=should_sort)
        except TypeError:
            # Backward compatibility with base versions without sort_result
            # support.
            return super().fetch_database(query)

    def fetch_subnodes(self, node_name: str,
                       namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch subnodes of a running node and returns it as a typedb fetch query result.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: fetch query result
        """
        query = f"""
            match
                $parent_node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
                (node: $parent_node, subnode: $subnode) isa subnode;
            fetch
                $subnode: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_subnodes(
            self,
            node_name: str,
            namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the subnodes of a running node and returns it as a list of dicts.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: list of dictionaries with the node_name and namespace of the subnodes
        """
        return node_query_to_node_dict(
            self.fetch_subnodes(node_name, namespace), 'subnode')

    def fetch_action_clients_nodes(
            self, action_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch action clients and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                $action_client isa ActionClient, has interface_name '{action_name}';
                (node: $node, client: $action_client) isa has_action;
            fetch
                $node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_action_clients_nodes(
            self, action_name: str) -> List[RuntimeNodeDict]:
        """
        Get action clients and returns it as a list of dicts.

        :param action: action name
        :return: list of dictionaries with the node_name and namespace of the client nodes
        """
        return node_query_to_node_dict(
            self.fetch_action_clients_nodes(action_name))

    def fetch_action_server_nodes(
            self, action_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch action servers and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                $action_server isa ActionServer, has interface_name '{action_name}';
                (node: $node, server: $action_server) isa has_action;
            fetch
                $node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_action_server_nodes(
            self, action_name: str) -> List[RuntimeNodeDict]:
        """
        Get action clients and returns it as a list of dicts.

        :param action: action name
        :return: list of dictionaries with the node_name and namespace of the client nodes
        """
        return node_query_to_node_dict(
            self.fetch_action_server_nodes(action_name))

    def fetch_action_clients_names(
            self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the name and type of all action clients of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
                (node: $node, client: $action_client) isa has_action;
            fetch
                $action_client: interface_name, interface_type;
        """
        return self.fetch_database(query)

    def get_action_clients_names(
            self,
            node_name: str,
            namespace: str = '') -> List[ROSActionResultDict]:
        """
        Get the name and type of all action clients of a running node, returns it as list of dicts.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the action_name and action_type of the action clients
        """
        ros_action_result_dict = []
        for result in self.fetch_action_clients_names(node_name, namespace):
            action = result.get('action_client')
            if len(action['interface_name']) == 0:
                logger.error(
                    'In get_action_clients_names: action does not have an action_name')
                return ros_action_result_dict
            if len(action['interface_name']) > 1:
                logger.error(
                    'In get_action_clients_names: action has more than 1 action_name')
                return ros_action_result_dict
            if len(action['interface_type']) > 1:
                logger.error(
                    'In get_action_clients_names: action {} has more than 1 action_type'.format(
                        action['interface_name']))
                return ros_action_result_dict
            if len(action['interface_type']) == 0:
                logger.error(
                    'In get_action_clients_names: action {} does not have an action_type'.format(
                        action['interface_name']))
                return ros_action_result_dict
            ros_action_result_dict.append({
                'action_name': action['interface_name'][0]['value'],
                'action_type': action['interface_type'][0]['value'],
            }
            )
        # Sort list to guarantee deterministic list order
        ros_action_result_dict.sort(
            key=lambda d: (
                d['action_name'],
                d['action_type']))
        return ros_action_result_dict

    def fetch_connected_action_server_nodes(
            self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the name and namespace of all runtime nodes that are servers for the action clients.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
                (node: $node, client: $action_client) isa has_action;
                $action_client isa ActionClient,
                    has interface_name $interface_name,
                    has interface_type $interface_type;
                $action_server isa ActionServer,
                    has interface_name $interface_name,
                    has interface_type $interface_type;
                (node: $server_node, server: $action_server) isa has_action;
            fetch
                $server_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_connected_action_server_nodes(
            self,
            node_name: str,
            namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the name and namespace of all runtime nodes that are servers for the action clients.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the action server nodes
        """
        return node_query_to_node_dict(
            self.fetch_connected_action_server_nodes(
                node_name, namespace), 'server_node')

    def fetch_connected_subscriber_nodes(
            self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the name and namespace of all runtime nodes that are subscribers of the publishers.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
                (node: $node, publisher: $publisher) isa has_topic;
                $publisher isa Publisher,
                    has interface_name $interface_name,
                    has interface_type $interface_type;
                $subscriber isa Subscriber,
                    has interface_name $interface_name,
                    has interface_type $interface_type;
                (node: $subscriber_node, subscriber: $subscriber) isa has_topic;
            fetch
                $subscriber_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_connected_subscriber_nodes(
            self,
            node_name: str,
            namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the name and namespace of all runtime nodes that are subscribers of the publishers.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the subscriber nodes
        """
        return node_query_to_node_dict(
            self.fetch_connected_subscriber_nodes(
                node_name, namespace), 'subscriber_node')

    def fetch_tactics(
            self, resolution_model: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: fetch query result
        """
        query = f"""
            match
                (tactic: $tactic) isa resolution_model,
                    has resolution_model_name '{resolution_model}';
            fetch
                $tactic: tactic_name;
        """
        return self.fetch_database(query)

    def get_tactics(self, resolution_model: str) -> List[str]:
        """
        Get all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: list of tactic names
        """
        query_result = self.fetch_tactics(resolution_model)
        return [result['tactic']['tactic_name'][0]['value']
                for result in query_result]

    def fetch_all_tactic_rules(self) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all tactic rules names.

        :return: fetch query result
        """
        query = """
            match
                $tactic_rule isa tactic_rule;
            fetch
                $tactic_rule: rule_name;
        """
        return self.fetch_database(query)

    def get_all_tactic_rules(self) -> List[str]:
        """
        Get all tactic tactic rules names.

        :return: list of tactic rule names
        """
        query_result = self.fetch_all_tactic_rules()
        return [result['tactic_rule']['rule_name'][0]['value']
                for result in query_result]

    def does_tactic_affect_nodes(
            self,
            tactic_name: str,
            node_name: str,
            namespace: str = '') -> bool:
        """
        Check whether a given tactic affects a given node.

        :param tactic_name: name of the tactic
        :param node_name: name of the running node
        :param namespace: namespace of the running node
        :return: true or false
        """
        query = f"""
            match
                $tactic isa Tactic, has tactic_name '{tactic_name}';
                (tactic: $tactic, consequent: $fa) isa tactic_rule;
                $fa ($feature)
                    isa feature_adaptation;
                $feature isa Feature;
                (variant: $feature, resolution_action: $resolution_action)
                    isa variant_resolution;
                $resolution_action (node: $node) isa resolution_action;
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
            get $node;
            count;
        """
        return (self.get_aggregate_database(query) > 0)

    def fetch_neighbours(
            self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the neighbours of a node.

        :param node_name: node name of the node
        :param namespace: namespace of the node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode,
                    has node_name '{node_name}', has namespace '{namespace}';
                $neighbours (node: $node, neighbour: $neighbour) isa
                    neighbours;
            fetch
                $neighbour: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_neighbours(
            self,
            node_name: str,
            namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the neighbours of a node.

        :param node_name: node name of the node
        :param namespace: namespace of the node
        :return: list of dictionaries with the node_name and namespace of the neighbour nodes
        """
        return node_query_to_node_dict(
            self.fetch_neighbours(
                node_name, namespace), 'neighbour')

    def fetch_connected_nodes(
            self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the connected nodes of a node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
                $connected_nodes (node: $node, connected: $connected)
                    isa connected_nodes;
            fetch
                $connected: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_connected_nodes(
            self,
            node_name: str,
            namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the connected nodes of a node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the neighbour nodes
        """
        return node_query_to_node_dict(
            self.fetch_connected_nodes(
                node_name, namespace), 'connected')

    def manual_running_nodes(self, node_names: List[str]):
        """
        Update the running nodes in the knowledge base.

        :param node_names: list of node names
        """
        insert_statements = ''
        for i, node_name in enumerate(node_names):
            insert_statements += f"""
                $node_{i} has running true;
            """
        nl = '\n'
        query = f"""
            match
                {' '.join([
                    f'$node_{i} isa ROSNode, has node_name "{node_name}"; {nl}'
                    for i, node_name in enumerate(node_names)
                ])}
            insert
                {insert_statements}
        """
        return self.insert_database(query)

    def fetch_database_unordered(
            self, query: str) -> List[dict[str, MatchResultDict]]:
        """Perform fetch query without recursively sorting result keys."""
        try:
            return super().fetch_database_unordered(query)
        except AttributeError:
            try:
                return self.fetch_database(query, sort_result=False)
            except TypeError:
                return self.fetch_database(query)

    def fetch_database_unsorted(
            self, query: str) -> List[dict[str, MatchResultDict]]:
        """Backward-compatible alias for fetch_database_unordered."""
        return self.fetch_database_unordered(query)

    def fetch_applicable_tactics(self,
                                 resolution_model: str,
                                 interface_name: str) -> List[dict[str,
                                                                   MatchResultDict]]:
        """
        Fetch all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface, has interface_name '{interface_name}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (interface: $interface,
                    resolution_model: $resolution_model, tactic_rule: $tactic_rule)
                    isa applicable_tactics;
            fetch
                $tactic_rule: rule_name;
        """
        return self.fetch_database_unordered(query)

    def fetch_applicable_valid_tactics(
            self,
            resolution_model: str,
            interface_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch applicable and valid tactics for a ROS interface and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface, has interface_name '{interface_name}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (interface: $interface,
                    resolution_model: $resolution_model, tactic_rule: $tactic_rule)
                    isa applicable_tactics;
                $tactic_rule isa tactic_rule, has rule_valid true;
            fetch
                $tactic_rule: rule_name;
        """
        return self.fetch_database(query)

    def fetch_current_state_action(self, action_name):
        query = f"""
            match
                $action_server isa ActionServer, has interface_name "{action_name}";
                $s (ros_action : $action_server) isa state,
                    has current true;
            fetch
                $s: state_name;
        """
        query_result = self.fetch_database(query)
        return query_result

    def fetch_current_state(self):
        query = """
            match
                $s isa state,
                    has current true;
            fetch
                $s: state_name;
        """
        query_result = self.fetch_database(query)
        return query_result

    def get_current_state(self):
        current_state = self.fetch_current_state()
        if len(current_state) > 0:
            return current_state[0]['s']['state_name'][0]['value']
        return None

    def get_current_state_action(self, action_name):
        current_state = self.fetch_current_state_action(action_name)
        if len(current_state) > 0:
            return current_state[0]['s']['state_name'][0]['value']
        return None

    def fetch_valid_rule(
            self,
            tactic_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch valid rule actions for a tactic.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $t isa Tactic, has tactic_name "{tactic_name}";
                $tactic_rule (antecedent: $ant, tactic:$t, consequent:$fa)
                    isa tactic_rule;
                $ant has expression_satisfied true;
            fetch
                variant_activation: {{
                    match
                        $fa (activation: $feature_activate) isa feature_adaptation;
                        (tactic:$t, variant_resolution:$vr) isa resolution_model;
                        $vr (resolution_action:$res_action, variant: $feature_activate)
                            isa variant_activation;
                    fetch
                        set_parameter_action: {{
                            match
                                $res_action (node: $node, parameter: $parameter,
                                            parameter_value: $parameter_value)
                                    isa! set_nodes_parameters;
                            fetch
                                $node: node_name;
                                $parameter: parameter_name;
                                param_values: {{
                                    match
                                        $parameter_value isa! ValueArray;
                                        $index (array: $parameter_value, array_value: $value)
                                            isa at_index;
                                    fetch
                                        $index: index;
                                        $value: attribute;
                                }};
                        }};
                        set_lifecycle_action: {{
                            match
                                $res_action (node: $node) isa! set_lifecycle_state;
                            fetch
                                $node: node_name;
                                $res_action: lifecycle_state;
                        }};
                }};
                variant_deactivation: {{
                    match
                        $fa (deactivation: $feature_deactivate) isa feature_adaptation;
                        (tactic:$t, variant_resolution:$vr) isa resolution_model;
                        $vr (resolution_action:$res_action, variant: $feature_deactivate)
                            isa variant_deactivation;
                    fetch
                        set_parameter_action: {{
                            match
                                $res_action (node: $node, parameter: $parameter,
                                            parameter_value: $parameter_value)
                                    isa! set_nodes_parameters;
                            fetch
                                $node: node_name;
                                $parameter: parameter_name;
                                param_values: {{
                                    match
                                        $parameter_value isa! ValueArray;
                                        $index (array: $parameter_value, array_value: $value)
                                            isa at_index;
                                    fetch
                                        $index: index;
                                        $value: attribute;
                                }};
                        }};
                        set_lifecycle_action: {{
                            match
                                $res_action (node: $node) isa! set_lifecycle_state;
                            fetch
                                $node: node_name;
                                $res_action: lifecycle_state;
                        }};
                }};
        """
        return self.fetch_database(query)

    def fetch_applicable_valid_adaptations(self,
                                 resolution_model: str,
                                 interface_name: str) -> List[dict[str,
                                                                MatchResultDict]]:
        """
        Fetch applicable and valid adaptations for a ROS interface and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface, has interface_name '{interface_name}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (interface: $interface,
                    resolution_model: $resolution_model, tactic_rule: $tactic_rule)
                    isa applicable_tactics;
                $tactic_rule (tactic:$t, consequent:$fa) isa tactic_rule,
                    has rule_valid true;
            fetch
                variant_activation: {{
                    match
                        $fa (activation: $feature_activate) isa feature_adaptation;
                        (tactic:$t, variant_resolution:$vr) isa resolution_model;
                        $vr (resolution_action:$res_action, variant: $feature_activate)
                            isa variant_activation;
                    fetch
                        set_parameter_action: {{
                            match
                                $res_action (node: $node, parameter: $parameter,
                                            parameter_value: $parameter_value)
                                    isa! set_nodes_parameters;
                            fetch
                                $node: node_name;
                                $parameter: parameter_name;
                                param_values: {{
                                    match
                                        $parameter_value isa! ValueArray;
                                        $index (array: $parameter_value, array_value: $value)
                                            isa at_index;
                                    fetch
                                        $index: index;
                                        $value: attribute;
                                }};
                        }};
                        set_lifecycle_action: {{
                            match
                                $res_action (node: $node) isa! set_lifecycle_state;
                            fetch
                                $node: node_name;
                                $res_action: lifecycle_state;
                        }};
                }};
                variant_deactivation: {{
                    match
                        $fa (deactivation: $feature_deactivate) isa feature_adaptation;
                        (tactic:$t, variant_resolution:$vr) isa resolution_model;
                        $vr (resolution_action:$res_action, variant: $feature_deactivate)
                            isa variant_deactivation;
                    fetch
                        set_parameter_action: {{
                            match
                                $res_action (node: $node, parameter: $parameter,
                                            parameter_value: $parameter_value)
                                    isa! set_nodes_parameters;
                            fetch
                                $node: node_name;
                                $parameter: parameter_name;
                                param_values: {{
                                    match
                                        $parameter_value isa! ValueArray;
                                        $index (array: $parameter_value, array_value: $value)
                                            isa at_index;
                                    fetch
                                        $index: index;
                                        $value: attribute;
                                }};
                        }};
                        set_lifecycle_action: {{
                            match
                                $res_action (node: $node) isa! set_lifecycle_state;
                            fetch
                                $node: node_name;
                                $res_action: lifecycle_state;
                        }};
                }};
        """
        return self.fetch_database(query)

    def fetch_applicable_valid_adaptations_names(
            self,
            tactic_names) -> List[dict[str, MatchResultDict]]:
        """
        Fetch applicable and valid adaptation names.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        match_block = """
        match
        """
        fetch_block = """
        fetch
        """
        for i, tactic_name in enumerate(tactic_names):
            match_block += f"""
                $tactic_rule_{i} (antecedent: $ant_{i}, consequent: $fa_{i})
                    isa tactic_rule, has rule_name '{tactic_name}';
                $fa_{i} ($feature_{i}) isa feature_adaptation;
            """
            fetch_block += f"""
                $ant_{i}: expression_satisfied;
            """
        query = match_block + fetch_block
        return self.fetch_database(query)

    def get_applicable_tactics(
            self,
            resolution_model: str,
            interface_name: str) -> List[str]:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: list containing all tactic's names that are applicable
        """
        query_result = self.fetch_applicable_tactics(
            resolution_model, interface_name)
        return sorted(
            result['tactic_rule']['rule_name'][0]['value']
            for result in query_result
        )

    def get_satisfied_tactics(
            self,
            tactic_names: List[str]):
        query_result = self.fetch_applicable_valid_adaptations_names(
            tactic_names)
        return [
            query_result[0]['ant_' + str(i)]['expression_satisfied'][0]['value']
            for i, _ in enumerate(tactic_names)
        ]

    def fetch_relaxed_requirement_fulfillment(
            self,
            system_name: str,
            requirement_name: str) -> List[dict[str,
                                                MatchResultDict]]:
        """
        Fetch relaxed requirement fulfillment.

        :param system_name: system name
        :param requirement_name: requirement name
        :return: fetch query result
        """
        return self.fetch_relaxed_requirements_fulfillment(
            system_name, requirement_name)

    def fetch_relaxed_requirements_fulfillment(
            self,
            system_name: str,
            *requirement_names: List[str]) -> List[dict[str, MatchResultDict]]:
        """
        Fetch multiple relaxed requirements fulfillment.

        :param system_name: system name
        :param requirement_name: requirement name
        :return: fetch query result
        """
        match_block = f"""
            match
                $system isa System, has system_name '{system_name}';
        """
        fetch_block = 'fetch '

        for i, requirement_name in enumerate(requirement_names):
            match_block += f"""
                (system: $system) isa relaxed_requirement,
                    has requirement_name '{requirement_name}',
                    has fulfillment $fulfillment_{i};
            """
            fetch_block += f'$fulfillment_{i};'

        query = match_block + fetch_block
        return self.fetch_database(query)

    def get_relaxed_requirement_fulfillment(
            self,
            system_name: str,
            requirement_name: str) -> List[dict[str,
                                                MatchResultDict]]:
        """
        Fetch relaxed requirement fulfillment.

        :param system_name: system name
        :param requirement_name: requirement name
        :return: fulfillment value
        """
        return self.fetch_relaxed_requirement_fulfillment(
            system_name, requirement_name)[0]['fulfillment_0']['value']

    def get_relaxed_requirements_fulfillment(
            self,
            system_name: str,
            *requirement_names: List[str]) -> List[float]:
        """
        Fetch multiple relaxed requirements fulfillment.

        :param system_name: system name
        :param requirement_names: list of requirement names
        :return: list of fulfillment values
        """
        return [x['fulfillment_' + str(i)]['value'] for i, x in enumerate(
            self.fetch_relaxed_requirements_fulfillment(system_name, *requirement_names))]

    def fetch_in_effect_requirement_fulfillment(
            self) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all relaxed requirement in effect fulfillment.

        :return: fetch query result
        """
        query = """
            match
                $req (system: $system) isa relaxed_requirement,
                    has in_effect true;
            fetch
                $req: requirement_name, fulfillment;
                $system: system_name;
        """
        return self.fetch_database(query)

    def get_in_effect_requirement_fulfillment(self) -> List[dict]:
        """
        Fetch all relaxed requirement in effect fulfillment.

        :return: fetch query result
        """
        query_result = self.fetch_in_effect_requirement_fulfillment()
        query_dict = [
            {'requirement_name': result['req']['requirement_name'][0]['value'],
             'fulfillment': result['req']['fulfillment'][0]['value'],
             'system': result['system']['system_name'][0]['value']}
            for result in query_result]
        return sorted(query_dict, key=lambda item: item['requirement_name'])

    def set_requirement_in_effect(self, requirement_name: str, in_effect: bool
                                  ) -> Optional[Iterator[ConceptMap]]:
        """
        Set the in_effect status of a relaxed requirement.

        :param requirement_name: requirement name
        :param in_effect: boolean indicating if the requirement is in effect
        """
        in_effect_tql_type = convert_py_type_to_query_type(in_effect)
        query = f"""
            match
                $req isa relaxed_requirement,
                    has requirement_name '{requirement_name}';
            insert
                $req has in_effect {in_effect_tql_type};
        """
        return self.insert_database(query)

    def update_all_requirement_in_effect(
            self,
            requirement_name: str,
            in_effect: bool) -> Optional[Iterator[ConceptMap]]:
        """
        Set the in_effect status of a relaxed requirement.

        :param requirement_name: requirement name
        :param in_effect: boolean indicating if the requirement is in effect
        """
        out_effect_tql_type = convert_py_type_to_query_type(not in_effect)
        in_effect_tql_type = convert_py_type_to_query_type(in_effect)
        query = f"""
        match
            $requirement isa relaxed_requirement,
                has requirement_name '{requirement_name}',
                has in_effect $in_effect;
            $in_effect = {out_effect_tql_type};
        delete
            $requirement has $in_effect;
        insert
            $requirement has in_effect {in_effect_tql_type};
        """
        return self.update_database(query)

    # This only works if there are more requirements than those mentioned in
    # requirement_names.
    def update_requirements_in_effect(
            self, requirement_names, all_requirements):
        if(not all_requirements):
            match_block = """
            match
                $requirement isa relaxed_requirement, has in_effect $in_effect,
                has requirement_name $req_name;
            """
            delete_block = """
            delete
            $requirement has $in_effect;
            """
            insert_block = """
            insert
            $requirement has in_effect false;
            """
            for i, requirement_name in enumerate(requirement_names):
                match_block += f"""
                $req_name != '{requirement_name}';
                $req_{i} isa relaxed_requirement,
                has requirement_name '{requirement_name}',
                has in_effect $eff_{i};
                """
                delete_block += f"""
                    $req_{i} has $eff_{i};
                """
                insert_block += f"""
                    $req_{i} has in_effect true;
                """
            query = match_block + delete_block + insert_block
            return self.update_database(query)
        else:
            match_block = """
            match
            """
            delete_block = """
            delete
            """
            insert_block = """
            insert
            """
            for i, requirement_name in enumerate(requirement_names):
                match_block += f"""
                $req_{i} isa relaxed_requirement,
                has requirement_name '{requirement_name}',
                has in_effect $eff_{i};
                """
                delete_block += f"""
                    $req_{i} has $eff_{i};
                """
                insert_block += f"""
                    $req_{i} has in_effect true;
                """
            query = match_block + delete_block + insert_block
            return self.update_database(query)

    def fetch_relaxed_requirement_hypothetical_fulfillment(
            self, system_name: str, requirement_name: str, tactic_rule: str
    ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param requirement_name: requirement name
        :param tactic_rule: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                $system isa System, has system_name '{system_name}';
                $requirement (system: $system) isa relaxed_requirement,
                    has requirement_name '{requirement_name}';
                $tr isa tactic_rule, has rule_name '{tactic_rule}';
                $tactic_impact (tactic_rule: $tr, impacted: $requirement)
                    isa tactic_rule_impacts_requirement;
            fetch
                $tactic_impact : fulfillment;
        """
        return self.fetch_database(query)

    def fetch_relaxed_requirements_hypothetical_fulfillment(
            self, tactic_rules: List[str], system_name: str
    ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param requirement_name: requirement name
        :param tactic_rule: tactic rule name
        :return: fetch query result
        """
        match_block = f"""
            match
                $system isa System, has system_name '{system_name}';
                $requirement (system: $system) isa relaxed_requirement,
                    has in_effect true;
        """
        fetch_block = """
        fetch

        """
        for i, tactic_rule in enumerate(tactic_rules):
            match_block += f"""
            $tr_{i} isa tactic_rule, has rule_name '{tactic_rule}';
            $tactic_impact_{i} (tactic_rule: $tr_{i}, impacted: $requirement)
                isa tactic_rule_impacts_requirement;
            """
            fetch_block += f"""
            $tactic_impact_{i} : fulfillment;
            """
        query = match_block + fetch_block

        return self.fetch_database(query)

    def get_relaxed_requirement_hypothetical_fulfillment(
            self, system_name: str, requirement_name: str, tactic_rule: str
    ) -> List[dict[str, MatchResultDict]]:
        """
        Get hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param requirement_name: requirement name
        :param tactic_rule: tactic rule name
        :return: fulfillment value
        """
        query_result = self.fetch_relaxed_requirement_hypothetical_fulfillment(
            system_name, requirement_name, tactic_rule)
        return query_result[0]['tactic_impact']['fulfillment'][0]['value']

    def get_relaxed_requirements_hypothetical_fulfillment(
            self, tactic_rules: List[str], system_name: str
    ) -> List[dict[str, MatchResultDict]]:
        """
        Get hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param tactic_ruls: tactic rule names
        :return: fulfillment value
        """
        x = {}

        query_result = self.fetch_relaxed_requirements_hypothetical_fulfillment(
            tactic_rules, system_name)

        for rule in tactic_rules:
            x[rule] = []
        for singular_query_result in query_result:
            for i, tactic_rule in enumerate(tactic_rules):
                x[tactic_rule].append(
                    singular_query_result['tactic_impact_' + str(i)]
                    ['fulfillment'][0]['value'])

        return x

    def fetch_requirement_in_effect(self, requirement_name: str
                                    ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch relaxed requirement in effect attribute.

        :param requirement_name: requirement name
        :return: fetch query result
        """
        query = f"""
            match
                $req isa relaxed_requirement,
                    has requirement_name '{requirement_name}';
            fetch
                $req: in_effect;
        """
        return self.fetch_database(query)

    def get_requirement_in_effect(self, requirement_name: str) -> bool:
        """
        Get relaxed requirement in effect attribute.

        :param requirement_name: requirement name
        :return: boolean indicating if the requirement is in effect
        """
        query_result = self.fetch_requirement_in_effect(requirement_name)
        if query_result is None or len(query_result) == 0:
            self.logger.warning(
                'Requirement %s not found in the knowledge base.',
                requirement_name)
            return False
        if len(query_result[0]['req']['in_effect']) == 0:
            return False
        return query_result[0]['req']['in_effect'][0]['value']

    def fetch_latest_measurement(
            self, measure_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch latest measurement of a measure.

        :param measure_name: measure name
        :return: fetch query result
        """
        query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
                $measurement (measure: $measure,
                              measurement_value: $measurement_val) isa measurement,
                    has latest true;
            fetch
                double_value: {{
                    match
                        $measurement_val isa ValueDouble, has double_value $value;
                    fetch
                        $value;
                }};
                integer_value: {{
                    match
                        $measurement_val isa ValueInteger, has integer_value $value;
                    fetch
                        $value;
                }};
                string_value: {{
                    match
                        $measurement_val isa ValueString, has string_value $value;
                    fetch
                        $value;
                }};
                bool_value: {{
                    match
                        $measurement_val isa ValueBool, has bool_value $value;
                    fetch
                        $value;
                }};
                array_values : {{
                    match
                        $measurement_val isa ValueArray;
                        (array: $measurement_val, array_value: $value) isa at_index,
                                has index $index;
                        $singleton_types sub! ValueSingleton;
                        $value isa $singleton_types;
                    fetch
                        $value: attribute;
                        $index;
                    sort $index asc;
                }};
        """
        return self.fetch_database(query)

    def fetch_all_measurements(
            self, measure_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all measurements of a measure.

        :param measure_name: measure name
        :return: fetch query result
        """
        query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
                $measurement (measure: $measure,
                              measurement_value: $measurement_val) isa measurement;
            fetch
                double_value: {{
                    match
                        $measurement_val isa ValueDouble, has double_value $value;
                    fetch
                        $value;
                }};
                integer_value: {{
                    match
                        $measurement_val isa ValueInteger, has integer_value $value;
                    fetch
                        $value;
                }};
                string_value: {{
                    match
                        $measurement_val isa ValueString, has string_value $value;
                    fetch
                        $value;
                }};
                bool_value: {{
                    match
                        $measurement_val isa ValueBool, has bool_value $value;
                    fetch
                        $value;
                }};
                array_values : {{
                    match
                        $measurement_val isa ValueArray;
                        (array: $measurement_val, array_value: $value) isa at_index,
                                has index $index;
                        $singleton_types sub! ValueSingleton;
                        $value isa $singleton_types;
                    fetch
                        $value: attribute;
                        $index;
                    sort $index asc;
                }};
        """
        return self.fetch_database(query)

    def get_latest_measurement(
            self, measure_name: str) -> Union[float, int, str, bool, List]:
        """
        Get latest measurement of a measure.

        :param measure_name: name of the measure
        :return: measurement value
        """
        query_result = self.fetch_latest_measurement(
            measure_name)

        if len(query_result) == 0:
            return float('nan')

        first = query_result[0]
        for key in (
            'double_value',
            'integer_value',
            'string_value',
                'bool_value'):
            values = first.get(key, [])
            if values:
                return values[0]['value']['value']

        array_values = first.get('array_values', [])
        if array_values:
            return [entry['value']['attribute'][0]['value']
                    for entry in array_values]
        return float('nan')

    def fetch_tactic_rule_valid(
            self, tactic_rule: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch whether a tactic_rule is valid.

        :param tactic_rule: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                $tr isa tactic_rule, has rule_name '{tactic_rule}';
            fetch
                $tr: rule_valid;
        """
        return self.fetch_database(query)

    def get_tactic_rule_valid(self, tactic_rule: str) -> bool:
        """
        Get whether a tactic_rule is valid.

        :param tactic_rule: measure name
        :return: true or false
        """
        query_result = self.fetch_tactic_rule_valid(tactic_rule)
        return query_result[0]['tr']['rule_valid'][0]['value']

    def is_feature_selected(self, feature_name: str) -> bool:
        """
        Return whether a feature is selected.

        :param feature_name: feature name
        :return: true or false
        """
        query = f"""
            match
                $f isa Feature, has feature_name '{feature_name}';
            fetch
                $f: selected;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['f']['selected'][0]['value']

    def update_feature_selected_by_param_value(self, feature_name: str):
        """
        Update whether a feature is selected based on its parameter value.

        :param feature_name: feature name
        """
        query = f"""
        match
            $f isa Feature, has feature_name "{feature_name}";
            $vr (variant: $f, resolution_action: $ra) isa variant_resolution;
            $ra (node: $n, parameter: $p, parameter_value: $pv) isa set_nodes_parameters;
            $old_hpv (node: $n, parameter: $p) isa has_parameter_value;
        delete
            $old_hpv isa has_parameter_value;
        insert
            $hpv (node: $n, parameter: $p, parameter_value: $pv) isa has_parameter_value;

        """
        query_result = self.update_database(query)
        return query_result

    def is_node_running(self, node_name: str) -> bool | None:
        """
        Return whether a ROS node is running.

        :param node_name: node name
        :return: true or false
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}';
            fetch
                $node: running;
        """
        query_result = self.fetch_database(query)
        try:
            return query_result[0]['node']['running'][0]['value']
        except IndexError:
            return None

    def is_set_nodes_parameters_feasible(
            self, node_name: str, parameter_name: str) -> bool:
        """
        Return whether a set_nodes_parameters action is feasible.

        :param node_name: node name
        :param parameter_name: parameter name
        :return: true or false
        """
        query = f"""
            match
                $ra (node: $node, parameter: $parameter) isa set_nodes_parameters;
                $node isa ROSNode, has node_name '{node_name}';
                $parameter isa Parameter, has parameter_name '{parameter_name}';
            fetch
                $ra: feasible;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['ra']['feasible'][0]['value']

    def is_set_lifecycle_state_feasible(
            self, node_name: str, lifecycle_state: str) -> bool:
        """
        Return whether a set_lifecycle_state action is feasible.

        :param node_name: node name
        :param lifecycle_state: parameter name
        :return: true or false
        """
        query = f"""
            match
                $ra (node: $node) isa set_lifecycle_state, has lifecycle_state '{lifecycle_state}';
                $node isa LifeCycleNode, has node_name '{node_name}';
            fetch
                $ra: feasible;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['ra']['feasible'][0]['value']

    def fetch_measures_interfaces(
            self, include_qos: bool = True):
        """
        Fetch measures and their source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        qos_sub_query = ''
        if include_qos:
            qos_sub_query = """
            match
                $measure isa Measure, has measure_name $measure_name;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface;
            fetch
                $measure_name;
                $measurement_interface: measurement_function_name,
                    measurement_function_lib,
                    measurement_function_args,
                    measurement_proxy,
                    measurement_period,
                    service_request_kwargs;
                $source: interface_name, interface_type;
            qos_sub_query: {
                match
                    $source isa! Publisher;
                    (interface: $source, qos: $qos) isa has_qos;
                    $qos isa QoSProfile;
                fetch
                    $qos: reliability,
                        history,
                        depth,
                        durability,
                        deadline,
                        lifespan,
                        liveliness,
                        lease_duration;
            };
            """
        else:
            qos_sub_query = """
            match
                $measure isa Measure, has measure_name $measure_name;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface;
            fetch
                $measure_name;
                $measurement_interface: measurement_function_name,
                    measurement_function_lib,
                    measurement_function_args,
                    measurement_proxy,
                    measurement_period,
                    service_request_kwargs;
                $source: interface_name, interface_type;
            """
        query = qos_sub_query
        return self.fetch_database(query)

    def get_measures_interfaces(self, include_qos: bool = True):
        """
        Get measures and source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        def get_first_value(thing: dict, attribute_label: str):
            values = thing.get(attribute_label, [])
            if not values:
                return None
            return convert_query_type_to_py_type(values[0])

        result_dict_list = []
        for result in self.fetch_measures_interfaces(include_qos=include_qos):
            result_dict = {}
            measure = result.get('measure_name')
            if measure:
                result_dict['measure_name'] = convert_query_type_to_py_type(
                    measure)

            result_dict['source'] = result.get(
                'source').get('type').get('label')
            result_dict['interface_name'] = convert_query_type_to_py_type(
                result.get('source').get('interface_name')[0])

            result_dict['interface_type'] = convert_query_type_to_py_type(
                result.get('source').get('interface_type')[0])

            measurement_interface = result.get('measurement_interface')
            for attribute_label in (
                'measurement_function_name',
                'measurement_function_lib',
                'measurement_function_args',
                'measurement_proxy',
                'measurement_period',
                'service_request_kwargs',
            ):
                attribute_value = get_first_value(
                    measurement_interface, attribute_label)
                if attribute_value is not None:
                    result_dict[attribute_label] = attribute_value

            qos_dict = {}
            qos_list = result.get('qos_sub_query')
            if include_qos and isinstance(qos_list, list) and qos_list:
                qos = qos_list[0].get('qos')
                for attribute_label in (
                    'reliability',
                    'history',
                    'depth',
                    'durability',
                    'deadline',
                    'lifespan',
                    'liveliness',
                    'lease_duration',
                ):
                    attribute_value = get_first_value(qos, attribute_label)
                    if attribute_value is not None:
                        qos_dict[attribute_label] = attribute_value

            if qos_dict:
                result_dict['qos'] = qos_dict

            if result_dict:
                result_dict_list.append(result_dict)

        return result_dict_list

    def delete_latest_measurement(
            self, *measure_names: str) -> Optional[Iterator[ConceptMap]]:
        """
        Delete latest measurement.

        :param measure_names: measure names
        :return: query result
        """
        match_del_query = """
            match
        """
        delete_del_query = 'delete \n'

        for i, measure_name in enumerate(measure_names):
            match_del_query += f"""
                    $measure_{i} isa Measure, has measure_name '{measure_name}';
                    $measurement_{i} (measure: $measure_{i}) isa measurement,
                    has latest $latest_{i};
                    $latest_{i} == true;
            """
            delete_del_query += f"""$measurement_{i} has $latest_{i}; """

        self.delete_from_database(match_del_query + delete_del_query)

    def value_query(self, value: Union[
            str,
            float,
            int,
            bool,
            List[str],
            List[float],
            List[int],
            List[bool],
    ], suffix):
        value_query = ''
        variable_name = ''
        if (isinstance(value, list)):
            query_fragments = []
            query_fragments.append('$array isa ValueArray;')
            variable_name = '$array'
            for index, item in enumerate(value):
                value_query_, variable_name_ = create_value_query(item, str(index))
                query_fragments.append(
                    f"""
                        {value_query_}
                        (array: $array, array_value: {variable_name_}) isa at_index,
                            has index {index};
                    """
                )
            value_query = '\n'.join(query_fragments)
        else:
            value_query, variable_name = create_value_query(value, suffix)

        return value_query, variable_name

    def insert_measurement_query(
            self,
            *measure_value_pairs):
        time = convert_py_type_to_query_type(datetime.now())
        match_insert_query = """
            match

        """
        insert_insert_query = """
            insert

        """
        for i, (measure_name, value) in enumerate(measure_value_pairs):
            value_query, variable_name = self.value_query(value, measure_name + str(i))

            match_insert_query += f"""
                    $measure_{i} isa Measure, has measure_name '{measure_name}';

            """
            insert_insert_query += f"""
                    {value_query}
                    $measurement_{i} (measure: $measure_{i}, measurement_value: {variable_name})
                        isa measurement,
                        has measurement_time {time},
                        has latest true;

            """
        return self.insert_database(match_insert_query + insert_insert_query)

    def add_measurement(
        self,
        measure_name: str,
        value: Union[
            str,
            float,
            int,
            bool,
            List[str],
            List[float],
            List[int],
            List[bool],
        ],
    ) -> Optional[Iterator[ConceptMap]]:
        """
        Add new measurement.

        :param measure_name: measure name
        :param value: measured value
        :return: query result
        """
        self.delete_latest_measurement(measure_name)

        return self.insert_measurement_query((measure_name, value))

    def add_measurements(
            self,
            measure_dict):
        """Add new measurements."""
        self.delete_latest_measurement(*measure_dict.keys())
        self.insert_measurement_query(*list(measure_dict.items()))

    def fetch_tactic_rule_impacts_fulfillment(
            self, impacted_name: str, tactic_rule_name: str):
        """
        Fetch hypothetical fulfillment of a expression or requirement given a tactic rule.

        :param impacted_name: expression or requirement name
        :param rule_name: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                {{
                    $impacted isa expression,
                        has expression_name '{impacted_name}';
                }} or {{
                    $impacted isa relaxed_requirement,
                        has requirement_name '{impacted_name}';
                }};
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                $tr_impacts (impacted: $impacted, tactic_rule: $tr) isa tactic_rule_impacts,
                    has fulfillment $fulfillment;
            fetch
                $fulfillment;
        """
        query_result = self.fetch_database(query)
        return query_result

    def fetch_resulting_effect_value(self, tactic_rule: str, measure_name: str
                                     ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch resulting effect value of a tactic on a measure.

        :param tactic_rule: tactic rule name
        :param measure_name: measure name
        """
        query = f"""
            match
                $tactic_rule (effect: $effect) isa tactic_rule, has rule_name '{tactic_rule}';
                $measure isa Measure, has measure_name '{measure_name}';
                $effect (measure: $measure, effect_value: $effect_value) isa relative_effect,
                    has resulting_effect_value $resulting_effect_value;
            fetch
                $resulting_effect_value;
        """
        return self.fetch_database(query)

    def get_resulting_effect_value(
            self,
            tactic_rule: str,
            measure_name: str) -> float:
        """
        Get resulting effect value of a tactic on a measure.

        :param tactic_rule: tactic rule name
        :param measure_name: measure name
        :return: resulting effect value
        """
        query_result = self.fetch_resulting_effect_value(
            tactic_rule, measure_name)
        return query_result[0]['resulting_effect_value']['value']

    def fetch_fuzzy_membership_degree(self, expression_name: str
                                      ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: membership degree
        """
        query = f"""
            match
                $fe isa fuzzy_expression, has expression_name '{expression_name}',
                    has membership_degree $membership_degree;
            fetch
                $membership_degree;
        """
        return self.fetch_database(query)

    def get_fuzzy_membership_degree(self, expression_name: str) -> str:
        """
        Get fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: membership type
        """
        query_result = self.fetch_fuzzy_membership_degree(expression_name)
        return query_result[0]['membership_degree']['value']

    def fetch_relaxed_expression_fulfillment(
            self, expression_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch fuzzy fulfillment of a fuzzy expression.

        :param expression_name: fuzzy expression name
        """
        query = f"""
            match
                $relaxed_expression isa relaxed_expression,
                    has expression_name '{expression_name}',
                    has fulfillment $fulfillment;
            fetch
                $fulfillment;
        """
        return self.fetch_database(query)

    def get_relaxed_expression_fulfillment(self, expression_name: str) -> str:
        """
        Get fuzzy fulfillment of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: fulfillment type
        """
        query_result = self.fetch_relaxed_expression_fulfillment(
            expression_name)
        return query_result[0]['fulfillment']['value']

    def fetch_potential_requirements_fulfillment(
            self,
            action_name: str,
            resolution_model: Optional[str] = None
    ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all potential relaxed requirement fulfillments per applicable tactic.

        :param action_name: ROS interface/action name
        :param resolution_model: optional resolution model name
        :return: fetch query result
        """
        if resolution_model is not None:
            return self.fetch_potential_requirements_fulfillment_for_resolution_model(
                action_name, resolution_model)

        resolution_model_query = '$resolution_model isa resolution_model;'

        query = f"""
            match
                $ros_interface isa ROSInterface, has interface_name '{action_name}';
                {resolution_model_query}
                (interface: $ros_interface,
                    resolution_model: $resolution_model,
                    tactic_rule: $tactic_rule)
                    isa applicable_tactics;
                $tactic_impact (impacted: $req, tactic_rule: $tactic_rule)
                    isa tactic_rule_impacts_requirement_in_effect, has fulfillment $fulfillment;
                $req isa relaxed_requirement,
                    has in_effect true,
                    has requirement_name $requirement_name;
                $tactic_rule has rule_name $rule_name;
            fetch
                $rule_name;
                $fulfillment;
                $requirement_name;
        """
        return self.fetch_database_unordered(query)

    def fetch_potential_requirements_fulfillment_for_resolution_model(
            self,
            action_name: str,
            resolution_model: str
    ) -> List[dict[str, MatchResultDict]]:
        """
        Fetch potential relaxed requirement fulfillment using a fixed resolution model.

        This is a strict fast-path for the hot query path.

        :param action_name: ROS interface/action name
        :param resolution_model: resolution model name
        :return: fetch query result
        """
        query = f"""
            match
                $ros_interface isa ROSInterface, has interface_name '{action_name}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (interface: $ros_interface,
                    resolution_model: $resolution_model,
                    tactic_rule: $tactic_rule)
                    isa applicable_tactics;
                $tactic_impact (
                    resolution_model: $resolution_model,
                    tactic_rule: $tactic_rule,
                    impacted: $req
                ) isa resolution_model_tactic_rule_impacts_requirement_in_effect,
                    has fulfillment $fulfillment;
                $req has requirement_name $requirement_name;
                $tactic_rule has rule_name $rule_name;
            fetch
                $rule_name;
                $fulfillment;
                $requirement_name;
        """
        return self.fetch_database_unordered(query)

    @staticmethod
    def _build_requirement_impact_dicts(
            action_name: str,
            query_result: List[dict[str, MatchResultDict]]
    ) -> List[RequirementImpactDict]:
        """Convert query result rows to requirement impact dataclasses."""
        return [
            RequirementImpactDict(
                action_name=action_name,
                tactic_rule=result['rule_name']['value'],
                requirement_name=result['requirement_name']['value'],
                fulfillment=result['fulfillment']['value']
            ) for result in query_result
        ]

    def get_potential_requirements_fulfillment(
            self,
            action_name: str,
            resolution_model: Optional[str] = None
    ) -> List[RequirementImpactDict]:
        """
        Get all potential relaxed requirement fulfillments per applicable tactic.

        :param action_name: ROS interface/action name
        :param resolution_model: optional resolution model name
        :return: list of RequirementImpactDict
        """
        if resolution_model is not None:
            return self.get_potential_requirements_fulfillment_for_resolution_model(
                action_name, resolution_model)

        query_result = self.fetch_potential_requirements_fulfillment(
            action_name)
        return self._build_requirement_impact_dicts(action_name, query_result)

    def get_potential_requirements_fulfillment_for_resolution_model(
            self,
            action_name: str,
            resolution_model: str
    ) -> List[RequirementImpactDict]:
        """
        Get potential relaxed requirement fulfillment using a fixed resolution model.

        :param action_name: ROS interface/action name
        :param resolution_model: resolution model name
        :return: list of RequirementImpactDict
        """
        query_result = self.fetch_potential_requirements_fulfillment_for_resolution_model(
            action_name, resolution_model)
        return self._build_requirement_impact_dicts(action_name, query_result)

    def fetch_all_requirements(self):
        """
        Fetch all requirements names.

        :return: fetch query result
        """
        query = """
            match
                $req isa relaxed_requirement;
            fetch
                $req: requirement_name;
        """
        return self.fetch_database(query)

    def get_all_requirements(self):
        """
        Get all requirements names.

        :return: list with requirement names
        """
        query_result = self.fetch_all_requirements()
        return [result['req']['requirement_name'][0]['value']
                for result in query_result if len(result['req']['requirement_name']) > 0]

    def fetch_all_expressions(self):
        """
        Fetch all expressions names.

        :return: fetch query result
        """
        query = """
            match
                $expr isa expression;
            fetch
                $expr: expression_name;
        """
        return self.fetch_database(query)

    def get_all_expressions(self):
        """
        Get all expressions names.

        :return: list with expressions names
        """
        query_result = self.fetch_all_expressions()
        return [result['expr']['expression_name'][0]['value']
                for result in query_result if len(result['expr']['expression_name']) > 0]

    def get_expression_satisfied(self, expression_name):
        query = f"""
            match
                $expr isa logical_expression,
                    has expression_name '{expression_name}',
                    has expression_satisfied $expression_satisfied;
            fetch
                $expression_satisfied;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['expression_satisfied']['value']

    def fetch_reconfiguration_plan(self, rule_name: str):
        """
        Fetch adaptation plan for a rule.

        :param rule_name: rule name
        :param value: measured value
        :return: query result
        """
        query = f"""
            match
                (tactic:$t, consequent:$fa) isa tactic_rule, has rule_name '{rule_name}';
                $plan (feature_adaptation: $fa) isa reconfiguration_plan;
                (plan:$plan, action: $res_action) isa plan_action_indexed, has action_index $index;
            fetch
                $index;
                set_parameter_action: {{
                    match
                        $res_action (
                            node: $node,
                            parameter: $parameter,
                            parameter_value: $parameter_value) isa! set_nodes_parameters;
                    fetch
                        $node: node_name;
                        $parameter: parameter_name;
                        param_value_array: {{
                            match
                                $parameter_value isa ValueArray;
                                $param_index
                                 (array: $parameter_value, array_value: $value) isa at_index;
                            fetch
                                $param_index: index;
                                $value: attribute;
                        }};
                        param_value_singleton: {{
                            match
                                $parameter_value isa $value_type;
                                $value_type sub! ValueSingleton;
                            fetch
                                $parameter_value: attribute;
                        }};
                }};
                set_lifecycle_action: {{
                    match
                        $res_action (node: $node) isa! set_lifecycle_state;
                    fetch
                        $node: node_name;
                        $res_action: lifecycle_state;
                }};
            sort $index;
        """
        return self.fetch_database(query)

    def get_reconfiguration_plan(self, tactic_rule: str) -> AdaptationPlan:
        query_result = self.fetch_reconfiguration_plan(tactic_rule)
        return AdaptationPlan.from_typedb_results(query_result)
