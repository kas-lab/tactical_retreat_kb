# TypeDB 3 Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate `typedb_tactics` from TypeDB 2 to TypeDB 3 by updating the Dockerfile, rewriting `TacticalRetreatInterface` to use composition, updating all imports, rewriting all fetch queries and result-parsing helpers, updating aggregate/select syntax, and verifying all tests pass inside the `tactical_retreat` container.

**Architecture:** `TacticalRetreatInterface` stops subclassing `TypeDBInterface` and instead holds `self.db = TypeDBInterface(...)`. All fetch queries switch from `fetch $var: attr;` to `fetch { "key": $var.attr };`. Result parsing switches from `result[var][attr][0]['value']` to `result['key']`.

**Tech Stack:** Python 3.10, ROS 2 Humble, TypeDB 3.x, `typedb-driver` (PyPI), `colcon`, Docker container `tactical_retreat` at `/home/ubuntu-user/tactical_retreat_ws/`.

> **Critical rule:** Every test and build step must run **inside the `tactical_retreat` container** via `docker exec`. Do not run tests on the host. TypeDB server runs as the container entrypoint.
>
> **Run command template:**
> ```bash
> docker exec tactical_retreat bash -lc \
>   'source /opt/ros/humble/setup.bash && \
>    source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
>    cd /home/ubuntu-user/tactical_retreat_ws && \
>    <YOUR COMMAND>'
> ```

---

## Task 1: Update the Dockerfile for TypeDB 3

**Files:**
- Modify: `Dockerfile`

The Dockerfile currently installs TypeDB 2.28.3 and `typedb-driver==2.28.0`. Both must be updated to TypeDB 3.

**Step 1: Check TypeDB 3 apt install instructions**

Open https://typedb.com/docs/ and find the current Linux apt install instructions for TypeDB 3. Note the apt repo URL, GPG key fingerprint, and package name/version. As of writing, the GPG key is expected to remain `17507562824cfdcc` and the package is `typedb`, but **verify this before editing**.

**Step 2: Update TypeDB server installation in Dockerfile**

Replace lines 38–44 in `Dockerfile`:

```dockerfile
# OLD
RUN gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-key 17507562824cfdcc
RUN gpg --export 17507562824cfdcc | sudo tee /etc/apt/trusted.gpg.d/vaticle.gpg > /dev/null
RUN echo "deb https://repo.typedb.com/public/public-release/deb/ubuntu trusty main" | tee /etc/apt/sources.list.d/vaticle.list > /dev/null

RUN apt-get update && apt-get install -y \
    typedb=2.28.3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install typedb-driver==2.28.0
```

Replace with (substitute `<TYPEDB3_VERSION>` with the actual TypeDB 3 version):

```dockerfile
# NEW
RUN gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-key 17507562824cfdcc
RUN gpg --export 17507562824cfdcc | sudo tee /etc/apt/trusted.gpg.d/vaticle.gpg > /dev/null
RUN echo "deb https://repo.typedb.com/public/public-release/deb/ubuntu trusty main" | tee /etc/apt/sources.list.d/vaticle.list > /dev/null

RUN apt-get update && apt-get install -y \
    typedb=<TYPEDB3_VERSION> \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install typedb-driver
```

**Step 3: Remove Java dependency (TypeDB 3 is written in Rust)**

In the `apt-get install` block (lines 6–33), remove `openjdk-11-jre`.

**Step 4: Update or remove TypeDB Studio**

