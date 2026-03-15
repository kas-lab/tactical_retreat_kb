# Schema Cleanup & Semantic Correctness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove TypeDB 2 dead code, fix cardinality errors, flatten unused type hierarchies, and improve semantic clarity across all schema files — no new functionality.

**Architecture:** Three sequential passes — dead code removal, renames/fixes/simplifications, structural restructuring — with a full test run between each. Changes are purely to `.tql` schema and data-fixture files.

**Tech Stack:** TypeDB 3, TypeQL, Python pytest (for verification)

**Spec:** `docs/superpowers/specs/2026-03-15-schema-cleanup-design.md`

**Test command (run after every commit):**
```bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
```

---

## Chunk 1: Pass 1 — Dead Code Removal

---

### Task 1: Remove `fulfillment` stored attribute

**Files:**
- Modify: `schemas/relaxed/relaxed_model.tql` (lines 12, 36, 40, 134, 139)
- Modify: `schemas/relaxed/queries/get_requirement_fulfillment.tql`

`fulfillment` was a TypeDB 2 leftover — it is now computed on the fly by `fun relaxed_requirement_fulfillment()`. Both the attribute definition and all `owns fulfillment` declarations must be removed.

- [ ] **Step 1: Remove attribute definition and all `owns` declarations**

  In `schemas/relaxed/relaxed_model.tql`, delete:
  - Line ~12: `attribute fulfillment, value double;`
  - Line ~36: `owns fulfillment,` (on `relaxed_requirement`)
  - Line ~40: `owns fulfillment,` (on `relaxed_expression`)
  - Line ~134: `propositional_expression owns fulfillment;`
  - Line ~139: `fuzzy_expression owns fulfillment;`

- [ ] **Step 2: Rewrite `get_requirement_fulfillment.tql`** (if the file exists)

  Check if `schemas/relaxed/queries/get_requirement_fulfillment.tql` exists. If it does, the current file uses `has fulfillment $fulfillment` which no longer works. Replace the entire file with `fun`-based equivalents:

  ```typeql
  # Fetch fulfillment of a specific requirement
  match
      $system isa System, has system_name 'Mirte';
      $req (system: $system) isa relaxed_requirement,
          has requirement_name 'R1.1 Velocity';
      let $fulfillment = relaxed_requirement_fulfillment($req);
  fetch { $fulfillment };


  # Fetch fulfillment of all requirements in effect
  match
      $req isa relaxed_requirement,
          has in_effect true;
      let $fulfillment = relaxed_requirement_fulfillment($req);
  fetch
      $req: requirement_name;
      $fulfillment;
  ```

- [ ] **Step 3: Run tests**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```
  Expected: same tests pass as before.

- [ ] **Step 4: Commit**

  ```bash
  git add schemas/relaxed/relaxed_model.tql schemas/relaxed/queries/get_requirement_fulfillment.tql
  git commit -m "refactor: remove stored fulfillment attribute (TypeDB 2 leftover)"
  ```

---

### Task 2: Remove `offset_value` from `FuzzySet`

**Files:**
- Modify: `schemas/logical_expressions/fuzzy_expression.tql` (line ~7)

`offset_value` on `FuzzySet` is redundant — the correct owner is `fuzzy_expression`. The attribute definition (line ~1) and `fuzzy_expression owns offset_value` (line ~74) both stay unchanged.

- [ ] **Step 1: Remove the `FuzzySet owns offset_value` line**

  In `schemas/logical_expressions/fuzzy_expression.tql`, delete only the line:
  ```
  FuzzySet owns offset_value;
  ```
  (approximately line 7 — search for `FuzzySet owns offset_value`)

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/logical_expressions/fuzzy_expression.tql
  git commit -m "refactor: remove offset_value from FuzzySet (keep on fuzzy_expression)"
  ```

---

### Task 3: Remove dead attributes from `tactics_model.tql`

**Files:**
- Modify: `schemas/tactics_model/tactics_model.tql`

Three attributes are dead code and never referenced in queries or tests.

