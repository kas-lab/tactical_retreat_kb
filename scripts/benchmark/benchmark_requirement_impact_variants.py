#!/usr/bin/env python3
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

"""Benchmark requirement-impact schema variants with separate cold and warm timings."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import asdict
from dataclasses import dataclass
import importlib.util
import json
import logging
import math
from pathlib import Path
import tempfile
import time
from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple
import uuid

from typedb_tactics.typedb_tactical_retreat_interface import TacticalRetreatInterface


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent
DISCOVER_SCHEMA_REL = (
    'schemas/discover_hypothetical_req_fulfillment/'
    'discover_hypothetical_req_fulfillment.tql'
)
DISCOVER_SCHEMA_PATH = (REPO_DIR / DISCOVER_SCHEMA_REL).resolve()
NOISY_LOGGERS = (
    'ros_typedb.typedb_interface',
    'typedb_tactics.typedb_tactical_retreat_interface',
)


def load_benchmark_queries_module():
    """Import benchmark_queries.py to reuse schema/data defaults."""
    module_path = SCRIPT_DIR / 'benchmark_queries.py'
    spec = importlib.util.spec_from_file_location(
        'typedb_tactics_benchmark_queries_variants',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def suppress_benchmark_logging():
    """Silence expected TypeDB errors while trying candidate variants."""
    loggers = [logging.getLogger(name) for name in NOISY_LOGGERS]
    previous_states = [(logger, logger.disabled) for logger in loggers]
    for logger in loggers:
        logger.disabled = True
    try:
        yield
    finally:
        for logger, disabled in previous_states:
            logger.disabled = disabled


def percentile(values: List[float], fraction: float) -> float:
    """Compute nearest-rank percentile on a sorted list."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if fraction <= 0.0:
        return sorted_values[0]
    if fraction >= 1.0:
        return sorted_values[-1]
    rank = math.ceil(fraction * len(sorted_values))
    return sorted_values[rank - 1]


def canonical_rows(rows: List[dict]) -> List[dict]:
    """Canonicalize rows for semantic-equivalence checks."""
    normalized_rows = []
    for row in rows:
        if hasattr(row, '__dataclass_fields__'):
            normalized_rows.append(asdict(row))
        else:
            normalized_rows.append(row)
    return sorted(
        normalized_rows,
        key=lambda row: json.dumps(row, sort_keys=True),
    )


def replace_function(text: str, func_name: str, new_definition: str) -> str:
    """Replace one TypeQL function body by name."""
    marker = f'fun {func_name}('
    start = text.find(marker)
    if start < 0:
        raise ValueError(f'Function not found: {func_name}')
    next_fun = text.find('\nfun ', start + 1)
    end = len(text) if next_fun < 0 else next_fun + 1
    replacement = new_definition.strip() + '\n\n'
    return text[:start] + replacement + text[end:]


def typeql_block(*lines: str) -> str:
    """Join TypeQL lines without forcing long Python source lines."""
    return '\n'.join(lines) + '\n'


