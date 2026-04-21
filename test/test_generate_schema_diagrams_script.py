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

"""Tests for bulk schema diagram generation script."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_schema_diagrams.py"
    spec = importlib.util.spec_from_file_location("generate_schema_diagrams", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_schema(path: Path, content: str = "define\n\nThing sub entity;\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_schema_files_filters_queries_and_examples_by_default(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "core" / "alpha.tql")
    _write_schema(schemas_root / "core" / "not_a_schema.tql", "match $x isa Thing;")
    _write_schema(schemas_root / "core" / "alpha_example.tql")
    _write_schema(schemas_root / "core" / "queries" / "alpha_query.tql", "match $x isa Thing;")
    _write_schema(schemas_root / "feature" / "beta.tql")

    discovered = module.discover_schema_files(schemas_root)
    relative = {path.relative_to(schemas_root).as_posix() for path in discovered}

    assert relative == {"core/alpha.tql", "feature/beta.tql"}


def test_discover_schema_files_can_include_examples_and_queries(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "core" / "alpha.tql")
    _write_schema(schemas_root / "core" / "alpha_example.tql")
    _write_schema(schemas_root / "core" / "queries" / "alpha_query.tql", "match $x isa Thing;")

    discovered = module.discover_schema_files(
        schemas_root,
        include_examples=True,
        include_queries=True,
    )
    relative = {path.relative_to(schemas_root).as_posix() for path in discovered}

    assert relative == {
        "core/alpha.tql",
        "core/alpha_example.tql",
        "core/queries/alpha_query.tql",
    }


def test_generate_schema_diagrams_writes_outputs_with_selected_options(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    output_dir = tmp_path / "schemas_diagrams"

    _write_schema(schemas_root / "first" / "alpha.tql")
    _write_schema(schemas_root / "second" / "beta.tql")
    _write_schema(schemas_root / "second" / "beta_example.tql")
    _write_schema(schemas_root / "second" / "queries" / "beta_query.tql", "match $x isa Thing;")

    calls = []

    class FakeAPI:
        def parse_schema_file(self, schema_path: Path):
            return {"schema": schema_path}

        def write_graph(self, model, output_path: Path, output_format: str, orientation: str):
            calls.append(
                {
                    "schema": model["schema"].name,
                    "output": Path(output_path).name,
                    "format": output_format,
                    "orientation": orientation,
                }
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("digraph typedb_schema {}", encoding="utf-8")

    outputs = module.generate_schema_diagrams(
        schemas_root=schemas_root,
        output_dir=output_dir,
        output_format="dot",
        orientation="horizontal",
        include_examples=False,
        include_queries=False,
        api=FakeAPI(),
    )

    assert {path.name for path in outputs} == {"alpha.dot", "beta.dot"}
    assert all(path.exists() for path in outputs)
    assert {call["schema"] for call in calls} == {"alpha.tql", "beta.tql"}
    assert {call["format"] for call in calls} == {"dot"}
    assert {call["orientation"] for call in calls} == {"horizontal"}


def test_generate_schema_diagrams_handles_duplicate_stems_without_aborting(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    output_dir = tmp_path / "schemas_diagrams"

    _write_schema(schemas_root / "alpha" / "shared.tql")
    _write_schema(schemas_root / "beta" / "shared.tql")

    class FakeAPI:
        def parse_schema_file(self, schema_path: Path):
            return {"schema": schema_path}

        def write_graph(self, model, output_path: Path, output_format: str, orientation: str):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("digraph typedb_schema {}", encoding="utf-8")

    outputs = module.generate_schema_diagrams(
        schemas_root=schemas_root,
        output_dir=output_dir,
        output_format="dot",
        orientation="vertical",
        api=FakeAPI(),
    )

    output_names = {path.name for path in outputs}
    assert len(output_names) == 2
    assert all(name.startswith("shared") and name.endswith(".dot") for name in output_names)
    assert all("__" in name for name in output_names)


def test_load_schema_diagram_api_source_tree_fallback(monkeypatch):
    module = _load_script_module()
    script_path = Path(module.__file__).resolve()
    candidate = script_path.parents[2] / "ros_typedb" / "ros_typedb_tools"

    path_without_candidate = [entry for entry in module.sys.path if entry != str(candidate)]
    monkeypatch.setattr(module.sys, "path", path_without_candidate)
    module.sys.modules.pop("ros_typedb_tools", None)
    module.sys.modules.pop("ros_typedb_tools.schema_diagram", None)

    original_import = builtins.__import__
    state = {"forced": False}

    def import_with_forced_first_failure(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ros_typedb_tools.schema_diagram" and not state["forced"]:
            state["forced"] = True
            raise ImportError("forced import failure for fallback path")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_forced_first_failure)

    api = module._load_schema_diagram_api()

    assert state["forced"] is True
    assert module.sys.path[0] == str(candidate)
    assert callable(api.parse_schema_file)
    assert callable(api.write_graph)
