import mod

from GTRI.canonicalisation import GraphCanonicaliser
from GTRI.morphism import Morphism
from GTRI.rule_graph import RuleGraph
from typing import Optional


class Transition:
    def __init__(self, rule_graph: RuleGraph):
        self._maximal_subrule: RuleGraph = rule_graph

        self._minimal_subrule: Optional[RuleGraph] = None
        self._minimal_subrule_anchor: Optional[Morphism] = None

    def __eq__(self, other: 'Transition') -> bool:
        return self._maximal_subrule == other._maximal_subrule

    def __ne__(self, other: 'Transition') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 17 * hash(self._maximal_subrule)

    def __ge__(self, other: 'Transition') -> bool:
        return not self < other

    def __gt__(self, other: 'Transition') -> bool:
        return not self <= other

    def __le__(self, other: 'Transition') -> bool:
        return self == other or self < other

    def __lt__(self, other: 'Transition') -> bool:
        return self._maximal_subrule < other._maximal_subrule

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self.maximal_subrule.name

    @property
    def maximal_subrule(self) -> RuleGraph:
        return self._maximal_subrule

    @property
    def minimal_subrule(self) -> RuleGraph:
        if self._minimal_subrule is None:
            self._minimal_subrule, self._minimal_subrule_anchor = self._maximal_subrule.get_minimal_subrule()

        return self._minimal_subrule

    @property
    def minimal_subrule_anchor(self) -> Morphism:
        if self._minimal_subrule_anchor is None:
            self._minimal_subrule, self._minimal_subrule_anchor = self._maximal_subrule.get_minimal_subrule()

        return self._minimal_subrule_anchor

    @staticmethod
    def load(data: str, canonicaliser: GraphCanonicaliser) -> 'Transition':
        return Transition(RuleGraph.from_rule(mod.ruleGMLString(data, add=False), canonicaliser))

    def can_embed(self, pattern: RuleGraph) -> bool:
        return any(self.maximal_subrule.embed(pattern))

    def save(self) -> str:
        return self.maximal_subrule.rule.to_gml()
