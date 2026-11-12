# tactical_retreat_kb

`tactical_retreat_kb` is a ROS 2 package that provides the knowledge base (KB) of a managing system for self-adaptive ROS 2 systems. The KB holds the adaptation knowledge (variability, requirements, context, runtime ROS graph and tactics) and answers runtime questions such as "which tactics are valid right now?", "how well are the requirements fulfilled?". These answers are exposed to the rest of the system as ROS services and topics.

The KB is designed to be backend-agnostic: the ROS node only talks to a KB *interface* object, so any knowledge representation can be plugged in as long as it implements the methods the node calls. Currently:

| Backend | Status | Implementation |
|---|---|---|
| **Xtext / EMF models** | **Active, default** | Queries the Java objects of the Xtext DSL models directly via JPype |
| TypeDB | Legacy, currently **not working** | TypeQL schemas + `typedb_tactical_retreat_interface.py` |

## Navigation

- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Xtext Models](#xtext-models)
- [Quick Start](#quick-start)
- [Testing](#testing)
- [Docker](#docker)
- [Legacy TypeDB Backend](#legacy-typedb-backend)
- [Scripts](#scripts)

## Architecture

```text
 other ROS nodes  ──services/topics──▶  TacticalRetreatKB (lifecycle node)
                                             │  self.interface.<method>(...)
                                             ▼
                                  KB interface (pluggable backend)
                                   ├── XText TacticalRetreatInterface   ← in use
                                   └── TypeDB TacticalRetreatInterface  ← legacy
```

- **ROS node**: [`tactical_retreat_kb_xtext.py`](./tactical_retreat_kb/tactical_retreat_kb_xtext.py) defines the `TacticalRetreatKB` lifecycle node. It loads the models when it is created, sets up measurement subscribers and services, and exposes KB queries under `<node_name>/...` (for example `fetch_rules`, `satisfied_rule`, `valid_ranked_tactics`, `fetch_resolutions`, `fetch_plan`,, `fetch_requirements_fulfillment_ineffect`, `update_running`, `update_in_effect`, `update_has_param_value`, `fetch_policy`). It also publishes `requirements`, `fm_configuration` and `context_model`.
- **Xtext interface**: [`xtext_tactical_retreat_interface.py`](./tactical_retreat_kb/xtext_tactical_retreat_interface.py) starts a JVM through [JPype](https://jpype.readthedocs.io/), loads the Xtext models into an EMF `XtextResourceSet`, and evaluates queries directly on the resulting Java objects. Feature model configurations are handled through FeatureIDE. Fuzzy/RELAX requirement fulfillment is computed in Python by [`tactical_retreat_kb/fuzzy/`](./tactical_retreat_kb/fuzzy/).
- **Entry point**: [`tactical_retreat_node.py`](./tactical_retreat_kb/tactical_retreat_node.py) (the `tactical_retreat` executable) runs the Xtext-backed node.

### Adding another KB backend

To use a different knowledge representation, implement a class that provides the same public methods as the Xtext `TacticalRetreatInterface` and instantiate it in `TacticalRetreatKB.__init__` instead of `XTextInterface`.

## Repository Structure

```text
tactical_retreat_kb/
├── tactical_retreat_kb/                     # Main Python package
│   ├── tactical_retreat_node.py             # Executable entry point (Xtext node)
│   ├── tactical_retreat_kb_xtext.py         # ROS lifecycle node (backend-agnostic, uses Xtext interface)
│   ├── xtext_tactical_retreat_interface.py  # Xtext/EMF KB interface (active)
│   ├── fuzzy/                               # Fuzzy sets, fuzzy expressions, RELAX requirement evaluation
│   ├── utils.py
│   ├── tactical_retreat_kb.py               # Legacy TypeDB-based node
│   └── typedb_tactical_retreat_interface.py # Legacy TypeDB interface
├── jars/                    # Java dependencies (Xtext, EMF, FeatureIDE, CoreSense DSLs, ROS tooling) loaded by JPype
├── launch/                  # ROS 2 launch files (currently TypeDB parameters only, see Quick Start)
├── test/
│   ├── models/              # Example Xtext models used by test_xtext_interface.py
│   ├── test_xtext_interface.py
│   ├── typedb_tests/        # Legacy TypeDB tests
│   └── data/                # Legacy TypeDB test data (.tql)
├── schemas/                 # Legacy TypeDB schemas
├── schemas_diagrams/        # Generated diagrams of the TypeDB schemas
├── scripts/                 # Helper scripts (mostly TypeDB-oriented)
├── fuzzy/                   # Plotting scripts for fuzzy membership functions
├── package.xml
├── setup.py
└── README.md
```

The `jars/` folder is installed to the package share directory, and the interface adds `share/tactical_retreat_kb/jars/*` to the JVM classpath at import time.

## Xtext Models

The Xtext backend is configured with one model file per DSL. Each file is passed in as a node parameter:

| Parameter | Extension | Content |
|---|---|---|
| `ros_path` | `.ros` (list) | ROS package/interface specs (messages, services, actions) |
| `ros2_path` | `.ros2` (list) | ROS 2 node models |
| `rossystem_path` | `.rossystem` (list) | The ROS system: which nodes and interfaces make up the managed system |
| `var_path` | `.var` | Variability (feature) model |
| `resolution_path` | `.resolution` | Resolution model: maps features to reconfigurations (parameter changes, lifecycle transitions) |
| `context_path` | `.context` | Context model: measures and where to obtain them |
| `reqs_path` | `.reqs` | RELAX requirements, with fuzzy membership functions |
| `tactics_path` | `.tactics` | Tactics: global and per-action rules, each with a guard and actions |

The node also takes two flags:

| Parameter | Default | Meaning |
|---|---|---|
| `require_nodes_running` | `False` | Whether tactics require their target nodes to be running |
| `verify_parameters` | `False` | Whether parameter values are verified against the model |

[`test/models/`](./test/models/) has a small but complete set of example models.

> **Note:** Use absolute paths. Imports between models (`import "test.var";`) are resolved against each resource's URI, and that resolution fails for relative URIs.

## Quick Start

Requirements:

- ROS 2 Humble/Jazzy
- Java 21 runtime (`openjdk-21-jre`)
- Python: `JPype1`, plus `numpy`, `scipy` and `pandas`
- ROS dependencies: see [`package.xml`](./package.xml) and [`dependencies.repos`](./dependencies.repos)

Build:

```Bash
source /opt/ros/{distro}/setup.bash
colcon build --symlink-install --packages-up-to tactical_retreat_kb
source install/setup.bash
```

The models are loaded in the node constructor, so pass the parameters when you start the node. For example, create a parameters file `kb_params.yaml`:

```yaml
tactical_retreat_kb:
  ros__parameters:
    ros_path: ["/abs/path/models/my.ros", "/abs/path/models/lifecycle_msgs.ros"]
    ros2_path: ["/abs/path/models/my.ros2"]
    rossystem_path: ["/abs/path/models/my.rossystem"]
    var_path: "/abs/path/models/my.var"
    resolution_path: "/abs/path/models/my.resolution"
    context_path: "/abs/path/models/my.context"
    reqs_path: "/abs/path/models/my.reqs"
    tactics_path: "/abs/path/models/my.tactics"
    require_nodes_running: false
    verify_parameters: false
```

Then run the node and bring it through its lifecycle:

```Bash
ros2 run tactical_retreat_kb tactical_retreat --ros-args --params-file kb_params.yaml
ros2 lifecycle set /tactical_retreat_kb configure
ros2 lifecycle set /tactical_retreat_kb activate
```

## Testing

```Bash
colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb
```

Run only the Xtext interface tests, without needing a TypeDB server:

```Bash
colcon test --packages-select tactical_retreat_kb  --pytest-args test/test_xtext_interface.py
```

The lint/style tests (`test_flake8`, `test_pep257`, `test_copyright`) can be selected the same way. The tests under `test/typedb_tests/` belong to the legacy TypeDB backend and are expected to fail at the moment.

## Legacy TypeDB Backend

The package started as a TypeDB-based KB, with the knowledge stored as TypeQL schemas and queried through TypeQL rules. That code is still in the repository but is **out of date and currently not working** with the rest of the system:

- [`tactical_retreat_kb.py`](./tactical_retreat_kb/tactical_retreat_kb.py): node based on `ROSTypeDBInterface` from `ros_typedb`
- [`typedb_tactical_retreat_interface.py`](./tactical_retreat_kb/typedb_tactical_retreat_interface.py): TypeQL query wrappers
- [`schemas/`](./schemas/): TypeDB schemas (`data_structure`, `context_model`, `ros_model`, `feature_model`, `logical_expressions`, `tactics_model`, `feature_adaptation_plan`)
- [`schemas_diagrams/`](./schemas_diagrams/): generated schema diagrams
- [`test/typedb_tests/`](./test/typedb_tests/) and [`test/data/`](./test/data/): tests and data

It targeted TypeDB 2.28.3 with the 2.28.0 Python driver, on a server at `localhost:1729`.
## Scripts

[`scripts/`](./scripts/) holds the helper scripts for schema diagrams, benchmarking, schema-load profiling and running tests in Docker. All except `run-tests-docker.sh` target the legacy TypeDB backend. See [`scripts/README.md`](./scripts/README.md).
