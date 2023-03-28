from GTRI.embedding import Embedding
from GTRI.rule_graph import RuleGraph
from GTRI.transition import Transition
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple


def build_minimal_rule_lattice(reference_transitions: Iterable[Transition],
                               spurious_transitions: Iterable[Transition]) -> 'RuleLattice':
    minimal_rule_embeddings: List[Embedding] = []
    for transition in reference_transitions:
        minimal_rule_embeddings.append(Embedding(
            transition.minimal_subrule, transition, transition.minimal_subrule_anchor
        ))

    root: LatticeNode = LatticeNode(minimal_rule_embeddings).get_maximum_common_subrule()
    rule_lattice: RuleLattice = RuleLattice(root, (transition for transition in spurious_transitions
                                                   if transition.can_embed(root.pattern)))

    while rule_lattice.active_node:
        rule_lattice.resolve_node()

    print()
    print()

    return rule_lattice


class LatticeNode:
    def __init__(self, embeddings: Iterable[Embedding]):
        self._embeddings: List[Embedding] = list(embeddings)

        self._pattern: Optional[RuleGraph] = None
        patterns: Set[RuleGraph] = set(embedding.pattern for embedding in self._embeddings)
        if len(patterns) == 1:
            self._pattern = list(patterns)[0]

        self._coverage: Optional[Tuple[Transition]] = None

        self._successors: Optional[List['LatticeNode']] = None

    def __eq__(self, other: 'LatticeNode') -> bool:
        return self._pattern == other._pattern

    def __ne__(self, other: 'LatticeNode') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 37 * hash(self._pattern)

    @property
    def pattern(self) -> Optional[RuleGraph]:
        return self._pattern

    @property
    def host_transitions(self) -> Iterable[Transition]:
        return set(embedding.host_transition for embedding in self._embeddings)

    @property
    def coverage(self) -> Tuple[Transition]:
        if not self._coverage:
            self._coverage = tuple(sorted(self.host_transitions))

        return self._coverage

    def successors(self) -> Iterable['LatticeNode']:
        if not self.pattern:
            return

        if self._successors:
            yield from self._successors
            return

        extensions: Dict[RuleGraph, Set[Embedding]] = {}

        for index, embedding in enumerate(self._embeddings):
            print()

            embedding_extensions: List[Embedding] = list(embedding.extensions())

            print(f"\t\tSearching for maximal common subrule. "
                  f"Processing embedding {index + 1}/{len(self._embeddings)} "
                  f"with {len(embedding_extensions)} possible extensions...", end='\033[F')

            for extension in embedding_extensions:
                if extension.pattern not in extensions:
                    extensions[extension.pattern] = set()

                extensions[extension.pattern].add(extension)

        for extension, embeddings in extensions.items():
            yield LatticeNode(embeddings)

    def get_maximum_common_subrule(self) -> 'LatticeNode':
        if self._successors:
            return self

        successors: List[LatticeNode] = []

        for child in self.successors():
            if child.coverage == self.coverage:
                return child.get_maximum_common_subrule()

            successors.append(child)

        self._successors = successors
        return self


class CandidateRule:
    def __init__(self, node: LatticeNode, distortion: Iterable[Transition]):
        self._coverage: List[Transition] = list(node.host_transitions)
        self._distortion: List[Transition] = list(distortion)
        self._rule: RuleGraph = node.pattern

    @property
    def coverage(self) -> Iterable[Transition]:
        return self._coverage

    @property
    def distortion(self) -> Iterable[Transition]:
        return self._distortion

    @property
    def rule(self) -> RuleGraph:
        return self._rule

    @property
    def amount_of_distortion(self) -> int:
        return len(self._distortion)


class RuleLattice:
    def __init__(self, root: LatticeNode, spurious_transitions: Iterable[Transition]):
        self._roots: List[LatticeNode] = [root]
        self._nodes: Dict[LatticeNode, Set[LatticeNode]] = {self._roots[0]: set()}

        self._candidates: Dict[LatticeNode, CandidateRule] = {
            self._roots[0]: CandidateRule(self._roots[0], spurious_transitions)
        }

        self._node_queue: List[LatticeNode] = []
        if self._candidates[self._roots[0]].amount_of_distortion > 0:
            self._node_queue.append(self._roots[0])

        self._seen_nodes: Set[LatticeNode] = {self._roots[0]}

    @property
    def queue_length(self) -> int:
        return len(self._node_queue)

    @property
    def active_node(self) -> Optional[LatticeNode]:
        if self.queue_length == 0:
            return None

        return self._node_queue[0]

    def _add_node(self, node: LatticeNode, parent: LatticeNode) -> Optional[LatticeNode]:
        if node in self._seen_nodes:
            return None
        self._seen_nodes.add(node)

        maximal_common_subrule: LatticeNode = node.get_maximum_common_subrule()

        if maximal_common_subrule in self._candidates:
            if maximal_common_subrule not in self._nodes[parent]:
                self._nodes[parent].add(maximal_common_subrule)

            return None

        self._nodes[parent].add(maximal_common_subrule)
        self._nodes[maximal_common_subrule] = set()

        self._candidates[maximal_common_subrule] = CandidateRule(
            maximal_common_subrule, (transition for transition in self._candidates[parent].distortion
                                     if transition.can_embed(maximal_common_subrule.pattern))
        )

        if self._candidates[maximal_common_subrule].amount_of_distortion > 0:
            self._node_queue.append(maximal_common_subrule)

        print(f'\t\tFound {len(self)} candidate rules with {self.queue_length} open...', end='\r')
        return maximal_common_subrule

    def resolve_node(self):
        active_node: LatticeNode = self.active_node
        self._node_queue = self._node_queue[1:]

        if not active_node:
            return

        for child in active_node.successors():
            self._add_node(child, active_node)

    def __iter__(self) -> Iterator[CandidateRule]:
        return iter(self._candidates.values())

    def __len__(self) -> int:
        return len(self._candidates)

    def merge(self, other: Optional['RuleLattice']) -> 'RuleLattice':
        result: RuleLattice = RuleLattice(self._roots[0], [])
        result._roots = list(self._roots)
        result._nodes = dict(self._nodes)
        result._candidates = dict(self._candidates)
        result._node_queue = list(self._node_queue)

        if other is not None:
            result._roots.extend(root for root in other._roots if root and root not in self._roots)

            for parent, children in other._nodes.items():
                if parent not in result._nodes:
                    result._nodes[parent] = set()

                result._nodes[parent].update(children)

            result._candidates.update({node: candidate for node, candidate in other._candidates.items()
                                       if node not in self._candidates})
            result._node_queue.extend(other._node_queue)

        return result
