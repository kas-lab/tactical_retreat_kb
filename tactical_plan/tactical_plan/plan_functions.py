# Copyright 2025 KAS lab
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

from typing import Dict, List

from tactical_msgs.msg import RequirementImpact


def select_tactic_max_avg_fulfillment(
        requirement_impact_list: List[RequirementImpact]) -> str:
    """Select tactic to be executed by calculatin the avg fullfillment.

    :param requirement_impact_list: List of RequirementImpact.
    :return: tactic rule name to be executed.
    """
    best_name = None
    best_avg = None
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}

    for impact in requirement_impact_list:
        name = impact.tactic_rule
        totals[name] = totals.get(name, 0.0) + impact.fulfillment
        counts[name] = counts.get(name, 0) + 1
        avg = totals[name] / counts[name]
        if best_avg is None or avg > best_avg:
            best_avg = avg
            best_name = name

    return best_name
