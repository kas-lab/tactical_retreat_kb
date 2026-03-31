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

def fetch_tactic_rule_dependency_fulfillment(
        self, expression_name, tactic_rule_name):
    query = f"""
            match
                $expr isa expression,
                    has expression_name '{expression_name}';
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                $tr_dependency (dependent: $expr, tactic_rule: $tr) isa tactic_rule_dependency;
            fetch
                $tr_dependency: fulfillment;
        """
    query_result = self.fetch_database(query)
    return query_result

def fetch_next_state_name(self):
    query = """
            match
                (current_state: $s, next_state:$s2) isa state_sequence;
            fetch
                $s2: state_name;
        """
    query_result = self.fetch_database(query)
    return query_result

#Given an imaginary choice in tactic_rule, we dream up a new state and action that will result.
def dream(self, tactic_rule_name):
    query = f"""
            match
                $tr isa tactic_rule,
                    has rule_name '{tactic_rule_name}';
                (action: $tr, current_state: $s, next_state:$s2) isa state_sequence;
                $requirement isa relaxed_requirement,
                    has in_effect true;
                $tactic_impact (tactic_rule: $tr, impacted: $requirement) isa tactic_rule_impacts_requirement;
            fetch
                $s2: state_name;
                $tactic_impact: fulfillment; 
    """
    query_result = self.fetch_database(query)
    return query_result

@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'test_states',
        ['schemas/data_structure/data_structure.tql',
            'schemas/context_model/context_model.tql',
            'schemas/logical_expressions/logical_expression.tql',
            'schemas/logical_expressions/fuzzy_expression.tql',
            'schemas/ros_model/ros_model.tql',
            'schemas/feature_model/feature_model.tql',
            'schemas/relaxed/relaxed_model.tql',
            'schemas/tactics_model/tactics_model.tql',
            'schemas/discover_hypothetical_req_fulfillment/'
            'discover_hypothetical_req_fulfillment.tql',
            'schemas/discover_tactics_model/discover_tactics_model.tql',
			'schemas/states/states.tql'],
        ['test/data/test_states.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    yield kb_interface
    # kb_interface.delete_database()


def test_current_state(kb_interface):
    def fetch_state_current_by_name(self, state_name):
        query = f"""
            match
                $s isa state,
                    has state_name '{state_name}';
            fetch
                $s: current;
        """
        query_result = self.fetch_database(query)
        return query_result

    def fetch_state_current(self):
        query = """
            match
                $s isa state,
                    has current true;
            fetch
                $s: state_name;
        """
        query_result = self.fetch_database(query)
        return query_result

    kb_interface.register_method('fetch_state_current_by_name', fetch_state_current_by_name)
    kb_interface.register_method(
        'fetch_tactic_rule_dependency_fulfillment',
        fetch_tactic_rule_dependency_fulfillment)

    current_state = kb_interface.fetch_state_current_by_name('current_state')

    assert len(current_state[0]['s']['current']) == 1
    assert current_state[0]['s']['current'][0]['value'] is True

    not_current_state = kb_interface.fetch_state_current_by_name('not_current_state')

    assert len(not_current_state[0]['s']['current']) == 1
    assert not_current_state[0]['s']['current'][0]['value'] is False

    kb_interface.register_method('fetch_state_current', fetch_state_current)
    current_state = kb_interface.fetch_state_current()

    assert len(current_state[0]['s']['state_name']) == 1
    assert current_state[0]['s']['state_name'][0]['value'] == "current_state" or current_state[1]['s']['state_name'][0]['value'] == "current_state"

    alt_state_1 = kb_interface.fetch_state_current_by_name('alt_state_1')
    alt_state_2 = kb_interface.fetch_state_current_by_name('alt_state_2')
    alt_state_3 = kb_interface.fetch_state_current_by_name('alt_state_3')

    assert len(alt_state_1[0]['s']['current']) == 1
    assert len(alt_state_2[0]['s']['current']) == 1
    assert len(alt_state_3[0]['s']['current']) == 1
    assert alt_state_1[0]['s']['current'][0]['value'] is False
    assert alt_state_2[0]['s']['current'][0]['value'] is False
    assert alt_state_3[0]['s']['current'][0]['value'] is True

    impact_part_of_precondition = kb_interface.fetch_tactic_rule_dependency_fulfillment(
        'measure_less_1_0', 'effective_rule')
    
    assert len(impact_part_of_precondition) == 1
    assert impact_part_of_precondition[0]['tr_dependency']['fulfillment'][0]['value'] == 1.0

    impact_state_1_precondition = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'state_1_precondition', 'effective_rule')
    assert len(impact_state_1_precondition) == 1
    assert impact_state_1_precondition[0]['fulfillment']['value'] == pytest.approx(
        1.0)

    impact_state_2_precondition = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'state_2_precondition', 'effective_rule')

    assert len(impact_state_2_precondition) == 1
    assert impact_state_2_precondition[0]['fulfillment']['value'] == pytest.approx(
        0.0)

    impact_state_3_precondition = kb_interface.fetch_tactic_rule_impacts_fulfillment(
        'state_3_precondition', 'effective_rule')
    
    assert len(impact_state_3_precondition) == 1
    assert impact_state_3_precondition[0]['fulfillment']['value'] == pytest.approx(
        0.0)
    
    kb_interface.register_method(
        'fetch_next_state_name',
        fetch_next_state_name
    )
    x = kb_interface.fetch_next_state_name()
    assert len(x[0]['s2']['state_name']) == 1
    assert x[0]['s2']['state_name'][0]['value'] == "alt_state_1"

    req_ful = kb_interface.fetch_in_effect_requirement_fulfillment()

    kb_interface.register_method('dream',dream)

    dream_result = kb_interface.dream("effective_rule")


    assert len(dream_result[0]['s2']['state_name']) == 1
    assert dream_result[0]['s2']['state_name'][0]['value'] == "alt_state_1"

    assert len(dream_result[0]['tactic_impact']['fulfillment']) == 1

    assert dream_result[0]['tactic_impact']['fulfillment'][0]['value'] > req_ful[0]['req']['fulfillment'][0]['value']
    # assert x[0]['s2']['state_name'][0]['value'] == "alt_state_1"
    