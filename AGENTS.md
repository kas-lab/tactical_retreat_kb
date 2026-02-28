# Agent guide

This file provides guidance for Agents to work with this repository

## Project overview

This project is about implementing a managing system, in the context of self-adaptive systems, to manage ROS 2-based systems at runtime. The main idea is to capture all the knowledge required by the managing system with TypeDB and then query TypeDB at runtime to decide when and how the managed system should be adapted. The schema folder contains all TypeDB meta-models, and `typedb_tactics` contain the python scripts used to interact with TypeDB. The code is packaged as a ROS 2 package.

In summary the main meta-models needed for adaptation are:

- Variability model: Captures how the possible variability of the managed system, in this work we use Feature Models for this. For example, it captures how the parameters of a Node can be varied, or which combinations of nodes can be active at the same time.
- Requirements model: Express the managed system requirements
- Context model: represents the runtime context
- Runtime ROS graph: represents the runtime ROS graph
- Adaptation plan model: represents which tactics can be applied to adapt the system

## Dependencies and environment

- TypeDB **3.x** (target; was TypeDB 2.28.3 on the `optimizations` branch)
- TypeDB Python driver: **`typedb-driver`** (PyPI, 3.x series; was `typedb-client==2.28.0`)
- Python dependencies:
  - setuptools==75.8.2
  - packaging==24.1
  - empy==3.3.4
  - pandas==2.0.2
  - scipy==1.15.2
  - numpy==1.23.5
- ROS 2 Humble
- ROS dependencies: check `package.xml` and `dependencies.repos`

## Common commands

Source ROS and workspace before anything:

```Bash
source /opt/ros/humble/setup.bash
```

From the workspace folder:

```Bash
source ../../install/setup.bash
```

Build repo:

```Bash
colcon build --symlink-install
```

Test the whole repo:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics
```

Run specific tests:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_relaxed_model
```

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_ros_model
```

And so on.

**Testing note:** Running the full test suite takes ~10 minutes and most of that time is spent setting up the KB/TypeDB. Prefer running only the relevant tests for the module you changed (e.g., if you change the relaxed model, run `test_relaxed_model`).

**Mandatory lint/style gate (all agent changes):** Before considering work complete, always run `test_flake8` and `test_pep257` and ensure both pass. This is required even if you already ran focused functional tests.

Local:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_pep257
```

Docker (`tactical_retreat`):

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8'
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_pep257'
```

**TypeDB note:** Tests and the KB node expect a running TypeDB server (default `localhost:1729`). Start TypeDB before running tests.

## Fetch ordering policy

- TypeDB 3 does not guarantee result order. `sort_fetch_results` and `fetch_database_unordered` are removed.
- If a test relies on deterministic result order, sort in Python after fetching (e.g., `results.sort(key=lambda d: d['node_name'])`).
- Do not add `sort_fetch_results` to `TacticalRetreatInterface.__init__` — it no longer exists.

## Cross-repo compatibility (typedb_tactics + ros_typedb)

- Changes in `typedb_tactics` may depend on API changes in `ros_typedb` (`TypeDBInterface`).
- If constructor or fetch API changes are introduced (e.g., `sort_fetch_results`, `sort_result`), verify compatibility with the installed/overlay version used in Docker.
- Typical mismatch symptom: `TypeError` in `TacticalRetreatInterface.__init__` due to argument count/signature drift.

## TypeDB rules: common pitfalls

- **Relation creation vs attribute assignment:** you cannot create a new relation and assign attributes to it in the same `then` clause. Create the relation in one rule, then assign attributes in another rule, or bind the relation in the `when` and only add attributes in the `then`.
- **Variables in `then`:** any variable used in the `then` must be bound in the `when` **outside nested patterns** (e.g., not only inside `or {}` or `not {}` blocks). Otherwise you will get `[TQL33]`.
- **Negation cycles:** if a rule both reads and writes the same predicate under `not {}`, TypeDB rejects it (`[RUW02]`). Stratify by writing to a different relation/attribute layer and then copy results in a positive rule.
- **Minimal schema edits:** prefer subtyping existing relations over adding parallel relations, to keep fetch/query code stable.

## Docker test tips

- **Container running:** `docker exec` fails if the container is not running. Check `docker ps` or start the container first.
- **Non-interactive exec:** for CI/agents, prefer `docker exec tactical_retreat ...` (no `-it`).
- **Timeouts:** schema-heavy `colcon test` runs can exceed default agent timeouts; allow 5–7 minutes.

## Benchmark protocol

- For quick method hotspot iteration:
  - `python3 scripts/benchmark.py --runs 1 --methods get_potential_requirements_fulfillment`
- For query + initialization decomposition:
  - `python3 scripts/benchmark_queries.py --profiles hyp --runs 5`
- Do not claim performance gains from a single run; use `--runs > 1` and compare p50/p95 and row stability.
- Keep inference enabled for production-representative checks unless explicitly doing an infer/no-infer comparison.

## Performance acceptance checklist

- Relevant tests pass for changed modules.
- Target query row counts are stable across warm runs.
- No regression in `fetch_potential_requirements_fulfillment` / `get_potential_requirements_fulfillment` on `hyp` profile.
- If schema/rules changed, compare before/after with both:
  - `scripts/benchmark.py` (real interface method path)
  - `scripts/benchmark_queries.py` (bottleneck attribution)

## Run the KB node

Ensure a TypeDB server is running, then launch the lifecycle KB node:

```Bash
ros2 launch typedb_tactics tactical_retreat_kb.launch.py \
  schema_path:="['schemas/data_structure/data_structure.tql','schemas/context_model/context_model.tql','schemas/ros_model/ros_model.tql']" \
  data_path:="['test/data/test_ros_model.tql']" \
  database_name:=tactical_kb \
  address:=localhost:1729 \
  force_database:=True \
  force_data:=True \
  infer:=True
