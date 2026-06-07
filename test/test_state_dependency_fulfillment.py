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

# ---------------------------------------------------------------------------
# Shared fetch helpers
# ---------------------------------------------------------------------------


def fetch_fulfillment(self, expression_name, state_name):
    query = f"""
        match
            $sd (dependent: $expression, system_state: $state) isa state_dependency;
            $expression has expression_name "{expression_name}";
            $state has state_name "{state_name}";
        fetch
            $sd: fulfillment;
    """
    return self.fetch_database(query)


def fetch_state_dependency_count(self, expression_name):
    query = f"""
        match
            $sd (dependent: $expression) isa state_dependency;
            $expression has expression_name "{expression_name}";
        fetch
            $sd: fulfillment;
    """
    return self.fetch_database(query)


def fetch_comparison_state_dependency_count(self, expression_name):
    query = f"""
        match
            $sd (dependent: $expression) isa comparison_state_dependency;
            $expression has expression_name "{expression_name}";
        fetch
            $sd: fulfillment;
    """
    return self.fetch_database(query)


def fetch_lhs_interval_operand(self, expression_name, state_name):
    query = f"""
        match
            $sd (dependent: $expression, system_state: $state) isa state_dependency;
            $expression has expression_name "{expression_name}";
            $state has state_name "{state_name}";
            $tag (sd_dependency: $sd, lhs_interval: $interval) isa sd_lhs_interval_operand;
            $interval has median_bound_value $median;
        fetch
            $interval: median_bound_value;
    """
    return self.fetch_database(query)


def fetch_rhs_double_operand(self, expression_name, state_name):
    query = f"""
        match
            $sd (dependent: $expression, system_state: $state) isa state_dependency;
            $expression has expression_name "{expression_name}";
            $state has state_name "{state_name}";
            $tag (sd_dependency: $sd, rhs_double: $val) isa sd_rhs_double_operand;
        fetch
            $val: double_value;
    """
    return self.fetch_database(query)


def fetch_req_fulfillment(self, requirement_name, state_name):
    query = f"""
        match
            $sd (dependent: $req, system_state: $state) isa state_dependency;
            $req has requirement_name "{requirement_name}";
            $state has state_name "{state_name}";
        fetch
            $sd: fulfillment;
    """
    return self.fetch_database(query)


def fetch_rhs_measure_without_interval(self, expression_name, state_name):
    query = f"""
        match
            $sd (dependent: $expression, system_state: $state) isa state_dependency;
            $expression has expression_name "{expression_name}";
            $state has state_name "{state_name}";
            (sd_dependency: $sd, rhs_measure: $m) isa sd_rhs_measure_without_interval;
            $m has measure_name $name;
        fetch
            $m: measure_name;
    """
    return self.fetch_database(query)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

STATE = 'sd-fast-near'


@pytest.fixture(scope='module')
def kb_interface():
    kb_interface = TypeDBInterface(
        'localhost:1729',
        'test_state_dependency_fulfillment',
        ['schemas/data_structure/data_structure.tql',
         'schemas/context_model/context_model.tql',
         'schemas/logical_expressions/logical_expression.tql',
         'schemas/ros_model/ros_model.tql',
         'schemas/feature_model/feature_model.tql',
         'schemas/tactics_model/tactics_model.tql',
         'schemas/logical_expressions/fuzzy_expression.tql',
         'schemas/relaxed/relaxed_model.tql',
         'schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql',
         'schemas/states/states.tql',
         'schemas/states/simple_state_dependency_fulfillment.tql'],
        ['test/data/test_simple_state_dependency_fulfillment.tql'],
        force_database=True,
        force_data=True,
        infer=True)
    kb_interface.register_method('fetch_fulfillment', fetch_fulfillment)
    kb_interface.register_method(
        'fetch_state_dependency_count', fetch_state_dependency_count)
    kb_interface.register_method(
        'fetch_comparison_state_dependency_count',
        fetch_comparison_state_dependency_count)
    kb_interface.register_method(
        'fetch_lhs_interval_operand', fetch_lhs_interval_operand)
    kb_interface.register_method(
        'fetch_rhs_double_operand', fetch_rhs_double_operand)
    kb_interface.register_method(
        'fetch_rhs_measure_without_interval', fetch_rhs_measure_without_interval)
    kb_interface.register_method('fetch_req_fulfillment', fetch_req_fulfillment)
    yield kb_interface
    kb_interface.delete_database()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fulfillment_of(kb, expression_name, state=STATE):
    result = kb.fetch_fulfillment(expression_name, state)
    assert len(result) == 1, (
        f"Expected exactly one state_dependency for '{expression_name}' in state "
        f"'{state}', got {len(result)}"
    )
    return result[0]['sd']['fulfillment'][0]['value']


