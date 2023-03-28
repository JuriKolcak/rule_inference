import mod

from GTRI.canonicalisation import CanonicalGraph, CanonicalRule, GraphCanonicaliser
from GTRI.morphism import Morphism
from GTRI.networkx_interface import graph_to_nx_graph, nx_graph_to_gml
from GTRI.rule_builder import RuleBuilder
from itertools import chain
from networkx import connected_components
from networkx import Graph as NXGraph
from networkx.algorithms.isomorphism import GraphMatcher
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union


_isomorphism_label_settings: mod.LabelSettings = mod.LabelSettings(mod.LabelType.String, mod.LabelRelation.Isomorphism)


def _is_combined(label: str) -> bool:
    return label.find(';') >= 0


def is_relabeled(element: Union[mod.Graph.Vertex, mod.Graph.Edge]) -> bool:
    return _is_combined(element.stringLabel)


def _has_abstract_label(element: Union[mod.Graph.Vertex, mod.Graph.Edge]) -> bool:
    return element.stringLabel.find('*') >= 0


def _split_label(label: str) -> (Optional[str], Optional[str]):
    labels: List[str] = label.split(';')

    left_label: Optional[str] = labels[0] if labels[0] else None
    right_label: Optional[str] = labels[1] if len(labels) > 1 and labels[1] else None

    return left_label, right_label


def split_element_label(element: Union[mod.Graph.Vertex, mod.Graph.Edge]) -> (Optional[str], Optional[str]):
    return _split_label(element.stringLabel)


def _combine_labels(left_label: Optional[str], right_label: Optional[str]) -> str:
    left_string_label = left_label if left_label else ""
    right_string_label = right_label if right_label else ""

    if left_string_label != right_string_label:
        return f"{left_string_label};{right_string_label}"

    return left_string_label


def _combine_element_labels(left_element: Union[mod.Rule.LeftGraph.Vertex, mod.Rule.LeftGraph.Edge],
                            right_element: Union[mod.Rule.RightGraph.Vertex, mod.Rule.RightGraph.Edge]) -> str:
    left_label: Optional[str] = None if left_element.isNull() else left_element.stringLabel
    right_label: Optional[str] = None if right_element.isNull() else right_element.stringLabel

    return _combine_labels(left_label, right_label)


def _compare_labels(supergraph_label: Optional[str], subgraph_label: Optional[str]) -> bool:
    if subgraph_label and supergraph_label and _is_combined(subgraph_label) and _is_combined(supergraph_label):
        left_subgraph_label, right_subgraph_label = _split_label(subgraph_label)
        left_supergraph_label, right_supergraph_label = _split_label(supergraph_label)

        return _compare_labels(left_supergraph_label, left_subgraph_label) \
            and _compare_labels(right_supergraph_label, right_subgraph_label)

    if not supergraph_label:
        return not subgraph_label

    if subgraph_label == "*":
        return True

    return subgraph_label == supergraph_label


def _compare_elements(supergraph_element: Dict[str, Any], subgraph_element: Dict[str, Any]) -> bool:
    return _compare_labels(supergraph_element["label"], subgraph_element["label"])


def _equal_elements(graph1_element: Dict[str, Any], graph2_element: Dict[str, Any]) -> bool:
    return graph1_element["label"] == graph2_element["label"]


def _find_modified_nodes(nx_graph: NXGraph,
                         component: Set[Union[int, mod.Graph.Vertex]]) -> Iterable[Union[int, mod.Graph.Vertex]]:
    for node in component:
        if _is_combined(nx_graph.nodes[node]["label"]) \
                or any(_is_combined(nx_graph.edges[edge]["label"]) for edge in nx_graph.edges(node)):
            yield node


def _nx_graph_to_mod_graph(nx_graph: NXGraph, canonicaliser: GraphCanonicaliser) -> Optional[CanonicalGraph]:
    components: List[Set[Union[int, mod.Graph.Vertex]]] = list(connected_components(nx_graph))

    if len(components) > 1:
        principal_nodes: List[Union[int, mod.Graph.Vertex]] = []
        for component in components:
            new_principal_nodes: List[Union[int, mod.Graph.Vertex]] = []

            for modified_node in _find_modified_nodes(nx_graph, component):
                new_principal_nodes.append(modified_node)

                for principal_node in principal_nodes:
                    nx_graph.add_edge(principal_node, modified_node, label="no_edge")

            if len(new_principal_nodes) == 0:
                return None

            principal_nodes.extend(new_principal_nodes)

    return canonicaliser.canonicalise_graph(mod.Graph.fromGMLString(nx_graph_to_gml(nx_graph), add=False
    ))


def _rule_to_nx_graph(rule: mod.Rule) -> NXGraph:
    graph: NXGraph = NXGraph()

    for vertex in rule.vertices:
        label = _combine_element_labels(vertex.left, vertex.right)
        graph.add_node(vertex.id, label=label)

    for edge in rule.edges:
        label = _combine_element_labels(edge.left, edge.right)
        graph.add_edge(edge.source.id, edge.target.id, label=label)

    return graph


