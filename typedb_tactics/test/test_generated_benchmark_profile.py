# Copyright 2026 KAS Lab
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

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_generated_benchmark_profile',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/logical_expressions/fuzzy_expression.tql',
         'schemas/ros_model/ros_model.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/feature_model/feature_model_logical_expression.tql',
         'schemas/relaxed/relaxed_model.tql',
         'schemas/tactics_model/tactics_model.tql',
         'schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql',
         'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['scripts/generated.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
    yield kb_interface
    kb_interface.delete_database()


def test_generated_profile_potential_requirements_non_empty(kb_interface):
    impacts = kb_interface.get_potential_requirements_fulfillment(
        '/navigate_to_pose',
        resolution_model='rebet_frog')

    assert len(impacts) > 0
    for impact in impacts:
        assert impact.tactic_rule
        assert impact.requirement_name
        assert impact.fulfillment is not None
