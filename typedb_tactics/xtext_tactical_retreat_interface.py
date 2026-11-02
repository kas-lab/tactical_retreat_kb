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
from system import RosPublisherReference, System, RosNode
from ros import PackageSet, ActionSpec
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
from org.eclipse.emf.ecore.util import EcoreUtil
from org.eclipse.xtext.serializer import ISerializer
from eu.coresense.common import NameProvider
from eu.coresense.context.generator import ContextNameProvider
from eu.coresense.resolution.generator import ResolutionNameProvider
# from eu.coresense.adaptation.generator import TacticsNameProvider
from eu.coresense.common import RosNameProvider, MathOperator, Literal, IntLiteral, DecimalLiteral
from eu.coresense.common import StringLiteral, BooleanLiteral, Utilities

from eu.coresense.adaptation.tactics import TacticsModel, ActionTactics, PureTactic
from eu.coresense.adaptation.tactics import ContextThresholdCondition, LogicalOperator, ContextContextCondition
from eu.coresense.adaptation.tactics import SelectVariant, DeselectVariant
from eu.coresense.adaptation.tactics import TacticsFactory
from eu.coresense.requirements.generator import RequirementsModelGenerator
from eu.coresense.requirements.requirementsModel import RequirementsModel, AsCloseLit, Shall
from eu.coresense.requirements.requirementsModel import Negation, CompoundExpression, And, Or
from eu.coresense.requirements.requirementsModel import Quantifiable, AsAsPossible
from eu.coresense.requirements.requirementsModel import FuzzyTriangular as J_FuzzyTriangular
from eu.coresense.requirements.requirementsModel import FuzzyRightShoulder as J_FuzzyRightShoulder
from eu.coresense.requirements.requirementsModel import FuzzyLeftShoulder as J_FuzzyLeftShoulder
from eu.coresense.requirements.requirementsModel import Proposition as J_Proposition



from eu.coresense.resolution.resolutionModel import ResolutionModel, Reconfiguration, SetParam
from eu.coresense.resolution.resolutionModel import SetLifecycle, LifecycleState
from eu.coresense.context.contextModel import ContextModel, QualifiedPublisherRef, QualifiedRef, CompositeRef
from eu.coresense.context.contextModel import QualifiedActionServerRef, QualifiedServiceServerRef
from uma.caosd.rhea.AdvancedConstraintsFMmetamodel import AdvancedConstraintsFMmetamodelPackage
from uma.caosd.rhea.BasicFMmetamodel import Feature, Alternative, OrGroup
from java.lang import String, Integer, Thread
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
# from eu.coresense.adaptation.generator import State, TQLGenerator


logger = logging.getLogger(__name__)


def instanceis(clas, obj):
    return isinstance(obj, clas)

def _sublist_instances(some_list, some_type):
    return [some_element for some_element in some_list if isinstance(some_element,some_type)]


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

def j_as_as_possible_equals(as_as_possible_one, as_as_possible_two):
    if(as_as_possible_one.getTimeFrequency().equals(as_as_possible_two.getTimeFrequency())):
        c_var_one = as_as_possible_one.getQuantity().getContextVariable()
        c_var_two = as_as_possible_two.getQuantity().getContextVariable()
        if(c_var_one.equals(c_var_two)):
            return True
    return False

def j_context_var_from_expression(j_expression):
    if isinstance(j_expression, AsAsPossible):
        return j_expression.getQuantity().getContextVariable()
    if isinstance(j_expression, AsCloseLit):
        return j_expression.getComparator().getContextVariable()
    if isinstance(j_expression,Quantifiable):
        return j_expression.getContextVariable()
    if isinstance(j_expression, J_Proposition):
        return j_expression.getCondition().getMeasurement()




