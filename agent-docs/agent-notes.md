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

## Guardrails

- Do not reintroduce `infer` parameters.
- Keep query failures explicit (`TypeDBQueryError`) unless call sites intentionally handle fallback.
