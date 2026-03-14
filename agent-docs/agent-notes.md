# Agent Notes

Quick checklist for agents. Canonical commands and workflow live in [../AGENTS.md](../AGENTS.md).
Schema/module context lives in [schema-guide.md](schema-guide.md).

## Before coding

- Confirm container `tactical_retreat` is running.
- Confirm TypeDB server is available in that container.

## Before finishing

- Follow the required build/test/lint flow in `AGENTS.md`.
- Include executed commands and pass/fail summary in the final report.
- Ensure Python files follow `flake8` and `pep257`.
- Ensure new/edited Python files keep the required Apache 2.0 copyright header (template in `AGENTS.md`).
- If you changed benchmark tooling, remember the user-facing scripts live in `scripts/benchmark/`, not directly in `scripts/`.

## Guardrails

- Do not reintroduce `infer` parameters.
- Keep query failures explicit (`TypeDBQueryError`) unless call sites intentionally handle fallback.
- Do not make the benchmark-validation tests part of the default package suite again unless explicitly requested.
- Do not make `connected_nodes()` recurse through `neighbours()`; keep the `direct_neighbours()` split.
