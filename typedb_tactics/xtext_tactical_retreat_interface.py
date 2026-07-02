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
from dataclasses import dataclass
from datetime import datetime
import inspect
import os
import logging
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypedDict
from typing import Union
from ament_index_python.packages import get_package_share_directory
from aal_msgs.msg import Adaptation
from lifecycle_msgs.msg import Transition
from rclpy.parameter import Parameter
import traceback
from functools import partial
import jpype
import jpype.imports

jars_path = os.path.join(get_package_share_directory("adapt_x"), "jars", "rem")

jpype.startJVM(
    classpath=[jars_path + "/*"]
)

from rosToolingSupport import RosToolingSupport
from de.fraunhofer.ipa.ros import RosStandaloneSetupGenerated
from de.fraunhofer.ipa.rossystem import RosSystemStandaloneSetupGenerated
from de.fraunhofer.ipa.ros2 import Ros2StandaloneSetupGenerated
from eu.coresense.variability import FeatureModelStandaloneSetupGenerated
from eu.coresense.resolution import ResolutionModelStandaloneSetupGenerated
from eu.coresense.context import ContextModelStandaloneSetupGenerated
from eu.coresense.requirements import RequirementsModelStandaloneSetupGenerated
from eu.coresense.adaptation import TacticsStandaloneSetupGenerated

from org.eclipse.xtext.resource import XtextResourceSet
from eu.coresense.common import NameProvider
from eu.coresense.context.generator import ContextNameProvider
from eu.coresense.resolution.generator import ResolutionNameProvider
from eu.coresense.adaptation.generator import TacticsNameProvider
from eu.coresense.common import RosNameProvider, MathOperator, Literal, IntLiteral, DecimalLiteral, StringLiteral, BooleanLiteral

from eu.coresense.adaptation.tactics import TacticsModel, AtomicRule, ConditionAction, MeasurementThresholdCondition, MeasurementMeasurementCondition, LogicalOperator, AtomicActionDeselectFeature, AtomicActionSelectFeature
from eu.coresense.requirements.generator import RequirementsModelGenerator
from eu.coresense.requirements.requirementsModel import RequirementsModel
from eu.coresense.resolution.resolutionModel import ResolutionModel, Reconfiguration, SetParam, SetLifecycle, LifeCycleState
from eu.coresense.context.contextModel import ContextModel, QualifiedPublisherRef, QualifiedActionServerRef, QualifiedServiceServerRef
from uma.caosd.rhea.AdvancedConstraintsFMmetamodel import AdvancedConstraintsFMmetamodelPackage
from uma.caosd.rhea.BasicFMmetamodel import Feature, Alternative, OrGroup
from java.lang import String, Integer
from java.util import HashSet
from ros import ParameterBoolean, ParameterInteger, ParameterDouble, ParameterString, ParameterSequence


logger = logging.getLogger(__name__)

def instanceis(clas, obj):
    return isinstance(obj,clas)

def valueOf(param):
    if (isinstance(param, ParameterBoolean)):
        return bool(((ParameterBoolean) @ param).isValue())
    elif (isinstance(param, ParameterInteger)):
        return int(((ParameterInteger) @ param).getValue())
    elif (isinstance(param, ParameterDouble)):
        return float(((ParameterDouble) @ param).getValue())
    elif (isinstance(param, ParameterString)):
        return str(((ParameterString) @ param).getValue())
    elif (isinstance(param, ParameterSequence)):
        return list(((ParameterSequence) @ param).getValue().stream().map(valueOf).toList())



# @dataclass
# class RequirementImpactDict():
#     """Dataclass for requirement impact information."""

#     action_name: str  #: name of the action
#     requirement_name: str  #: name of the requirement
#     tactic_rule: str  #: name of the tactic rule
#     fulfillment: float  #: fulfillment value


# def create_value_query(value, suffix=''):
#     if not isinstance(value, (str, float, int, bool, list)):
#         logger.error(
#             'Unsupported type %s for value %s',
#             type(value),
#             value)
#         return None, None