def build_variant_texts(base_schema_text: str) -> Dict[str, str]:
    """Build candidate schema texts from the current baseline."""
    comparison_lhs_via_measure_helper = typeql_block(
        'fun tactic_rule_hypothetical_comparison_lhs_value('
        '$tr: tactic_rule, $e: comparison_expression) -> double:',
        '  match',
        '    { $e links (lhs_value: $lhs_term_m);',
        '      $lhs_term_m isa Measure;',
        '      let $lhs_measure_value = '
        'tactic_rule_hypothetical_measure_value($tr, $lhs_term_m);',
        '      let $v_cmp_lhs = $lhs_measure_value; } or',
        '    { $e links (lhs_value: $lhs_term_d);',
        '      $lhs_term_d isa ValueSingleton;',
        '      $lhs_term_d has double_value $lhs_d;',
        '      let $v_cmp_lhs = $lhs_d; } or',
        '    { $e links (lhs_value: $lhs_term_i);',
        '      $lhs_term_i isa ValueSingleton;',
        '      $lhs_term_i has integer_value $lhs_i;',
        '      let $v_cmp_lhs = $lhs_i + 0.0; };',
        '  return first $v_cmp_lhs;',
    )
    comparison_rhs_via_measure_helper = typeql_block(
        'fun tactic_rule_hypothetical_comparison_rhs_value('
        '$tr: tactic_rule, $e: comparison_expression) -> double:',
        '  match',
        '    { $e links (rhs_value: $rhs_term_m);',
        '      $rhs_term_m isa Measure;',
        '      let $rhs_measure_value = '
        'tactic_rule_hypothetical_measure_value($tr, $rhs_term_m);',
        '      let $v_cmp_rhs = $rhs_measure_value; } or',
        '    { $e links (rhs_value: $rhs_term_d);',
        '      $rhs_term_d isa ValueSingleton;',
        '      $rhs_term_d has double_value $rhs_d;',
        '      let $v_cmp_rhs = $rhs_d; } or',
        '    { $e links (rhs_value: $rhs_term_i);',
        '      $rhs_term_i isa ValueSingleton;',
        '      $rhs_term_i has integer_value $rhs_i;',
        '      let $v_cmp_rhs = $rhs_i + 0.0; };',
        '  return first $v_cmp_rhs;',
    )
    fuzzy_term_via_measure_helper = typeql_block(
        'fun tactic_rule_hypothetical_fuzzy_term('
        '$tr: tactic_rule, $e: fuzzy_comparison_expression) -> double:',
        '  match',
        '    { $e links (term: $term_ft_m);',
        '      $term_ft_m isa Measure;',
        '      let $measure_value_ft = '
        'tactic_rule_hypothetical_measure_value($tr, $term_ft_m);',
        '      let $raw_ft = $measure_value_ft; } or',
        '    { $e links (term: $term_ft_d);',
        '      $term_ft_d isa ValueSingleton;',
        '      $term_ft_d has double_value $vs_d_ft;',
        '      let $raw_ft = $vs_d_ft; } or',
        '    { $e links (term: $term_ft_i);',
        '      $term_ft_i isa ValueSingleton;',
        '      $term_ft_i has integer_value $vs_i_ft;',
        '      let $raw_ft = $vs_i_ft + 0.0; };',
        '    { $e has offset_value $off_ft; let $q_hft = $raw_ft + $off_ft; } or',
        '    { not { $e has offset_value $_; }; let $q_hft = $raw_ft; };',
        '  return first $q_hft;',
    )
    relaxed_term_via_measure_helper = typeql_block(
        'fun tactic_rule_hypothetical_relaxed_term('
        '$tr: tactic_rule, $e: relaxed_fuzzy_expression) -> double:',
        '  match',
        '    { $e links (term: $term_rt_m);',
        '      $term_rt_m isa Measure;',
        '      let $measure_value_rt = '
        'tactic_rule_hypothetical_measure_value($tr, $term_rt_m);',
        '      let $raw_rt = $measure_value_rt; } or',
        '    { $e links (term: $term_rt_d);',
        '      $term_rt_d isa ValueSingleton;',
        '      $term_rt_d has double_value $vs_d_rt;',
        '      let $raw_rt = $vs_d_rt; } or',
        '    { $e links (term: $term_rt_i);',
        '      $term_rt_i isa ValueSingleton;',
        '      $term_rt_i has integer_value $vs_i_rt;',
        '      let $raw_rt = $vs_i_rt + 0.0; };',
        '    { $e has required_value $rv_rt; let $q_hrt = $raw_rt - $rv_rt; } or',
        '    { $e has required_period $rp_rt; let $q_hrt = $raw_rt - $rp_rt; } or',
        '    { not { $e has required_value $_; }; not { $e has required_period $_; };',
        '      let $q_hrt = $raw_rt; };',
        '  return first $q_hrt;',
    )
    branch_reduced_fuzzy_or = """
fun tactic_rule_impacts_fuzzy_or_fulfillment($tr: tactic_rule, $e: fuzzy_or) -> double:
  match
    $e links (expression: $child_fo);
    { $child_fo isa fuzzy_not;
      let $m_fn_fo = tactic_rule_impacts_fuzzy_not_membership($tr, $child_fo);
      let $m_fo = $m_fn_fo; } or
    { $child_fo isa comparison_expression;
      let $m_cmp_fo = tactic_rule_impacts_comparison_fulfillment($tr, $child_fo);
      let $m_fo = $m_cmp_fo; } or
    { $child_fo isa not_expression;
      let $m_not_fo = tactic_rule_impacts_not_membership($tr, $child_fo);
      let $m_fo = $m_not_fo; } or
    { $child_fo isa relaxed_fuzzy_expression;
      let $m_rf_fo = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $child_fo);
      let $m_fo = $m_rf_fo; } or
    { $child_fo isa fuzzy_comparison_expression;
      let $m_leaf_fo = tactic_rule_impacts_fuzzy_leaf_fulfillment($tr, $child_fo);
      let $m_fo = $m_leaf_fo; } or
    { $child_fo isa logical_expression;
      not { $child_fo isa comparison_expression; };
      let $m_log_fo = logical_expression_membership($child_fo);
      let $m_fo = $m_log_fo; };
  return max($m_fo);
"""
    branch_reduced_fuzzy_and = """
fun tactic_rule_impacts_fuzzy_and_fulfillment($tr: tactic_rule, $e: fuzzy_and) -> double:
  match
    $e links (expression: $child_fa);
    { $child_fa isa fuzzy_not;
      let $m_fn_fa = tactic_rule_impacts_fuzzy_not_membership($tr, $child_fa);
      let $m_fa = $m_fn_fa; } or
    { $child_fa isa comparison_expression;
      let $m_cmp_fa = tactic_rule_impacts_comparison_fulfillment($tr, $child_fa);
      let $m_fa = $m_cmp_fa; } or
    { $child_fa isa not_expression;
      let $m_not_fa = tactic_rule_impacts_not_membership($tr, $child_fa);
      let $m_fa = $m_not_fa; } or
    { $child_fa isa relaxed_fuzzy_expression;
      let $m_rf_fa = tactic_rule_impacts_relaxed_leaf_fulfillment($tr, $child_fa);
      let $m_fa = $m_rf_fa; } or
    { $child_fa isa fuzzy_comparison_expression;
      let $m_leaf_fa = tactic_rule_impacts_fuzzy_leaf_fulfillment($tr, $child_fa);
      let $m_fa = $m_leaf_fa; } or
    { $child_fa isa logical_expression;
      not { $child_fa isa comparison_expression; };
      let $m_log_fa = logical_expression_membership($child_fa);
      let $m_fa = $m_log_fa; };
  return min($m_fa);
"""
    requirement_via_any_expression = typeql_block(
        'fun tactic_rule_impacts_requirement_fulfillment('
        '$tr: tactic_rule, $req: relaxed_requirement) -> double:',
        '  match',
        '    $req links (expression: $req_expr);',
        '    let $req_m = '
        'tactic_rule_impacts_any_expression_fulfillment($tr, $req_expr);',
        '  return min($req_m);',
    )
    variants = {'baseline': base_schema_text}

    branch_reduced = replace_function(
        base_schema_text,
        'tactic_rule_impacts_fuzzy_or_fulfillment',
        branch_reduced_fuzzy_or,
    )
    branch_reduced = replace_function(
        branch_reduced,
        'tactic_rule_impacts_fuzzy_and_fulfillment',
        branch_reduced_fuzzy_and,
    )
    variants['fuzzy_child_branch_reduced'] = branch_reduced

    variants['requirement_via_any_expression'] = replace_function(
        base_schema_text,
        'tactic_rule_impacts_requirement_fulfillment',
        requirement_via_any_expression,
    )

    measure_helper_reuse = replace_function(
        base_schema_text,
        'tactic_rule_hypothetical_comparison_lhs_value',
        comparison_lhs_via_measure_helper,
    )
    measure_helper_reuse = replace_function(
        measure_helper_reuse,
        'tactic_rule_hypothetical_comparison_rhs_value',
        comparison_rhs_via_measure_helper,
    )
    measure_helper_reuse = replace_function(
        measure_helper_reuse,
        'tactic_rule_hypothetical_fuzzy_term',
        fuzzy_term_via_measure_helper,
    )
    measure_helper_reuse = replace_function(
        measure_helper_reuse,
        'tactic_rule_hypothetical_relaxed_term',
        relaxed_term_via_measure_helper,
    )
    variants['measure_helper_reuse'] = measure_helper_reuse

    measure_plus_branch = replace_function(
        measure_helper_reuse,
        'tactic_rule_impacts_fuzzy_or_fulfillment',
        branch_reduced_fuzzy_or,
    )
    measure_plus_branch = replace_function(
        measure_plus_branch,
        'tactic_rule_impacts_fuzzy_and_fulfillment',
        branch_reduced_fuzzy_and,
    )
    variants['measure_helper_plus_fuzzy_branch_reduced'] = measure_plus_branch

    measure_plus_requirement = replace_function(
        measure_helper_reuse,
        'tactic_rule_impacts_requirement_fulfillment',
        requirement_via_any_expression,
    )
    variants['measure_helper_plus_requirement_dispatch'] = measure_plus_requirement

    combined = replace_function(
        measure_plus_branch,
        'tactic_rule_impacts_requirement_fulfillment',
        requirement_via_any_expression,
    )
    variants['measure_plus_fuzzy_plus_requirement_dispatch'] = combined
    return variants


