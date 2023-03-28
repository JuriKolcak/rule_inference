import mod

from typing import Dict, List, Set, Tuple, Union


class EdgeTuple(Tuple[int, int]):
    def __new__(cls, edge: Tuple[int, int]):
        return super().__new__(cls, sorted(edge))


class RuleSideGraph:
    def __init__(self, name: str):
        self._name: str = name

        self._elements: Dict[Union[int, EdgeTuple], str] = {}

    @property
    def vertices(self) -> Dict[int, str]:
        return {element: label for element, label in self._elements.items() if isinstance(element, int)}

    @property
    def edges(self) -> Dict[EdgeTuple, str]:
        return {element: label for element, label in self._elements.items() if not isinstance(element, int)}

    def has_element(self, element: Union[int, EdgeTuple]) -> bool:
        return element in self._elements

    def label(self, element: Union[int, EdgeTuple]) -> str:
        return self._elements[element]

    def add_element(self, element: Union[int, EdgeTuple], label: str):
        self._elements[element] = label

    def remove_element(self, element: Union[int, EdgeTuple]):
        del self._elements[element]

    def to_gml(self, indent: int = 1) -> str:
        indent_string = "\t" * indent

        output = [f"{indent_string}{self._name} ["]

        for element, label in self._elements.items():
            if isinstance(element, int):
                output.append(f"{indent_string}\tnode [ id {element} label \"{label}\" ]")
            else:
                output.append(f"{indent_string}\tedge [ source {element[0]} target {element[1]} label \"{label}\" ]")

        output.append(f"{indent_string}]")

        return "\n".join(output)


class RuleBuilder:
    def __init__(self, rule_id: str):
        self._id: str = rule_id

        self._left: RuleSideGraph = RuleSideGraph("left")
        self._context: RuleSideGraph = RuleSideGraph("context")
        self._right: RuleSideGraph = RuleSideGraph("right")

    @property
    def vertices(self) -> Set[int]:
        return set(self._left.vertices.keys()).union(self._context.vertices.keys()).union(self._right.vertices.keys())

    @property
    def edges(self) -> Set[EdgeTuple]:
        return set(self._left.edges.keys()).union(self._context.edges.keys()).union(self._right.edges.keys())

    @staticmethod
    def _add_edge_vertices(edge: EdgeTuple, target_graph: RuleSideGraph, alternative_graphs: List[RuleSideGraph]):
        for vertex in edge:
            if not target_graph.has_element(vertex) and\
                    (len(alternative_graphs) == 0 or
                     any(not graph.has_element(vertex) for graph in alternative_graphs)):
                target_graph.add_element(vertex, "*")

    @staticmethod
    def from_rule(rule: mod.Rule) -> 'RuleBuilder':
        builder = RuleBuilder(rule.name)

        for vertex in rule.vertices:
            if not vertex.left.isNull():
                builder.add_left_vertex(vertex.id, vertex.left.stringLabel)

            if not vertex.right.isNull():
                builder.add_right_vertex(vertex.id, vertex.right.stringLabel)

        for edge in rule.edges:
            if not edge.left.isNull():
                builder.add_left_edge(edge.source.id, edge.target.id, edge.left.stringLabel)

            if not edge.right.isNull():
                builder.add_right_edge(edge.source.id, edge.target.id, edge.right.stringLabel)

        return builder

    def _add_side_element(self, element: Union[int, EdgeTuple], label: str,
                          side: RuleSideGraph, opposite_side: RuleSideGraph):
        if self._context.has_element(element):
            context_label = self._context.label(element)
            if context_label == label:
                return

            opposite_side.add_element(element, context_label)
            self._context.remove_element(element)
        elif opposite_side.has_element(element) and opposite_side.label(element) == label:
            opposite_side.remove_element(element)
            if side.has_element(element):
                side.remove_element(element)

            self._context.add_element(element, label)
            return

        side.add_element(element, label)

    def _add_left_element(self, element: Union[int, EdgeTuple], label: str):
        self._add_side_element(element, label, self._left, self._right)

    def _add_context_element(self, element: Union[int, EdgeTuple], label: str):
        if self._left.has_element(element):
            self._left.remove_element(element)

        if self._right.has_element(element):
            self._right.remove_element(element)

        self._context.add_element(element, label)

    def _add_right_element(self, element: Union[int, EdgeTuple], label: str):
        self._add_side_element(element, label, self._right, self._left)

    def _add_side_edge_vertices(self, edge: EdgeTuple, side: RuleSideGraph):
        self._add_edge_vertices(edge, side, [self._context])

    def has_vertex(self, id: int) -> bool:
        return id in self.vertices

    def has_edge(self, source: int, target: int) -> bool:
        edge = EdgeTuple((source, target))

        return edge in self.edges

    def add_left_vertex(self, id: int, label: str):
        self._add_left_element(id, label)

    def add_context_vertex(self, id: int, label: str):
        self._add_context_element(id, label)

    def add_right_vertex(self, id: int, label: str):
        self._add_right_element(id, label)

    def add_left_edge(self, source: int, target: int, label: str):
        edge = EdgeTuple((source, target))
        self._add_side_edge_vertices(edge, self._left)

        self._add_left_element(edge, label)

    def add_context_edge(self, source: int, target: int, label: str):
        edge = EdgeTuple((source, target))
        self._add_edge_vertices(edge, self._context, [self._left, self._right])

        self._add_context_element(edge, label)

    def add_right_edge(self, source: int, target: int, label: str):
        edge = EdgeTuple((source, target))
        self._add_side_edge_vertices(edge, self._right)

        self._add_right_element(edge, label)

    def add_context_graph(self, graph: mod.Graph):
        vertex_id_map = {}

        for vertex in graph.vertices:
            vertex_id_map[vertex.id] = 1 + max(self.vertices) if len(self.vertices) > 0 else 0
            self.add_context_vertex(vertex_id_map[vertex.id], vertex.stringLabel)

        for edge in graph.edges:
            self.add_context_edge(vertex_id_map[edge.source.id], vertex_id_map[edge.target.id], edge.stringLabel)

    def to_gml(self) -> str:
        return f"rule [\n\truleID \"{self._id}\"\n{self._left.to_gml()}\n{self._context.to_gml()}\n"\
               f"{self._right.to_gml()}\n]"

    def to_mod_rule(self, add=False) -> mod.Rule:
        return mod.ruleGMLString(self.to_gml(), add=add)
