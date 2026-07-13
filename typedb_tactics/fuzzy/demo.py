from fuzzy_sets import (
    FuzzyTriangular, FuzzyGaussian, FuzzyExponentialSaturation, FuzzySigmoid,
    FuzzyBoundedLinearFraction, FuzzyExponentialDecay, FuzzyRationalDecay,
)
from fuzzy_expressions import (
    Proposition, FuzzyUnimodalExpression, FuzzyAscendExpression,
    FuzzyDecayExpression, FuzzyAnd, FuzzyOr, FuzzyNot,
)
from relaxed_requirements import (
    AsCloseAsPossibleExpression, AsManyAsPossibleExpression, AsFewAsPossibleExpression,
    ShallExpression, MayExpression, RelaxedRequirement,
)

print("=== 1. Raw fuzzy sets sanity check ===")
tri = FuzzyTriangular(a=0, b=10, c=20)
for x in (-5, 0, 5, 10, 15, 20, 25):
    print(f"triangular({x}) = {tri.membership(x):.3f}")

gauss = FuzzyGaussian(sigma=2, center=10)
print(f"gaussian(10)={gauss.membership(10):.3f}  gaussian(12)={gauss.membership(12):.3f}")

print("\n=== 2. as_close_as_possible_expression ===")
# Requirement: "temperature should be as close as possible to 21 degrees"
# measured temperature = 23 -> offset shifts (23 - 21) = 2 into the triangular set
temp_measure = Proposition(23.0, name="measured_temperature")
closeness_set = FuzzyTriangular(a=-3, b=0, c=3)  # peak fulfillment at offset==0
temp_close_expr = AsCloseAsPossibleExpression(
    proposition=temp_measure, fuzzy_set=closeness_set, required_value=21.0, name="temp_as_close_as_possible"
)
print(f"quantified_value (measured - required) = {temp_close_expr.quantified_value}")
print(f"fulfillment = {temp_close_expr.fulfillment:.3f}")

print("\n=== 3. as_many_as_possible / as_few_as_possible ===")
uptime_measure = Proposition(0.92, name="uptime_ratio")
as_many_expr = AsManyAsPossibleExpression(
    proposition=uptime_measure,
    fuzzy_set=FuzzySigmoid(exponent=15, inflection_point=0.9),
    name="uptime_as_many_as_possible",
)
print(f"as_many_as_possible fulfillment = {as_many_expr.fulfillment:.3f}")

incidents_measure = Proposition(2.0, name="incident_count")
as_few_expr = AsFewAsPossibleExpression(
    proposition=incidents_measure,
    fuzzy_set=FuzzyExponentialDecay(exponent=0.5),
    name="incidents_as_few_as_possible",
)
print(f"as_few_as_possible fulfillment = {as_few_expr.fulfillment:.3f}")

print("\n=== 4. Boolean/crisp propositions ===")
alarm_ok = Proposition(True, name="alarm_silenced")
print(f"crisp fulfillment = {alarm_ok.fulfillment}")

print("\n=== 5. Logical operators (and/or/not) ===")
and_expr = FuzzyAnd(temp_close_expr, as_many_expr, name="temp_and_uptime")
or_expr = FuzzyOr(as_few_expr, as_many_expr, name="few_or_many")
not_expr = FuzzyNot(as_few_expr, name="not_few")
print(f"AND = {and_expr.fulfillment:.3f} (min)")
print(f"OR  = {or_expr.fulfillment:.3f} (max)")
print(f"NOT = {not_expr.fulfillment:.3f} (1 - x)")

print("\n=== 6. shall / may compound expressions ===")
shall = ShallExpression(temp_close_expr, as_many_expr, alarm_ok, name="core_shall")
may = MayExpression(as_few_expr, as_many_expr, name="either_may")
print(f"shall (min) = {shall.fulfillment:.3f}")
print(f"may (max)   = {may.fulfillment:.3f}")

print("\n=== 7. Full relaxed_requirement ===")
req = RelaxedRequirement(
    "keep_system_comfortable_and_available",
    shall,
    or_expr,
    description="System should stay near target temperature, mostly available, few incidents",
)
print(req)
print(f"requirement_fulfillment = {req.requirement_fulfillment:.3f}")
