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
from datetime import datetime
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

from typedb.driver import ConceptMap


logger = logging.getLogger(__name__)


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
        value_query = f"{variable_name} isa ValueString, has string_value '{value}';"
    elif isinstance(value, float):
        value_query = f'{variable_name} isa ValueDouble, has double_value {value};'
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
            infer: Optional[bool] = False) -> None:

        super().__init__(
            address,
            database_name,
            schema_path,
            data_path,
            force_database,
            force_data,
            infer
        )

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
            self.fetch_action_clients(action_name))

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
                        action['action_name']))
                return ros_action_result_dict
            if len(action['interface_type']) == 0:
                logger.error(
                    'In get_action_clients_names: action {} does not have an action_type'.format(
                        action['action_name']))
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

    def fetch_applicable_tactics(self,
                                 resolution_model: str,
                                 interface_name: str) -> List[dict[str, MatchResultDict]]:
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
        query = f"""
            match
                $system isa System, has system_name '{system_name}';
                (system: $system) isa relaxed_requirement,
                    has requirement_name '{requirement_name}',
                    has fulfillment $fulfillment;
            fetch $fulfillment;
        """
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
            system_name, requirement_name)[0]['fulfillment']['value']

    def fetch_in_effect_requirement_fulfillment(self) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all relaxed requirement in effect fulfillment.

        :return: fetch query result
        """
        query = """
            match
                $req isa relaxed_requirement,
                    has in_effect true;
            fetch
                $req: requirement_name, fulfillment;
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
             'fulfillment': result['req']['fulfillment'][0]['value']} for result in query_result]
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

    def get_latest_measurement(self, measure_name: str) -> Union[float, int, str, bool, List]:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param action_name: name of the ROS action
        :param action_name: type of the ROS action
        :return: list containing all tactic's names that are applicable
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

    def is_feature_selectable(self, feature_name: str) -> bool:
        """
        Return whether a feature is selectable.

        :param feature_name: feature name
        :return: true or false
        """
        query = f"""
            match
                $f isa Feature, has feature_name '{feature_name}';
            fetch
                $f: selectable;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['f']['selectable'][0]['value']

    def is_node_running(self, node_name: str) -> bool:
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
        return query_result[0]['node']['running'][0]['value']

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

    def fetch_measures_inferfaces(self):
        query = """
            match
                $measure isa Measure, has measure_name $measure_name;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface;
            fetch
                $measure_name;
                $measurement_interface: attribute;
                $source: interface_name, interface_type;
            qos_sub_query: {
                match
                    $source isa! Publisher;
                    (interface: $source, qos: $qos) isa has_qos;
                    $qos isa QoSProfile;
                fetch
                    $qos: attribute;
            };
        """
        return self.fetch_database(query)

    def get_measures_interfaces(self):
        result_dict_list = []
        for result in self.fetch_measures_inferfaces():
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
            for attribute in measurement_interface.get('attribute'):
                attribute_label = attribute.get('type').get('label')
                result_dict[attribute_label] = convert_query_type_to_py_type(
                    attribute)

            qos_list = result.get('qos_sub_query')
            qos_dict = {}
            if isinstance(qos_list, list) and qos_list:
                qos = qos_list[0].get('qos')
                for attribute in qos.get('attribute'):
                    attribute_label = attribute.get('type').get('label')
                    qos_dict[attribute_label] = convert_query_type_to_py_type(
                        attribute)

            if qos_dict:
                result_dict['qos'] = qos_dict

            if result_dict:
                result_dict_list.append(result_dict)

        return result_dict_list

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
        value_query = ''
        variable_name = ''
        if (isinstance(value, list)):
            query_fragments = []
            query_fragments.append('$array isa ValueArray;')
            variable_name = '$array'
            for index, item in enumerate(value):
                value_query_, variable_name_ = create_value_query(item, index)
                query_fragments.append(
                    f"""
                        {value_query_}
                        (array: $array, array_value: {variable_name_}) isa at_index,
                            has index {index};
                    """
                )
            value_query = '\n'.join(query_fragments)
        else:
            value_query, variable_name = create_value_query(value)

        time = convert_py_type_to_query_type(datetime.now())
        query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
            insert
                {value_query}
                $measurement (measure: $measure, measurement_value: {variable_name})
                    isa measurement,
                    has measurement_time {time};
        """
        return self.insert_database(query)

    def fetch_fuzzy_membership(self, expression_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: fetch query result
        """
        query = f"""
            match
                $fe isa fuzzy_expression, has fuzzy_expression_name '{expression_name}';
            fetch
                $fe: membership;
        """
        return self.fetch_database(query)

    def get_fuzzy_membership(self, expression_name: str) -> str:
        """
        Get fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: membership type
        """
        query_result = self.fetch_fuzzy_membership(expression_name)
        return query_result[0]['fe']['membership'][0]['value']