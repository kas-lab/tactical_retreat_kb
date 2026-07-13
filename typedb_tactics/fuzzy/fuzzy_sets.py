"""
Fuzzy membership functions ("FuzzySet"s), ported from fuzzy_expression.tql.

Three families, matching `AscendSet`, `DecaySet`, `UnimodalSet` in the TQL:

- Ascend  : monotonically increasing membership, m(x) -> 1 as x grows.
- Decay   : monotonically decreasing membership, m(x) -> 0 as x grows.
- Unimodal: rises then falls (or a bell curve), single peak.

All membership() calls clamp their result to [0, 1] to guard against
floating point noise / out-of-domain inputs (the TQL rules don't clamp,
but a real degree of membership should never leave [0, 1]).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


class FuzzySet(ABC):
    """Abstract base, mirrors `FuzzySet sub entity, abstract` in the TQL."""

    @abstractmethod
    def membership(self, x: float) -> float:
        ...


# --------------------------------------------------------------------------
# Unimodal sets
# --------------------------------------------------------------------------

@dataclass
class FuzzyTriangular(FuzzySet):
    """
    μ(x) = (x - a) / (b - a),  a <= x <= b
    μ(x) = (c - x) / (c - b),  b <  x <= c
    μ(x) = 0                   otherwise
    """
    a: float
    b: float
    c: float

    def membership(self, x: float) -> float:
        if self.a <= x <= self.b:
            if self.b == self.a:
                return 1.0
            return _clamp((x - self.a) / (self.b - self.a))
        if self.b < x <= self.c:
            if self.c == self.b:
                return 1.0
            return _clamp((self.c - x) / (self.c - self.b))
        return 0.0


@dataclass
class FuzzyGaussian(FuzzySet):
    """μ(x) = e^(-0.5 * ((x - center) / sigma)^2)"""
    sigma: float
    center: float

    def membership(self, x: float) -> float:
        return _clamp(math.exp(-0.5 * ((x - self.center) / self.sigma) ** 2))


# --------------------------------------------------------------------------
# Ascend sets (monotonic increasing)
# --------------------------------------------------------------------------

@dataclass
class FuzzyExponentialSaturation(FuzzySet):
    """m(x) = 1 - e^(-exponent * x), exponent > 0"""
    exponent: float

    def membership(self, x: float) -> float:
        return _clamp(1.0 - math.exp(-self.exponent * x))


@dataclass
class FuzzySigmoid(FuzzySet):
    """m(x) = 1 / (1 + e^(-exponent * (x - inflection_point)))"""
    exponent: float
    inflection_point: float

    def membership(self, x: float) -> float:
        return _clamp(1.0 / (1.0 + math.exp(-self.exponent * (x - self.inflection_point))))


@dataclass
class FuzzyBoundedLinearFraction(FuzzySet):
    """m(x) = x / (x + curvature), curvature > 0"""
    curvature: float

    def membership(self, x: float) -> float:
        return _clamp(x / (x + self.curvature))


# --------------------------------------------------------------------------
# Decay sets (monotonic decreasing)
# --------------------------------------------------------------------------

@dataclass
class FuzzyExponentialDecay(FuzzySet):
    """m(x) = e^(-exponent * x), exponent > 0"""
    exponent: float

    def membership(self, x: float) -> float:
        return _clamp(math.exp(-self.exponent * x))


@dataclass
class FuzzyRationalDecay(FuzzySet):
    """m(x) = curvature / (x + curvature), curvature > 0"""
    curvature: float

    def membership(self, x: float) -> float:
        return _clamp(self.curvature / (x + self.curvature))
