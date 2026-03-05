# context_model schema

## Purpose

`context_model.tql` represents runtime context measurements and how those measurements are
produced from ROS interfaces.

It answers two core questions:

1. What is being measured now (or at a timestamp)?
2. Which runtime interface/function produced that measurement?

## Main files

- `context_model.tql`: measurement and measurement-interface model.
- `context_model_example.tql`: sample measure and time-stamped measurements.
- `queries/insert_measurement.tql`: insert a measurement value.
- `queries/fetch_measurements.tql`: fetch latest measurement value.
- `queries/fetch_measurement_interfaces.tql`: fetch extraction/proxy metadata.

## Core modeling concepts

### Measure entities

- `Measure` is keyed by `measure_name` and may include `description`.
- Typed subtypes (`MeasureBool`, `MeasureInteger`, `MeasureDouble`, etc.) keep measure
  semantics explicit.

### Measurement relation

- `measurement` links one `measure` to one `measurement_value`.
- Each measurement stores `measurement_time` and optional `latest`.
- Values come from `data_structure` (`Value` plays `measurement_value`).

### Measurement interfaces

- `measurement_interface` links:
  - `measure`: what is measured.
  - `source`: ROS interface where raw data comes from.
  - `output` (optional): interface that publishes transformed measurement.
- It also stores runtime extraction metadata:
  `measurement_function_name`, `measurement_function_lib`,
  `measurement_function_args`, `measurement_proxy`, `measurement_period`,
  `service_request_kwargs`.

## Dependencies

- Depends on `data_structure` (`Value` roles).
- Connected to ROS interfaces from `ros_model` (`Publisher`, `ServiceServer`, `ActionServer`).

## Notes for query authors

- Use `latest true` when callers need the current value only.
- Keep timestamps explicit; this model supports historical traces.
- Query result ordering is not guaranteed; sort in caller code if required.
