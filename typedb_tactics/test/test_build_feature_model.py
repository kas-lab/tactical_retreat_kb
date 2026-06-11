# Copyright 2026 KAS lab
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

from typedb_tactics.feature_model import FeatureModel
from typedb_tactics.feature_model import ReconfigurationStep
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_build_feature_model',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/feature_model/feature_model_logical_expression.tql'],
        ['test/data/test_feature_model.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
    yield kb_interface
    kb_interface.delete_database()


@pytest.fixture(scope='module')
def feature_model(kb_interface):
    """Build and return the FeatureModel once for all tests in this module."""
    return kb_interface.build_feature_model()


def test_build_feature_model_returns_feature_model(feature_model):
    assert isinstance(feature_model, FeatureModel)


def test_feature_model_contains_all_features(feature_model):
    expected = {
        'feature_parent_alternative',
        'f_alternative_child_1', 'f_alternative_child_2', 'f_alternative_child_3',
        'feature_parent_or_group',
        'f_or_group_child_1', 'f_or_group_child_2', 'f_or_group_child_3',
        'f_selected_1', 'f_selected_2',
        'f_not_selected_1', 'f_not_selected_2',
        'f_req_constrained_1', 'f_req_constrained_2',
        'f_excl_constrained_1', 'f_excl_constrained_2',
        'fm_and_parent', 'fm_and_c1', 'fm_and_c2',
    }
    assert expected.issubset(feature_model.features)


def test_feature_model_mandatory(feature_model):
    assert 'feature_parent_alternative' in feature_model.mandatory
    assert 'feature_parent_or_group' in feature_model.mandatory
    assert 'fm_and_parent' in feature_model.mandatory
    assert 'fm_and_c1' in feature_model.mandatory
    assert 'f_alternative_child_1' not in feature_model.mandatory


def test_feature_model_hierarchy_children(feature_model):
    assert feature_model.hierarchy_children['fm_and_parent'] == frozenset(
        {'fm_and_c1', 'fm_and_c2'})
    assert 'feature_parent_alternative' not in feature_model.hierarchy_children
    assert 'feature_parent_or_group' not in feature_model.hierarchy_children


def test_feature_model_alternative_children(feature_model):
    assert feature_model.alternative_children['feature_parent_alternative'] == frozenset(
        {'f_alternative_child_1', 'f_alternative_child_2', 'f_alternative_child_3'})
    assert 'fm_and_parent' not in feature_model.alternative_children
    assert 'feature_parent_or_group' not in feature_model.alternative_children


def test_feature_model_or_group_children(feature_model):
    assert feature_model.or_group_children['feature_parent_or_group'] == frozenset(
        {'f_or_group_child_1', 'f_or_group_child_2', 'f_or_group_child_3'})
    assert 'fm_and_parent' not in feature_model.or_group_children
    assert 'feature_parent_alternative' not in feature_model.or_group_children


def test_feature_model_requires(feature_model):
    assert ('f_req_constrained_1', 'f_selected_1') in feature_model.requires
    assert ('f_req_constrained_2', 'f_not_selected_1') in feature_model.requires


def test_feature_model_excludes_bidirectional(feature_model):
    assert ('f_excl_constrained_1', 'f_selected_1') in feature_model.excludes
    assert ('f_selected_1', 'f_excl_constrained_1') in feature_model.excludes


def test_feature_model_selected(feature_model):
    assert feature_model.selected['f_alternative_child_3'] is True
    assert feature_model.selected['f_alternative_child_1'] is False
    assert feature_model.selected['f_selected_1'] is True
    assert feature_model.selected['f_not_selected_1'] is False
    assert feature_model.selected.get('f_not_selected_2', False) is False


def test_plan_reconfiguration_xor_switch(feature_model):
    # Activate an unselected XOR child — the currently selected sibling is deactivated first.
    plan = feature_model.get_feature_reconfiguration_plan(['f_alternative_child_1'], [])
    assert plan == [
        ReconfigurationStep('f_alternative_child_3', 'deactivate', 1),
        ReconfigurationStep('f_alternative_child_1', 'activate', 2),
    ]


def test_plan_reconfiguration_with_explicit_deactivation(feature_model):
    # Activate XOR child and explicitly deactivate another selected feature.
    # f_req_constrained_* features are not selected in the test data, so they
    # do not appear in the plan even though they require f_selected_1.
    plan = feature_model.get_feature_reconfiguration_plan(
        ['f_alternative_child_1'], ['f_selected_1'])
    assert plan == [
        ReconfigurationStep('f_alternative_child_3', 'deactivate', 1),
        ReconfigurationStep('f_selected_1', 'deactivate', 1),
        ReconfigurationStep('f_alternative_child_1', 'activate', 2),
    ]


def test_plan_reconfiguration_requires_propagation(fresh_feature_model):
    # Simulate a state where f_req_constrained_1 is selected (it requires f_selected_1).
    # Deactivating f_selected_1 must automatically include f_req_constrained_1.
    fresh_feature_model.refresh_selected([
        {'f': {'feature_name': [{'value': 'f_selected_1'}], 'selected': [{'value': True}]}},
        {'f': {'feature_name': [{'value': 'f_req_constrained_1'}], 'selected': [{'value': True}]}},
    ])
    plan = fresh_feature_model.get_feature_reconfiguration_plan([], ['f_selected_1'])
    deactivated = {s.feature_name for s in plan if s.action == 'deactivate'}
    assert 'f_selected_1' in deactivated
    assert 'f_req_constrained_1' in deactivated


@pytest.fixture
def fresh_feature_model(kb_interface):
    """Build a fresh FeatureModel for tests that mutate selected state."""
    return kb_interface.build_feature_model()


def test_refresh_selected_updates_values(fresh_feature_model):
    fake_results = [
        {'f': {'feature_name': [{'value': 'f_selected_1'}], 'selected': [{'value': False}]}},
        {'f': {'feature_name': [{'value': 'f_not_selected_1'}], 'selected': [{'value': True}]}},
        {'f': {'feature_name': [{'value': 'f_not_selected_2'}]}},
    ]
    fresh_feature_model.refresh_selected(fake_results)
    assert fresh_feature_model.selected['f_selected_1'] is False
    assert fresh_feature_model.selected['f_not_selected_1'] is True
    assert fresh_feature_model.selected['f_not_selected_2'] is False


def test_refresh_selected_replaces_entire_dict(fresh_feature_model):
    fake_results = [
        {'f': {'feature_name': [{'value': 'f_selected_1'}], 'selected': [{'value': True}]}},
    ]
    fresh_feature_model.refresh_selected(fake_results)
    assert set(fresh_feature_model.selected.keys()) == {'f_selected_1'}


def test_refresh_feature_model_selected(kb_interface, fresh_feature_model):
    fresh_feature_model.selected['f_selected_1'] = False
    fresh_feature_model.selected['f_not_selected_1'] = True
    kb_interface.refresh_feature_model_selected(fresh_feature_model)
    assert fresh_feature_model.selected['f_selected_1'] is True
    assert fresh_feature_model.selected['f_not_selected_1'] is False
