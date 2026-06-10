# Feature Reconfiguration Plan — Algorithm

## Goal

Given a set of features to activate and a set to deactivate, produce an ordered
list of `ReconfigurationStep` entries that brings the system to the desired state
while respecting XOR group constraints and `requires` dependencies.

## Inputs

| Parameter | Meaning |
|---|---|
| `to_activate` | Feature names that should become selected |
| `to_deactivate` | Feature names that should become unselected |

Both lists are filtered: features already in the desired state are dropped (no-ops).

## Algorithm — Two Phases

### Phase 1: Build the full change set

1. `activate_set` = `to_activate` filtered to currently-unselected features.
2. `deactivate_set` = `to_deactivate` filtered to currently-selected features.
3. **XOR expansion** — for each feature in `activate_set` that belongs to an XOR
   (`alternative`) group, add all currently-selected siblings to `deactivate_set`.
4. **Requires closure** — repeat until stable: for every `(requiring, required)`
   edge in `requires`, if `required` is in `deactivate_set` and `requiring` is
   currently selected, add `requiring` to `deactivate_set`.

### Phase 2: Assign execution-wave indices

- All deactivations → **index 1** (order among deactivations does not matter;
  only the final state counts).
- Activations → BFS topological waves starting at **index 2**:
  - Build a sub-graph of `requires` edges restricted to `activate_set`.
  - Wave N contains features whose dependencies in `activate_set` are all in
    waves < N.
  - If a cycle is detected (no progress), assign all remaining features to the
    current wave (best-effort).

## Method Breakdown

| Method | Responsibility |
|---|---|
| `_filter_activate` | Drop already-selected features from `to_activate` |
| `_filter_deactivate` | Drop already-unselected features from `to_deactivate` |
| `_xor_deactivations` | Find selected XOR siblings of features being activated |
| `_requires_closure` | Transitively expand deactivation set via `requires` edges |
| `_activation_waves` | Topological BFS → wave indices for activations |
| `get_feature_reconfiguration_plan` | Orchestrate phases 1 & 2, return sorted steps |
