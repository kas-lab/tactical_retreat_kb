# Structural Variant Campaign: tactic_rule_impacts_* Functions

Date: 2026-03-15

## S-V1: Inline leaf functions into any_expression_fulfillment

**Idea**: Replace single calls to `tactic_rule_impacts_fuzzy_leaf_fulfillment` and
`tactic_rule_impacts_relaxed_leaf_fulfillment` inside `any_expression_fulfillment` with
6 explicit subtype branches, giving TypeDB direct subtype dispatch without the function call hop.

**Hypothesis**: TypeDB can dispatch directly by exact subtype (relaxed_unimodal, relaxed_ascend,
relaxed_decay, fuzzy_ascend, fuzzy_decay, fuzzy_unimodal) faster than going through an
intermediate function that then does a 3-branch OR dispatch.

**Result**: 1617ms vs V0 1598ms (+1.2% regression). Inlining adds overhead, not reduces it.

**Conclusion**: Rejected. The intermediate function call overhead in TypeDB 3 is negligible;
the benefit of keeping the dispatch in the leaf function (fewer total branches per call site)
outweighs direct subtype dispatch.

---

## R-V1: requirement_fulfillment — delegate to any_expression_fulfillment

**Idea**: Replace the 3-branch OR dispatch (shall, may, relaxed_fuzzy) in
`tactic_rule_impacts_requirement_fulfillment` with a single call to
`tactic_rule_impacts_any_expression_fulfillment`.

```typeql
fun tactic_rule_impacts_requirement_fulfillment($tr: tactic_rule, $req: relaxed_requirement) -> double:
  match
    $req links (expression: $rreq_e);
    let $req_m = tactic_rule_impacts_any_expression_fulfillment($tr, $rreq_e);
  return min($req_m);
```

**Hypothesis**: Eliminates the 3-branch type dispatch in requirement_fulfillment. TypeDB's
query plan for a single function call may be more efficient than a 3-branch OR.

**Result**: 12908ms vs V0 11946ms (+8% regression).

**Conclusion**: Rejected. The 3-branch direct dispatch in `requirement_fulfillment` is faster
than delegating to `any_expression_fulfillment` (which has 10 branches and broader type scope).
TypeDB handles the narrow 3-type dispatch in `requirement_fulfillment` more efficiently than
the general 10-type dispatch in `any_expression_fulfillment`.

**Key insight**: For `return min()` aggregating functions, keeping the dispatch narrow
(only the 3 types that actually appear as requirement children) is faster than using a
general dispatcher. This is consistent with the confirmed rule: "branch ordering matters for
`return first` functions but NOT for `return min`/`return max`" — the aggregation pattern
itself creates different planner behaviour.