# ---------------------------------------------------------------------------
# Test: state_dependency creation
# ---------------------------------------------------------------------------

def test_state_dependency_is_created_for_measure_in_state(kb_interface):
    # 'lt-1-iv' has lhs = velocity, which IS in the fast-near state via the
    # 'fast' label.  Exactly one state_dependency should exist.
    result = kb_interface.fetch_state_dependency_count('lt-1-iv')
    assert len(result) == 1


def test_comparison_leaf_seeds_concrete_comparison_state_dependency(kb_interface):
    result = kb_interface.fetch_comparison_state_dependency_count('lt-1-iv')
    assert len(result) == 1


def test_fuzzy_leaf_seeds_concrete_comparison_state_dependency(kb_interface):
    result = kb_interface.fetch_comparison_state_dependency_count(
        'fuzzy-unimodal-iv')
    assert len(result) == 1


def test_relaxed_fuzzy_leaf_seeds_concrete_comparison_state_dependency(
        kb_interface):
    result = kb_interface.fetch_comparison_state_dependency_count('acp-iv')
    assert len(result) == 1


def test_no_state_dependency_for_temperature_only_expression(kb_interface):
    result = kb_interface.fetch_state_dependency_count('temp-only')
    assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: operand classification
# ---------------------------------------------------------------------------

def test_lhs_interval_operand_tagged_with_median(kb_interface):
    result = kb_interface.fetch_lhs_interval_operand('lt-1-iv', STATE)
    assert len(result) == 1
    assert result[0]['interval']['median_bound_value'][0]['value'] == pytest.approx(0.25)


def test_rhs_literal_double_operand_tagged(kb_interface):
    result = kb_interface.fetch_rhs_double_operand('lt-1-iv', STATE)
    assert len(result) == 1
    assert result[0]['val']['double_value'][0]['value'] == pytest.approx(0.30)


def test_measure_without_interval_tagged_for_temperature(kb_interface):
    result = kb_interface.fetch_rhs_measure_without_interval('lt-1-im', STATE)
    assert len(result) == 1
    assert result[0]['m']['measure_name'][0]['value'] == 'sd-temperature'


def test_measure_without_interval_resolved_to_live_measurement(kb_interface):
    result = kb_interface.fetch_rhs_double_operand('lt-1-im', STATE)
    assert len(result) == 1
    assert result[0]['val']['double_value'][0]['value'] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Test: less_than fulfillment
# ---------------------------------------------------------------------------

def test_less_than_interval_double_true(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-1-iv') == pytest.approx(1.0)


def test_less_than_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-0-iv') == pytest.approx(0.0)


def test_less_than_double_interval_true(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-1-di') == pytest.approx(1.0)


def test_less_than_double_interval_false(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-0-di') == pytest.approx(0.0)


def test_less_than_interval_interval_true(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-1-ii') == pytest.approx(1.0)


def test_less_than_interval_measure_fallback_true(kb_interface):
    assert fulfillment_of(kb_interface, 'lt-1-im') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: less_than_equal fulfillment
# ---------------------------------------------------------------------------

def test_less_than_equal_interval_double_at_boundary(kb_interface):
    assert fulfillment_of(kb_interface, 'lte-1-iv') == pytest.approx(1.0)


def test_less_than_equal_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'lte-0-iv') == pytest.approx(0.0)


def test_less_than_equal_interval_interval_true(kb_interface):
    assert fulfillment_of(kb_interface, 'lte-1-ii') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: greater_than fulfillment
# ---------------------------------------------------------------------------

def test_greater_than_interval_double_true(kb_interface):
    assert fulfillment_of(kb_interface, 'gt-1-iv') == pytest.approx(1.0)


def test_greater_than_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'gt-0-iv') == pytest.approx(0.0)


def test_greater_than_interval_interval_false(kb_interface):
    assert fulfillment_of(kb_interface, 'gt-0-ii') == pytest.approx(0.0)


def test_greater_than_interval_measure_fallback_false(kb_interface):
    assert fulfillment_of(kb_interface, 'gt-0-im') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: greater_than_equal fulfillment
# ---------------------------------------------------------------------------

def test_greater_than_equal_interval_double_at_boundary(kb_interface):
    assert fulfillment_of(kb_interface, 'gte-1-iv') == pytest.approx(1.0)


def test_greater_than_equal_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'gte-0-iv') == pytest.approx(0.0)


def test_greater_than_equal_double_interval_at_boundary(kb_interface):
    assert fulfillment_of(kb_interface, 'gte-1-di') == pytest.approx(1.0)


def test_greater_than_equal_interval_interval_true(kb_interface):
    assert fulfillment_of(kb_interface, 'gte-1-ii') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: equal fulfillment
# ---------------------------------------------------------------------------

def test_equal_interval_double_true(kb_interface):
    assert fulfillment_of(kb_interface, 'eq-1-iv') == pytest.approx(1.0)


def test_equal_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'eq-0-iv') == pytest.approx(0.0)


