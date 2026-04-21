# Symbolic States Schema

This folder contains several related schema variants:

- `symbolic_states.tql`: the main relation-based schema for symbolic discretization of context variables.
- `symbolic_states_entity_scheme.tql`: the older entity-based alternative where a symbolic scheme is modeled as an entity.
- `symbolic_states_unified.tql`: an alternative design that routes all label semantics through a single higher-level definition abstraction.

This README documents the main relation-based `symbolic_states.tql`.

## Goal

The purpose of `symbolic_states.tql` is to add a semantic layer on top of raw measurements from the context model.

Instead of reasoning only over continuous values such as velocity `0.22`, this schema makes it possible to define named symbolic labels such as:

- `low`
- `medium`
- `high`

and then infer, at query time, which labels are active for the latest measurements.

The current design assumes:

- exclusive partitions are desirable for many schemes
- half-open intervals are the preferred interval semantics
- multiple parallel interpretations of the same measure are allowed
- symbolic assignments are inferred and queried through the scheme relation, not materialized as a separate assignment relation
- undefined is an acceptable fallback when a scheme does not cover a value

## Dependencies

`symbolic_states.tql` intentionally does not redefine concepts already provided elsewhere. It must be loaded after its dependencies.

Current dependencies:

- `schemas/data_structure/data_structure.tql`
- `schemas/context_model/context_model.tql`
- `schemas/logical_expressions/logical_expression.tql`

From those models it reuses:

- `Measure`
- `measurement`, `latest`
- `ValueDouble`, `ValueInteger`
- `description`
- `logical_expression`

## Current Model

The implemented metamodel is centered around the following concepts.

### Symbolic schemes

A `symbolic_scheme` relation is a named interpretation of one or more context variables.

Important attributes:

- `symbolic_scheme_name`
- `exclusive_partition`
- `undefined_state`
- `ambiguous_state`

The intention is that a scheme relation represents something like:

- `velocity-bands/v1`
- `velocity-safety/v1`
- `navigation-context/v1`

`symbolic_scheme_name` is the only scheme identifier currently modeled.

### State dimensions and system states

The schema also supports building a system-state abstraction on top of symbolic schemes.

- `state_dimension` marks which `symbolic_scheme` relations count as dimensions of the system state
- `system_state` is a relation that groups one label per selected dimension
- `current_state` is an inferred attribute on `system_state` that is `true` when the state's labels match the currently active labels of the marked dimensions

This allows modeling state tuples such as:

- `low-safe`
- `medium-unsafe`
- `high-safe`

without introducing separate user-defined state-space types.

### Symbolic labels

A `SymbolicLabel` is an abstract symbolic category.

Subtypes:

- `AtomicSymbolicLabel`
- `CompositeSymbolicLabel`

Important attributes:

- `symbolic_label_name`
- `symbolic_order`
- `symbolic_active`

`symbolic_order` gives ordinal semantics for labels such as `low < medium < high`.

`symbolic_label_name` is the only label identifier currently modeled.

### Atomic interval definitions

Atomic labels are currently defined with numeric intervals:

- `symbolic_double_interval`
- `symbolic_integer_interval`

The schema does not require measures to be declared as `MeasureDouble` or `MeasureInteger`.
It allows a generic `Measure` to play both interval relations, and the rules discriminate by the runtime type of the latest measurement value.

These now sit under a small relation hierarchy:

- `symbolic_definition` is an abstract super-relation
- `symbolic_interval_definition` is an abstract interval-specific sub-relation
- `symbolic_logical_definition`, `symbolic_double_interval`, and `symbolic_integer_interval` are concrete definition relations

The interval semantics are intentionally half-open:

- lower bound is inclusive
- upper bound is exclusive

Supported interval shapes:

- bounded: `[lower, upper)`
- lower-unbounded: `(-inf, upper)`
- upper-unbounded: `[lower, +inf)`

### Composite labels

A `CompositeSymbolicLabel` is defined through `symbolic_logical_definition`, whose `definition` role is played by an existing `logical_expression`.

At the moment, the practical interpretation is:

- a composite symbolic label can be backed by a logical expression over raw measures and literal values

This gives support for composite symbolic concepts without introducing a new boolean logic just for symbolic labels.

### Query-time assignments

There is no `current_symbolic_assignment` relation in the main schema.

Instead, the query-time result is obtained by traversing:

- a `symbolic_scheme` relation
- to the related `SymbolicLabel` instances with `symbolic_active = true`

## Inference Semantics

