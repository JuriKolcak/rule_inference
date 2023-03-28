import json

from docplex.mp.dvar import Var
from docplex.mp.model import Model
from docplex.mp.solution import SolveSolution
from GTRI.canonicalisation import GraphCanonicaliser
from GTRI.iterated_map import IteratedMap
from GTRI.rule_graph import RuleGraph
from GTRI.rule_lattice import build_minimal_rule_lattice, CandidateRule, RuleLattice
from GTRI.transition import Transition
from typing import Dict, Iterable, List, Optional


def model_from_iterated_map(iterated_map: IteratedMap, spurious_scalar: float) -> 'ILPModel':
    global_rule_lattice: Optional[RuleLattice] = None

    for index, (minimal_rule, transitions) in enumerate(iterated_map.minimal_rules.items()):
        print(f'\tminimal rule \"{minimal_rule.name}\" ({index + 1}/{iterated_map.number_of_minimal_rules}) '
              f'with {minimal_rule.rule.number_of_vertices} vertices and {minimal_rule.rule.number_of_edges} edges.')
        print(f'\t- derived from {len(transitions)} transitions)')
        print()

        print('\tEnumerating generated transitions...')
        generated_transitions: List[Transition] = list(iterated_map.enumerate_applications(minimal_rule.rule))

        reference_transitions: List[Transition] = []
        spurious_transitions: List[Transition] = []
        for transition in generated_transitions:
            if iterated_map.has_transition(transition):
                reference_transitions.append(transition)
            else:
                spurious_transitions.append(transition)

        print(f'\t\tFound {len(reference_transitions)} reference transitions.')
        print(f'\t\tfound {len(spurious_transitions)} spurious transitions.')
        print()

        print('\tComputing Candidate Rules...')
        single_rule_lattice: RuleLattice = build_minimal_rule_lattice(reference_transitions, spurious_transitions)

        print(f'\t\tFound {len(single_rule_lattice)} candidate rules.')
        print('\n\t---------------------------------\n')

        global_rule_lattice = single_rule_lattice.merge(global_rule_lattice)

    model = ILPModel.from_candidates(global_rule_lattice, spurious_scalar)

    return model


class ILPSolution:
    def __init__(self, solution: SolveSolution, rules: Dict[RuleGraph, List[Transition]],
                 spurious_transitions: Dict[Transition, List[RuleGraph]]):
        self._solution: SolveSolution = solution

        self._rules: Dict[RuleGraph, List[Transition]] = {
            rule: list(transitions) for rule, transitions in rules.items()}

        self._spurious_transitions: Dict[Transition, List[RuleGraph]] = {
            transition: list(rules) for transition, rules in spurious_transitions.items()}

    def print_information(self):
        print('Solution Summary')
        print(f' - objective value: {self._solution.objective_value}')
        print(f' - number of rules: {len(self._rules)}')
        print(f' - number of spurious transitions: {len(self._spurious_transitions)}')
        print()

        print('Solution Rules')
        for index, (rule, coverage) in enumerate(self._rules.items()):
            print(f'\trule {index} with {rule.rule.number_of_vertices} vertices and {rule.rule.number_of_edges} edges')
            print(f'\t - reference transitions: {len(coverage)}')
            print(f'\t - spurious transitions: '
                  f'{len([transition for transition, rules in self._spurious_transitions.items() if rule in rules])}')

    def save(self, file_name: str):
        data = {
                "rules": [
                    {
                        "gml": rule.rule.to_gml(),
                        "reference_transitions": [transition.name for transition in transitions],
                        "spurious_transitions": [transition.name for transition, rules
                                                 in self._spurious_transitions.items() if rule in rules]
                    }
                    for rule, transitions in self._rules.items()
                ],
                "spurious_transitions": {
                    transition.name: transition.maximal_subrule.rule.to_gml()
                    for transition in self._spurious_transitions
                }
            }

        with open(file_name, "w") as file:
            json.dump(data, file, indent=2)


