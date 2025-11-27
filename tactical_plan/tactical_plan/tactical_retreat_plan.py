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
import rclpy
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from tactical_msgs.srv import PotentialRequirementFulfillment

from tactical_plan.plan_functions import select_tactic_max_avg_fulfillment


class TacticalPlan(Node):
    def __init__(self, name: str):
        super().__init__(name)

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.potential_requirements_fulfillment_cli = self.create_client(
            PotentialRequirementFulfillment,
            '/tactical_kb/potential_requirements_fulfillment'
        )

        self.register_plan_heuristic_function(select_tactic_max_avg_fulfillment)

        return super().on_activate(state)

    def call_service(self, cli, request, timeout_sec=5.0):
        if cli.wait_for_service(timeout_sec=5.0) is False:
            self.get_logger().error(
                'service not available {}'.format(cli.srv_name))
            return None
        future = cli.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if future.done() is False:
            self.get_logger().error(
                'Future not completed {}'.format(cli.srv_name))
            return None

        return future.result()

    def register_plan_heuristic_function(self, func):
        self.select_tactic = func

    def plan_tactical_actions(self, action_name: str):
        request = PotentialRequirementFulfillment.Request()
        request.action_name = action_name
        response = self.call_service(
            self.potential_requirements_fulfillment_cli,
            request
        )

        if response is None:
            self.get_logger().error(
                'Failed to call service potential_requirements_fulfillment')
            return None

        return self.select_tactic(response.requirements_impact)
