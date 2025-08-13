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

class GetSubNodeResultDict(TypedDict):
    """TypedDict for get_subnodes method result."""

    namespace: str  #: node namspace
    node_name: str  #: node name

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
	
    def get_subnodes_raw(self, node_name: str, namespace: str = "") -> list[dict[str, MatchResultDict]]:
        """
        Get subnodes of a running node and returns it as a typedb fetch query result.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: list of dictionaries with the node_name and namespace of the subnodes
        """
        query = f"""
            match
                (node: $parent_node) isa runtime_node, has node_name '{node_name}', has namespace '{namespace}';
                (node:$parent_node, subnode: $subnode) isa subnode;
                $runtime_subnode (node: $subnode) isa runtime_node;
            fetch
                $runtime_subnode: node_name, namespace;
        """
        return self.fetch_database(query)
    
    def get_subnodes(self, node_name: str, namespace: str = "") -> List[GetSubNodeResultDict]:
        """
        Get the subnodes of a running node and returns it as a list of dicts.

        :param node_name: node name of the parent running node
        :param namespace: namespace of the parent running node
        :return: list of dictionaries with the node_name and namespace of the subnodes
        """
        query_result = self.get_subnodes_raw(node_name, namespace)

        subnodes = list()
        for result in query_result:
            runtime_subnode = result.get('runtime_subnode')
            if len(runtime_subnode['namespace']) > 1:
                logger.error('In get_subnodes: runtime node has more than 1 namespace')
                return subnodes
            if len(runtime_subnode['node_name']) > 1:
                logger.error('In get_subnodes: runtime node has more than 1 node_name')
                return subnodes
            subnodes.append({
                'namespace': runtime_subnode['namespace'][0]['value'],
                'node_name': runtime_subnode['node_name'][0]['value'],
                }
            )
        return subnodes