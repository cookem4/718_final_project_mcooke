#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=40
#SBATCH --time=12:00:00
#SBATCH --job-name mcooke_compiler_data_sweep
#SBATCH --output=compiler_data_sweep_%j.out
#SBATCH --mail-type=FAIL
module load NiaEnv/2019b
module load cmake
module load gcc
module load python/3
module load valgrind
python3 run_search_space.py
