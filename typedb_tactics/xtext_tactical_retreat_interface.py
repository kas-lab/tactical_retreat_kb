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
from system import RosPublisherReference
from rosToolingSupport import RosToolingSupport
from de.fraunhofer.ipa.ros import RosStandaloneSetupGenerated
from de.fraunhofer.ipa.rossystem import RosSystemStandaloneSetupGenerated
from de.fraunhofer.ipa.ros2 import Ros2StandaloneSetupGenerated
from eu.coresense.variability import FeatureModelStandaloneSetupGenerated
from eu.coresense.resolution import ResolutionModelStandaloneSetupGenerated, Resolver
from eu.coresense.context import ContextModelStandaloneSetupGenerated
from eu.coresense.requirements import RequirementsModelStandaloneSetupGenerated
from eu.coresense.adaptation import TacticsStandaloneSetupGenerated

from org.eclipse.xtext.resource import XtextResourceSet
from org.eclipse.xtext.serializer import ISerializer
from eu.coresense.common import NameProvider
from eu.coresense.context.generator import ContextNameProvider
from eu.coresense.resolution.generator import ResolutionNameProvider
from eu.coresense.adaptation.generator import TacticsNameProvider
from eu.coresense.common import RosNameProvider, MathOperator, Literal, IntLiteral, DecimalLiteral
from eu.coresense.common import StringLiteral, BooleanLiteral

from eu.coresense.adaptation.tactics import TacticsModel, ConditionAction, ActionRules, AdaptationRule
from eu.coresense.adaptation.tactics import MeasurementThresholdCondition, LogicalOperator
from eu.coresense.adaptation.tactics import AtomicActionDeselectFeature, AtomicActionSelectFeature
from eu.coresense.adaptation.tactics import TacticsFactory
from eu.coresense.requirements.generator import RequirementsModelGenerator
from eu.coresense.requirements.requirementsModel import RequirementsModel, AsCloseLit, Shall
from eu.coresense.requirements.requirementsModel import Negation, CompoundExpression, And, Or
from eu.coresense.requirements.requirementsModel import Quantifiable, AsAsPossible
from eu.coresense.requirements.requirementsModel import FuzzyTriangular as J_FuzzyTriangular
from eu.coresense.requirements.requirementsModel import FuzzyRightShoulder as J_FuzzyRightShoulder
from eu.coresense.requirements.requirementsModel import FuzzyLeftShoulder as J_FuzzyLeftShoulder


from eu.coresense.resolution.resolutionModel import ResolutionModel, Reconfiguration, SetParam
from eu.coresense.resolution.resolutionModel import SetLifecycle, LifecycleState
from eu.coresense.context.contextModel import ContextModel, QualifiedPublisherRef, QualifiedRef, CompositeRef
from eu.coresense.context.contextModel import QualifiedActionServerRef, QualifiedServiceServerRef
from uma.caosd.rhea.AdvancedConstraintsFMmetamodel import AdvancedConstraintsFMmetamodelPackage
from uma.caosd.rhea.BasicFMmetamodel import Feature, Alternative, OrGroup
from java.lang import String, Integer
from java.util import HashSet, ArrayList
from java.nio.file import Files
from java.io import FileWriter
from ros import ParameterBoolean, ParameterInteger, ParameterDouble
from ros import ParameterString, ParameterSequence
from eu.coresense.variability.generator import FeatureModelGenerator
from de.ovgu.featureide.fm.core.io.manager import FeatureModelManager, ConfigurationIO

from de.ovgu.featureide.fm.core.analysis.cnf.formula import FeatureModelFormula
from de.ovgu.featureide.fm.core.configuration import Configuration, ConfigurationAnalyzer, ConfigurationPropagator, Selection
from de.ovgu.featureide.fm.core.job import LongRunningWrapper, SliceFeatureModel
from de.ovgu.featureide.fm.core.base import FeatureUtils
from de.ovgu.featureide.fm.core.init import LibraryManager
from de.ovgu.featureide.fm.core.init import FMCoreLibrary
from typedb_tactics.fuzzy.fuzzy_expressions import Proposition, Expression, FuzzyAnd, FuzzyOr, FuzzyNot
from typedb_tactics.fuzzy.fuzzy_sets import FuzzyTriangular, FuzzyRightShoulder, FuzzyLeftShoulder
from typedb_tactics.fuzzy.relaxed_requirements import AsCloseAsPossibleExpression, ShallExpression, AsManyAsPossibleExpression
from eu.coresense.adaptation.generator import State, TQLGenerator


logger = logging.getLogger(__name__)


def instanceis(clas, obj):
    return isinstance(obj, clas)


def _value_from_lit(lit):
    if (isinstance(lit, DecimalLiteral)):
        return float((DecimalLiteral @ lit).getValue().floatValue())
    if (isinstance(lit, IntLiteral)):
        return int((IntLiteral @ lit).getValue())
    if (isinstance(lit, StringLiteral)):
        return str((StringLiteral @ lit).getValue())
    if (isinstance(lit, BooleanLiteral)):
        return bool((BooleanLiteral @ lit).isValue())
    return lit


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


YELLOW_BOLD = "\033[33;1m"
RESET = "\033[0m"


def getSubtreeFeatures(root):
    res = ArrayList()
    if (not res.contains(root.getName())):
        res.add(root.getName())

    children = FeatureUtils.getChildren(root)
    if (children is not None):
        for f in children:
            res.addAll(getSubtreeFeatures(f))
    return res


