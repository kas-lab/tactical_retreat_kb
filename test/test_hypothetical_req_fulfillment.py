# Copyright 2025 KAS Lab
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
        'test_hypothetical_req_fulfillment',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/relaxed/relaxed_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/tactics_model/discover_hypothetical_req_fulfillment.tql'],
        ['schemas/ros_model/ros_model_example.tql',
            'schemas/tactics_model/tactics_example.tql',
            'schemas/relaxed/relaxed_mirte_example.tql',
            'test/data/test_tactics_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_tactic_impacts_requirement(kb_interface):
    requirements = kb_interface.get_tactic_impacts_requirement('MIN')
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('MED')
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('MAX')
    assert 'R1.2 Movement Power' in requirements

    requirements = kb_interface.get_tactic_impacts_requirement('tr_variant_resolution_feasible')
    assert len(requirements) == 0