def _match_to_morphism(range: 'RuleGraph', image: 'RuleGraph', match: Dict[int, int]) -> Morphism:
    return Morphism({
        range.get_vertex(range_vertex_index): image.get_vertex(image_vertex_index)
        for range_vertex_index, image_vertex_index in match.items()
    })


class RuleGraph:
    def __init__(self, graph: CanonicalGraph, name: str, canonicaliser: GraphCanonicaliser):
        self._canonicaliser: GraphCanonicaliser = canonicaliser
        self._name: str = name

        self._graph: CanonicalGraph = graph
        self._nx_graph: NXGraph = graph_to_nx_graph(self._graph.graph, use_indices=True)

        self._rule: Optional[CanonicalRule] = None

    def __eq__(self, other: 'RuleGraph') -> bool:
        return self._graph == other._graph

    def __ne__(self, other: 'RuleGraph') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 19 * hash(self._graph)

    def __ge__(self, other: 'RuleGraph') -> bool:
        return not self < other

    def __gt__(self, other: 'RuleGraph') -> bool:
        return not self <= other

    def __le__(self, other: 'RuleGraph') -> bool:
        return self == other or self < other

    def __lt__(self, other: 'RuleGraph') -> bool:
        return self._graph < other._graph

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> CanonicalGraph:
        return self._graph

    @property
    def abstract_vertices(self) -> Iterable[mod.Graph.Vertex]:
        return (vertex for vertex in self.graph.vertices if _has_abstract_label(vertex))

    @property
    def abstract_edges(self) -> Iterable[mod.Graph.Edge]:
        return (edge for edge in self.graph.edges if _has_abstract_label(edge))

    @property
    def abstract_elements(self) -> Iterable[Union[mod.Graph.Vertex, mod.Graph.Edge]]:
        return chain(self.abstract_vertices, self.abstract_edges)

    @property
    def rule(self) -> CanonicalRule:
        if not self._rule:
            self._rule = self._to_rule()

        return self._rule

    @staticmethod
    def from_rule(rule: mod.Rule, canonicaliser: GraphCanonicaliser) -> Optional['RuleGraph']:
        nx_graph: NXGraph = _rule_to_nx_graph(rule)

        graph: Optional[CanonicalGraph] = _nx_graph_to_mod_graph(nx_graph, canonicaliser)

        if not graph:
            return None

        return RuleGraph(graph, rule.name, canonicaliser)

    @staticmethod
    def load(data: Dict[str, str], canonicaliser: GraphCanonicaliser) -> 'RuleGraph':
        return RuleGraph(canonicaliser.canonicalise_graph(mod.graphGMLString(data["gml"], add=False)),
                         data["name"], canonicaliser)

    def _compute_automorphisms(self) -> Iterable[Morphism]:
        graph_matcher: GraphMatcher = GraphMatcher(self._nx_graph, self._nx_graph)

        for isomorphism in graph_matcher.isomorphisms_iter():
            yield Morphism(isomorphism)

    def _to_rule(self) -> CanonicalRule:
        builder: RuleBuilder = RuleBuilder(self.name)

        for vertex in self.graph.vertices:
            if is_relabeled(vertex):
                left_label, right_label = split_element_label(vertex)

                if left_label:
                    builder.add_left_vertex(vertex.id, left_label)

                if right_label:
                    builder.add_right_vertex(vertex.id, right_label)
            else:
                builder.add_context_vertex(vertex.id, vertex.stringLabel)

        for edge in self.graph.edges:
            if edge.stringLabel == "no_edge":
                continue

            if is_relabeled(edge):
                left_label, right_label = split_element_label(edge)

                if left_label:
                    builder.add_left_edge(edge.source.id, edge.target.id, left_label)

                if right_label:
                    builder.add_right_edge(edge.source.id, edge.target.id, right_label)
            else:
                builder.add_context_edge(edge.source.id, edge.target.id, edge.stringLabel)

        return self._canonicaliser.canonicalise_rule(builder.to_mod_rule())

    def get_vertex(self, vertex_id: int) -> mod.Graph.Vertex:
        return next(vertex for vertex in self.graph.vertices if vertex.id == vertex_id)

    def get_edge(self, source: mod.Graph.Vertex, target: mod.Graph.Vertex) -> Optional[mod.Graph.Edge]:
        for edge in self.graph.edges:
            if (edge.source == source and edge.target == target) or (edge.source == target and edge.target == source):
                return edge

        return None

    def get_adjacent_edges(self, vertex: mod.Graph.Vertex) -> Iterable[mod.Graph.Edge]:
        for edge in self.graph.edges:
            if edge.stringLabel == "no_edge":
                continue

            if edge.source == vertex or edge.target == vertex:
                yield edge

    def relabel_element(self, element: Union[mod.Graph.Vertex, mod.Graph.Edge],
                        new_label: str) -> Tuple['RuleGraph', Morphism]:
        new_nx_graph: NXGraph = self._nx_graph.copy()
        element_id: str
        if type(element) is mod.Graph.Vertex:
            element_id = str(element.id)
            new_nx_graph.nodes[element.id]["label"] = new_label
        else:
            element_id = f"{element.source.id}-{element.target.id}"
            new_nx_graph.edges[element.source.id, element.target.id]["label"] = new_label

        new_rule_graph: RuleGraph = RuleGraph(_nx_graph_to_mod_graph(new_nx_graph, self._canonicaliser),
                                              f"{self.name}_L{element_id}", self._canonicaliser)

        return new_rule_graph, \
            Morphism({new_rule_graph.get_vertex(vertex.id): vertex for vertex in self.graph.vertices})

    def relabel_element_left(self, element: Union[mod.Graph.Vertex, mod.Graph.Edge],
                             new_label: str) -> Tuple['RuleGraph', Morphism]:
        left_label, right_label = split_element_label(element)
        full_new_label = _combine_labels(new_label, right_label)

        return self.relabel_element(element, full_new_label)

    def relabel_element_right(self, element: Union[mod.Graph.Vertex, mod.Graph.Edge],
                              new_label: str) -> Tuple['RuleGraph', Morphism]:
        left_label, right_label = split_element_label(element)
        full_new_label = _combine_labels(left_label, new_label)

        return self.relabel_element(element, full_new_label)

    def add_edge(self, source: mod.Graph.Vertex, target: Optional[mod.Graph.Vertex]) -> Tuple['RuleGraph', Morphism]:
        new_nx_graph: NXGraph = self._nx_graph.copy()

        target_id: int
        if target:
            target_id = target.id
        else:
            target_id = self.graph.number_of_vertices
            new_nx_graph.add_node(target_id, label="*")

        new_nx_graph.add_edge(source.id, target_id, label="*")

        new_rule_graph: RuleGraph = RuleGraph(_nx_graph_to_mod_graph(new_nx_graph, self._canonicaliser),
                                              f"{self.name}_A{source.id}-{target_id}", self._canonicaliser)

        return new_rule_graph, \
            Morphism({new_rule_graph.get_vertex(vertex.id): vertex for vertex in self.graph.vertices})

    def get_minimal_subrule(self) -> Tuple['RuleGraph', Morphism]:
        builder: RuleBuilder = RuleBuilder(f"min_{self._name}")

        vertex_id_map: Dict[int, int] = {}

        for vertex in self.graph.vertices:
            if not is_relabeled(vertex):
                continue

            left_label, right_label = split_element_label(vertex)

            subgraph_vertex_id = len(builder.vertices)
            vertex_id_map[vertex.id] = subgraph_vertex_id

            if left_label:
                builder.add_left_vertex(subgraph_vertex_id, "*")

            if right_label:
                builder.add_right_vertex(subgraph_vertex_id, right_label)

        for edge in self.graph.edges:
            if not is_relabeled(edge):
                continue

            if edge.source.id not in vertex_id_map:
                subgraph_vertex_id = len(builder.vertices)
                vertex_id_map[edge.source.id] = subgraph_vertex_id

                builder.add_context_vertex(subgraph_vertex_id, "*")

            if edge.target.id not in vertex_id_map:
                subgraph_vertex_id = len(builder.vertices)
                vertex_id_map[edge.target.id] = subgraph_vertex_id

                builder.add_context_vertex(subgraph_vertex_id, "*")

            left_label, right_label = split_element_label(edge)

            if left_label:
                builder.add_left_edge(vertex_id_map[edge.source.id], vertex_id_map[edge.target.id], "*")

            if right_label:
                builder.add_right_edge(vertex_id_map[edge.source.id], vertex_id_map[edge.target.id], right_label)

        subrule: RuleGraph = RuleGraph.from_rule(builder.to_mod_rule(), self._canonicaliser)

        vertex_map: Dict[mod.Graph.Vertex, mod.Graph.Vertex] = {}
        for vertex_id, subgraph_vertex_id in vertex_id_map.items():
            vertex: mod.Graph.Vertex = next(vertex for vertex in self.graph.vertices if vertex.id == vertex_id)
            subgraph_vertex: mod.Graph.Vertex = next(vertex for vertex in subrule.graph.vertices
                                                     if vertex.id == subgraph_vertex_id)

            vertex_map[subgraph_vertex] = vertex

        return subrule, Morphism(vertex_map)

    def isomorphisms(self, other: 'RuleGraph') -> Iterable[Morphism]:
        graph_matcher: GraphMatcher = GraphMatcher(other._nx_graph, self._nx_graph,
                                                   node_match=_equal_elements, edge_match=_equal_elements)

        for isomorphism in graph_matcher.isomorphisms_iter():
            yield _match_to_morphism(other, self, isomorphism)

    def embed(self, subgraph: 'RuleGraph') -> Iterable[Morphism]:
        graph_matcher: GraphMatcher = GraphMatcher(self._nx_graph, subgraph._nx_graph,
                                                   node_match=_compare_elements, edge_match=_compare_elements)

        for monomorphism in graph_matcher.subgraph_monomorphisms_iter():
            yield - _match_to_morphism(self, subgraph, monomorphism)

    def save(self) -> Dict[str, str]:
        return {
            "gml": self.graph.to_gml(),
            "name": self.name
        }
