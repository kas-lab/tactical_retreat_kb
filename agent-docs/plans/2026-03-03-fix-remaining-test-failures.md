# Fix Remaining Test Failures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all failing tests in the typedb_tactics TypeDB 3 migration so that test_fuzzy_expression.py, test_relaxed_model.py, test_tactics_model.py, test_tactical_retreat_interface.py, test_hypothetical_req_fulfillment.py, and test_generated_benchmark_profile.py all pass.

**Architecture:** All TypeDB 2 rule-inferred attributes (`membership_degree`, `fulfillment`, `rule_valid`, `feasible`, `resulting_effect_value`, graph relations `neighbours`/`connected_nodes`/`applicable_tactics`, and dependency/impact relations) are replaced with Python computation in the interface class. Schema and data file structural errors ([REP1], [CNT5], [WCP4]) are fixed first to unblock data loading, then interface methods are rewritten to compute values instead of querying rule-inferred attributes.

**Tech Stack:** Python 3, TypeDB 3, TypeQL, ROS 2 Humble, pytest, Docker (container: `tactical_retreat`)

---

## Environment Setup

All tests run inside the Docker container. After editing host files, sync with:
```bash
docker cp <host_file> tactical_retreat:<container_path>
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon build --packages-select typedb_tactics --symlink-install'
```

Key paths:
- Host workspace: `~/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/`
- Container workspace: `/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/`
- Run a single test file: `docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest test/test_fuzzy_expression.py -v'`

---

## Task A: Fix Schema `@card` Violations

**Files:**
- Modify: `schemas/ros_model/ros_model.tql`
- Modify: `schemas/tactics_model/tactics_model.tql`

**Context:** TypeDB 3 defaults `relates` to `@card(0..1)`. Any role with more than one player in a single relation instance raises `[CNT5]`. Two schemas have multi-player roles without the annotation.

**Step 1: Fix `has_parameter` in ros_model.tql**

Find the `has_parameter` relation definition in `schemas/ros_model/ros_model.tql` and add `@card(0..)` to the `parameter` role:

```typeql
# BEFORE:
relation has_parameter,
    relates node,
    relates parameter;

# AFTER:
relation has_parameter,
    relates node,
    relates parameter @card(0..);
```

**Step 2: Fix `tactic_rule` roles in tactics_model.tql**

Find `tactic_rule` in `schemas/tactics_model/tactics_model.tql`. The `effect` and `antecedent` roles each get `@card(0..)`:

```typeql
# BEFORE:
relation tactic_rule,
    relates effect,
    relates antecedent,
    ...;

# AFTER:
relation tactic_rule,
    relates effect @card(0..),
    relates antecedent @card(0..),
    ...;
```

Also check for `tactic_rule_dependency`, `tactic_rule_impacts`, `applicable_tactics`, `neighbours`, `connected_nodes` in `schemas/discover_tactics_model/` and `schemas/discover_hypothetical_req_fulfillment/` — add `@card(0..)` to any role that could have multiple players.

**Step 3: Sync and verify schema loads without error**

```bash
docker cp schemas/ros_model/ros_model.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/schemas/ros_model/ros_model.tql
docker cp schemas/tactics_model/tactics_model.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/schemas/tactics_model/tactics_model.tql
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   python3 -m pytest test/test_ros_model.py -v'
```

Expected: All 3 tests in test_ros_model.py still PASS (regression check).

**Step 4: Commit**

```bash
git add schemas/ros_model/ros_model.tql schemas/tactics_model/tactics_model.tql
git commit -m "fix: add @card(0..) to multi-player roles in ros_model and tactics_model schemas"
```

---

## Task B: Fix `[REP1]` in Data Files

**Files:**
- Modify: `test/data/test_tactical_retreat_interface.tql`
- Modify: `schemas/tactics_model/tactics_example.tql`
- Modify: `test/data/test_tactics_model.tql`

**Context:** TypeDB 3 `[REP1]` fires when:
1. A named relation variable `$r (role: $x) isa T` is created in INSERT AND used as a role player in the same INSERT block.
2. A named variable bound via role pattern `$r (role: $x) isa T` in MATCH is then used as a role player in INSERT.