def j_as_close_lit_equals(as_close_lit_one, as_close_lit_two):
    if _value_from_lit(as_close_lit_one.getQuantity()) == _value_from_lit(as_close_lit_two.getQuantity()):
        c_var_one = as_close_lit_one.getComparator().getContextVariable()
        c_var_two = as_close_lit_two.getComparator().getContextVariable()
        if c_var_one.equals(c_var_two):
            return True
    return False

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

        self.j_res_set = XtextResourceSet()
        # Callbacks run on JPype-attached threads whose context class loader is null,
        # so give the resource set an explicit one for classpath URI resolution.
        self.j_res_set.setClasspathURIContext(TacticsModel.class_.getClassLoader())
        self.logger = logger
        self.logger.info(f"{ros_path}")
        self.load_model("ros", RosStandaloneSetupGenerated(), ros_path)
        self.j_ros2_resources = self.load_model("ros2", Ros2StandaloneSetupGenerated(), ros2_path)
        self.j_rossystem_resources, _ = self.load_model("rossystem",
                                                        RosSystemStandaloneSetupGenerated(),
                                                        rossystem_path)
        j_fm_resources, _ = self.load_model("var", FeatureModelStandaloneSetupGenerated(), var_path)
        j_res_sources, _ = self.load_model("resolution", ResolutionModelStandaloneSetupGenerated(),
                                        resolution_path)
        j_context_resources, _ = self.load_model("context", ContextModelStandaloneSetupGenerated(),
                                              context_path)
        j_requirements_resources, _ = self.load_model("reqs",
                                                   RequirementsModelStandaloneSetupGenerated(),
                                                   reqs_path)
        j_tactics_resources, self.j_tactics_injector = self.load_model("tactics",
                                                                 TacticsStandaloneSetupGenerated(),
                                                                 tactics_path)

        self.j_tactics_model_resource = j_tactics_resources.get(0)
        self.j_tactics_model = (TacticsModel) @ self.j_tactics_model_resource.getContents().get(0)

        self.j_requirements_model_resource = j_requirements_resources.get(0)
        self.j_requirements_model = (RequirementsModel) @ \
            self.j_requirements_model_resource.getContents().get(0)

        self.j_context_model_resource = j_context_resources.get(0)
        self.j_context_model = (ContextModel) @ \
            self.j_context_model_resource.getContents().get(0)

        self.j_resolution_model_resource = j_res_sources.get(0)
        self.j_resolution_model = (ResolutionModel) @ \
            self.j_resolution_model_resource.getContents().get(0)

        self.resolver = Resolver(self.j_resolution_model)
        # TQLGenerator.setGlobalResource(self.j_tactics_model_resource)

        if hasattr(j_fm_resources, "get"):
            resource0 = j_fm_resources.get(0)
        else:
            resource0 = j_fm_resources[0]

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

        self.j_dsl_feature_model = root_obj

        # for j_action_rule in self.j_tactics_model.getActionTactics():
        #     self.j_states_map = TQLGenerator.createStates(self.j_tactics_model,
        #                                                   self.j_requirements_model,
        #                                                   consider_features_in_state)
        #     for key in self.j_states_map.keySet():
        #         self.logger.info(f"{str(key)} - \
        #                           {str(self.j_states_map.get(key).size())} states generated")
        # if (generate_state):
        #     self.j_states = TQLGenerator.createStates(self.j_context_model)

        #     self.logger.info(f"{str(self.j_states.size())} states generated")
        #     for j_state in self.j_states:
        #         self.logger.info(f"{str(State.render(j_state.precondition))} states generated")

        self.namer = NameProvider()
        self.namer.register(ResolutionNameProvider())

        LibraryManager.registerLibrary(FMCoreLibrary.getInstance())

        path = Files.createTempFile("featuremodel", ".xml")
        fw = FileWriter(path.toFile(), True)

        generator = FeatureModelGenerator()
        fm_xml = generator.generateXml(self.j_dsl_feature_model.getFm())
        fw.write(fm_xml)
        fw.close()

        conf_path = Files.createTempFile("configuration", ".xml")
        fw = FileWriter(conf_path.toFile(), True)

        conf_xml = generator.generateConfiguration(self.j_dsl_feature_model.getFm())

        fw.write(conf_xml)
        fw.close()
        self.featureModel = FeatureModelManager.load(path)

        formula = FeatureModelFormula(self.featureModel)
        self.j_fm_configuration = ConfigurationIO.getInstance().load(conf_path,
                                                                  FeatureModelManager
                                                                  .getInstance(path))
        self.logger.info(f"conf ? {str(self.j_fm_configuration.toString())}")
        # select_exclusive(configuration, formula, "MPPI", Selection.UNSELECTED, logger)
        # select_exclusive(configuration, formula, "RPP", Selection.SELECTED, logger)
        # propagator = ConfigurationPropagator(formula, self.j_fm_configuration)

        self.action_allconf = {}
        self.latest_measures = {"moving_backward" : False, "lastRearScan" : 10}
        self.in_effect_requirements = []
        self.traversed_requirements = {}

        for j_req in self.j_requirements_model.getRequirements():
            some_list = []
            self.traverseExpression(j_req.getExpression(), some_list)
            self.traversed_requirements[j_req] = some_list

        self.j_configuration_propagator = ConfigurationPropagator(formula, self.j_fm_configuration)

        # p = LongRunningWrapper.runMethod(propagator.coverFeatures(["MPPI_DIFF"], False))
        # self.logger.info(f"assertTrue ? {str(p)}")

        # self.logger.info(f"assertTrue ? {str(LongRunningWrapper.runMethod(propagator.isValid()))}")

        # self.logger.info(f"assertEquals Selection.UNDEFINED = {str(self.j_fm_configuration.getSelectableFeature("MPPI_OMNI").getManual())}")
        # self.logger.info(f"assertEquals Selection.SELECTED = {str(self.j_fm_configuration.getSelectableFeature("MPPI_DIFF").getManual())}")

        # self.to_xtext(first_state)
        # LongRunningWrapper.runMethod(propagator.update())

        # self.logger.info(f"conf aft ? {str(self.j_fm_configuration.getSelectedFeatureNames())}")

        # valid = LongRunningWrapper.runMethod(propagator.isValid())
        # if not valid:
        #     self.logger.warning("Update produced an invalid/contradictory configuration!")
        self.update_requirements_in_effect(requirement_names=[], all_requirements=True)
        self.logger.info("ready")

    def _retrieve_tactic_by_name(self, tactic_name):
        for j_rule in self.j_tactics_model.getTactics():
            if isinstance(j_rule, PureTactic):
                if str(j_rule.getName()) == tactic_name:
                    return j_rule
            elif isinstance(j_rule, ActionTactics):
                for j_pure_tactic in j_rule.getTactics():
                    if str(j_pure_tactic.getName()) == tactic_name:
                        return j_pure_tactic
        return None

    def _retrieve_action_by_name(self, action_name):
        j_package_set_list = Utilities.deriveFromImports(self.j_tactics_model_resource, ".ros", self.j_tactics_model.getImports(), PackageSet.class_)
        for j_package_set in j_package_set_list:
            for j_package in j_package_set.getPackage():
                for j_spec_base in j_package.getSpec():
                    if isinstance(j_spec_base, ActionSpec):
                        if str(j_spec_base.getName()) == action_name:
                            return j_spec_base

    def new_tactic(self, old_tactic, requirement, action):
        # Called from ROS callback threads, which JPype attaches with a null context
        # class loader; Xtext scoping needs one to resolve the imported models.
        Thread.currentThread().setContextClassLoader(TacticsModel.class_.getClassLoader())

        #Get the pure action from other tactic.
        j_action = self._retrieve_action_by_name(action)
        j_reused_rule = self._retrieve_tactic_by_name(old_tactic)
        self.logger.info(f"acc {str(j_action)} tac {str(j_reused_rule)}")

        j_pure_tactic = TacticsFactory.eINSTANCE.createPureTactic()
        j_pure_tactic.setName("PLACEHOLDER")
        self.logger.info(f"2 {str(EcoreUtil.copy(j_reused_rule.getAction()))}")

        # 'action' is a containment: copy it, otherwise it is moved out of the reused rule
        j_pure_tactic.setAction(EcoreUtil.copy(j_reused_rule.getAction()))

        self.logger.info(f"3 {str(j_pure_tactic)}")
        j_action_tactics = TacticsFactory.eINSTANCE.createActionTactics()
        j_action_tactics.setAction(j_action)
        j_action_tactics.getTactics().add(j_pure_tactic)

        self.j_tactics_model.getTactics().add(j_action_tactics)
        self.logger.info(f"4 {str(j_action_tactics)}")


        # injector = TacticsStandaloneSetupGenerated().createInjectorAndDoEMFRegistration()
        serializer = self.j_tactics_injector.getInstance(ISerializer.class_)

        # self.j_tactics_model_resource.getContents().add(j_tactics_model)
        dsl_text = serializer.serialize(j_action_tactics)

        self.logger.info(f"New Tactic Generated \n {str(dsl_text)}")
        # createActionTactics
        # createAdaptationRule
    

    def to_xtext(self, j_state):
        # TODO: needs to be updated to new TacticsModel changes.
        pass
        # TacticsFactory.eINSTANCE.createMeasurementCondition()
        # j_context_guard = TacticsFactory.eINSTANCE.createContextGuard()
        # j_context_guard.setContextCondition(j_state.precondition)
        # j_condition_action = TacticsFactory.eINSTANCE.createConditionAction()
        # j_atomic_rule = TacticsFactory.eINSTANCE.createAtomicRule()
        # j_condition_action.setContextGuard(j_context_guard)

        # res_model = TQLGenerator.getResolutionModel(self.j_tactics_model, self.j_tactics_model_resource).get(Integer @ 0)

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
        # j_action_rules = TacticsFactory.eINSTANCE.createActionTactics()
        # j_action_rules.getAdaptationRules().add(j_atomic_rule)

        # j_func_map = self.j_resolution_model.getFunctionalMapping().get(Integer @ 0)
        # j_action_rules.setAction(j_func_map.getAction())

        # self.j_tactics_model.getTactics().get(Integer @ 0).getAdaptationRules().add(j_atomic_rule)

        # # injector = TacticsStandaloneSetupGenerated().createInjectorAndDoEMFRegistration()
        # serializer = self.j_tactics_injector.getInstance(ISerializer.class_)

        # # self.j_tactics_model_resource.getContents().add(j_tactics_model)
        # dslText = serializer.serialize(self.j_tactics_model)

        # self.logger.info(f"dsltext {str(dslText)}")
        # # createActionTactics
        # # createAdaptationRule

    def to_fuzzy(self, j_expression_list: list) -> Optional[Expression]:
        j_expression = j_expression_list[0]
        if isinstance(j_expression, AsCloseLit):
            j_as_close_lit = (AsCloseLit) @ j_expression
            req_value = _value_from_lit(j_as_close_lit.getQuantity())
            j_fuzzy_tri = (J_FuzzyTriangular) @ j_as_close_lit.getMembershipFunction()

            prop = self.to_fuzzy([j_as_close_lit.getComparator()])
            if (prop is None):
                return None
            a = tofloat(j_fuzzy_tri.getA())
            b = tofloat(j_fuzzy_tri.getB())
            c = tofloat(j_fuzzy_tri.getC())
            fuzzy_tri = FuzzyTriangular(a=a, b=b, c=c)
            return AsCloseAsPossibleExpression(proposition=prop, fuzzy_set=fuzzy_tri,
                                               required_value=float(req_value))
        if isinstance(j_expression, AsAsPossible):
            j_as_as_possible = (AsAsPossible) @ j_expression

            j_memb_func = j_as_as_possible.getMembershipFunction()
            if (isinstance(j_memb_func, J_FuzzyRightShoulder)):
                j_fuzzy_rsh = (J_FuzzyRightShoulder) @ j_as_as_possible.getMembershipFunction()

                measure_name = str(j_as_as_possible.getQuantity().getContextVariable().getName())

                mes = self.latest_measures.get(measure_name, None)
                if (mes is None):
                    return None
                prop = Proposition(name=measure_name, value=mes)
                foot = tofloat(j_fuzzy_rsh.getFoot())
                shoulder = tofloat(j_fuzzy_rsh.getShoulder())
                # self.logger.info(f"measure_name {measure_name} foot {foot} shoulder {shoulder}")
                fuzzy_rsh = FuzzyRightShoulder(foot=foot, shoulder=shoulder)
                return AsManyAsPossibleExpression(proposition=prop, fuzzy_set=fuzzy_rsh)
            if (isinstance(j_memb_func, J_FuzzyLeftShoulder)):
                j_fuzzy_lsh = (J_FuzzyLeftShoulder) @ j_as_as_possible.getMembershipFunction()

                measure_name = str(j_as_as_possible.getQuantity().getContextVariable().getName())

                mes = self.latest_measures.get(measure_name, None)
                if (mes is None):
                    return None
                prop = Proposition(name=measure_name, value=mes)
                foot = tofloat(j_fuzzy_lsh.getFoot())
                shoulder = tofloat(j_fuzzy_lsh.getShoulder())
                # self.logger.info(f"measure_name {measure_name} foot {foot} shoulder {shoulder}")
                fuzzy_lsh = FuzzyLeftShoulder(foot=foot, shoulder=shoulder)
                return AsManyAsPossibleExpression(proposition=prop, fuzzy_set=fuzzy_lsh)
        if isinstance(j_expression, CompoundExpression):
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
                fuzzy_child = self.to_fuzzy(j_expression_list[1:4])

            else:
                fuzzy_child = self.to_fuzzy([child])

            if (fuzzy_child is not None):
                return FuzzyNot(fuzzy_child)
            else:
                return None
            # TODO: the below... is
            # if(isinstance(j_as_as_possible.getTimeFrequency(), ))

        if isinstance(j_expression, J_Proposition):
            j_condition = j_expression.getCondition()
            
            measure_name = str(j_condition.getMeasurement().getName())
            context_val = self.latest_measures.get(measure_name, None)
            j_operator = j_condition.getOperator()
            comparator = _value_from_lit(j_condition.getValue())
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

            return Proposition(value=res)
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
            self.j_res_set,
            ext,
            path,
        )

        self.progress_message(f"Loaded {int(loadresult.resources.size())}.{ext} files")
        return loadresult.resources, loadresult.injector

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

                return (res and self._eval_feature_condition(j_second_term, configuration))
            if (j_log_op == LogicalOperator.OR):
                self.logger.info("OR")

                return (res or self._eval_feature_condition(j_second_term, configuration))

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
        if (isinstance(j_measurement_condition, ContextThresholdCondition)):
            j_threshold = ((ContextThresholdCondition)
                           @ j_measurement_condition).getThresholdValue()
            comparator = _value_from_lit(j_threshold)

        if(isinstance(j_measurement_condition,ContextContextCondition)):
            raise NotImplementedError

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
        return [str(f) for f in self.j_fm_configuration.getSelectedFeatureNames()]

    def _latest_measurements(self):
        return self.latest_measures

    def _adaptation_rule_satisfied(self, j_adaptation_rule: PureTactic,
                                   tactic_names):
        measures = self.latest_measures
        current_configuration = set(self._current_configuration())
        self.logger.info(f"current_configuration {str(current_configuration)}")
        # TODO: invert this, we should grab for the rules requested, not eliminate from all
        if str(j_adaptation_rule.getName()) in tactic_names:
            j_guard = j_adaptation_rule.getGuard()
            if (j_guard is not None):
                feature_guard = True
                condition_guard = True
                if (j_guard.getFeatureGuard() is not None):
                    j_feature_condition = j_guard.getFeatureGuard() \
                        .getFeatureCondition()
                    feature_guard = self._eval_feature_condition(j_feature_condition,
                                                                 current_configuration)
                if (j_guard.getContextGuard() is not None):
                    j_measurement_cond = j_guard.getContextGuard() \
                        .getContextCondition()
                    condition_guard = self._eval_measurement_condition(j_measurement_cond,
                                                                       measures)
                return feature_guard and condition_guard
            else:
                return True
                # self.logger.info(f"feat guard {feature_guard} condition_guard {condition_guard}")

    def _get_satisfied_action_tactics(self, tactic_names, action_name):
        satisfied = []

        for j_rule in self.j_tactics_model.getTactics():
            if (isinstance(j_rule, ActionTactics)):
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

        for j_rule in self.j_tactics_model.getTactics():
            if isinstance(j_rule, PureTactic):
                j_adaptation_rule = j_rule
                sat = self._adaptation_rule_satisfied(j_adaptation_rule, tactic_names)
                if sat is not None:
                    satisfied.append(sat)
                else:
                    self.logger.info(f"sat was none for {str(j_adaptation_rule.getName())}")

        return satisfied

    def get_valid_tactics(
            self,
            tactic_names: List[str],
            action_name) -> List[bool]:
        valid = []

        if(action_name != ""):
            valid = self._get_satisfied_action_tactics(tactic_names, action_name)
        else:
            valid = self._get_satisfied_global_tactics(tactic_names)

        self.logger.info(f"valid {tactic_names} {str(valid)}")

        return valid


    def _tactics_without_requirements(self, action_name):
        # Tactics for an action without a requirement associated.
        tactics = []
        for j_rule in self.j_tactics_model.getTactics():
            j_requirement = j_rule.getRequirement()

            if (j_requirement is None) and isinstance(j_rule, ActionTactics):

                j_action_rule = j_rule

                if action_name == str(j_action_rule.getAction().getName()):
                    tactics.append(j_action_rule)
        return tactics


    def _ranked_tactics(self, action_name):
        reqs = self._potentially_violated_requirements(action_name)
        ranked_tactics = {}
        for req in reqs:
            req_name = str(req.getName())
            tactics = self._tactics_for_requirement(req_name)
            most_similar_tacs = sorted(tactics,
                                key=self._tactic_distance)
            ranked_tactics[req_name] = most_similar_tacs

        without_req = self._tactics_without_requirements(action_name)

        most_similar_reqless = sorted(without_req,
                                key=self._tactic_distance)
        ranked_tactics["none"] = most_similar_reqless

        return ranked_tactics


    def get_valid_ranked_tactics(
            self,
            tactic_names: List[str],
            action_name) -> tuple[List[bool],dict]:
        satisfied = []

        if(action_name != ""):
            satisfied = self._get_satisfied_action_tactics(tactic_names, action_name)
        else:
            satisfied = self._get_satisfied_global_tactics(tactic_names)

        self.logger.info(f"satisfied {tactic_names} {str(satisfied)}")

        ranked_tactics = self._ranked_tactics(action_name)

        return satisfied, ranked_tactics

    def traverseExpression(self, j_expression, j_expression_list: list):
        # self.logger.info(f"expr {j_expression}")
        if isinstance(j_expression, AsCloseLit):
            j_expression_list.append(j_expression)
            return
        if isinstance(j_expression, AsAsPossible):
            j_expression_list.append(j_expression)
            return
        if isinstance(j_expression, CompoundExpression):
            j_compound = j_expression
            j_left_expr = j_compound.getLeftExpression()
            j_right_expr = j_compound.getRightExpression()

            j_expression_list.append(j_compound)
            self.traverseExpression(j_left_expr, j_expression_list)
            self.traverseExpression(j_right_expr, j_expression_list)
            return
        if isinstance(j_expression, Shall):
            # self.logger.info("s")
            # j_shall = (Shall) @ j_expression
            j_expression_list.append(j_expression)
            self.traverseExpression(j_expression.getExpression(), j_expression_list)
            return
        if isinstance(j_expression, Negation):
            # j_neg = (Negation) @ j_expression
            j_expression_list.append(j_expression)
            self.traverseExpression(j_expression.getExpression(), j_expression_list)
            return
        if isinstance(j_expression, Quantifiable):
            j_expression_list.append(j_expression)
            return
        if isinstance(j_expression, J_Proposition):
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

    def update_param_value(self, node_name, param_name, param_value):
        j_ros_node = RosToolingSupport.nodeInRosSystems(String @ node_name,
                                                        self.j_rossystem_resources)
        if j_ros_node is None:
            self.logger.info(f"ParamEvent affected node {node_name} not found in ROS2 model.")
            return

        j_node = j_ros_node.getFrom()
        j_parameter = RosToolingSupport.findParameter(j_node, param_name)
        j_ros_parameter = RosToolingSupport.findRosParameter(j_ros_node, param_name)

        in_ros = j_parameter is not None
        in_ros_sys = j_ros_parameter is not None
        j_param_value = RosToolingSupport.convertParameterValue(param_value)
        if((not in_ros) and in_ros_sys):
            raise RuntimeError("Very strange, a parameter was found in the rossystem but not in the ros files which should not be possible")

        if in_ros_sys:
            # It already has an override, so just update that.
            RosToolingSupport.updateRosParameter(j_ros_parameter, j_param_value)
        elif in_ros:
            # Not in the rossystem, so we add it there.
            RosToolingSupport.newRosParameter(j_ros_node, j_parameter, j_param_value)
        else:
            RosToolingSupport.newParameter(j_node, j_param_value)

    def update_requirements_in_effect(self, requirement_names, all_requirements):
        if (all_requirements):
            self.in_effect_requirements = [j_req
                                           for j_req in self.j_requirements_model.getRequirements()]
        else:
            self.in_effect_requirements = []
            for req_name in requirement_names:
                for j_req in self.j_requirements_model.getRequirements():
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

        for j_context_var in self.j_context_model.getEnvironmental_variables():
            result_dict = {}
            result_dict['measure_name'] = str(j_context_var.getName())
            j_reference = j_context_var.getSource().getRef()
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
                    result_dict["service_request_kwargs"] = str(j_context_var.getKwargs())
            elif (isinstance(j_reference, CompositeRef)):
                j_composite_ref = (CompositeRef) @ j_reference
                result_dict['source'] = "Composite"
                result_dict['measure_names'] = [str(j_ctxtVar.getName())
                                                for j_ctxtVar in j_composite_ref.getContextVars()]

            result_dict["measurement_function_name"] = str(j_context_var.getFunctionName())

            lib = j_context_var.getFunctionLibrary()
            if (lib is not None):
                result_dict["measurement_function_lib"] = str(lib)

            args = j_context_var.getFunctionArgs()

            if (args is not None):
                result_dict["measurement_function_args"] = str(args)

            proxy = bool(j_context_var.getDoProxy())

            if (proxy is not False):
                result_dict["measurement_proxy"] = True

            period = int(j_context_var.getPeriod())
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

        for j_rule in self.j_tactics_model.getTactics():
            j_requirement = j_rule.getRequirement()
            req_name = "None"
            if (j_requirement is not None):
                req_name = j_requirement.getName()

            if (isinstance(j_rule, ActionTactics)):
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

        for j_rule in self.j_tactics_model.getTactics():
            j_requirement = j_rule.getRequirement()
            req_name = "None"
            if (j_requirement is not None):
                req_name = j_requirement.getName()

            if (isinstance(j_rule, PureTactic)):
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
                all_selected_features = set(sorted({str(feat) for feat in self.j_fm_configuration.getSelectedFeatureNames()}))
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
        j_func_maps = self.j_resolution_model.getFunctionalMapping()
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


    def _tactics_for_requirement(self, requirement_name : str) -> List:
        tactics = []
        for j_rule in self.j_tactics_model.getTactics():
            j_requirement = j_rule.getRequirement()

            if (j_requirement is not None):
                if requirement_name == str(j_requirement.getName()):
                    if (isinstance(j_rule, ActionTactics)):
                        j_action_rule = j_rule
                        tactics.extend(j_action_rule.getAdaptationRules())
                    else:
                        tactics.append(j_rule)
        return tactics

    def _distance_between_measure_and_condition(self, j_measurement_condition, measures) -> float:
        j_context_var = j_measurement_condition.getMeasurement()
        current_value = measures[str(j_context_var.getName())]
        distance = 0.0
        if(isinstance(j_measurement_condition, ContextThresholdCondition)):
            j_threshold = ((ContextThresholdCondition)
                            @ j_measurement_condition).getThresholdValue()
            comparator = _value_from_lit(j_threshold)
            j_operator = j_measurement_condition.getOperator()
            
            if (j_operator == MathOperator.LESS):
                if current_value >= comparator:
                    distance = current_value - comparator
                #distance is 0.0
            if (j_operator == MathOperator.GREATER):
                if current_value <= comparator:
                    distance = comparator - current_value
                #distance is 0.0
            if (j_operator == MathOperator.EQUAL):
                distance = abs(current_value - comparator)
            if (j_operator == MathOperator.DIFFERENT):
                if(current_value == comparator):
                    distance = 1.0 #actually it would be the smallest possible unit to make them different
            if (j_operator == MathOperator.GREQ):
                if current_value < comparator:
                    distance = comparator - current_value
            if (j_operator == MathOperator.LEQ):
                if current_value > comparator:
                    distance = current_value - comparator

            j_log_op = j_measurement_condition.getLogicalOp()
            j_second_term = j_measurement_condition.getSecondTerm()
            # self.logger.info(f"loggg op {str(j_log_op)}")
            # self.logger.info(f"loggg op {str(j_second_term)}")
    
            # j_log_op_val = j_log_op.getValue()
            if (j_log_op is not None) and (j_second_term is not None):
                if (j_log_op == LogicalOperator.AND):
                    self.logger.info("and")
    
                    return (distance + self._distance_between_measure_and_condition(j_second_term, measures))
                if (j_log_op == LogicalOperator.OR):
                    self.logger.info("OR")
    
                    return min(distance, self._distance_between_measure_and_condition(j_second_term, measures))
        if(isinstance(j_measurement_condition, ContextContextCondition)):
            # You would do something like, checking the distance to each context var and finding the min one to make the condition be met.
            raise NotImplementedError

        return distance
        
    def _distance_to_context_guard(self, j_context_guard):
        measures = self.latest_measures
        j_measurement_condition = j_context_guard.getContextCondition()
        return self._distance_between_measure_and_condition(j_measurement_condition, measures)

    def _create_reconfiguration(self, j_feature_condition):
        sel = "DESEL_" if str(j_feature_condition.getNot()) == "!" else "SEL_"
        feature_name = str(j_feature_condition.getVariant().getFeature().getName())
        return sel+feature_name

    def _distance_between_conf_and_condition(self, j_feature_condition):
        j_configuration_copy = Configuration(self.j_fm_configuration, FeatureModelFormula(self.featureModel))

        reconf_dict = self._some_other_function(j_feature_condition, {}, 0)

        deltas = []
        for reconf in reconf_dict.values():
            initial_conf = [str(f) for f in j_configuration_copy.getSelectedFeatureNames()]
            self.logger.info(f"preConffff ? {str(initial_conf)}")
            formula = FeatureModelFormula(self.featureModel)
            j_conf_prop = ConfigurationPropagator(formula, j_configuration_copy)
            self.logger.info(f"reconf ? {str(reconf)}")

            self._process_selection(reconf, j_configuration_copy)
            LongRunningWrapper.runMethod(j_conf_prop.resolve())
            self._process_selection(reconf, j_configuration_copy)
            LongRunningWrapper.runMethod(j_conf_prop.resolve())
            LongRunningWrapper.runMethod(j_conf_prop.update())
            if not bool(LongRunningWrapper.runMethod(j_conf_prop.isValid())):
                raise RuntimeError("Invalid Configuration after reconfiguration!")

            configuration = [str(f) for f in j_configuration_copy.getSelectedFeatureNames()]

            self.logger.info(f"postConffff ? {str(configuration)}")
            # self.action_currconf[action_name] = configuration
            delta =  self.configuration_delta(set(initial_conf), set(configuration))
            deselection_set = set(configuration) - set(initial_conf)
            selection_set = set(initial_conf) - set(configuration)
            delta = deselection_set.union(selection_set)
            deltas.append(len(delta))
            self.logger.info(f"deltur ? {str(delta)}")
        return min(deltas)




    def _some_other_function(self,j_feature_condition,
                             reconfigurations : dict, index : int):
        if index not in reconfigurations:
            reconfigurations[index] = [self._create_reconfiguration(j_feature_condition)]
        else:
            reconfigurations[index].append(self._create_reconfiguration(j_feature_condition))

        j_second_term = j_feature_condition.getSecondTerm()
        j_log_op = j_feature_condition.getLogicalOp()

        # While its an and add to the current computation, when it is an or split off.
        if (j_log_op is not None) and (j_second_term is not None):
            if j_log_op == LogicalOperator.AND:
                self._some_other_function(j_second_term,
                                        reconfigurations, index)
            if j_log_op == LogicalOperator.OR:
                self._some_other_function(j_second_term,
                                          reconfigurations, index+1)

        return reconfigurations

    def _tactic_distance(self, j_pure_tactic):
        j_guard = j_pure_tactic.getGuard()
        distance = 0.0

        if j_guard is not None:
            self.logger.info(f"uuh {j_pure_tactic.getName()} {str(j_guard.getContextGuard())}")
            if j_guard.getContextGuard() is not None:
                j_context_guard = j_guard.getContextGuard()
                context_dist = self._distance_to_context_guard(j_context_guard)
                distance += context_dist
            if j_guard.getFeatureGuard() is not None:
                j_feature_condition = j_guard.getFeatureGuard() \
                            .getFeatureCondition()
                conf_dist = self._distance_between_conf_and_condition(j_feature_condition)
                self.logger.info(f"conf dist {str(conf_dist)}")
                distance += conf_dist

        return distance

    def _potentially_violated_requirements(self, action_name):
        # Requirements which are referenced by a tactic
        potentially_violated_reqs = []
        for j_rule in self.j_tactics_model.getTactics():
            j_requirement = j_rule.getRequirement()

            if (j_requirement is not None) and isinstance(j_rule, ActionTactics):

                j_action_rule = j_rule

                if action_name == str(j_action_rule.getAction().getName()):
                    potentially_violated_reqs.append(j_requirement)
        return potentially_violated_reqs

    def similar_requirements(self, interface_name):
        """
        For every potentially violated requirement,
        the ordered list of other requirements by similarity to it.
        """

        # Gather the potentially violated, accounting for current action
        potentially_violated_reqs = self._potentially_violated_requirements(interface_name)

        #
        req_tac = {}
        self.logger.info(f"pot vi r {str(potentially_violated_reqs)}")

        for violated_requirement in potentially_violated_reqs:
            reqs = list(self.j_requirements_model.getRequirements())
            reqs.remove(violated_requirement)
            most_similar_reqs = sorted(reqs,
                                       key=partial(self._requirement_similarity,
                                                   violated_requirement), reverse=True)

            req_tac[str(violated_requirement.getName())] = [str(req.getName()) for req in most_similar_reqs]
        return req_tac
        # max(_requirement_similarity
        #Then the tactics of the closest requirements.

    def _find_req_by_name(self, req_name):
        for req in self.requirementsModel.getRequirements():
            if(str(req.getName()) == req_name):
                return req


    def _requirement_similarity(self, j_requirement_one, j_requirement_two):
        self.logger.info(f"1: {j_requirement_one.getName()} 2: {j_requirement_two.getName()} ")
        qa_similarity = int(j_requirement_one.getQa().equals(j_requirement_two.getQa()))

        i = self.traversed_requirements[j_requirement_one]
        j = self.traversed_requirements[j_requirement_two]

        i_context_vars = [j_context_var_from_expression(expr) for expr in i if j_context_var_from_expression(expr)]
        j_context_vars = [j_context_var_from_expression(expr) for expr in j if j_context_var_from_expression(expr)]

        self.logger.info(f"1: {str([str(cvar.getName()) for cvar in i_context_vars])} 2: {str([str(cvar.getName()) for cvar in j_context_vars])} ")
        

        i_as_as_list = _sublist_instances(i,AsAsPossible)
        j_as_as_list = _sublist_instances(j,AsAsPossible)

        expr_scores = []
        as_as_score = 0
        if len(i_as_as_list) > 0:
            for i_as_as in i_as_as_list:
                for j_as_as in j_as_as_list:
                    as_as_score += int(j_as_as_possible_equals(i_as_as,j_as_as))
            as_as_score = as_as_score / len(i_as_as_list)
            expr_scores.append(as_as_score)
        i_as_close_list = _sublist_instances(i,AsCloseLit)
        j_as_close_list = _sublist_instances(j,AsCloseLit)

        as_close_score = 0
        if len(i_as_close_list) > 0:
            for i_as_close in i_as_close_list:
                for j_as_close in j_as_close_list:
                    as_close_score += int(j_as_close_lit_equals(i_as_close,j_as_close))
            as_close_score = as_close_score / len(i_as_close_list)
            expr_scores.append(as_close_score)

        if(len(expr_scores) > 0):
            expr_similarity = sum(expr_scores)/ len(expr_scores)
        else:
            expr_similarity = 0.0
        # [expr in i]
        # self.logger.info(f"1: {str(i)} 2: {str(j)} ")
        # self.logger.info(f"equals: {str(i.equals(j))}")
        # self.logger.info(f"==: {str(i == j)}")

        # #AsAsPossible, AsCloseLit
        # expr_similarity = bool(i.equals(j))

        return qa_similarity + expr_similarity


    def nodesWith(self, getList, targetName):
        nodes = []
        for ros_node in self.allRossystemNodes(True):
            node = ros_node.getFrom()
            for item in getattr(node, getList)():
                if (item.getName().equals(targetName)):
                    nodes.append(node)
        
        return nodes

    def allRossystemNodes(self, skipSubnodes):
        rosNodesInRossystems = []

        for resource in self.rosSystemResources:
            sys = System @ resource.getContents().get(0)
            for component in sys.getComponents():
                if not isinstance(component, RosNode):
                    continue
                
                isSubnode = component.getParent() != None
                
                if(not skipSubnodes or not isSubnode):
                    rosNodesInRossystems.append(component)

        return rosNodesInRossystems

    def nodesWithActionClient(self, actionName):
        return self.nodesWith("getActionclient", actionName)


    def nodesWithActionServer(self, actionName):
        return self.nodesWith("getActionserver", actionName)


    def nodesWithServiceClient(self, serviceName):
        return self.nodesWith("getServiceclient", serviceName)


    def nodesWithServiceServer(self, serviceName):
        return self.nodesWith("getServiceserver", serviceName)


    def nodesWithPublisher(self, topicName):
        return self.nodesWith("getPublisher", topicName)


    def nodesWithSubscriber(self, topicName):
        return self.nodesWith("getSubscriber", topicName)



    def processExpansion(self):
        rosNodes = []
        for resource in self.rosSystemResources:
            sys = System @ resource.getContents().get(0)
        for process in sys.getProcesses():
            for component in process.getComponents():
                if (not isinstance(component, RosNode)):
                    continue
                rosNodes.append(component.getFrom())
					
        return rosNodes

    def allConnectedNodes(self, node):
        connectedNodes = set()

        connectedNodes.union(set(self.processExpansion()))


        # All the nodes with clients to my server
        for actionServer in node.getActionserver():
            connectedNodes.union(self.nodesWithActionClient(actionServer.getName()))  

        # for actionClient in node.getActionclient():
        #     connectedNodes.union(self.nodesWithActionServer(actionClient.getName()))

        # Collect all nodes from subscribers
        # for subscriber in node.getSubscriber():
            # connectedNodes.union(self.nodesWithPublisher(subscriber.getName()))

        # All the nodes subscribing to my publishers
        for  publisher in node.getPublisher():
            connectedNodes.union(self.nodesWithSubscriber(publisher.getName()))

        for serviceServer in node.getServiceserver():
            connectedNodes.union(self.nodesWithServiceClient(serviceServer.getName()))

        # for serviceClient in node.getServiceclient():
        #     connectedNodes.union(self.nodesWithServiceServer(serviceClient.getName())) 

        return connectedNodes


    def distance_nodes(self, node_a, node_b):
        pass


    def _featuresInvolvedInRule(self, rule):
        selected_by = []
        deselected_by = []
        j_pure_tactic = (PureTactic) @ rule
        j_tactic_action = j_pure_tactic.getAction()
        for j_simple_action in j_tactic_action.getActions():
            if isinstance(j_simple_action, DeselectVariant):
                deselected_by.append(j_simple_action.getVariant().getFeature())
            if isinstance(j_simple_action, SelectVariant):
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
    #     subconf = Configuration(self.j_fm_configuration, slicedFormula)

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
        # for i, j_state in enumerate(self.j_states):
        #     state_name = str(j_state.name())
        #     state_dict[state_name] = []
        #     if (int(j_state.associatedRules.size()) > 0):
        #         state_dict[state_name] = [str(rule.getName()) for rule in j_state.associatedRules]
        #     for rule in j_state.associatedRules:
        #         selected_by, deselected_by = self._featuresInvolvedInRule(rule)

        #         for selected_feature in selected_by:
        #             for conf in all_configurations:

        #                 if str(selected_feature.getName()) in conf:
        #                     table[(str(conf), state_name)] = str(rule.getName())
        #         for deselected_feature in deselected_by:
        #             for conf in all_configurations:
        #                 if not (str(deselected_feature.getName()) in conf):
        #                     table[(str(conf), state_name)] = str(rule.getName())
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

        # self.logger.info(f"table {str(table)}")

        # return state_dict, table, reconfigurations

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

    def _process_selection(self, reconfigurations, conf):
        for reconf in reconfigurations:
            if "DESEL_" in reconf:
                conf.setManual(reconf[6:], Selection.UNSELECTED)
            elif "SEL_" in reconf:
                conf.setManual(reconf[4:], Selection.SELECTED)

    def reconfiguration(self, reconfigurations: list[str]) -> list[str]:
        initial_conf = self._current_configuration()
        self.j_fm_configuration.resetAutomaticValues()
        self.logger.info(f"initialConf ? {str(initial_conf)}")
        self._process_selection(reconfigurations, self.j_fm_configuration)
        LongRunningWrapper.runMethod(self.j_configuration_propagator.resolve())
        self._process_selection(reconfigurations, self.j_fm_configuration)
        LongRunningWrapper.runMethod(self.j_configuration_propagator.resolve())
        LongRunningWrapper.runMethod(self.j_configuration_propagator.update())
        if (not bool(LongRunningWrapper.runMethod(self.j_configuration_propagator.isValid()))):
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
        for j_resolution in self.j_resolution_model.getResolutions():
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