```

Adjust `schema_path` and `data_path` for your use case (paths can be absolute or relative to the package root).

## Architecture

### TypeDB interface

The `typedb_tactical_retreat_interface.py` python script defines the `TacticalRetreatInterface` class which is used to encapsulate the logic to interact with the TypeDB database. It mostly contain methods that wrap TypeDB queries and return the query results in a structured way.

The `tactical_retreat_kb.py` python script defines the `TacticalRetreatKB` class as a subclass of `ROSTypeDBInterface` which is a subclass of a lifecycle ROS Node. This class is mainly used to expose the interfaces of `TacticalRetreatInterface` as ROS interfaces (i.e., topics, services, and actions). At runtime, this node is the one that manages the database. Other nodes in the system request reading/writing data via the exposed ROS interfaces.

### TypeDB Schemas

Located in the folder `schemas` and its subfolder.

#### Data structure schema

Located in the folder `schemas/data_structure`
This schema represents the basic data structures used in this project to represent boolean, double, integer, and string values; `ValueBool`, `ValueDouble`, `ValueInteger`, and `ValueString` respectively. Also it represents arrays of values with `ValueArray`.

#### Context model Schema

Located in the folder `schemas/context_model`
This schema captures how to measurements of the system and environment variables.

Entities:

- `Measure`: represents a measure of the system or environment

Relations:

- `measurement`: represents a runtime measurement of a Measure at a specific timestamps
- `measurement_interface`: represents which interface is used to get the measurements from, and which functions `measurement_function_name`, function library `measurement_function_lib`, and function arguments `measurement_function_args` are used to turn the raw data into a proper measurement

#### Feature model Schema

Located in the folder `schemas/feature_model`
This schema is used to capture Feature Models

Entities:

- `Feature` represents a Feature in the feature model

Relations:

- `feature_hierarchy` represents that a Feature (role `parent`) is the parent of another Feature (role `child`). The `feature_hierarchy` relation has subtypes `alternative` and `or_group`
  - `alternative` means that only one of the child Features can be selected at a time
  - `or_group` multiple child Features can be selected at the same time
- `cross_tree_constraint` represents constraints in the selection between Features. It has subtypes `excludes_constraint` and `requires_constraint`
  - `excludes_constraint` represents that a Feature (role `constrained`) cannot be selected while another Feature is selected (role `constraint`)
  - `requires_constraint` represents that a Feature (role `constrained`) can only be selected if another Feature is selected (role `constraint`)

#### logical expressions Schema

Located in the folder `schemas/logical_expressions`

We use a multi-sorted, quantifier-free first-order logic over typed state variables, with sorts for booleans, integers, reals, strings, and arrays of these types. Atomic formulas are either comparison predicates between terms (e.g. <, ≤, >, ≥, =, ≠ applied to variables or constants of compatible types) or propositional atoms over boolean terms. Negation is restricted to atomic formulas, yielding negation normal form (NNF). In addition, formulas are constrained to a conjunctive normal form (CNF) shape at the meta-model level: an or_expression (clause) may only relate atomic_expression instances (literals), while an and_expression (conjunction) may only relate atomic_expression instances and or_expression instances. This induces a three-tier expression graph (literals → disjunctions → conjunctions) that is acyclic and stratified, so every well-formed formula denotes a finite conjunction of finite disjunctions of literals (possibly degenerate to a single clause or a single literal), which can be evaluated monotonically by TypeDB rules.

#### fuzzy expressions Schema

Located in the folder `schemas/logical_expressions`

Models fuzzy branching temporal logic~(FBTL). FBTL provides the temporal operators $U$~(until) and $X$~(delay), and defines the path operators $F$ (eventually) and $G$ (always) from them. FBTL also provides the path quantifiers $A$ (for all fullpaths) and $E$ (for at least one fullpath). Each RELAX expression has the form $A\,\pi$, where $\pi$ is a path formula headed by one of $U$, $X$, $F$, or $G$.

#### Relaxed model Schema

Located in the folder `schemas/relaxed`

Represents [RELAX](https://link.springer.com/article/10.1007/s00766-010-0101-0) requirements, i.e., system requirements.

RELAX requirements constrain how the system should behave in all possible execution traces (i.e., all fullpaths) via $A$, and constrain temporal evolution along each fullpath via $\pi$. Exact runtime evaluation under FBTL semantics would require reasoning over the robot--mission state space to account for all fullpaths, and this work does not incorporate such a model (e.g., an MDP as in~\cite{camara2020software}). Post--execution evaluation can be performed over the monitored execution trace.

The time-degeneration process evaluates each RELAX expression pointwise from the current context. For runtime evaluation, it discards the leading path quantifier $A$ and interprets the temporal operators $G$ and $F$ instantaneously, which yields a satisfaction degree for the current time instant. Concretely, it discards $G$ from the formulas produced for the RELAX expressions \emph{SHALL $\phi$} and \emph{MAY $\phi_1$ OR MAY $\phi_2$}. It also discards $F$ from the formulas produced for \emph{AS CLOSE AS POSSIBLE TO $q$ $\phi$}, \emph{AS MANY AS POSSIBLE $\phi$}, and \emph{AS FEW AS POSSIBLE $\phi$}. Under a pointwise semantics, the expression \emph{EVENTUALLY $\phi$} cannot be evaluated at runtime because satisfaction depends on whether $\phi$ holds at some future time, which is not determined by the current context alone. Therefore, \emph{EVENTUALLY $\phi$} is evaluated only post-execution in this work.

Formally, let $u_t(\phi)\in[0,1]$ denote the satisfaction degree of a (time-degenerated) \emph{fuzzy} formula $\phi$ computed from the runtime context at time instant $t$, where $0$ denotes complete violation and $1$ denotes full satisfaction. Crisp propositions are a special case with $u_t(\phi)\in\{0,1\}$. For compound formulas, this work evaluates negation, conjunction, and disjunction as $u_t(\neg\phi)=1-u_t(\phi)$, $u_t(\phi\wedge\psi)=\min(u_t(\phi),u_t(\psi))$, and $u_t(\phi\vee\psi)=\max(u_t(\phi),u_t(\psi))$. Time-degeneration is applied as a syntactic rewrite on the original FBTL formula. It drops the leading path quantifier and interprets temporal operators instantaneously, namely $A\,\pi \mapsto \pi$, $G\,\phi \mapsto \phi$, and $F\,\phi \mapsto \phi$. The runtime evaluator then computes $u_t(\phi)$ on the resulting degenerated formula $\phi$. Take \Cref{req:velocity} as an example, the time-degenerated satisfaction degree would be defined as $u_{R.1}(\neg objectClose \vee (\Delta(p) - 0.18) \in S) = max(1 - u_t(objectClose), u_t((\Delta(p) - 0.18) \in S))$.

#### ROS model schema

Located in the folder `schemas/ros_model`

Defines a meta-model for ROS Systems. To enable the representation of a runtime ROS graph, including which Nodes are running and how they interface with each other.

#### Tactics model schema

Located in the folder `schemas/tactics_model`

Defines which Tactics can be applied to the Self-adaptive system, including its preconditions (`antecedent`), the reconfiguration actions it triggers (`consequent`), and its expected effects on the runtime measurements (`effect`)

#### Discover tactics model schema

Located in the folder `schemas/discover_tactics_model`

The schema represents the logic to restrict the adaptation loop to tactic rules that can affect the managed actions. The procedure derives the set of ROS nodes reachable from the node that exposes the action interface, either as an action server or as an equivalent service abstraction, using the runtime ROS graph stored in the knowledge base. It then evaluates the consequent of each tactic rule by mapping it to its resolution action(s) and target node(s), and it selects the rules that target at least one node in the reachable set.

#### Discover hypothetical requirement fulfillment

Located in the folder `schemas/discover_hypothetical_req_fulfillment`

This schema captures the logic to calculate what would be the expected fulfillment of requirements when tactic rules are applied to the system. This is done for each pair of requirement and tatic rule. This allows us to select the tactic rule that would maximizes an objective function over the requirement fulfillments, e.g., the tactic rule that is expected to result in the higher average requirement fulfillment when executed.

## Docker

Build:

```Bash
docker build --secret id=gh_token,src=<(gh auth token) --build-arg DEPS_CACHE_BUSTER=${date} -t tactical_retreat .
```

Start container in the background with TypeDB server running and mounting the packages `typedb_tactics` and `ros_monitors`:

```Bash
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics -v $HOME/ros_workspaces/tactical_retreat_ws/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors tactical_retreat typedb server
```

Start new terminal in the container:

```Bash
docker exec -it tactical_retreat bash
```

Run tests in the container:

```Bash
docker exec -it tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics'
```

If running from a non-interactive environment, drop `-it`:

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics'
```