The fix for case 1: split into 2 stages — first INSERT (anonymous, with `expression_name` key), then MATCH+INSERT to use it as role player.
The fix for case 2: add an `expression_name` attribute to the type and give it a unique value in Stage 1; in later stages, match by `has expression_name '...'` not by role pattern.

**Step 1: Fix `test_tactical_retreat_interface.tql`**

Read the file to find the exact [REP1] location (around lines 30-36 where `$less_than (lhs_value:...) isa less_than` is created AND used as `antecedent:$less_than` in the same INSERT).

Split into two stages:
```typeql
# STAGE 1: Insert the less_than expression (anonymous, with key)
insert
(lhs_value: $lhs, rhs_value: $rhs) isa less_than, has expression_name 'lt_key_1';
# ... (other leaf expressions that ARE NOT used as role players in this stage)

# STAGE 2: Match the less_than, insert the tactic_rule that uses it
match
$lt isa less_than, has expression_name 'lt_key_1';
# ... (match other needed entities)
insert
(antecedent: $lt, ...) isa tactic_rule, has ...;
```

**Step 2: Fix `tactics_example.tql` and `test_tactics_model.tql`**

Both files have `feature_adaptation` relations matched via role pattern then used as role players. The fix requires:
1. Add `expression_name` ownership to `feature_adaptation` in `tactics_model.tql` schema.
2. In Stage 1 data: insert each `feature_adaptation` anonymously with a unique `has expression_name 'fa_key_N'`.
3. In later stages: match `$fa isa feature_adaptation, has expression_name 'fa_key_N'` then use `$fa` as role player.

In `schemas/tactics_model/tactics_model.tql`, add to the `feature_adaptation` definition:
```typeql
# Add expression_name ownership to feature_adaptation
feature_adaptation owns expression_name;
```

Then rewrite the stage(s) in `tactics_example.tql` and `test_tactics_model.tql` that:
- Previously: `match $s4a_fa_min (activation: $s4a_f_sel) isa feature_adaptation; insert ... (consequent: $s4a_fa_min) isa ...;`
- After:
  - Stage N-1: `insert (activation: $x) isa feature_adaptation, has expression_name 'fa_key_1';`
  - Stage N: `match $fa isa feature_adaptation, has expression_name 'fa_key_1'; insert (consequent: $fa) isa ...;`

**Step 3: Sync all changed files and run targeted test**

```bash
# Sync all changed data/schema files
docker cp test/data/test_tactical_retreat_interface.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/test/data/test_tactical_retreat_interface.tql
docker cp schemas/tactics_model/tactics_example.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/schemas/tactics_model/tactics_example.tql
docker cp schemas/tactics_model/tactics_model.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/schemas/tactics_model/tactics_model.tql
docker cp test/data/test_tactics_model.tql tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/test/data/test_tactics_model.tql
```

