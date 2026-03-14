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
from contextlib import contextmanager
import inspect
from itertools import product
import logging
import math
from pathlib import Path
import time

from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from ros_typedb.typedb_interface import TypeDBQueryError
from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent


def to_abs_paths(paths: List[str]) -> List[str]:
    """Resolve repository-relative paths to absolute paths."""
    return [str((REPO_DIR / path).resolve()) for path in paths]


DEFAULT_SCHEMAS = to_abs_paths([
    'schemas/data_structure/data_structure.tql',
    'schemas/context_model/context_model.tql',
    'schemas/logical_expressions/logical_expression.tql',
    'schemas/logical_expressions/fuzzy_expression.tql',
    'schemas/ros_model/ros_model.tql',
    'schemas/feature_model/feature_model.tql',
    'schemas/relaxed/relaxed_model.tql',
    'schemas/tactics_model/tactics_model.tql',
    'schemas/discover_hypothetical_req_fulfillment/'
    'discover_hypothetical_req_fulfillment.tql',
    'schemas/discover_tactics_model/discover_tactics_model.tql',
])
DEFAULT_DATA = [str((SCRIPT_DIR / 'benchmark.tql').resolve())]

PROBE_LOGGERS = (
    'ros_typedb.typedb_interface',
    'typedb_tactics.typedb_tactical_retreat_interface',
)


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
    key: str,
) -> List[str]:
    query_result = kb_interface.fetch_database(query)
    values = []
    for result in query_result:
        value = result.get(key)
        if value is None:
            continue
        values.append(value)
    return unique_preserve(values)


def fetch_node_values(
    kb_interface: TacticalRetreatInterface,
    query: str,
) -> List[Tuple[str, str]]:
    query_result = kb_interface.fetch_database(query)
    nodes: List[Tuple[str, str]] = []
    for result in query_result:
        node_name = result.get('node_name')
        namespace = result.get('namespace')
        if node_name is None or namespace is None:
            continue
        nodes.append((node_name, namespace))
    return unique_preserve(nodes)


def fetch_attr_pairs(
    kb_interface: TacticalRetreatInterface,
    query: str,
    left_key: str,
    right_key: str,
) -> List[Tuple[str, str]]:
    query_result = kb_interface.fetch_database(query)
    pairs: List[Tuple[str, str]] = []
    for result in query_result:
        left_value = result.get(left_key)
        right_value = result.get(right_key)
        if left_value is None or right_value is None:
            continue
        pairs.append((left_value, right_value))
    return unique_preserve(pairs)


@contextmanager
def suppress_probe_logging():
    """Temporarily disable noisy loggers during expected-invalid probes."""
    loggers = [logging.getLogger(name) for name in PROBE_LOGGERS]
    previous_states = [(logger, logger.disabled) for logger in loggers]
    for logger in loggers:
        logger.disabled = True
    try:
        yield
    finally:
        for logger, disabled in previous_states:
            logger.disabled = disabled


