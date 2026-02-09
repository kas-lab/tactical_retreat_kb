

import argparse
import time
from decimal import Decimal

from typing import Iterator
from typing import List
from typing import Tuple

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


def float_range(start: float, stop: float, step: float) -> Iterator[float]:
    if step <= 0:
        raise ValueError("step must be > 0")

    start_decimal = Decimal(str(start))
    stop_decimal = Decimal(str(stop))
    step_decimal = Decimal(str(step))
    current = start_decimal

    # Include the stop value if it falls exactly on a step.
    while current <= stop_decimal:
        yield float(current)
        current += step_decimal


def add_measurements(
    kb_interface: TacticalRetreatInterface,
    measure_names_range: List[Tuple[str, float, float, float]],
):
    for measure_name, range_start, range_stop, range_step in measure_names_range:
        measurement_count = 0
        for measured_value in float_range(range_start, range_stop, range_step):
            kb_interface.add_measurement(measure_name, measured_value)
            measurement_count += 1

        print(
            f"Added {measurement_count} measurements for {measure_name} "
            f"(from {range_start:.2f} to {range_stop:.2f}, step {range_step:.2f})"
        )


def main(runs: int):
    interface_start_time = time.perf_counter()
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'benchmark',
        ['../schemas/data_structure/data_structure.tql',
            '../schemas/context_model/context_model.tql',
            '../schemas/logical_expressions/logical_expression.tql',
            '../schemas/logical_expressions/fuzzy_expression.tql',
            '../schemas/ros_model/ros_model.tql',
            '../schemas/feature_model/feature_model.tql',
            '../schemas/feature_model/feature_model_logical_expression.tql',
            '../schemas/relaxed/relaxed_model.tql',
            '../schemas/tactics_model/tactics_model.tql',
            '../schemas/discover_hypothetical_req_fulfillment/'
            'discover_hypothetical_req_fulfillment.tql',
            '../schemas/discover_tactics_model/discover_tactics_model.tql'],
        ['generated.tql'],
        force_database=True,
        force_data=True,
        infer=True
    )
    interface_creation_time_s = time.perf_counter() - interface_start_time
    print(
        "TacticalRetreatInterface creation time: "
        f"{interface_creation_time_s:.6f}s"
    )

    def get_expression_satisfied(self, expression_name):
        query = f"""
            match
                $expr isa logical_expression,
                    has expression_name '{expression_name}';
            fetch
                $expr: expression_satisfied;
        """
        query_result = self.fetch_database(query)
        return query_result[0]['expr']['expression_satisfied'][0]['value']

    kb_interface.register_method('get_expression_satisfied', get_expression_satisfied)

    measures_name_range = [
        ("nearest_object", 0.01, 10.0, 0.01),
        ("current_velocity", 0.01, 5.0, 0.01),
        ("power_draw", 1.0, 100.0, 1.0),
        ("power_budget", 1.0, 100.0, 1.0),
    ]

    add_measurements(kb_interface, measures_name_range)

    kb_interface.add_measurement('nearest_object', 0.09)

    kb_interface.add_measurement('too_close', True)
    kb_interface.add_measurement('too_close', False)

    kb_interface.add_measurement('power_draw', 50.0)

    kb_interface.add_measurement('power_draw', 50.0)

    expression_names = [
        'nearest_object_less',
        'power_draw_greater',
        'nearest_object_less_1',
        'power_draw_greater_1',
        'nearest_object_greater',
        'power_draw_leq',
        'current_velocity_less'
    ]

    elapsed_times_s = []
    for expression_name in expression_names:
        expression_elapsed_times_s = []
        expression_satisfied = None

        for run_idx in range(runs):
            start_time = time.perf_counter()
            expression_satisfied = kb_interface.get_expression_satisfied(
                expression_name)
            elapsed_time_s = time.perf_counter() - start_time
            elapsed_times_s.append(elapsed_time_s)
            expression_elapsed_times_s.append(elapsed_time_s)

            print(
                f"{expression_name} run {run_idx + 1}/{runs}: "
                f"satisfied={expression_satisfied}, "
                f"time={elapsed_time_s:.6f}s"
            )

        expression_avg_time_s = (
            sum(expression_elapsed_times_s) / len(expression_elapsed_times_s))
        print(
            f"{expression_name} average over {runs} runs: "
            f"{expression_avg_time_s:.6f}s"
        )

    if elapsed_times_s:
        average_time_s = sum(elapsed_times_s) / len(elapsed_times_s)
        print(
            "Overall average get_expression_satisfied time "
            f"({len(elapsed_times_s)} total calls): {average_time_s:.6f}s"
        )

    print(
        "TacticalRetreatInterface creation time: "
        f"{interface_creation_time_s:.6f}s"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark get_expression_satisfied for configured expressions."
        )
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per expression (default: 1).",
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be >= 1")

    main(args.runs)
