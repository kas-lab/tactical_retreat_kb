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
from typedb_tactics.utils import build_value_query


def test_string_value():
    query, var = build_value_query('hello')
    assert query is not None
    assert var == '$value'
    assert 'ValueString' in query
    assert '"hello"' in query


def test_string_suffix():
    query, var = build_value_query('world', 'my_suffix')
    assert query is not None
    assert var == '$valuemy_suffix'
    assert '$valuemy_suffix' in query


def test_float_value():
    query, var = build_value_query(1.5)
    assert query is not None
    assert var == '$value'
    assert 'ValueDouble' in query
    assert 'double_value' in query
    assert '1.500000000000000' in query


def test_int_value():
    query, var = build_value_query(42)
    assert query is not None
    assert var == '$value'
    assert 'ValueInteger' in query
    assert '42' in query


def test_bool_true():
    query, var = build_value_query(True)
    assert query is not None
    assert var == '$value'
    assert 'ValueBool' in query
    assert 'bool_value' in query


def test_bool_false():
    query, var = build_value_query(False)
    assert query is not None
    assert var == '$value'
    assert 'ValueBool' in query
    assert 'bool_value' in query


def test_bool_not_treated_as_int():
    """bool is a subclass of int; True must produce ValueBool, not ValueInteger."""
    query_bool, _ = build_value_query(True)
    query_int, _ = build_value_query(1)
    assert query_bool is not None
    assert query_int is not None
    assert 'ValueBool' in query_bool
    assert 'ValueInteger' not in query_bool
    assert 'ValueInteger' in query_int
    assert 'ValueBool' not in query_int


def test_list_variable_name():
    _, var = build_value_query([1, 2, 3])
    assert var == '$array'


def test_list_contains_array_declaration():
    query, _ = build_value_query([1, 2])
    assert query is not None
    assert 'ValueArray' in query


def test_list_contains_at_index_relations():
    query, _ = build_value_query([10, 20])
    assert query is not None
    assert 'at_index' in query
    assert 'has index 0' in query
    assert 'has index 1' in query


def test_list_of_integers():
    query, _ = build_value_query([1, 2])
    assert query is not None
    assert 'ValueInteger' in query
    assert '1' in query
    assert '2' in query


def test_list_of_strings():
    query, _ = build_value_query(['a', 'b'])
    assert query is not None
    assert 'ValueString' in query
    assert '"a"' in query
    assert '"b"' in query


def test_list_of_floats():
    query, _ = build_value_query([1.0, 2.0])
    assert query is not None
    assert 'ValueDouble' in query


def test_unsupported_type_returns_none():
    query, var = build_value_query(object())  # type: ignore[arg-type]
    assert query is None
    assert var is None