def build_variant_schema_paths(
    base_schema_paths: List[str],
    variant_schema_path: Path,
) -> List[str]:
    """Replace the discover-hyp schema path with the candidate schema path."""
    discover_suffix = DISCOVER_SCHEMA_REL.replace('\\', '/')
    result = []
    for path in base_schema_paths:
        normalized = path.replace('\\', '/')
        if normalized.endswith(discover_suffix):
            result.append(str(variant_schema_path))
        else:
            result.append(path)
    return result


@dataclass(frozen=True)
class CaseSpec:
    """One benchmark case."""

    label: str
    runner: Callable[[], List[dict]]


def benchmark_case(case: CaseSpec, warm_runs: int) -> Dict[str, float | int | str | bool]:
    """Measure one cold invocation and N warm invocations."""
    cold_start = time.perf_counter()
    cold_result = case.runner()
    cold_ms = (time.perf_counter() - cold_start) * 1000.0

    warm_durations_ms: List[float] = []
    row_counts = [len(cold_result)]
    for _ in range(warm_runs):
        start = time.perf_counter()
        result = case.runner()
        warm_durations_ms.append((time.perf_counter() - start) * 1000.0)
        row_counts.append(len(result))

    return {
        'label': case.label,
        'cold_ms': cold_ms,
        'warm_avg_ms': sum(warm_durations_ms) / len(warm_durations_ms),
        'warm_p50_ms': percentile(warm_durations_ms, 0.50),
        'warm_p95_ms': percentile(warm_durations_ms, 0.95),
        'row_count_min': min(row_counts),
        'row_count_max': max(row_counts),
        'row_count_stable': min(row_counts) == max(row_counts),
        'cold_row_count': len(cold_result),
    }


