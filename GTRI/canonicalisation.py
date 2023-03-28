import mod

from GTRI.networkx_interface import get_component_graphs, graph_to_nx_graph, graph_to_unlabeled_edge_nx_graph, \
    nx_graph_to_gml, rule_combined_graph_to_nx_graph
from networkx import Graph as NXGraph
from typing import Dict, Iterable, Tuple, Union


class CanonicalGraph:
    def __init__(self, graph: mod.Graph, canonicaliser: 'GraphCanonicaliser'):
        self._graph: mod.Graph = graph

        self._canonical_smiles: str = canonicaliser.graph_canonical_smiles(self._graph)

        self._automorphism_group: mod.Graph.AutGroup = self._graph.aut()

    def __eq__(self, other: 'CanonicalGraph') -> bool:
        return self.canonical_smiles == other.canonical_smiles

    def __ne__(self, other: 'CanonicalGraph') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 41 * hash(self.canonical_smiles)

    def __ge__(self, other: 'CanonicalGraph') -> bool:
        return not self < other

    def __gt__(self, other: 'CanonicalGraph') -> bool:
        return not self <= other

    def __le__(self, other: 'CanonicalGraph') -> bool:
        return self.canonical_smiles <= other.canonical_smiles

    def __lt__(self, other: 'CanonicalGraph') -> bool:
        return self.canonical_smiles < other.canonical_smiles

    def __str__(self) -> str:
        return str(self.graph)

    @property
    def graph(self) -> mod.Graph:
        return self._graph

    @property
    def canonical_smiles(self) -> str:
        return self._canonical_smiles

    @property
    def vertices(self) -> Iterable[mod.Graph.Vertex]:
        yield from self.graph.vertices

    @property
    def edges(self) -> Iterable[mod.Graph.Edge]:
        yield from self.graph.edges

    @property
    def number_of_vertices(self) -> int:
        return self.graph.numVertices

    @property
    def number_of_edges(self) -> int:
        return self.graph.numEdges

    @property
    def automorphism_generators(self) -> Iterable[mod.Graph.Aut]:
        return self._automorphism_group.gens

    def to_gml(self) -> str:
        return self.graph.getGMLString()


class CanonicalRule:
    def __init__(self, rule: mod.Rule, canonicaliser: 'GraphCanonicaliser'):
        self._rule: mod.Rule = rule

        self._canonical_smiles: Tuple[str] = canonicaliser.rule_canonical_smiles(self._rule)

        self._left: Tuple[CanonicalGraph] = canonicaliser.canonicalise_nx_graph(
            graph_to_nx_graph(rule.left, use_indices=True))
        self._right: Tuple[CanonicalGraph] = canonicaliser.canonicalise_nx_graph(
            graph_to_nx_graph(rule.right, use_indices=True))

    def __eq__(self, other: 'CanonicalRule') -> bool:
        return self.canonical_smiles == other.canonical_smiles

    def __ne__(self, other: 'CanonicalRule') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 47 * hash(self.canonical_smiles)

    def __str__(self) -> str:
        return str(self.rule)

    @property
    def rule(self) -> mod.Rule:
        return self._rule

    @property
    def canonical_smiles(self) -> Tuple[str]:
        return self._canonical_smiles

    @property
    def left(self) -> Tuple[CanonicalGraph]:
        return self._left

    @property
    def right(self) -> Tuple[CanonicalGraph]:
        return self._right

    @property
    def name(self) -> str:
        return self.rule.name

    @property
    def vertices(self) -> Iterable[mod.Rule.Vertex]:
        yield from self.rule.vertices

    @property
    def edges(self) -> Iterable[mod.Rule.Edge]:
        yield from self.rule.edges

    @property
    def number_of_vertices(self) -> int:
        return self.rule.numVertices

    @property
    def number_of_edges(self) -> int:
        return self.rule.numEdges

    def to_gml(self) -> str:
        return self.rule.getGMLString()


class GraphCanonicaliser:
    def __init__(self):
        self._label_db: Dict[str, str] = {}

    def _relabel_via_database(self, label: str) -> str:
        if label not in self._label_db:
            self._label_db[label] = f'{len(self._label_db) + 1}C'

        return self._label_db[label]

    def graph_canonical_smiles(self, graph: mod.Graph) -> str:
        return mod.graphGMLString(
            nx_graph_to_gml(graph_to_unlabeled_edge_nx_graph(graph, lambda x: self._relabel_via_database(x))), add=False
        ).smiles

    def nx_graph_canonical_smiles(self, graph: NXGraph) -> Tuple[str]:
        components = list(get_component_graphs(graph).keys())

        return tuple(sorted(self.graph_canonical_smiles(component) for component in components))

    def rule_canonical_smiles(self, rule: mod.Rule) -> Tuple[str]:
        return self.nx_graph_canonical_smiles(rule_combined_graph_to_nx_graph(rule))

    def canonical_smiles(self, graph: Union[mod.Graph, mod.Rule, NXGraph]) -> Tuple[str]:
        if isinstance(graph, mod.Graph):
            return tuple(self.graph_canonical_smiles(graph))

        if isinstance(graph, NXGraph):
            return self.nx_graph_canonical_smiles(graph)

        return self.rule_canonical_smiles(graph)

    def canonicalise_graph(self, graph: mod.Graph) -> CanonicalGraph:
        return CanonicalGraph(graph, self)

    def canonicalise_graphs(self, graphs: Iterable[mod.Graph]) -> Dict[mod.Graph, CanonicalGraph]:
        return {graph: self.canonicalise_graph(graph) for graph in graphs}

    def canonicalise_nx_graph(self, graph: NXGraph) -> Tuple[CanonicalGraph]:
        return tuple(sorted((CanonicalGraph(component, self) for component in get_component_graphs(graph)),
                            key=lambda x: x.canonical_smiles))

    def canonicalise_rule(self, rule: mod.Rule) -> CanonicalRule:
        return CanonicalRule(rule, self)