- [ ] **Step 1: Remove attribute definitions and any `owns` declarations**

  Search for and delete:
  - `attribute tactic_resolution_model, value string;` (lines ~12–14) and any `owns tactic_resolution_model`
  - `attribute tactic_select_variant, value string;` and any `owns tactic_select_variant`
  - `attribute variant_name sub name;` (line ~10 — this is a subtype of `name`, no `value string` clause) and any `owns variant_name`

  Note: `variant_name` must be deleted entirely — it does NOT become a plain attribute in Pass 2.

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/tactics_model/tactics_model.tql
  git commit -m "refactor: remove dead tactic_resolution_model, tactic_select_variant, variant_name attributes"
  ```

---

### Task 4: Remove dead attributes from `ros_model.tql`

**Files:**
- Modify: `schemas/ros_model/ros_model.tql`

`is_active` is defined but never owned by any entity. `lifecycle_transition` is defined but never owned either. Both can be deleted as attribute definitions only.

- [ ] **Step 1: Remove attribute definitions**

  In `schemas/ros_model/ros_model.tql`, delete only the attribute definitions — neither has an `owns` declaration anywhere:
  - `attribute is_active, value boolean;` (approximately line 12 — no `owns` declaration exists, so nothing else to remove)
  - `attribute lifecycle_transition, value string;` (approximately line 9 — no `owns` declaration exists)

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/ros_model/ros_model.tql
  git commit -m "refactor: remove unused is_active and lifecycle_transition attribute definitions"
  ```

---

### Task 5: Remove `Measure` and `Parameter` subtypes from schema

**Files:**
- Modify: `schemas/context_model/context_model.tql`
- Modify: `schemas/ros_model/ros_model.tql`

The subtype hierarchies are not used in match queries — value types are encoded in the `Value` entity. Only the type definitions need to go here; data fixtures are updated in Task 6.

- [ ] **Step 1: Remove all `Measure` subtypes from `context_model.tql`**

  Delete all of:
  ```typeql
  MeasureBool sub Measure;
  MeasureInteger sub Measure;
  MeasureDouble sub Measure;
  MeasureString sub Measure;
  MeasureBoolArray sub Measure;
  MeasureIntegerArray sub Measure;
  MeasureStringArray sub Measure;
  MeasureDoubleArray sub Measure;
  ```

- [ ] **Step 2: Remove all `Parameter` subtypes from `ros_model.tql`**

  Delete all of:
  ```typeql
  ParameterBool sub Parameter;
  ParameterInteger sub Parameter;
  ParameterDouble sub Parameter;
  ParameterString sub Parameter;
  ParameterBoolArray sub Parameter;
  ParameterIntegerArray sub Parameter;
  ParameterStringArray sub Parameter;
  ParameterDoubleArray sub Parameter;
  ```

