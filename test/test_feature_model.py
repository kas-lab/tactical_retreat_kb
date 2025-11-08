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


@pytest.fixture(scope="module")
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_feature_model',
        ['typedb/data_structure/data_structure.tql',
            'typedb/context_model/context_model.tql',
            'typedb/ros_model/ros_model.tql',
            'typedb/tactics_model/tactics_model.tql',
            'typedb/feature_model/feature_model.tql'],
        ['test/data/test_feature_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()

def test_feature_selectable(kb_interface):
    assert kb_interface.is_feature_selectable('f_alternative_child_1') is False
    assert kb_interface.is_feature_selectable('f_alternative_child_2') is False
    assert kb_interface.is_feature_selectable('f_alternative_child_3') is True

    assert kb_interface.is_feature_selectable('f_or_group_child_1') is True
    assert kb_interface.is_feature_selectable('f_or_group_child_2') is True
    assert kb_interface.is_feature_selectable('f_or_group_child_3') is True

    assert kb_interface.is_feature_selectable('f_req_constrained_1') is True
    assert kb_interface.is_feature_selectable('f_req_constrained_2') is False
    assert kb_interface.is_feature_selectable('f_req_constrained_3') is True
    assert kb_interface.is_feature_selectable('f_req_constrained_4') is False
    assert kb_interface.is_feature_selectable('f_req_constrained_5') is False

    assert kb_interface.is_feature_selectable('f_excl_constrained_1') is False
    assert kb_interface.is_feature_selectable('f_excl_constrained_2') is True
    assert kb_interface.is_feature_selectable('f_excl_constrained_3') is False
    assert kb_interface.is_feature_selectable('f_excl_constrained_4') is True
    assert kb_interface.is_feature_selectable('f_excl_constrained_5') is False