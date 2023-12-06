#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=40
#SBATCH --time=12:00:00
#SBATCH --job-name mcooke_test_run
#SBATCH --output=mcooke_test_run_%j.out
#SBATCH --mail-type=FAIL
module load NiaEnv/2019b
module load cmake
module load gcc
module load python/3
module load valgrind
python3 generate_ntt_impl.py --dimension=129 --verbose=1 --codesize=4000 --heapsize=10000 --stacksize=40000