- [ ] **Step 3: Run tests (expect failures from data fixtures — proceed to Task 6)**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```
  If tests fail due to unknown type errors on `MeasureDouble` etc., that is expected — fix in Task 6.

---

### Task 6: Update data fixtures after subtype removal

**Files:**
- Modify: `test/data/test_tactical_retreat_interface.tql` (lines 87–95)
- Modify: `test/data/test_tactics_model.tql` (line 54)
- Modify: `schemas/tactics_model/tactics_example.tql` (line 119)
- Modify: `schemas/ros_model/ros_model_example.tql` (lines 110, 113, 116)
- Modify: `schemas/ros_model/queries/update_has_parameter_value.tql` (line 5)
- Modify: `schemas/ros_model/queries/fetch_has_param_value.tql` (line 5)
- Modify: `scripts/benchmark/benchmark.tql` (lines ~587, 590, 593, 910)
- Modify: `scripts/generated.tql` (many lines — sed replacement)

Replace every `isa MeasureBool`, `isa MeasureInteger`, `isa MeasureDouble`, `isa MeasureString`, `isa MeasureBoolArray`, `isa MeasureIntegerArray`, `isa MeasureStringArray`, `isa MeasureDoubleArray` with `isa Measure`.

Replace every `isa ParameterBool`, `isa ParameterInteger`, `isa ParameterDouble`, `isa ParameterString`, `isa ParameterBoolArray`, `isa ParameterIntegerArray`, `isa ParameterStringArray`, `isa ParameterDoubleArray` with `isa Parameter`.

- [ ] **Step 1: Replace Measure subtypes in test data**

  In `test/data/test_tactical_retreat_interface.tql` lines 87–95, change:
  ```typeql
  $measure_string isa MeasureString, has measure_name "measure_string";
  $measure_double isa MeasureDouble, has measure_name "measure_double";
  $measure_integer isa MeasureInteger, has measure_name "measure_integer";
  $measure_bool isa MeasureBool, has measure_name "measure_bool";
  $measure_string_array isa MeasureStringArray, has measure_name "measure_string_array";
  $measure_double_array isa MeasureDoubleArray, has measure_name "measure_double_array";
  $measure_integer_array isa MeasureIntegerArray, has measure_name "measure_integer_array";
  $measure_bool_array isa MeasureBoolArray, has measure_name "measure_bool_array";
  ```
  To (all `isa Measure`):
  ```typeql
  $measure_string isa Measure, has measure_name "measure_string";
  $measure_double isa Measure, has measure_name "measure_double";
  $measure_integer isa Measure, has measure_name "measure_integer";
  $measure_bool isa Measure, has measure_name "measure_bool";
  $measure_string_array isa Measure, has measure_name "measure_string_array";
  $measure_double_array isa Measure, has measure_name "measure_double_array";
  $measure_integer_array isa Measure, has measure_name "measure_integer_array";
  $measure_bool_array isa Measure, has measure_name "measure_bool_array";
  ```

- [ ] **Step 2: Replace Parameter subtypes in test data and schema examples**

  In `test/data/test_tactics_model.tql` line 54:
  ```typeql
  # Before:
  $parameter isa ParameterDouble, has parameter_name "parameter";
  # After:
  $parameter isa Parameter, has parameter_name "parameter";
  ```

  In `schemas/tactics_model/tactics_example.tql` line 119:
  ```typeql
  # Before:
  $p_max_speed isa ParameterDoubleArray, has parameter_name "max_velocity";
  # After:
  $p_max_speed isa Parameter, has parameter_name "max_velocity";
  ```

  In `schemas/ros_model/ros_model_example.tql` lines 110, 113, 116:
  ```typeql
  # Before:
  $max_velocity_param isa ParameterDoubleArray, ...
  $odom_topic_param isa ParameterString, ...
  $odom_duration_param isa ParameterDouble, ...
  # After (all):
  $max_velocity_param isa Parameter, ...
  $odom_topic_param isa Parameter, ...
  $odom_duration_param isa Parameter, ...
  ```

  In `schemas/ros_model/queries/update_has_parameter_value.tql` line 5 and `schemas/ros_model/queries/fetch_has_param_value.tql` line 5:
  ```typeql
  # Before:
  $max_velocity_param isa ParameterDoubleArray, ...
  # After:
  $max_velocity_param isa Parameter, ...
  ```

- [ ] **Step 3: Replace Parameter subtypes in benchmark and generated scripts**

  In `scripts/benchmark/benchmark.tql` lines ~587, 590, 593, 910:
  Change `isa ParameterDoubleArray`, `isa ParameterString`, `isa ParameterDouble` → `isa Parameter`.

  For `scripts/generated.tql` (100+ occurrences), use a bulk replacement. Since this file is generated, verify whether it can simply be regenerated with the updated generator instead. If it cannot, replace all occurrences manually or with a script:
  - All `isa ParameterBool`, `isa ParameterInteger`, `isa ParameterDouble`, `isa ParameterString`, `isa ParameterBoolArray`, `isa ParameterIntegerArray`, `isa ParameterStringArray`, `isa ParameterDoubleArray` → `isa Parameter`

- [ ] **Step 4: Run tests**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```
  Expected: all previously-passing tests pass again.

