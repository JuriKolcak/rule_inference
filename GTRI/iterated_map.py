import mod

from GTRI.canonicalisation import CanonicalGraph, CanonicalRule, GraphCanonicaliser
from GTRI.rule_builder import RuleBuilder
from GTRI.rule_graph import RuleGraph
from GTRI.transition import Transition
from typing import Dict, Iterable, List, Optional, Set


specialisation_label_settings: mod.LabelSettings = mod.LabelSettings(mod.LabelType.Term,
                                                                     mod.LabelRelation.Specialisation)


def _try_get_range_vertex(vertex_map: mod.VertexMapUnionGraphUnionGraph,
                          image_vertex: mod.UnionGraph.Vertex) -> Optional[mod.UnionGraph.Vertex]:
    range_vertex: Optional[mod.UnionGraph.Vertex] = vertex_map.inverse(image_vertex)

    if not range_vertex or vertex_map[range_vertex].id != image_vertex.id:
        return None

    return range_vertex


def _rule_from_vertex_map(name: str, vertex_map: mod.VertexMapUnionGraphUnionGraph) -> mod.Rule:
    right_vertex_id_map: Dict[int, int] = {}

    builder: RuleBuilder = RuleBuilder(name)

    for left_vertex in vertex_map.domain.vertices:
        builder.add_left_vertex(left_vertex.id, left_vertex.stringLabel)

    for right_vertex in vertex_map.codomain.vertices:
        left_vertex: Optional[mod.UnionGraph.Vertex] = _try_get_range_vertex(vertex_map, right_vertex)

        if not left_vertex:
            vertex_id = len(builder.vertices) + 1
            right_vertex_id_map[right_vertex.id] = vertex_id
        else:
            vertex_id = left_vertex.id

        builder.add_right_vertex(vertex_id, right_vertex.stringLabel)

    for left_edge in vertex_map.domain.edges:
        builder.add_left_edge(left_edge.source.id, left_edge.target.id, left_edge.stringLabel)

    for right_edge in vertex_map.codomain.edges:
        source_vertex: Optional[mod.UnionGraph.Vertex] = _try_get_range_vertex(vertex_map, right_edge.source)
        target_vertex: Optional[mod.UnionGraph.Vertex] = _try_get_range_vertex(vertex_map, right_edge.target)

        source_id: int = right_vertex_id_map[right_edge.source.id] if not source_vertex else source_vertex.id
        target_id: int = right_vertex_id_map[right_edge.target.id] if not target_vertex else target_vertex.id

        builder.add_right_edge(source_id, target_id, right_edge.stringLabel)

    return builder.to_mod_rule()


class IteratedMap:
    def __init__(self, input_graphs: Iterable[CanonicalGraph], transitions: Iterable[Transition],
                 canonicaliser: GraphCanonicaliser):
        self._input_graphs: List[CanonicalGraph] = list(input_graphs)
        self._transitions: Set[Transition] = set(transitions)

        self._canonicaliser: GraphCanonicaliser = canonicaliser

        self._minimal_rules: Dict[RuleGraph, List[Transition]] = {}
        for transition in self._transitions:
            if transition.minimal_subrule not in self._minimal_rules:
                self._minimal_rules[transition.minimal_subrule] = []

            self._minimal_rules[transition.minimal_subrule].append(transition)

        self._transition_system: mod.DG = mod.DG(graphPolicy=mod.IsomorphismPolicy.Check,
                                                 labelSettings=specialisation_label_settings)

    def __enter__(self) -> 'IteratedMap':
        self._dg_builder = self._transition_system.build()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._dg_builder = None

    @property
    def minimal_rules(self) -> Dict[RuleGraph, List[Transition]]:
        return {rule: list(transitions) for rule, transitions in self._minimal_rules.items()}

    @property
    def number_of_minimal_rules(self) -> int:
        return len(self._minimal_rules)

    def print_summary(self):
        print('Input Summary:')
        print('-------------------')
        print(f'\tinput graphs: {len(self._input_graphs)}')
        print(f'\ttransitions: {len(self._transitions)}')
        print(f'\tminimal rules: {self.number_of_minimal_rules} of which '
              f'{len([transitions for transitions in self._minimal_rules.values() if len(transitions) == 1])}'
              f' are trivial')
        print()

    def has_transition(self, transition: Transition) -> bool:
        return transition in self._transitions

    def enumerate_applications(self, rule: CanonicalRule) -> Iterable[Transition]:
        strategy: mod.DGStrat = (mod.addSubset(graph.graph for graph in self._input_graphs) >> rule.rule)

        self._dg_builder.execute(strategy)

        hyper_edges: List[mod.DGHyperEdge] = [edge for edge in self._transition_system.edges if rule.rule in edge.rules]

        generated_transitions: Set[Transition] = set()
        for index, hyper_edge in enumerate(hyper_edges):
            vertex_mapper: mod.DGVertexMapper = mod.DGVertexMapper(hyper_edge)

            vertex_maps: List[mod.VertexMapUnionGraphUnionGraph] = [
                vertex_map for hyper_edge_rule, vertex_map in vertex_mapper
                if self._canonicaliser.canonicalise_rule(hyper_edge_rule) == rule
            ]

            print(f"\t\tFound {len(generated_transitions)} transitions. "
                  f"Processing hyper edge {index + 1}/{len(hyper_edges)} "
                  f"with {len(vertex_maps)} element maps...",
                  end='\r')

            new_transitions: Set[Transition] = set()
            for map_index, vertex_map in enumerate(vertex_maps):
                transition_rule: Optional[RuleGraph] = RuleGraph.from_rule(
                    _rule_from_vertex_map(f"{rule.name[4:]}_{hyper_edge.id}_{map_index}", vertex_map),
                    self._canonicaliser
                )

                if transition_rule:
                    new_transitions.add(Transition(transition_rule))

            generated_transitions.update(new_transitions)

        print()
        return generated_transitions