def resolve_context(
    kb_interface: TacticalRetreatInterface,
) -> Tuple[Dict[str, List], List[Dict[str, str]]]:
    context: Dict[str, List] = {}
    context_errors: List[Dict[str, str]] = []

    def safe_context_value(key: str, resolver, default):
        try:
            context[key] = resolver()
        except TypeDBQueryError as err:
            context[key] = default
            context_errors.append({
                'context_key': key,
                'error': str(err),
            })

    safe_context_value(
        'nodes',
        lambda: fetch_node_values(
            kb_interface,
            """
                match
                    $node isa ROSNode;
                fetch {
                    "node_name": $node.node_name,
                    "namespace": $node.namespace
                };
            """),
        [])
    safe_context_value(
        'nodes_with_subnode',
        lambda: fetch_node_values(
            kb_interface,
            """
                match
                    (node: $node, subnode: $subnode) isa subnode;
                fetch {
                    "node_name": $node.node_name,
                    "namespace": $node.namespace
                };
            """),
        [])
    safe_context_value(
        'nodes_with_action_client',
        lambda: fetch_node_values(
            kb_interface,
            """
                match
                    $client isa ActionClient;
                    (node: $node, client: $client) isa has_action;
                fetch {
                    "node_name": $node.node_name,
                    "namespace": $node.namespace
                };
            """),
        [])
    safe_context_value(
        'nodes_with_publisher',
        lambda: fetch_node_values(
            kb_interface,
            """
                match
                    $publisher isa Publisher;
                    (node: $node, publisher: $publisher) isa has_topic;
                fetch {
                    "node_name": $node.node_name,
                    "namespace": $node.namespace
                };
            """),
        [])

    safe_context_value(
        'action_client_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $action_client isa ActionClient;
                fetch { "interface_name": $action_client.interface_name };
            """,
            'interface_name'),
        [])
    safe_context_value(
        'action_server_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $action_server isa ActionServer;
                fetch { "interface_name": $action_server.interface_name };
            """,
            'interface_name'),
        [])

    safe_context_value(
        'resolution_models',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $resolution_model isa resolution_model;
                fetch {
                    "resolution_model_name": $resolution_model.resolution_model_name
                };
            """,
            'resolution_model_name'),
        [])
    safe_context_value(
        'interface_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $interface isa ROSInterface;
                fetch { "interface_name": $interface.interface_name };
            """,
            'interface_name'),
        [])

    safe_context_value(
        'applicable_pairs',
        lambda: fetch_attr_pairs(
            kb_interface,
            """
                match
                    $interface isa ROSInterface;
                    $resolution_model isa resolution_model;
                    let $tactic_rule in applicable_tactics($interface, $resolution_model);
                fetch {
                    "resolution_model_name": $resolution_model.resolution_model_name,
                    "interface_name": $interface.interface_name
                };
            """,
            'resolution_model_name',
            'interface_name'),
        [])
    context['applicable_resolution_models'] = unique_preserve(
        [pair[0] for pair in context['applicable_pairs']])
    context['applicable_interfaces'] = unique_preserve(
        [pair[1] for pair in context['applicable_pairs']])
    safe_context_value(
        'system_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $system isa System;
                fetch { "system_name": $system.system_name };
            """,
            'system_name'),
        [])
    safe_context_value(
        'requirement_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $req isa relaxed_requirement;
                fetch { "requirement_name": $req.requirement_name };
            """,
            'requirement_name'),
        [])
    safe_context_value(
        'in_effect_requirement_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $req isa relaxed_requirement, has in_effect true;
                fetch { "requirement_name": $req.requirement_name };
            """,
            'requirement_name'),
        [])

    safe_context_value(
        'expression_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $expr isa expression;
                fetch { "expression_name": $expr.expression_name };
            """,
            'expression_name'),
        [])
    safe_context_value(
        'logical_expression_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $expr isa logical_expression;
                fetch { "expression_name": $expr.expression_name };
            """,
            'expression_name'),
        [])
    safe_context_value(
        'fuzzy_expression_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $expr isa fuzzy_expression;
                fetch { "expression_name": $expr.expression_name };
            """,
            'expression_name'),
        [])
    safe_context_value(
        'relaxed_expression_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $expr isa relaxed_expression;
                fetch { "expression_name": $expr.expression_name };
            """,
            'expression_name'),
        [])

    safe_context_value(
        'effect_pairs',
        lambda: fetch_attr_pairs(
            kb_interface,
            """
                match
                    $tactic_rule (effect: $effect) isa tactic_rule,
                        has rule_name $rule_name;
                    $effect isa relative_effect;
                    $effect links (measure: $measure, effect_value: $delta);
                    $delta has double_value $_;
                    (measure: $measure, measurement_value: $current)
                        isa measurement,
                        has latest true;
                    $current has double_value $_;
                fetch {
                    "rule_name": $rule_name,
                    "measure_name": $measure.measure_name
                };
            """,
            'rule_name',
            'measure_name'),
        [])
    safe_context_value(
        'measure_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $measure isa Measure;
                fetch { "measure_name": $measure.measure_name };
            """,
            'measure_name'),
        [])
    safe_context_value(
        'tactic_rule_names',
        lambda: fetch_attr_values(
            kb_interface,
            """
                match
                    $tactic_rule isa tactic_rule;
                fetch { "rule_name": $tactic_rule.rule_name };
            """,
            'rule_name'),
        [])
    context['tactic_rule_with_valid'] = list(context.get('tactic_rule_names', []))

    return context, context_errors


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
    tactic_interface_names = (
        unique_preserve(action_client_names + action_server_names)
        or context.get('applicable_interfaces', [])
        or context.get('interface_names', [])
    )
    resolution_models = (
        context.get('resolution_models', [])
        or context.get('applicable_resolution_models', [])
    )
    system_names = context.get('system_names', [])
    requirement_names = context.get('requirement_names', [])
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
    applicable_pairs = context.get('applicable_pairs', [])
    effect_pairs = context.get('effect_pairs', [])

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
        if applicable_pairs:
            call_specs = [
                ([resolution_model, interface_name], {})
                for resolution_model, interface_name in applicable_pairs
            ]
        else:
            call_specs = [
                ([resolution_model, interface_name], {})
                for resolution_model, interface_name in product(
                    resolution_models, tactic_interface_names)
            ]
    elif method_name == 'get_relaxed_requirement_fulfillment':
        call_specs = [
            ([system_name, requirement_name], {})
            for system_name, requirement_name in product(system_names, requirement_names)
        ]
    elif method_name == 'get_in_effect_requirement_fulfillment':
        call_specs = [([], {})]
    elif method_name == 'get_requirement_in_effect':
        call_specs = [([requirement_name], {}) for requirement_name in requirement_names]
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
        if effect_pairs:
            call_specs = [
                ([rule_name, measure_name], {})
                for rule_name, measure_name in effect_pairs
            ]
        else:
            call_specs = []
    elif method_name == 'get_fuzzy_membership_degree':
        call_specs = [([expression_name], {}) for expression_name in fuzzy_expression_names]
    elif method_name == 'get_expression_satisfied':
        call_specs = [([expression_name], {}) for expression_name in logical_expression_names]
    elif method_name == 'get_relaxed_expression_fulfillment':
        call_specs = [([expression_name], {}) for expression_name in relaxed_expression_names]
    elif method_name == 'get_potential_requirements_fulfillment':
        if applicable_pairs:
            call_specs.extend(
                [([action_name], {'resolution_model': resolution_model})
                 for resolution_model, action_name in applicable_pairs]
            )
        elif resolution_models:
            call_specs.extend(
                [([action_name], {'resolution_model': resolution_model})
                 for action_name, resolution_model in product(
                     tactic_interface_names, resolution_models)]
            )
        else:
            call_specs = [([action_name], {}) for action_name in tactic_interface_names]
    elif method_name == 'get_potential_requirements_fulfillment_for_resolution_model':
        if applicable_pairs:
            call_specs = [
                ([action_name, resolution_model], {})
                for resolution_model, action_name in applicable_pairs
            ]
        else:
            call_specs = [
                ([action_name, resolution_model], {})
                for action_name, resolution_model in product(
                    tactic_interface_names, resolution_models)
            ]
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
        context: Dict[str, List],
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

    benchmark_results = []
    skipped_methods = []
    error_methods = []
    filtered_methods = []

    for method_name in method_names:
        call_specs = build_method_calls(method_name, context)
        if not call_specs:
            skipped_methods.append(method_name)
            continue
        if max_combinations is not None and max_combinations > 0:
            call_specs = call_specs[:max_combinations]

        method = getattr(kb_interface, method_name)
        valid_call_specs = []
        filtered_combinations = 0
        with suppress_probe_logging():
            for args, kwargs, call_description in call_specs:
                try:
                    method(*args, **kwargs)
                except Exception:  # pylint: disable=broad-exception-caught
                    filtered_combinations += 1
                    continue
                valid_call_specs.append((args, kwargs, call_description))

        if filtered_combinations:
            filtered_methods.append({
                'method_name': method_name,
                'filtered_combinations': filtered_combinations,
                'kept_combinations': len(valid_call_specs),
            })

        if not valid_call_specs:
            error_methods.append({
                'method_name': method_name,
                'total_combinations': len(call_specs),
                'failed_combinations': len(call_specs),
                'failed_invocations': filtered_combinations,
                'samples': [],
            })
            continue

        elapsed_times_s = []
        result_sizes = []
        successful_combinations = 0
        failed_invocations = 0
        error_samples = []

        for args, kwargs, call_description in valid_call_specs:
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

        total_combinations = len(valid_call_specs)
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
    return (
        benchmark_results,
        skipped_methods,
        error_methods,
        unknown_selected_methods,
        filtered_methods,
    )


