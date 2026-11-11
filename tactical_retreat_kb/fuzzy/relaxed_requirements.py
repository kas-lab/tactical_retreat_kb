"""
Relaxed-requirements layer, ported from relaxed_model.tql.

Built on top of fuzzy_expressions.Expression (everything has `.fulfillment`
in [0, 1]).

Mirrors:
  - as_close_as_possible_expression : unimodal set, auto offset = -required_value
  - as_many_as_possible_expression  : ascend set, no offset
  - as_few_as_possible_expression   : decay set, no offset
  - shall_expression                : min() over its operands
  - may_expression                  : max() over its operands
  - relaxed_requirement             : min() over its expressions -> requirement_fulfillment

`until_expression`, `eventually_expression`, `after/before/in_expression`
are declared but have no evaluation rules yet in the TQL (marked TODO
there), so they are intentionally not implemented here.
"""
from __future__ import annotations

from typing import List, Optional

from .fuzzy_expressions import (
    Expression,
    FuzzyAscendExpression,
    FuzzyDecayExpression,
    FuzzyUnimodalExpression,
    Proposition,
)
from .fuzzy_sets import FuzzySet


class AsCloseAsPossibleExpression(FuzzyUnimodalExpression):
    """
    as_close_as_possible_expression: a unimodal membership function
    (triangular/gaussian) evaluated on (measured_value - required_value),
    per `as_close_as_possible_fuzzy_expression_offset`
    (offset_value = -1.0 * required_value).
    """

    def __init__(
        self,
        proposition: Proposition,
        fuzzy_set: FuzzySet,
        required_value: float,
        name: Optional[str] = None,
    ):
        self.required_value = required_value
        super().__init__(proposition, fuzzy_set, offset=-required_value, name=name)


class AsManyAsPossibleExpression(FuzzyAscendExpression):
    """as_many_as_possible_expression: an ascend set, no offset."""

    def __init__(self, proposition: Proposition, fuzzy_set: FuzzySet, name: Optional[str] = None):
        super().__init__(proposition, fuzzy_set, offset=0.0, name=name)


class AsFewAsPossibleExpression(FuzzyDecayExpression):
    """as_few_as_possible_expression: a decay set, no offset."""

    def __init__(self, proposition: Proposition, fuzzy_set: FuzzySet, name: Optional[str] = None):
        super().__init__(proposition, fuzzy_set, offset=0.0, name=name)


class ShallExpression(Expression):
    """shall_expression_fulfillment: min() over its operands."""

    def __init__(self, *expressions: Expression, name: Optional[str] = None):
        if not expressions:
            raise ValueError("shall_expression needs at least one expression")
        self.expressions = expressions
        self.name = name

    @property
    def fulfillment(self) -> float:
        return min(e.fulfillment for e in self.expressions)


class MayExpression(Expression):
    """may_expression_fulfillment: max() over its operands."""

    def __init__(self, *expressions: Expression, name: Optional[str] = None):
        if not expressions:
            raise ValueError("may_expression needs at least one expression")
        self.expressions = expressions
        self.name = name

    @property
    def fulfillment(self) -> float:
        return max(e.fulfillment for e in self.expressions)


class RelaxedRequirement:
    """
    relaxed_requirement: a named requirement made of one or more
    relaxed_expressions. requirement_fulfillment = min() over all of them
    (see `requirement_fulfillment` rule -- "interpreting multiple
    expressions as a fuzzy and").
    """

    def __init__(
        self,
        requirement_name: str,
        *expressions: Expression,
        description: Optional[str] = None,
        in_effect: bool = True,
    ):
        if not expressions:
            raise ValueError("relaxed_requirement needs at least one expression")
        self.requirement_name = requirement_name
        self.description = description
        self.in_effect = in_effect
        self.expressions: List[Expression] = list(expressions)

    @property
    def requirement_fulfillment(self) -> float:
        if not self.in_effect:
            raise ValueError(f"Requirement {self.requirement_name!r} is not in_effect")
        return min(e.fulfillment for e in self.expressions)

    def __repr__(self) -> str:
        try:
            f = f"{self.requirement_fulfillment:.4f}"
        except ValueError:
            f = "n/a (not in effect)"
        return f"<RelaxedRequirement {self.requirement_name!r} fulfillment={f}>"
