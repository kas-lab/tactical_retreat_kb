# Suggested commands

## Environment setup

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

## Build

```bash
colcon build --symlink-install
```

## Focused tests

```bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_relaxed_model
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_ros_model
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_hyp
```

## Mandatory lint/style gates

```bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_flake8
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics --pytest-args -k test_pep257
```

## Full package tests

```bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics
```

## Docker workflow

```bash
cd <workspace_root>
docker build --secret id=gh_token,src=<(gh auth token) --build-arg DEPS_CACHE_BUSTER=${date} -t tactical_retreat .
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v "$PWD/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics" -v "$PWD/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors" tactical_retreat typedb server
docker exec tactical_retreat bash -lc 'source /opt/ros/humble/setup.bash && source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics'
scripts/run-tests-docker.sh -k test_hyp
```

## Benchmarks

```bash
python3 scripts/benchmark.py --runs 1 --methods get_potential_requirements_fulfillment
python3 scripts/benchmark_queries.py --profiles hyp --runs 5
```

## Schema diagrams

```bash
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py
```

## Run the node

```bash
ros2 run typedb_tactics tactical_retreat
ros2 launch typedb_tactics tactical_retreat_kb.launch.py schema_path:="['schemas/data_structure/data_structure.tql','schemas/context_model/context_model.tql','schemas/ros_model/ros_model.tql']" data_path:="['test/data/test_ros_model.tql']" database_name:=tactical_kb address:=localhost:1729 force_database:=True force_data:=True infer:=True
```

## Useful Linux/project commands

```bash
git status
rg PATTERN
rg --files
find . -maxdepth 2 -type f
ls
cd <workspace_root>/src/typedb_tactics
```
