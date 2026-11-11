import math
import unittest

from fuzzy_sets import (
    FuzzyTriangular, FuzzyGaussian, FuzzyExponentialSaturation, FuzzySigmoid,
    FuzzyBoundedLinearFraction, FuzzyExponentialDecay, FuzzyRationalDecay,
)
from fuzzy_expressions import Proposition, FuzzyAnd, FuzzyOr, FuzzyNot
from relaxed_requirements import (
    AsCloseAsPossibleExpression, AsManyAsPossibleExpression, ShallExpression, MayExpression,
    RelaxedRequirement,
)


class TestFuzzySets(unittest.TestCase):
    def test_triangular_formula(self):
        f = FuzzyTriangular(a=0, b=10, c=20)
        self.assertAlmostEqual(f.membership(5), (5 - 0) / (10 - 0))
        self.assertAlmostEqual(f.membership(15), (20 - 15) / (20 - 10))
        self.assertEqual(f.membership(-1), 0.0)
        self.assertEqual(f.membership(21), 0.0)

    def test_gaussian_formula(self):
        f = FuzzyGaussian(sigma=2, center=10)
        expected = math.exp(-0.5 * ((12 - 10) / 2) ** 2)
        self.assertAlmostEqual(f.membership(12), expected)

    def test_exponential_saturation_formula(self):
        f = FuzzyExponentialSaturation(exponent=0.3)
        expected = 1.0 - math.exp(-0.3 * 4)
        self.assertAlmostEqual(f.membership(4), expected)

    def test_sigmoid_formula(self):
        f = FuzzySigmoid(exponent=1.0, inflection_point=5.0)
        self.assertAlmostEqual(f.membership(5.0), 0.5)

    def test_bounded_linear_fraction_formula(self):
        f = FuzzyBoundedLinearFraction(curvature=2.0)
        self.assertAlmostEqual(f.membership(2.0), 2.0 / (2.0 + 2.0))

    def test_exponential_decay_formula(self):
        f = FuzzyExponentialDecay(exponent=0.5)
        self.assertAlmostEqual(f.membership(2.0), math.exp(-0.5 * 2.0))

    def test_rational_decay_formula(self):
        f = FuzzyRationalDecay(curvature=3.0)
        self.assertAlmostEqual(f.membership(1.0), 3.0 / (1.0 + 3.0))


class TestOperators(unittest.TestCase):
    def test_and_is_min(self):
        p1 = Proposition(True)
        p2 = Proposition(False)
        self.assertEqual(FuzzyAnd(p1, p2).fulfillment, 0.0)

    def test_or_is_max(self):
        p1 = Proposition(True)
        p2 = Proposition(False)
        self.assertEqual(FuzzyOr(p1, p2).fulfillment, 1.0)

    def test_not_is_complement(self):
        p1 = Proposition(True)
        self.assertEqual(FuzzyNot(p1).fulfillment, 0.0)


class TestRelaxedRequirements(unittest.TestCase):
    def test_as_close_as_possible_offset(self):
        prop = Proposition(23.0)
        fset = FuzzyTriangular(a=-3, b=0, c=3)
        expr = AsCloseAsPossibleExpression(prop, fset, required_value=21.0)
        # offset_value = -required_value -> quantified_value = 23 - 21 = 2
        self.assertAlmostEqual(expr.quantified_value, 2.0)
        self.assertAlmostEqual(expr.fulfillment, fset.membership(2.0))

    def test_shall_is_min_may_is_max(self):
        a, b, c = Proposition(True), Proposition(False), Proposition(True)
        shall = ShallExpression(a, b, c)
        may = MayExpression(a, b, c)
        self.assertEqual(shall.fulfillment, 0.0)
        self.assertEqual(may.fulfillment, 1.0)

    def test_requirement_fulfillment_is_min_over_expressions(self):
        e1 = Proposition(True)  # fulfillment 1.0
        prop = Proposition(23.0)
        fset = FuzzyTriangular(a=-3, b=0, c=3)
        e2 = AsCloseAsPossibleExpression(prop, fset, required_value=21.0)  # 1/3
        req = RelaxedRequirement("r1", e1, e2)
        self.assertAlmostEqual(req.requirement_fulfillment, min(1.0, e2.fulfillment))

    def test_requirement_not_in_effect_raises(self):
        req = RelaxedRequirement("r2", Proposition(True), in_effect=False)
        with self.assertRaises(ValueError):
            _ = req.requirement_fulfillment


if __name__ == "__main__":
    unittest.main()
