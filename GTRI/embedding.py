import mod

from GTRI.morphism import Morphism
from GTRI.rule_graph import is_relabeled, split_element_label, RuleGraph
from GTRI.transition import Transition
from itertools import chain
from typing import Dict, Iterable, Optional, Set, Tuple, Union


def _edge_to_hashable(edge: mod.Graph.Edge) -> Tuple[mod.Graph.Vertex]:
    return tuple(sorted([edge.source, edge.target]))


class Embedding:
    def __init__(self, pattern: RuleGraph, host_transition: Transition, morphism: Morphism):
        self._host_transition: Transition = host_transition

        self._pattern: RuleGraph = pattern

        self._morphism: Morphism = morphism

    def __eq__(self, other: 'Embedding') -> bool:
        return self._host_transition == other._host_transition and self._pattern == other._pattern \
            and self._morphism == other._morphism

    def __ne__(self, other: 'Embedding') -> bool:
        return not self == other

    def __hash__(self):
        return 23 * hash(self._host_transition) + 29 * hash(self._pattern) + 31 * hash(self._morphism)

    def __ge__(self, other: 'Embedding') -> bool:
        return not self < other

    def __gt__(self, other: 'Embedding') -> bool:
        return not self <= other

    def __le__(self, other: 'Embedding') -> bool:
        return self == other or self < other

    def __lt__(self, other: 'Embedding') -> bool:
        if self._host_transition > other._host_transition:
            return False
        elif self._host_transition < other._host_transition:
            return True

        if self._pattern > other._pattern:
            return False
        elif self._pattern < other._pattern:
            return True

        return self._morphism < other._morphism

    @property
    def host_transition(self) -> Transition:
        return self._host_transition

    @property
    def pattern(self) -> RuleGraph:
        return self._pattern

    def _pattern_edge_to_host(self, edge: mod.Graph.Edge) -> mod.Graph.Edge:
        return self.host_transition.maximal_subrule.get_edge(self._morphism[edge.source], self._morphism[edge.target])

    def _edge_additions(self) -> Iterable[Tuple[RuleGraph, Morphism]]:
        for pattern_vertex in self.pattern.graph.vertices:
            existing_edges: Set[Tuple[mod.Graph.Vertex]] = set(
                _edge_to_hashable(self._pattern_edge_to_host(pattern_edge))
                for pattern_edge in self.pattern.get_adjacent_edges(pattern_vertex))

            for host_edge in self.host_transition.maximal_subrule.get_adjacent_edges(self._morphism[pattern_vertex]):
                if _edge_to_hashable(host_edge) in existing_edges:
                    continue

                other_endpoint: mod.Graph.Vertex = host_edge.target \
                    if host_edge.source == self._morphism[pattern_vertex] \
                    else host_edge.source

                other_endpoint_range: Optional[mod.Graph.Vertex] = None
                for range_vertex, image_vertex in self._morphism.items():
                    if image_vertex == other_endpoint:
                        other_endpoint_range = range_vertex
                        break

                addition_pattern, addition_morphism = self.pattern.add_edge(pattern_vertex, other_endpoint_range)

                vertex_map: Dict[mod.Graph.Vertex, mod.Graph.Vertex] = {
                    range_vertex: image_vertex for range_vertex, image_vertex
                    in (addition_morphism + self._morphism).items()
                }
                if not other_endpoint_range:
                    vertex_map[addition_pattern.get_vertex(self.pattern.graph.number_of_vertices)] = other_endpoint

                yield addition_pattern, Morphism(vertex_map)

    def _label_specifications(self) -> Iterable[Tuple[RuleGraph, Morphism]]:
        for pattern_element in self.pattern.abstract_elements:
            host_element: Union[mod.Graph.Vertex, mod.Graph.Edge]
            if type(pattern_element) is mod.Graph.Vertex:
                host_element = self._morphism[pattern_element]
            else:
                host_element = self._pattern_edge_to_host(pattern_element)

            relabel_pattern: Optional[RuleGraph] = None
            relabel_morphism: Optional[Morphism] = None

            if is_relabeled(pattern_element):
                left_pattern_label, right_pattern_label = split_element_label(pattern_element)
                left_host_label, right_host_label = split_element_label(host_element)

                if left_pattern_label and left_pattern_label == "*":
                    relabel_pattern, relabel_morphism = self.pattern.relabel_element_left(pattern_element,
                                                                                          left_host_label)
                elif right_pattern_label and right_pattern_label == "*":
                    relabel_pattern, relabel_morphism = self.pattern.relabel_element_right(pattern_element,
                                                                                           right_host_label)
            else:
                relabel_pattern, relabel_morphism = self.pattern.relabel_element(pattern_element,
                                                                                 host_element.stringLabel)

            yield relabel_pattern, relabel_morphism + self._morphism

    def _build_embeddings(self, extension_generator: Iterable[Tuple[RuleGraph, Morphism]]) -> Iterable['Embedding']:
        patterns: Dict[RuleGraph, Set[Morphism]] = {}

        for pattern, pattern_morphism in extension_generator:
            if pattern in patterns:
                original_pattern = next(other_pattern for other_pattern in patterns if other_pattern == pattern)
                patterns[pattern].update(
                    isomorphism + pattern_morphism for isomorphism in pattern.isomorphisms(original_pattern)
                )
            else:
                patterns[pattern] = {pattern_morphism}

        for pattern, morphisms in patterns.items():
            for morphism in morphisms:
                yield Embedding(pattern, self._host_transition, morphism)

    def extensions(self) -> Iterable['Embedding']:
        extension_generator: Iterable[Tuple[RuleGraph, Morphism]] = self._label_specifications()

        if self.pattern.graph.number_of_edges < self.host_transition.maximal_subrule.graph.number_of_edges:
            extension_generator = chain(extension_generator, self._edge_additions())

        yield from self._build_embeddings(extension_generator)
