import cProfile
import mod
import sys

from argparse import ArgumentParser
from GTRI.canonicalisation import CanonicalGraph, GraphCanonicaliser
from GTRI.ilp_model import model_from_iterated_map, ILPModel, ILPSolution
from GTRI.iterated_map import IteratedMap
from GTRI.rule_graph import RuleGraph
from GTRI.transition import Transition
from os import listdir, path
from typing import List


def _parse_iterated_map(input_directory: str, canonicaliser: GraphCanonicaliser) -> IteratedMap:
    graph_subdirectory = path.join(input_directory, "graphs")

    input_graphs: List[CanonicalGraph] = list(set(canonicaliser.canonicalise_graph(
        mod.Graph.fromGMLFile(path.join(graph_subdirectory, file_name), add=False))
                                                  for file_name in listdir(graph_subdirectory)))

    rule_subdirectory = path.join(input_directory, "rules")

    transitions: List[Transition] = list(set(
        Transition(RuleGraph.from_rule(mod.Rule.fromGMLFile(path.join(rule_subdirectory, file_name), add=False),
                                       canonicaliser)) for file_name in listdir(rule_subdirectory)
    ))

    return IteratedMap(input_graphs, transitions, canonicaliser)


def main():
    parser: ArgumentParser = ArgumentParser(description='Finds a generating rule set for a labeled iterated map.')

    parser.add_argument('input_directory', help="Directory containing the input labeled iterated map consisting "
                                                "of 'graphs' subfolder with input graphs and "
                                                "'rules' subfolder with transitions as gml rules.")
    parser.add_argument('output_file', nargs='?', default=None, help="File for writing the inferred rules.")

    parser.add_argument('-r', '--distortion_scale', type=float, default=1.0,
                        help="Scalar by which the number of spurious transitions is multiplied in the ILP. "
                             "Used to establish a desired relationship between the compression and distortion rates.")

    parser.add_argument('-s', '--save_model', type=str, default=None,
                        help="Save the ILP model to the specified file in json format. "
                             "The model can be reloaded for experiments with varying distortion scales.")

    parser.add_argument('-l', '--load_model', type=str, default=None,
                        help="Load the ILP model from file instead of building from the labeled iterated map.")

    arguments = parser.parse_args(sys.argv[1:])

    canonicaliser: GraphCanonicaliser = GraphCanonicaliser()

    if arguments.load_model:
        print('Loading ILP Model from file...')
        print('-------------------')
        model: ILPModel = ILPModel.load(arguments.load_model, arguments.distortion_scale, canonicaliser)
    else:
        iterated_map: IteratedMap = _parse_iterated_map(arguments.input_directory, canonicaliser)
        iterated_map.print_summary()

        print('Building ILP Model...')
        print('-------------------\n')
        with iterated_map:
            model: ILPModel = model_from_iterated_map(iterated_map, arguments.distortion_scale)

        if arguments.save_model:
            model.save(arguments.save_model)

    model.print_information()

    print()

    print('Solving Rule Distillation Model...')
    print('-------------------')
    solution: ILPSolution = model.solve()
    solution.print_information()

    if arguments.output_file:
        solution.save(arguments.output_file)


if __name__ == "__main__":
    # with cProfile.Profile() as profile:
    #     main()
    #
    # profile.dump_stats("profile.prof")
    main()
