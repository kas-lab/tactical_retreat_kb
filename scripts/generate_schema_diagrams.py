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
"""Generate diagrams for TypeDB schema files in typedb_tactics."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable


@dataclass(frozen=True)
class SchemaDiagramAPI:
    """Subset of ros_typedb_tools schema diagram API used by this script."""

    parse_schema_file: object
    write_graph: object


def _load_schema_diagram_api() -> SchemaDiagramAPI:
    """Load ros_typedb_tools schema utilities from installed env or source tree."""
    try:
        from ros_typedb_tools.schema_diagram import parse_schema_file
        from ros_typedb_tools.schema_diagram import write_graph
        return SchemaDiagramAPI(parse_schema_file=parse_schema_file, write_graph=write_graph)
    except ImportError:
        script_path = Path(__file__).resolve()
        candidate = script_path.parents[2] / 'ros_typedb' / 'ros_typedb_tools'
        if candidate.is_dir():
            sys.path.insert(0, str(candidate))
            from ros_typedb_tools.schema_diagram import parse_schema_file
            from ros_typedb_tools.schema_diagram import write_graph
            return SchemaDiagramAPI(parse_schema_file=parse_schema_file, write_graph=write_graph)

    raise RuntimeError(
        'Could not import ros_typedb_tools.schema_diagram. '
        'Install ros_typedb_tools or run from this workspace source tree.'
    )


def discover_schema_files(
    schemas_root: Path,
    include_examples: bool = False,
    include_queries: bool = False,
) -> list[Path]:
    """Discover schema .tql files under schemas_root respecting filters."""
    schemas_root = Path(schemas_root)
    if not schemas_root.is_dir():
        raise FileNotFoundError(f'Schemas directory not found: {schemas_root}')

    selected: list[Path] = []
    for schema_file in sorted(schemas_root.rglob('*.tql')):
        relative_path = schema_file.relative_to(schemas_root)
        is_query = 'queries' in relative_path.parts
        is_example = schema_file.stem.endswith('_example')

        if not include_queries and is_query:
            continue
        if not include_examples and is_example:
            continue
        if not is_query and not is_example and not _is_define_schema_file(schema_file):
            continue
        selected.append(schema_file)
    return selected


def _build_output_paths(
    schema_files: Iterable[Path],
    schemas_root: Path,
    output_dir: Path,
    output_format: str,
) -> dict[Path, Path]:
    output_dir = Path(output_dir)
    outputs: dict[Path, Path] = {}
    occupied: set[str] = set()

    schema_list = list(schema_files)
    stem_counts: dict[str, int] = {}
    for schema_file in schema_list:
        stem_counts[schema_file.stem] = stem_counts.get(schema_file.stem, 0) + 1

    for schema_file in schema_list:
        stem = schema_file.stem
        if stem_counts[stem] == 1:
            candidate_name = f'{stem}.{output_format}'
        else:
            rel_parent = schema_file.relative_to(schemas_root).parent
            parent_hint = '_'.join(rel_parent.parts) if rel_parent.parts else 'root'
            candidate_name = f'{stem}__{parent_hint}.{output_format}'

        unique_name = _deduplicate_name(candidate_name, occupied)
        occupied.add(unique_name)
        outputs[schema_file] = output_dir / unique_name

    return outputs


def generate_schema_diagrams(
    schemas_root: Path,
    output_dir: Path,
    output_format: str = 'svg',
    orientation: str = 'vertical',
    include_examples: bool = False,
    include_queries: bool = False,
    api: SchemaDiagramAPI | None = None,
) -> list[Path]:
    """Generate diagrams for discovered schema files and return output paths."""
    schema_files = discover_schema_files(
        schemas_root=schemas_root,
        include_examples=include_examples,
        include_queries=include_queries,
    )
    if not schema_files:
        return []

    output_map = _build_output_paths(schema_files, schemas_root, output_dir, output_format)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    schema_api = api if api is not None else _load_schema_diagram_api()
    generated: list[Path] = []
    for schema_file in schema_files:
        output_path = output_map[schema_file]
        model = schema_api.parse_schema_file(schema_file)
        schema_api.write_graph(
            model,
            output_path=output_path,
            output_format=output_format,
            orientation=orientation,
        )
        generated.append(output_path)

    return generated


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for bulk schema diagram generation."""
    parser = argparse.ArgumentParser(
        prog='generate_schema_diagrams.py',
        description='Generate diagrams for typedb_tactics schema files.',
    )
    script_path = Path(__file__).resolve()
    default_schemas_root = script_path.parents[1] / 'schemas'
    default_output_dir = script_path.parents[1] / 'schemas_diagrams'

    parser.add_argument(
        '--schemas-root',
        type=Path,
        default=default_schemas_root,
        help=f'Directory containing schema .tql files (default: {default_schemas_root}).',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=default_output_dir,
        help=f'Directory for generated diagrams (default: {default_output_dir}).',
    )
    parser.add_argument(
        '--format',
        choices=['svg', 'dot'],
        default='svg',
        help='Output format (default: svg).',
    )
    parser.add_argument(
        '--orientation',
        choices=['vertical', 'horizontal'],
        default='vertical',
        help='Diagram orientation (default: vertical).',
    )
    parser.add_argument(
        '--include-examples',
        action='store_true',
        help='Include schema files ending with _example.tql.',
    )
    parser.add_argument(
        '--include-queries',
        action='store_true',
        help='Include .tql files under any queries/ subdirectory.',
    )
    return parser


def _is_define_schema_file(schema_file: Path) -> bool:
    text = schema_file.read_text(encoding='utf-8')
    cleaned = '\n'.join(line.split('#', maxsplit=1)[0] for line in text.splitlines())
    return re.search(r'\bdefine\b', cleaned, flags=re.IGNORECASE) is not None


def _deduplicate_name(candidate_name: str, occupied: set[str]) -> str:
    if candidate_name not in occupied:
        return candidate_name

    stem = Path(candidate_name).stem
    suffix = Path(candidate_name).suffix
    index = 2
    while True:
        new_name = f'{stem}__{index}{suffix}'
        if new_name not in occupied:
            return new_name
        index += 1


def main(argv: list[str] | None = None) -> int:
    """Run bulk schema diagram generation."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        outputs = generate_schema_diagrams(
            schemas_root=args.schemas_root,
            output_dir=args.output_dir,
            output_format=args.format,
            orientation=args.orientation,
            include_examples=args.include_examples,
            include_queries=args.include_queries,
        )
    except Exception as exc:
        print(f'Failed to generate diagrams: {exc}', file=sys.stderr)
        return 1

    if not outputs:
        print('No schema files matched the selection filters.')
        return 0

    print(f'Generated {len(outputs)} schema diagram(s) in {args.output_dir}')
    for output in outputs:
        print(f' - {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
