# tactics_model schema

## Purpose

`tactics_model.tql` represents adaptation tactics, their preconditions, expected effects,
and concrete resolution actions over the ROS system.

## Main files

- `tactics_model.tql`: tactic/rule/effect/resolution schema.
- `tactics_example.tql`: staged example with MIN/MED/MAX tactic rules.
- `queries/fetch_valid_rule.tql`: fetch valid tactic rules.
- `queries/fetch_resolution_actions.tql`: fetch resolved adaptation actions.

## Core modeling concepts

### Tactics and rules

- `Tactic` entity keyed by `tactic_name`.
- `tactic_rule` relation includes:
  - `antecedent` (logical preconditions),
  - `consequent` (adaptation consequence),
  - `effect` (predicted impact on measures),
  - metadata such as `rule_name` and `rule_valid`.

### Effects

- Abstract `effect` relation links a `measure` and a resulting value.
- `absolute_effect`: direct target value.
- `relative_effect`: delta/change effect.

### Consequents and resolution

- `feature_adaptation` consequence activates/deactivates features.
- `resolution_model` groups executable adaptation alternatives for a tactic.
- `variant_resolution` links a feature variant to concrete actions.
- `resolution_action` subtypes include:
  - `set_nodes_parameters`
  - `set_lifecycle_state`

## Dependencies

- Uses `logical_expressions` for rule antecedents.
- Uses `feature_model` for feature adaptations and variants.
- Uses `ros_model` for node/action targets.
- Uses `context_model` + `data_structure` for effect measures/values.

## Practical modeling pattern

`tactics_example.tql` is intentionally staged to avoid relation-construction pitfalls:

1. Insert entities and leaf relations.
2. Match by stable keys (`expression_name`, feature names, values).
3. Insert higher-level relations (`or_expression`, `and_expression`, `tactic_rule`,
   variant resolutions, and final `resolution_model`).

## Notes for query authors

- Keep `rule_name` and `resolution_model_name` stable; query APIs depend on them.
- `rule_valid`/`feasible` are central runtime filters; preserve semantics when editing rules.
