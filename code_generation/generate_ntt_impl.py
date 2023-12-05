import re
import argparse
import numpy as np
import pdb
import vprint as vp
import ntt_source as ns
import ntt_params as nt
import search_space as ss

def get_arch():
    bash_command = "lscpu"
    output = ss.run_bash_cmd(bash_command) 
    matches = re.findall(r"Architecture:\s+(.*)", output)
    arch_str = ""
    if not matches:
        print("ERROR: No arch available")
    arch_str = matches[0]
    is_x86 = arch_str == "x86_64"
    is_arm64 = arch_str == "arm64"
    is_arm32 = arch_str == "arm32"
    matches = re.findall(r"avx2", output)
    has_avx2 = True if matches else False
    matches = re.findall(r"avx512", output)
    has_avx512 = True if matches else False
    matches = re.findall(r"Thread\(s\) per core:\s+(\d+)", output)
    num_threads_per_core = 1
    if matches:
        num_threads_per_core = int(matches[0])
    matches = re.findall(r"Core\(s\) per socket:\s+(\d+)", output)
    cores_per_socket = 1
    if matches:
        cores_per_socket = int(matches[0])
    matches = re.findall(r"Socket\(s\):\s+(\d+)", output)
    sockets = 1
    if matches:
        sockets = int(matches[0])
    num_threads = num_threads_per_core * cores_per_socket * sockets
    ret_dict = {
            "x86" : is_x86,
            "arm64" : is_arm64,
            "arm32" : is_arm32,
            "avx2" : has_avx2,
            "avx512" : has_avx512,
            "num_threads" : num_threads
    }
    return ret_dict

def main(args):
    # Access command-line arguments using args.argument_name
    dimension = int(args.dimension)
    code_size = int(args.codesize)
    heap_size = int(args.heapsize)
    stack_size = int(args.stacksize)
    # Set global verbosity variable
    vp.verbose = True if int(args.verbose) == 1 else False
    
    ntt_parameters = nt.NTT_Params(dimension)

    arch_dict = get_arch()

    # Build initial search space
    search_space = ss.build_search_space(arch_dict, ntt_parameters)

    print(f"Initial search space size: {len(search_space)} variants")

    # Do a quick prune of search space based on code size - don't need to run
    # anything, just compilation and analysis via the ntt object file size
    # In this pruning stage, start with "-O3" and if the size doesn't fit
    # within the boundary try "-Os"
    # By default the point in the search space should be "-O3", otherwise if
    # "-Os" is needed to fit, change the build flag in the search space object
    vp.vprint("-----------------------------------------------------------------")
    if code_size > 0:
        search_space = ss.prune_search_space_code_size(search_space, code_size)
        print(f"Size after pruning for code size: {len(search_space)} variants")
    else:
        print("Skipping code size pruning")
    vp.vprint("-----------------------------------------------------------------")

    # Does a binary search of max process stack size
    vp.vprint("-----------------------------------------------------------------")
    if stack_size > 0:
        search_space = ss.prune_search_space_stack_size(search_space, stack_size)
        print(f"Size after pruning for stack size: {len(search_space)} variants")
    else:
        print("Skipping stack size pruning")
    vp.vprint("-----------------------------------------------------------------")

    # Lastly eliminate based on heap requirements, which will be the most
    # costly to profile
    vp.vprint("-----------------------------------------------------------------")
    if heap_size > 0:
        search_space = ss.prune_search_space_heap_size(search_space, heap_size)
        print(f"Size after pruning for heap size: {len(search_space)} variants")
    else:
        print("Skipping heap size pruning")
    vp.vprint("-----------------------------------------------------------------")

    # For the remaining points in the search space, all fit within the program
    # requirements. Run them all to pick option with lowest time
    vp.vprint("-----------------------------------------------------------------")
    if len(search_space) == 0:
        print(f"ERROR! no NTT implemenation for the target architecture can be implemented with:\nCode size less than {code_size}B\nPeak heap less than {heap_size}B\nMax stack less than {stack_size}B")
    else:
        n_a = "(N/A)"
        optimal_point = ss.prune_search_space_runtime(search_space)
        print(f"Done! Generated NTT implementation {optimal_point.variant_name} to run in {optimal_point.runtime}us with: \nCode size {optimal_point.code_size if code_size > 0 else n_a}B\nPeak heap {optimal_point.max_heap if heap_size > 0 else n_a}B\nMax stack {optimal_point.max_stack if stack_size > 0 else n_a}B\nIs deployed in ntt_target.o")
    vp.vprint("-----------------------------------------------------------------")

    ###################
    # FUTURE WORK
    # ILP Notes:
    # - Might not be needed since search space is relatively small
    # - Caching-based appcoaches could give more insight into complexity of
    # search-space, but it was also shown that caching was not very helpful due
    # to regularity of accesses
    # - Maybe some pseudo-caching where some powers are stored, even half, anything that can be used to prevent
    # computation of a_pow_b_mod_m
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code generation in C for efficient arbitrary-radix NTT implementations")
    parser.add_argument("-d", "--dimension", default=129, help="The NTT dimension")
    parser.add_argument("-c", "--codesize", default=0, help="The maximum acceptable code size in Bytes")
    parser.add_argument("-e", "--heapsize", default=0, help="The maximum acceptable peak heap size in Bytes")
    parser.add_argument("-s", "--stacksize", default=0, help="The maximum acceptable peak stack size in Bytes")
    parser.add_argument("-v", "--verbose", default=0, help="Enable (1) or disable (0) verbose prints")
    
    args = parser.parse_args()

    main(args)