Run a focused test selection:

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_hyp'
```

## Information on TypeDB 2

The documentation for TypeDB 2 lives at https://typedb.com/docs/home/2.x/ — use this only as a historical reference. The target for this project is TypeDB 3.

## TypeDB 3 Migration

This section documents all changes required to migrate `typedb_tactics` from TypeDB 2 to TypeDB 3. The primary file being migrated is `typedb_tactics/typedb_tactical_retreat_interface.py` (1471 lines). Tests and any TypeDB 2 schema files also need updating.

### Dependencies update

| | TypeDB 2 | TypeDB 3 |
|---|---|---|
| Server version | 2.28.3 | 3.x |
| Python driver (PyPI) | `typedb-client==2.28.0` | `typedb-driver` (latest 3.x) |
| TypeDB 3 docs | — | https://typedb.com/docs/ |

### Files that need changing

- `typedb_tactics/typedb_tactical_retreat_interface.py` — all 9 changes below apply here
- `test/test_ros_model.py`, `test/test_kb.py`, and all other test files that construct `TacticalRetreatInterface` or parse fetch results
- Schema files in `schemas/` — audit each; `ros_model.tql` and others still use TypeDB 2 `sub attribute, value string` syntax

### Change 0: Dockerfile — update TypeDB server and Python driver versions

The `Dockerfile` hardcodes TypeDB 2 and must be updated before building a new image. Key lines to change:

| Line | Current (TypeDB 2) | Required (TypeDB 3) |
|---|---|---|
| 43 | `typedb=2.28.3` | TypeDB 3.x package — check https://typedb.com/docs/ for the current apt install instructions; the repo URL or GPG key may also differ |
| 46 | `pip3 install typedb-driver==2.28.0` | `pip3 install typedb-driver` (latest 3.x series, no version pin until stable) |
| 50–51 | TypeDB Studio 2.28.0 `.deb` | TypeDB Studio for TypeDB 3 — update URL and version, or remove if Studio is not required for testing |
| 38–44 | TypeDB 2 apt repo + GPG key | Verify whether the TypeDB 3 apt repo/key is the same; update if not |

Additionally, **TypeDB 3 is written in Rust** and no longer requires a JVM. Once confirmed, `openjdk-11-jre` (line 27) can be removed from the `apt-get install` block.

**All development, testing, and execution must happen inside the `tactical_retreat` container**, not on the host. The container mounts the source tree at `/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/` (and `ros_monitors` alongside it). The TypeDB server starts automatically as the container's entrypoint (`typedb server`).

Build the updated image (requires a GitHub token for private deps):

```bash
docker build --secret id=gh_token,src=<(gh auth token) \
  --build-arg DEPS_CACHE_BUSTER=$(date +%s) \
  -t tactical_retreat .
