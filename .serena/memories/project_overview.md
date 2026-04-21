# typedb_tactics overview

- Purpose: ROS 2 Humble `ament_python` package for managing self-adaptive systems at runtime using TypeDB as the knowledge base.
- Core idea: capture adaptation knowledge in TypeDB schemas and query it at runtime to decide when and how a ROS-based managed system should adapt.
- Main domains modeled in `schemas/`: data structures, context model, ROS graph/runtime model, feature model, logical/fuzzy expressions, RELAX requirements, tactics model, tactic discovery, and hypothetical requirement fulfillment.
- Main runtime Python API: `typedb_tactics/typedb_tactical_retreat_interface.py` defines `TacticalRetreatInterface`, which wraps TypeDB queries and returns structured Python/ROS results.
- Main ROS node: `typedb_tactics/tactical_retreat_kb.py` defines `TacticalRetreatKB`, a lifecycle node built on top of `ros_typedb` integration.
- Console entrypoint: `tactical_retreat = typedb_tactics.tactical_retreat_node:main`.
- Launch entrypoint: `launch/tactical_retreat_kb.launch.py` starts the lifecycle KB node with schema/data/database/address/inference arguments.
- Key external dependencies: TypeDB 2.28.x, TypeDB Python driver 2.28.x, ROS 2 Humble, `ros_typedb`, `ros_typedb_msgs`, `adapt_x_msgs`, `geometry_msgs`, `ros_monitors_functions`, `rebet_monitors`.
- Important runtime assumption: tests and the KB node expect a running TypeDB server at `localhost:1729` unless configured otherwise.
- Cross-repo note: `typedb_tactics` can depend on API details from `ros_typedb`; constructor/fetch changes must stay compatible with the installed or overlay version.