def test_equal_interval_interval_false(kb_interface):
    assert fulfillment_of(kb_interface, 'eq-0-ii') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: not_equal fulfillment
# ---------------------------------------------------------------------------

def test_not_equal_interval_double_true(kb_interface):
    assert fulfillment_of(kb_interface, 'neq-1-iv') == pytest.approx(1.0)


def test_not_equal_interval_double_false(kb_interface):
    assert fulfillment_of(kb_interface, 'neq-0-iv') == pytest.approx(0.0)


def test_not_equal_interval_interval_true(kb_interface):
    assert fulfillment_of(kb_interface, 'neq-1-ii') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: fuzzy expression fulfillment
# TypeDB uses 2.71828 as the approximation of e.
# velocity median in sd-fast-near = 0.25
# ---------------------------------------------------------------------------

_E = 2.71828  # TypeDB's e constant, used to predict expected membership


def test_fuzzy_unimodal_at_center(kb_interface):
    assert fulfillment_of(kb_interface, 'fuzzy-unimodal-iv') == pytest.approx(1.0)


def test_fuzzy_ascend_interval(kb_interface):
    expected = 1.0 - _E ** (-2.0 * 0.25)
    assert fulfillment_of(kb_interface, 'fuzzy-ascend-iv') == pytest.approx(expected, rel=1e-4)


def test_fuzzy_decay_interval(kb_interface):
    expected = _E ** (-2.0 * 0.25)
    assert fulfillment_of(kb_interface, 'fuzzy-decay-iv') == pytest.approx(expected, rel=1e-4)


def test_as_close_as_possible_interval(kb_interface):
    assert fulfillment_of(kb_interface, 'acp-iv') == pytest.approx(1.0)


def test_as_many_as_possible_interval(kb_interface):
    expected = 1.0 - _E ** (-2.0 * 0.25)
    assert fulfillment_of(kb_interface, 'amap-iv') == pytest.approx(expected, rel=1e-4)


def test_as_few_as_possible_interval(kb_interface):
    expected = _E ** (-2.0 * 0.25)
    assert fulfillment_of(kb_interface, 'afap-iv') == pytest.approx(expected, rel=1e-4)


# ---------------------------------------------------------------------------
# Helpers for compound expression tests
# ---------------------------------------------------------------------------

def req_fulfillment_of(kb, requirement_name, state=STATE):
    result = kb.fetch_req_fulfillment(requirement_name, state)
    assert len(result) == 1, (
        f"Expected exactly one state_dependency for requirement '{requirement_name}' "
        f"in state '{state}', got {len(result)}"
    )
    return result[0]['sd']['fulfillment'][0]['value']


# ---------------------------------------------------------------------------
# Test: compound expression leaf seeds
# ---------------------------------------------------------------------------

def test_compound_leaf_true(kb_interface):
    assert fulfillment_of(kb_interface, 'comp-true') == pytest.approx(1.0)


def test_compound_leaf_false(kb_interface):
    assert fulfillment_of(kb_interface, 'comp-false') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: not_expression fulfillment propagation
# ---------------------------------------------------------------------------

def test_not_expression_negates_true(kb_interface):
    assert fulfillment_of(kb_interface, 'not-comp-true') == pytest.approx(0.0)


def test_fuzzy_not_negates_true(kb_interface):
    assert fulfillment_of(kb_interface, 'fnot-comp-true') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: or_expression fulfillment propagation (MAX)
# ---------------------------------------------------------------------------

def test_or_expression_max_true_false(kb_interface):
    assert fulfillment_of(kb_interface, 'or-true-false') == pytest.approx(1.0)


