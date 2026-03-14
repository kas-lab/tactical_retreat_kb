# TypeDB-native connected_nodes + applicable_tactics + potential fulfillment

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Python BFS/composition workarounds and make `get_connected_nodes`, `get_applicable_tactics`, and `get_potential_requirements_fulfillment*` work through TypeDB-native queries on CE 3.8.1.

**Architecture:** Fix the `connected_nodes` schema function to use the "recurse-on-from" tabling pattern (fixed root arg → one table, no WouldBlock deadlock). Then replace each Python workaround method with a single TypeDB query that calls the schema functions directly.

**Tech Stack:** TypeDB CE 3.8.1, TypeQL `fun`, Python typedb-driver 3.x, pytest inside container `tatical_retreat`.

---

## Background

The WouldBlock panic (`executor/read/tabled_functions.rs:91`) was caused by
`connected_nodes_from($node, $prev)` using "recurse-on-to": `$node` varies
across recursive calls, producing N tabled instances that try to read each
other → deadlock. The AGENTS.md fix: always recurse with the **fixed root**,
so there is exactly one table.

Workarounds to remove:
- `fetch_connected_nodes`: Python BFS over `get_neighbours`
- `fetch_applicable_tactics`: Python host lookup + BFS + set intersection
- `fetch_potential_requirements_fulfillment_for_resolution_model`: Python N×M loop
- `fetch_potential_requirements_fulfillment` (no rm): Python loop over all resolution models

---

## Task 1: Fix `connected_nodes` schema function

**Files:**
- Modify: `schemas/discover_tactics_model/discover_tactics_model.tql`

The current functions:

```typeql
fun connected_nodes($node: ROSNode) -> { ROSNode }:
  match
    { let $conn in neighbours($node); }
    or
    { let $next in neighbours($node);
      let $conn in connected_nodes_from($next, $node); };
  return { $conn };

fun connected_nodes_from($node: ROSNode, $prev: ROSNode) -> { ROSNode }:
  match
    { let $conn in neighbours($node); not { $conn is $prev; }; }
    or
    { let $next in neighbours($node); not { $next is $prev; };
      let $conn in connected_nodes_from($next, $node); };
  return { $conn };
```

Replace **both** with a single "recurse-on-from" function (remove `connected_nodes_from` entirely):

```typeql
fun connected_nodes($root: ROSNode) -> { ROSNode }:
  match
    {
      let $nb in neighbours($root);
    } or {
      let $via in connected_nodes($root);
      let $nb in neighbours($via);
    };
  return { $nb };
```

Key difference: the recursive call always passes `$root` (fixed), not `$via`
(varying). TypeDB creates exactly one tabled instance per `$root` value.

**Step 1: Edit the schema file**

Open `schemas/discover_tactics_model/discover_tactics_model.tql`.

Replace the block starting at `fun connected_nodes($node: ROSNode)` through
the end of `fun connected_nodes_from(...)` (the two functions) with:

```typeql
fun connected_nodes($root: ROSNode) -> { ROSNode }:
  match
    {
      let $nb in neighbours($root);
    } or {
      let $via in connected_nodes($root);
      let $nb in neighbours($via);
    };
  return { $nb };
```

**Step 2: Verify the file looks correct**

The schema file should now have: `fun neighbours(...)`, `fun connected_nodes($root: ROSNode)`, `fun interface_hosts(...)`, `fun tactic_rule_consequent_features(...)`, `fun resolution_model_tactic_rules(...)`, `fun tactic_rule_target_nodes(...)`, `fun applicable_tactics(...)`. No `connected_nodes_from` anywhere.

