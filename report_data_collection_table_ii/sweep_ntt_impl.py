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

def main():

    # dimension_lst = list(range(32, 256))
    # Dimensions for modern NTT implementations:
    # 256, 512, 1024, 2048
    dimension_lst = [256, 512, 1024, 2048]

    data_collection_dict = {}

    arch_dict = get_arch()
    for dimension in dimension_lst:
        ntt_parameters = nt.NTT_Params(dimension)
        # Build initial search space
        search_space = ss.build_search_space(arch_dict, ntt_parameters)
        print(f"On dimension {dimension}")
        for search_space_point in search_space:
            print(f"On search space point {search_space_point.variant_name}")
            code_gen_point = ns.Ntt_Source(search_space_point)
            # Call code gen
            code_gen_point.generate_target()
            search_space_point.set_stack_size()
            search_space_point.set_heap_size()
            search_space_point.set_code_size()
            search_space_point.set_code_lines()
            search_space_point.set_runtime()
            if (not search_space_point.variant_name in data_collection_dict):
                data_collection_dict[search_space_point.variant_name] = []
                data_collection_dict[search_space_point.variant_name].append("Dim,Runtime,Heap,Stack,Code,CodeLines")
            data_collection_dict[search_space_point.variant_name].append( \
                    str(dimension) + "," \
                    + str(search_space_point.runtime) + "," \
                    + str(search_space_point.max_heap) + "," \
                    + str(search_space_point.max_stack) + "," \
                    + str(search_space_point.code_size) + "," \
                    + str(search_space_point.code_lines))
    # Print all dict entries
    for key in data_collection_dict:
        with open(str(key + ".csv"), "w") as file:
            for entry in data_collection_dict[key]:
                file.write(entry + "\n")

if __name__ == "__main__":
    main()