The schema currently infers:

1. Whether an atomic label is active from the latest numeric measurement and its interval.
2. Whether a composite label is active from the satisfaction of its backing logical expression.
3. Whether a scheme is `undefined_state = true` because no label in an exclusive partition is active.
4. Whether a scheme is `ambiguous_state = true` because more than one differently named label in an exclusive partition is active.
5. Which declared `system_state` is the current one through the inferred `current_state` attribute.

The schema also infers default `false` values for:

- `symbolic_active`
- `undefined_state`
- `ambiguous_state`

so these attributes are easier to query directly.

## What Is Included Today

Implemented in `symbolic_states.tql`:

- named symbolic schemes
- ordered symbolic labels
- atomic integer and double intervals
- exclusive-partition-friendly modeling
- multiple schemes over the same measure
- query-time active labels through the scheme relation
- relation-based state dimensions and enumerated system states
- inferred `current_state` on declared system states
- undefined fallback for uncovered values
- ambiguity detection for overlapping active labels in exclusive schemes
- composite symbolic labels backed by `logical_expression`

## Deferred Ideas

These were discussed but intentionally not included yet, either to keep the schema smaller or because they conflicted with the current rule base.

### 1. Coverage and overlap verification

Desired behavior:

- prove that an exclusive scheme covers the intended domain
- detect interval gaps
- detect interval overlaps

This is not enforced by the schema today.

Recommended future approach:

- add a validation script or model-check step
- verify schemes offline before loading production data

This is still useful even though completeness is not represented as a stored schema attribute.

### 2. Hysteresis

Discussed idea:

- use different thresholds for entering and leaving a symbolic label

Example:

- enter `high` at `0.26`
- leave `high` at `0.24`

Why deferred:

- this is more naturally a transition policy over symbolic assignments than a base discretization rule

This should probably be added later as a separate layer rather than embedded directly into the current interval semantics.

### 3. Richer calibration and applicability modeling

Current design:

- schemes only carry a single name attribute

Deferred idea:

- represent calibration, platform, mission profile, controller version, or environment as first-class entities and relations

That would make scheme applicability more queryable and less string-based.

### 4. Total coverage as a hard invariant

Current design:

- total coverage is not represented as a stored schema attribute
- it is not guaranteed by the schema

Deferred idea:

- formally enforce or verify total coverage over a known numeric domain

### 7. Non-numeric symbolic partitions

Not included yet:

- symbolic labels over strings
- symbolic labels over booleans
- symbolic labels over arrays

The current schema only supports numeric discretization over integer and double measures.

### 8. Multi-dimensional atomic regions

Current atomic model assumes:

- one interval over one measure per atomic label definition

Deferred idea:

- define atomic symbolic regions over multiple variables directly, not only through a composite logical expression

Examples:

- `(velocity in medium) AND (distance in near)` as one first-class region
- rectangular or polyhedral regions in a multi-dimensional space

### 9. Relation to fuzzy sets

A useful future bridge is:

- treat symbolic intervals as crisp sets
- connect them to fuzzy sets as a graded generalization

That could support:

- hard symbolic classification
- soft confidence/membership side by side

## Example Modeling Pattern

A common intended usage is:

1. Define a raw measure in the context model, such as `velocity`.
2. Define one or more symbolic schemes for that measure, such as:
   `velocity-bands/v1`
   `velocity-safety/v1`
3. Add ordered labels such as `low`, `medium`, `high`.
4. Define half-open intervals for atomic labels.
5. Query the scheme relation for labels with `symbolic_active = true` to obtain the active symbolic label(s).

For system-state abstractions:

1. Mark the schemes that count as state dimensions using `state_dimension`.
2. Enumerate `system_state` tuples such as `medium-safe` or `high-unsafe`.
3. Query `system_state` with `current_state = true` to obtain the currently matching declared state.

For composite concepts:

1. Define an existing `logical_expression` over raw measures and values.
2. Link that expression to a `CompositeSymbolicLabel`.
3. Query the active composite label through the scheme relation and `symbolic_active`.

## Current Test Fixture

The initial test coverage for this schema is in:

- `test/data/test_symbolic_states.tql`
- `test/test_symbolic_states.py`

The test currently exercises:

- exclusive atomic partitioning
- multiple parallel schemes on the same measure
- relation-based state dimensions and current system state inference
- composite symbolic labels backed by logical expressions
- undefined fallback when a scheme contains a gap
- ambiguous fallback when an exclusive scheme contains overlapping active labels
