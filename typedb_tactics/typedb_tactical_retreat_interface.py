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
"""TypeDB query facade for Tactical Retreat domain operations."""

from dataclasses import dataclass
from datetime import datetime
import logging
import time
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypedDict
from typing import Union

from ros_typedb.typedb_helpers import convert_py_type_to_query_type
from ros_typedb.typedb_interface import TypeDBInterface
from ros_typedb.typedb_interface import TypeDBQueryError


logger = logging.getLogger(__name__)


@dataclass
class RequirementImpactDict():
    """Dataclass for requirement impact information."""

    action_name: str  #: name of the action
    requirement_name: str  #: name of the requirement
    tactic_rule: str  #: name of the tactic rule
    fulfillment: float  #: fulfillment value


def create_value_query(value, suffix=''):
    """
    Build a TypeQL insert snippet for a scalar ``Value*`` instance.

    :param value: scalar Python value to encode (str, float, bool, or int).
    :param suffix: optional suffix to make variable names unique.
    :return: tuple ``(query_snippet, variable_name)`` or ``None`` if unsupported.
    """
    if not isinstance(value, (str, float, int, bool, list)):
        logger.error(
            'Unsupported type %s for value %s',
            type(value),
            value)
        return None

    variable_name = f'$value{suffix}'

    value_query = ''
    if isinstance(value, str):
        value_query = f'{variable_name} isa ValueSingleton, has string_value "{value}";'
    elif isinstance(value, float):
        value_query = f'{variable_name} isa ValueSingleton, has double_value {value};'
    elif isinstance(value, bool):
        value_query = f"""{variable_name} isa ValueSingleton,
            has bool_value {convert_py_type_to_query_type(value)};"""
    elif isinstance(value, int):
        value_query = f'{variable_name} isa ValueSingleton, has integer_value {value};'
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
    """
    Convert fetch query results to a list of node dicts.

    :param query_result: list of fetch result dicts with 'node_name' and 'namespace' keys.
    :return: list of RuntimeNodeDict sorted by node_name then namespace.
    """
    # TypeDB 3 fetch projections guarantee a single scalar per key;
    # the old multi-value cardinality guard from TypeDB 2 is no longer needed.
    seen = set()
    node_dict = []
    for result in query_result:
        key = (result['node_name'], result['namespace'])
        if key in seen:
            continue
        seen.add(key)
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
            force_data: Optional[bool] = False) -> None:
        """
        Initialise TacticalRetreatInterface.

        :param address: TypeDB server address (e.g. 'localhost:1729').
        :param database_name: name of the TypeDB database.
        :param schema_path: list of .tql schema file paths.
        :param data_path: list of .tql data file paths.
        :param force_database: delete and recreate database if it exists.
        :param force_data: clear all data before loading data_path files.
        """
        self.db = TypeDBInterface(
            address,
            database_name,
            schema_path,
            data_path,
            force_database,
            force_data)

    def delete_database(self) -> None:
        """Delete the database."""
        self.db.delete_database()

    def warm_up(self) -> None:
        """
        Prime TypeDB JIT by executing representative queries once at startup.

        Queries succeed with empty results when no measurements exist — the
        NOT-branch ('no effect') in hypothetical functions still fires and
        triggers JIT compilation for the full call chain.
        """
        t_start = time.perf_counter()
        logger.info('TypeDB warm-up: starting.')

        # 1. One (rule, in_effect requirement) pair — transitively invokes all
        #    16 schema functions in discover_hypothetical_req_fulfillment.tql.
        #    JIT compilation is function-level; one call per function suffices.
        #    in_effect requirements are used to avoid slow non-effect traversals.
        try:
            rules = self.get_all_tactic_rules()
            reqs = self._get_in_effect_requirement_names()
            if rules and reqs:
                self.fetch_tactic_rule_impacts_requirement(reqs[0], rules[0])
        except Exception as e:
            logger.warning(
                'TypeDB warm-up: fetch_tactic_rule_impacts_requirement failed: %s', e)

        # 2. Applicable tactics — warms applicable_tactics function separately
        #    since fetch_potential_requirements_fulfillment calls it in production.
        try:
            models = self._get_all_resolution_models()
            interfaces = self._get_all_ros_interfaces()
            if models and interfaces:
                self.fetch_applicable_tactics(models[0], interfaces[0])
        except Exception as e:
            logger.warning('TypeDB warm-up: fetch_applicable_tactics failed: %s', e)

        # 2. Current (non-hypothetical) requirement fulfillment.
        try:
            self.fetch_in_effect_requirement_fulfillment()
        except Exception as e:
            logger.warning(
                'TypeDB warm-up: fetch_in_effect_requirement_fulfillment failed: %s', e)

        # 3. Structural tactic validity check.
        try:
            rules = self.get_all_tactic_rules()
            if rules:
                self.fetch_tactic_rule_valid(rules[0])
        except Exception as e:
            logger.warning('TypeDB warm-up: fetch_tactic_rule_valid failed: %s', e)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        logger.info('TypeDB warm-up: complete in %.0fms.', elapsed_ms)

    def fetch_database(self, query: str) -> List[dict]:
        """
        Delegate fetch query to the underlying TypeDBInterface.

        :param query: TypeQL fetch query string.
        :return: list of result dicts.
        """
        return self._fetch(query)

    def _fetch(self, query: str) -> List[dict]:
        """Run a fetch query."""
        return self.db.fetch_database(query)

    def _insert(self, query: str) -> Optional[Iterator]:
        """Run an insert query."""
        return self.db.insert_database(query)

    def _delete(self, query: str):
        """Run a delete query."""
        return self.db.delete_from_database(query)

    def _aggregate(self, query: str):
        """Run an aggregate query."""
        return self.db.get_aggregate_database(query)

    def register_method(self, method_name: str, func) -> None:
        """
        Dynamically register a function as a bound method on this instance.

        The function must accept ``self`` as its first argument (i.e. the
        ``TacticalRetreatInterface`` instance).  After registration the method
        can be called as ``kb_interface.<method_name>(...)``.

        :param method_name: attribute name to bind the method under.
        :param func: callable with signature ``func(self, *args, **kwargs)``.
        """
        import types
        setattr(self, method_name, types.MethodType(func, self))

    def fetch_attribute_from_thing(
            self,
            thing: str,
            key_attr_list: list,
            attr: str) -> list:
        """
        Fetch attribute values from a thing matched by one or more key attributes.

        :param thing: thing type name (e.g. 'less_than').
        :param key_attr_list: list of (attr_name, attr_value) pairs to match on.
        :param attr: attribute name to fetch.
        :return: list of attribute values (Python-typed).
        """
        return self.db.fetch_attribute_from_thing(thing, key_attr_list, attr)

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
        return self._fetch(query)

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
        return self._fetch(query)

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
        return self._fetch(query)

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
        return self._fetch(query)

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
        return self._fetch(query)

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
        return self._fetch(query)

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
        return self._fetch(query)

    def get_tactics(self, resolution_model: str) -> List[str]:
        """
        Get all tactic names in the given resolution model.

        :param resolution_model: name of the resolution model
        :return: list of tactic names
        """
        query_result = self.fetch_tactics(resolution_model)
        return [result['tactic_name'] for result in query_result]

    def _fetch_all_resolution_models(self) -> List[dict]:
        """
        Fetch all resolution model names.

        :return: fetch query result
        """
        query = """
            match
                $resolution_model isa resolution_model;
            fetch {
                "resolution_model_name": $resolution_model.resolution_model_name
            };
        """
        return self._fetch(query)

    def _get_all_resolution_models(self) -> List[str]:
        """
        Get all resolution model names.

        :return: list of resolution model names
        """
        query_result = self._fetch_all_resolution_models()
        return [
            result['resolution_model_name']
            for result in query_result
        ]

    def _fetch_all_ros_interfaces(self) -> List[dict]:
        """
        Fetch all ROSInterface names.

        :return: fetch query result
        """
        query = """
            match
                $interface isa ROSInterface;
            fetch {
                "interface_name": $interface.interface_name
            };
        """
        return self._fetch(query)

    def _get_all_ros_interfaces(self) -> List[str]:
        """
        Get all ROSInterface names.

        :return: list of ROSInterface names
        """
        query_result = self._fetch_all_ros_interfaces()
        return [result['interface_name'] for result in query_result]

    def _get_in_effect_requirement_names(self) -> List[str]:
        """
        Get requirement names that have in_effect true.

        Uses a structural query only — does NOT call any schema function,
        so the JIT cold state is preserved for subsequent timing.

        :return: list of requirement_name strings with in_effect true
        """
        rows = self._fetch("""
            match
                $req isa relaxed_requirement,
                    has requirement_name $name,
                    has in_effect true;
            fetch { "name": $name };
        """)
        return [row['name'] for row in rows if row.get('name') is not None]

    def fetch_all_tactic_rules(self) -> List[dict]:
        """
        Fetch all tactic rules names.

        :return: fetch query result
        """
        query = """
            match
                $tactic_rule isa tactic_rule;
            fetch {
                "rule_name": $tactic_rule.rule_name
            };
        """
        return self._fetch(query)

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
                $fa isa feature_adaptation, links ($feature);
                $feature isa Feature;
                (variant: $feature, resolution_action: $ra)
                    isa variant_resolution;
                $ra isa resolution_action;
                $ra links (node: $node);
                $node isa ROSNode, has node_name '{node_name}',
                    has namespace '{namespace}';
            select $node; reduce $c = count;
        """
        try:
            return (self._aggregate(query) or 0) > 0
        except TypeDBQueryError:
            logger.error(
                'Failed to evaluate tactic-node impact '
                '(tactic_name=%s, node_name=%s, namespace=%s).',
                tactic_name,
                node_name,
                namespace)
            raise

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
                let $neighbour in neighbours($node);
            fetch {{
                "node_name": $neighbour.node_name,
                "namespace": $neighbour.namespace
            }};
        """
        return self._fetch(query)

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
                $node isa ROSNode,
                    has node_name '{node_name}',
                    has namespace '{namespace}';
                let $connected in connected_nodes($node);
            fetch {{
                "node_name": $connected.node_name,
                "namespace": $connected.namespace
            }};
        """
        return self._fetch(query)

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
        connected_nodes = self.fetch_connected_nodes(node_name, namespace)
        connected_nodes.append({
            'node_name': node_name,
            'namespace': namespace,
        })
        return node_query_to_node_dict(connected_nodes)

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
                $interface isa ROSInterface,
                    has interface_name '{interface_name}';
                $rm isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                let $tr in applicable_tactics($interface, $rm);
            fetch {{
                "rule_name": $tr.rule_name
            }};
        """
        return self._fetch(query)

    def fetch_interface_hosts(self, interface_name: str) -> List[dict]:
        """
        Fetch the host nodes for a ROS interface supported by tactic applicability.

        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface, has interface_name '{interface_name}';
                {{
                    $interface isa ActionServer;
                    (node: $host, server: $interface) isa has_action;
                }} or {{
                    $interface isa ServiceServer;
                    (node: $host, server: $interface) isa has_service;
                }} or {{
                    $interface isa Publisher;
                    (node: $host, publisher: $interface) isa has_topic;
                }};
            fetch {{
                "node_name": $host.node_name,
                "namespace": $host.namespace
            }};
        """
        return self._fetch(query)

    def fetch_resolution_model_tactic_rule_targets(
            self, resolution_model: str) -> List[dict]:
        """
        Fetch tactic rule target nodes for a resolution model.

        :param resolution_model: name of the resolution model
        :return: fetch query result
        """
        query = f"""
            match
                $resolution_model isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                $resolution_model links (tactic: $rm_tactic, variant_resolution: $vr);
                $tactic_rule isa tactic_rule, links (tactic: $rm_tactic, consequent: $fa);
                {{
                    $fa links (activation: $feat);
                }} or {{
                    $fa links (deactivation: $feat);
                }};
                $vr links (variant: $feat, resolution_action: $ra);
                $ra links (node: $target);
            fetch {{
                "rule_name": $tactic_rule.rule_name,
                "node_name": $target.node_name,
                "namespace": $target.namespace
            }};
        """
        return self._fetch(query)

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
                $req isa relaxed_requirement,
                    has requirement_name '{requirement_name}';
                $req links (system: $system);
                let $fulfillment = relaxed_requirement_fulfillment($req);
            fetch {{ "fulfillment": $fulfillment }};
        """
        return self._fetch(query)

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
                let $fulfillment = relaxed_requirement_fulfillment($req);
            fetch {
                "requirement_name": $req.requirement_name,
                "fulfillment": $fulfillment
            };
        """
        return self._fetch(query)

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
            update
                $req has in_effect {in_effect_tql_type};
        """
        return self._insert(query)

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
        return self._fetch(query)

    def get_requirement_in_effect(self, requirement_name: str) -> bool:
        """
        Get relaxed requirement in effect attribute.

        :param requirement_name: requirement name
        :return: boolean indicating if the requirement is in effect
        """
        try:
            query_result = self.fetch_requirement_in_effect(requirement_name)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch requirement in_effect status '
                '(requirement_name=%s).',
                requirement_name)
            raise
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
            fetch {{
                "value": (
                    match
                        try {{
                            $measurement_val isa ValueSingleton, has data_value $value;
                        }};
                    return first $value;
                ),
                "array_values": [
                    match
                        $measurement_val isa ValueArray;
                        (array: $measurement_val, array_value: $v) isa at_index,
                            has index $index;
                        $v isa ValueSingleton;
                        sort $index;
                    fetch {{
                        "value": $v.data_value
                    }};
                ]
            }};
        """
        return self._fetch(query)

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
            fetch {{
                "value": (
                    match
                        try {{
                            $measurement_val isa ValueSingleton, has data_value $value;
                        }};
                    return first $value;
                ),
                "array_values": [
                    match
                        $measurement_val isa ValueArray;
                        (array: $measurement_val, array_value: $v) isa at_index,
                            has index $index;
                        $v isa ValueSingleton;
                        sort $index;
                    fetch {{
                        "value": $v.data_value
                    }};
                ]
            }};
        """
        return self._fetch(query)

    def get_latest_measurement(self, measure_name: str) -> Union[float, int, str, bool, List]:
        """
        Get latest measurement of a measure.

        :param measure_name: measure name
        :return: latest measurement
        """
        query_result = self.fetch_latest_measurement(measure_name)

        if len(query_result) == 0:
            return float('nan')

        value = query_result[0].get('value', None)
        if value is not None:
            return value

        array_values = query_result[0].get('array_values', None)
        if array_values is not None:
            return [value['value']
                    for value in array_values]

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
                true == tactic_rule_valid($tr);
            fetch {{ "rule_name": $tr.rule_name }};
        """
        return self._fetch(query)

    def get_tactic_rule_valid(self, tactic_rule: str) -> bool:
        """
        Get whether a tactic_rule is valid.

        :param tactic_rule: measure name
        :return: true or false
        """
        try:
            query_result = self.fetch_tactic_rule_valid(tactic_rule)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch tactic rule validity (tactic_rule=%s).',
                tactic_rule)
            raise
        return len(query_result) > 0

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
        try:
            query_result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch feature selectable status (feature_name=%s).',
                feature_name)
            raise
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
        try:
            query_result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch node running status (node_name=%s).',
                node_name)
            raise
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
                $ra isa set_nodes_parameters;
                $ra links (node: $node, parameter: $parameter);
                $node isa ROSNode, has node_name '{node_name}';
                $parameter isa Parameter, has parameter_name '{parameter_name}';
                true == set_nodes_parameters_feasible($ra);
            fetch {{ "node_name": $node.node_name }};
        """
        try:
            query_result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch set_nodes_parameters feasibility '
                '(node_name=%s, parameter_name=%s).',
                node_name,
                parameter_name)
            raise
        return len(query_result) > 0

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
                $ra isa set_lifecycle_state, has lifecycle_state '{lifecycle_state}';
                $ra links (node: $node);
                $node isa LifeCycleNode, has node_name '{node_name}';
                true == set_lifecycle_state_feasible($ra);
            fetch {{ "node_name": $node.node_name }};
        """
        try:
            query_result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to fetch set_lifecycle_state feasibility '
                '(node_name=%s, lifecycle_state=%s).',
                node_name,
                lifecycle_state)
            raise
        return len(query_result) > 0

    def fetch_measures_interfaces(
            self, include_qos: bool = True) -> List[dict]:
        """
        Fetch measures and their source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        if include_qos:
            query = """
            match
                $measure isa Measure;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface,
                    has measurement_function_name $fname,
                    has measurement_function_lib $flib,
                    has measurement_function_args $fargs;
                $source isa! Publisher;
                (interface: $source, qos: $qos) isa has_qos;
                $qos isa QoSProfile;
            fetch {
                "measure_name": $measure.measure_name,
                "measurement_function_name": $fname,
                "measurement_function_lib": $flib,
                "measurement_function_args": $fargs,
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
                $measure isa Measure;
                $measurement_interface (measure: $measure, source: $source)
                    isa measurement_interface,
                    has measurement_function_name $fname,
                    has measurement_function_lib $flib,
                    has measurement_function_args $fargs;
            fetch {
                "measure_name": $measure.measure_name,
                "measurement_function_name": $fname,
                "measurement_function_lib": $flib,
                "measurement_function_args": $fargs,
                "interface_name": $source.interface_name,
                "interface_type": $source.interface_type
            };
            """
        return self._fetch(query)

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
                (measure: $measure) isa measurement,
                    has latest $latest;
                $latest == true;
            delete $latest;
        """
        self._delete(delete_query)

        time = convert_py_type_to_query_type(datetime.now())
        query = f"""
            match
                $measure isa Measure, has measure_name '{measure_name}';
            insert
                {value_query}
                    (measure: $measure, measurement_value: {variable_name}) isa measurement,
                    has measurement_time {time},
                    has latest true;
        """
        return self._insert(query)

    def fetch_tactic_rule_impacts_fulfillment(self, impacted_name: str, tactic_rule_name: str):
        """
        Fetch hypothetical fulfillment of an expression given a tactic rule.

        :param impacted_name: expression name
        :param rule_name: tactic rule name
        :return: fetch query result
        """
        query = f"""
            match
                $impacted isa expression,
                    has expression_name '{impacted_name}';
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                let $fulfillment = tactic_rule_impacts_any_expression_fulfillment($tr, $impacted);
            fetch {{ "fulfillment": $fulfillment }};
        """
        return self._fetch(query)

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
                let $fulfillment = tactic_rule_impacts_requirement_fulfillment($tr, $impacted);
            fetch {{ "fulfillment": $fulfillment }};
        """
        query_result = self._fetch(query)
        return query_result

    def get_tactic_rule_impacts_requirement(self, impacted_name: str, rule_name: str) -> float:
        """
        Get hypothetical fulfillment of a requirement given a tactic rule.

        :param impacted_name: requirement name
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
                $tr (effect: $eff) isa tactic_rule, has rule_name '{tactic_rule}';
                $meas_q isa Measure, has measure_name '{measure_name}';
                $eff isa relative_effect;
                $eff links (measure: $meas_q);
                let $v = resulting_effect_value($eff);
            fetch {{ "resulting_effect_value": $v }};
        """
        return self._fetch(query)

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
                $e isa expression,
                    has expression_name '{expression_name}';
                let $membership_degree = fuzzy_membership_degree($e);
            fetch {{ "membership_degree": $membership_degree }};
        """
        try:
            result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to evaluate fetch_fuzzy_membership_degree '
                '(expression_name=%s).',
                expression_name)
            raise
        return result

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
                    has expression_name '{expression_name}';
                let $fulfillment = relaxed_expression_fulfillment($relaxed_expression);
            fetch {{ "fulfillment": $fulfillment }};
        """
        return self._fetch(query)

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

        query = f"""
            match
                $interface isa ROSInterface,
                    has interface_name '{action_name}';
                $rm isa resolution_model;
                let $tr in applicable_tactics($interface, $rm);
                $req isa relaxed_requirement, has in_effect true;
                let $fulfillment =
                    tactic_rule_impacts_requirement_fulfillment($tr, $req);
            fetch {{
                "rule_name": $tr.rule_name,
                "requirement_name": $req.requirement_name,
                "fulfillment": $fulfillment
            }};
        """
        result = self._fetch(query)
        return self._dedupe_requirement_impact_rows(result)

    def fetch_potential_requirements_fulfillment_for_resolution_model(
            self,
            action_name: str,
            resolution_model: str
            ) -> List[dict]:
        """
        Fetch potential relaxed requirement fulfillment using a fixed resolution model.

        :param action_name: ROS interface/action name
        :param resolution_model: resolution model name
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface,
                    has interface_name '{action_name}';
                $rm isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                let $tr in applicable_tactics($interface, $rm);
                $req isa relaxed_requirement, has in_effect true;
                let $fulfillment =
                    tactic_rule_impacts_requirement_fulfillment($tr, $req);
            fetch {{
                "rule_name": $tr.rule_name,
                "requirement_name": $req.requirement_name,
                "fulfillment": $fulfillment
            }};
        """
        result = self._fetch(query)
        return self._dedupe_requirement_impact_rows(result)

    @staticmethod
    def _dedupe_requirement_impact_rows(query_result: List[dict]) -> List[dict]:
        """Deduplicate requirement impact rows while keeping deterministic order."""
        seen = set()
        deduped = []
        for result in query_result:
            key = (
                result['rule_name'],
                result['requirement_name'],
                result['fulfillment'],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)
        deduped.sort(
            key=lambda item: (
                item['rule_name'],
                item['requirement_name'],
            ))
        return deduped

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
            fetch {
                "requirement_name": $req.requirement_name
            };
        """
        return self._fetch(query)

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
            fetch {
                "expression_name": $expr.expression_name
            };
        """
        return self._fetch(query)

    def get_all_expressions(self):
        """
        Get all expressions names.

        :return: list with expressions names
        """
        query_result = self.fetch_all_expressions()
        return [result['expression_name']
                for result in query_result if result.get('expression_name') is not None]

    def get_expression_satisfied(self, expression_name: str) -> bool:
        """
        Return whether the logical expression with the given name is satisfied.

        Uses the TypeDB 3 schema function ``expression_valid`` to compute
        satisfaction dynamically from the expression graph.

        :param expression_name: Unique ``expression_name`` attribute of the expression.
        :return: ``True`` if the expression evaluates as satisfied, ``False`` otherwise.
        :raises TypeDBQueryError: If the underlying TypeDB query fails.
        """
        query = f"""
            match
                $e isa logical_expression,
                    has expression_name '{expression_name}';
                true == expression_valid($e);
            fetch {{ "satisfied": true }};
        """
        try:
            result = self._fetch(query)
        except TypeDBQueryError:
            logger.error(
                'Failed to evaluate expression_valid '
                '(expression_name=%s).',
                expression_name)
            raise
        return len(result) > 0
