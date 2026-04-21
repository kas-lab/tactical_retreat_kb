# Copyright 2026 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
from decimal import Decimal
import inspect
from itertools import product
import math
import time

from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


DEFAULT_SCHEMAS = [
    '../schemas/data_structure/data_structure.tql',
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
    '../schemas/discover_tactics_model/discover_tactics_model.tql',
]


def float_range(start: float, stop: float, step: float) -> Iterator[float]:
    if step <= 0:
        raise ValueError('step must be > 0')

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
            f'Added {measurement_count} measurements for {measure_name} '
            f'(from {range_start:.2f} to {range_stop:.2f}, step {range_step:.2f})')


def percentile(values: List[float], fraction: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if fraction <= 0.0:
        return sorted_values[0]
    if fraction >= 1.0:
        return sorted_values[-1]
    rank = math.ceil(fraction * len(sorted_values))
    return sorted_values[rank - 1]


def unique_preserve(items: List):
    seen = set()
    unique_items = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


def fetch_attr_values(
    kb_interface: TacticalRetreatInterface,
    query: str,
    thing: str,
    attr: str,
) -> List[str]:
    query_result = kb_interface.fetch_database(query)
    values = []
    for result in query_result:
        thing_dict = result.get(thing, {})
        attr_values = thing_dict.get(attr, [])
        for attr_value in attr_values:
            value = attr_value.get('value')
            if value is None:
                continue
            values.append(value)
    return unique_preserve(values)


def fetch_node_values(
    kb_interface: TacticalRetreatInterface,
    query: str,
    thing: str,
) -> List[Tuple[str, str]]:
    query_result = kb_interface.fetch_database(query)
    nodes: List[Tuple[str, str]] = []
    for result in query_result:
        thing_dict = result.get(thing, {})
        node_names = thing_dict.get('node_name', [])
        namespaces = thing_dict.get('namespace', [])
        if not node_names or not namespaces:
            continue
        node_name = node_names[0].get('value')
        namespace = namespaces[0].get('value')
        if node_name is None or namespace is None:
            continue
        nodes.append((node_name, namespace))
    return unique_preserve(nodes)


def fetch_attr_pairs(
    kb_interface: TacticalRetreatInterface,
    query: str,
    left_thing: str,
    left_attr: str,
    right_thing: str,
    right_attr: str,
) -> List[Tuple[str, str]]:
    query_result = kb_interface.fetch_database(query)
    pairs: List[Tuple[str, str]] = []
    for result in query_result:
        left_dict = result.get(left_thing, {})
        right_dict = result.get(right_thing, {})
        left_values = left_dict.get(left_attr, [])
        right_values = right_dict.get(right_attr, [])
        if not left_values or not right_values:
            continue
        left_value = left_values[0].get('value')
        right_value = right_values[0].get('value')
        if left_value is None or right_value is None:
            continue
        pairs.append((left_value, right_value))
    return unique_preserve(pairs)


def resolve_context(kb_interface: TacticalRetreatInterface) -> Dict[str, List]:
    context: Dict[str, List] = {}

    context['nodes'] = fetch_node_values(
        kb_interface,
        """
            match
                $node isa ROSNode;
            fetch
                $node: node_name, namespace;
        """,
        'node')
    context['nodes_with_subnode'] = fetch_node_values(
        kb_interface,
        """
            match
                (node: $node, subnode: $subnode) isa subnode;
            fetch
                $node: node_name, namespace;
        """,
        'node')
    context['nodes_with_action_client'] = fetch_node_values(
        kb_interface,
        """
            match
                (node: $node, client: $client) isa has_action;
            fetch
                $node: node_name, namespace;
        """,
        'node')
    context['nodes_with_publisher'] = fetch_node_values(
        kb_interface,
        """
            match
                (node: $node, publisher: $publisher) isa has_topic;
            fetch
                $node: node_name, namespace;
        """,
        'node')

    context['action_client_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $action_client isa ActionClient;
            fetch
                $action_client: interface_name;
        """,
        'action_client',
        'interface_name')
    context['action_server_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $action_server isa ActionServer;
            fetch
                $action_server: interface_name;
        """,
        'action_server',
        'interface_name')

    context['resolution_models'] = fetch_attr_values(
        kb_interface,
        """
            match
                $resolution_model isa resolution_model;
            fetch
                $resolution_model: resolution_model_name;
        """,
        'resolution_model',
        'resolution_model_name')
    context['interface_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $interface isa ROSInterface;
            fetch
                $interface: interface_name;
        """,
        'interface',
        'interface_name')

    context['applicable_pairs'] = fetch_attr_pairs(
        kb_interface,
        """
            match
                $resolution_model isa resolution_model;
                $interface isa ROSInterface;
                (interface: $interface, resolution_model: $resolution_model, tactic_rule: $tr)
                    isa applicable_tactics;
            fetch
                $resolution_model: resolution_model_name;
                $interface: interface_name;
        """,
        'resolution_model',
        'resolution_model_name',
        'interface',
        'interface_name')
    context['applicable_resolution_models'] = unique_preserve(
        [pair[0] for pair in context['applicable_pairs']])
    context['applicable_interfaces'] = unique_preserve(
        [pair[1] for pair in context['applicable_pairs']])

    context['system_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $system isa System;
            fetch
                $system: system_name;
        """,
        'system',
        'system_name')

    context['requirement_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $req isa relaxed_requirement;
            fetch
                $req: requirement_name;
        """,
        'req',
        'requirement_name')
    context['in_effect_requirement_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $req isa relaxed_requirement, has in_effect true;
            fetch
                $req: requirement_name;
        """,
        'req',
        'requirement_name')

    context['expression_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $expr isa expression;
            fetch
                $expr: expression_name;
        """,
        'expr',
        'expression_name')
    context['logical_expression_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $expr isa logical_expression;
            fetch
                $expr: expression_name;
        """,
        'expr',
        'expression_name')
    context['fuzzy_expression_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $expr isa fuzzy_expression, has membership_degree $membership_degree;
            fetch
                $expr: expression_name;
        """,
        'expr',
        'expression_name')
    context['relaxed_expression_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $expr isa relaxed_expression, has fulfillment $fulfillment;
            fetch
                $expr: expression_name;
        """,
        'expr',
        'expression_name')

    context['measure_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $measure isa Measure;
            fetch
                $measure: measure_name;
        """,
        'measure',
        'measure_name')

    context['tactic_rule_names'] = fetch_attr_values(
        kb_interface,
        """
            match
                $tactic_rule isa tactic_rule;
            fetch
                $tactic_rule: rule_name;
        """,
        'tactic_rule',
        'rule_name')
    context['tactic_rule_with_valid'] = fetch_attr_values(
        kb_interface,
        """
            match
                $tactic_rule isa tactic_rule, has rule_valid $rule_valid;
            fetch
                $tactic_rule: rule_name;
        """,
        'tactic_rule',
        'rule_name')

    context['fulfillment_pairs'] = fetch_attr_pairs(
        kb_interface,
        """
            match
                $system isa System;
                $req (system: $system) isa relaxed_requirement,
                    has fulfillment $fulfillment;
            fetch
                $system: system_name;
                $req: requirement_name;
        """,
        'system',
        'system_name',
        'req',
        'requirement_name')

    context['impact_pairs'] = fetch_attr_pairs(
        kb_interface,
        """
            match
                $tr isa tactic_rule;
                $req isa relaxed_requirement;
                $tr_impacts (tactic_rule: $tr, impacted: $req) isa tactic_rule_impacts;
            fetch
                $tr: rule_name;
                $req: requirement_name;
        """,
        'tr',
        'rule_name',
        'req',
        'requirement_name')

    context['effect_pairs'] = fetch_attr_pairs(
        kb_interface,
        """
            match
                $tactic_rule (effect: $effect) isa tactic_rule;
                $effect (measure: $measure) isa relative_effect,
                    has resulting_effect_value $resulting_effect_value;
            fetch
                $tactic_rule: rule_name;
                $measure: measure_name;
        """,
        'tactic_rule',
        'rule_name',
        'measure',
        'measure_name')

    return context


def build_method_calls(
    method_name: str,
    context: Dict[str, List],
) -> List[Tuple[List, Dict, str]]:
    nodes = context.get('nodes', [])
    nodes_with_subnode = context.get('nodes_with_subnode', []) or nodes
    nodes_with_action_client = context.get('nodes_with_action_client', []) or nodes
    nodes_with_publisher = context.get('nodes_with_publisher', []) or nodes

    action_client_names = (
        context.get('action_client_names', [])
        or context.get('applicable_interfaces', [])
        or context.get('interface_names', [])
    )
    action_server_names = (
        context.get('action_server_names', [])
        or context.get('applicable_interfaces', [])
        or context.get('interface_names', [])
    )
    resolution_models = (
        context.get('resolution_models', [])
        or context.get('applicable_resolution_models', [])
    )
    interface_names = (
        context.get('interface_names', [])
        or context.get('applicable_interfaces', [])
    )
    system_names = context.get('system_names', [])
    requirement_names = context.get('requirement_names', [])
    in_effect_requirement_names = (
        context.get('in_effect_requirement_names', [])
        or requirement_names
    )
    tactic_rule_names = context.get('tactic_rule_names', [])
    tactic_rule_with_valid = (
        context.get('tactic_rule_with_valid', [])
        or tactic_rule_names
    )
    measure_names = context.get('measure_names', [])
    logical_expression_names = (
        context.get('logical_expression_names', [])
        or context.get('expression_names', [])
    )
    fuzzy_expression_names = context.get('fuzzy_expression_names', [])
    relaxed_expression_names = context.get('relaxed_expression_names', [])

    call_specs: List[Tuple[List, Dict]] = []

    if method_name == 'get_subnodes':
        call_specs = [([node_name, namespace], {}) for node_name, namespace in nodes_with_subnode]
    elif method_name == 'get_action_clients_nodes':
        call_specs = [([action_name], {}) for action_name in action_client_names]
    elif method_name == 'get_action_server_nodes':
        call_specs = [([action_name], {}) for action_name in action_server_names]
    elif method_name == 'get_action_clients_names':
        call_specs = [
            ([node_name, namespace], {})
            for node_name, namespace in nodes_with_action_client
        ]
    elif method_name == 'get_connected_action_server_nodes':
        call_specs = [
            ([node_name, namespace], {})
            for node_name, namespace in nodes_with_action_client
        ]
    elif method_name == 'get_connected_subscriber_nodes':
        call_specs = [
            ([node_name, namespace], {})
            for node_name, namespace in nodes_with_publisher
        ]
    elif method_name == 'get_tactics':
        call_specs = [([resolution_model], {}) for resolution_model in resolution_models]
    elif method_name == 'get_all_tactic_rules':
        call_specs = [([], {})]
    elif method_name == 'get_neighbours':
        call_specs = [([node_name, namespace], {}) for node_name, namespace in nodes]
    elif method_name == 'get_connected_nodes':
        call_specs = [([node_name, namespace], {}) for node_name, namespace in nodes]
    elif method_name == 'get_applicable_tactics':
        call_specs = [
            ([resolution_model, interface_name], {})
            for resolution_model, interface_name in product(resolution_models, interface_names)
        ]
    elif method_name == 'get_relaxed_requirement_fulfillment':
        call_specs = [
            ([system_name, requirement_name], {})
            for system_name, requirement_name in product(system_names, requirement_names)
        ]
    elif method_name == 'get_in_effect_requirement_fulfillment':
        call_specs = [([], {})]
    elif method_name == 'get_relaxed_requirement_hypothetical_fulfillment':
        call_specs = [
            ([system_name, requirement_name, tactic_rule], {})
            for system_name, requirement_name, tactic_rule in product(
                system_names, requirement_names, tactic_rule_names)
        ]
    elif method_name == 'get_requirement_in_effect':
        call_specs = [([requirement_name], {}) for requirement_name in in_effect_requirement_names]
    elif method_name == 'get_latest_measurement':
        call_specs = [([measure_name], {}) for measure_name in measure_names]
    elif method_name == 'get_tactic_rule_valid':
        call_specs = [([rule_name], {}) for rule_name in tactic_rule_with_valid]
    elif method_name == 'get_measures_interfaces':
        call_specs = [
            ([], {}),
            ([], {'include_qos': False}),
        ]
    elif method_name == 'get_tactic_rule_impacts_requirement':
        call_specs = [
            ([requirement_name, rule_name], {})
            for requirement_name, rule_name in product(requirement_names, tactic_rule_names)
        ]
    elif method_name == 'get_resulting_effect_value':
        call_specs = [
            ([rule_name, measure_name], {})
            for rule_name, measure_name in product(tactic_rule_names, measure_names)
        ]
    elif method_name == 'get_fuzzy_membership_degree':
        call_specs = [([expression_name], {}) for expression_name in fuzzy_expression_names]
    elif method_name == 'get_expression_satisfied':
        call_specs = [([expression_name], {}) for expression_name in logical_expression_names]
    elif method_name == 'get_relaxed_expression_fulfillment':
        call_specs = [([expression_name], {}) for expression_name in relaxed_expression_names]
    elif method_name == 'get_potential_requirements_fulfillment':
        call_specs.extend([([action_name], {}) for action_name in interface_names])
        call_specs.extend(
            [([action_name], {'resolution_model': resolution_model})
             for action_name, resolution_model in product(interface_names, resolution_models)]
        )
    elif method_name == 'get_all_requirements':
        call_specs = [([], {})]
    elif method_name == 'get_all_expressions':
        call_specs = [([], {})]

    deduplicated_specs: List[Tuple[List, Dict, str]] = []
    seen = set()
    for args, kwargs in call_specs:
        spec_key = (
            tuple(args),
            tuple(sorted(kwargs.items())),
        )
        if spec_key in seen:
            continue
        seen.add(spec_key)
        deduplicated_specs.append(
            (args, kwargs, f'args={args}, kwargs={kwargs}')
        )

    return deduplicated_specs


def benchmark_get_methods(
        kb_interface: TacticalRetreatInterface,
        runs: int,
        selected_methods: Optional[set[str]] = None,
        max_combinations: Optional[int] = None):
    all_method_names = sorted(
        name for name, func in inspect.getmembers(
            TacticalRetreatInterface, predicate=inspect.isfunction)
        if (
            name.startswith('get_')
            and func.__qualname__.startswith('TacticalRetreatInterface.')
        )
    )
    method_names = all_method_names
    if selected_methods:
        method_names = [
            method_name for method_name in method_names
            if method_name in selected_methods
        ]

    context = resolve_context(kb_interface)
    benchmark_results = []
    skipped_methods = []
    error_methods = []

    for method_name in method_names:
        call_specs = build_method_calls(method_name, context)
        if not call_specs:
            skipped_methods.append(method_name)
            continue
        if max_combinations is not None and max_combinations > 0:
            call_specs = call_specs[:max_combinations]

        method = getattr(kb_interface, method_name)
        elapsed_times_s = []
        result_sizes = []
        successful_combinations = 0
        failed_invocations = 0
        error_samples = []

        for args, kwargs, call_description in call_specs:
            combination_succeeded = False

            for _ in range(runs):
                start_time = time.perf_counter()
                try:
                    result = method(*args, **kwargs)
                except Exception as err:  # pylint: disable=broad-exception-caught
                    failed_invocations += 1
                    if len(error_samples) < 3:
                        error_samples.append({
                            'call': call_description,
                            'error': str(err),
                        })
                    continue

                elapsed_time_s = time.perf_counter() - start_time
                elapsed_times_s.append(elapsed_time_s)
                combination_succeeded = True

                result_size = 1
                if isinstance(result, (list, dict, tuple, set)):
                    result_size = len(result)
                elif isinstance(result, float) and math.isnan(result):
                    result_size = 0
                result_sizes.append(result_size)

            if combination_succeeded:
                successful_combinations += 1

        total_combinations = len(call_specs)
        failed_combinations = total_combinations - successful_combinations

        if not elapsed_times_s:
            error_methods.append({
                'method_name': method_name,
                'total_combinations': total_combinations,
                'failed_combinations': failed_combinations,
                'failed_invocations': failed_invocations,
                'samples': error_samples,
            })
            continue

        avg_time_s = sum(elapsed_times_s) / len(elapsed_times_s)
        p50_time_s = percentile(elapsed_times_s, 0.50)
        p95_time_s = percentile(elapsed_times_s, 0.95)
        result_size_avg = (
            sum(result_sizes) / len(result_sizes) if result_sizes else 0.0
        )
        result_size_min = min(result_sizes) if result_sizes else 0
        result_size_max = max(result_sizes) if result_sizes else 0

        benchmark_results.append({
            'method_name': method_name,
            'avg_time_s': avg_time_s,
            'p50_time_s': p50_time_s,
            'p95_time_s': p95_time_s,
            'result_size_avg': result_size_avg,
            'result_size_min': result_size_min,
            'result_size_max': result_size_max,
            'successful_invocations': len(elapsed_times_s),
            'failed_invocations': failed_invocations,
            'total_combinations': total_combinations,
            'successful_combinations': successful_combinations,
            'failed_combinations': failed_combinations,
        })

    benchmark_results.sort(key=lambda item: item['avg_time_s'], reverse=True)
    unknown_selected_methods = []
    if selected_methods:
        unknown_selected_methods = sorted(
            selected_methods.difference(set(all_method_names))
        )
    return benchmark_results, skipped_methods, error_methods, unknown_selected_methods


def main(runs: int, methods: Optional[str], max_combinations: Optional[int]):
    interface_start_time = time.perf_counter()
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'benchmark',
        DEFAULT_SCHEMAS,
        ['generated.tql'],
        force_database=True,
        force_data=True,
        infer=True
    )
    interface_creation_time_s = time.perf_counter() - interface_start_time
    print(
        'TacticalRetreatInterface creation time: '
        f'{interface_creation_time_s:.6f}s'
    )

    measures_name_range = [
        ('nearest_object', 0.01, 10.0, 0.01),
        ('current_velocity', 0.01, 5.0, 0.01),
        ('power_draw', 1.0, 100.0, 1.0),
        ('power_budget', 1.0, 100.0, 1.0),
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
    expression_results = []
    for expression_name in expression_names:
        expression_elapsed_times_s = []
        expression_satisfied = None
        for run_idx in range(runs):
            start_time = time.perf_counter()
            expression_satisfied = kb_interface.get_expression_satisfied(
                expression_name)
            elapsed_time_s = time.perf_counter() - start_time
            expression_elapsed_times_s.append(elapsed_time_s)
            print(
                f'{expression_name} run {run_idx + 1}/{runs}: '
                f'satisfied={expression_satisfied}, '
                f'time={elapsed_time_s:.6f}s'
            )

        expression_results.append({
            'expression_name': expression_name,
            'avg_time_s': (
                sum(expression_elapsed_times_s) / len(expression_elapsed_times_s)
            ),
            'p50_time_s': percentile(expression_elapsed_times_s, 0.50),
            'p95_time_s': percentile(expression_elapsed_times_s, 0.95),
            'last_satisfied': expression_satisfied,
        })

    expression_results.sort(key=lambda item: item['avg_time_s'], reverse=True)
    print('')
    print(
        'get_expression_satisfied benchmark over '
        f'{runs} run(s), sorted by avg_time_s descending:'
    )
    for expression_result in expression_results:
        print(
            f"{expression_result['expression_name']}: "
            f"avg={expression_result['avg_time_s']:.6f}s, "
            f"p50={expression_result['p50_time_s']:.6f}s, "
            f"p95={expression_result['p95_time_s']:.6f}s, "
            f"satisfied={expression_result['last_satisfied']}"
        )

    selected_methods = None
    if methods is not None and methods.strip() != '':
        selected_methods = {
            method_name.strip()
            for method_name in methods.split(',')
            if method_name.strip() != ''
        }

    (
        benchmark_results,
        skipped_methods,
        error_methods,
        unknown_selected_methods,
    ) = benchmark_get_methods(
        kb_interface,
        runs,
        selected_methods=selected_methods,
        max_combinations=max_combinations)

    print('')
    if selected_methods:
        print(f'Selected get_* methods: {", ".join(sorted(selected_methods))}')
        max_combinations_label = (
            max_combinations if max_combinations else 'unlimited')
        print(f'Max combinations per method: {max_combinations_label}')
        print('')
    print(f'get_* benchmark results over {runs} run(s), sorted by avg_time_s descending:')
    for result in benchmark_results:
        print(
            f"{result['method_name']}: "
            f"avg={result['avg_time_s']:.6f}s, "
            f"p50={result['p50_time_s']:.6f}s, "
            f"p95={result['p95_time_s']:.6f}s, "
            f"result_size_avg={result['result_size_avg']:.2f}, "
            f"result_size_range={result['result_size_min']}..{result['result_size_max']}, "
            f"success_invocations={result['successful_invocations']}, "
            f"failed_invocations={result['failed_invocations']}, "
            'success_combinations='
            f"{result['successful_combinations']}/"
            f"{result['total_combinations']}"
        )

    if skipped_methods:
        print('')
        print('Skipped methods (missing benchmark input data):')
        for method_name in skipped_methods:
            print(f'- {method_name}')

    if unknown_selected_methods:
        print('')
        print('Unknown selected methods:')
        for method_name in unknown_selected_methods:
            print(f'- {method_name}')

    if error_methods:
        print('')
        print('Methods with no successful invocations:')
        for error_info in error_methods:
            print(
                f"- {error_info['method_name']}: "
                f"success_combinations=0/{error_info['total_combinations']}, "
                f"failed_combinations={error_info['failed_combinations']}, "
                f"failed_invocations={error_info['failed_invocations']}"
            )
            for sample in error_info.get('samples', []):
                print(
                    f"  sample: {sample['call']} -> {sample['error']}"
                )

    if benchmark_results:
        overall_avg = (
            sum(item['avg_time_s'] for item in benchmark_results)
            / len(benchmark_results)
        )
        slowest = benchmark_results[0]
        fastest = benchmark_results[-1]
        print('')
        print(
            f'Benchmarked methods: {len(benchmark_results)} '
            f'(overall avg method latency: {overall_avg:.6f}s)'
        )
        print(
            f"Slowest: {slowest['method_name']} ({slowest['avg_time_s']:.6f}s)"
        )
        print(
            f"Fastest: {fastest['method_name']} ({fastest['avg_time_s']:.6f}s)"
        )

    print(
        'TacticalRetreatInterface creation time: '
        f'{interface_creation_time_s:.6f}s'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=(
            'Benchmark all get_* methods from TacticalRetreatInterface.'
        )
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=1,
        help='Number of runs per expression (default: 1).',
    )
    parser.add_argument(
        '--methods',
        type=str,
        default=None,
        help=(
            'Optional comma-separated get_* method names to benchmark. '
            'Example: --methods get_potential_requirements_fulfillment,get_applicable_tactics'
        ),
    )
    parser.add_argument(
        '--max-combinations',
        type=int,
        default=0,
        help=(
            'Optional cap of argument combinations per method. '
            'Use 0 for unlimited (default: 0).'
        ),
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error('--runs must be >= 1')
    if args.max_combinations < 0:
        parser.error('--max-combinations must be >= 0')

    max_combinations = args.max_combinations if args.max_combinations > 0 else None
    main(args.runs, args.methods, max_combinations)