#     variable_name = f'$value{suffix}'

#     value_query = ''
#     if isinstance(value, str):
#         value_query = f'{variable_name} isa ValueString, has string_value "{value}";'
#     elif isinstance(value, float):
#         formatted = format(value, '.15f')
#         value_query = f'{variable_name} isa ValueDouble, has double_value {formatted};'
#     elif isinstance(value, bool):
#         value_query = f"""{variable_name} isa ValueBool,
#             has bool_value {convert_py_type_to_query_type(value)};"""
#     elif isinstance(value, int):
#         value_query = f'{variable_name} isa ValueInteger, has integer_value {value};'
#     return value_query, variable_name


# class ROSActionResultDict(TypedDict):
#     """TypedDict for get_subnodes method result."""

#     action_name: str  #: action name
#     action_type: str  #: action type


# class RuntimeNodeDict(TypedDict):
#     """TypedDict for get_subnodes method result."""

#     namespace: str  #: node namespace
#     node_name: str  #: node name


# def node_query_to_node_dict(
#         query_result: List[dict[str, MatchResultDict]],
#         node_variable: str = 'node') -> List[RuntimeNodeDict]:
#     node_dict = []
#     for result in query_result:
#         node = result.get(node_variable)
#         if len(node['namespace']) > 1:
#             logger.error(
#                 'In node_query_to_node_dict: '
#                 'runtime node has more than 1 namespace')
#             return node_dict
#         if len(node['node_name']) > 1:
#             logger.error(
#                 'In node_query_to_node_dict: '
#                 'runtime node has more than 1 node_name')
#             return node_dict
#         node_dict.append({
#             'node_name': node['node_name'][0]['value'],
#             'namespace': node['namespace'][0]['value'],
#         }
#         )
#     # Sort list to guarantee deterministic list order
#     node_dict.sort(key=lambda d: (d['node_name'], d['namespace']))
#     return node_dict


YELLOW_BOLD = "\033[33;1m"
RESET = "\033[0m"


