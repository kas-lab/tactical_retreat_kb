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
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/relaxed/relaxed_model.tql'],
        ['schemas/relaxed/relaxed_mirte_example.tql',
         'schemas/relaxed/relaxed_paper_example.tql',
         'test/data/test_relaxed_model.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    kb_interface.delete_database()


def test_get_requirement_fulfillment(kb_interface):
    fulfillment = kb_interface.get_relaxed_requirement_fulfillment(
        'Mirte', 'R1.1 Velocity')
    assert fulfillment == pytest.approx(0.92442)


def test_get_in_effect_requirement_fulfillment(kb_interface):
    req_fulfillment_array = kb_interface.get_in_effect_requirement_fulfillment()
    assert req_fulfillment_array[0]['requirement_name'] == 'R1.1 Velocity'
    assert req_fulfillment_array[0]['fulfillment'] == pytest.approx(0.92442)


def test_set_requirement_in_effect(kb_interface):
    assert kb_interface.get_requirement_in_effect('fake_req') is False
    kb_interface.set_requirement_in_effect('fake_req', True)
    assert kb_interface.get_requirement_in_effect('fake_req') is True
    kb_interface.set_requirement_in_effect('fake_req', False)
    assert kb_interface.get_requirement_in_effect('fake_req') is False


def test_fuzzy_ascend(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_ascend_sigmoid_expression') == pytest.approx(0.913378192)
    assert kb_interface.get_fuzzy_membership('fuzzy_ascend_exp_saturation_expression') == pytest.approx(0.834700912)
    assert kb_interface.get_fuzzy_membership('fuzzy_ascend_blf_expression') == pytest.approx(0.947368421)

def test_fuzzy_unimodal(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_unimodal_triangular_expression') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership('fuzzy_unimodal_gaussian_expression') == pytest.approx(0.931085511)

def test_fuzzy_decay(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_decay_exp_expression') == pytest.approx(0.900009528)
    assert kb_interface.get_fuzzy_membership('fuzzy_decay_rational_expression') == pytest.approx(0.8)

def test_fuzzy_not(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_not_0') == pytest.approx(0.086621808)
    assert kb_interface.get_fuzzy_membership('fuzzy_not_1') == pytest.approx(0.2)

def test_fuzzy_or(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_or_0') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership('fuzzy_or_1') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership('fuzzy_or_2') == pytest.approx(0.947368421)
    assert kb_interface.get_fuzzy_membership('fuzzy_or_3') == pytest.approx(0.2)

def test_fuzzy_and(kb_interface):
    assert kb_interface.get_fuzzy_membership('fuzzy_and_0') == pytest.approx(0.931085511)
    assert kb_interface.get_fuzzy_membership('fuzzy_and_1') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership('fuzzy_and_2') == pytest.approx(0.8)
    assert kb_interface.get_fuzzy_membership('fuzzy_and_3') == pytest.approx(0.086621808)
    assert kb_interface.get_fuzzy_membership('fuzzy_and_4') == pytest.approx(0.92442)
    assert kb_interface.get_fuzzy_membership('fuzzy_and_5') == pytest.approx(0.2)

