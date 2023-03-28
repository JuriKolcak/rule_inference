import mod

from networkx import connected_components
from networkx import Graph as NXGraph
from typing import Any, Callable, Dict, Union


def _add_vertices_to_nx_graph(graph: Union[mod.Graph, mod.Rule.LeftGraph, mod.Rule.RightGraph],
                              nx_graph: NXGraph, relabel: Callable[[str], str], use_indices: bool):
    for vertex in graph.vertices:
        nx_graph.add_node(vertex.id if use_indices else vertex, label=relabel(vertex.stringLabel))


def _connect_labelled_edge_in_nx_graph(edge: Union[mod.Graph.Edge, mod.Rule.Edge],
                                       nx_graph: NXGraph, index: int) -> int:
    nx_graph.add_edge(edge.source.id, index, label='-')
    nx_graph.add_edge(index, edge.target.id, label='-')

    return index + 1


def _get_rule_element_label(element: Union[mod.Rule.LeftGraph.Vertex, mod.Rule.RightGraph.Vertex,
                                           mod.Rule.LeftGraph.Edge, mod.Rule.RightGraph.Edge],
                            label_if_empty: str = "") -> str:
    if element.isNull():
        return label_if_empty

    return element.stringLabel


def _nx_graph_to_mod(graph: NXGraph, node_dereference: Callable[[Any], int]) -> mod.Graph:
    return mod.graphGMLString(nx_graph_to_gml(graph, node_dereference), add=False)


def get_component_graphs(graph: NXGraph, node_dereference: Callable[[Any], int] = lambda x: x) ->\
        Dict[mod.Graph, NXGraph]:
    molecules = [graph.subgraph(component).copy() for component in connected_components(graph)]

    return {_nx_graph_to_mod(molecule, node_dereference): molecule for molecule in molecules}


def graph_to_nx_graph(graph: Union[mod.Graph, mod.Rule.LeftGraph, mod.Rule.RightGraph],
                      relabel: Callable[[str], str] = lambda x: x, use_indices: bool = False) -> NXGraph:
    nx_graph: NXGraph = NXGraph()

    _add_vertices_to_nx_graph(graph, nx_graph, relabel, use_indices)

    for edge in graph.edges:
        if edge.stringLabel == "no_edge":
            continue

        source, target = (edge.source.id, edge.target.id) if use_indices else (edge.source, edge.target)
        nx_graph.add_edge(source, target, label=relabel(edge.stringLabel))

    return nx_graph


def graph_to_unlabeled_edge_nx_graph(graph: mod.Graph, relabel: Callable[[str], str] = lambda x: x) -> NXGraph:
    nx_graph: NXGraph = NXGraph()

    vertex_count: int = graph.numVertices

    _add_vertices_to_nx_graph(graph, nx_graph, relabel, True)

    for edge in graph.edges:
        nx_graph.add_node(vertex_count, label=relabel(edge.stringLabel))

        vertex_count = _connect_labelled_edge_in_nx_graph(edge, nx_graph, vertex_count)

    return nx_graph


def nx_graph_to_gml(graph: NXGraph, node_dereference: Callable[[Any], int] = lambda x: x) -> str:
    out = ['graph [']

    for node in graph.nodes:
        label = graph.nodes[node]['label']
        out.append(f'\tnode [ id {node_dereference(node)} label "{label}" ]')

    for (source, target) in graph.edges:
        label = graph.edges[source, target]['label']
        out.append(f'\tedge [ source {node_dereference(source)} target {node_dereference(target)}'
                   f'label "{label}" ]')

    out.append(']')

    return '\n'.join(out)


def rule_combined_graph_to_nx_graph(rule: mod.Rule) -> NXGraph:
    graph: NXGraph = NXGraph()

    vertex_count: int = rule.numVertices

    for vertex in rule.vertices:
        graph.add_node(vertex.id, label=f'({_get_rule_element_label(vertex.left)}; '
                                        f'{_get_rule_element_label(vertex.right)})', rule_element=vertex)

    for edge in rule.edges:
        graph.add_node(vertex_count, label=f'({_get_rule_element_label(edge.left)}; '
                                           f'{_get_rule_element_label(edge.right)})', rule_element=edge)

        vertex_count = _connect_labelled_edge_in_nx_graph(edge, graph, vertex_count)

    return graph