```

Start the container (TypeDB server starts automatically):

```bash
docker run -d --rm --name tactical_retreat \
  -v $HOME/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics \
  -v $HOME/ros_workspaces/tactical_retreat_3_ws/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors \
  tactical_retreat typedb server
```

Verify TypeDB 3 is running before running any tests:

```bash
docker exec tactical_retreat bash -lc 'typedb --version'
```

### Change 1: Architecture — inheritance → composition

`TacticalRetreatInterface` currently subclasses `TypeDBInterface`. The new design removes inheritance; a `TypeDBInterface` instance is held as `self.db`.

```python
# OLD (TypeDB 2)
class TacticalRetreatInterface(TypeDBInterface):
    def __init__(self, address, database_name, schema_path=None, data_path=None,
                 force_database=False, force_data=False, infer=False,
                 sort_fetch_results=False):
        self._sort_fetch_results = bool(sort_fetch_results)
        super().__init__(address, database_name, schema_path, data_path,
                         force_database, force_data, infer)

# NEW (TypeDB 3)
class TacticalRetreatInterface:
    def __init__(self, address, database_name, schema_path=None, data_path=None,
                 force_database=False, force_data=False, infer=False):
        self.db = TypeDBInterface(address, database_name, schema_path, data_path,
                                  force_database, force_data, infer)
