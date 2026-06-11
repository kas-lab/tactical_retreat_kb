# Copyright 2026 KAS lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import FrozenSet
from typing import List
from typing import Literal
from typing import Set
from typing import Tuple


@dataclass
class ReconfigurationStep:
    """A single step in a feature reconfiguration plan."""

    feature_name: str
    """Feature to act on."""

    action: Literal['activate', 'deactivate']
    """Whether to activate or deactivate the feature."""

    index: int
    """Execution wave: steps with equal index may run in parallel."""


@dataclass
class FeatureModel:
    """In-memory feature model loaded from TypeDB.

    Structural fields are populated once at system initialisation and never
    modified afterwards.  Only ``selected`` is updated at runtime before each
    reconfiguration plan is computed.
    """

    # Static structure — built once, never mutated after construction.
    features: FrozenSet[str]
    """All feature names present in the model."""

    mandatory: FrozenSet[str]
    """Feature names that carry ``mandatory=true``."""

    hierarchy_children: Dict[str, FrozenSet[str]]
    """AND groups: parent feature name → frozenset of child feature names."""

    alternative_children: Dict[str, FrozenSet[str]]
    """XOR groups: parent feature name → frozenset of child feature names."""

    or_group_children: Dict[str, FrozenSet[str]]
    """OR groups: parent feature name → frozenset of child feature names."""

    requires: FrozenSet[Tuple[str, str]]
    """Direct requires edges: (requiring, required) feature name pairs."""

    excludes: FrozenSet[Tuple[str, str]]
    """Symmetric excludes pairs: both (A, B) and (B, A) are present for each conflict."""

    # Mutable state — refreshed before each plan computation.
    selected: Dict[str, bool] = field(default_factory=dict)
    """Current selected state keyed by feature name.

    Features absent from TypeDB (no ``selected`` attribute yet) are treated as
    unselected via ``selected.get(name, False)``.
    """

    # ------------------------------------------------------------------
    # Reconfiguration planning
    # ------------------------------------------------------------------

    def _filter_activate(self, to_activate: List[str]) -> Set[str]:
        """Return only features from to_activate that are currently unselected."""
        return {f for f in to_activate if not self.selected.get(f, False)}

    def _filter_deactivate(self, to_deactivate: List[str]) -> Set[str]:
        """Return only features from to_deactivate that are currently selected."""
        return {f for f in to_deactivate if self.selected.get(f, False)}

    def _xor_deactivations(self, activate_set: Set[str]) -> Set[str]:
        """Find currently-selected XOR siblings of features being activated."""
        result: Set[str] = set()
        for feature in activate_set:
            for children in self.alternative_children.values():
                if feature in children:
                    result.update(
                        s for s in children
                        if s != feature and self.selected.get(s, False)
                    )
        return result

    def _requires_closure(self, deactivate_set: Set[str]) -> Set[str]:
        """Expand deactivation set: include all selected features that require any member."""
        closure = set(deactivate_set)
        changed = True
        while changed:  # fixed-point loop to avoid infinite recursion
            changed = False
            for requiring, required in self.requires:
                if (required in closure
                        and self.selected.get(requiring, False)
                        and requiring not in closure):
                    closure.add(requiring)
                    changed = True
        return closure

    def _activation_waves(self, activate_set: Set[str]) -> Dict[str, int]:
        """Assign wave indices to activations via topological BFS on requires edges."""
        if not activate_set:
            return {}
        deps: Dict[str, Set[str]] = {f: set() for f in activate_set}
        for requiring, required in self.requires:
            if requiring in activate_set and required in activate_set:
                deps[requiring].add(required)
        indices: Dict[str, int] = {}
        assigned: Set[str] = set()
        remaining = set(activate_set)
        wave = 2
        while remaining:
            #  collect all features whose full dependency set is already contained in assigned
            ready = {f for f in remaining if deps[f] <= assigned}
            if not ready:
                # Cycle: no feature can satisfy its deps from within the
                # remaining set.  Assign all to the current wave as best-effort.
                for f in remaining:
                    indices[f] = wave
                break
            for f in ready:
                indices[f] = wave
            assigned |= ready
            remaining -= ready
            wave += 1
        return indices

    def get_feature_reconfiguration_plan(
        self,
        to_activate: List[str],
        to_deactivate: List[str],
    ) -> List[ReconfigurationStep]:
        """Compute a reconfiguration plan from the current selected state.

        Deactivations are assigned index 1 in any order.  Activations are
        ordered by ``requires`` dependencies starting at index 2.
        """
        activate_set = self._filter_activate(to_activate)
        deactivate_set = self._filter_deactivate(to_deactivate)
        deactivate_set |= self._xor_deactivations(activate_set)
        deactivate_set = self._requires_closure(deactivate_set)
        activation_indices = self._activation_waves(activate_set)
        steps: List[ReconfigurationStep] = [
            ReconfigurationStep(f, 'deactivate', 1)
            for f in deactivate_set
        ] + [
            ReconfigurationStep(f, 'activate', idx)
            for f, idx in activation_indices.items()
        ]
        return sorted(steps, key=lambda s: (s.index, s.feature_name))

    # ------------------------------------------------------------------
    # State refresh
    # ------------------------------------------------------------------

    def refresh_selected(self, results: List[dict]) -> None:
        """Update selected state in-place from raw TypeDB feature-selected fetch results."""
        new_selected = {}
        for row in results:
            f_attrs = row['f']
            name = f_attrs['feature_name'][0]['value']
            selected_vals = f_attrs.get('selected', [])
            new_selected[name] = selected_vals[0]['value'] if selected_vals else False
        self.selected = new_selected

    @classmethod
    def from_typedb_results(cls, results: List[dict]) -> 'FeatureModel':
        """Build a FeatureModel from raw TypeDB feature model fetch results."""
        features = set()
        mandatory = set()
        selected = {}
        hierarchy_children = {}
        alternative_children = {}
        or_group_children = {}
        requires_edges = set()
        excludes_edges = set()

        for row in results:
            f_attrs = row['f']
            name = f_attrs['feature_name'][0]['value']
            features.add(name)

            mandatory_vals = f_attrs.get('mandatory', [])
            if mandatory_vals and mandatory_vals[0]['value']:
                mandatory.add(name)

            selected_vals = f_attrs.get('selected', [])
            selected[name] = selected_vals[0]['value'] if selected_vals else False

            fh_sub = row.get('feature_hierarchy', [])
            if fh_sub:
                hierarchy_children[name] = frozenset(
                    r['c']['feature_name'][0]['value'] for r in fh_sub
                )

            alt_sub = row.get('alt_children', [])
            if alt_sub:
                alternative_children[name] = frozenset(
                    r['c']['feature_name'][0]['value'] for r in alt_sub
                )

            or_sub = row.get('or_children', [])
            if or_sub:
                or_group_children[name] = frozenset(
                    r['c']['feature_name'][0]['value'] for r in or_sub
                )

            for r in row.get('requires', []):
                req_name = r['req']['feature_name'][0]['value']
                requires_edges.add((name, req_name))

            for r in row.get('excludes', []):
                con_name = r['con']['feature_name'][0]['value']
                excludes_edges.add((name, con_name))

        return cls(
            features=frozenset(features),
            mandatory=frozenset(mandatory),
            hierarchy_children=hierarchy_children,
            alternative_children=alternative_children,
            or_group_children=or_group_children,
            requires=frozenset(requires_edges),
            excludes=frozenset(excludes_edges),
            selected=selected,
        )
