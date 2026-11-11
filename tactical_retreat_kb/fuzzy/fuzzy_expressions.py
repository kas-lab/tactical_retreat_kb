"""
Fuzzy propositional layer, ported from fuzzy_expression.tql.

Mirrors:
  - propositional_expression (a crisp boolean OR a numeric "measure")
  - fuzzy_{unimodal,ascend,decay}_expression (measure -> membership degree,
    via a FuzzySet, with an optional offset_value)
  - fuzzy_not / fuzzy_and / fuzzy_or (operators over anything with a
    `.fulfillment` -- Zadeh not/min/max)

Every node in the tree exposes a single read-only property `.fulfillment`
(a float in [0, 1]). This corresponds to `membership_degree` /
`expression_fulfillment` in the TQL -- the rules there just copy one onto
the other, so we collapse them into one concept here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from .fuzzy_sets import FuzzySet


class Expression(ABC):
    """Anything that can be asked "how fulfilled/true are you, 0..1?"."""

    name: Optional[str] = None

    @property
    @abstractmethod
    def fulfillment(self) -> float:
        ...

    def __repr__(self) -> str:
        label = f" {self.name!r}" if self.name else ""
        return f"<{type(self).__name__}{label} fulfillment={self.fulfillment:.4f}>"


class Proposition(Expression):
    """
    propositional_expression: wraps either
      - a crisp boolean measurement (bool_value true/false -> 1.0 / 0.0), or
      - a numeric measurement ("quantified_value") to be fed into a
        fuzzy_{unimodal,ascend,decay}_expression.

    Use `.fulfillment` for the crisp case and `.quantified_value` for the
    numeric case (used inside FuzzyExpression).
    """

    def __init__(self, value: Union[bool, float], name: Optional[str] = None):
        self.value = value
        self.name = name

    @property
    def is_crisp(self) -> bool:
        return isinstance(self.value, bool)

    @property
    def quantified_value(self) -> float:
        if self.is_crisp:
            raise ValueError(
                f"Proposition {self.name!r} holds a crisp boolean, "
                "it has no quantified_value"
            )
        return float(self.value)

    @property
    def fulfillment(self) -> float:
        if not self.is_crisp:
            raise ValueError(
                f"Proposition {self.name!r} holds a numeric measure, "
                "it has no fulfillment on its own -- wrap it in a "
                "FuzzyExpression (unimodal/ascend/decay) first"
            )
        return 1.0 if self.value else 0.0


class FuzzyExpression(Expression):
    """
    Base for fuzzy_unimodal_expression / fuzzy_ascend_expression /
    fuzzy_decay_expression: takes a Proposition's quantified_value
    (optionally shifted by `offset`), runs it through a FuzzySet, and
    that's the fulfillment/membership_degree.

    `offset` mirrors `offset_value`:
        quantified_value_used = proposition.quantified_value + offset
    """

    def __init__(
        self,
        proposition: Proposition,
        fuzzy_set: FuzzySet,
        offset: float = 0.0,
        name: Optional[str] = None,
    ):
        self.proposition = proposition
        self.fuzzy_set = fuzzy_set
        self.offset = offset
        self.name = name

    @property
    def quantified_value(self) -> float:
        return self.proposition.quantified_value + self.offset

    @property
    def fulfillment(self) -> float:
        return self.fuzzy_set.membership(self.quantified_value)


class FuzzyUnimodalExpression(FuzzyExpression):
    """fuzzy_unimodal_expression -- fuzzy_set must be a UnimodalSet (triangular/gaussian)."""


class FuzzyAscendExpression(FuzzyExpression):
    """fuzzy_ascend_expression -- fuzzy_set must be an AscendSet."""


class FuzzyDecayExpression(FuzzyExpression):
    """fuzzy_decay_expression -- fuzzy_set must be a DecaySet."""


# --------------------------------------------------------------------------
# Operators: fuzzy_not / fuzzy_and / fuzzy_or
# --------------------------------------------------------------------------

class FuzzyNot(Expression):
    """fuzzy_not_operator: 1 - membership(expression)"""

    def __init__(self, expression: Expression, name: Optional[str] = None):
        self.expression = expression
        self.name = name

    @property
    def fulfillment(self) -> float:
        return 1.0 - self.expression.fulfillment


class FuzzyAnd(Expression):
    """fuzzy_and_operator: min(membership(e) for e in expressions)"""

    def __init__(self, *expressions: Expression, name: Optional[str] = None):
        if not expressions:
            raise ValueError("fuzzy_and needs at least one expression")
        self.expressions = expressions
        self.name = name

    @property
    def fulfillment(self) -> float:
        return min(e.fulfillment for e in self.expressions)


class FuzzyOr(Expression):
    """fuzzy_or_operator: max(membership(e) for e in expressions)"""

    def __init__(self, *expressions: Expression, name: Optional[str] = None):
        if not expressions:
            raise ValueError("fuzzy_or needs at least one expression")
        self.expressions = expressions
        self.name = name

    @property
    def fulfillment(self) -> float:
        return max(e.fulfillment for e in self.expressions)
