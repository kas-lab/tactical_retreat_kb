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

from typing import Optional
from typing import TypedDict
from typing import List
from ros_typedb.typedb_interface import TypeDBInterface
from ros_typedb.typedb_interface import MatchResultDict
import logging
logger = logging.getLogger(__name__)


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
                       namespace: str = "") -> List[dict[str, MatchResultDict]]:
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
            namespace: str = "") -> List[RuntimeNodeDict]:
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
        ros_action_result_dict = list()
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
            self.fetch_connected_action_server_nodes(node_name, namespace), 'server_node')

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
            self.fetch_connected_subscriber_nodes(node_name, namespace), 'subscriber_node')

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
                (tactic: $tactic, consequent: $consequent) isa tactic_rule;
                {{
                    $consequent isa Feature;
                    (variant: $consequent, resolution_action: $resolution_action) isa
                        variant_resolution;
                }} or {{
                    $consequent (expression: $expression) isa and_expression;
                    $expression isa Feature;
                    (variant: $expression, resolution_action: $resolution_action) isa
                        variant_resolution;
                }};
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
                                 action_name: str,
                                 action_type: str) -> List[dict[str,
                                                                MatchResultDict]]:
        """
        Fetch all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param action_name: name of the ROS action
        :param action_name: type of the ROS action
        :return: fetch query result
        """
        query = f"""
            match
                $action isa ActionServer, has interface_name '{action_name}',
                    has interface_type '{action_type}';
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                (action: $action, resolution_model: $resolution_model, tactic_rule: $tactic_rule)
                    isa applicable_tactics;
            fetch
                $tactic_rule: rule_name;
        """
        return self.fetch_database(query)

    def get_applicable_tactics(
            self,
            resolution_model: str,
            action_name: str,
            action_type: str) -> List[str]:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param action_name: name of the ROS action
        :param action_name: type of the ROS action
        :return: list containing all tactic's names that are applicable
        """
        query_result = self.fetch_applicable_tactics(
            resolution_model, action_name, action_type)
        return sorted(
            result['tactic_rule']['rule_name'][0]['value']
            for result in query_result
        )
