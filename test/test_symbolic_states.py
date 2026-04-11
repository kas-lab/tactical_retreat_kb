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

from ros_typedb.typedb_interface import TypeDBInterface


def fetch_active_labels(self, scheme_name):
    query = f"""
        match
            $scheme (label: $label) isa symbolic_scheme,
                has symbolic_scheme_name "{scheme_name}";
            $label has symbolic_active true;
        fetch
            $label: symbolic_label_name;
    """
    return self.fetch_database(query)


def fetch_scheme_status(self, scheme_name):
    query = f"""
        match
            $scheme isa symbolic_scheme,
                has symbolic_scheme_name "{scheme_name}";
        fetch
            $scheme: exclusive_partition,
                undefined_state,
                ambiguous_state;
    """
    return self.fetch_database(query)


def fetch_median_value(self, label_name):
    query = f"""
        match
            $interval (label: $label) isa symbolic_interval_definition,
                has median_bound_value $median;
            $label has symbolic_label_name "{label_name}";
        fetch
            $interval: median_bound_value;
    """
    return self.fetch_database(query)


def fetch_current_system_state(self):
    query = """
        match
            $state isa system_state,
                has current_state true;
        fetch
            $state: state_name;
    """
    return self.fetch_database(query)


def fetch_system_states(self):
    query = """
        match
            $state isa system_state,
                has state_name $name;
        fetch
            $state: state_name;
    """
    return self.fetch_database(query)


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TypeDBInterface(
        'localhost:1729',
        'test_symbolic_states',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/states/symbolic_states.tql'],
        ['test/data/test_symbolic_states.tql'],
        force_database=True,
        force_data=True,
        infer=True,
        sort_fetch_results=True)
    kb_interface.register_method(
        'fetch_active_labels',
        fetch_active_labels)
    kb_interface.register_method(
        'fetch_scheme_status',
        fetch_scheme_status)
    kb_interface.register_method(
        'fetch_median_value',
        fetch_median_value)
    kb_interface.register_method(
        'fetch_current_system_state',
        fetch_current_system_state)
    kb_interface.register_method(
        'fetch_system_states',
        fetch_system_states)
    yield kb_interface
    kb_interface.delete_database()


def test_exclusive_partition_and_parallel_interpretations(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'low')],
        'symbolic_active')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'medium')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'high')],
        'symbolic_active')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'safe')],
        'symbolic_active')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'caution')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'unsafe')],
        'symbolic_active')[0] is False

    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'medium')],
        'symbolic_order')[0] == 2

    scheme_status = kb_interface.fetch_scheme_status('velocity-bands')
    assert len(scheme_status) == 1
    assert scheme_status[0]['scheme']['undefined_state'][0]['value'] is False
    assert scheme_status[0]['scheme']['ambiguous_state'][0]['value'] is False

    current_assignments = kb_interface.fetch_active_labels(
        'velocity-bands')
    assert len(current_assignments) == 1
    assert current_assignments[0]['label']['symbolic_label_name'][0]['value'] == (
        'medium')


def test_composite_symbolic_label(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'near')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'CompositeSymbolicLabel',
        [('symbolic_label_name', 'approach-medium')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'and_expression',
        [('expression_name', 'approach-medium-expr')],
        'expression_satisfied')[0] is True

    current_assignments = kb_interface.fetch_active_labels(
        'navigation-context')
    assert len(current_assignments) == 1
    assert current_assignments[0]['label']['symbolic_label_name'][0]['value'] == (
        'approach-medium')


def test_undefined_fallback(kb_interface):
    scheme_status = kb_interface.fetch_scheme_status('temperature-bands-gap')
    assert len(scheme_status) == 1
    assert scheme_status[0]['scheme']['undefined_state'][0]['value'] is True
    assert scheme_status[0]['scheme']['ambiguous_state'][0]['value'] is False

    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'cold')],
        'symbolic_active')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'warm')],
        'symbolic_active')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'hot')],
        'symbolic_active')[0] is False

    current_assignments = kb_interface.fetch_active_labels(
        'temperature-bands-gap')
    assert current_assignments == []


def test_ambiguous_state(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'overlap-low')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'overlap-medium')],
        'symbolic_active')[0] is True

    scheme_status = kb_interface.fetch_scheme_status('velocity-overlap')
    assert len(scheme_status) == 1
    assert scheme_status[0]['scheme']['undefined_state'][0]['value'] is False
    assert scheme_status[0]['scheme']['ambiguous_state'][0]['value'] is True


def test_current_system_state_and_state_space(kb_interface):
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'medium')],
        'symbolic_active')[0] is True
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'state-safe')],
        'symbolic_active')[0] is False
    assert kb_interface.fetch_attribute_from_thing(
        'AtomicSymbolicLabel',
        [('symbolic_label_name', 'state-unsafe')],
        'symbolic_active')[0] is True

    current_state = kb_interface.fetch_current_system_state()
    assert len(current_state) == 1
    assert current_state[0]['state']['state_name'][0]['value'] == 'medium-unsafe'

    all_states = kb_interface.fetch_system_states()
    assert sorted(
        state['state']['state_name'][0]['value'] for state in all_states) == [
            'high-safe',
            'high-unsafe',
            'low-safe',
            'low-unsafe',
            'medium-safe',
            'medium-unsafe']


def test_median_value_rules(kb_interface):
    # symbolic_double_interval_median_value:
    #   both bounds present → median = (lower + upper) / 2.0
    result = kb_interface.fetch_median_value('low')   # [0.0, 0.18)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.09)

    result = kb_interface.fetch_median_value('medium')   # [0.18, 0.26)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.22)

    # symbolic_double_interval_no_upper_bound_median_value:
    #   lower bound only → median = lower
    result = kb_interface.fetch_median_value('high')   # [0.26, ∞)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.26)

    # symbolic_double_interval_no_lower_bound_median_value:
    #   upper bound only → median = upper
    result = kb_interface.fetch_median_value('very-cold')   # (-∞, 0.0)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.0)

    # symbolic_integer_interval_median_value:
    #   both bounds present → median = (lower + upper) / 2.0
    result = kb_interface.fetch_median_value('count-low')   # [0, 10)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(5.0)

    # symbolic_integer_interval_no_upper_bound_median_value:
    #   lower bound only → median = lower
    result = kb_interface.fetch_median_value('count-high')   # [10, ∞)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(10.0)

    # symbolic_integer_interval_no_lower_bound_median_value:
    #   upper bound only → median = upper
    result = kb_interface.fetch_median_value('count-negative')   # (-∞, 0)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.0)
