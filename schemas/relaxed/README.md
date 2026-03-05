# relaxed schema

## Purpose

`relaxed_model.tql` models RELAX-style requirements with fuzzy fulfillment.
It captures requirement structures, temporal/event operators, and requirement-level
fulfillment degrees.

Conceptually, this is the project requirement model used during adaptation planning.
It represents how well requirements are expected to be satisfied given current context
and hypothetical tactic effects.

## Main files

- `relaxed_model.tql`: relaxed requirement and relaxed-expression model.
- `relaxed_mirte_example.tql`: MIRTE-focused requirement examples.
- `relaxed_paper_example.tql`: examples inspired by RELAX literature.
- `queries/get_requirement_fulfillment.tql`: fetch requirement fulfillment values.
- `queries/insert_requirement.tql`: minimal requirement insertion.
- `queries/query_mirte_memberships.tql`: inspect memberships for MIRTE fixtures.
- `queries/query_relaxed_paper_memberships.tql`: inspect memberships for paper fixtures.

## Core modeling concepts

### Requirements

- `System` identifies the managed system.
- `relaxed_requirement` (subtype of `system_requirement`) stores:
  - `requirement_name` (key),
  - `description`,
  - optional `in_effect`,
  - `fulfillment` score,
  - linked expressions.

### Relaxed expressions

- `relaxed_expression` extends base `expression` and holds `fulfillment`.
- Atomic and compound layers:
  - `atomic_relaxed_expression`
  - `compound_relaxed_expression`
  - `shall_expression`, `may_expression`, `eventually_expression`
  - event/timing types (`after_expression`, `before_expression`, `in_expression`, `until_expression`).

### Fuzzy requirement operators

- `relaxed_fuzzy_expression` and its subtypes:
  - `as_close_as_possible_expression`
  - `as_many_as_possible_expression`
  - `as_few_as_possible_expression`
  - frequency/time variants (for example `freq_as_close_as_possible_expression`).
- These connect to fuzzy sets from `logical_expressions/fuzzy_expression.tql`.

## Runtime semantics used in this project

The original model intent (documented in previous `AGENTS.md` versions) is:

- RELAX formulas are interpreted with a runtime-friendly degeneration of temporal semantics.
- Satisfaction is degree-valued in `[0, 1]` (`fulfillment` attribute).
- Compound fulfillment follows fuzzy logic composition:
  - negation approximated as `1 - x`,
  - conjunction as `min(...)`,
  - disjunction as `max(...)`.

This enables online tactical reasoning even when full path-space reasoning is not modeled.

## Dependencies

- Depends on `logical_expressions` for expression backbone.
- Depends on `context_model` + `data_structure` through `Measure`/`Value` usage.

## Practical modeling pattern

The example files use staged inserts (match + insert across multiple stages) to avoid
TypeDB constraints when creating relations and reusing them as role players in the same block.

## Notes for query authors

- `in_effect` is important for runtime planning queries; keep it explicit.
- For deterministic tests, sort query results in Python when required.
- Keep `expression_name` stable in staged inserts so multi-step expression wiring remains robust.
