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
logger = logging.getLogger(__name__)

from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import TypeDBInterface

# from typing import Iterator
# from typing import Literal
# from typing import Tuple
from typing import List
from typing import TypedDict
from typing import Optional

from collections import deque

class ROSActionResultDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    action_name: str  #: action name
    action_type: str  #: action type

class RuntimeNodeDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    namespace: str  #: node namespace
    node_name: str  #: node name

def runtime_node_query_to_runtime_node_dict(query_result: List[dict[str, MatchResultDict]]) -> List[RuntimeNodeDict]:
    runtime_node_dict = list()
    for result in query_result:
        runtime_node = result.get('runtime_node')
        if len(runtime_node['namespace']) > 1:
            logger.error('In runtime_node_query_to_runtime_node_dict: runtime node has more than 1 namespace')
            return runtime_node_dict
        if len(runtime_node['node_name']) > 1:
            logger.error('In runtime_node_query_to_runtime_node_dict: runtime node has more than 1 node_name')
            return runtime_node_dict
        runtime_node_dict.append({
            'namespace': runtime_node['namespace'][0]['value'],
            'node_name': runtime_node['node_name'][0]['value'],
            }
        )
    return runtime_node_dict

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

    def fetch_subnodes(self, node_name: str, namespace: str = "") -> List[dict[str, MatchResultDict]]:
        """
        Fetch subnodes of a running node and returns it as a typedb fetch query result.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: fetch query result
        """
        query = f"""
            match
                (node: $parent_node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
                (node:$parent_node, subnode: $subnode) isa subnode;
                $runtime_node (node: $subnode) isa runtime_node;
            fetch
                $runtime_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_subnodes(self, node_name: str, namespace: str = "") -> List[RuntimeNodeDict]:
        """
        Get the subnodes of a running node and returns it as a list of dicts.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: list of dictionaries with the node_name and namespace of the subnodes
        """
        return runtime_node_query_to_runtime_node_dict(self.fetch_subnodes(node_name, namespace))

    def fetch_action_clients_nodes(self, action_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch action clients and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                (client: $client) isa ros_action, has action_name '{action_name}';
                $runtime_node (node: $client) isa runtime_node;
            fetch
                $runtime_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_action_clients_nodes(self, action_name: str) -> List[RuntimeNodeDict]:
        """
        Get action clients and returns it as a list of dicts.

        :param action: action name
        :return: list of dictionaries with the node_name and namespace of the client nodes
        """
        return runtime_node_query_to_runtime_node_dict(self.fetch_action_clients(action_name))

    def fetch_action_server_nodes(self, action_name: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch action servers and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                (server: $server) isa ros_action, has action_name '{action_name}';
                $runtime_node (node: $server) isa runtime_node;
            fetch
                $runtime_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_action_server_nodes(self, action_name: str) -> List[RuntimeNodeDict]:
        """
        Get action clients and returns it as a list of dicts.

        :param action: action name
        :return: list of dictionaries with the node_name and namespace of the client nodes
        """
        return runtime_node_query_to_runtime_node_dict(self.fetch_action_server_nodes(action_name))

    def fetch_action_clients_names(self, node_name: str, namespace: str = '') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the name and type of all action clients of a running node and returns it as a typedb fetch query result.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                (node: $node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
                $action (client: $node) isa ros_action;
            fetch
                $action: action_name, action_type;
        """
        return self.fetch_database(query)

    def get_action_clients_names(self, node_name: str, namespace: str = '') -> List[ROSActionResultDict]:
        """
        Get the name and type of all action clients of a running node and returns it as list of dicts.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the action_name and action_type of the action clients
        """
        ros_action_result_dict = list()
        for result in self.fetch_action_clients_names(node_name, namespace):
            action = result.get('action')
            if len(action['action_name']) == 0:
                logger.error('In get_action_clients_names: action does not have an action_name')
                return ros_action_result_dict
            if len(action['action_name']) > 1:
                logger.error('In get_action_clients_names: action has more than 1 action_name')
                return ros_action_result_dict
            if len(action['action_type']) > 1:
                logger.error('In get_action_clients_names: action %s has more than 1 action_type'.format(action['action_name']))
                return ros_action_result_dict
            if len(action['action_type']) == 0:
                logger.error('In get_action_clients_names: action %s does not have an action_type'.format(action['action_name']))
                return ros_action_result_dict
            ros_action_result_dict.append({
                'action_name': action['action_name'][0]['value'],
                'action_type': action['action_type'][0]['value'],
                }
            )
        return ros_action_result_dict

    def fetch_connected_action_server_nodes(self, node_name: str, namespace: str ='') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the node name and namespace of all runtime nodes that are servers for the action clients of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                (node: $node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
                (server: $server, client: $node) isa ros_action;
                $runtime_node (node: $server) isa runtime_node;
            fetch
                $runtime_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_connected_action_server_nodes(self, node_name: str, namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the node name and namespace of all runtime nodes that are servers for the action clients of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the action server nodes
        """
        return runtime_node_query_to_runtime_node_dict(self.fetch_connected_action_server_nodes(node_name, namespace))

    def fetch_connected_subscriber_nodes(self, node_name: str, namespace: str ='') -> List[dict[str, MatchResultDict]]:
        """
        Fetch the node name and namespace of all runtime nodes that are subscribers of the publishers of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                (node: $node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
                (subscriber: $subscriber, publisher: $node) isa ros_topic;
                $runtime_node (node: $subscriber) isa runtime_node;
            fetch
                $runtime_node: node_name, namespace;
        """
        return self.fetch_database(query)

    def get_connected_subscriber_nodes(self, node_name: str, namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the node name and namespace of all runtime nodes that are subscribers of the publishers of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the subscriber nodes
        """
        return runtime_node_query_to_runtime_node_dict(self.fetch_connected_subscriber_nodes(node_name, namespace))

    def get_active_neighbours(self, node_name: str, namespace: str = '') -> List[RuntimeNodeDict]:
        """
        Get the active neighbours of a running node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: list of dictionaries with the node_name and namespace of the neighbour nodes
        """
        # Collect neighbors in a set of tuples
        neighbours = set()

        nodes = {(node_name, namespace)}
        for n in self.get_subnodes(node_name, namespace):
            nodes.add((n['node_name'], n.get('namespace', '')))
            # consider subnodes as neighbours
            neighbours.add((n['node_name'], n.get('namespace', '')))

        for n, ns in nodes:
            # Expect these to return lists of dicts: {'node_name':..., 'namespace':...}
            for action_server in self.get_connected_action_server_nodes(n, ns):
                neighbours.add((action_server['node_name'], action_server['namespace']))
            for subscriber_node in self.get_connected_subscriber_nodes(n, ns):
                neighbours.add((subscriber_node['node_name'], subscriber_node['namespace']))

        # Remove the node and its subnodes. They might appear if they are both the efferent/afferent
        # neighbours.difference_update(nodes)
        neighbours.difference_update({(node_name, namespace)})

        # make order deterministic
        ordered = sorted(neighbours)
        return [{'node_name': n, 'namespace': ns} for n, ns in ordered]

    def get_active_connected_nodes(self, runtime_nodes: List[RuntimeNodeDict]) -> List[RuntimeNodeDict]:
        stack = deque(runtime_nodes)
        visited = set()

        while len(stack) > 0:
            node = stack.pop()
            if (node['node_name'], node['namespace']) not in visited:
                visited.add((node['node_name'], node['namespace']))
                neighbours = self.get_active_neighbours(node['node_name'], node['namespace'])
                for n in neighbours:
                    if (n['node_name'], n['namespace']) not in visited and n not in stack:
                        stack.append(n)

        ordered = sorted(visited)
        return [{'node_name': n, 'namespace': ns} for n, ns in ordered]

    def fetch_tactics(self, resolution_model: str) -> List[dict[str, MatchResultDict]]:
        """
        Fetch all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: fetch query result
        """
        query = f"""
            match
                (tactic: $tactic) isa resolution_model, has resolution_model_name '{resolution_model}';
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
        return [result['tactic']['tactic_name'][0]['value'] for result in query_result]

    def does_tactic_affect_nodes(self, tactic_name: str, node_name: str, namespace: str = '') -> bool:
        query = f"""
            match
                $tactic isa Tactic, has tactic_name '{tactic_name}';
                (tactic: $tactic, consequent: $consequent) isa tactic_rule;
                {{
                    $consequent isa Feature;
                    (variant: $consequent, resolution_action: $resolution_action) isa variant_resolution;
                }} or {{
                    $consequent (expression: $expression) isa and_expression;
                    $expression isa Feature;
                    (variant: $expression, resolution_action: $resolution_action) isa variant_resolution;
                }};
                $resolution_action (node: $node) isa resolution_action;
                $runtime_node (node: $node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
            get $runtime_node;
            count;
        """
        return (self.get_aggregate_database(query) > 0 )