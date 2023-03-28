import mod


from GTRI.canonicalisation import CanonicalGraph
from typing import Dict, Iterable, Iterator, Tuple


class Morphism:
    def __init__(self, vertex_map: Dict[mod.Graph.Vertex, mod.Graph.Vertex]):
        self._vertex_map: Dict[mod.Graph.Vertex, mod.Graph.Vertex] = vertex_map

        self._fingerprint: Tuple[Tuple[mod.Graph.Vertex, mod.Graph.Vertex]] = tuple(sorted(
            (range_vertex, image_vertex) for range_vertex, image_vertex in self._vertex_map.items()
        ))

    def __eq__(self, other: 'Morphism') -> bool:
        return self._fingerprint == other._fingerprint

    def __ne__(self, other: 'Morphism') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 37 * hash(self._fingerprint)

    def __ge__(self, other: 'Morphism') -> bool:
        return self._fingerprint >= other._fingerprint

    def __gt__(self, other: 'Morphism') -> bool:
        return self._fingerprint > other._fingerprint

    def __le__(self, other: 'Morphism') -> bool:
        return self._fingerprint <= other._fingerprint

    def __lt__(self, other: 'Morphism') -> bool:
        return self._fingerprint < other._fingerprint

    def __iter__(self) -> Iterator[mod.Graph.Vertex]:
        return iter(self._vertex_map)

    def __getitem__(self, item: mod.Graph.Vertex) -> mod.Graph.Vertex:
        return self._vertex_map[item]

    def __len__(self) -> int:
        return len(self._fingerprint)

    def __neg__(self) -> 'Morphism':
        return Morphism({image_vertex: range_vertex for range_vertex, image_vertex in self.items()})

    def __add__(self, other: 'Morphism') -> 'Morphism':
        return Morphism({range_vertex: other[image_vertex] for range_vertex, image_vertex in self.items()})

    @staticmethod
    def _identity(graph: mod.Graph) -> 'Morphism':
        return Morphism({vertex: vertex for vertex in graph.vertices})

    @staticmethod
    def _from_automorphism(graph: mod.Graph, automorphism: mod.Graph.Aut) -> 'Morphism':
        return Morphism({vertex: automorphism[vertex] for vertex in graph.vertices})

    @staticmethod
    def _from_automorphism_generators(graph: CanonicalGraph) -> Iterable['Morphism']:
        for automorphism_generator in graph.automorphism_generators:
            yield Morphism._from_automorphism(graph.graph, automorphism_generator)

        yield Morphism._identity(graph.graph)

    def items(self) -> Iterable[Tuple[mod.Graph.Vertex, mod.Graph.Vertex]]:
        return self._vertex_map.items()

    def canonicalise(self, range: CanonicalGraph, image: CanonicalGraph) -> 'Morphism':
        smallest_candidate: Morphism = self

        for range_automorphism in Morphism._from_automorphism_generators(range):
            partial_candidate: Morphism = range_automorphism + self

            for image_automorphism in Morphism._from_automorphism_generators(image):
                candidate: Morphism = partial_candidate + image_automorphism

                if candidate < smallest_candidate:
                    smallest_candidate = candidate

        return smallest_candidate

