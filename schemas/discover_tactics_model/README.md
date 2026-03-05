# discover_tactics_model schema

## Purpose

This schema narrows candidate tactics to the ones relevant for a requested ROS interface
or action path. It builds neighborhood/connectivity views over the ROS graph and links them
to tactic resolution models.

This corresponds to the adaptation-loop filtering step: instead of evaluating all tactic rules,
evaluate only rules that can affect nodes reachable from the managed action/service/topic path.

## Main files

- `discover_tactics_model.tql`: discovery-specific relations.
- `queries/fetch_neighbours.tql`: inspect computed neighborhoods.
- `queries/tactic_affects_node.tql`: validate whether tactic consequents affect target nodes.
- `queries/applicable_tactics.tql`: fetch tactic rules applicable to a given interface.

## Core modeling concepts

### Graph expansion relations

- `neighbours(node, neighbour)`: local node neighborhood.
- `connected_nodes(node, connected)`: broader connectivity closure.

### Applicable tactic relation

- `applicable_tactics(interface, resolution_model, tactic_rule)` binds:
  - requested ROS interface,
  - a resolution model,
  - tactic rules that can affect nodes relevant to that interface.

## Dependencies

- Depends on `ros_model` for nodes/interfaces.
- Depends on `tactics_model` for resolution models and tactic rules.

## Notes for query authors

- Use this schema for search-space reduction before expensive fulfillment evaluation.
- Prefer action/service/topic interface names as entry points for discovery queries.