def fetch_attr_pairs(
    kb_interface: TacticalRetreatInterface,
    query: str,
    left_key: str,
    right_key: str,
) -> List[Tuple[str, str]]:
    """Fetch deduplicated pairs from a generic fetch query."""
    rows = kb_interface.fetch_database(query)
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for row in rows:
        left = row.get(left_key)
        right = row.get(right_key)
        if left is None or right is None:
            continue
        pair = (left, right)
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    return pairs


def resolve_benchmark_targets(
    kb_interface: TacticalRetreatInterface,
) -> Tuple[str, str, List[Tuple[str, str]]]:
    """Pick one action/model pair and its direct (rule, requirement) cases."""
    applicable_pairs = fetch_attr_pairs(
        kb_interface,
        """
            match
                $interface isa ROSInterface;
                $rm isa resolution_model;
                let $tr in applicable_tactics($interface, $rm);
            fetch {
                "interface_name": $interface.interface_name,
                "resolution_model_name": $rm.resolution_model_name
            };
        """,
        'interface_name',
        'resolution_model_name',
    )
    if not applicable_pairs:
        raise RuntimeError('No applicable interface/resolution-model pairs found.')
    action_name, resolution_model = applicable_pairs[0]

    direct_pairs = fetch_attr_pairs(
        kb_interface,
        f"""
            match
                $interface isa ROSInterface, has interface_name '{action_name}';
                $rm isa resolution_model, has resolution_model_name '{resolution_model}';
                let $tr in applicable_tactics($interface, $rm);
                $req isa relaxed_requirement, has in_effect true;
            fetch {{
                "rule_name": $tr.rule_name,
                "requirement_name": $req.requirement_name
            }};
        """,
        'rule_name',
        'requirement_name',
    )
    if not direct_pairs:
        raise RuntimeError('No direct (rule, requirement) pairs found.')
    return action_name, resolution_model, direct_pairs