def main(runs: int, methods: Optional[str], max_combinations: Optional[int]):
    interface_start_time = time.perf_counter()
    kb_interface = TacticalRetreatInterface(
        'localhost:1729',
        'benchmark',
        DEFAULT_SCHEMAS,
        DEFAULT_DATA,
        force_database=True,
        force_data=True
    )
    interface_creation_time_s = time.perf_counter() - interface_start_time
    print(
        'TacticalRetreatInterface creation time: '
        f'{interface_creation_time_s:.6f}s'
    )

    selected_methods = None
    if methods is not None and methods.strip() != '':
        selected_methods = {
            method_name.strip()
            for method_name in methods.split(',')
            if method_name.strip() != ''
        }

    context, context_errors = resolve_context(kb_interface)
    if context_errors:
        print('')
        print('Context discovery warnings:')
        for context_error in context_errors:
            print(
                f"- {context_error['context_key']}: {context_error['error']}"
            )

    (
        benchmark_results,
        skipped_methods,
        error_methods,
        unknown_selected_methods,
        filtered_methods,
    ) = benchmark_get_methods(
        kb_interface,
        runs,
        context,
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

    if filtered_methods:
        print('')
        print('Filtered invalid benchmark combinations:')
        for filtered_info in filtered_methods:
            print(
                f"- {filtered_info['method_name']}: "
                f"kept={filtered_info['kept_combinations']}, "
                f"filtered={filtered_info['filtered_combinations']}"
            )

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
        slowest_results = benchmark_results[:5]
        slowest = benchmark_results[0]
        fastest = benchmark_results[-1]
        print('')
        print(
            f'Benchmarked methods: {len(benchmark_results)} '
            f'(overall avg method latency: {overall_avg:.6f}s)'
        )
        print('5 slowest methods:')
        for index, result in enumerate(slowest_results, start=1):
            print(
                f"  {index}. {result['method_name']} "
                f"({result['avg_time_s']:.6f}s)"
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
