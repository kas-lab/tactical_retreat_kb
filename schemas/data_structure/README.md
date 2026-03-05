# data_structure schema

## Purpose

`data_structure.tql` defines the foundational typed values used by all higher-level schemas.
It is the common layer that lets other models attach and compare booleans, integers,
doubles, strings, and ordered arrays.

## Main files

- `data_structure.tql`: schema definition.
- `data_structure_example.tql`: example inserts for singleton values and arrays.
- `queries/fetch_values.tql`: example fetches for scalar and array values.

## Core modeling concepts

### Value hierarchy

- `Value` (abstract): common supertype for all value carriers.
- `ValueSingleton`: one scalar value (`data_value`) with concrete sub-attributes:
  `bool_value`, `integer_value`, `double_value`, `string_value`.
- `ValueArray`: ordered collection of `Value` elements.

### Ordered arrays

- Relation `at_index` connects one `ValueArray` (`array`) to one value (`array_value`)
  and stores position in attribute `index`.
- This design keeps array order explicit in the data model.

## How other schemas use it

- `context_model`: uses `Value` for `measurement_value`.
- `ros_model`: uses `Value` for ROS parameter values.
- `logical_expressions` and `relaxed`: compare measures to typed values.
- `tactics_model`: uses values in effects and parameter-setting actions.

## Notes for query authors

- Prefer `ValueSingleton` when a scalar is expected.
- For arrays, always include `(array: ..., array_value: ...) isa at_index, has index ...`.
- TypeDB fetch order is not guaranteed; sort by `index` in query or Python when needed.