- [ ] **Step 5: Commit**

  ```bash
  git add schemas/context_model/context_model.tql schemas/ros_model/ros_model.tql \
      test/data/test_tactical_retreat_interface.tql test/data/test_tactics_model.tql \
      schemas/tactics_model/tactics_example.tql schemas/ros_model/ros_model_example.tql \
      schemas/ros_model/queries/update_has_parameter_value.tql \
      schemas/ros_model/queries/fetch_has_param_value.tql \
      scripts/benchmark/benchmark.tql scripts/generated.tql
  git commit -m "refactor: flatten Measure and Parameter subtype hierarchies"
  ```

---

## Chunk 2: Pass 2 — Renames, Cardinality Fixes, Structural Simplifications

---

### Task 7: Rename `lifecycle_state` → `target_lifecycle_state` on `set_lifecycle_state`

**Files:**
- Modify: `schemas/tactics_model/tactics_model.tql`
- Modify: `schemas/tactics_model/queries/fetch_resolution_actions.tql`

`lifecycle_state` on `LifeCycleNode` means "current state". On `set_lifecycle_state` (a resolution action) it meant "target state" — the rename makes this explicit. The regex constraint is identical and carries over unchanged.

- [ ] **Step 1: Add `target_lifecycle_state` attribute and update `set_lifecycle_state`**

  In `schemas/tactics_model/tactics_model.tql`:

  1. Find the `lifecycle_state` attribute definition (which belongs to `LifeCycleNode`) — this one stays as `lifecycle_state` and must NOT be renamed.

  2. Add a new attribute definition alongside it:
     ```typeql
     attribute target_lifecycle_state, value string,
         regex "^(unconfigured|inactive|active|finalized)$";
     ```

  3. Find `set_lifecycle_state owns lifecycle_state` and change to:
     ```typeql
     set_lifecycle_state owns target_lifecycle_state;
     ```

- [ ] **Step 2: Update `fun set_lifecycle_state_feasible`**

  In `schemas/tactics_model/tactics_model.tql`, inside `fun set_lifecycle_state_feasible`, find:
  ```typeql
  $ra has lifecycle_state $target;
  ```
  Change to:
  ```typeql
  $ra has target_lifecycle_state $target;
  ```
  Leave the `$node has lifecycle_state $current` line unchanged — it refers to `LifeCycleNode`.

- [ ] **Step 3: Update `fetch_resolution_actions.tql`**

  In `schemas/tactics_model/queries/fetch_resolution_actions.tql`, find any match on `has lifecycle_state` applied to a `set_lifecycle_state` instance and change to `has target_lifecycle_state`.

- [ ] **Step 4: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/tactics_model/tactics_model.tql schemas/tactics_model/queries/fetch_resolution_actions.tql
  git commit -m "refactor: rename lifecycle_state to target_lifecycle_state on set_lifecycle_state"
  ```

---

### Task 8: Fix `gid` cardinality on `TopicInterface`

**Files:**
- Modify: `schemas/ros_model/ros_model.tql`

`TopicInterface` can have at most one DDS GID — the cardinality was `@card(0..)` by mistake.

- [ ] **Step 1: Fix cardinality**

  In `schemas/ros_model/ros_model.tql`, find:
  ```typeql
  TopicInterface owns gid @card(0..);
  ```
  Change to:
  ```typeql
  TopicInterface owns gid @card(0..1);
  ```

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/ros_model/ros_model.tql
  git commit -m "fix: gid cardinality on TopicInterface changed from 0.. to 0..1"
  ```

---

### Task 9: Remove abstract `name` attribute hierarchy

**Files:**
- Modify: `schemas/tactics_model/tactics_model.tql`

The abstract `name` attribute has subtypes `resolution_model_name`, `tactic_name`, `rule_name`. No polymorphic cross-type name queries exist, so the hierarchy adds complexity without benefit.

