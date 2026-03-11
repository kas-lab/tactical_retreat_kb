# discover_hypothetical_req_fulfillment schema

## Purpose

`discover_hypothetical_req_fulfillment.tql` computes hypothetical requirement fulfillment
under each tactic rule, so orchestration logic can compare candidate adaptations before
execution.

In short: it estimates "if tactic X is applied, how would requirement Y fulfill?"

This is the selection-support layer used to rank tactics by expected impact on requirements
before applying reconfiguration actions to the running ROS system.

## Main files

- `discover_hypothetical_req_fulfillment.tql`: function-based hypothetical fulfillment logic.

## Core modeling concepts

### Function-based evaluation

- The schema computes hypothetical fulfillment directly with functions instead of materializing
  dependency or impact relations.
- The hot path is `tactic_rule_impacts_requirement_fulfillment`, which evaluates a requirement
  under a candidate tactic rule on demand.

## Dependencies

- Depends on:
  - `tactics_model` (tactic rules and effects),
  - `logical_expressions` and fuzzy operators,
  - `relaxed` requirements,
  - `context_model` measures.

## Notes for query authors

- Runtime queries should call the fulfillment functions directly.
- Typical consumer pattern: evaluate requirements per tactic and then optimize an objective
  such as mean fulfillment over in-effect requirements.