```

All internal query calls must be updated to route through `self.db`:

| Old call | New call |
|---|---|
| `self.fetch_database(q)` | `self.db.fetch_database(q)` |
| `self.get_database(q)` | `self.db.get_database(q)` |
| `self.get_aggregate_database(q)` | `self.db.get_aggregate_database(q)` |
| `self.insert_database(q)` | `self.db.insert_database(q)` |
| `self.delete_from_database(q)` | `self.db.delete_from_database(q)` |
| `self.update_database(q)` | `self.db.update_database(q)` |
| `self.delete_database()` | `self.db.delete_database()` |

### Change 2: Import paths

```python
# OLD (TypeDB 2) — in typedb_tactical_retreat_interface.py
from ros_typedb.typedb_interface import convert_py_type_to_query_type
from ros_typedb.typedb_interface import convert_query_type_to_py_type
from ros_typedb.typedb_interface import MatchResultDict
from ros_typedb.typedb_interface import TypeDBInterface

# NEW (TypeDB 3)
from ros_typedb.typedb_helpers import convert_py_type_to_query_type   # moved
from ros_typedb.typedb_helpers import convert_query_type_to_py_type   # moved
from ros_typedb.typedb_interface import MatchResultDict                # still here
from ros_typedb.typedb_interface import TypeDBInterface                # still here
```

Also remove the now-unused `import inspect` and `from typedb.driver import ConceptMap` if present.

### Change 3: TypeQL fetch syntax

Every `fetch` query in `typedb_tactical_retreat_interface.py` must be rewritten.

```typeql
# TypeDB 2 — INVALID in TypeDB 3
fetch
    $node: node_name, namespace;

# TypeDB 3 — correct
fetch {
    "node_name": $node.node-name,
    "namespace": $node.namespace
};
```

Note the hyphen in `node-name` vs the underscore in the attribute label as defined in the schema. Use the schema attribute label exactly (e.g., `node_name` → `node-name` only if the schema defines it with a hyphen; check `schemas/ros_model/ros_model.tql` for the actual label).

Multi-attribute fetch with a bound attribute variable:

```typeql
# TypeDB 2
fetch
    $entity: attribute1, attribute2;

# TypeDB 3
fetch {
    "attribute1": $entity.attribute1,
    "attribute2": $entity.attribute2
};
```

Multi-value (array) fetch:

```typeql
# TypeDB 3 — collect multiple values of the same attribute type
fetch {
    "addresses": [$entity.address]
};
```

### Change 4: Fetch result format

`fetch_database()` in TypeDB 3 calls `as_concept_documents()`, returning a list of flat Python-native dicts keyed by the fetch projection names defined in the query.

```python
# TypeDB 2 result — deeply nested with type metadata
result['node']['node_name'][0]['value']       # string value
result['node']['node_name'][0]['type']['label']  # attribute label

# TypeDB 3 result — flat, native Python types
result['node_name']   # plain Python str
result['namespace']   # plain Python str
result['age']         # plain Python int (long in TypeDB maps to int)
result['alive']       # plain Python bool
result['height']      # plain Python float
result['birth-date']  # plain Python str (ISO datetime with nanosecond precision)
```

**Consequence:** every result-parsing function that uses `result[var][attr][0]['value']` must be rewritten. In `typedb_tactical_retreat_interface.py` this includes:

- `node_query_to_node_dict()` — accesses `node['namespace'][0]['value']`; rewrite to `result['namespace']`
- `get_action_clients_names()` — accesses `action['interface_name'][0]['value']`
- Every other method that unpacks fetch results with `[0]['value']`

Example rewrite of `node_query_to_node_dict`:

```python
# OLD
def node_query_to_node_dict(query_result, node_variable='node'):
    node_dict = []
    for result in query_result:
        node = result.get(node_variable)
        node_dict.append({
            'node_name': node['node_name'][0]['value'],
            'namespace': node['namespace'][0]['value'],
        })
    return node_dict