class ILPModel:
    def __init__(self, candidate_rules: Iterable[RuleGraph], reference_transitions: Dict[Transition, List[RuleGraph]],
                 spurious_transitions: Dict[Transition, List[RuleGraph]], spurious_scalar: float):
        self._model: Model = Model("Rule Inference Model")

        self._spurious_scaling_factor: float = spurious_scalar

        self._reference_transitions: Dict[Transition, List[RuleGraph]] = reference_transitions
        self._spurious_transitions: Dict[Transition, List[RuleGraph]] = spurious_transitions

        self._candidate_rules: Dict[RuleGraph, Var] = {}
        self._candidate_variables: Dict[Var, RuleGraph] = {}

        for index, candidate_rule in enumerate(candidate_rules):
            candidate_variable: Var = self._model.binary_var(f"rule{index}")
            self._candidate_rules[candidate_rule] = candidate_variable
            self._candidate_variables[candidate_variable] = candidate_rule

        self._goal_variables: Dict[Var, Transition] = {}
        for index, transition in enumerate(self._reference_transitions):
            goal_variable: Var = self._model.binary_var(f"transition{index}")
            self._goal_variables[goal_variable] = transition

            self._model.add_constraint(goal_variable >= 1)

            generating_candidate_variables: List[Var] = [self._candidate_rules[candidate] for candidate
                                                         in self._reference_transitions[transition]]
            self._model.add_constraint(goal_variable == self._model.logical_or(*generating_candidate_variables))

        self._distortion_variables: Dict[Var, Transition] = {}
        for index, transition in enumerate(self._spurious_transitions):
            error_variable: Var = self._model.binary_var(f"error{index}")
            self._distortion_variables[error_variable] = transition

            for candidate_rule in self._spurious_transitions[transition]:
                self._model.add_constraint(error_variable >= self._candidate_rules[candidate_rule])

        rule_variable_sum = self._model.sum(list(self._candidate_variables))
        distortion_variable_sum = self._model.sum(list(self._distortion_variables))
        self._model.minimize(rule_variable_sum + self._spurious_scaling_factor * distortion_variable_sum)

    @staticmethod
    def from_candidates(candidates: Iterable[CandidateRule], spurious_scalar: float) -> 'ILPModel':
        reference_transitions: Dict[Transition, List[RuleGraph]] = {}
        spurious_transitions: Dict[Transition, List[RuleGraph]] = {}

        candidate_rules: List[RuleGraph] = []
        for candidate in candidates:
            candidate_rules.append(candidate.rule)

            for transition in candidate.coverage:
                if transition not in reference_transitions:
                    reference_transitions[transition] = []

                reference_transitions[transition].append(candidate.rule)

            for transition in candidate.distortion:
                if transition not in spurious_transitions:
                    spurious_transitions[transition] = []

                spurious_transitions[transition].append(candidate.rule)

        return ILPModel(candidate_rules, reference_transitions, spurious_transitions, spurious_scalar)

    def print_information(self):
        self._model.print_information()
        print(f' - number of candidate rules: {len(self._candidate_variables)}')
        print(f' - number of transitions to cover: {len(self._goal_variables)}')
        print(f' - number of spurious transitions: {len(self._distortion_variables)}')

    def solve(self) -> ILPSolution:
        solution: SolveSolution = self._model.solve()

        rules: Dict[RuleGraph, List[Transition]] = {}
        spurious_transition: Dict[Transition, List[RuleGraph]] = {}

        for variable in solution.iter_variables():
            if variable.solution_value < 1 or variable not in self._candidate_variables:
                continue

            rule = self._candidate_variables[variable]
            rules[rule] = [transition for transition in self._reference_transitions
                           if rule in self._reference_transitions[transition]]

            for transition, candidates in self._spurious_transitions.items():
                if rule not in candidates:
                    continue

                if transition not in spurious_transition:
                    spurious_transition[transition] = []

                spurious_transition[transition].append(rule)

        return ILPSolution(solution, rules, spurious_transition)

    @staticmethod
    def load(file_name: str, spurious_scalar: float, canonicaliser: GraphCanonicaliser) -> 'ILPModel':
        with open(file_name, "r") as file:
            data = json.load(file)

        indexed_candidate_rules: Dict[int, RuleGraph] = {
            int(index): RuleGraph.load(rule_graph_data, canonicaliser)
            for index, rule_graph_data in data["candidate_rules"].items()
        }

        return ILPModel(indexed_candidate_rules.values(),
                        {Transition.load(transition_data, canonicaliser): [indexed_candidate_rules[int(index)]
                                                                           for index in index_list]
                         for transition_data, index_list in data["reference_transitions"].items()},
                        {Transition.load(transition_data, canonicaliser): [indexed_candidate_rules[int(index)]
                                                                           for index in index_list]
                         for transition_data, index_list in data["spurious_transitions"].items()}, spurious_scalar)

    def save(self, file_name: str):
        candidate_rule_identifiers: Dict[RuleGraph, int] = {
            candidate_rule: index for index, candidate_rule in enumerate(self._candidate_rules)
        }

        data = {
            "candidate_rules": {
                index: candidate_rule.save() for candidate_rule, index in candidate_rule_identifiers.items()
            },
            "reference_transitions": {
                transition.save(): [candidate_rule_identifiers[rule] for rule in rules]
                for transition, rules in self._reference_transitions.items()
            },
            "spurious_transitions": {
                transition.save(): [candidate_rule_identifiers[rule] for rule in rules]
                for transition, rules in self._spurious_transitions.items()
            }
        }

        with open(file_name, "w") as file:
            json.dump(data, file, indent=2)