- [ ] **Step 1: Flatten the hierarchy**

  In `schemas/tactics_model/tactics_model.tql`:

  1. Remove the abstract `name` attribute definition. The actual line is: `attribute name @abstract, value string;`

  2. Change each subtype declaration from `sub name` to a plain top-level attribute. The subtypes do NOT repeat `value string` (they inherit it from `name`). For example:
     ```typeql
     # Before (actual schema syntax):
     attribute resolution_model_name sub name;
     attribute tactic_name sub name;
     attribute rule_name sub name;
     # After:
     attribute resolution_model_name, value string;
     attribute tactic_name, value string;
     attribute rule_name, value string;
     ```

  The `@key` and `@unique` constraints on those attributes stay exactly as they are.

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/tactics_model/tactics_model.tql
  git commit -m "refactor: flatten abstract name attribute hierarchy into plain attributes"
  ```

---

### Task 10: Simplify `compound_relaxed_expression`

**Files:**
- Modify: `schemas/relaxed/relaxed_model.tql`

`compound_relaxed_expression` is never instantiated directly — only `shall_expression` and `may_expression` are. Its `compound_member` role is unused.

- [ ] **Step 1: Make abstract and remove unused role (one atomic edit)**

  In `schemas/relaxed/relaxed_model.tql`, find the `compound_relaxed_expression` definition and:
  1. Add `abstract` to the entity/relation definition
  2. Remove the `relates compound_member @card(0..);` line

  No `plays compound_relaxed_expression:compound_member` declarations exist elsewhere — only this one `relates` line needs removal.

- [ ] **Step 2: Run tests and commit**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  git add schemas/relaxed/relaxed_model.tql
  git commit -m "refactor: make compound_relaxed_expression abstract and remove unused compound_member role"
  ```

---

## Chunk 3: Pass 3 — Structural Restructuring

---

### Task 11: Move `System` to `tactics_model.tql` and add relation role to `resolution_model`

**Files:**
- Modify: `schemas/tactics_model/tactics_model.tql`
- Modify: `schemas/relaxed/relaxed_model.tql`

`System` is currently defined in `relaxed_model.tql` but is conceptually a tactics-layer concept (it owns resolution models). Moving it to `tactics_model.tql` makes the dependency direction explicit. `resolution_model` currently references the system by a plain `ros_system: string` attribute — replace this with a proper `system` role.

- [ ] **Step 1: Move `System` entity and its attribute definitions to `tactics_model.tql`**

  Cut the following from `schemas/relaxed/relaxed_model.tql` (check exact syntax in the file):
  ```typeql
  attribute system_name, value string;

  entity System,
      owns system_name @key,
      owns start_time;
  ```
  **Do NOT move `attribute start_time, value datetime;`** — `start_time` is already defined in `ros_model.tql` (owned by `ROSNode`). Moving it would cause a duplicate attribute definition error. Only move `system_name` and the `System` entity block.

  Paste into `schemas/tactics_model/tactics_model.tql` (near the top, before `resolution_model`).

  `relaxed_model.tql` still uses `System` for `system_requirement` — this is fine as long as `tactics_model.tql` is loaded first (verified in Task 13).

- [ ] **Step 2: Replace `ros_system` on `resolution_model` with a `system` role**

  In `schemas/tactics_model/tactics_model.tql`:

  1. Remove the `ros_system: string` attribute definition:
     ```typeql
     attribute ros_system, value string;   # delete this line
     ```

  2. Remove `resolution_model owns ros_system` (or `has ros_system`).

  3. Add a `system` role to `resolution_model`:
     ```typeql
     relation resolution_model,
         ...existing roles...,
         relates system @card(1);
     ```

  4. Add the role player declaration:
     ```typeql
     System plays resolution_model:system;
     ```