class TacticalRetreatInterface:
    """Class to interact with the TacticalRetreat knowledge model in typeDB."""

    def __init__(self,
                 resolution_path: str = "",
                 var_path: str = "",
                 context_path: str = "",
                 reqs_path: str = "",
                 ros_path: List[str] = [""],
                 ros2_path: List[str] = [""],
                 rossystem_path: List[str] = [""],
                 tactics_path: str = "",
                 require_nodes_running: bool = False,
                 verify_parameters: bool = False,
                 generate_state: bool = True,
                 consider_features_in_state: bool = False, logger=None) -> None:
        RosToolingSupport.registerEPackages()
        AdvancedConstraintsFMmetamodelPackage.eINSTANCE.eClass()

        self.resSet = XtextResourceSet()
        self.logger = logger
        self.logger.info(f"{ros_path}")
        self.load_model("ros", RosStandaloneSetupGenerated(), ros_path)
        self.ros2Resources = self.load_model("ros2", Ros2StandaloneSetupGenerated(), ros2_path)
        self.rosSystemResources = self.load_model("rossystem", RosSystemStandaloneSetupGenerated(), rossystem_path)
        fmResources = self.load_model("var", FeatureModelStandaloneSetupGenerated(), var_path)
        resSources = self.load_model("resolution", ResolutionModelStandaloneSetupGenerated(), resolution_path)
        contextResources = self.load_model("context", ContextModelStandaloneSetupGenerated(), context_path)
        requirementsResources = self.load_model("reqs",
                                                RequirementsModelStandaloneSetupGenerated(),
                                                reqs_path)
        tacticsResources = self.load_model("tactics", TacticsStandaloneSetupGenerated(),
                                           tactics_path)

        self.tacticsModelResource = tacticsResources.get(0)
        self.tacticsModel = (TacticsModel) @ self.tacticsModelResource.getContents().get(0)

        self.requirementsModelResource = requirementsResources.get(0)
        self.requirementsModel = (RequirementsModel) @ \
            self.requirementsModelResource.getContents().get(0)

        self.contextModelResource = contextResources.get(0)
        self.contextModel = (ContextModel) @ \
            self.contextModelResource.getContents().get(0)


        self.resolutionModelResource = resSources.get(0)
        self.resolutionModel = (ResolutionModel) @ \
            self.resolutionModelResource.getContents().get(0)

        if (generate_state):
            from eu.coresense.adaptation.generator import State

            if hasattr(fmResources, "get"):
                resource0 = fmResources.get(0)
            else:
                resource0 = fmResources[0]

            try:
                from org.eclipse.emf.ecore.util import EcoreUtil
                EcoreUtil.resolveAll(resource0)
            except Exception:
                pass

            try:
                root_obj = resource0.getContents().get(0)
            except Exception:
                root_obj = resource0.contents().get(0)

            try:
                from org.eclipse.emf.ecore.resource import Resource as EMFResource
                if isinstance(root_obj, EMFResource):
                    root_obj = root_obj.getContents().get(0)
            except Exception:
                pass

            self.DSLFeatureModel = root_obj

            for j_action_rule in self.tacticsModel.getActionRules():
                self.j_states = State.FromRules(j_action_rule.getAdaptationRules(),
                                self.DSLFeatureModel.getFm(), consider_features_in_state)

                self.logger.info(f"{str(self.j_states.size())} states generated")


        self.logger.info("ready")

    def progress_message(self, msg: str):
        self.logger.info(f"{YELLOW_BOLD}{msg}{RESET}")

    def load_model(self, ext, setup_obj, path):
        resources = RosToolingSupport.loadModel(
            setup_obj,
            self.resSet,
            ext,
            path,
        )

        self.progress_message(f"Loaded {int(resources.size())}.{ext} files")
        return resources


    def manual_running_nodes(self, node_names: List[str]):
        """
        Update the running nodes in the knowledge base.

        :param node_names: list of node names
        """
        pass
        # insert_statements = ''
        # for i, node_name in enumerate(node_names):
        #     insert_statements += f"""
        #         $node_{i} has running true;
        #     """
        # nl = '\n'
        # query = f"""
        #     match
        #         {' '.join([
        #             f'$node_{i} isa ROSNode, has node_name "{node_name}"; {nl}'
        #             for i, node_name in enumerate(node_names)
        #         ])}
        #     insert
        #         {insert_statements}
        # """
        # return self.insert_database(query)


    def _get_condition_action(self, j_atomic_rule: AtomicRule) -> ConditionAction:
        if (isinstance(j_atomic_rule, AtomicRule)):
            j_atomic_rule = (AtomicRule) @ j_atomic_rule
            j_rule_body = j_atomic_rule.getRuleBody()
            if (isinstance(j_rule_body, ConditionAction)):
                return (ConditionAction) @ j_rule_body
            
    def _value_from_lit(self, lit):
        if (isinstance(lit,DecimalLiteral)):
            return float((DecimalLiteral @ lit).getValue().longValue())
        if (isinstance(lit,IntLiteral)):
            return int((IntLiteral @ lit).getValue())
        if (isinstance(lit,StringLiteral)):
            return str((StringLiteral @ lit).getValue())
        if (isinstance(lit,BooleanLiteral)):
            return bool((BooleanLiteral @ lit).isValue())

    def _eval_measurement_condition(self, j_measurement_condition, measures) -> bool:
        self.logger.info("called")
        
        context_var_name = str(j_measurement_condition
                               .getMeasurement().getName())
        context_val = measures.get(context_var_name, None)

        if context_val is None:
            return False

        j_operator = j_measurement_condition.getOperator()


        comparator = None
        if (isinstance(j_measurement_condition, MeasurementThresholdCondition)):
            j_threshold = ((MeasurementThresholdCondition) @ j_measurement_condition).getThresholdValue()
            comparator = self._value_from_lit(j_threshold)

         # if(isinstance(j_measurmement_condition,MeasurementMeasurementCondition)):

        res = False

        if (j_operator == MathOperator.LESS):
            res = context_val < comparator
        if (j_operator == MathOperator.GREATER):
            res = context_val > comparator
        if (j_operator == MathOperator.EQUAL):
            res = context_val == comparator
        if (j_operator == MathOperator.DIFFERENT):
            res = context_val != comparator
        if (j_operator == MathOperator.GREQ):
            res = context_val >= comparator
        if (j_operator == MathOperator.LEQ):
            res = context_val <= comparator

        j_log_op = j_measurement_condition.getLogicalOp()
        j_second_term = j_measurement_condition.getSecondTerm()
        self.logger.info(f"loggg op {str(j_log_op)}")
        self.logger.info(f"loggg op {str(j_second_term)}")

        # j_log_op_val = j_log_op.getValue()
        if (j_log_op is not None) and (j_second_term is not None):
            if (j_log_op == LogicalOperator.AND):
                self.logger.info(f"and")

                return (res and self._eval_measurement_condition(j_second_term, measures))
            if (j_log_op == LogicalOperator.OR):
                self.logger.info(f"OR")

                return (res or self._eval_measurement_condition(j_second_term, measures))

        return res

    def get_satisfied_tactics(
            self,
            tactic_names: List[str]) -> List[bool]:
        measures = self.latest_measures
        satisfied = []
        for j_action_rule in self.tacticsModel.getActionRules():
            for j_adaptation_rule in j_action_rule.getAdaptationRules():
                if (str(j_adaptation_rule.getName()) in tactic_names):
                    j_condition_action = self._get_condition_action(j_adaptation_rule)
                    j_measurement_condition = j_condition_action.getContextGuard().getContextCondition()
                    satisfied.append(self._eval_measurement_condition(j_measurement_condition, measures))

        return satisfied

    def get_relaxed_requirements_fulfillment(
            self,
            system_name: str,
            *requirement_names: List[str]) -> List[float]:
        """
        Fetch multiple relaxed requirements fulfillment.

        :param system_name: system name
        :param requirement_names: list of requirement names
        :return: list of fulfillment values
        """
        pass
        # return [x['fulfillment_' + str(i)]['value'] for i, x in enumerate(
        #     self.fetch_relaxed_requirements_fulfillment(system_name, *requirement_names))]


    # # This only works if there are more requirements than those mentioned in
    # # requirement_names.
    def update_requirements_in_effect(
            self, requirement_names, all_requirements):
        pass
        # if(not all_requirements):
        #     match_block = """
        #     match
        #         $requirement isa relaxed_requirement, has in_effect $in_effect,
        #         has requirement_name $req_name;
        #     """
        #     delete_block = """
        #     delete
        #     $requirement has $in_effect;
        #     """
        #     insert_block = """
        #     insert
        #     $requirement has in_effect false;
        #     """
        #     for i, requirement_name in enumerate(requirement_names):
        #         match_block += f"""
        #         $req_name != '{requirement_name}';
        #         $req_{i} isa relaxed_requirement,
        #         has requirement_name '{requirement_name}',
        #         has in_effect $eff_{i};
        #         """
        #         delete_block += f"""
        #             $req_{i} has $eff_{i};
        #         """
        #         insert_block += f"""
        #             $req_{i} has in_effect true;
        #         """
        #     query = match_block + delete_block + insert_block
        #     return self.update_database(query)
        # else:
        #     match_block = """
        #     match
        #     """
        #     delete_block = """
        #     delete
        #     """
        #     insert_block = """
        #     insert
        #     """
        #     for i, requirement_name in enumerate(requirement_names):
        #         match_block += f"""
        #         $req_{i} isa relaxed_requirement,
        #         has requirement_name '{requirement_name}',
        #         has in_effect $eff_{i};
        #         """
        #         delete_block += f"""
        #             $req_{i} has $eff_{i};
        #         """
        #         insert_block += f"""
        #             $req_{i} has in_effect true;
        #         """
        #     query = match_block + delete_block + insert_block
        #     return self.update_database(query)

    def get_relaxed_requirement_hypothetical_fulfillment(
            self, system_name: str, requirement_name: str, tactic_rule: str
    ):
        """
        Get hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param requirement_name: requirement name
        :param tactic_rule: tactic rule name
        :return: fulfillment value
        """\

        pass
        # query_result = self.fetch_relaxed_requirement_hypothetical_fulfillment(
        #     system_name, requirement_name, tactic_rule)
        # return query_result[0]['tactic_impact']['fulfillment'][0]['value']

    def get_relaxed_requirements_hypothetical_fulfillment(
            self, tactic_rules: List[str], system_name: str
    ):
        """
        Get hypothetical fulfillment of a relaxed requirement after applying a tactic rule.

        :param system_name: system name
        :param tactic_ruls: tactic rule names
        :return: fulfillment value
        """
        pass
        # x = {}