def build_cases(
    kb_interface: TacticalRetreatInterface,
    action_name: str,
    resolution_model: str,
    direct_pairs: List[Tuple[str, str]],
    max_direct_pairs: int,
) -> List[CaseSpec]:
    """Build the direct, raw, and end-to-end cases for one target set."""
    cases: List[CaseSpec] = []
    for rule_name, requirement_name in direct_pairs[:max_direct_pairs]:
        cases.append(
            CaseSpec(
                label=f'direct_fetch_impact[{rule_name}|{requirement_name}]',
                runner=lambda rule_name=rule_name, requirement_name=requirement_name: (
                    kb_interface.fetch_tactic_rule_impacts_requirement(
                        requirement_name, rule_name)
                ),
            )
        )

    raw_all_pairs_query = f"""
        match
            $interface isa ROSInterface, has interface_name '{action_name}';
            $rm isa resolution_model, has resolution_model_name '{resolution_model}';
            let $tr in applicable_tactics($interface, $rm);
            $req isa relaxed_requirement, has in_effect true;
            let $fulfillment = tactic_rule_impacts_requirement_fulfillment($tr, $req);
        fetch {{
            "rule_name": $tr.rule_name,
            "requirement_name": $req.requirement_name,
            "fulfillment": $fulfillment
        }};
    """
    cases.append(
        CaseSpec(
            label='raw_function_all_pairs',
            runner=lambda query=raw_all_pairs_query: kb_interface.fetch_database(query),
        )
    )
    cases.append(
        CaseSpec(
            label=f'fetch_potential_requirements_fulfillment[{action_name}]',
            runner=lambda: kb_interface.fetch_potential_requirements_fulfillment(
                action_name),
        )
    )
    cases.append(
        CaseSpec(
            label=(
                'fetch_potential_requirements_fulfillment['
                f'{action_name}|{resolution_model}]'
            ),
            runner=lambda: kb_interface.fetch_potential_requirements_fulfillment(
                action_name,
                resolution_model=resolution_model,
            ),
        )
    )
    cases.append(
        CaseSpec(
            label=(
                'get_potential_requirements_fulfillment['
                f'{action_name}|{resolution_model}]'
            ),
            runner=lambda: kb_interface.get_potential_requirements_fulfillment(
                action_name,
                resolution_model=resolution_model,
            ),
        )
    )
    return cases


def collect_semantic_snapshot(
    kb_interface: TacticalRetreatInterface,
    action_name: str,
    resolution_model: str,
    direct_pairs: List[Tuple[str, str]],
    max_direct_pairs: int,
) -> Dict[str, List[dict]]:
    """Collect canonical results for semantic-equivalence checks."""
    snapshot: Dict[str, List[dict]] = {}
    for rule_name, requirement_name in direct_pairs[:max_direct_pairs]:
        label = f'direct_fetch_impact[{rule_name}|{requirement_name}]'
        snapshot[label] = canonical_rows(
            kb_interface.fetch_tactic_rule_impacts_requirement(
                requirement_name,
                rule_name,
            )
        )

    snapshot['raw_function_all_pairs'] = canonical_rows(
        kb_interface.fetch_database(
            f"""
                match
                    $interface isa ROSInterface, has interface_name '{action_name}';
                    $rm isa resolution_model, has resolution_model_name '{resolution_model}';
                    let $tr in applicable_tactics($interface, $rm);
                    $req isa relaxed_requirement, has in_effect true;
                    let $fulfillment = tactic_rule_impacts_requirement_fulfillment($tr, $req);
                fetch {{
                    "rule_name": $tr.rule_name,
                    "requirement_name": $req.requirement_name,
                    "fulfillment": $fulfillment
                }};
            """
        )
    )
    snapshot[
        f'fetch_potential_requirements_fulfillment[{action_name}|{resolution_model}]'
    ] = canonical_rows(
        kb_interface.fetch_potential_requirements_fulfillment(
            action_name,
            resolution_model=resolution_model,
        )
    )
    snapshot[
        f'get_potential_requirements_fulfillment[{action_name}|{resolution_model}]'
    ] = canonical_rows(
        kb_interface.get_potential_requirements_fulfillment(
            action_name,
            resolution_model=resolution_model,
        )
    )
    return snapshot


def compare_snapshots(
    baseline_snapshot: Dict[str, List[dict]],
    candidate_snapshot: Dict[str, List[dict]],
) -> List[str]:
    """Return the labels whose canonical results changed."""
    mismatches = []
    for label, expected in baseline_snapshot.items():
        if candidate_snapshot.get(label) != expected:
            mismatches.append(label)
    return mismatches