def test_fuzzy_or_max_true_false(kb_interface):
    assert fulfillment_of(kb_interface, 'for-true-false') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: and_expression fulfillment propagation (MIN)
# ---------------------------------------------------------------------------

def test_and_expression_min_true_false(kb_interface):
    assert fulfillment_of(kb_interface, 'and-true-false') == pytest.approx(0.0)


def test_fuzzy_and_min_true_false(kb_interface):
    assert fulfillment_of(kb_interface, 'fand-true-false') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: shall_expression fulfillment propagation (MIN)
# ---------------------------------------------------------------------------

def test_shall_true(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-true') == pytest.approx(1.0)


def test_shall_false(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-false') == pytest.approx(0.0)


def test_shall_mixed_min(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-mixed') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: may_expression fulfillment propagation (MAX)
# ---------------------------------------------------------------------------

def test_may_true(kb_interface):
    assert fulfillment_of(kb_interface, 'may-true') == pytest.approx(1.0)


def test_may_false(kb_interface):
    assert fulfillment_of(kb_interface, 'may-false') == pytest.approx(0.0)


def test_may_mixed_max(kb_interface):
    assert fulfillment_of(kb_interface, 'may-mixed') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: relaxed_requirement fulfillment propagation (MIN of expressions)
# ---------------------------------------------------------------------------

def test_req_shall_true(kb_interface):
    assert req_fulfillment_of(kb_interface, 'req-shall-true') == pytest.approx(1.0)


def test_req_shall_false(kb_interface):
    assert req_fulfillment_of(kb_interface, 'req-shall-false') == pytest.approx(0.0)


def test_req_mixed_min(kb_interface):
    assert req_fulfillment_of(kb_interface, 'req-mixed') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: gather-rule branch coverage (each sd_* sibling branch exercised)
# ---------------------------------------------------------------------------

def test_or_expression_with_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'or-with-not') == pytest.approx(1.0)


def test_and_expression_with_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'and-with-or') == pytest.approx(0.0)


def test_fuzzy_or_with_fuzzy_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'for-with-fnot') == pytest.approx(1.0)


def test_fuzzy_and_with_fuzzy_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'fand-with-fnot') == pytest.approx(0.0)


def test_fuzzy_and_with_fuzzy_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'fand-with-for') == pytest.approx(0.0)


def test_shall_with_may_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-may') == pytest.approx(0.0)


def test_may_with_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-not') == pytest.approx(1.0)


def test_req_with_may_child(kb_interface):
    assert req_fulfillment_of(kb_interface, 'req-with-may') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: shall remaining branches (sd_not, sd_or, sd_and, sd_fuzzy_not,
#       sd_fuzzy_or, sd_fuzzy_and)
# ---------------------------------------------------------------------------

def test_shall_with_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-not') == pytest.approx(1.0)


def test_shall_with_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-or') == pytest.approx(1.0)


def test_shall_with_and_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-and') == pytest.approx(0.0)


def test_shall_with_fuzzy_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-fnot') == pytest.approx(1.0)


def test_shall_with_fuzzy_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-for') == pytest.approx(1.0)


def test_shall_with_fuzzy_and_child(kb_interface):
    assert fulfillment_of(kb_interface, 'shall-with-fand') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: may remaining branches (sd_or, sd_and, sd_fuzzy_not, sd_fuzzy_or,
#       sd_fuzzy_and)
# ---------------------------------------------------------------------------

def test_may_with_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-or') == pytest.approx(1.0)


def test_may_with_and_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-and') == pytest.approx(0.0)


def test_may_with_fuzzy_not_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-fnot') == pytest.approx(1.0)


def test_may_with_fuzzy_or_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-for') == pytest.approx(1.0)


def test_may_with_fuzzy_and_child(kb_interface):
    assert fulfillment_of(kb_interface, 'may-with-fand') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: single-child compound expressions (MAX/MIN with no competition)
# ---------------------------------------------------------------------------

def test_or_single_child(kb_interface):
    assert fulfillment_of(kb_interface, 'or-single-true') == pytest.approx(1.0)


def test_fuzzy_or_single_child(kb_interface):
    assert fulfillment_of(kb_interface, 'for-single-true') == pytest.approx(1.0)


def test_and_single_child(kb_interface):
    assert fulfillment_of(kb_interface, 'and-single-true') == pytest.approx(1.0)


def test_fuzzy_and_single_child(kb_interface):
    assert fulfillment_of(kb_interface, 'fand-single-true') == pytest.approx(1.0)
