# logical_expressions schema

## Purpose

This folder models boolean and fuzzy expressions used in tactic antecedents,
requirement definitions, and hypothetical fulfillment analysis.

It provides:

- crisp logical expressions (comparisons, propositional atoms, NOT/AND/OR),
- fuzzy sets and fuzzy operators,
- extension files that connect expression operands to project entities.

## Main files

- `logical_expression.tql`: base logical expression model.
- `logical_expression_ext.tql`: bridges logical operands to `Measure` and `Value`.
- `fuzzy_expression.tql`: fuzzy sets and fuzzy expression operators.
- `fuzzy_expression_ext.tql`: extra role ownership/bridges for fuzzy composition.

## Crisp logic model

The logical layer follows a multi-sorted, quantifier-free first-order fragment over typed
runtime variables (`Measure`, `Value*`). In practice:

- terms are typed (`bool`, `integer`, `double`, `string`, arrays),
- atomic predicates compare compatible typed operands or use propositional atoms,
- negation is intended at literal level,
- composed formulas are built with relation graph structure (`not`/`and`/`or`).

This is aligned with the project goal of evaluating preconditions and requirement expressions
from runtime KB state without introducing explicit quantifier reasoning.

### Expression hierarchy

- `expression` (abstract): keyed by `expression_name`.
- `logical_expression` (abstract): has boolean `expression_satisfied`.
- `atomic_expression`: base for literals.
- `compound_expression`: base for operators.

### Atomic expression types

- `propositional_expression(atom)`.
- `comparison_expression(lhs_value, rhs_value)` with typed comparison subtypes:
  `less_than`, `less_than_equal`, `greater_than`, `greater_than_equal`, `equal`, `not_equal`.

### Compound expression types

- `not_expression(expression)`.
- `and_expression(expression...)`.
- `or_expression(expression...)`.

## Fuzzy model

### Fuzzy sets

- `FuzzySet` with concrete families:
  - Ascending: `FuzzyExponentialSaturation`, `FuzzySigmoid`, `FuzzyBoundedLinearFraction`.
  - Decaying: `FuzzyExponentialDecay`, `FuzzyRationalDecay`.
  - Unimodal: `FuzzyTriangular`, `FuzzyGaussian`.

### Fuzzy expressions

- `fuzzy_expression` stores `membership_degree` and can store `quantified_value`.
- `fuzzy_comparison_expression` binds a `term` and can use
  `fuzzy_decay_expression`, `fuzzy_ascend_expression`, `fuzzy_unimodal_expression`.
- Fuzzy operators: `fuzzy_and`, `fuzzy_or`, `fuzzy_not`.

The fuzzy layer is used as the practical runtime approximation for temporal/quality requirements
where binary satisfaction is too strict. Membership values in `[0, 1]` encode degree of
satisfaction and compose through fuzzy operators.

## FBTL/RELAX context

In the original design notes, this layer supports a fuzzy branching temporal logic style used by
RELAX requirements. Runtime evaluation in this repository is pointwise (current-state centered)
and tied to current monitored context values, with temporal operators approximated through the
relaxed model semantics.

## Extension files

- `logical_expression_ext.tql` maps `Measure` and `Value` to comparison/propositional roles.
- `fuzzy_expression_ext.tql` lets atomic and negated crisp expressions participate in fuzzy
  operator composition and hold `membership_degree` where needed.

## Notes on TypeDB 3 migration status

- Legacy rule blocks for fuzzy membership/operator inference are not fully ported in this
  folder.
- In TypeDB 3, prefer `fun`-based computation or Python-side evaluation where rules were
  previously used.

## Notes for query authors

- Keep expression graphs acyclic and staged when inserting complex structures.
- Use stable `expression_name` keys to stitch multi-stage inserts safely.
