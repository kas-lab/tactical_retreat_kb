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
import logging
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypedDict
from typing import Union

from ros_typedb.typedb_helpers import convert_py_type_to_query_type
from ros_typedb.typedb_interface import TypeDBInterface


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


class ROSActionResultDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    action_name: str  #: action name
    action_type: str  #: action type


class RuntimeNodeDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    namespace: str  #: node namespace
    node_name: str  #: node name


def node_query_to_node_dict(
        query_result: List[dict]) -> List[RuntimeNodeDict]:
    """Convert fetch query results to a list of node dicts.

    :param query_result: list of fetch result dicts with 'node_name' and 'namespace' keys.
    :return: list of RuntimeNodeDict sorted by node_name then namespace.
    """
    # TypeDB 3 fetch projections guarantee a single scalar per key;
    # the old multi-value cardinality guard from TypeDB 2 is no longer needed.
    node_dict = []
    for result in query_result:
        node_dict.append({
            'node_name': result['node_name'],
            'namespace': result['namespace'],
        })
    # Sort list to guarantee deterministic list order
    node_dict.sort(key=lambda d: (d['node_name'], d['namespace']))
    return node_dict


class TacticalRetreatInterface:
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
        """
        Initialise TacticalRetreatInterface.

        :param address: TypeDB server address (e.g. 'localhost:1729').
        :param database_name: name of the TypeDB database.
        :param schema_path: list of .tql schema file paths.
        :param data_path: list of .tql data file paths.
        :param force_database: delete and recreate database if it exists.
        :param force_data: clear all data before loading data_path files.
        :param infer: enable inference engine.
        """
        self.db = TypeDBInterface(
            address,
            database_name,
            schema_path,
            data_path,
            force_database,
            force_data,
            infer)

    def delete_database(self) -> None:
        """Delete the database."""
        self.db.delete_database()

    def fetch_subnodes(self, node_name: str,
                       namespace: str = '') -> List[dict]:
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
            fetch {{
                "node_name": $subnode.node_name,
                "namespace": $subnode.namespace
            }};
        """
        return self.db.fetch_database(query)

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
            self.fetch_subnodes(node_name, namespace))

    def fetch_action_clients_nodes(
            self, action_name: str) -> List[dict]:
        """
        Fetch action clients and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                $action_client isa ActionClient, has interface_name '{action_name}';
                (node: $node, client: $action_client) isa has_action;
            fetch {{
                "node_name": $node.node_name,
                "namespace": $node.namespace
            }};
        """
        return self.db.fetch_database(query)

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
            self, action_name: str) -> List[dict]:
        """
        Fetch action servers and returns it as a typedb fetch query result.

        :param action: action name
        :return: fetch query result
        """
        query = f"""
            match
                $action_server isa ActionServer, has interface_name '{action_name}';
                (node: $node, server: $action_server) isa has_action;
            fetch {{
                "node_name": $node.node_name,
                "namespace": $node.namespace
            }};
        """
        return self.db.fetch_database(query)

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
            self, node_name: str, namespace: str = '') -> List[dict]:
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
            fetch {{
                "interface_name": $action_client.interface_name,
                "interface_type": $action_client.interface_type
            }};
        """
        return self.db.fetch_database(query)

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
            ros_action_result_dict.append({
                'action_name': result['interface_name'],
                'action_type': result['interface_type'],
            })
        ros_action_result_dict.sort(key=lambda d: (d['action_name'], d['action_type']))
        return ros_action_result_dict

    def fetch_connected_action_server_nodes(
            self, node_name: str, namespace: str = '') -> List[dict]:
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
            fetch {{
                "node_name": $server_node.node_name,
                "namespace": $server_node.namespace
            }};
        """
        return self.db.fetch_database(query)

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
                node_name, namespace))

    def fetch_connected_subscriber_nodes(
            self, node_name: str, namespace: str = '') -> List[dict]:
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
            fetch {{
                "node_name": $subscriber_node.node_name,
                "namespace": $subscriber_node.namespace
            }};
        """
        return self.db.fetch_database(query)

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
                node_name, namespace))

    def fetch_tactics(
            self, resolution_model: str) -> List[dict]:
        """
        Fetch all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: fetch query result
        """
        query = f"""
            match
                (tactic: $tactic) isa resolution_model,
                    has resolution_model_name '{resolution_model}';
            fetch {{
                "tactic_name": $tactic.tactic_name
            }};
        """
        return self.db.fetch_database(query)

    def get_tactics(self, resolution_model: str) -> List[str]:
        """
        Get all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: list of tactic names
        """
        query_result = self.fetch_tactics(resolution_model)
        return [result['tactic_name'] for result in query_result]

    def fetch_all_tactic_rules(self) -> List[dict]:
        """
        Fetch all tactic rules names.

        :return: fetch query result
        """
        query = """
            match
                $tactic_rule isa tactic_rule;
            fetch {{
                "rule_name": $tactic_rule.rule_name
            }};
        """
        return self.db.fetch_database(query)

    def get_all_tactic_rules(self) -> List[str]:
        """
        Get all tactic tactic rules names.

        :return: list of tactic rule names
        """
        query_result = self.fetch_all_tactic_rules()
        return [result['rule_name'] for result in query_result]

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
        return (self.db.get_aggregate_database(query) > 0)

    def fetch_neighbours(
            self, node_name: str, namespace: str = '') -> List[dict]:
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
            fetch {{
                "node_name": $neighbour.node_name,
                "namespace": $neighbour.namespace
            }};
        """
        return self.db.fetch_database(query)

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
                node_name, namespace))

    def fetch_connected_nodes(
            self, node_name: str, namespace: str = '') -> List[dict]:
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
            fetch {{
                "node_name": $connected.node_name,
                "namespace": $connected.namespace
            }};
        """
        return self.db.fetch_database(query)

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
                node_name, namespace))

    def fetch_applicable_tactics(self,
                                 resolution_model: str,
                                 interface_name: str) -> List[dict]:
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
            fetch {{
                "rule_name": $tactic_rule.rule_name
            }};
        """
        return self.db.fetch_database(query)

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
        return sorted(result['rule_name'] for result in query_result)

    def fetch_relaxed_requirement_fulfillment(
            self,
            system_name: str,
            requirement_name: str) -> List[dict]:
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
            fetch {{ "fulfillment": $fulfillment }};
        """
        return self.db.fetch_database(query)

    def get_relaxed_requirement_fulfillment(
            self,
            system_name: str,
            requirement_name: str) -> List[dict]:
        """
        Fetch relaxed requirement fulfillment.

        :param system_name: system name
        :param requirement_name: requirement name
        :return: fulfillment value
        """
        return self.fetch_relaxed_requirement_fulfillment(
            system_name, requirement_name)[0]['fulfillment']

    def fetch_in_effect_requirement_fulfillment(self) -> List[dict]:
        """
        Fetch all relaxed requirement in effect fulfillment.

        :return: fetch query result
        """
        query = """
            match
                $req isa relaxed_requirement,
                    has in_effect true;
            fetch {{
                "requirement_name": $req.requirement_name,
                "fulfillment": $req.fulfillment
            }};
        """
        return self.db.fetch_database(query)

    def get_in_effect_requirement_fulfillment(self) -> List[dict]:
        """
        Fetch all relaxed requirement in effect fulfillment.

        :return: fetch query result
        """
        query_result = self.fetch_in_effect_requirement_fulfillment()
        query_dict = [
            {'requirement_name': result['requirement_name'],
             'fulfillment': result['fulfillment']}
            for result in query_result]
        return sorted(query_dict, key=lambda item: item['requirement_name'])

    def set_requirement_in_effect(self, requirement_name: str, in_effect: bool
                                  ) -> Optional[Iterator]:
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
        return self.db.insert_database(query)

    def fetch_requirement_in_effect(self, requirement_name: str
                                    ) -> List[dict]:
        """
        Fetch relaxed requirement in effect attribute.

        :param requirement_name: requirement name
        :return: fetch query result
        """
        query = f"""
            match
                $req isa relaxed_requirement,
                    has requirement_name '{requirement_name}';
            fetch {{
                "in_effect": $req.in_effect
            }};
        """
        return self.db.fetch_database(query)

    def get_requirement_in_effect(self, requirement_name: str) -> bool:
        """
        Get relaxed requirement in effect attribute.

        :param requirement_name: requirement name
        :return: boolean indicating if the requirement is in effect
        """
        query_result = self.fetch_requirement_in_effect(requirement_name)
        if query_result is None or len(query_result) == 0:
            logger.warning(
                'Requirement %s not found in the knowledge base.',
                requirement_name)
            return False
        if query_result[0].get('in_effect') is None:
            return False
        return query_result[0]['in_effect']

    def fetch_latest_measurement(
            self, measure_name: str) -> List[dict]:
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
                {{
                    $measurement_val isa ValueDouble, has double_value $value;
                }} or {{
                    $measurement_val isa ValueInteger, has integer_value $value;
                }} or {{
                    $measurement_val isa ValueString, has string_value $value;
                }} or {{
                    $measurement_val isa ValueBool, has bool_value $value;
                }};
            fetch {{
                "value": $value
            }};
        """
        return self.db.fetch_database(query)

    def fetch_all_measurements(
            self, measure_name: str) -> List[dict]:
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
                {{
                    $measurement_val isa ValueDouble, has double_value $value;
                }} or {{
                    $measurement_val isa ValueInteger, has integer_value $value;
                }} or {{
                    $measurement_val isa ValueString, has string_value $value;
                }} or {{
                    $measurement_val isa ValueBool, has bool_value $value;
                }};
            fetch {{
                "value": $value
            }};
        """
        return self.db.fetch_database(query)

    def get_latest_measurement(self, measure_name: str) -> Union[float, int, str, bool, List]:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param action_name: name of the ROS action
        :param action_name: type of the ROS action
        :return: list containing all tactic's names that are applicable
        """
        query_result = self.fetch_latest_measurement(measure_name)

        if len(query_result) == 0:
            return float('nan')

        return query_result[0]['value']

    def fetch_tactic_rule_valid(
            self, tactic_rule: str) -> List[dict]:
        """
        Fetch whether a tactic_rule is valid.

        :param tactic_rule: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                $tr isa tactic_rule, has rule_name '{tactic_rule}';
            fetch {{
                "rule_valid": $tr.rule_valid
            }};
        """
        return self.db.fetch_database(query)

    def get_tactic_rule_valid(self, tactic_rule: str) -> bool:
        """
        Get whether a tactic_rule is valid.

        :param tactic_rule: measure name
        :return: true or false
        """
        query_result = self.fetch_tactic_rule_valid(tactic_rule)
        return query_result[0]['rule_valid']

    def is_feature_selectable(self, feature_name: str) -> bool:
        """
        Return whether a feature is selectable.

        :param feature_name: feature name
        :return: true or false
        """
        query = f"""
            match
                $f isa Feature, has feature_name '{feature_name}';
            fetch {{
                "selectable": $f.selectable
            }};
        """
        query_result = self.db.fetch_database(query)
        return query_result[0]['selectable']

    def is_node_running(self, node_name: str) -> bool:
        """
        Return whether a ROS node is running.

        :param node_name: node name
        :return: true or false
        """
        query = f"""
            match
                $node isa ROSNode, has node_name '{node_name}';
            fetch {{
                "running": $node.running
            }};
        """
        query_result = self.db.fetch_database(query)
        return query_result[0]['running']

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
            fetch {{
                "feasible": $ra.feasible
            }};
        """
        query_result = self.db.fetch_database(query)
        return query_result[0]['feasible']

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
            fetch {{
                "feasible": $ra.feasible
            }};
        """
        query_result = self.db.fetch_database(query)
        return query_result[0]['feasible']

    def fetch_measures_interfaces(
            self, include_qos: bool = True) -> List[dict]:
        """
        Fetch measures and their source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        if include_qos:
            query = """
            match
                $measure isa Measure, has measure_name $measure_name;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface;
                $source isa! Publisher;
                (interface: $source, qos: $qos) isa has_qos;
                $qos isa QoSProfile;
            fetch {
                "measure_name": $measure_name,
                "measurement_function_name":
                    $measurement_interface.measurement_function_name,
                "measurement_function_lib":
                    $measurement_interface.measurement_function_lib,
                "measurement_function_args":
                    $measurement_interface.measurement_function_args,
                "measurement_proxy": $measurement_interface.measurement_proxy,
                "measurement_period": $measurement_interface.measurement_period,
                "service_request_kwargs":
                    $measurement_interface.service_request_kwargs,
                "interface_name": $source.interface_name,
                "interface_type": $source.interface_type,
                "reliability": $qos.reliability,
                "history": $qos.history,
                "depth": $qos.depth,
                "durability": $qos.durability,
                "deadline": $qos.deadline,
                "lifespan": $qos.lifespan,
                "liveliness": $qos.liveliness,
                "lease_duration": $qos.lease_duration
            };
            """
        else:
            query = """
            match
                $measure isa Measure, has measure_name $measure_name;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface;
            fetch {
                "measure_name": $measure_name,
                "measurement_function_name":
                    $measurement_interface.measurement_function_name,
                "measurement_function_lib":
                    $measurement_interface.measurement_function_lib,
                "measurement_function_args":
                    $measurement_interface.measurement_function_args,
                "measurement_proxy": $measurement_interface.measurement_proxy,
                "measurement_period": $measurement_interface.measurement_period,
                "service_request_kwargs":
                    $measurement_interface.service_request_kwargs,
                "interface_name": $source.interface_name,
                "interface_type": $source.interface_type
            };
            """
        return self.db.fetch_database(query)

    def get_measures_interfaces(self, include_qos: bool = True):
        """
        Get measures and source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        result_dict_list = []
        for result in self.fetch_measures_interfaces(include_qos=include_qos):
            result_dict = {}

            measure_name = result.get('measure_name')
            if measure_name is not None:
                result_dict['measure_name'] = measure_name

            # 'source' type is 'Publisher' when include_qos=True (query filters isa! Publisher).
            # When include_qos=False, source type is not projected by the query; set to None.
            result_dict['source'] = 'Publisher' if include_qos else None
            result_dict['interface_name'] = result.get('interface_name')
            result_dict['interface_type'] = result.get('interface_type')

            for attribute_label in (
                'measurement_function_name',
                'measurement_function_lib',
                'measurement_function_args',
                'measurement_proxy',
                'measurement_period',
                'service_request_kwargs',
            ):
                attribute_value = result.get(attribute_label)
                if attribute_value is not None:
                    result_dict[attribute_label] = attribute_value

            if include_qos:
                qos_dict = {}
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
                    attribute_value = result.get(attribute_label)
                    if attribute_value is not None:
                        qos_dict[attribute_label] = attribute_value
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
    ) -> Optional[Iterator]:
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

        delete_query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
                $measurement (measure: $measure) isa measurement,
                    has latest $latest;
                $latest == true;
            delete $measurement has $latest;
        """
        self.db.delete_from_database(delete_query)

        time = convert_py_type_to_query_type(datetime.now())
        query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
            insert
                {value_query}
                $measurement (measure: $measure, measurement_value: {variable_name})
                    isa measurement,
                    has measurement_time {time},
                    has latest true;
        """
        return self.db.insert_database(query)

    def fetch_tactic_rule_impacts_fulfillment(self, impacted_name: str, tactic_rule_name: str):
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
            fetch {{ "fulfillment": $fulfillment }};
        """
        query_result = self.db.fetch_database(query)
        return query_result

    def fetch_tactic_rule_impacts_requirement(self, impacted_name: str, tactic_rule_name: str):
        """
        Fetch hypothetical fulfillment of a requirement given a tactic rule.

        :param impacted_name: requirement name
        :param rule_name: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                $impacted isa relaxed_requirement,
                    has requirement_name '{impacted_name}';
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                $tr_impacts (impacted: $impacted, tactic_rule: $tr) isa tactic_rule_impacts,
                    has fulfillment $fulfillment;
            fetch {{ "fulfillment": $fulfillment }};
        """
        query_result = self.db.fetch_database(query)
        return query_result

    def get_tactic_rule_impacts_requirement(self, impacted_name: str, rule_name: str) -> float:
        """
        Get hypothetical fulfillment of a expression or requirement given a tactic rule.

        :param impacted_name: expression or requirement name
        :param rule_name: tactic rule name
        :return: fulfillment
        """
        query_result = self.fetch_tactic_rule_impacts_requirement(
            impacted_name, rule_name)
        return [result['fulfillment'] for result in query_result]

    def fetch_resulting_effect_value(self, tactic_rule: str, measure_name: str
                                     ) -> List[dict]:
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
            fetch {{ "resulting_effect_value": $resulting_effect_value }};
        """
        return self.db.fetch_database(query)

    def get_resulting_effect_value(self, tactic_rule: str, measure_name: str) -> float:
        """
        Get resulting effect value of a tactic on a measure.

        :param tactic_rule: tactic rule name
        :param measure_name: measure name
        :return: resulting effect value
        """
        query_result = self.fetch_resulting_effect_value(
            tactic_rule, measure_name)
        return query_result[0]['resulting_effect_value']

    def fetch_fuzzy_membership_degree(self, expression_name: str
                                      ) -> List[dict]:
        """
        Fetch fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: membership degree
        """
        query = f"""
            match
                $fe isa fuzzy_expression, has expression_name '{expression_name}',
                    has membership_degree $membership_degree;
            fetch {{ "membership_degree": $membership_degree }};
        """
        return self.db.fetch_database(query)

    def get_fuzzy_membership_degree(self, expression_name: str) -> str:
        """
        Get fuzzy membership of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: membership type
        """
        query_result = self.fetch_fuzzy_membership_degree(expression_name)
        return query_result[0]['membership_degree']

    def fetch_relaxed_expression_fulfillment(self, expression_name: str
                                             ) -> List[dict]:
        """
        Fetch fuzzy fulfillment of a fuzzy expression.

        :param expression_name: fuzzy expression name
        """
        query = f"""
            match
                $relaxed_expression isa relaxed_expression,
                    has expression_name '{expression_name}',
                    has fulfillment $fulfillment;
            fetch {{ "fulfillment": $fulfillment }};
        """
        return self.db.fetch_database(query)

    def get_relaxed_expression_fulfillment(self, expression_name: str) -> str:
        """
        Get fuzzy fulfillment of a fuzzy expression.

        :param expression_name: fuzzy expression name
        :return: fulfillment type
        """
        query_result = self.fetch_relaxed_expression_fulfillment(expression_name)
        return query_result[0]['fulfillment']

    def fetch_potential_requirements_fulfillment(
            self,
            action_name: str,
            resolution_model: Optional[str] = None
            ) -> List[dict]:
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
            fetch {{
                "rule_name": $rule_name,
                "fulfillment": $fulfillment,
                "requirement_name": $requirement_name
            }};
        """
        return self.db.fetch_database(query)

    def fetch_potential_requirements_fulfillment_for_resolution_model(
            self,
            action_name: str,
            resolution_model: str
            ) -> List[dict]:
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
            fetch {{
                "rule_name": $rule_name,
                "fulfillment": $fulfillment,
                "requirement_name": $requirement_name
            }};
        """
        return self.db.fetch_database(query)

    @staticmethod
    def _build_requirement_impact_dicts(
            action_name: str,
            query_result: List[dict]
            ) -> List[RequirementImpactDict]:
        """Convert query result rows to requirement impact dataclasses."""
        return [
            RequirementImpactDict(
                action_name=action_name,
                tactic_rule=result['rule_name'],
                requirement_name=result['requirement_name'],
                fulfillment=result['fulfillment']
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
            fetch {{
                "requirement_name": $req.requirement_name
            }};
        """
        return self.db.fetch_database(query)

    def get_all_requirements(self):
        """
        Get all requirements names.

        :return: list with requirement names
        """
        query_result = self.fetch_all_requirements()
        return [result['requirement_name']
                for result in query_result if result.get('requirement_name') is not None]

    def fetch_all_expressions(self):
        """
        Fetch all expressions names.

        :return: fetch query result
        """
        query = """
            match
                $expr isa expression;
            fetch {{
                "expression_name": $expr.expression_name
            }};
        """
        return self.db.fetch_database(query)

    def get_all_expressions(self):
        """
        Get all expressions names.

        :return: list with expressions names
        """
        query_result = self.fetch_all_expressions()
        return [result['expression_name']
                for result in query_result if result.get('expression_name') is not None]

    def get_expression_satisfied(self, expression_name):
        query = f"""
            match
                $expr isa logical_expression,
                    has expression_name '{expression_name}',
                    has expression_satisfied $expression_satisfied;
            fetch {{ "expression_satisfied": $expression_satisfied }};
        """
        query_result = self.db.fetch_database(query)
        return query_result[0]['expression_satisfied']
