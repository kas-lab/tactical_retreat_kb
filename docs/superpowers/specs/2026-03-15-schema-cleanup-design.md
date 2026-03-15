# Schema Cleanup & Semantic Correctness — Design Spec

**Date:** 2026-03-15
**Status:** Approved

## Summary

A three-pass refactoring of the TypeDB 3 schemas to remove dead code left over from the TypeDB 2 migration, fix cardinality errors, simplify unnecessary type hierarchies, and improve semantic clarity. No new functionality is added.

---

## Pass 1 — Dead Code Removal

### Attributes to remove

| Attribute | File(s) | Notes |
|-----------|---------|-------|
| `fulfillment: double` (attribute definition) | `relaxed_model.tql` line 12 | Remove attribute type definition and all `owns fulfillment` declarations |
| `owns fulfillment` | `relaxed_model.tql` lines 36, 40, 134, 139 | On `relaxed_requirement`, `relaxed_expression`, `propositional_expression`, `fuzzy_expression` |
| `offset_value: double` on `FuzzySet` | `fuzzy_expression.tql` | Remove only the `FuzzySet owns offset_value` declaration; the `offset_value` attribute definition and `fuzzy_expression owns offset_value` both stay |
| `tactic_resolution_model: string` | `tactics_model.tql` | Remove attribute definition and any `owns` |
| `tactic_select_variant: string` | `tactics_model.tql` | Remove attribute definition and any `owns` |
| `is_active: boolean` | `ros_model.tql` | Remove attribute definition only — `is_active` is defined but not owned by any entity (no `owns is_active` declaration exists) |
| `lifecycle_transition: string` | `ros_model.tql` line 9 | Defined but no entity/relation owns it — remove the attribute definition only |
| `variant_name: string` | `tactics_model.tql` | Entirely dead — remove attribute definition and any `owns`; do NOT carry forward as a plain attribute in Pass 2 |

### Queries to update

| File | Change |
|------|--------|
| `schemas/relaxed/queries/get_requirement_fulfillment.tql` | Remove or rewrite — this query fetches `has fulfillment $fulfillment` which will no longer exist as a stored attribute. Replace with the `fun relaxed_requirement_fulfillment()` call if a replacement query is needed. |

### Types to remove entirely

**Measure subtypes** (flatten to `Measure`):
`MeasureBool`, `MeasureInteger`, `MeasureDouble`, `MeasureString`,
`MeasureBoolArray`, `MeasureIntegerArray`, `MeasureStringArray`, `MeasureDoubleArray`

**Parameter subtypes** (flatten to `Parameter`):
`ParameterBool`, `ParameterInteger`, `ParameterDouble`, `ParameterString`,
`ParameterBoolArray`, `ParameterIntegerArray`, `ParameterStringArray`, `ParameterDoubleArray`

**Rationale:** These subtypes are not used in match queries. The value type is encoded in the `Value` entity subtype (`ValueSingleton` owning `bool_value`, `integer_value`, etc.) linked via `measurement` or `has_parameter_value`.

### Data fixtures to update after subtype removal

The following files insert instances typed as `Measure`/`Parameter` subtypes and must be updated to use `isa Measure` / `isa Parameter` instead:

| File | Change |
|------|--------|
| `test/data/test_tactical_retreat_interface.tql` (lines ~87–95+) | Change `isa MeasureString`, `isa MeasureDouble`, etc. → `isa Measure` |
| `schemas/ros_model/ros_model_example.tql` | Change `isa ParameterString`, `isa ParameterDouble`, etc. → `isa Parameter` |
| Any other test data or example `.tql` files that insert Measure/Parameter subtypes | Same change |

---

## Pass 2 — Renames, Cardinality Fixes, Structural Simplifications

### Rename

- `lifecycle_state: string` on `set_lifecycle_state` → `target_lifecycle_state: string`
  - **Rationale:** `lifecycle_state` on `LifeCycleNode` is the *current* observed state; the same attribute name on `set_lifecycle_state` (a resolution action) referred to the *target* state. The rename eliminates semantic ambiguity.
  - **Regex:** The `lifecycle_state` regex (`^(unconfigured|inactive|active|finalized)$`) carries over unchanged to `target_lifecycle_state`. Note: the deleted `lifecycle_transition` attribute (Pass 1) had a *different* regex — these are unrelated.
  - **Files to update:**
    - `schemas/tactics_model/tactics_model.tql` — rename attribute definition and `set_lifecycle_state owns lifecycle_state` → `owns target_lifecycle_state`
    - `schemas/tactics_model/tactics_model.tql` — update `fun set_lifecycle_state_feasible`: the line `$ra has lifecycle_state $target` must become `$ra has target_lifecycle_state $target` (the `$node has lifecycle_state $current` line remains unchanged — it refers to `LifeCycleNode`)
    - `schemas/tactics_model/queries/fetch_resolution_actions.tql` — update any `has lifecycle_state` match on `set_lifecycle_state` instances

### Cardinality fix