Check that `test_tactics_model.py::test_measurement_latest` passes (it doesn't need rule-inferred attributes):
```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_tactics_model.py::test_measurement_latest -v'
```
Expected: PASS.

**Step 4: Commit**

```bash
git add test/data/test_tactical_retreat_interface.tql schemas/tactics_model/tactics_example.tql schemas/tactics_model/tactics_model.tql test/data/test_tactics_model.tql
git commit -m "fix: resolve [REP1] errors in data files by splitting INSERT stages and adding expression_name to feature_adaptation"
```

---

## Task C: Fix `add_measurement` Method

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Context:** The `add_measurement` method (around line 1035) has two bugs:
1. Wrong TypeDB 3 delete attribute syntax: `delete $measurement has $latest;` must be `delete has $latest of $measurement;`
2. `[WCP4]` from a named measurement variable with cross-schema `plays` augmentations — fix by restructuring the INSERT.

**Step 1: Find the exact `add_measurement` code**

Read `typedb_tactics/typedb_tactical_retreat_interface.py` around line 1035. Note the exact queries.

**Step 2: Fix delete syntax**

```python
# BEFORE (TypeDB 2 syntax):
delete_query = f"""match
    $measure isa Measure, has measure_name '{measure_name}';
    $measurement ($measure) isa measurement, has latest $latest; $latest == true;
    delete $measurement has $latest;"""

# AFTER (TypeDB 3 syntax):
delete_query = f"""match
    $measure isa Measure, has measure_name '{measure_name}';
    $measurement ($measure) isa measurement, has latest $latest; $latest == true;
    delete has $latest of $measurement;"""
```

**Step 3: Fix [WCP4] in INSERT**

If the INSERT creates a named variable for `measurement` that has cross-schema `plays` roles, make it anonymous:

```python
# BEFORE (may cause [WCP4] if $measurement is named):
insert_query = f"""match ...;
    insert $measurement (...) isa measurement, has value {value}, has latest true;"""

# AFTER (anonymous measurement):
insert_query = f"""match ...;
    insert (...) isa measurement, has value {value}, has latest true;"""
```

**Step 4: Sync and test add_measurement**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_tactics_model.py::test_measurement_latest test/test_tactical_retreat_interface.py -v -k "measurement"'
```

Expected: `test_measurement_latest` PASS, measurement-related tactical_retreat_interface tests PASS.

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "fix: correct TypeDB 3 delete attribute syntax and [WCP4] in add_measurement"
```

---

## Task D: Python Computation for `rule_valid`, `feasible`, `resulting_effect_value`

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Context:** TypeDB 2 rules previously inferred:
- `rule_valid`: a `tactic_rule` is valid if its `antecedent` expressions are all satisfied AND there are no conflicting states
- `feasible`: a `set_nodes_parameters` or `set_lifecycle_state` action is feasible if its target parameters/states match current conditions
- `resulting_effect_value`: the numeric value of the effect after applying a tactic rule

These must now be computed in Python by fetching the underlying data and applying the logic.

**Step 1: Understand existing query methods**

Read `typedb_tactical_retreat_interface.py` lines 790-950 to understand:
- `fetch_tactic_rule_valid` (line ~792) — what it queries
- `get_tactic_rule_valid` (line ~799) — what it returns
- `is_set_nodes_parameters_feasible` (line ~843) — logic
- `is_set_lifecycle_state_feasible` (line ~864) — logic
- `get_resulting_effect_value` (line ~900) — logic

Also read the schema in `schemas/tactics_model/tactics_model.tql` to understand the type hierarchy and attributes involved.

**Step 2: Rewrite `fetch_tactic_rule_valid` / `get_tactic_rule_valid`**

Logic: A `tactic_rule` is valid when all its `antecedent` expressions evaluate to true (satisfied). Since `expression.satisfied` IS populated (it's a data attribute, not rule-inferred), query antecedent satisfiedness:

```python
def get_tactic_rule_valid(self, tactic_rule_name: str) -> bool:
    """Return True if all antecedents of the tactic rule are satisfied."""
    query = f"""match
        $tr isa tactic_rule, has tactic_rule_name '{tactic_rule_name}';
        (antecedent: $ant, tactic_rule_rel: $tr) isa tactic_rule_antecedent;
        $ant has satisfied $sat;
        fetch {{ "satisfied": $sat }};"""
    results = self.db.fetch_database(query)
    if not results:
        return True  # No antecedents = vacuously valid
    return all(r['satisfied'] for r in results)
```

**Note:** Adjust the query to match the exact schema shape. Read `tactics_model.tql` to see how `antecedent` role and `satisfied` attribute are structured. If `tactic_rule` relates `antecedent` directly (not via a separate relation), query:

```python
query = f"""match
    $tr isa tactic_rule, has tactic_rule_name '{tactic_rule_name}';
    (effect: $tr) isa feature_adaptation, has satisfied $sat;
    fetch {{ "satisfied": $sat }};"""
```

Run the test to see what the actual schema yields, adjust accordingly.

**Step 3: Rewrite `is_set_nodes_parameters_feasible`**

Logic: A `set_nodes_parameters` action is feasible if the target parameter value is within bounds or consistent with current state. Read the current implementation and the test in `test/test_tactics_model.py::test_set_nodes_parameters_feasible` to understand what "feasible" means in context.

Implement by fetching current parameter state and checking bounds:

```python
def is_set_nodes_parameters_feasible(self, node_name: str, parameter_name: str) -> bool:
    """Return True if setting the parameter is feasible given current node state."""
    query = f"""match
        $node isa ROSNode, has node_name '{node_name}';
        $param isa Parameter, has parameter_name '{parameter_name}';
        (node: $node, parameter: $param) isa has_parameter;
        fetch {{ "node_name": $node.node-name, "parameter_name": $param.parameter-name }};"""
    results = self.db.fetch_database(query)
    # Parameter exists → feasible
    return len(results) > 0
```

Read `test_tactics_model.py` to understand what the test asserts and make the implementation match.

**Step 4: Rewrite `is_set_lifecycle_state_feasible`**

Similar approach — read the test assertion and implement Python logic.

**Step 5: Rewrite `get_resulting_effect_value`**

Logic: Query the `tactic_rule`'s `effect` and its `quantified_value`, then compute the result based on operation type.

```python
def get_resulting_effect_value(self, tactic_rule_name: str) -> float | None:
    """Return the resulting effect value after applying the tactic rule."""
    query = f"""match
        $tr isa tactic_rule, has tactic_rule_name '{tactic_rule_name}';
        (tactic_rule_rel: $tr, effect: $eff) isa tactic_rule_effect;
        $eff has quantified_value $qv;
        fetch {{ "quantified_value": $qv }};"""
    results = self.db.fetch_database(query)
    if not results:
        return None
    values = [r['quantified_value'] for r in results]
    # Rules previously computed: resulting_effect_value = min of effects (for tactic_rule)
    return min(values) if values else None
```

Adjust the query and aggregation based on the actual schema. Read `tactics_model.tql` for the exact role names.

**Step 6: Sync and run tests**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_tactics_model.py -v'
```

Expected: All 6 tests PASS.

**Step 7: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "feat: replace rule-inferred rule_valid/feasible/resulting_effect_value with Python computation"
```

---

## Task E: Python Fuzzy Membership Computation

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Context:** TypeDB 2 rules computed `membership_degree` for 7 fuzzy set types. The test `test_fuzzy_expression.py` calls `get_fuzzy_membership_degree(expression_name)` and expects a float result. The method must now:
1. Query the fuzzy expression's type and parameters.
2. Query the `quantified_value`.
3. Compute membership in Python using the appropriate math formula.
4. Handle compound operators (NOT = 1-x, OR = max, AND = min) recursively.

**Step 1: Read the test to understand expected behavior**

Read `test/test_fuzzy_expression.py`. Note:
- What expression names are used
- What membership values are expected
- Which compound operators are tested

Also read `test/data/test_fuzzy_expression.tql` to understand the exact data structure.

**Step 2: Add Python fuzzy math functions to the interface**

Add a private helper section (before the class or as static methods):

```python
import math

def _fuzzy_sigmoid(exponent: float, inflection: float, x: float) -> float:
    """m(x) = 1 / (1 + e^(-exp*(x - inflection)))"""
    return 1.0 / (1.0 + math.exp(-exponent * (x - inflection)))

def _fuzzy_exp_saturation(exponent: float, x: float) -> float:
    """m(x) = 1 - e^(-exp*x)"""
    return 1.0 - math.exp(-exponent * x)

def _fuzzy_bounded_linear_fraction(curvature: float, x: float) -> float:
    """m(x) = x / (x + curvature)"""
    return x / (x + curvature)

def _fuzzy_triangular(a: float, b: float, c: float, x: float) -> float:
    """m(x) = (x-a)/(b-a) for a<=x<=b, (c-x)/(c-b) for b<=x<=c, else 0"""
    if x <= a or x >= c:
        return 0.0
    if x <= b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)

def _fuzzy_gaussian(sigma: float, center: float, x: float) -> float:
    """m(x) = e^(-0.5*((x-center)/sigma)^2)"""
    return math.exp(-0.5 * ((x - center) / sigma) ** 2)

def _fuzzy_exp_decay(exponent: float, x: float) -> float:
    """m(x) = e^(-exp*x)"""
    return math.exp(-exponent * x)

def _fuzzy_rational_decay(curvature: float, x: float) -> float:
    """m(x) = curvature / (x + curvature)"""
    return curvature / (x + curvature)
```

**Step 3: Rewrite `fetch_fuzzy_membership_degree` / `get_fuzzy_membership_degree`**

The new implementation:
1. Queries the fuzzy expression by name to determine its type (FuzzySigmoid, FuzzyExponentialSaturation, etc.)
2. Queries the associated fuzzy set's parameters and the expression's `quantified_value`
3. Applies the appropriate Python formula
4. For compound operators, recursively gets sub-expression membership values and applies AND/OR/NOT

```python
def get_fuzzy_membership_degree(self, expression_name: str) -> float | None:
    """Compute fuzzy membership degree for expression_name in Python."""
    # First, determine expression type
    type_query = f"""match
        $fe isa fuzzy_expression, has expression_name '{expression_name}';
        fetch {{ "type": $fe.type }};"""
    # NOTE: TypeDB 3 fetch doesn't expose type directly - use a different approach
    # Query for each possible type or use a get query:
    type_result = self.db.get_database(f"""match
        $fe isa fuzzy_expression, has expression_name '{expression_name}';
        select $fe;""")
    if not type_result:
        return None
    fe_type = type_result[0]['fe']['type']['label']

    if fe_type in ('fuzzy_ascend_expression', 'fuzzy_decay_expression', 'fuzzy_unimodal_expression'):
        return self._compute_leaf_membership(expression_name, fe_type)
    elif fe_type == 'fuzzy_not':
        return self._compute_fuzzy_not(expression_name)
    elif fe_type == 'fuzzy_or':
        return self._compute_fuzzy_or(expression_name)
    elif fe_type == 'fuzzy_and':
        return self._compute_fuzzy_and(expression_name)
    return None

def _compute_leaf_membership(self, expression_name: str, expr_type: str) -> float | None:
    """Compute membership for a leaf fuzzy expression."""
    # Query quantified_value and fuzzy set type + parameters
    query = f"""match
        $fe isa fuzzy_expression, has expression_name '{expression_name}',
            has quantified_value $qv;
        (fuzzy_set: $fs, fuzzy_member: $fe) isa {expr_type};
        fetch {{
            "quantified_value": $qv,
            "fs_type": $fs.type
        }};"""
    # ... (fetch params of $fs based on type, then compute)
```

**Important:** Read the actual schema carefully before writing these queries. The exact relation shapes between `fuzzy_expression`, `fuzzy_set`, and their roles need to match the schema in `fuzzy_expression.tql`. Check:
- Does `fuzzy_ascend_expression` relate `fuzzy_set` AND `fuzzy_member`?
- How is `quantified_value` associated?

Adjust queries accordingly. Use `text2typeql` script to find examples:
```bash
# In src/ros_typedb/
python3 scripts/find-text2typeql-examples.py "fetch entity attribute type" --top-k 5 --min-score 1
```

**Step 4: Handle compound operators**

```python
def _compute_fuzzy_not(self, expression_name: str) -> float | None:
    """NOT: 1 - membership of sub-expression."""
    query = f"""match
        $op isa fuzzy_not, has expression_name '{expression_name}';
        (fuzzy_operator: $op, expression: $sub) isa fuzzy_not;
        $sub has expression_name $sub_name;
        fetch {{ "sub_name": $sub_name }};"""
    results = self.db.fetch_database(query)
    if not results:
        return None
    sub_name = results[0]['sub_name']
    sub_val = self.get_fuzzy_membership_degree(sub_name)
    return 1.0 - sub_val if sub_val is not None else None

def _compute_fuzzy_or(self, expression_name: str) -> float | None:
    """OR: max of sub-expression memberships."""
    query = f"""match
        $op isa fuzzy_or, has expression_name '{expression_name}';
        (fuzzy_operator: $op, expression: $sub) isa fuzzy_or;
        $sub has expression_name $sub_name;
        fetch {{ "sub_name": $sub_name }};"""
    results = self.db.fetch_database(query)
    vals = [self.get_fuzzy_membership_degree(r['sub_name']) for r in results]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None

def _compute_fuzzy_and(self, expression_name: str) -> float | None:
    """AND: min of sub-expression memberships."""
    # Same pattern as fuzzy_or but with min
    ...
    return min(vals) if vals else None
```

**Step 5: Sync and run fuzzy tests**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_fuzzy_expression.py -v'
```

Expected: All 7 tests PASS.

**Step 6: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "feat: replace fuzzy membership rules with Python math computation"
```

---

## Task F: Python Relaxed Fulfillment Computation

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Context:** TypeDB 2 rules computed `fulfillment` attribute on relaxed expressions:
- `shall_expression`: fulfillment = min of its sub-expression memberships
- `may_expression`: fulfillment = max of its sub-expression memberships
- `relaxed_requirement`: fulfillment = min of shall_expression fulfillments

The method `fetch_relaxed_expression_fulfillment` must now compute this in Python.

**Step 1: Read existing methods and test expectations**

Read `typedb_tactical_retreat_interface.py` around line 1173 for `fetch_relaxed_expression_fulfillment` and `get_relaxed_requirement_fulfillment`. Read `test/test_relaxed_model.py` to understand expected values.

Also read `schemas/relaxed/relaxed_model.tql` to understand the schema structure:
- How `shall_expression`, `may_expression`, `relaxed_requirement` relate to fuzzy expressions
- Role names

**Step 2: Rewrite `fetch_relaxed_expression_fulfillment`**

```python
def fetch_relaxed_expression_fulfillment(self, expression_name: str) -> list[dict]:
    """Compute fulfillment for a relaxed expression (shall/may) in Python."""
    # Determine expression type
    type_result = self.db.get_database(f"""match
        $re isa relaxed_expression, has expression_name '{expression_name}';
        select $re;""")
    if not type_result:
        return []
    re_type = type_result[0]['re']['type']['label']

    # Get sub-expression memberships
    sub_query = f"""match
        $re isa {re_type}, has expression_name '{expression_name}';
        ($re, expression: $sub) isa {re_type};
        $sub has expression_name $sub_name;
        fetch {{ "sub_name": $sub_name }};"""
    sub_results = self.db.fetch_database(sub_query)

    memberships = []
    for r in sub_results:
        val = self.get_fuzzy_membership_degree(r['sub_name'])
        if val is not None:
            memberships.append(val)

    if not memberships:
        return []

    if re_type == 'shall_expression':
        fulfillment = min(memberships)
    elif re_type == 'may_expression':
        fulfillment = max(memberships)
    else:
        fulfillment = min(memberships)

    return [{'fulfillment': fulfillment}]
```

**Step 3: Rewrite `get_relaxed_requirement_fulfillment`**

```python
def get_relaxed_requirement_fulfillment(self, requirement_name: str) -> float | None:
    """Compute fulfillment for a relaxed requirement (min of shall fulfillments)."""
    # Query shall_expressions that make up this requirement
    query = f"""match
        $rr isa relaxed_requirement, has requirement_name '{requirement_name}';
        ($rr, shall: $se) isa relaxed_requirement_composition;
        $se has expression_name $se_name;
        fetch {{ "se_name": $se_name }};"""
    results = self.db.fetch_database(query)

    fulfillments = []
    for r in results:
        fut = self.fetch_relaxed_expression_fulfillment(r['se_name'])
        if fut:
            fulfillments.append(fut[0]['fulfillment'])

    return min(fulfillments) if fulfillments else None
```

**Note:** Adjust role names and relation names based on actual `relaxed_model.tql` schema.

**Step 4: Sync and run relaxed model tests**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_relaxed_model.py -v'
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "feat: replace relaxed fulfillment rules with Python min/max computation"
```

---

## Task G: Python Graph Relations (`neighbours`, `connected_nodes`, `applicable_tactics`)

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Context:** TypeDB 2 rules inferred three graph relations:
- `neighbours`: Two ROSNodes are neighbours if they share a topic (one publishes, other subscribes) or one is a sub-node of the other
- `connected_nodes`: Transitive closure of neighbours (BFS)
- `applicable_tactics`: Tactic rules applicable to a resolution model interface via connected nodes

These are now computed in Python.

**Step 1: Rewrite `fetch_neighbours`**

```python
def fetch_neighbours(self, node_name: str, namespace: str) -> list[dict]:
    """Return nodes that are neighbours of the given node (Python computation)."""
    # Shared topic: both connected to same topic (pub+sub)
    shared_topic_query = f"""match
        $n1 isa ROSNode, has node_name '{node_name}', has namespace '{namespace}';
        $n2 isa ROSNode;
        not {{ $n1 is $n2; }};
        $topic isa ROSTopic;
        (publisher: $n1, topic: $topic) isa publishes;
        (subscriber: $n2, topic: $topic) isa subscribes;
        fetch {{
            "node_name": $n2.node-name,
            "namespace": $n2.namespace
        }};"""
    # Also: reverse direction (n2 publishes, n1 subscribes)
    # Also: sub-node relationship
    results = self.db.fetch_database(shared_topic_query)
    # ... collect all unique neighbours
    return results
```

**Step 2: Rewrite `fetch_connected_nodes` (BFS)**

```python
def fetch_connected_nodes(self, node_name: str, namespace: str) -> list[dict]:
    """Return all nodes reachable from node_name via BFS on neighbours."""
    visited = {(node_name, namespace)}
    queue = [(node_name, namespace)]
    connected = []

    while queue:
        current_name, current_ns = queue.pop(0)
        neighbours = self.fetch_neighbours(current_name, current_ns)
        for n in neighbours:
            key = (n['node_name'], n['namespace'])
            if key not in visited:
                visited.add(key)
                queue.append(key)
                connected.append(n)

    return connected
```

**Step 3: Rewrite `fetch_applicable_tactics`**

```python
def fetch_applicable_tactics(self, resolution_model_name: str, interface_name: str) -> list[dict]:
    """Return tactic rules applicable to the interface via connected nodes."""
    # Get nodes in resolution model connected to interface
    connected = self.fetch_connected_nodes_for_interface(interface_name)
    if not connected:
        return []

    # For each connected node, find tactic rules that target it
    results = []
    for node in connected:
        query = f"""match
            $rm isa resolution_model, has model_name '{resolution_model_name}';
            $n isa ROSNode, has node_name '{node["node_name"]}';
            $tr isa tactic_rule;
            (resolution_model: $rm, interface: $n, tactic_rule_rel: $tr) isa applicable_to;
            fetch {{
                "tactic_rule_name": $tr.tactic-rule-name
            }};"""
        results.extend(self.db.fetch_database(query))
    return results
```

**Note:** The exact query structure depends on the schema. Read `schemas/discover_tactics_model/discover_tactics_model.tql` and the existing `fetch_applicable_tactics` method to understand the correct role/relation names.

**Step 4: Sync and test**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_tactical_retreat_interface.py -v'
```

Expected: All 11 tests PASS.

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "feat: replace neighbours/connected_nodes/applicable_tactics rules with Python BFS computation"
```

---

## Task H: Fix `discover_hypothetical_req_fulfillment`

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`
- Possibly: `schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql`

**Context:** `test_hypothetical_req_fulfillment.py` uses:
- Old TypeDB 2 fetch syntax (inline `fetch $tr_dependency: fulfillment;`)
- Result format `fulfillment_query_res[0]['tr_dependency']['fulfillment'][0]['value']`
- Rules for `tactic_rule_dependency`, `tactic_rule_impacts`, stratified fulfillment propagation

This is the most complex task. The test file itself may contain the old TypeDB 2 syntax.

**Step 1: Read the test file**

Read `test/test_hypothetical_req_fulfillment.py` completely. Note:
- All inline TypeQL queries
- All result format accesses
- Which methods from `typedb_tactical_retreat_interface.py` it calls

**Step 2: Update inline TypeQL queries in the test (if any)**

The test may have inline TypeDB 2 fetch syntax. Update each:
```python
# OLD:
query = "fetch $tr_dependency: fulfillment;"
result = db.fetch_database(query)
val = result[0]['tr_dependency']['fulfillment'][0]['value']

# NEW (TypeDB 3 flat result):
query = "fetch { \"fulfillment\": $tr_dependency.fulfillment };"
result = db.fetch_database(query)
val = result[0]['fulfillment']
```

**Step 3: Implement `tactic_rule_dependency` computation in Python**

Logic from stripped rules:
- Direct dependency: `tactic_rule A` has dependency on `tactic_rule B` if B's effect conflicts with A's antecedent
- Transitive via fulfillment propagation

Implement as Python methods in the interface:

```python
def get_tactic_rule_dependency_fulfillment(self, tr_name: str) -> float | None:
    """Compute the hypothetical fulfillment if tactic rule is applied."""
    # 1. Get the rule's effects
    # 2. Get the relaxed requirements affected
    # 3. Simulate applying the effect (update quantified_value)
    # 4. Recompute fuzzy membership and fulfillment
    # 5. Return resulting fulfillment
    ...
```

**Step 4: Sync and run test**

```bash
docker cp typedb_tactics/typedb_tactical_retreat_interface.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/typedb_tactics/typedb_tactical_retreat_interface.py
docker cp test/test_hypothetical_req_fulfillment.py tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/test/test_hypothetical_req_fulfillment.py
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_hypothetical_req_fulfillment.py -v'
```

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py test/test_hypothetical_req_fulfillment.py
git commit -m "feat: implement hypothetical req fulfillment computation in Python"
```

---

## Task I: Fix `test_generated_benchmark_profile`

**Files:**
- Read: `scripts/generated.tql`
- Possibly modify: `test/test_generated_benchmark_profile.py`

**Step 1: Read the test file**

```bash
cat test/test_generated_benchmark_profile.py
cat scripts/generated.tql | head -50
```

**Step 2: Check for data loading errors**

Run the test in isolation:
```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/test_generated_benchmark_profile.py -v -s 2>&1 | head -100'
```

**Step 3: Fix any issues found**

Common issues:
- TypeDB 2 fetch/result syntax in the test
- `generated.tql` may have [REP1] or [CNT5] errors
- May depend on rule-inferred attributes

Fix each issue found.

**Step 4: Commit any fixes**

```bash
git add <changed files>
git commit -m "fix: update test_generated_benchmark_profile for TypeDB 3"
```

---

## Task J: Full Test Suite Pass and Lint

**Files:**
- Possibly: `typedb_tactics/typedb_tactical_retreat_interface.py` (minor fixes)

**Step 1: Run all tests together**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && \
   python3 -m pytest test/ -v --ignore=test/test_kb.py 2>&1'
```

Expected: All tests pass (excluding test_kb.py which requires live ROS nodes).

**Step 2: Run flake8 lint**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics \
   --pytest-args -k test_flake8'
```

Fix any lint errors. Common issues: line too long (max 99 chars), unused imports, trailing whitespace.

**Step 3: Run pep257 lint**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics \
   --pytest-args -k test_pep257'
```

Fix any docstring style errors.

**Step 4: Final commit**

```bash
git add -u
git commit -m "fix: resolve all remaining lint errors after TypeDB 3 migration"
```

---

## Quick Reference

### Sync a file to container:
```bash
docker cp <host_relative_path> tactical_retreat:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/<same_path>
```

### Run a single test:
```bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest test/TEST_FILE.py -v -s 2>&1 | tail -50'
```

### TypeDB 3 key syntax reminders:
- Delete attribute: `delete has $attr of $entity;` (NOT `delete $entity has $attr;`)
- Fetch flat result: `fetch { "key": $var.attribute-name };` → `result['key']`
- Multi-player role: `relates role_name @card(0..);`
- No named relation in INSERT that is also used as role player in SAME block

### text2typeql search:
```bash
# From src/ros_typedb/ directory:
python3 scripts/find-text2typeql-examples.py "your query description" --top-k 5 --min-score 1
```
