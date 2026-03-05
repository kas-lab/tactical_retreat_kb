# feature_model schema

## Purpose

The feature model schema represents variability choices and constraints used by tactics.
It defines selectable features, hierarchy groups, and cross-tree constraints.
In the adaptation loop, this is the variability model that captures which alternatives can
be activated/deactivated and which combinations are valid.

## Main files

- `feature_model.tql`: core feature-model entities and relations.
- `feature_model_logical_expression.tql`: bridge so `Feature` can act as a propositional atom.
- `feature_model_example.tql`: sample hierarchy (`MAX_SPEED` with alternatives).

## Core modeling concepts

### Feature entity

- `Feature` is keyed by `feature_name`.
- Optional state attributes:
  - `selected`: currently selected in a configuration.
  - `selectable`: currently allowed to be selected.
  - `mandatory`: mandatory feature flag.

### Hierarchy constraints

- `feature_hierarchy(parent, child)` models tree/graph parent-child structure.
- `alternative` subtype models XOR groups.
- `or_group` subtype models OR groups.

### Cross-tree constraints

- `cross_tree_constraint(constraint, constrained)` models inter-feature constraints.
- Subtypes:
  - `excludes_constraint`: mutual exclusion semantics.
  - `requires_constraint`: dependency semantics.

### Logical bridge

- `feature_model_logical_expression.tql` maps `Feature` to
  `propositional_expression:atom`, enabling feature conditions in rule antecedents.

## Dependencies

- Core schema is mostly standalone.
- Bridge file depends on `logical_expressions`.
- Used by `tactics_model` through `feature_adaptation` and variant resolution.

## Notes for query authors

- Use stable `feature_name` values because many tactic mappings depend on exact names.
- For strategy evaluation, pair feature queries with `selected` / `selectable` attributes.
