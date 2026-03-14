# Benchmark Scripts

This directory contains the user-facing benchmark scripts for `typedb_tactics`.

It intentionally does **not** document the variant-experiment scripts that were
added to let agents compare schema rewrites, such as:

- `benchmark_requirement_impact_variants.py`
- `benchmark_logical_expression.py`

## Common Setup

Run the benchmarks inside the `tactical_retreat` container with ROS and the
workspace sourced:

```bash
docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   cd /home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics/scripts/benchmark && \
   python3 <script>.py ..."
```

Most scripts create and delete their own TypeDB database automatically.

## Shared Benchmark Data

[`benchmark.tql`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/scripts/benchmark/benchmark.tql)
is the main benchmark fixture used by:

- `benchmark.py`
- `benchmark_queries.py`
- `benchmark_requirement_impact_functions.py`

The DTM-focused benchmark uses the existing ROS/tactics example data instead of
`benchmark.tql`.

## `benchmark.py`

[`benchmark.py`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/scripts/benchmark/benchmark.py)
benchmarks all public `get_*` methods on `TacticalRetreatInterface`.

What it does:

- loads the benchmark schema set plus `benchmark.tql`
- discovers valid input combinations from the database
- silently filters invalid combinations before timing
- prints one result row per `get_*` method
- prints the 5 slowest methods at the end

Useful options:

- `--runs N`: number of timed invocations per valid method/input combination
- `--methods a,b,c`: benchmark only specific `get_*` methods
- `--max-combinations N`: cap the number of valid input combinations per method

Examples:

```bash
python3 benchmark.py --runs 5
python3 benchmark.py --runs 3 --methods get_applicable_tactics,get_potential_requirements_fulfillment
python3 benchmark.py --runs 1 --max-combinations 10
```

When to use it:

- comparing high-level Python getter performance
- checking whether a schema change affects end-to-end `get_*` latency

## `benchmark_queries.py`

[`benchmark_queries.py`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/scripts/benchmark/benchmark_queries.py)
benchmarks all public `fetch_*` methods on `TacticalRetreatInterface`.

What it does:

- loads either the dedicated benchmark profile or the legacy multi-file profile
- discovers valid `fetch_*` inputs from the selected dataset
- silently filters invalid combinations before timing
- supports text and JSON output
- prints the 5 slowest methods at the end in text mode

Useful options:

- `--runs N`: number of timed invocations per valid method/input combination
- `--data-profile benchmark|legacy`: choose the built-in dataset
- `--data path1,path2,...`: override the data profile with explicit files
- `--methods a,b,c`: benchmark only specific `fetch_*` methods
- `--max-combinations N`: cap the number of valid combinations per method
- `--format text|json`: choose the output format
- `--db-prefix NAME`: database name prefix
- `--address HOST:PORT`: TypeDB address

Examples:

```bash
python3 benchmark_queries.py --runs 5 --data-profile benchmark
python3 benchmark_queries.py --runs 1 --data-profile legacy --methods fetch_applicable_tactics
python3 benchmark_queries.py --runs 1 --format json --max-combinations 5
```

When to use it:

- comparing raw query-facing method performance
- checking benchmark behavior on `benchmark.tql` versus legacy fixture data

## `benchmark_requirement_impact_functions.py`

[`benchmark_requirement_impact_functions.py`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/scripts/benchmark/benchmark_requirement_impact_functions.py)
benchmarks each function in
[`discover_hypothetical_req_fulfillment.tql`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/schemas/discover_hypothetical_req_fulfillment/discover_hypothetical_req_fulfillment.tql)
with one representative valid input case.

Purpose:

- estimate which schema functions are the heaviest on a real benchmark dataset
- compare each function against the final
  `tactic_rule_impacts_requirement_fulfillment` query
- keep cold and warm timings separate

What it reports:

- one representative tactic rule for the whole run
- one representative valid input per function
- `cold`, `warm_avg`, `warm_p50`, and `warm_p95`
- each function’s warm p50 as a percentage of the final requirement function,
  when that final function is included

Useful options:

- `--warm-runs N`: number of warm timed runs after one cold run
- `-k REGEX` / `--function-regex REGEX`: benchmark only functions whose names
  match the regex
- `--db-name NAME`: database name for the run
- `--address HOST:PORT`: TypeDB address

Examples:

```bash
python3 benchmark_requirement_impact_functions.py
python3 benchmark_requirement_impact_functions.py --warm-runs 10
python3 benchmark_requirement_impact_functions.py -k tactic_rule_hypothetical_measure_
python3 benchmark_requirement_impact_functions.py -k 'tactic_rule_impacts_(shall|may|requirement)'
```

When to use it:

- understanding where time is spent inside
  `tactic_rule_impacts_requirement_fulfillment`
- checking whether a schema rewrite sped up a leaf helper, a fuzzy combinator,
  or the final requirement function

## `benchmark_dtm.py`

[`benchmark_dtm.py`](/home/gus/ros_workspaces/tactical_retreat_3_ws/src/typedb_tactics/scripts/benchmark/benchmark_dtm.py)
is a focused benchmark for the `discover_tactics_model.tql` graph functions:

- `neighbours()`
- `connected_nodes()`
- `applicable_tactics()`

It uses `ros_model_example.tql` and `tactics_example.tql`, not `benchmark.tql`.

Useful options:

- `--runs N`: number of warm runs per repeat
- `--repeats N`: number of fresh database repeats
- `--label NAME`: free-form label printed in the report
- `--db NAME`: database name
- `--address HOST:PORT`: TypeDB address

Examples:

```bash
python3 benchmark_dtm.py
python3 benchmark_dtm.py --runs 10 --repeats 5
python3 benchmark_dtm.py --label current
```

When to use it:

- checking graph-query regressions after edits to `discover_tactics_model.tql`
- separating cold-vs-warm effects for `neighbours`, `connected_nodes`, and
  `applicable_tactics`
