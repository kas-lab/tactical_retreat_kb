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
"""Generate a single merged schema diagram for typedb_tactics."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable


DEFAULT_IGNORED_SCHEMA_FILENAMES = {
    "discover_hypothetical_req_fulfillment.tql",
    "discover_tactics_model.tql",
}


@dataclass(frozen=True)
class SchemaDiagramAPI:
    """Subset of ros_typedb_tools schema diagram API used by this script."""

    parse_schema_files: object
    write_graph: object


def _load_schema_diagram_api() -> SchemaDiagramAPI:
    """Load ros_typedb_tools schema utilities from installed env or source tree."""
    try:
        from ros_typedb_tools.schema_diagram import parse_schema_files
        from ros_typedb_tools.schema_diagram import write_graph
        return SchemaDiagramAPI(parse_schema_files=parse_schema_files, write_graph=write_graph)
    except ImportError:
        script_path = Path(__file__).resolve()
        candidate = script_path.parents[2] / "ros_typedb" / "ros_typedb_tools"
        if candidate.is_dir():
            sys.path.insert(0, str(candidate))
            from ros_typedb_tools.schema_diagram import parse_schema_files
            from ros_typedb_tools.schema_diagram import write_graph
            return SchemaDiagramAPI(parse_schema_files=parse_schema_files, write_graph=write_graph)

    raise RuntimeError(
        "Could not import ros_typedb_tools.schema_diagram. "
        "Install ros_typedb_tools or run from this workspace source tree."
    )


def discover_schema_files_for_merge(
    schemas_root: Path,
    ignored_schema_filenames: Iterable[str],
    include_examples: bool = False,
    include_queries: bool = False,
) -> list[Path]:
    """Discover schema files for merge, applying ignore and content filters."""
    schemas_root = Path(schemas_root)
    if not schemas_root.is_dir():
        raise FileNotFoundError(f"Schemas directory not found: {schemas_root}")

    ignored = {name for name in ignored_schema_filenames}
    selected: list[Path] = []

    for schema_file in sorted(schemas_root.rglob("*.tql")):
        relative_path = schema_file.relative_to(schemas_root)
        is_query = "queries" in relative_path.parts
        is_example = schema_file.stem.endswith("_example")

        if schema_file.name in ignored:
            continue
        if not include_queries and is_query:
            continue
        if not include_examples and is_example:
            continue
        if not is_query and not is_example and not _is_define_schema_file(schema_file):
            continue
        selected.append(schema_file)

    return selected


def generate_merged_schema_diagram(
    schemas_root: Path,
    output_path: Path,
    output_format: str = "svg",
    orientation: str = "vertical",
    ignored_schema_filenames: Iterable[str] = (),
    include_examples: bool = False,
    include_queries: bool = False,
    api: SchemaDiagramAPI | None = None,
) -> tuple[Path | None, list[Path]]:
    """Generate one merged schema diagram and return output path and merged files."""
    schema_files = discover_schema_files_for_merge(
        schemas_root=schemas_root,
        ignored_schema_filenames=ignored_schema_filenames,
        include_examples=include_examples,
        include_queries=include_queries,
    )
    if not schema_files:
        return None, []

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema_api = api if api is not None else _load_schema_diagram_api()
    merged_schema = schema_api.parse_schema_files(schema_files)
    schema_api.write_graph(
        merged_schema,
        output_path=output_path,
        output_format=output_format,
        orientation=orientation,
    )

    return output_path, schema_files


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for merged schema diagram generation."""
    parser = argparse.ArgumentParser(
        prog="generate_merged_schema_diagram.py",
        description="Generate one merged diagram for typedb_tactics schema files.",
    )
    script_path = Path(__file__).resolve()
    default_schemas_root = script_path.parents[1] / "schemas"

    parser.add_argument(
        "--schemas-root",
        type=Path,
        default=default_schemas_root,
        help=f"Directory containing schema .tql files (default: {default_schemas_root}).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path for merged diagram. Defaults to "
        "<package>/schemas_diagrams/merged_schema.<format>.",
    )
    parser.add_argument(
        "--format",
        choices=["svg", "dot"],
        default="svg",
        help="Output format (default: svg).",
    )
    parser.add_argument(
        "--orientation",
        choices=["vertical", "horizontal"],
        default="vertical",
        help="Diagram orientation (default: vertical).",
    )
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help="Include schema files ending with _example.tql.",
    )
    parser.add_argument(
        "--include-queries",
        action="store_true",
        help="Include .tql files under any queries/ subdirectory.",
    )
    parser.add_argument(
        "--include-default-ignored",
        action="store_true",
        help="Include discovery schemas that are ignored by default.",
    )
    parser.add_argument(
        "--ignore-schema",
        action="append",
        default=[],
        help="Additional schema filename to ignore (can be passed multiple times).",
    )
    return parser


def _default_output_path(output_format: str) -> Path:
    script_path = Path(__file__).resolve()
    return script_path.parents[1] / "schemas_diagrams" / f"merged_schema.{output_format}"


def _is_define_schema_file(schema_file: Path) -> bool:
    text = schema_file.read_text(encoding="utf-8")
    cleaned = "\n".join(line.split("#", maxsplit=1)[0] for line in text.splitlines())
    return re.search(r"\bdefine\b", cleaned, flags=re.IGNORECASE) is not None


def main(argv: list[str] | None = None) -> int:
    """Run merged schema diagram generation."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    ignored_names = set(args.ignore_schema)
    if not args.include_default_ignored:
        ignored_names.update(DEFAULT_IGNORED_SCHEMA_FILENAMES)

    output_path = args.output if args.output is not None else _default_output_path(args.format)

    try:
        output_path, used_files = generate_merged_schema_diagram(
            schemas_root=args.schemas_root,
            output_path=output_path,
            output_format=args.format,
            orientation=args.orientation,
            ignored_schema_filenames=ignored_names,
            include_examples=args.include_examples,
            include_queries=args.include_queries,
        )
    except Exception as exc:
        print(f"Failed to generate merged schema diagram: {exc}", file=sys.stderr)
        return 1

    if output_path is None:
        print("No schema files matched the selection filters.")
        return 0

    print(f"Generated merged schema diagram: {output_path}")
    print(f"Merged {len(used_files)} schema file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
