# ros_model schema

## Purpose

`ros_model.tql` captures ROS graph/runtime knowledge used by the adaptation logic:

- nodes and lifecycle state,
- topics/services/actions,
- QoS profiles,
- node parameters and parameter values,
- deployment/process-group structure.

## Main files

- `ros_model.tql`: main ROS meta-model.
- `ros_model_example.tql`: rich Nav2-like runtime example.
- `default_qos.tql`: reusable QoS profile fixture.
- `queries/fetch_action_servers.tql`: fetch action servers.
- `queries/get_subnodes.tql`: fetch subnode composition.
- `queries/fetch_has_param_value.tql`: fetch parameter values.
- `queries/update_has_parameter_value.tql`: replace parameter values.

## Core modeling concepts

### Nodes

- `ROSNode` represents runtime node instances (`node_name` key, `namespace`, start/end time,
  optional `running`).
- `LifeCycleNode` extends `ROSNode` with `lifecycle_state`.
- `node_deployment` records package/executable.
- `process_group` and `subnode` model composition and grouped processes.

### Interfaces and communication

- `ROSInterface` (abstract) with concrete interface families:
  - Topics: `Publisher`, `Subscriber` via `has_topic`.
  - Services: `ServiceServer`, `ServiceClient` via `has_service`.
  - Actions: `ActionServer`, `ActionClient` via `has_action`.
- `QoSProfile` with relation `has_qos` links topic interfaces to QoS attributes.

### Parameters

- `Parameter` and typed subtypes model declared parameters.
- `has_parameter` links node to declared parameters.
- `has_parameter_value` links node+parameter to a concrete `Value` and flags `default_value`.

## Dependencies

- Depends on `data_structure` for parameter values.
- Integrates with `context_model` because publishers/service servers/action servers can be
  measurement sources.
- Used heavily by `tactics_model` and `discover_tactics_model`.

## Notes for query authors

- Interface roles are directional (`afferent` vs `efferent`) through `has_interface` subtypes.
- Arrays for parameter values are modeled through `ValueArray` + `at_index`.
- Keep lifecycle state strings within the schema regex constraints.