# NEW
def node_query_to_node_dict(query_result):
    node_dict = []
    for result in query_result:
        node_dict.append({
            'node_name': result['node_name'],
            'namespace': result['namespace'],
        })
    return node_dict
```

### Change 5: Aggregate query syntax

```typeql
# TypeDB 2 — INVALID in TypeDB 3
get $node; count;
get $s; sum $s;

# TypeDB 3
select $node; reduce $c = count;
select $s; reduce $total = sum($s);
```

`get_aggregate_database()` in `TypeDBInterface` already handles the TypeDB 3 `reduce` result format. The queries themselves are the only thing to change.

### Change 6: Remove sort_fetch_results

`TypeDBInterface` in TypeDB 3 has no `sort_fetch_results` parameter and no `fetch_database_unordered()` method.

- Remove `sort_fetch_results` from `TacticalRetreatInterface.__init__`
- Remove the overridden `fetch_database()` method in `TacticalRetreatInterface`
- Remove `self._sort_fetch_results` usage
- In tests that relied on `sort_fetch_results=True` for deterministic ordering, sort results in Python after fetching:

  ```python
  # OLD — test fixture
  kb_interface = TacticalRetreatInterface(..., sort_fetch_results=True)

  # NEW — test fixture
  kb_interface = TacticalRetreatInterface(...)

  # NEW — sort after fetch if needed
  results = kb_interface.get_nodes()
  results.sort(key=lambda d: (d['node_name'], d['namespace']))
  ```

### Change 7: `get` query — `get $var;` → `select $var;`

Any TypeQL query with `get $var;` must use `select $var;` in TypeDB 3.

```typeql
# TypeDB 2
match $node isa ROSNode; get $node;

# TypeDB 3
match $node isa ROSNode; select $node;
```

### Change 8: Schema syntax (TypeDB 3)

The existing schemas still use TypeDB 2 syntax. Audit and update each schema file.

```typeql
# TypeDB 2
package sub attribute,
    value string;

# TypeDB 3
attribute package, value string;
```

Multi-valued `owns` requires `@card(0..)`:

```typeql
# TypeDB 3 — entity can own multiple values of this attribute
ROSNode owns start_time @card(0..);
```

Check the TypeDB 3 docs (https://typedb.com/docs/) for the full schema syntax. Read existing schema files carefully before touching them — some may already be partially updated.

### Change 9: MatchResultDict location (unchanged)

`MatchResultDict` has **not** moved; it remains in `ros_typedb.typedb_interface`:

```python
from ros_typedb.typedb_interface import MatchResultDict  # still correct in TypeDB 3
```

### Before/after quick-reference table

| Pattern | TypeDB 2 (old) | TypeDB 3 (new) |
|---|---|---|
| Class definition | `class TacticalRetreatInterface(TypeDBInterface):` | `class TacticalRetreatInterface:` |
| DB instance | `self` (is TypeDBInterface) | `self.db` (holds TypeDBInterface) |
| Fetch call | `self.fetch_database(q)` | `self.db.fetch_database(q)` |
| Import helpers | `from ros_typedb.typedb_interface import convert_*` | `from ros_typedb.typedb_helpers import convert_*` |
| Fetch syntax | `fetch $n: node_name, namespace;` | `fetch { "node_name": $n.node_name, ... };` |
| Result access | `r['node']['node_name'][0]['value']` | `r['node_name']` |
| Aggregate | `get $x; count;` | `select $x; reduce $c = count;` |
| Select | `get $x;` | `select $x;` |
| Sort param | `sort_fetch_results=True` in constructor | Sort in Python after fetch |
| Schema attr | `foo sub attribute, value string;` | `attribute foo, value string;` |

## Agent helpers

- `docs/agent-notes.md` has a quick checklist and common failure checks.
- `scripts/run-tests-docker.sh` runs tests in the `tactical_retreat` container (supports `-k`).
- `scripts/benchmark.py` benchmarks `get_*` interface methods and `get_expression_satisfied`.
- `scripts/benchmark_queries.py` benchmarks schema/data init and focused query latency by profile.