def run_variant(
    variant_name: str,
    schema_text: str,
    base_schema_paths: List[str],
    data_paths: List[str],
    address: str,
    db_prefix: str,
    warm_runs: int,
    max_direct_pairs: int,
    reference_targets: Tuple[str, str, List[Tuple[str, str]]] | None,
    baseline_snapshot: Dict[str, List[dict]] | None,
) -> Dict:
    """Run one schema variant and collect benchmark plus semantic data."""
    with tempfile.TemporaryDirectory(prefix='typedb_req_variant_') as tmp_dir:
        variant_schema_path = Path(tmp_dir) / f'{variant_name}.tql'
        variant_schema_path.write_text(schema_text)
        schema_paths = build_variant_schema_paths(base_schema_paths, variant_schema_path)
        db_name = f'{db_prefix}_{variant_name}_{uuid.uuid4().hex[:8]}'
        kb_interface = TacticalRetreatInterface(
            address,
            db_name,
            schema_paths,
            data_paths,
            force_database=True,
            force_data=True,
        )
        try:
            if reference_targets is None:
                action_name, resolution_model, direct_pairs = resolve_benchmark_targets(
                    kb_interface)
            else:
                action_name, resolution_model, direct_pairs = reference_targets

            cases = build_cases(
                kb_interface,
                action_name,
                resolution_model,
                direct_pairs,
                max_direct_pairs,
            )
            case_results = [benchmark_case(case, warm_runs) for case in cases]
            snapshot = collect_semantic_snapshot(
                kb_interface,
                action_name,
                resolution_model,
                direct_pairs,
                max_direct_pairs,
            )
            mismatches: List[str] = []
            if baseline_snapshot is not None:
                mismatches = compare_snapshots(baseline_snapshot, snapshot)

            target_label = f'fetch_potential_requirements_fulfillment[{action_name}]'
            target_result = next(
                case_result for case_result in case_results
                if case_result['label'] == target_label
            )
            return {
                'variant': variant_name,
                'action_name': action_name,
                'resolution_model': resolution_model,
                'direct_pairs': direct_pairs,
                'case_results': case_results,
                'target_case': target_result,
                'semantic_mismatches': mismatches,
                'semantic_snapshot': snapshot,
            }
        finally:
            with suppress(Exception):
                kb_interface.delete_database()


def rank_variants(reports: List[Dict]) -> List[Dict]:
    """Rank variants by warm target latency, then cold target latency."""
    def key(report: Dict) -> Tuple[float, float, int]:
        if report.get('benchmark_error'):
            return (float('inf'), float('inf'), float('inf'))
        target = report['target_case']
        return (
            target['warm_p50_ms'],
            target['cold_ms'],
            len(report['semantic_mismatches']),
        )

    return sorted(reports, key=key)


