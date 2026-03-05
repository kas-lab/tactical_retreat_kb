# discover_hypothetical_req_fulfillment schema

## Purpose

`discover_hypothetical_req_fulfillment.tql` computes hypothetical requirement fulfillment
under each tactic rule, so orchestration logic can compare candidate adaptations before
execution.

In short: it estimates "if tactic X is applied, how would requirement Y fulfill?"

This is the selection-support layer used to rank tactics by expected impact on requirements
before applying reconfiguration actions to the running ROS system.

## Main files

- `discover_hypothetical_req_fulfillment.tql`: dependency and impact relations,
  plus stratified impact layers.

## Core modeling concepts

### Direct dependency

- `tactic_rule_dependency(tactic_rule, dependent)` connects a tactic rule to expressions or
  requirements that directly depend on its effects.
- Stores a `fulfillment` projection for the direct dependency.

### Impact propagation

- `tactic_rule_impacts` represents direct or indirect impacts.
- Stratified subtypes (`_base`, `_or`, `_and`, `_shall_expression`, `_may_expression`,
  `_requirement`) avoid negation cycles and separate operator semantics.

### In-effect scoped impacts

- Parallel `*_in_effect` relations keep impact propagation restricted to requirements currently
  in effect for runtime candidate selection.

### Resolution-model scoped hot path

- `resolution_model_tactic_rule_impacts_requirement_in_effect` denormalizes the most common
  runtime decision query path: for each `(resolution_model, tactic_rule, requirement in effect)`,
  store hypothetical fulfillment.

## Dependencies

- Depends on:
  - `tactics_model` (tactic rules and effects),
  - `logical_expressions` and fuzzy operators,
  - `relaxed` requirements,
  - `context_model` measures.

## Notes for query authors

- This schema is intentionally layered to keep reasoning stratified and maintainable.
- When extending impact logic, add new subtype layers carefully to avoid semantic cycles.
- Keep runtime-focused queries aligned with the resolution-model-scoped relation above.
- Typical consumer pattern: compute impacts per tactic and then optimize an objective
  (for example mean fulfillment over in-effect requirements).
