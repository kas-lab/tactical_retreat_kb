# typedb_tactics Scripts

This directory contains helper scripts for benchmarking, profiling, testing, and generating schema diagrams.

## Overview

This folder currently contains scripts for four main purposes:

- Diagram generation:
  - `generate_schema_diagrams.py` creates one figure per schema file.
  - `generate_merged_schema_diagram.py` creates one combined figure from multiple schemas.
- Benchmarking:
  - `benchmark.py` measures `TacticalRetreatInterface` method timings.
  - `benchmark_queries.py` measures schema/data initialization and query bottlenecks.
- Profiling:
  - `profile_schema_load.py` measures how long each schema file takes to load.
- Test execution:
  - `run-tests-docker.sh` runs the `typedb_tactics` test suite inside the `tactical_retreat` Docker container.

The sections below explain how to run each script and what to expect from it.

## Prerequisites

For scripts that import `typedb_tactics` or talk to TypeDB, use the workspace environment first:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Run those commands from the workspace root:

```bash
cd <workspace_root>
```

Many scripts also require a running TypeDB server on `localhost:1729`.

## Recommended Invocation Style

For scripts in this folder, prefer one of these patterns:

From the workspace root:

```bash
python3 src/typedb_tactics/scripts/<script_name>.py ...
```

Or from this directory:

```bash
cd src/typedb_tactics/scripts
python3 <script_name>.py ...
```

## Scripts

### `generate_schema_diagrams.py`

Generates one diagram per schema file into `src/typedb_tactics/schemas_diagrams`.

Default behavior:
- includes real schema `.tql` files
- excludes `queries/`
- excludes `*_example.tql`
- output format is `.svg`
- orientation is vertical

Examples:

```bash
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py --format dot
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py --include-examples --include-queries
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py --orientation horizontal
```

### `generate_merged_schema_diagram.py`

Generates a single merged diagram from multiple schema files.

Default behavior:
- scans `src/typedb_tactics/schemas`
- merges schema-definition `.tql` files
- excludes `queries/`
- excludes `*_example.tql`
- excludes `discover_hypothetical_req_fulfillment.tql`
- excludes `discover_tactics_model.tql`
- output format is `.svg`
- output path defaults to `src/typedb_tactics/schemas_diagrams/merged_schema.svg`

Examples:

```bash
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py --format dot
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py --ignore-schema relaxed_model.tql
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py --include-default-ignored
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py --orientation horizontal
```

### `benchmark.py`

Benchmarks `get_*` methods from `TacticalRetreatInterface`.

This script uses relative schema paths such as `../schemas/...`, so it is safest to run it from this directory after sourcing the workspace.

What this benchmark measures:
- `TacticalRetreatInterface` creation time (schema + data load)
- `get_expression_satisfied` latency for the fixed expression list in the script
- all `get_*` methods in `TacticalRetreatInterface` (or the subset passed with `--methods`)

Output includes:
- per-case latency stats (`avg`, `p50`, `p95`)
- success/failure counts per method call combination
- result size summary (`avg`, `min`, `max`)
- methods sorted by decreasing average latency
- skipped methods (missing input context) and methods with only failed invocations

Examples:

```bash
cd src/typedb_tactics/scripts
python3 benchmark.py
python3 benchmark.py --runs 10
python3 benchmark.py --methods get_potential_requirements_fulfillment,get_applicable_tactics
python3 benchmark.py --runs 10 --methods get_potential_requirements_fulfillment --max-combinations 50
```

Interpretation notes:
- Use `--methods` to isolate hotspots and reduce runtime when iterating.
- `--max-combinations` is useful for quick A/B checks on query or rule changes.
- For full-impact checks, run without `--methods` and without `--max-combinations`.

### `benchmark_queries.py`

Benchmarks initialization time and selected raw query paths for predefined profiles.

Profiles:
- `generated`
- `hyp`

Output includes:
- initialization breakdown (`init_no_schema`, per-schema timings, per-data-file timings)
- query latency stats (`cold`, `warm_avg`, `warm_p50`, `warm_p95`)
- row count stability across warm runs
- top 3 slowest query cases (by warm p50)
- top 3 slowest schema files (by load time)

Examples:

```bash
cd src/typedb_tactics/scripts
python3 benchmark_queries.py
python3 benchmark_queries.py --profiles hyp --runs 10
python3 benchmark_queries.py --profiles generated --runs 10
python3 benchmark_queries.py --profiles generated,hyp --runs 10 --format json
python3 benchmark_queries.py --no-infer
```

Interpretation notes:
- `cold` includes first-call overhead; use `warm_p50` and `warm_p95` for steady-state latency.
- Run with `--no-infer` only for comparison studies; production behavior should usually be benchmarked with inference enabled.

### `profile_schema_load.py`

Profiles schema loading time per schema file.

Examples:

```bash
cd src/typedb_tactics/scripts
python3 profile_schema_load.py
python3 profile_schema_load.py --runs 5
python3 profile_schema_load.py --no-infer
python3 profile_schema_load.py --schemas ../schemas/data_structure/data_structure.tql ../schemas/context_model/context_model.tql
```

### `run-tests-docker.sh`

Runs `typedb_tactics` tests inside the `tactical_retreat` Docker container.

The container must already be running.

Examples:

```bash
bash src/typedb_tactics/scripts/run-tests-docker.sh
bash src/typedb_tactics/scripts/run-tests-docker.sh -k test_relaxed_model
```

### `generated.tql`

This is not an executable script. It is a data file used by the benchmark tooling.

## Useful Checks

Show help for the diagram scripts:

```bash
python3 src/typedb_tactics/scripts/generate_schema_diagrams.py --help
python3 src/typedb_tactics/scripts/generate_merged_schema_diagram.py --help
```

Run the script-specific tests:

```bash
python3 -m pytest -q src/typedb_tactics/test/test_generate_schema_diagrams_script.py
python3 -m pytest -q src/typedb_tactics/test/test_generate_merged_schema_diagram_script.py
```