**Step 3: Run the existing tests to confirm they still pass** (schema is reloaded by each test fixture)

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest -q test/test_tactical_retreat_interface.py -k 'test_get_connected_nodes or test_get_neighbours' -v"
```

Expected: 2 PASSED. (The Python BFS workaround still runs at this point; this confirms the schema loads without error.)

---

## Task 2: Replace `fetch_connected_nodes` with TypeDB-native query

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

Current implementation (lines ~600–623) does Python BFS calling
`get_neighbours` in a loop. Replace with a single TypeDB fetch using the
`connected_nodes` schema function.

**Step 1: Replace the method body**

Find `def fetch_connected_nodes(` and replace the entire method body:

```python
    def fetch_connected_nodes(
            self, node_name: str, namespace: str = '') -> List[dict]:
        """
        Fetch the connected nodes of a node.

        :param node_name: node name of the running node
        :param namespace: namespace of the running node
        :return: fetch query result
        """
        query = f"""
            match
                $node isa ROSNode,
                    has node_name '{node_name}',
                    has namespace '{namespace}';
                let $connected in connected_nodes($node);
            fetch {{
                "node_name": $connected.node_name,
                "namespace": $connected.namespace
            }};
        """
        return self._fetch(query)
```

**Step 2: Run the connected_nodes test**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest -q test/test_tactical_retreat_interface.py -k 'test_get_connected_nodes' -v"
```

Expected: 1 PASSED. Result must contain 8 nodes: behavior_server, bt_navigator, bt_navigator_navigate_through_poses_rclcpp, bt_navigator_navigate_to_pose_rclcpp, controller_server, planner_server, relay_node_cmd_vel, velocity_smoother.

If it panics or fails with WouldBlock, investigate before proceeding (it means the schema fix in Task 1 did not take effect — check the DB was actually reloaded).

---

## Task 3: Replace `fetch_applicable_tactics` with TypeDB-native query

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

Current implementation (lines ~643–680) does: fetch host nodes, Python BFS each host, fetch resolution model targets, Python set intersection. Replace with a single TypeDB fetch using the `applicable_tactics` schema function.

**Step 1: Replace the method body**

Find `def fetch_applicable_tactics(` and replace the entire method body:

```python
    def fetch_applicable_tactics(self,
                                 resolution_model: str,
                                 interface_name: str) -> List[dict]:
        """
        Fetch all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface,
                    has interface_name '{interface_name}';
                $rm isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                let $tr in applicable_tactics($interface, $rm);
            fetch {{
                "rule_name": $tr.rule_name
            }};
        """
        return self._fetch(query)
```

Note: `fetch_interface_hosts` and `fetch_resolution_model_tactic_rule_targets`
remain in the class — they are used by other code. Only the
`fetch_applicable_tactics` implementation changes.

**Step 2: Run the applicable_tactics tests**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest -q test/test_tactical_retreat_interface.py -k 'test_get_applicable_tactics' -v"
```

Expected: 1 PASSED. Verified assertions:
- `get_applicable_tactics('rebetmc', '/navigate_to_pose')` == `['MAX', 'MED', 'MIN']`
- `get_applicable_tactics('rebetmc', '/follow_path')` == `['MAX', 'MED', 'MIN']`
- `get_applicable_tactics('rebetmc', '/compute_path_to_pose')` == `[]`
- `get_applicable_tactics('rebetmc', '~/change_state')` == `['MAX', 'MED', 'MIN']`
- `get_applicable_tactics('rebetmc', '~/transition_event')` == `['MAX', 'MED', 'MIN']`
- `get_applicable_tactics('rebetmc', 'odom')` == `[]`

---

## Task 4: Replace `fetch_potential_requirements_fulfillment_for_resolution_model` with single TypeDB query

**Files:**
- Modify: `typedb_tactics/typedb_tactical_retreat_interface.py`

Current implementation (lines ~1455–1486) does: get applicable tactics, get
in-effect requirements, N×M Python loop calling
`fetch_tactic_rule_impacts_requirement` for each pair. Replace with a single
TypeDB query joining applicable tactics, in-effect requirements, and
fulfillment computation.

**Step 1: Replace the method body**

Find `def fetch_potential_requirements_fulfillment_for_resolution_model(` and replace:

```python
    def fetch_potential_requirements_fulfillment_for_resolution_model(
            self,
            action_name: str,
            resolution_model: str
            ) -> List[dict]:
        """
        Fetch potential relaxed requirement fulfillment using a fixed resolution model.

        :param action_name: ROS interface/action name
        :param resolution_model: resolution model name
        :return: fetch query result
        """
        query = f"""
            match
                $interface isa ROSInterface,
                    has interface_name '{action_name}';
                $rm isa resolution_model,
                    has resolution_model_name '{resolution_model}';
                let $tr in applicable_tactics($interface, $rm);
                $req isa relaxed_requirement, has in_effect true;
                let $fulfillment =
                    tactic_rule_impacts_requirement_fulfillment($tr, $req);
            fetch {{
                "rule_name": $tr.rule_name,
                "requirement_name": $req.requirement_name,
                "fulfillment": $fulfillment
            }};
        """
        result = self._fetch(query)
        return self._dedupe_requirement_impact_rows(result)
```

**Step 2: Replace `fetch_potential_requirements_fulfillment` (no resolution_model loop)**

Find `def fetch_potential_requirements_fulfillment(` and replace the method body:

```python
    def fetch_potential_requirements_fulfillment(
            self,
            action_name: str,
            resolution_model: Optional[str] = None
            ) -> List[dict]:
        """
        Fetch all potential relaxed requirement fulfillments per applicable tactic.

        :param action_name: ROS interface/action name
        :param resolution_model: optional resolution model name
        :return: fetch query result
        """
        if resolution_model is not None:
            return self.fetch_potential_requirements_fulfillment_for_resolution_model(
                action_name, resolution_model)

        query = f"""
            match
                $interface isa ROSInterface,
                    has interface_name '{action_name}';
                $rm isa resolution_model;
                let $tr in applicable_tactics($interface, $rm);
                $req isa relaxed_requirement, has in_effect true;
                let $fulfillment =
                    tactic_rule_impacts_requirement_fulfillment($tr, $req);
            fetch {{
                "rule_name": $tr.rule_name,
                "requirement_name": $req.requirement_name,
                "fulfillment": $fulfillment
            }};
        """
        result = self._fetch(query)
        return self._dedupe_requirement_impact_rows(result)
```

**Step 3: Run the targeted fulfillment tests**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k 'potential_requirements_fulfillment'"
```

Expected: tests in `test_hypothetical_req_fulfillment.py` pass with 9 impacts for `/navigate_to_pose`.

---

## Task 5: Run full test suite

**Step 1: Build (symlink-install means no rebuild needed, but verify)**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws && colcon build --symlink-install --packages-select typedb_tactics 2>&1 | tail -5"
```

**Step 2: Run all relevant tests**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics && python3 -m pytest -q test/test_tactical_retreat_interface.py test/test_hypothetical_req_fulfillment.py -v"
```

Expected: all tests in both files pass.

**Step 3: Run the targeted colcon test**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k 'test_get_connected_nodes or test_get_applicable_tactics or potential_requirements_fulfillment'"
```

Expected: all pass, no failures.

---

## Task 6: Run benchmarks — verify no skips

**Step 1: Hot-methods only benchmark**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/scripts/benchmark && python3 benchmark.py --runs 1 --methods get_applicable_tactics,get_potential_requirements_fulfillment,get_potential_requirements_fulfillment_for_resolution_model --max-combinations 1"
```

Expected: output shows timing rows for all three methods, no "SKIPPED" lines.

**Step 2: Default benchmark**

```bash
docker exec tatical_retreat bash -lc "source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/scripts/benchmark && python3 benchmark.py --runs 1 --max-combinations 1"
```

Expected: completes without TypeDB server panic, no container restart, timing rows for all methods.

---

## Task 7: Code review and cleanup

**Step 1: Invoke code reviewer**

Use `superpowers:requesting-code-review` skill to review the changes in:
- `schemas/discover_tactics_model/discover_tactics_model.tql`
- `typedb_tactics/typedb_tactical_retreat_interface.py`

Focus reviewer on:
1. Schema `connected_nodes` uses "recurse-on-from" correctly
2. Python methods no longer contain BFS/composition logic
3. No leftover references to `connected_nodes_from`
4. Query strings are well-formed TypeQL

**Step 2: Fix any reviewer findings**

Address any correctness or style issues before final commit.

**Step 3: Final commit**

```bash
git add schemas/discover_tactics_model/discover_tactics_model.tql
git add typedb_tactics/typedb_tactical_retreat_interface.py
git commit -m "fix: replace Python BFS/composition workarounds with TypeDB-native queries

- Fix connected_nodes schema to use recurse-on-from pattern (single table,
  no WouldBlock deadlock on CE 3.8.1)
- Remove connected_nodes_from function (was recurse-on-to, caused N tables)
- fetch_connected_nodes: now uses TypeDB connected_nodes() directly
- fetch_applicable_tactics: now uses TypeDB applicable_tactics() directly
- fetch_potential_requirements_fulfillment_for_resolution_model: single
  joined query (applicable_tactics + in_effect req + fulfillment)
- fetch_potential_requirements_fulfillment: single query over all resolution
  models; no more Python loop

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