def tofloat(bigdecimal) -> float:
    return float(bigdecimal.floatValue())


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
                 generate_state: bool = False,
                 consider_features_in_state: bool = False, logger=logger) -> None:
        RosToolingSupport.registerEPackages()
        AdvancedConstraintsFMmetamodelPackage.eINSTANCE.eClass()

        self.resSet = XtextResourceSet()
        self.logger = logger
        self.logger.info(f"{ros_path}")
        self.load_model("ros", RosStandaloneSetupGenerated(), ros_path)
        self.ros2Resources = self.load_model("ros2", Ros2StandaloneSetupGenerated(), ros2_path)
        self.rosSystemResources = self.load_model("rossystem", RosSystemStandaloneSetupGenerated(),
                                                  rossystem_path)
        fmResources, _ = self.load_model("var", FeatureModelStandaloneSetupGenerated(), var_path)
        resSources, _ = self.load_model("resolution", ResolutionModelStandaloneSetupGenerated(),
                                        resolution_path)
        contextResources, _ = self.load_model("context", ContextModelStandaloneSetupGenerated(),
                                              context_path)
        requirementsResources, _ = self.load_model("reqs",
                                                   RequirementsModelStandaloneSetupGenerated(),
                                                   reqs_path)
        tacticsResources, self.tacticsInjector = self.load_model("tactics",
                                                                 TacticsStandaloneSetupGenerated(),
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

        self.resolver = Resolver(self.resolutionModel)
        TQLGenerator.setGlobalResource(self.tacticsModelResource)

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

        # for j_action_rule in self.tacticsModel.getActionRules():
        #     self.j_states_map = TQLGenerator.createStates(self.tacticsModel,
        #                                                   self.requirementsModel,
        #                                                   consider_features_in_state)
        #     for key in self.j_states_map.keySet():
        #         self.logger.info(f"{str(key)} - \
        #                           {str(self.j_states_map.get(key).size())} states generated")
        if (generate_state):
            self.j_states = TQLGenerator.createStates(self.contextModel)

            self.logger.info(f"{str(self.j_states.size())} states generated")
            for j_state in self.j_states:
                self.logger.info(f"{str(State.render(j_state.precondition))} states generated")

        self.namer = NameProvider()
        self.namer.register(ResolutionNameProvider())

        LibraryManager.registerLibrary(FMCoreLibrary.getInstance())

        path = Files.createTempFile("featuremodel", ".xml")
        fw = FileWriter(path.toFile(), True)

        generator = FeatureModelGenerator()
        fm_xml = generator.generateXml(self.DSLFeatureModel.getFm())
        fw.write(fm_xml)
        fw.close()

        conf_path = Files.createTempFile("configuration", ".xml")
        fw = FileWriter(conf_path.toFile(), True)

        conf_xml = generator.generateConfiguration(self.DSLFeatureModel.getFm())

        fw.write(conf_xml)
        fw.close()
        self.featureModel = FeatureModelManager.load(path)

        formula = FeatureModelFormula(self.featureModel)
        self.fmConfiguration = ConfigurationIO.getInstance().load(conf_path,
                                                                  FeatureModelManager
                                                                  .getInstance(path))
        self.logger.info(f"conf ? {str(self.fmConfiguration.toString())}")
        # select_exclusive(configuration, formula, "MPPI", Selection.UNSELECTED, logger)
        # select_exclusive(configuration, formula, "RPP", Selection.SELECTED, logger)
        # propagator = ConfigurationPropagator(formula, self.fmConfiguration)

        self.action_allconf = {}
        self.latest_measures = {}
        self.in_effect_requirements = []
        self.traversed_requirements = {}

        for j_req in self.requirementsModel.getRequirements():
            some_list = []
            self.traverseExpression(j_req.getExpression(), some_list)
            self.traversed_requirements[j_req] = some_list

        self.configurationPropagator = ConfigurationPropagator(formula, self.fmConfiguration)

        # p = LongRunningWrapper.runMethod(propagator.coverFeatures(["MPPI_DIFF"], False))
        # self.logger.info(f"assertTrue ? {str(p)}")

        # self.logger.info(f"assertTrue ? {str(LongRunningWrapper.runMethod(propagator.isValid()))}")

        # self.logger.info(f"assertEquals Selection.UNDEFINED = {str(self.fmConfiguration.getSelectableFeature("MPPI_OMNI").getManual())}")
        # self.logger.info(f"assertEquals Selection.SELECTED = {str(self.fmConfiguration.getSelectableFeature("MPPI_DIFF").getManual())}")

        # self.to_xtext(first_state)
        # LongRunningWrapper.runMethod(propagator.update())

        # self.logger.info(f"conf aft ? {str(self.fmConfiguration.getSelectedFeatureNames())}")

        # valid = LongRunningWrapper.runMethod(propagator.isValid())
        # if not valid:
        #     self.logger.warning("Update produced an invalid/contradictory configuration!")
        self.update_requirements_in_effect(requirement_names=[], all_requirements=True)
        self.logger.info("ready")

    def to_xtext(self, j_state):
        # TODO: needs to be updated to new TacticsModel changes.
        pass
        # TacticsFactory.eINSTANCE.createMeasurementCondition()
        # j_context_guard = TacticsFactory.eINSTANCE.createContextGuard()
        # j_context_guard.setContextCondition(j_state.precondition)
        # j_condition_action = TacticsFactory.eINSTANCE.createConditionAction()
        # j_atomic_rule = TacticsFactory.eINSTANCE.createAtomicRule()
        # j_condition_action.setContextGuard(j_context_guard)

        # res_model = TQLGenerator.getResolutionModel(self.tacticsModel, self.tacticsModelResource).get(Integer @ 0)

        # j_f_qref = TacticsFactory.eINSTANCE.createQualifiedFeatureRef()
        # j_f_qref.setModel(res_model)
        # j_f_qref.setFeature(res_model.getResolutions().get(Integer @ 0).getFeatureRef().getFeature())

        # j_a = TacticsFactory.eINSTANCE.createAtomicActionSelectFeature()
        # j_a.setVariant(j_f_qref)

        # j_b = TacticsFactory.eINSTANCE.createAtomicAction()
        # j_b.getActions().add(j_a)
        # j_condition_action.setAtomicAction(j_b)

        # j_atomic_rule.setRuleBody(j_condition_action)  # condition action extends rulebody
        # j_atomic_rule.setName("placeholder")
        # # j_tactics_model = TacticsFactory.eINSTANCE.createTacticsModel()
        # j_action_rules = TacticsFactory.eINSTANCE.createActionRules()
        # j_action_rules.getAdaptationRules().add(j_atomic_rule)

        # j_func_map = self.resolutionModel.getFunctionalMapping().get(Integer @ 0)
        # j_action_rules.setAction(j_func_map.getAction())

        # self.tacticsModel.getRules().get(Integer @ 0).getAdaptationRules().add(j_atomic_rule)

        # # injector = TacticsStandaloneSetupGenerated().createInjectorAndDoEMFRegistration()
        # serializer = self.tacticsInjector.getInstance(ISerializer.class_)

        # # self.tacticsModelResource.getContents().add(j_tactics_model)
        # dslText = serializer.serialize(self.tacticsModel)

        # self.logger.info(f"dsltext {str(dslText)}")
        # # createActionRules
        # # createAdaptationRule

    def _to_python_fuzzy_set(self, j_membership_function):
        if isinstance(j_membership_function, J_FuzzyTriangular):
            j_fuzzy_tri = (J_FuzzyTriangular) @ j_membership_function
            return FuzzyTriangular(
                a=tofloat(j_fuzzy_tri.getA()),
                b=tofloat(j_fuzzy_tri.getB()),
                c=tofloat(j_fuzzy_tri.getC())
            )

        if isinstance(j_membership_function, J_FuzzyRightShoulder):
            j_fuzzy_rsh = (J_FuzzyRightShoulder) @ j_membership_function
            return FuzzyRightShoulder(
                foot=tofloat(j_fuzzy_rsh.getFoot()),
                shoulder=tofloat(j_fuzzy_rsh.getShoulder())
            )

        if isinstance(j_membership_function, J_FuzzyLeftShoulder):
            j_fuzzy_lsh = (J_FuzzyLeftShoulder) @ j_membership_function
            return FuzzyLeftShoulder(
                foot=tofloat(j_fuzzy_lsh.getFoot()),
                shoulder=tofloat(j_fuzzy_lsh.getShoulder())
            )

        raise TypeError(
            f"Unsupported membership function: {j_membership_function}"
        )

    def to_fuzzy(self, j_expression_list: list) -> Optional[Expression]:
        j_expression = j_expression_list[0]
        if isinstance(j_expression, AsCloseLit):
            j_as_close_lit = (AsCloseLit) @ j_expression
            req_value = _value_from_lit(j_as_close_lit.getQuantity())

            prop = self.to_fuzzy([j_as_close_lit.getComparator()])
            if (prop is None):
                return None
            fuzzy_set = self._to_python_fuzzy_set(
                j_as_close_lit.getMembershipFunction()
            )
            return AsCloseAsPossibleExpression(proposition=prop, fuzzy_set=fuzzy_set,
                                               required_value=float(req_value))
        if isinstance(j_expression, AsAsPossible):
            j_as_as_possible = (AsAsPossible) @ j_expression

            measure_name = str(j_as_as_possible.getQuantity().getContextVariable().getName())

            mes = self.latest_measures.get(measure_name, None)
            if (mes is None):
                return None
            prop = Proposition(name=measure_name, value=mes)
            fuzzy_set = self._to_python_fuzzy_set(
                j_as_as_possible.getMembershipFunction()
            )
            return AsManyAsPossibleExpression(proposition=prop, fuzzy_set=fuzzy_set)
        if isinstance(j_expression, CompoundExpression):
            # self.logger.info(f"here!! {j_expression} {CompoundExpression} {And}")
            right_index = 2
            left_fuzzy = None
            right_fuzzy = None
            left_child = j_expression_list[1]
            if (isinstance(left_child, Negation)):
                left_fuzzy = self.to_fuzzy(j_expression_list[1:3])
                right_index += 1
            else:
                left_fuzzy = self.to_fuzzy([left_child])

            right_child = j_expression_list[right_index]

            if (isinstance(right_child, Negation)):
                right_fuzzy = self.to_fuzzy(j_expression_list[right_index:right_index+2])
            else:
                right_fuzzy = self.to_fuzzy([right_child])

            if isinstance(left_child, CompoundExpression) or isinstance(right_child,
                                                                        CompoundExpression):
                raise NotImplementedError

            fuzzy_children: List[Expression] = [left_fuzzy, right_fuzzy]
            # self.logger.info(f"fuzzy children {left_child} {right_child} {fuzzy_children}")
            if (any(child is None for child in fuzzy_children)):
                return None
            if isinstance(j_expression, And):
                return FuzzyAnd(*fuzzy_children)

            if isinstance(j_expression, Or):
                return FuzzyOr(*fuzzy_children)

        if isinstance(j_expression, Quantifiable):
            measure_name = str(j_expression.getContextVariable().getName())

            mes = self.latest_measures.get(measure_name, None)
            if (mes is None):
                return None
            return Proposition(name=measure_name, value=mes)

        if isinstance(j_expression, Negation):

            child = j_expression_list[1]

            if isinstance(child, CompoundExpression):  # or negation I suppose?
                raise NotImplementedError

            fuzzy_child = self.to_fuzzy([child])

            if (fuzzy_child is not None):
                return FuzzyNot(self.to_fuzzy([child]))
            else:
                return None
            # TODO: the below... is
            # if(isinstance(j_as_as_possible.getTimeFrequency(), ))

        # if isinstance(j_expression, Shall):
        #     self.logger.info("s")
        #     j_shall = (Shall) @ j_expression
        #     j_expression_list.append(j_shall)
        #     self.traverseExpression(j_shall.getExpression(), j_expression_list)
        #     return

    def progress_message(self, msg: str):
        self.logger.info(f"{YELLOW_BOLD}{msg}{RESET}")

    def load_model(self, ext, setup_obj, path):
        loadresult = RosToolingSupport.loadModel(
            setup_obj,
            self.resSet,
            ext,
            path,
        )

        self.progress_message(f"Loaded {int(loadresult.resources.size())}.{ext} files")
        return loadresult.resources, loadresult.injector

    def getContextVar(self, string_name):
        for contextVar in self.contextModel.getEnvironmental_variables():
            if (contextVar.getName() == string_name):
                return contextVar
        raise Exception(f"Couldn't find contextVar {string_name}")

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

    def _get_condition_action(self, j_atomic_rule: AdaptationRule) -> ConditionAction:
        j_atomic_rule = (AdaptationRule) @ j_atomic_rule
        j_rule_body = j_atomic_rule.getRuleBody()
        j_tactic_action = j_rule_body.getAction()
        if (isinstance(j_tactic_action, ConditionAction)):
            return (ConditionAction) @ j_tactic_action

    def _eval_feature_condition(self, j_feature_condition, configuration) -> bool:
        sel_or_not = str(j_feature_condition.getNot()) == "!"
        feature_name = str(j_feature_condition.getVariant().getFeature().getName())

        res = False
        j_second_term = j_feature_condition.getSecondTerm()
        j_log_op = j_feature_condition.getLogicalOp()

        if (not sel_or_not):
            res = feature_name in configuration
        else:
            res = not (feature_name in configuration)

        if (j_log_op is not None) and (j_second_term is not None):
            if (j_log_op == LogicalOperator.AND):
                self.logger.info("and")

                return (res and self._eval_measurement_condition(j_second_term, configuration))
            if (j_log_op == LogicalOperator.OR):
                self.logger.info("OR")

                return (res or self._eval_measurement_condition(j_second_term, configuration))

        return res

    def _eval_measurement_condition(self, j_measurement_condition, measures) -> bool:
        # self.logger.info("called")

        context_var_name = str(j_measurement_condition
                               .getMeasurement().getName())
        context_val = measures.get(context_var_name, None)

        if context_val is None:
            return False

        j_operator = j_measurement_condition.getOperator()

        comparator = None
        if (isinstance(j_measurement_condition, MeasurementThresholdCondition)):
            j_threshold = ((MeasurementThresholdCondition)
                           @ j_measurement_condition).getThresholdValue()
            comparator = _value_from_lit(j_threshold)

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
        # self.logger.info(f"loggg op {str(j_log_op)}")
        # self.logger.info(f"loggg op {str(j_second_term)}")

        # j_log_op_val = j_log_op.getValue()
        if (j_log_op is not None) and (j_second_term is not None):
            if (j_log_op == LogicalOperator.AND):
                self.logger.info("and")

                return (res and self._eval_measurement_condition(j_second_term, measures))
            if (j_log_op == LogicalOperator.OR):
                self.logger.info("OR")

                return (res or self._eval_measurement_condition(j_second_term, measures))

        return res

    def _current_configuration(self):
        return [str(f) for f in self.fmConfiguration.getSelectedFeatureNames()]

    def _adaptation_rule_satisfied(self, j_adaptation_rule: AdaptationRule,
                                   tactic_names):
        measures = self.latest_measures
        current_configuration = set(self._current_configuration()) #set(self.action_currconf[action_name])
        self.logger.info(f"current_configuration {str(current_configuration)}")
        # TODO: invert this, we should grab for the rules requested, not eliminate from all
        if (str(j_adaptation_rule.getName()) in tactic_names):
            j_condition_action = self._get_condition_action(j_adaptation_rule)
            if (j_condition_action is not None):
                feature_guard = True
                condition_guard = True
                if (j_condition_action.getFeatureGuard() is not None):
                    j_feature_condition = j_condition_action.getFeatureGuard() \
                        .getFeatureCondition()
                    feature_guard = self._eval_feature_condition(j_feature_condition,
                                                                 current_configuration)
                if (j_condition_action.getContextGuard() is not None):
                    j_measurement_cond = j_condition_action.getContextGuard() \
                        .getContextCondition()
                    condition_guard = self._eval_measurement_condition(j_measurement_cond,
                                                                       measures)
                return feature_guard and condition_guard
            else:
                return True
                # self.logger.info(f"feat guard {feature_guard} condition_guard {condition_guard}")

    def _get_satisfied_action_tactics(self, tactic_names, action_name):
        satisfied = []

        for j_rule in self.tacticsModel.getRules():
            if (isinstance(j_rule, ActionRules)):
                j_action_rule = j_rule
                for j_adaptation_rule in j_action_rule.getAdaptationRules():
                    sat = self._adaptation_rule_satisfied(j_adaptation_rule, tactic_names)
                    if sat is not None:
                        satisfied.append(sat)
                    else:
                        self.logger.info(f"sat was none for {str(j_adaptation_rule.getName())}")

        return satisfied

    def _get_satisfied_global_tactics(self, tactic_names):
        satisfied = []

        for j_rule in self.tacticsModel.getRules():
            if (isinstance(j_rule, AdaptationRule)):
                j_adaptation_rule = j_rule
                sat = self._adaptation_rule_satisfied(j_adaptation_rule, tactic_names)
                if sat is not None:
                    satisfied.append(sat)
                else:
                    self.logger.info(f"sat was none for {str(j_adaptation_rule.getName())}")

        return satisfied

    def get_satisfied_tactics(
            self,
            tactic_names: List[str],
            action_name) -> List[bool]:
        satisfied = []

        if(action_name != ""):
            satisfied = self._get_satisfied_action_tactics(tactic_names, action_name)
        else:
            satisfied = self._get_satisfied_global_tactics(tactic_names)

        self.logger.info(f"satisfied {tactic_names} {str(satisfied)}")

        return satisfied

    def traverseExpression(self, j_expression, j_expression_list: list):
        self.logger.info(f"expr {j_expression}")
        if isinstance(j_expression, AsCloseLit):
            self.logger.info("asl")

            j_expression_list.append(j_expression)
            return
        if isinstance(j_expression, AsAsPossible):
            self.logger.info("asm")

            j_expression_list.append(j_expression)
            return
        if isinstance(j_expression, CompoundExpression):
            self.logger.info("cmp")
            j_compound = j_expression
            j_left_expr = j_compound.getLeftExpression()
            j_right_expr = j_compound.getRightExpression()

            j_expression_list.append(j_compound)
            self.traverseExpression(j_left_expr, j_expression_list)
            self.traverseExpression(j_right_expr, j_expression_list)
            return
        if isinstance(j_expression, Shall):
            self.logger.info("s")
            j_shall = (Shall) @ j_expression
            j_expression_list.append(j_shall)
            self.traverseExpression(j_shall.getExpression(), j_expression_list)
            return
        if isinstance(j_expression, Negation):
            j_neg = (Negation) @ j_expression
            j_expression_list.append(j_neg)
            self.traverseExpression(j_neg.getExpression(), j_expression_list)
            return
        if isinstance(j_expression, Quantifiable):
            j_expression_list.append(j_expression)
            return

        raise Exception(f"{j_expression} {j_expression_list} unknown type")

    def get_relaxed_requirements_fulfillment(
            self,
            system_name: str,
            *requirement_names: List[str]) -> None:
        """
        Fetch multiple relaxed requirements fulfillment.

        :param system_name: system name
        :param requirement_names: list of requirement names
        :return: list of fulfillment values
        """
        pass

    def update_requirements_in_effect(self, requirement_names, all_requirements):
        if (all_requirements):
            self.in_effect_requirements = [j_req
                                           for j_req in self.requirementsModel.getRequirements()]
        else:
            self.in_effect_requirements = []
            for req_name in requirement_names:
                for j_req in self.requirementsModel.getRequirements():
                    if j_req.getName() == req_name:
                        self.in_effect_requirements.append(j_req)

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

    def get_measures_interfaces(self, include_qos: bool = True):
        """
        Get measures and source interfaces.

        :param include_qos: include QoS details for publisher sources
        """
        result_dict_list = []

        for j_contextVar in self.contextModel.getEnvironmental_variables():
            result_dict = {}
            result_dict['measure_name'] = str(j_contextVar.getName())
            j_reference = j_contextVar.getSource().getRef()
            if (isinstance(j_reference, QualifiedRef)):
                j_qualified_ref = j_reference

            # j_node = j_contextVar.getSource().getNode()
                if (isinstance(j_qualified_ref, QualifiedPublisherRef)):

                    j_pub_ref = (QualifiedPublisherRef) @ j_qualified_ref
                    result_dict['source'] = "Publisher"
                    # TODO: account for remapping
                    result_dict['interface_type'] = str(j_pub_ref.getPublisher().getMessage()
                                                        .getFullname())
                    result_dict['interface_name'] = str(j_pub_ref.getPublisher().getName())

                    for interface in j_pub_ref.getNode().getRosinterfaces():
                        reference = interface.getReference()
                        if (isinstance(reference, RosPublisherReference)):
                            if (reference.getFrom() == j_pub_ref.getPublisher()):
                                result_dict['interface_name'] = str(interface.getName())

                    # for j_publisher in j_node.getFrom().getPublisher():
                    #     if(str(j_publisher.getMessage().getFullname()) == result_dict['interface_type']):
                    #         self.logger.info(f"Would objects also work? {j_publisher == j_pub_ref.getPublisher()}")
                    #         result_dict['interface_name'] ==
                if (isinstance(j_qualified_ref, QualifiedActionServerRef)):
                    j_act_ref = (QualifiedActionServerRef) @ j_qualified_ref
                    result_dict['source'] = "ActionServer"
                    result_dict['interface_type'] = str(j_act_ref.getActionServer().getAction()
                                                        .getFullname())
                    result_dict['interface_name'] = str(j_act_ref.getActionServer().getName())

                if (isinstance(j_qualified_ref, QualifiedServiceServerRef)):
                    j_ser_ref = (QualifiedServiceServerRef) @ j_qualified_ref
                    result_dict['source'] = "ServiceServer"
                    result_dict['interface_type'] = str(j_ser_ref.getServiceServer().getService()
                                                        .getFullname())
                    result_dict['interface_name'] = str(j_ser_ref.getServiceServer().getName())
                    result_dict["service_request_kwargs"] = str(j_contextVar.getKwargs())
            elif (isinstance(j_reference, CompositeRef)):
                j_composite_ref = (CompositeRef) @ j_reference
                result_dict['source'] = "Composite"
                result_dict['measure_names'] = [str(j_ctxtVar.getName())
                                                for j_ctxtVar in j_composite_ref.getContextVars()]

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

    def _reconfs(self, j_adaptation_rule):
        selected_by, deselected_by = self._featuresInvolvedInRule(j_adaptation_rule)
        reconfs = []

        for feat in selected_by:
            reconfs.append("SEL_" + str(feat.getName()))
        for feat in deselected_by:
            reconfs.append("DESEL_" + str(feat.getName()))

        return reconfs

    def _get_applicable_action_tactics(self, resolution_model, interface_name):
        res = {}
        # slicedFormula, subconf = self._find_subconfiguration(interface_name)
        # undef_subconf = Configuration(slicedFormula)

        # # p_available_alts = []
        # configurationAnalyzer = ConfigurationAnalyzer(slicedFormula, undef_subconf)
        # allConfigurations = configurationAnalyzer.getSolutions(100000)
        # all_configurations = []
        # for k, featureList in enumerate(allConfigurations):
        #     all_configurations.append(sorted({str(feature) for feature in featureList
        #                               if str(feature) != "__root__"}))

        # self.action_allconf[interface_name] = all_configurations
        # self.action_currconf[interface_name] = sorted({str(feat)
        #                                                for feat in
        #                                                subconf.getSelectedFeatureNames()})

        for j_rule in self.tacticsModel.getRules():
            j_requirement = j_rule.getRequirement()
            req_name = "None"
            if (j_requirement is not None):
                req_name = j_requirement.getName()

            if (isinstance(j_rule, ActionRules)):
                j_action_rule = j_rule
                self.logger.info(f"{interface_name} 2 {str(j_action_rule.getAction().getName())}")

                if (interface_name == str(j_action_rule.getAction().getName())):
                    self.logger.info("3")
                    for j_adap_rule in j_action_rule.getAdaptationRules():
                        res[(str(j_adap_rule.getName()),
                             str(req_name))] = self._reconfs(j_adap_rule)

        return res


    def _get_applicable_global_tactics(self, resolution_model):
        res = {}

        for j_rule in self.tacticsModel.getRules():
            j_requirement = j_rule.getRequirement()
            req_name = "None"
            if (j_requirement is not None):
                req_name = j_requirement.getName()

            if (isinstance(j_rule, AdaptationRule)):
                j_adap_rule = j_rule
                res[(str(j_adap_rule.getName()), req_name)] = self._reconfs(j_adap_rule)

        return res

    def get_applicable_tactics(
            self,
            resolution_model: str,
            interface_name: str) -> dict:
        """
        Get all tactics that are applicable given an ROS action name and resolution model.

        :param resolution_model: name of the resolution model to check
        :param interfafa_listce_name: name of the ROS interface
        :return: dict of rules to feature adaptations
        """
        res = {}

        if(interface_name != ""):
            res = self._get_applicable_action_tactics(resolution_model, interface_name)
        else:
            res = self._get_applicable_global_tactics(resolution_model)

        return res

    def _requirement_fulfilment(self, j_req):
        traversed = self.traversed_requirements[j_req]
        j_first_expr = traversed[0]
        if (isinstance(j_first_expr, Shall)):
            fuzzified = self.to_fuzzy(traversed[1:])
            # self.logger.info(f"fuzzified? {fuzzified}")
            if (fuzzified is not None):
                s = ShallExpression(fuzzified)
                return s.fulfillment

    def get_in_effect_requirement_fulfillment(self):
        ff = []
        for j_req in self.in_effect_requirements:
            j_feature_qual = j_req.getFeatureQualifier()
            if (j_feature_qual is not None):
                all_selected_features = set(sorted({str(feat) for feat in self.fmConfiguration.getSelectedFeatureNames()}))
                if str(j_feature_qual.getFeature().getName()) in all_selected_features:
                    req_ff = self._requirement_fulfilment(j_req)
                    if ff is not None:
                        ff.append(
                            {
                                'requirement_name': str(j_req.getName()),
                                'fulfillment': req_ff,
                                'system': ''
                            }
                        )
            else:
                req_ff = self._requirement_fulfilment(j_req)
                if ff is not None:
                    ff.append(
                        {
                            'requirement_name': str(j_req.getName()),
                            'fulfillment': req_ff,
                            'system': ''
                        }
                    )
        return ff

    def _functional_mapping(self, action_name: str) -> Feature:
        j_func_maps = self.resolutionModel.getFunctionalMapping()
        for j_func_map in j_func_maps:
            self.logger.info(f"acc name {j_func_map.getAction().getName()}")
            if (action_name == str(j_func_map.getAction().getName())):
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

    def _featuresInvolvedInRule(self, rule):
        selected_by = []
        deselected_by = []
        j_atomic_rule = (AdaptationRule) @ rule
        j_rule_body = j_atomic_rule.getRuleBody()
        j_atomic_action = j_rule_body.getAction().getAtomicAction()
        for j_simple_action in j_atomic_action.getActions():
            if isinstance(j_simple_action, AtomicActionDeselectFeature):
                deselected_by.append(j_simple_action.getVariant().getFeature())
            if isinstance(j_simple_action, AtomicActionSelectFeature):
                selected_by.append(j_simple_action.getVariant().getFeature())
        return selected_by, deselected_by

    # def _find_subconfiguration(self, action_name):
    #     j_feature = self._functional_mapping(action_name)
    #     if j_feature is None:
    #         raise Exception(f"Action name {action_name} not found to belong to a func mapping")
    #     self.logger.info(f"acc name {str(j_feature)}")
    #     subtreeFeatures = getSubtreeFeatures(self.featureModel.getFeature(j_feature.getName()))
    #     slicedModel = LongRunningWrapper.runMethod(SliceFeatureModel(self.featureModel,
    #                                                                  subtreeFeatures, True))
    #     slicedFormula = FeatureModelFormula(slicedModel)
    #     subconf = Configuration(self.fmConfiguration, slicedFormula)

    #     return slicedFormula, subconf

    # def get_fetch_policy(self, action_name: str):
    #     table = {}
    #     reconfigurations = []
    #     state_dict = {}

    #     slicedFormula, subconf = self._find_subconfiguration(action_name)
    #     undef_subconf = Configuration(slicedFormula)

    #     # p_available_alts = []
    #     configurationAnalyzer = ConfigurationAnalyzer(slicedFormula, undef_subconf)
    #     allConfigurations = configurationAnalyzer.getSolutions(100000)
    #     all_configurations = []
    #     for k, featureList in enumerate(allConfigurations):
    #         all_configurations.append(sorted({str(feature) for feature in featureList
    #                                   if str(feature) != "__root__"}))
    #         reconfigurations.append(str(sorted({str(feature) for feature in featureList
    #                                     if str(feature) != "__root__"})))

    #     self.action_allconf[action_name] = all_configurations
    #     self.action_currconf[action_name] = sorted({str(feat)
    #                                                 for feat in subconf.getSelectedFeatureNames()})

    #     self.logger.info(f"all configurations {str(all_configurations)}")

        # TODO: ensure alternative is mandatory.
        # self._subtree_features(j_feature, p_available_alts, partial(instanceis, Alternative))
        # available_alts_feats = []
        # for feat in p_available_alts:
        #   available_alts_feats.extend(feat.getChildren())
        # available_opts_feats = []
        # self._subtree_features(j_feature, available_opts_feats, self._isOptional)

        # for i, j_state in enumerate(self.j_states_map.get(action_name)):
        for i, j_state in enumerate(self.j_states):
            state_name = str(j_state.name())
            state_dict[state_name] = []
            if (int(j_state.associatedRules.size()) > 0):
                state_dict[state_name] = [str(rule.getName()) for rule in j_state.associatedRules]
            for rule in j_state.associatedRules:
                selected_by, deselected_by = self._featuresInvolvedInRule(rule)

                for selected_feature in selected_by:
                    for conf in all_configurations:

                        if str(selected_feature.getName()) in conf:
                            table[(str(conf), state_name)] = str(rule.getName())
                for deselected_feature in deselected_by:
                    for conf in all_configurations:
                        if not (str(deselected_feature.getName()) in conf):
                            table[(str(conf), state_name)] = str(rule.getName())
                # for alt in available_alts_feats:
                #     sel_feat = 'select_' + str(alt.getName())

                #     if (alt in selected_by):
                #         reconfigurations.append(sel_feat)
                #         table[(sel_feat, state_name)] = rule.getName()
                #     # It is not allowed to deselect a mandatory alt.
                # for opt in available_opts_feats:
                #     sel_feat = 'select_' + str(opt.getName())
                #     desel_feat = 'deselect_' + str(opt.getName())

                #     if (opt in selected_by):
                #         reconfigurations.append(sel_feat)
                #         table[(sel_feat, state_name)] = str(rule.getName())
                #     if (opt in deselected_by):
                #         reconfigurations.append(desel_feat)
                #         table[(desel_feat, state_name)] = str(rule.rule.getName())

        self.logger.info(f"table {str(table)}")

        return state_dict, table, reconfigurations

    # def get_reconfiguration_plan(self, tactic_rule: str) -> AdaptationPlan:
    #     query_result = self.fetch_reconfiguration_plan(tactic_rule)
    #     return AdaptationPlan.from_typedb_results(query_result)

    def configuration_delta(self, current_configuration, configuration):
        deselection_set = current_configuration - configuration
        selection_set = configuration - current_configuration
        reconfigurations = []
        for feat in deselection_set:
            desels = self.resolver.deselectionActions(feat)
            if (not desels.isEmpty()):
                reconfigurations.extend(list(desels))

        for feat in selection_set:
            sels = self.resolver.selectionActions(feat)
            if (not sels.isEmpty()):
                reconfigurations.extend(list(sels))

        return [str(self.namer.uniqueName(reconf)) for reconf in reconfigurations]

    def change_configuration(self, configuration_string: str) -> list[str]:
        configuration = set(eval(configuration_string))
        current_configuration = self._current_configuration()

        # self.action_currconf[action_name] = configuration

        reconfigurations = self.configuration_delta(set(current_configuration), configuration)

        return reconfigurations

    def _process_selection(self, reconfigurations):
        for reconf in reconfigurations:
            if "DESEL_" in reconf:
                self.fmConfiguration.setManual(reconf[6:], Selection.UNSELECTED)
            elif "SEL_" in reconf:
                self.fmConfiguration.setManual(reconf[4:], Selection.SELECTED)

    def reconfiguration(self, reconfigurations: list[str]) -> list[str]:
        initial_conf = self._current_configuration()
        self.fmConfiguration.resetAutomaticValues()
        self.logger.info(f"initialConf ? {str(initial_conf)}")
        self._process_selection(reconfigurations)
        LongRunningWrapper.runMethod(self.configurationPropagator.resolve())
        self._process_selection(reconfigurations)
        LongRunningWrapper.runMethod(self.configurationPropagator.resolve())
        LongRunningWrapper.runMethod(self.configurationPropagator.update())
        if (not bool(LongRunningWrapper.runMethod(self.configurationPropagator.isValid()))):
            raise Exception("Invalid Configuration after reconfiguration!")

        configuration = self._current_configuration()

        self.logger.info(f"postConf ? {str(configuration)}")
        # self.action_currconf[action_name] = configuration
        return self.configuration_delta(set(initial_conf), set(configuration))

    # TODO: use dict?
    def lifecycleStateToTransition(self, j_lc_state: LifecycleState):
        if (j_lc_state == LifecycleState.UNCONFIGURED):
            return Transition(id=Transition.TRANSITION_CLEANUP),
        if (j_lc_state == LifecycleState.INACTIVE):
            return Transition(id=Transition.TRANSITION_DEACTIVATE),
        if (j_lc_state == LifecycleState.ACTIVE):
            return Transition(id=Transition.TRANSITION_ACTIVATE)
        if (j_lc_state == LifecycleState.FINALIZED):
            return Transition(id=Transition.TRANSITION_ACTIVE_SHUTDOWN)

    def paramToRosParameterMsg(self, j_param, j_param_value):
        param_name = str(j_param.getName())
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
            for sel_ac in j_resolution.getSelection_actions():
                reconf_name = str(self.namer.uniqueName(sel_ac))
                resolution_to_adaptations[reconf_name] = [self.reconfigurationToAdaptation(sel_ac)]
            for desel_ac in j_resolution.getDeselection_actions():
                rec_name = str(self.namer.uniqueName(desel_ac))
                resolution_to_adaptations[rec_name] = [self.reconfigurationToAdaptation(desel_ac)]

        return resolution_to_adaptations

    def eval_bound(self, value, j_bound_pair):
        if (value is None):
            return False
        lower_bound = _value_from_lit(j_bound_pair.getKey())
        upper_bound = _value_from_lit(j_bound_pair.getValue())

        low_bound_eval = True

        if (lower_bound is not None):
            low_bound_eval = value >= lower_bound

        up_bound_eval = True

        if (upper_bound is not None):
            up_bound_eval = value < upper_bound

        return (low_bound_eval and up_bound_eval)

    def eval_bool_condition(self, value, j_bool_value):
        if (value is None):
            return False
        bool_value = bool(j_bool_value)

        return value == bool_value

    def get_current_state_action(self, action_name, logger):
        # logger.info("Fetching state internal")
        # j_states = self.j_states_map[action_name]
        j_states = self.j_states
        measures: dict = self.latest_measures
        states = []
        # TODO: can be optimized to end as soon as any state is found.
        for i, j_state in enumerate(j_states):
            checks = []
            while (all(checks)):
                for j_entry in j_state.getContextBoundPairs():
                    value = measures.get(j_entry.getKey().getName(), None)
                    j_bound_pair = j_entry.getValue()
                    checks.append(self.eval_bound(value, j_bound_pair))
                for j_entry in j_state.getContextBoolConditions():
                    value = measures.get(j_entry.getKey().getName(), None)
                    j_bool_val = j_entry.getValue()
                    checks.append(self.eval_bool_condition(value, j_bool_val))

                if (all(checks)):
                    states.append(str(j_state.name()))
                    break
        # logger.info(f"states {states}")
        if (len(states) > 1):
            raise Exception("More than one current state")
        elif (len(states) == 1):
            return states[0]
        return None
