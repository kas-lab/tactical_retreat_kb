# CLAUDE.md

Claude-specific notes for this repository.

## Canonical instructions

- Use [AGENTS.md](AGENTS.md) as the single source of truth.
- Skim [agent-docs/agent-notes.md](agent-docs/agent-notes.md) as a pre-implementation checklist.

## Scope

- Do not duplicate commands or workflow here.
- If this file conflicts with `AGENTS.md`, follow `AGENTS.md`.

## Context

- This package is migrated to **TypeDB 3**. Do not use TypeDB 2 syntax (rules, `isa!`, old driver API).
  - Exception: `isa!` **is** valid inside `fun` match bodies for exact-type dispatch in OR branches (e.g. `$x isa! FuzzySigmoid`). The restriction applies to schema *definitions*, not function bodies.

## Testing

- Test data files (`test/data/*.tql`) are single `insert` blocks; variables declared earlier in the block are reusable by later statements.
- When auditing schema function test coverage: check **every OR branch** of every `fun` has at least one test case that hits that branch. Dispatching functions like `quantified_value_fuzzy_expression` (4 branches: ValueSingleton+double/integer, Measure+double/integer) are easy to miss.
