# Style and conventions

- Language: Python.
- Packaging/build: ROS 2 `ament_python` package (`package.xml` + `setup.py` + `setup.cfg`).
- Naming follows standard Python conventions: modules and functions use `snake_case`, classes use `PascalCase`, constants use `UPPER_CASE`.
- The codebase uses type hints regularly, including modern unions like `list[str] | str` and `TypedDict`/`dataclass` for structured results.
- Existing code often imports individual typing names (`Optional`, `List`, `Union`, etc.) rather than `import typing as t`; follow local style in touched files.
- Docstrings are present for some public data structures and are enforced through `ament_pep257`; new public code should include concise docstrings where appropriate.
- Lint/style is enforced by tests `test_flake8` and `test_pep257`; treat those as mandatory gates for all changes.
- Python files use the Apache 2.0 copyright/license header already present in the repository; preserve it and add it to new Python files.
- Query performance convention: runtime fetches should be unordered by default; only use ordered/sorted fetch behavior when deterministic ordering is required, especially in tests.
- TypeDB rule authoring constraints to remember:
  - do not create a relation and assign attributes to it in the same `then` clause
  - variables used in `then` must be bound in `when` outside nested patterns
  - avoid negation cycles (`not {}` cannot both read and write the same predicate)
  - prefer minimal schema edits, usually subtyping existing relations instead of introducing parallel ones
- Compatibility convention: if constructor or fetch APIs change, verify compatibility with the `ros_typedb` version used by the workspace/container.