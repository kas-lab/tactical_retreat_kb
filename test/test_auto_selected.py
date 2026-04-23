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
        'test_auto_feature_selection',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['test/data/test_selected.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    # kb_interface.delete_database()


def test_selected(kb_interface):
    assert kb_interface.is_feature_selected('LOW_SPEED') is False
    assert kb_interface.is_feature_selected('MED_SPEED') is False
    assert kb_interface.is_feature_selected('HI_SPEED') is True


def test_selectable_already_selected(kb_interface):
    assert kb_interface.is_feature_selectable('LOW_SPEED') is True
    assert kb_interface.is_feature_selectable('MED_SPEED') is True
    assert kb_interface.is_feature_selectable('HI_SPEED') is False


def test_update_selected(kb_interface):
    kb_interface.update_feature_selected_by_param_value('LOW_SPEED')
    assert kb_interface.is_feature_selected('LOW_SPEED') is True
    assert kb_interface.is_feature_selected('MED_SPEED') is False
    assert kb_interface.is_feature_selected('HI_SPEED') is False