- `gid: integer` on `TopicInterface`: `@card(0..)` → `@card(0..1)`
  - **Rationale:** A topic interface has at most one DDS GID. The `@card(0..)` was set to make an old test pass and does not reflect the domain.
  - **File:** `schemas/ros_model/ros_model.tql`

### Remove abstract `name` hierarchy

- Delete abstract attribute `name`
- `resolution_model_name`, `tactic_name`, `rule_name` become plain top-level `string` attributes with no common supertype
- **Note:** `variant_name` is entirely deleted in Pass 1 (dead code) and does NOT become a plain attribute here
- **Rationale:** The abstract `name` supertype was only justified if polymorphic cross-type name queries were needed. They are not — each name is always queried in isolation on its specific type.
- **File:** `schemas/tactics_model/tactics_model.tql`

### Simplify `compound_relaxed_expression`

Apply both changes atomically in `schemas/relaxed/relaxed_model.tql`:
- Add `abstract` to the `compound_relaxed_expression` definition
- Remove the `relates compound_member @card(0..);` line

No `plays compound_relaxed_expression:compound_member` declarations exist elsewhere — only the one `relates` line needs to be removed.

**Rationale:** `compound_relaxed_expression` is never instantiated directly — only its concrete subtypes `shall_expression` and `may_expression` are used. Each subtype already defines its own `expression` role for membership. The `compound_member` role was unused.

---

## Pass 3 — Structural Restructuring

### Move `System` and connect it to `resolution_model`

**Changes:**

1. **Move `System` entity definition** (`system_name @key`, `start_time: datetime @card(1)`) from `schemas/relaxed/relaxed_model.tql` to `schemas/tactics_model/tactics_model.tql`

2. **Update `resolution_model`** in `tactics_model.tql`:
   - Remove `ros_system: string` attribute definition and `resolution_model owns ros_system`
   - Add a new role to `resolution_model`, e.g. `system @card(1)`, played by `System`

3. **Update data files** that currently insert `resolution_model` instances with `has ros_system`:

   | File | Change |
   |------|--------|
   | `schemas/tactics_model/tactics_example.tql` | Replace `has ros_system "nav2"` with a `links (system: $sys)` where `$sys isa System, has system_name "nav2"` |
   | `test/data/test_discover_tactics_model_branches.tql` | Same |
   | `test/data/test_tactics_model.tql` | Same |
   | `test/data/test_tactical_retreat_interface.tql` | Same |
   | `scripts/generated.tql` | Same (or mark as out-of-scope if generated) |
   | `scripts/benchmark/benchmark.tql` (many lines ~998–1212) | Same (or mark as out-of-scope if benchmark-only) |

4. **Schema load order:** `tactics_model.tql` must be loaded before `relaxed_model.tql`. `relaxed_model.tql` continues to use `System` (for `system_requirement`) — after the move this dependency becomes explicit. Verify the existing load order in `typedb_tactical_retreat_interface.py` (or wherever schemas are loaded) and adjust if needed.

**Rationale:** `resolution_model.ros_system` stored a system name as a plain string while a `System` entity with `system_name @key` already existed. Using a relation role instead of a string reference makes the connection explicit, queryable, and type-safe.

---

## What Is Not Changed

| Item | Reason kept |
|------|-------------|
| `has_interface` subtypes (`has_topic`, `has_service`, `has_action`) | Polymorphic queries across interface types are actively used |
| `Value` / `ValueArray` / `at_index` | `Value` must be an entity to play roles in relations; array indexing pattern is the best available in TypeDB 3 |
| `start_time` shared attribute | Polymorphic use across `ROSNode` and `System` is acceptable |
| `process_group` and `subnode` | Semantically distinct: OS-level process grouping vs logical sub-component nesting |
| `relaxed_fuzzy_expression:term` (separate from `fuzzy_comparison_expression:term`) | TypeDB single inheritance prevents sharing; both are necessary |
| `description` shared attribute | Generic human-readable description acceptable across `Measure` and `relaxed_requirement` |
| `and_expression` / `or_expression` asymmetry | Intentional DAG constraint preventing cycles in `fun` function recursion |
| `atomic_relaxed_expression` and sub-expressions | Incomplete but intentional; reserved for future RELAXED paper modeling |
| `tactic_rule:antecedent @card(0..)` | Zero antecedents is valid (unconditional tactic) |
| `measurement_function_args` and `service_request_kwargs` | Semantically distinct: direct function calls vs ROS service calls |
| `measurement_proxy: boolean` | Actively used to flag proxy-mediated measurement retrieval |
| `default_value: boolean` on `has_parameter_value` | Actively used to distinguish default vs runtime-configured parameter values |
| `System` disconnected from `ROSNode` | Intentional design choice |

---

## Implementation Approach

**Option B — By change category**, three sequential passes with test runs between each:

1. **Pass 1** (dead code removal) — lowest risk; validates test suite is stable after removals
2. **Pass 2** (renames, cardinality, structural simplifications) — medium risk; isolated changes
3. **Pass 3** (System restructuring) — highest risk; spans two schema files and requires data fixture updates

**Test command after each pass:**
```bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
```