- [ ] **Step 3: Run tests (expect fixture failures — continue to Task 12)**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```

---

### Task 12: Update all data fixtures for `ros_system` → `System` relation

**Files:**
- Modify: `schemas/tactics_model/tactics_example.tql`
- Modify: `test/data/test_discover_tactics_model_branches.tql`
- Modify: `test/data/test_tactics_model.tql`
- Modify: `test/data/test_tactical_retreat_interface.tql`
- Modify: `scripts/generated.tql` (if in scope)
- Modify: `scripts/benchmark/benchmark.tql` (if in scope)

Every fixture that inserts a `resolution_model` with `has ros_system "..."` must instead insert a `System` entity and link it via the new `system` role.

**CRITICAL — TypeDB 3 [REP1] constraint:** You CANNOT combine a named relation variable with inline role-player syntax (e.g. `$rm (system: $sys) isa resolution_model` triggers [REP1]). Always split into two statements:
```typeql
$rm isa resolution_model, has resolution_model_name "...";
$rm links (system: $sys);
```

- [ ] **Step 1: Update `test/data/test_tactics_model.tql`**

  Find the `resolution_model` insert with `has ros_system "system"` (line ~212). Replace:
  ```typeql
  # Before:
  $rm isa resolution_model,
      has resolution_model_name "res_model",
      has ros_system "system";

  # After:
  $sys isa System, has system_name "system";
  $rm isa resolution_model,
      has resolution_model_name "res_model";
  $rm links (system: $sys);
  ```
  Note: if a `System` with that name is already in the fixture, reuse the variable instead of inserting again.

- [ ] **Step 2: Update `test/data/test_discover_tactics_model_branches.tql`**

  Find `has ros_system "cov"` (line ~48). Replace:
  ```typeql
  # After:
  $sys isa System, has system_name "cov";
  $rm isa resolution_model, has resolution_model_name "...";
  $rm links (system: $sys);
  ```

- [ ] **Step 3: Update `test/data/test_tactical_retreat_interface.tql`**

  Find `has ros_system "mock"` (line ~84). Replace:
  ```typeql
  # After:
  $sys isa System, has system_name "mock";
  $rm isa resolution_model, has resolution_model_name "res_mock";
  $rm links (system: $sys);
  ```

- [ ] **Step 4: Update `schemas/tactics_model/tactics_example.tql`**

  Find `has ros_system "nav2"` (line ~207). Replace:
  ```typeql
  # After:
  $sys isa System, has system_name "nav2";
  $rm isa resolution_model, has resolution_model_name "rebetmc";
  $rm links (system: $sys);
  ```

- [ ] **Step 5: Update `scripts/benchmark/benchmark.tql` and `scripts/generated.tql`**

  These files are committed to the repo (not gitignored) and must be updated to keep the DB loadable.

  In `scripts/benchmark/benchmark.tql`: find all `has ros_system "nav2"` occurrences (lines ~998, 1148, 1156, …). For each `resolution_model` insert, apply the same split pattern. If multiple `resolution_model` entries share the same system name, insert the `System` entity once and reuse the variable.

  In `scripts/generated.tql`: find `has ros_system "rebet_frog"` (line ~2940). Apply the same pattern. If this file is auto-generated by a script, update the generator script instead of the output file directly (search the repo for the generator).

- [ ] **Step 7: Run tests**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```
  Expected: all previously-passing tests pass again.

- [ ] **Step 8: Commit**

  ```bash
  git add schemas/tactics_model/tactics_model.tql schemas/relaxed/relaxed_model.tql \
      schemas/tactics_model/tactics_example.tql \
      test/data/test_discover_tactics_model_branches.tql \
      test/data/test_tactics_model.tql \
      test/data/test_tactical_retreat_interface.tql \
      scripts/generated.tql scripts/benchmark/benchmark.tql
  git commit -m "refactor: move System to tactics_model, replace ros_system string with System relation role"
  ```

---

### Task 13: Verify and fix schema load order

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py` (or wherever schemas are loaded)

`tactics_model.tql` now defines `System`, which `relaxed_model.tql` depends on. Verify the load order is correct.

- [ ] **Step 1: Find where schemas are loaded**

  Search for where `.tql` schema files are opened/loaded in the Python code (run from the repo root):
  ```bash
  cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics
  grep -r "relaxed_model\|tactics_model" typedb_tactics/ --include="*.py" -l
  ```

- [ ] **Step 2: Verify load order**

  Confirm that `tactics_model.tql` is loaded before `relaxed_model.tql`. If not, reorder the load sequence.

- [ ] **Step 3: Run final test suite**

  ```bash
  docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest ...'
  ```
  Expected: all previously-passing tests pass. Pass 3 complete.

- [ ] **Step 4: Commit if any load-order change was needed**

  ```bash
  git add typedb_tactics/typedb_tactical_retreat_interface.py
  git commit -m "fix: ensure tactics_model.tql loads before relaxed_model.tql (System dependency)"
  ```
