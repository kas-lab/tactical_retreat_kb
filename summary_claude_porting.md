---
  Summary — TypeDB 2→3 Migration Status

  What's Done ✅

  Tests passing (15/15):
  - test_ros_model.py — 3 pass
  - test_logical_expression.py — 10 pass
  - test_feature_model.py — 2 pass

  Committed changes (both typedb3 and typedb3_py branches):
  - All Python interface changes (composition, imports, fetch syntax, result
  parsing)
  - logical_expression.tql + new logical_expression_ext.tql
  - fuzzy_expression.tql (schema defs, no rules) + new fuzzy_expression_ext.tql
  - test_logical_expression.tql split into 3 files (anonymous leaf → compound →
  satisfied pipeline)
  - ros_typedb: removed .resolve() from define query path (schemas load correctly
  without it)

  ---
  What's Missing ❌ — The Big One

  TypeDB 3.8 removed the rule keyword. Any define block with rule causes [TSV7]
  Query parsing failed. Rules must be replaced with TypeDB 3 fun (function)
  definitions.

  This affects:
  1. fuzzy_expression.tql — 13 rules computing membership_degree from fuzzy set
  parameters (sigmoid, gaussian, triangular, etc.) and fuzzy operators (AND=min,
  OR=max, NOT=1-x)
  2. relaxed_model.tql — fulfillment rules (shall=min, may=max, requirement=min)
  3. discover_hypothetical_req_fulfillment.tql — likely has rules too (not
  investigated)

  The fix: Replace each rule with a TypeDB 3 fun function:
  define
  fun fuzzy_sigmoid_membership($exponent: double, $inflection: double, $x: double)
  -> { double }:
      match let $m = 1.0 / (1.0 + 2.71828 ^ (-1.0 * $exponent * ($x -
  $inflection)));
      return { $m };
  Then rewrite the Python queries to call the functions instead of querying has
  membership_degree $m on inferred data. Docs:
  https://typedb.com/docs/typeql-reference/functions/

  Also not investigated:
  - test_hypothetical_req_fulfillment.py
  - test_generated_benchmark_profile.py
  - test_tactical_retreat_interface.py
  - test_kb.py

  Data pipeline WIP (committed with "wip:" prefix, not fully tested):
  - relaxed_paper_example.tql, relaxed_mirte_example.tql, tactics_example.tql —
  rewritten as multi-stage match+insert pipelines
  - test_fuzzy_expression.tql, test_relaxed_model.tql, test_tactics_model.tql —
  rewritten as multi-stage pipelines

  These data files are correct in structure but their corresponding tests still fail
   because the computation rules are gone.
