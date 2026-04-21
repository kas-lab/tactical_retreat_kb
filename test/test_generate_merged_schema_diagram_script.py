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

"""Tests for merged schema diagram generation script."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_merged_schema_diagram.py"
    spec = importlib.util.spec_from_file_location("generate_merged_schema_diagram", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_schema(path: Path, content: str = "define\nThing sub entity;\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovery_for_merge_ignores_default_exclusions_and_non_schema_files(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "base" / "core.tql")
    _write_schema(schemas_root / "base" / "discover_tactics_model.tql")
    _write_schema(schemas_root / "base" / "discover_hypothetical_req_fulfillment.tql")
    _write_schema(schemas_root / "base" / "runtime_insert.tql", "insert $x isa Thing;")
    _write_schema(schemas_root / "base" / "core_example.tql")
    _write_schema(schemas_root / "base" / "queries" / "fetch_data.tql", "match $x isa Thing;")

    discovered = module.discover_schema_files_for_merge(
        schemas_root,
        ignored_schema_filenames=module.DEFAULT_IGNORED_SCHEMA_FILENAMES,
    )

    assert [path.name for path in discovered] == ["core.tql"]


def test_discovery_for_merge_can_include_default_ignored_files(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "discover_tactics_model.tql")
    _write_schema(schemas_root / "discover_hypothetical_req_fulfillment.tql")

    discovered = module.discover_schema_files_for_merge(
        schemas_root,
        ignored_schema_filenames=[],
    )

    assert {path.name for path in discovered} == {
        "discover_hypothetical_req_fulfillment.tql",
        "discover_tactics_model.tql",
    }


def test_generate_merged_schema_diagram_uses_filtered_inputs(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    output_path = tmp_path / "schemas_diagrams" / "merged.dot"

    _write_schema(schemas_root / "first" / "alpha.tql")
    _write_schema(schemas_root / "second" / "discover_tactics_model.tql")
    _write_schema(schemas_root / "second" / "beta.tql")

    seen_inputs = []
    seen_write = []

    class FakeAPI:
        def parse_schema_files(self, schema_paths):
            seen_inputs.extend(path.name for path in schema_paths)
            return {"merged": True}

        def write_graph(self, model, output_path, output_format, orientation):
            seen_write.append((model, Path(output_path), output_format, orientation))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("digraph typedb_schema {}", encoding="utf-8")

    generated_output, merged_files = module.generate_merged_schema_diagram(
        schemas_root=schemas_root,
        output_path=output_path,
        output_format="dot",
        orientation="horizontal",
        ignored_schema_filenames=module.DEFAULT_IGNORED_SCHEMA_FILENAMES,
        api=FakeAPI(),
    )

    assert generated_output == output_path
    assert output_path.exists()
    assert set(seen_inputs) == {"alpha.tql", "beta.tql"}
    assert len(merged_files) == 2
    assert seen_write[0][2] == "dot"
    assert seen_write[0][3] == "horizontal"


def test_main_defaults_output_extension_to_requested_format(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    _write_schema(schemas_root / "alpha.tql")

    seen = {}

    def fake_generate_merged_schema_diagram(**kwargs):
        seen.update(kwargs)
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("digraph typedb_schema {}", encoding="utf-8")
        return output_path, [schemas_root / "alpha.tql"]

    monkeypatch.setattr(module, "generate_merged_schema_diagram", fake_generate_merged_schema_diagram)

    rc = module.main(["--schemas-root", str(schemas_root), "--format", "dot"])

    assert rc == 0
    assert Path(seen["output_path"]).name == "merged_schema.dot"
