# Agent guide

This file provides guidance for Agents to work with this repository

## Project overview

This project is about implementing a managing system, in the context of self-adaptive systems, to manage ROS 2-based systems at runtime. The main idea is to capture all the knowledge required by the managing system with TypeDB and then query TypeDB at runtime to decide when and how the managed system should be adapted. The schema folder contains all TypeDB meta-models, and `tactical_retreat_kb` contain the python scripts used to interact with TypeDB. The code is packaged as a ROS 2 package.

In summary the main meta-models needed for adaptation are:

- Variability model: Captures how the possible variability of the managed system, in this work we use Feature Models for this. For example, it captures how the parameters of a Node can be varied, or which combinations of nodes can be active at the same time.
- Requirements model: Express the managed system requirements
- Context model: represents the runtime context
- Runtime ROS graph: represents the runtime ROS graph
- Adaptation plan model: represents which tactics can be applied to adapt the system

## Dependencies and environment

- TypeDB 2.28.3
- TypeDB python driver 2.28.0
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

From the workspace root:

```Bash
source install/setup.bash
```

If you are working from `src/tactical_retreat_kb` instead of the workspace root, the equivalent command is:

```Bash
source ../../install/setup.bash
```

Build repo:

```Bash
colcon build --symlink-install
```

Test the whole repo:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb
```

Run specific tests:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_relaxed_model
```

```Bash
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_ros_model
```

And so on.

**Testing note:** Running the full test suite takes ~10 minutes and most of that time is spent setting up the KB/TypeDB. Prefer running only the relevant tests for the module you changed (e.g., if you change the relaxed model, run `test_relaxed_model`).

**Mandatory lint/style gate (all agent changes):** Before considering work complete, always run `test_flake8` and `test_pep257` and ensure both pass. This is required even if you already ran focused functional tests.

Local:

```Bash
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_flake8
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_pep257
```

Docker (`tactical_retreat`):

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_flake8'
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_pep257'
```

**TypeDB note:** Tests and the KB node expect a running TypeDB server (default `localhost:1729`). Start TypeDB before running tests.

## Fetch ordering policy

- Runtime fetches should be unordered by default for performance.
- Use `sort_fetch_results=True` when constructing `TacticalRetreatInterface` in tests that rely on deterministic result order.
- Prefer `fetch_database_unordered(...)` in hot-path query methods.
- Use ordered fetches only when deterministic ordering is required for assertions/debugging.

## Cross-repo compatibility (tactical_retreat_kb + ros_typedb)

- Changes in `tactical_retreat_kb` may depend on API changes in `ros_typedb` (`TypeDBInterface`).
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
- **Portable mounts:** prefer running Docker commands from the workspace root and mounting packages via `"$PWD/src/..."` instead of hard-coded host paths.

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
ros2 launch tactical_retreat_kb tactical_retreat_kb.launch.py \
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

Start container in the background with TypeDB server running and mounting the packages `tactical_retreat_kb` and `ros_monitors`:

```Bash
cd <workspace_root>
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v "$PWD/src/tactical_retreat_kb:/home/ubuntu-user/tactical_retreat_ws/src/tactical_retreat_kb" -v "$PWD/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors" tactical_retreat typedb server
```

Start new terminal in the container:

```Bash
docker exec -it tactical_retreat bash
```

Run tests in the container:

```Bash
docker exec -it tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb'
```

If running from a non-interactive environment, drop `-it`:

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb'
```

Run a focused test selection:

```Bash
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb --pytest-args -k test_hyp'
```

## Information on TypeDB 2

the documentation for typedb2 lives here: https://typedb.com/docs/home/2.x/

## Agent helpers

- `docs/agent-notes.md` has a quick checklist and common failure checks.
- `scripts/README.md` explains how to run the helper scripts in `scripts/`.
- `scripts/run-tests-docker.sh` runs tests in the `tactical_retreat` container (supports `-k`).
- `scripts/generate_schema_diagrams.py` generates one diagram per schema.
- `scripts/generate_merged_schema_diagram.py` generates one merged schema diagram, with default ignores for the discovery schemas.
- `scripts/benchmark.py` benchmarks `get_*` interface methods and `get_expression_satisfied`.
- `scripts/benchmark_queries.py` benchmarks schema/data init and focused query latency by profile.
