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

import math

import pytest

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_states',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/feature_model/feature_model_logical_expression.tql',
            'schemas/tactics_model/tactics_model.tql',
			'schemas/states/states.tql'],
        ['test/data/test_states.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    # kb_interface.delete_database()


def test_current_state(kb_interface):
    def fetch_state_current(self, state_name):
        query = f"""
            match
                $s isa state,
                    has state_name '{state_name}';
            fetch
                $s: current;
        """
        query_result = self.fetch_database(query)
        return query_result

    kb_interface.register_method('fetch_state_current', fetch_state_current)

    current_state = kb_interface.fetch_state_current('current_state')

    assert len(current_state[0]['s']['current']) == 1
    assert current_state[0]['s']['current'][0]['value'] is True

    not_current_state = kb_interface.fetch_state_current('not_current_state')

    assert len(not_current_state[0]['s']['current']) == 1
    assert not_current_state[0]['s']['current'][0]['value'] is False