Lines 50–51 install TypeDB Studio 2.28.0. Either update to the TypeDB 3-compatible Studio version (check https://typedb.com/docs/) or remove those lines entirely if Studio is not required for CI/testing.

**Step 5: Build the image**

```bash
docker build \
  --secret id=gh_token,src=<(gh auth token) \
  --build-arg DEPS_CACHE_BUSTER=$(date +%s) \
  -t tactical_retreat .
```

Expected: build completes without errors.

**Step 6: Verify TypeDB 3 server starts**

```bash
docker run -d --rm --name tactical_retreat_test tactical_retreat typedb server
sleep 5
docker exec tactical_retreat_test bash -lc 'typedb --version'
docker stop tactical_retreat_test
```

Expected: version string containing `3.`.

**Step 7: Commit**

```bash
git add Dockerfile
git commit -m "build: update Dockerfile to TypeDB 3 server and typedb-driver"
```

---

## Task 2: Update imports in typedb_tactical_retreat_interface.py

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py:14-30`

**Background:** In TypeDB 3 / new `ros_typedb`, `convert_py_type_to_query_type` and `convert_query_type_to_py_type` have moved from `ros_typedb.typedb_interface` to `ros_typedb.typedb_helpers`. `MatchResultDict` and `TypeDBInterface` remain in `ros_typedb.typedb_interface`.

**Step 1: Run lint to confirm current state**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: flake8 either passes or shows existing failures (baseline).

**Step 2: Update the import block**

Replace lines 14–30 of `typedb_tactics/typedb_tactical_retreat_interface.py`:

```python
# OLD
from ros_typedb.typedb_interface import convert_py_type_to_query_type
from ros_typedb.typedb_interface import convert_query_type_to_py_type
from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import TypeDBInterface

from typedb.driver import ConceptMap
```

```python
# NEW
from ros_typedb.typedb_helpers import convert_py_type_to_query_type
from ros_typedb.typedb_helpers import convert_query_type_to_py_type
from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import TypeDBInterface
```

Do **not** remove `import inspect` here — it is still used at line ~120 by the `__init__` compatibility shim. It will be removed in Task 3 once that shim is deleted.

**Step 3: Verify imports resolve inside container**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   python3 -c "from ros_typedb.typedb_helpers import convert_py_type_to_query_type; print(\"OK\")"'
```

Expected: `OK`

**Step 4: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: update ros_typedb import paths for TypeDB 3"
```

---

## Task 3: Switch TacticalRetreatInterface from inheritance to composition

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py:108-155`

**Background:** `TacticalRetreatInterface` currently inherits from `TypeDBInterface`. The new `TypeDBInterface` in `ros_typedb` has no `sort_fetch_results` parameter and no `fetch_database_unordered`. The class must be rewritten to hold `self.db = TypeDBInterface(...)` and delegate all query calls to it.

**Step 1: Rewrite the class definition and `__init__`**

Replace the class header and `__init__` (lines 108–143):

```python
# OLD
class TacticalRetreatInterface(TypeDBInterface):
    """Class to interact with the TacticalRetreat knowledge model in typeDB."""

    def __init__(
            self,
            address: str,
            database_name: str,
            schema_path: Optional[list[str] | str] = None,
            data_path: Optional[list[str] | str] = None,
            force_database: Optional[bool] = False,
            force_data: Optional[bool] = False,
            infer: Optional[bool] = False,
            sort_fetch_results: Optional[bool] = False) -> None:
        self._sort_fetch_results = bool(sort_fetch_results)
        super_init = inspect.signature(TypeDBInterface.__init__)
        if 'sort_fetch_results' in super_init.parameters:
            super().__init__(...)
        else:
            super().__init__(...)
```

```python
# NEW
class TacticalRetreatInterface:
    """Class to interact with the TacticalRetreat knowledge model in typeDB."""

    def __init__(
            self,
            address: str,
            database_name: str,
            schema_path: Optional[list[str] | str] = None,
            data_path: Optional[list[str] | str] = None,
            force_database: Optional[bool] = False,
            force_data: Optional[bool] = False,
            infer: Optional[bool] = False) -> None:
        """
        Initialise TacticalRetreatInterface.

        :param address: TypeDB server address (e.g. 'localhost:1729').
        :param database_name: name of the TypeDB database.
        :param schema_path: list of .tql schema file paths.
        :param data_path: list of .tql data file paths.
        :param force_database: delete and recreate database if it exists.
        :param force_data: clear all data before loading data_path files.
        :param infer: enable inference engine.
        """
        self.db = TypeDBInterface(
            address,
            database_name,
            schema_path,
            data_path,
            force_database,
            force_data,
            infer)
        self.logger = logging.getLogger(__name__)
```

**Step 2: Remove the overridden `fetch_database`, `fetch_database_unordered`, and `fetch_database_unsorted` methods**

Delete lines 145–155 (the overridden `fetch_database`) and lines 543–555 (`fetch_database_unordered` and `fetch_database_unsorted`). These methods existed only to support `sort_fetch_results`, which is removed.

**Step 3: Add `delete_database` delegation method**

Tests call `kb_interface.delete_database()`. Since we no longer inherit from `TypeDBInterface`, add an explicit delegation:

```python
def delete_database(self) -> None:
    """Delete the database."""
    self.db.delete_database()
```

Place this immediately after `__init__`.

**Step 4: Run flake8 inside container**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: PASS (or only pre-existing failures unrelated to this change).

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: replace TypeDBInterface inheritance with composition"
```

---

## Task 4: Replace self.* query calls with self.db.*

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py` (all occurrences)

**Background:** After removing inheritance, every call to `self.fetch_database(q)`, `self.get_database(q)`, etc., is now a broken reference. Replace all with `self.db.<method>(q)`.

**Step 1: Identify all occurrences**

```bash
grep -n 'self\.fetch_database\|self\.get_database\|self\.get_aggregate_database\|self\.insert_database\|self\.delete_from_database\|self\.update_database\|self\.fetch_database_unordered' \
  typedb_tactics/typedb_tactical_retreat_interface.py
```

**Step 2: Replace all query delegation calls**

Use your editor or sed to replace:

| Old | New |
|---|---|
| `self.fetch_database(` | `self.db.fetch_database(` |
| `self.fetch_database_unordered(` | `self.db.fetch_database(` |
| `self.get_database(` | `self.db.get_database(` |
| `self.get_aggregate_database(` | `self.db.get_aggregate_database(` |
| `self.insert_database(` | `self.db.insert_database(` |
| `self.delete_from_database(` | `self.db.delete_from_database(` |
| `self.update_database(` | `self.db.update_database(` |

Note: `fetch_database_unordered` no longer exists in `TypeDBInterface` — replace it with `self.db.fetch_database(`. Result ordering is no longer guaranteed; callers that need order must sort themselves (this is addressed in Task 7).

**Step 3: Run flake8**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: PASS.

**Step 4: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: delegate all query calls to self.db"
```

---

## Task 5: Rewrite all fetch queries to TypeDB 3 syntax

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Background:** TypeDB 2 fetch syntax (`fetch $var: attr1, attr2;`) is invalid in TypeDB 3. TypeDB 3 uses JSON-like projection syntax: `fetch { "key": $var.attr };`.

**TypeDB 3 fetch syntax rules:**
- Each projected attribute gets a string key: `"key": $var.attr_name`
- The attribute name in the projection uses the schema label (with hyphens if that's what the schema defines)
- Wrap all projections in `{ }` after `fetch`
- Sub-fetch blocks (`key: { match ...; fetch ...; };`) are replaced with separate queries or joined differently — check TypeDB 3 docs for sub-fetch support
- Bare attribute variable fetch: `fetch { "fulfillment": $fulfillment };` (no entity prefix)

**Step 1: Systematically rewrite each fetch query**

Work through every `fetch` block in `typedb_tactical_retreat_interface.py`. The table below lists each method and its required query change:

| Method | Old fetch clause | New fetch clause |
|---|---|---|
| `fetch_subnodes` | `fetch $subnode: node_name, namespace;` | `fetch { "node_name": $subnode.node_name, "namespace": $subnode.namespace };` |
| `fetch_action_clients_nodes` | `fetch $node: node_name, namespace;` | `fetch { "node_name": $node.node_name, "namespace": $node.namespace };` |
| `fetch_action_server_nodes` | `fetch $node: node_name, namespace;` | `fetch { "node_name": $node.node_name, "namespace": $node.namespace };` |
| `fetch_action_clients_names` | `fetch $action_client: interface_name, interface_type;` | `fetch { "interface_name": $action_client.interface_name, "interface_type": $action_client.interface_type };` |
| `fetch_action_server_names` | same pattern | same pattern |
| `fetch_connected_action_server_nodes` | `fetch $server_node: node_name, namespace;` | `fetch { "node_name": $server_node.node_name, "namespace": $server_node.namespace };` |
| `fetch_connected_subscriber_nodes` | `fetch $subscriber_node: node_name, namespace;` | `fetch { "node_name": $subscriber_node.node_name, "namespace": $subscriber_node.namespace };` |
| `fetch_tactics` | `fetch $tactic: tactic_name;` | `fetch { "tactic_name": $tactic.tactic_name };` |
| `fetch_all_tactic_rules` | `fetch $tactic_rule: rule_name;` | `fetch { "rule_name": $tactic_rule.rule_name };` |
| `fetch_neighbours` | `fetch $neighbour: node_name, namespace;` | `fetch { "node_name": $neighbour.node_name, "namespace": $neighbour.namespace };` |
| `fetch_connected_nodes` | `fetch $connected: node_name, namespace;` | `fetch { "node_name": $connected.node_name, "namespace": $connected.namespace };` |
| `fetch_applicable_tactics` | `fetch $tactic_rule: rule_name;` | `fetch { "rule_name": $tactic_rule.rule_name };` |
| `fetch_relaxed_requirement_fulfillment` | `fetch $fulfillment;` | `fetch { "fulfillment": $fulfillment };` |
| `fetch_in_effect_requirement_fulfillment` | `fetch $req: requirement_name, fulfillment;` | `fetch { "requirement_name": $req.requirement_name, "fulfillment": $req.fulfillment };` |
| `fetch_requirement_in_effect` | `fetch $req: in_effect;` | `fetch { "in_effect": $req.in_effect };` |
| `fetch_tactic_rule_valid` | `fetch $tr: rule_valid;` | `fetch { "rule_valid": $tr.rule_valid };` |
| `is_feature_selectable` | `fetch $f: selectable;` | `fetch { "selectable": $f.selectable };` |
| `is_node_running` | `fetch $node: running;` | `fetch { "running": $node.running };` |
| `is_set_nodes_parameters_feasible` | `fetch $ra: feasible;` | `fetch { "feasible": $ra.feasible };` |
| `is_set_lifecycle_state_feasible` | `fetch $ra: feasible;` | `fetch { "feasible": $ra.feasible };` |
| `fetch_tactic_rule_impacts_fulfillment` | `fetch $fulfillment;` | `fetch { "fulfillment": $fulfillment };` |
| `fetch_tactic_rule_impacts_requirement` | `fetch $fulfillment;` | `fetch { "fulfillment": $fulfillment };` |
| `fetch_resulting_effect_value` | `fetch $resulting_effect_value;` | `fetch { "resulting_effect_value": $resulting_effect_value };` |
| `fetch_fuzzy_membership_degree` | `fetch $membership_degree;` | `fetch { "membership_degree": $membership_degree };` |
| `fetch_relaxed_expression_fulfillment` | `fetch $fulfillment;` | `fetch { "fulfillment": $fulfillment };` |
| `fetch_all_requirements` | `fetch $req: requirement_name;` | `fetch { "requirement_name": $req.requirement_name };` |
| `fetch_all_expressions` | `fetch $expr: expression_name;` | `fetch { "expression_name": $expr.expression_name };` |
| `get_expression_satisfied` | `fetch $expression_satisfied;` | `fetch { "expression_satisfied": $expression_satisfied };` |
| `fetch_potential_requirements_fulfillment` | `fetch $rule_name; $fulfillment; $requirement_name;` | `fetch { "rule_name": $rule_name, "fulfillment": $fulfillment, "requirement_name": $requirement_name };` |
| `fetch_potential_requirements_fulfillment_for_resolution_model` | same | same |

> **Note on `fetch_measures_interfaces` and `fetch_latest_measurement`:** These contain sub-fetch blocks using TypeDB 2 syntax. TypeDB 3 supports sub-fetch via pipeline stages. Rewrite these carefully:
> - `fetch_latest_measurement`: The nested `double_value: { match ...; fetch $value; }` pattern needs to be rewritten. Check TypeDB 3 docs for sub-fetch syntax. Alternatively, restructure into multiple top-level queries.
> - `fetch_measures_interfaces`: The `qos_sub_query: { match ...; fetch $qos: ...; };` pattern needs the same treatment.

**Step 2: Run flake8**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: PASS.

**Step 3: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: rewrite all fetch queries to TypeDB 3 { } syntax"
```

---

## Task 6: Rewrite all result-parsing helpers for the new flat result format

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Background:** TypeDB 3 `fetch_database()` returns a list of flat Python-native dicts keyed by the fetch projection names. The old format `result[var][attr][0]['value']` is dead. The new format is `result['key']` where `'key'` matches the string used in the fetch projection.

**Step 1: Rewrite `node_query_to_node_dict`**

This is the most-used result parser; getting it right first unblocks many other methods.

Old code (lines 82–105):
```python
def node_query_to_node_dict(
        query_result: List[dict[str, MatchResultDict]],
        node_variable: str = 'node') -> List[RuntimeNodeDict]:
    node_dict = []
    for result in query_result:
        node = result.get(node_variable)
        if len(node['namespace']) > 1:
            ...
        node_dict.append({
            'node_name': node['node_name'][0]['value'],
            'namespace': node['namespace'][0]['value'],
        })
    node_dict.sort(key=lambda d: (d['node_name'], d['namespace']))
    return node_dict
```

New code:
```python
def node_query_to_node_dict(
        query_result: List[dict]) -> List[RuntimeNodeDict]:
    """Convert fetch query results to a list of node dicts.

    :param query_result: list of fetch result dicts with 'node_name' and 'namespace' keys.
    :return: list of RuntimeNodeDict sorted by node_name then namespace.
    """
    node_dict = []
    for result in query_result:
        node_dict.append({
            'node_name': result['node_name'],
            'namespace': result['namespace'],
        })
    node_dict.sort(key=lambda d: (d['node_name'], d['namespace']))
    return node_dict
```

Note: the `node_variable` parameter is removed because the new fetch queries use explicit string keys, not entity variable names.

**Step 2: Update all callers of `node_query_to_node_dict`**

The old signature had an optional `node_variable` parameter (e.g., `node_query_to_node_dict(result, 'subnode')`). Since the new fetch queries all use `"node_name"` and `"namespace"` as the projection keys regardless of which entity variable was used in the query, the second argument is no longer needed. Remove the argument from all call sites:

- `get_subnodes`: `node_query_to_node_dict(self.fetch_subnodes(...), 'subnode')` → `node_query_to_node_dict(self.fetch_subnodes(...))`
- `get_action_clients_nodes`: remove `'node'` arg
- `get_action_server_nodes`: remove `'node'` arg
- `get_connected_action_server_nodes`: remove `'server_node'` arg
- `get_connected_subscriber_nodes`: remove `'subscriber_node'` arg
- `get_neighbours`: remove `'neighbour'` arg
- `get_connected_nodes`: remove `'connected'` arg

**Step 3: Rewrite `get_action_clients_names` result parsing**

Old parsing (lines ~277–299):
```python
action['interface_name'][0]['value']
action['interface_type'][0]['value']
```

New parsing (keys match the fetch projection from Task 5):
```python
result['interface_name']   # plain str
result['interface_type']   # plain str
```

Rewrite `get_action_clients_names`:
```python
def get_action_clients_names(self, node_name, namespace=''):
    ...
    ros_action_result_dict = []
    for result in self.fetch_action_clients_names(node_name, namespace):
        ros_action_result_dict.append({
            'action_name': result['interface_name'],
            'action_type': result['interface_type'],
        })
    ros_action_result_dict.sort(key=lambda d: (d['action_name'], d['action_type']))
    return ros_action_result_dict
```

Apply the same pattern to `get_action_server_names` if it exists.

**Step 4: Rewrite simple single-value parsers**

All methods of the form `query_result[0][var][attr][0]['value']` become `query_result[0]['key']`.

| Method | Old | New |
|---|---|---|
| `get_tactics` | `result['tactic']['tactic_name'][0]['value']` | `result['tactic_name']` |
| `get_all_tactic_rules` | `result['tactic_rule']['rule_name'][0]['value']` | `result['rule_name']` |
| `get_applicable_tactics` | `result['tactic_rule']['rule_name'][0]['value']` | `result['rule_name']` |
| `get_relaxed_requirement_fulfillment` | `[...][0]['fulfillment']['value']` | `query_result[0]['fulfillment']` |
| `get_in_effect_requirement_fulfillment` | `result['req']['requirement_name'][0]['value']`, `result['req']['fulfillment'][0]['value']` | `result['requirement_name']`, `result['fulfillment']` |
| `get_requirement_in_effect` | `query_result[0]['req']['in_effect'][0]['value']` | `query_result[0]['in_effect']` |
| `get_tactic_rule_valid` | `query_result[0]['tr']['rule_valid'][0]['value']` | `query_result[0]['rule_valid']` |
| `is_feature_selectable` | `query_result[0]['f']['selectable'][0]['value']` | `query_result[0]['selectable']` |
| `is_node_running` | `query_result[0]['node']['running'][0]['value']` | `query_result[0]['running']` |
| `is_set_nodes_parameters_feasible` | `query_result[0]['ra']['feasible'][0]['value']` | `query_result[0]['feasible']` |
| `is_set_lifecycle_state_feasible` | `query_result[0]['ra']['feasible'][0]['value']` | `query_result[0]['feasible']` |
| `get_tactic_rule_impacts_requirement` | `result['fulfillment']['value']` | `result['fulfillment']` |
| `get_resulting_effect_value` | `query_result[0]['resulting_effect_value']['value']` | `query_result[0]['resulting_effect_value']` |
| `get_fuzzy_membership_degree` | `query_result[0]['membership_degree']['value']` | `query_result[0]['membership_degree']` |
| `get_relaxed_expression_fulfillment` | `query_result[0]['fulfillment']['value']` | `query_result[0]['fulfillment']` |
| `get_all_requirements` | `result['req']['requirement_name'][0]['value']` | `result['requirement_name']` |
| `get_all_expressions` | `result['expr']['expression_name'][0]['value']` | `result['expression_name']` |
| `get_expression_satisfied` | `query_result[0]['expression_satisfied']['value']` | `query_result[0]['expression_satisfied']` |

**Step 5: Rewrite `_build_requirement_impact_dicts`**

Old (lines ~1368–1375):
```python
return [
    RequirementImpactDict(
        action_name=action_name,
        tactic_rule=result['rule_name']['value'],
        requirement_name=result['requirement_name']['value'],
        fulfillment=result['fulfillment']['value']
    ) for result in query_result
]
```

New:
```python
return [
    RequirementImpactDict(
        action_name=action_name,
        tactic_rule=result['rule_name'],
        requirement_name=result['requirement_name'],
        fulfillment=result['fulfillment']
    ) for result in query_result
]
```

**Step 6: Rewrite `get_latest_measurement` and `get_measures_interfaces`**

These are the most complex parsers. The approach depends on how the sub-fetch queries are rewritten in Task 5. After rewriting those queries, update the Python parsing to match the new key names returned by TypeDB 3.

For `get_latest_measurement`, the result will no longer be nested sub-lists. The new structure depends on how the sub-fetch is written. If the measurement type branches are turned into separate queries, then each branch returns a single value or empty list. Update `get_latest_measurement` accordingly.

For `get_measures_interfaces`, the `get_first_value` helper and all the `result.get('source').get('type').get('label')` calls must be rewritten. In TypeDB 3, `source` will be the type string directly, not a nested dict. Re-examine the new fetch query output shape carefully before rewriting this method.

**Step 7: Run flake8**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: PASS.

**Step 8: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: update result parsers for TypeDB 3 flat dict format"
```

---

## Task 7: Update aggregate and select query syntax

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

**Background:** TypeDB 3 replaces `get $var; count;` with `select $var; reduce $c = count;`. Also `get $var;` becomes `select $var;`.

**Step 1: Find all aggregate and get queries**

```bash
grep -n 'get \$\|count;\|sum \$' \
  typedb_tactics/typedb_tactical_retreat_interface.py
```

**Step 2: Rewrite `does_tactic_affect_nodes`**

Old query (lines ~456–470):
```typeql
...
get $node;
count;
```

New query:
```typeql
...
select $node; reduce $c = count;
```

And update the result check. `get_aggregate_database` in TypeDB 3 returns an int directly:
```python
return (self.db.get_aggregate_database(query) or 0) > 0
```

**Step 3: Rewrite any other `get $var;` that feeds `get_aggregate_database`**

Check all `self.db.get_aggregate_database(...)` call sites. Ensure each query uses `select $var; reduce $c = count;` (or the equivalent sum/min/max reduce form).

**Step 4: Run flake8**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "refactor: update aggregate and select query syntax for TypeDB 3"
```

---

## Task 8: Update test fixtures — remove sort_fetch_results

**Files:**
- Modify: `test/test_tactical_retreat_interface.py:37`
- Modify: `test/test_ros_model.py:32`
- Modify: all other test files that pass `sort_fetch_results=True` to `TacticalRetreatInterface`

**Step 1: Find all test fixtures with sort_fetch_results**

```bash
grep -rn 'sort_fetch_results' test/
```

**Step 2: Remove `sort_fetch_results=True` from each fixture**

For each occurrence, remove the argument. Example for `test/test_tactical_retreat_interface.py`:

```python
# OLD
kb_interface = TacticalRetreatInterface(
    'localhost:1729',
    'test_model_interface',
    [...schemas...],
    [...data...],
    force_database=True,
    force_data=True,
    infer=True,
    sort_fetch_results=True)

# NEW
kb_interface = TacticalRetreatInterface(
    'localhost:1729',
    'test_model_interface',
    [...schemas...],
    [...data...],
    force_database=True,
    force_data=True,
    infer=True)
```

**Step 3: Add explicit sort after fetches in tests that assert positional order**

Any test that asserts `result[0]['node_name'] == 'some_node'` relies on deterministic ordering that was previously guaranteed by `sort_fetch_results`. Now sort explicitly in the test or call a method that already sorts (like `node_query_to_node_dict`, which sorts by `node_name`):

```python
# If a test calls a `get_*` method that already sorts internally, no change needed.
# If a test calls a `fetch_*` method and checks order, sort first:
results = kb_interface.fetch_something(...)
results.sort(key=lambda r: r['node_name'])
assert results[0]['node_name'] == 'expected'
```

Inspect each failing test to determine if sorting is needed.

**Step 4: Run pep257**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_pep257'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add test/
git commit -m "test: remove sort_fetch_results from fixtures, sort in Python where needed"
```

---

## Task 9: Audit and update schema files for TypeDB 3 syntax

**Files:**
- Modify: `schemas/ros_model/ros_model.tql` and other schema files as needed

**Background:** TypeDB 2 schema syntax (`sub attribute, value string;`) is invalid in TypeDB 3. Check each schema file.

**Step 1: Identify TypeDB 2 syntax in schemas**

```bash
grep -rn 'sub attribute\|sub entity\|sub relation' schemas/
```

**Step 2: Update attribute definitions**

TypeDB 2 → TypeDB 3:

```typeql
# TypeDB 2
node_name sub attribute, value string;
depth sub attribute, value long;

# TypeDB 3
attribute node_name, value string;
attribute depth, value long;
```

**Step 3: Check `owns` for multi-valued attributes**

In TypeDB 3, if an entity can own multiple values of the same attribute type, add `@card(0..)`:

```typeql
# TypeDB 3 — multiple start_time values allowed
ROSNode owns start_time @card(0..);
```

For single-valued attributes, `@card(1)` or no annotation (default is single value). Check the data and tests to determine cardinality.

**Step 4: Update entity and relation definitions if needed**

TypeDB 3 relation syntax may differ — check TypeDB 3 docs at https://typedb.com/docs/ for the current define block syntax.

**Step 5: Test schema loads inside container**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_ros_model'
```

Expected: PASS (or only assertion failures due to result format — not schema load errors).

**Step 6: Commit**

```bash
git add schemas/
git commit -m "fix: update schema files to TypeDB 3 define syntax"
```

---

## Task 10: Run the full test suite and fix remaining failures

**Files:**
- Modify: any file with remaining failures

**Step 1: Run the full test suite inside the container**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics'
```

Expected: all tests PASS. Allow ~10 minutes.

**Step 2: For each failing test, diagnose using the migration failure checks**

Consult `docs/agent-notes.md` section "TypeDB 3 migration failure checks":

- Empty fetch result or `KeyError` → fetch query still uses TypeDB 2 syntax
- `TypeError` on `[0]['value']` → result parsing not yet updated
- `None` from aggregate → `select`/`reduce` syntax not applied
- `AttributeError: sort_fetch_results` → `sort_fetch_results` arg not yet removed from a test fixture
- `ImportError` → import path not updated
- Schema error → schema file still uses TypeDB 2 syntax

Fix each failure, run flake8 + pep257 after each fix, commit.

**Step 3: Run lint gates**

```bash
docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_flake8'

docker exec tactical_retreat bash -lc \
  'source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws && \
   colcon test --event-handlers console_cohesion+ \
   --packages-select typedb_tactics --pytest-args -k test_pep257'
```

Both must PASS before declaring the migration complete.

**Step 4: Final commit**

```bash
git add -A
git commit -m "fix: resolve remaining TypeDB 3 migration failures, all tests pass"
```
