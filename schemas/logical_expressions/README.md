# Logical models

## Fragement of first-order logic

We use a multi-sorted, quantifier-free first-order logic over typed state variables, with sorts for booleans, integers, reals, strings, and arrays of these types. Atomic formulas are either comparison predicates between terms (e.g. <, ≤, >, ≥, =, ≠ applied to variables or constants of compatible types) or propositional atoms over boolean terms. Negation is restricted to atomic formulas, yielding negation normal form (NNF). In addition, formulas are constrained to a conjunctive normal form (CNF) shape at the meta-model level: an or_expression (clause) may only relate atomic_expression instances (literals), while an and_expression (conjunction) may only relate atomic_expression instances and or_expression instances. This induces a three-tier expression graph (literals → disjunctions → conjunctions) that is acyclic and stratified, so every well-formed formula denotes a finite conjunction of finite disjunctions of literals (possibly degenerate to a single clause or a single literal), which can be evaluated monotonically by TypeDB rules.

**Grammar:**
```
t   ::= x | c
α   ::= t <  t
     |  t <= t
     |  t >  t
     |  t >= t
     |  t =  t
     |  t != t
     |  q
ℓ   ::= α | ¬α
C   ::= ℓ | C ∨ ℓ
φ   ::= C | φ ∧ C
```

* x is a (typed) state variable, c is a (typed) constant
* q is a boolean state variable (propositional atom)
* α are atomic formulas, ℓ are literals, C are clauses, and φ are formulas

## Fuzzy Branching Temporal Logic

Semantically, an FBTL atomic formula is a function

p:State→[0,1]
p:State→[0,1]