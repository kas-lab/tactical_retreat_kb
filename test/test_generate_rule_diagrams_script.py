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
"""Tests for bulk rule diagram generation script."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_rule_diagrams.py"
    spec = importlib.util.spec_from_file_location("generate_rule_diagrams", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_schema(path: Path, content: str = "define\n\nThing sub entity;\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_rule_files_filters_queries_examples_and_rule_free_files(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "core" / "with_rules.tql", "define\nrule r:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "core" / "rule_free.tql", "define\nThing sub entity;")
    _write_schema(schemas_root / "core" / "with_rules_example.tql", "define\nrule ex:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "core" / "queries" / "query_rule.tql", "define\nrule q:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")

    discovered = module.discover_rule_files(schemas_root)
    relative = {path.relative_to(schemas_root).as_posix() for path in discovered}

    assert relative == {"core/with_rules.tql"}


def test_discover_rule_files_can_include_examples_and_queries(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"

    _write_schema(schemas_root / "core" / "with_rules.tql", "define\nrule r:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "core" / "with_rules_example.tql", "define\nrule ex:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "core" / "queries" / "query_rule.tql", "define\nrule q:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")

    discovered = module.discover_rule_files(schemas_root, include_examples=True, include_queries=True)
    relative = {path.relative_to(schemas_root).as_posix() for path in discovered}

    assert relative == {
        "core/with_rules.tql",
        "core/with_rules_example.tql",
        "core/queries/query_rule.tql",
    }


def test_generate_rule_diagrams_writes_outputs_with_selected_options(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    output_dir = tmp_path / "schemas_diagrams" / "rules"

    _write_schema(schemas_root / "first" / "alpha.tql", "define\nrule a:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "second" / "beta.tql", "define\nrule b:\nwhen { $x isa Thing; }\nthen { $x has done true; };")
    _write_schema(schemas_root / "second" / "rule_free.tql", "define\nThing sub entity;")

    calls = []

    class FakeAPI:
        def parse_rule_file(self, schema_path: Path):
            return {"schema": schema_path}

        def write_rule_graph(self, model, output_path: Path, output_format: str, orientation: str):
            calls.append(
                {
                    "schema": model["schema"].name,
                    "output": Path(output_path).name,
                    "format": output_format,
                    "orientation": orientation,
                }
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("digraph typedb_rule_graph {}", encoding="utf-8")

    outputs = module.generate_rule_diagrams(
        schemas_root=schemas_root,
        output_dir=output_dir,
        output_format="dot",
        orientation="horizontal",
        api=FakeAPI(),
    )

    assert {path.name for path in outputs} == {"alpha_rules.dot", "beta_rules.dot"}
    assert all(path.exists() for path in outputs)
    assert {call["schema"] for call in calls} == {"alpha.tql", "beta.tql"}
    assert {call["format"] for call in calls} == {"dot"}
    assert {call["orientation"] for call in calls} == {"horizontal"}


def test_generate_rule_diagrams_handles_duplicate_stems_without_aborting(tmp_path: Path):
    module = _load_script_module()
    schemas_root = tmp_path / "schemas"
    output_dir = tmp_path / "schemas_diagrams" / "rules"

    _write_schema(schemas_root / "alpha" / "shared.tql", "define\nrule a:\nwhen { $x isa Thing; }\nthen { $x has mark true; };")
    _write_schema(schemas_root / "beta" / "shared.tql", "define\nrule b:\nwhen { $x isa Thing; }\nthen { $x has done true; };")

    class FakeAPI:
        def parse_rule_file(self, schema_path: Path):
            return {"schema": schema_path}

        def write_rule_graph(self, model, output_path: Path, output_format: str, orientation: str):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("digraph typedb_rule_graph {}", encoding="utf-8")

    outputs = module.generate_rule_diagrams(
        schemas_root=schemas_root,
        output_dir=output_dir,
        output_format="dot",
        orientation="vertical",
        api=FakeAPI(),
    )

    output_names = {path.name for path in outputs}
    assert len(output_names) == 2
    assert all(name.startswith("shared_rules") and name.endswith(".dot") for name in output_names)
    assert all("__" in name for name in output_names)


def test_load_rule_diagram_api_source_tree_fallback(monkeypatch):
    module = _load_script_module()
    script_path = Path(module.__file__).resolve()
    candidate = script_path.parents[2] / "ros_typedb" / "ros_typedb_tools"

    path_without_candidate = [entry for entry in module.sys.path if entry != str(candidate)]
    monkeypatch.setattr(module.sys, "path", path_without_candidate)
    module.sys.modules.pop("ros_typedb_tools", None)
    module.sys.modules.pop("ros_typedb_tools.rule_diagram", None)

    original_import = builtins.__import__
    state = {"forced": False}

    def import_with_forced_first_failure(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ros_typedb_tools.rule_diagram" and not state["forced"]:
            state["forced"] = True
            raise ImportError("forced import failure for fallback path")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_forced_first_failure)

    api = module._load_rule_diagram_api()

    assert state["forced"] is True
    assert module.sys.path[0] == str(candidate)
    assert callable(api.parse_rule_file)
    assert callable(api.write_rule_graph)
