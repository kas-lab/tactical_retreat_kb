#!/usr/bin/env bash
set -euo pipefail

# Run tests inside the tactical_retreat container (non-interactive).

if ! docker ps --format '{{.Names}}' | grep -q '^tactical_retreat$'; then
  echo "Container 'tactical_retreat' is not running." >&2
  echo "Start it first, e.g.:" >&2
  echo "  docker run -d --rm --name tactical_retreat ..." >&2
  exit 1
fi

pytest_args=()
if [[ "${1:-}" == "-k" ]]; then
  pytest_args=("--pytest-args" "-k" "${2:-}")
fi

docker exec tactical_retreat bash -lc \
  "source /opt/ros/humble/setup.bash && \
   source /home/ubuntu-user/tactical_retreat_ws/install/setup.bash && \
   colcon test --event-handlers console_cohesion+ --packages-select tactical_retreat_kb ${pytest_args[*]}"