# 
        # query_result = self.fetch_relaxed_requirements_hypothetical_fulfillment(
            # tactic_rules, system_name)
# 
        # for rule in tactic_rules:
            # x[rule] = []
        # for singular_query_result in query_result:
            # for i, tactic_rule in enumerate(tactic_rules):
                # x[tactic_rule].append(
                    # singular_query_result['tactic_impact_' + str(i)]
                    # ['fulfillment'][0]['value'])
# 
        # return x


    def get_measures_interfaces(self, include_qos: bool = True):
        """
        Get measures and source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        result_dict_list = []

        for j_contextVar in self.contextModel.getEnvironmental_variables():
            result_dict = {}
            result_dict['measure_name'] = str(j_contextVar.getName())
            j_qualified_ref = j_contextVar.getSource().getRef()
            # j_node = j_contextVar.getSource().getNode()

            if (isinstance(j_qualified_ref, QualifiedPublisherRef)):
                j_pub_ref = (QualifiedPublisherRef) @ j_qualified_ref
                result_dict['source'] = "Publisher"
                # TODO: account for remapping
                result_dict['interface_type'] = str(j_pub_ref.getPublisher().getMessage().getFullname())
                result_dict['interface_name'] = str(j_pub_ref.getPublisher().getName())

                # for j_publisher in j_node.getFrom().getPublisher():
                #     if(str(j_publisher.getMessage().getFullname()) == result_dict['interface_type']):
                #         self.logger.info(f"Would objects also work? {j_publisher == j_pub_ref.getPublisher()}")
                #         result_dict['interface_name'] == 
            if (isinstance(j_qualified_ref, QualifiedActionServerRef)):
                j_act_ref = (QualifiedActionServerRef) @ j_qualified_ref
                result_dict['source'] = "ActionServer"
                result_dict['interface_type'] = str(j_act_ref.getActionServer().getAction().getFullname())
                result_dict['interface_name'] = str(j_act_ref.getActionServer().getName())

            if (isinstance(j_qualified_ref, QualifiedServiceServerRef)):
                j_ser_ref = (QualifiedServiceServerRef) @ j_qualified_ref
                result_dict['source'] = "ServiceServer"
                result_dict['interface_type'] = str(j_ser_ref.getServiceServer().getService().getFullname())
                result_dict['interface_name'] = str(j_ser_ref.getServiceServer().getName())
                result_dict["service_request_kwargs"] = str(j_contextVar.getKwargs())

            result_dict["measurement_function_name"] = str(j_contextVar.getFunctionName())

            lib = j_contextVar.getFunctionLibrary()
            if (lib is not None):
                result_dict["measurement_function_lib"] = str(lib)

            args = j_contextVar.getFunctionArgs()

            if (args is not None): 
                result_dict["measurement_function_args"] = str(args)

            proxy = bool(j_contextVar.getDoProxy())

            if (proxy is not False):
                result_dict["measurement_proxy"] = True

            period = int(j_contextVar.getPeriod())
            if (period != 0):
                result_dict["measurement_period"] = period

            # qos_dict = {}
            # qos_list = result.get('qos_sub_query')
            # if include_qos and isinstance(qos_list, list) and qos_list:
            #     qos = qos_list[0].get('qos')
            #     for attribute_label in (
            #         'reliability',
            #         'history',
            #         'depth',
            #         'durability',
            #         'deadline',
            #         'lifespan',
            #         'liveliness',
            #         'lease_duration',
            #     ):
            #         attribute_value = get_first_value(qos, attribute_label)
            #         if attribute_value is not None:
            #             qos_dict[attribute_label] = attribute_value

            # if qos_dict:
            #     result_dict['qos'] = qos_dict

            result_dict_list.append(result_dict)

        return result_dict_list

    def add_measurements(
            self,
            measure_dict, logger):
        """Add new measurements."""
        self.latest_measures = measure_dict



    def get_applicable_tactics(
            self,
            resolution_model: str,
            interface_name: str) -> dict[str, List[str]]:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interface_name: name of the ROS interface
        :return: dict of rules to feature adaptations
        """

        pass
        # query_result = self.fetch_applicable_tactics(
        #     resolution_model, interface_name)

        # rules = {}
        # for rule_query in query_result:
        #     rule_name = rule_query["rule_name"]["value"]

        #     rules[rule_name] = []

        #     for deselection in rule_query["deselecting_rules"]:
        #         feat = deselection["f_name"]["value"]
        #         rules[rule_name].append("deselect_" + feat)
        #     for selection in rule_query["selecting_rules"]:
        #         feat = selection["f_name"]["value"]
        #         rules[rule_name].append("select_" + feat)

        # return rules

    def _functional_mapping(self, action_name: str) -> Feature:
        j_func_maps = self.resolutionModel.getFunctionalMapping()
        for j_func_map in j_func_maps:
            self.logger.info(f"acc name {j_func_map.getAction().getName()}")
            if(action_name == str(j_func_map.getAction().getName())):
                return j_func_map.getFeature()

    def _subtree_features(self, feature, subtree: List[Feature],
                          func=partial(instanceis, Feature)):
        if (func(feature)):
            subtree.append(feature)

        if (int(feature.getChildren().size()) > 0):
            for child in feature.getChildren():
                self._subtree_features(child, subtree, func)

    def _isOptional(self, feature: Feature):
        return (not feature.isMandatory()) and (not isinstance(feature.getParent(), Alternative))

    def _featuresInvolvedInRule(feature, rule):
        selected_by = []
        deselected_by = []
        j_atomic_rule = (AtomicRule) @ rule
        j_rule_body = j_atomic_rule.getRuleBody()
        j_atomic_action = j_rule_body.getAtomicAction()
        for j_simple_action in j_atomic_action.getActions():
            if isinstance(j_simple_action, AtomicActionDeselectFeature):
                deselected_by.append(j_simple_action.getVariant().getFeature())
            if isinstance(j_simple_action, AtomicActionSelectFeature):
                selected_by.append(j_simple_action.getVariant().getFeature())
        return selected_by, deselected_by

    def get_fetch_policy(self, action_name: str):
        table = {}
        reconfigurations = []
        state_dict = {}
        j_feature = self._functional_mapping(action_name)
        self.logger.info(f"acc name {str(j_feature)}")

        p_available_alts = []
        # TODO: ensure alternative is mandatory.
        self._subtree_features(j_feature, p_available_alts, partial(instanceis, Alternative))
        available_alts_feats = []
        for feat in p_available_alts:
            available_alts_feats.extend(feat.getChildren())
        available_opts_feats = []
        self._subtree_features(j_feature, available_opts_feats, self._isOptional)

        for i, j_state in enumerate(self.j_states):
            state_name = f"state_{i}"
            if (int(j_state.associatedRules.size()) > 0):
                state_dict[state_name] = [str(rule.getName()) for rule in j_state.associatedRules]
            for rule in j_state.associatedRules:
                selected_by, deselected_by = self._featuresInvolvedInRule(rule)
                for alt in available_alts_feats:
                    sel_feat = 'select_' + str(alt.getName())

                    if (alt in selected_by):
                        reconfigurations.append(sel_feat)
                        table[(sel_feat, state_name)] = rule.getName()
                    # It is not allowed to deselect a mandatory alt.
                for opt in available_opts_feats:
                    sel_feat = 'select_' + str(opt.getName())
                    desel_feat = 'deselect_' + str(opt.getName())

                    if (opt in selected_by):
                        reconfigurations.append(sel_feat)
                        table[(sel_feat, state_name)] = str(rule.getName())
                    if (opt in deselected_by):
                        reconfigurations.append(desel_feat)
                        table[(desel_feat, state_name)] = str(rule.rule.getName())

        return state_dict, table, reconfigurations

    # def get_reconfiguration_plan(self, tactic_rule: str) -> AdaptationPlan:
    #     query_result = self.fetch_reconfiguration_plan(tactic_rule)
    #     return AdaptationPlan.from_typedb_results(query_result)

    def get_reconfiguration_plan_compact(self, feature_name: str, vation: str) -> list[str]:
        pass
        # try:
        #     query_result = self.fetch_reconfiguration_plan_compact(feature_name, vation)
        #     actions_with_index: list[tuple[int, str]] = []
        #     for ftch in query_result:
        #         actions_with_index.append(
        #             (ftch["index"]["value"], ftch["action_name"]["value"]))
        #     ordered_actions = [
        #         action for _, action in sorted(actions_with_index, key=lambda pair: pair[0])
        #     ]

        # except Exception as e:
        #     raise e

        # return ordered_actions

    # TODO: use dict?
    def lifecycleStateToTransition(self, j_lc_state: LifeCycleState):
        if (j_lc_state == LifeCycleState.UNCONFIGURED):
            return Transition(id=Transition.TRANSITION_CLEANUP),
        if (j_lc_state == LifeCycleState.INACTIVE):
            return Transition(id=Transition.TRANSITION_DEACTIVATE),
        if (j_lc_state == LifeCycleState.ACTIVE):
            return Transition(id=Transition.TRANSITION_ACTIVATE)
        if (j_lc_state == LifeCycleState.FINALIZED):
            return Transition(id=Transition.TRANSITION_ACTIVE_SHUTDOWN)

    def paramToRosParameterMsg(self, j_param, j_param_value):
        param_name = j_param.getName()
        param_value = valueOf(j_param_value)
        return Parameter(param_name, value=param_value).to_parameter_msg()

    def reconfigurationToAdaptation(self, j_reconfiguration: Reconfiguration) -> Adaptation:
        node_name = str(j_reconfiguration.getNode().getName())

        if (isinstance(j_reconfiguration, SetLifecycle)):
            j_lc_state = ((SetLifecycle) @ j_reconfiguration).getState()
            return Adaptation(adaptation_target=Adaptation.STATETRANSITION,
                              node_name=node_name,
                              lifecycle_adaptation=self.lifecycleStateToTransition(j_lc_state)
                              )
        if (isinstance(j_reconfiguration, SetParam)):
            j_param = ((SetParam) @ j_reconfiguration).getParam()
            j_param_val = ((SetParam) @ j_reconfiguration).getValue()
            param_msg = self.paramToRosParameterMsg(j_param, j_param_val)

            return Adaptation(adaptation_target=Adaptation.ROSPARAMETER,
                              node_name=str(node_name),
                              parameter_adaptation=param_msg)

    def get_resolution_adaptations(self, logger=logger):

        resolution_to_adaptations = {}
        for j_resolution in self.resolutionModel.getResolutions():
            j_resolution.getSelection_actions()

            
            j_resolution.getDeselection_actions()

        # logger.info("Testsss")
        # query_result = self.fetch_resolution_adaptations()
        # logger.info("1")

        # resolution_to_adaptations = {}
        # for part in query_result:
        #     actions = []
        #     for lifecycle_entry in part.get('set_lifecycle_action', []):
        #         actions.append(_parse_lifecycle_action(lifecycle_entry))

        #     for parameter_entry in part.get('set_parameter_action', []):
        #         actions.append(_parse_parameter_action(parameter_entry))
        #     resolution_to_adaptations[part["action_name"]["value"]] = actions
        # logger.info("2")
        # return resolution_to_adaptations
