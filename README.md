# Problem Statement
Develop a code generator to create a custom NTT implementation for the target architecture to minimize runtime given a desired maximum memory footprint

# Overview
Literature shows disjointed approaches across both HW and SW. This project approahces NTT computation in the SW domain with a domain-specific code generator. The code generator presented first prunes a large search space of potential NTT implementation candidates by eliminating variants that do not fit within the required memory footprint. Graph traversal is then performed to locate the variant with minimal runtime for the target system. This includes consideration of multi-threading, AVX512/AVX2 instructions sets, and various N^2 versus NlogN implementations that each trade-off runtime, code size, heap size, and stack size. The initial search space is 94 points.

# To Run the Code Generation Tool
Code generation is run through the code_generation/generate_ntt_impl.py script. To run:
~~~
cd code_generation
python3 generate_ntt_impl.py --dimension=<#> --verbose=<0/1> --codesize=<Max code size in B> --heapsize=<Max heap size in B> --stacksize=<Max stack size in B>
~~~
Example invocation:
~~~
python3 generate_ntt_impl.py --dimension=129 --verbose=1 --codesize=4000 --heapsize=10000 --stacksize=20000
~~~
The target NTT implementation for the architecture that runs the generate_ntt_impl.py script is deployed to the ntt_test binary. The object files and source files are also available for custom linking and/or compilation. The source files consist of:
1. main.c - Runs a brief test suite to assert PASS/FAIL by performing the NTT in the forward and inverse directions
2. ntt_target.c/h - contains the ntt implementation for the deployed variant

Performing code generation may take a couple minutes. Once the best NTT implmenetation is deployed it may be used continuously in the desired application.

# To reproduce Table II in report
Data for Table II is produced from report_data_collection_table_ii/sweep_ntt_impl.py. To run:
~~~
cd report_data_collection_table_ii
python3 sweep_ntt_impl.py
~~~
Alternatively, on Niagara simply run data_collect_batch.sh from the report_data_collection_table_ii directory.
~~~
cd report_data_collection_table_ii
sbatch data_collect_batch.sh
~~~
As the script runs the data collection progress will be printed for each dimension of 256,512,1024,2048 for the shown variants in Table II. The results will be present as csv files corresponding to the variant names present in the first column of Table II.

Collecting this data should only take a couple minutes.

# To reproduce Fig 3 in report
Data for Figure 3 is produced from report_data_collection_figure_3/sweep_ntt_impl.py. To run:
~~~
cd report_data_collection_figure_3
python3 run_search_space.py
python3 plot_search_space.py
~~~
Alternatively, on Niagara simply run data_collect_batch.sh from the report_data_collection_figure_3 directory.
~~~
cd report_data_collection_figure_3
sbatch data_collect_batch.sh
~~~
As the script runs the data collection progress will be printed for each dimension between 32 and 255 for the entire cross product of variants. The results will be present as csv files. While not all variants could be printed from the generated cross product in the space, the variant name for each CSV contains the data that was used to generate the subfigured of Figure 3. The figures are then created with plot_search_space.py.

As this data is much more comprehensive, collection may take a few hours.