def print_text_report(reports: List[Dict], ranking: List[Dict]) -> None:
    """Print a human-readable comparison."""
    for report in reports:
        print(f"=== variant={report['variant']} ===")
        if report.get('benchmark_error'):
            print(f"benchmark_error={report['benchmark_error']}")
            print('')
            continue
        print(
            f"target action={report['action_name']} "
            f"resolution_model={report['resolution_model']}"
        )
        if report['semantic_mismatches']:
            print('semantic_mismatches=' + ', '.join(report['semantic_mismatches']))
        else:
            print('semantic_mismatches=none')
        for case_result in report['case_results']:
            print(
                f"  - {case_result['label']}: "
                f"cold={case_result['cold_ms']:.3f}ms "
                f"warm_avg={case_result['warm_avg_ms']:.3f}ms "
                f"warm_p50={case_result['warm_p50_ms']:.3f}ms "
                f"warm_p95={case_result['warm_p95_ms']:.3f}ms "
                f"rows={case_result['row_count_min']}..{case_result['row_count_max']}"
            )
        print('')

    print('=== ranking_by_target_warm_p50 ===')
    for index, report in enumerate(ranking, start=1):
        if report.get('benchmark_error'):
            print(
                f"{index}. {report['variant']}: "
                f"benchmark_error={report['benchmark_error']}"
            )
            continue
        target = report['target_case']
        print(
            f"{index}. {report['variant']}: "
            f"warm_p50={target['warm_p50_ms']:.3f}ms "
            f"cold={target['cold_ms']:.3f}ms "
            f"mismatches={len(report['semantic_mismatches'])}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Benchmark requirement-impact schema variants.'
    )
    parser.add_argument(
        '--address',
        default='localhost:1729',
        help='TypeDB address (default: localhost:1729).',
    )
    parser.add_argument(
        '--data-profile',
        choices=['benchmark', 'legacy'],
        default='benchmark',
        help='Dataset profile to use (default: benchmark).',
    )
    parser.add_argument(
        '--warm-runs',
        type=int,
        default=20,
        help='Warm invocations after one cold invocation (default: 20).',
    )
    parser.add_argument(
        '--max-direct-pairs',
        type=int,
        default=10,
        help='Maximum direct rule/requirement pairs to benchmark (default: 10).',
    )
    parser.add_argument(
        '--db-prefix',
        default='benchmark_req_impact',
        help='Database prefix (default: benchmark_req_impact).',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text).',
    )
    parser.add_argument(
        '--variants',
        nargs='*',
        default=None,
        help=(
            'Optional subset of variant names to run in addition to baseline '
            '(space-separated).'
        ),
    )
    args = parser.parse_args()

    if args.warm_runs < 1:
        parser.error('--warm-runs must be >= 1')
    if args.max_direct_pairs < 1:
        parser.error('--max-direct-pairs must be >= 1')

    benchmark_queries = load_benchmark_queries_module()
    base_schema_paths = list(benchmark_queries.DEFAULT_SCHEMAS)
    data_paths = list(benchmark_queries.DATA_PROFILES[args.data_profile])
    base_schema_text = DISCOVER_SCHEMA_PATH.read_text()
    variants = build_variant_texts(base_schema_text)
    if args.variants:
        unknown_variants = sorted(set(args.variants) - set(variants.keys()))
        if unknown_variants:
            parser.error('Unknown variant(s): ' + ', '.join(unknown_variants))
        selected_variants = set(args.variants)
    else:
        selected_variants = set(variants.keys())
    selected_variants.add('baseline')

    reports: List[Dict] = []
    baseline_report = run_variant(
        variant_name='baseline',
        schema_text=variants['baseline'],
        base_schema_paths=base_schema_paths,
        data_paths=data_paths,
        address=args.address,
        db_prefix=args.db_prefix,
        warm_runs=args.warm_runs,
        max_direct_pairs=args.max_direct_pairs,
        reference_targets=None,
        baseline_snapshot=None,
    )
    reports.append(baseline_report)

    reference_targets = (
        baseline_report['action_name'],
        baseline_report['resolution_model'],
        baseline_report['direct_pairs'],
    )
    for variant_name, schema_text in variants.items():
        if variant_name == 'baseline':
            continue
        if variant_name not in selected_variants:
            continue
        try:
            with suppress_benchmark_logging():
                reports.append(
                    run_variant(
                        variant_name=variant_name,
                        schema_text=schema_text,
                        base_schema_paths=base_schema_paths,
                        data_paths=data_paths,
                        address=args.address,
                        db_prefix=args.db_prefix,
                        warm_runs=args.warm_runs,
                        max_direct_pairs=args.max_direct_pairs,
                        reference_targets=reference_targets,
                        baseline_snapshot=baseline_report['semantic_snapshot'],
                    )
                )
        except Exception as err:  # pylint: disable=broad-exception-caught
            reports.append({
                'variant': variant_name,
                'benchmark_error': str(err),
                'semantic_mismatches': ['benchmark_error'],
                'target_case': {
                    'warm_p50_ms': float('inf'),
                    'cold_ms': float('inf'),
                },
            })

    ranking = rank_variants(reports)
    final_report = {
        'data_profile': args.data_profile,
        'warm_runs': args.warm_runs,
        'max_direct_pairs': args.max_direct_pairs,
        'reports': reports,
        'ranking': [
            {
                'variant': report['variant'],
                'target_warm_p50_ms': report['target_case'].get('warm_p50_ms'),
                'target_cold_ms': report['target_case'].get('cold_ms'),
                'semantic_mismatches': report['semantic_mismatches'],
                'benchmark_error': report.get('benchmark_error'),
            } for report in ranking
        ],
        'recommended_variant': next(
            (
                report['variant']
                for report in ranking
                if (
                    not report['semantic_mismatches']
                    and not report.get('benchmark_error')
                )
            ),
            None,
        ),
    }

    if args.format == 'json':
        print(json.dumps(final_report, indent=2))
        return
    print_text_report(reports, ranking)
    print('')
    print(f"recommended_variant={final_report['recommended_variant']}")


if __name__ == '__main__':
    main()
