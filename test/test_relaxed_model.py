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


@pytest.fixture
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_model_interface',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/relaxed/relaxed_model.tql'],
        ['schemas/relaxed/relaxed_mirte_example.tql',
            'schemas/relaxed/relaxed_paper_example.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    return kb_interface


def test_get_requirement_fulfillment(kb_interface):
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'R1.1 Velocity')
    assert fulfillment == pytest.approx(0.92442)
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'r_velocity_until_after_true')
    assert fulfillment == 1.0
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'r_velocity_until_after_false')
    assert fulfillment == pytest.approx(0.92442)
