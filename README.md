# Rule Inference

Script for inference of graph transformation rules from explicit transitions, represented as a labeled iterated map. Requires [MØD](https://cheminf.imada.sdu.dk/mod/), [NetworkX](https://networkx.org/) and [DOcplex](https://pypi.org/project/docplex/) to run.

Usage:
```commandline
main.py [-r <float>] <input_directory> [output_file]
```

where `input_directory` contains subfolders `graphs` and `rules`, specifying the input graphs and transitions, respectively, of the labeled iterated map;
`output_file` specifies the file into which the resulting rule set is outputted in a json format;
and `-r` is a scalar modifier controlling the impact of data distortion. Setting a large `-r` will force the algorithm to compute exact generating rule sets while setting `-r` to zero results in the distortion being completely ignored, the algorithm outputting a trivial minimal generating rule set.
