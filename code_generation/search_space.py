import ntt_source as ns
import ntt_params as nt
import pdb
import subprocess
import re
import vprint as vp

def run_bash_cmd(bash_command): 
    try: 
        # Run the command and capture the output and error 
        output = subprocess.check_output(bash_command, shell=True, universal_newlines=True, stderr=subprocess.STDOUT) 
        return output 
    except subprocess.CalledProcessError as e: 
        return ""


class Search_Space: 
    # These parameters set by running the test suite
    code_size = 0
    max_heap = 0
    max_stack = 0
    total_mem = 0
    instr_ret = 0
    runtime = 0
    prog_name = "./ntt_test"

    def set_runtime(self):
        # Check runtime with flag 
        NUM_TIME_RERUN = 10
        running_sum = 0;
        bash_cmd = self.bash_command_build + " -DDO_TIME=1 \"" 
        # Compile with timing 
        output = run_bash_cmd(bash_cmd) 
        for i in range(NUM_TIME_RERUN):
            # Execute 
            output = run_bash_cmd(self.prog_name) 
            matches = re.findall(r"TIME\:\s+(\d+)\s+us", output)
            running_sum = running_sum + int(matches[0])
        self.runtime = (running_sum / NUM_TIME_RERUN)
        vp.vprint(f"Runtime for {self.variant_name} is {self.runtime}")

    def set_heap_size(self):
        # Build first
        bash_command = self.bash_command_build + " \"" 
        output = run_bash_cmd(bash_command) 
        bash_command = "valgrind --tool=massif " + self.prog_name 
        output = run_bash_cmd(bash_command) 
        # Parse the massif output 
        bash_command = "ls massif* | xargs -I {} ms_print {}" 
        output = run_bash_cmd(bash_command) 
        massif_pattern = r"(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)"
        # The last line looks like this:
        # --------------------------------------------------------------------------------
        #   n        time(i)         total(B)   useful-heap(B) extra-heap(B)    stacks(B)
        # --------------------------------------------------------------------------------
        #  10        206,103            2,376            2,320            56            0
        # We want the total(B) argument
        matches = re.findall(massif_pattern, output)
        peak_match = re.findall("(\d+)\s+\(peak\)", output)
        # Find max manually 
        this_max = int(matches[0][2].replace(",","")) 
        for i in matches[1:-1]: 
            if int(i[2].replace(",","")) > this_max: 
                this_max = int(i[2].replace(",","")) 
        self.max_heap = this_max
        bash_command = "rm massif*" 
        output = run_bash_cmd(bash_command) 
        vp.vprint(f"Peak heap size for {self.variant_name} is {self.max_heap}")

    def set_stack_size(self):
        # Three options:
        # 1. Use stack token allocation
        # 2. Only calculate based on an estimation
        # of intrinsic data needed for recursive definitions, otherwise 
        # stack size will likely be insignificant, other than arrays local to
        # functions
        # 3. Modify stack size with "ulimit -s <#>" until stack overflow

        # Doing option 3
        bash_cmd = self.bash_command_build + " \"" 
        # Compile
        output = run_bash_cmd(bash_cmd) 
        stack_overflow = False
        # NOTE: this value is in KB
        bash_cmd = "ulimit -s"
        output = run_bash_cmd(bash_cmd)
        initial_stack_height = int(output)
        # prlimit accepts B, ulimit does KB
        cur_stack_height = 1024*initial_stack_height
        cur_cntr = cur_stack_height
        # Binary search until peak stack height determined
        # Run program with modified stack
        while (cur_cntr > 0):
            cur_cntr = cur_cntr // 2
            bash_cmd = "prlimit --pid=$$ --stack=" + str(cur_stack_height) + " && " + self.prog_name
            output = run_bash_cmd(bash_cmd)
            matches = "" if output is None else re.findall(r"PASS", output)
            if (matches):
                cur_stack_height -= cur_cntr
            else:
                cur_stack_height += cur_cntr
        self.max_stack = cur_stack_height
        vp.vprint(f"Peak stack size for {self.variant_name} is {self.max_stack}")

    def set_code_lines(self):
        # Check code size in B by parsing dissassembly
        # Build first
        bash_command = self.bash_command_build + " \"" 
        output = run_bash_cmd(bash_command) 
        # Check code size in Assembly lines 
        bash_command = "objdump -d -t ntt_target.o"
        output = run_bash_cmd(bash_command) 
        matches = re.findall(r"(\s+[0-9A-Fa-f]+)\:", output)
        # Get last address
        self.code_size = int(matches[-1], 16)
        vp.vprint(f"Code size for {self.variant_name} is {self.code_size}")

    def set_code_size(self):
        # Check code size in B 
        # Build first
        bash_command = self.bash_command_build + " \"" 
        output = run_bash_cmd(bash_command) 
        bash_command = "size ntt_target.o" 
        output = run_bash_cmd(bash_command) 
        matches = re.findall(r"\d+\s+\d+\s+\d+\s+(\d+)", output)
        self.code_size = int(matches[0])
        vp.vprint(f"Code size for {self.variant_name} is {self.code_size}")

    # Full suite of tests, not done by pruning
    def run_test_suite(self):
        bash_command = self.bash_command_build + "\"" 
        vp.vprint(bash_command)
        # Compile the program 
        output = run_bash_cmd(bash_command) 
        # Run the program 
        output = run_bash_cmd(self.prog_name) 
        vp.vprint(output)
        if (output.find("PASS") != -1): 
            vp.vprint(str("PASSED for NTT: " + self.variant_name)) 
        else: 
            vp.vprint(str("FAILED for NTT: " + self.variant_name)) 

        # Tools: 
        # valgrind --tool=cachegrind,massif,callgrind 
        # Can then run callgrind_annotate or ms_print for the given callgrind log 

        bash_command = "valgrind --tool=massif " + self.prog_name 
        output = run_bash_cmd(bash_command) 
        # Parse the massif output 
        bash_command = "ls massif* | xargs -I {} ms_print {}" 
        output = run_bash_cmd(bash_command) 
        massif_pattern = r"(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)"
        # The last line looks like this:
        # --------------------------------------------------------------------------------
        #   n        time(i)         total(B)   useful-heap(B) extra-heap(B)    stacks(B)
        # --------------------------------------------------------------------------------
        #  10        206,103            2,376            2,320            56            0
        # We want the total(B) argument
        matches = re.findall(massif_pattern, output)
        peak_match = re.findall("(\d+)\s+\(peak\)", output)
        # Find max manually 
        this_max = int(matches[0][2].replace(",","")) 
        for i in matches[1:-1]: 
            if int(i[2].replace(",","")) > this_max: 
                this_max = int(i[2].replace(",","")) 
        self.max_heap = this_max
        bash_command = "rm massif*" 
        output = run_bash_cmd(bash_command) 

        # Skip callgrind if parallel
        if (not self.is_omp and not self.is_pthread):
            bash_command = "valgrind --tool=callgrind " + self.prog_name 
            output = run_bash_cmd(bash_command) 
            # Parse the massif output 
            bash_command = "ls callgrind* | xargs -I {} callgrind_annotate {}" 
            output = run_bash_cmd(bash_command) 
            matches = re.findall(r"([\d,]+).*ntt_impl", output)
            self.instr_ret = int(matches[0].replace(",",""))
            bash_command = "rm callgrind*" 
            output = run_bash_cmd(bash_command) 
        else:
            self.instr_ret = int(0)

        # Check code size in B 
        bash_command = "size ntt_target.o" 
        output = run_bash_cmd(bash_command) 
        matches = re.findall(r"\d+\s+\d+\s+\d+\s+(\d+)", output)
        self.code_size = int(matches[0])

        # Check runtime with flag 
        NUM_TIME_RERUN = 10
        running_sum = 0;
        bash_cmd = self.bash_command_build + " -DDO_TIME=1 \"" 
        # Compile with timing 
        output = run_bash_cmd(bash_cmd) 
        for i in range(NUM_TIME_RERUN):
            # Execute 
            output = run_bash_cmd(self.prog_name) 
            matches = re.findall(r"TIME\:\s+(\d+)\s+us", output)
            running_sum = running_sum + int(matches[0])
        self.runtime = (running_sum / NUM_TIME_RERUN)

    def set_build_cmd(self):
        self.bash_command_build = "make clean && make CFLAGS=\" " + self.optimization_mode
        if (self.is_omp):
            self.bash_command_build += " -fopenmp "
        if (self.is_pthread):
            self.bash_command_build += " -pthread "
        if (self.is_avx):
            # if (self.is_avx512):
                # self.bash_command_build += " -mavx512 "
            # else:
            self.bash_command_build += " -mavx2 "

    def __init__(self, optimization_mode=" -O3 ", arch_dict=None, \
            type_str="TYPE_N2", is_lut=True, fixed_radix=False, \
            max_mixed_radix=1, is_omp=False, is_avx=False, is_recursive=False, \
            recursive_base_case=0, is_pthread=False, max_threads=None, \
            separate_inv_impl=True, ntt_parameters=None): 
        self.ntt_parameters=ntt_parameters
        self.optimization_mode=optimization_mode
        self.type_str = type_str 
        self.is_lut = is_lut 
        self.fixed_radix = fixed_radix 
        self.mixed_radix = True if not fixed_radix else False
        self.max_mixed_radix = max_mixed_radix 
        self.is_avx = is_avx 
        if arch_dict is None:
            self.is_avx512 = False
        else:
            self.is_avx512 = arch_dict["avx512"]
        if arch_dict is None:
            self.is_avx2 = False
        else:
            self.is_avx2 = arch_dict["avx2"]
        self.is_omp = is_omp 
        # Note: pthread and omp are mutually exclusive
        self.is_pthread = is_pthread 
        if max_threads is not None:
            self.max_threads = max_threads
        else:
            self.max_threads = arch_dict["num_threads"]
        self.is_recursive = is_recursive 
        self.recursive_base_case = recursive_base_case 
        # View code-size/performance tradeoff with separate
        # Forward and inverse implementations. To keep a common
        # Interface regardless use function interfaces
        self.separate_inv_impl = separate_inv_impl 
        self.variant_name = str(self.type_str) + \
                            "_LUT" + str(int(self.is_lut)) + \
                            "_F" + str(int(self.fixed_radix)) + \
                            "_MR" + str(self.max_mixed_radix) + \
                            "_P" + str(int(self.is_omp)) + \
                            "_AVX" + str(int(self.is_avx)) + \
                            "_R" + str(int(self.is_recursive)) + \
                            "_RB" + str(int(self.recursive_base_case)) + \
                            "_PT" + str(int(self.is_pthread)) + \
                            "_NT" + str(int(self.max_threads)) + \
                            "_DI" + str(int(self.separate_inv_impl))
        self.set_build_cmd()

####################
# TODO when traversing the search space there is no nuance with memory footprint, max heap size, avx usage
# The nuance comes from multi-threaded vs single-threaded for the NTT N^2 vs. NlogN inplace/recursive
####################

def build_search_space(arch_dict, ntt_parameters):
    # TODO might want to move these vectors into a file instead of looping over them
    # manually
    mixed_radix_range = [3, 5, 7, 11, 13]
    # TODO recursive_base_case=32 fails with N=1024?
    recursive_base_case_range = [8, 16, 32, 64, 128, 256]
    search_space_objs = [] 
    # Cross product of search space creates a set of NTT objects with certain attributes
    for separate_inv_impl in [False, True]:
        NTT_TYPE = "TYPE_N2"
        for is_lut in [False, True]:
            # OMP and AVX only work with LUT-based twiddle
            # solutions due to data dependencies with twiddle calcs
            if is_lut:
                for is_avx in [False, True]:
                    for is_omp in [False, True]:
                        new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                                    arch_dict=arch_dict, \
                                                    is_lut=is_lut, \
                                                    fixed_radix=False, \
                                                    max_mixed_radix=1, \
                                                    is_omp=is_omp, \
                                                    is_avx=is_avx, \
                                                    is_recursive=False, \
                                                    recursive_base_case=0, \
                                                    ntt_parameters=ntt_parameters, \
                                                    separate_inv_impl=separate_inv_impl) 
                        search_space_objs.append(new_data_obj) 
            else:
                new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                            arch_dict=arch_dict, \
                                            is_lut=is_lut, \
                                            fixed_radix=False, \
                                            max_mixed_radix=1, \
                                            is_omp=False, \
                                            is_avx=False, \
                                            is_recursive=False, \
                                            recursive_base_case=0, \
                                            ntt_parameters=ntt_parameters, \
                                            separate_inv_impl=separate_inv_impl) 
                search_space_objs.append(new_data_obj) 
        NTT_TYPE = "TYPE_FAST"
        for is_recursive in [False, True]:
            for is_lut in [False, True]:
                if is_recursive:
                    for recursive_base_case in recursive_base_case_range:
                        # OMP and AVX only work with LUT-based twiddle
                        # solutions due to data dependencies with twiddle calcs
                        if is_lut:
                            for is_omp in [False, True]:
                                for is_avx in [False, True]:
                                    new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                                                arch_dict=arch_dict, \
                                                                is_lut=is_lut, \
                                                                fixed_radix=True, \
                                                                max_mixed_radix=2, \
                                                                is_omp=is_omp, \
                                                                is_avx=is_avx, \
                                                                is_recursive=True, \
                                                                recursive_base_case=recursive_base_case, \
                                                                ntt_parameters=ntt_parameters, \
                                                                separate_inv_impl=separate_inv_impl) 
                                    search_space_objs.append(new_data_obj) 
                        else:
                            new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                                        arch_dict=arch_dict, \
                                                        is_lut=is_lut, \
                                                        fixed_radix=True, \
                                                        max_mixed_radix=2, \
                                                        is_omp=False, \
                                                        is_avx=False, \
                                                        is_recursive=True, \
                                                        recursive_base_case=recursive_base_case, \
                                                        ntt_parameters=ntt_parameters, \
                                                        separate_inv_impl=separate_inv_impl) 
                            search_space_objs.append(new_data_obj) 
                else:
                    for is_fixed_radix in [False, True]:
                        if (is_fixed_radix):
                            new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                                        arch_dict=arch_dict, \
                                                        is_lut=is_lut, \
                                                        fixed_radix=True, \
                                                        max_mixed_radix=2, \
                                                        is_omp=False, \
                                                        is_avx=False, \
                                                        is_recursive=False, \
                                                        recursive_base_case=0, \
                                                        ntt_parameters=ntt_parameters, \
                                                        separate_inv_impl=separate_inv_impl) 
                            search_space_objs.append(new_data_obj) 
                        else:
                            for max_mixed_radix in mixed_radix_range:
                                new_data_obj = Search_Space(type_str=NTT_TYPE, \
                                                            arch_dict=arch_dict, \
                                                            is_lut=is_lut, \
                                                            fixed_radix=False, \
                                                            max_mixed_radix=max_mixed_radix, \
                                                            is_omp=False, \
                                                            is_avx=False, \
                                                            is_recursive=False, \
                                                            recursive_base_case=0, \
                                                            ntt_parameters=ntt_parameters, \
                                                            separate_inv_impl=separate_inv_impl) 
                                search_space_objs.append(new_data_obj) 

    return search_space_objs

# Input: list of search space objects
def prune_search_space_stack_size(search_space, max_stack):
    pruned_list = []
    for search_space_point in search_space:
        code_gen_point = ns.Ntt_Source(search_space_point)
        # Call code gen
        code_gen_point.generate_target()
        search_space_point.set_stack_size()
        if (search_space_point.max_stack <= max_stack):
            pruned_list.append(search_space_point)
        else:
            vp.vprint(f"Pruning {search_space_point.variant_name} due to stack size")
    return pruned_list

def prune_search_space_heap_size(search_space, max_heap):
    pruned_list = []
    for search_space_point in search_space:
        code_gen_point = ns.Ntt_Source(search_space_point)
        # Call code gen
        code_gen_point.generate_target()
        search_space_point.set_heap_size()
        if (search_space_point.max_heap <= max_heap):
            pruned_list.append(search_space_point)
        else:
            vp.vprint(f"Pruning {search_space_point.variant_name} due to heap size")
    return pruned_list

def prune_search_space_code_size(search_space, max_code):
    pruned_list = []
    for search_space_point in search_space:
        code_gen_point = ns.Ntt_Source(search_space_point)
        # Call code gen
        code_gen_point.generate_target()
        # search_space_point.set_code_size()
        search_space_point.set_code_lines()
        if (search_space_point.code_size <= max_code):
            pruned_list.append(search_space_point)
        else:
            vp.vprint(f"Attempting with -Os on {search_space_point.variant_name} before pruning")
            # Attempt to change to "-Os" build flag before pruning
            search_space_point.optimization_mode = " -Os "
            search_space_point.set_build_cmd()
            # search_space_point.set_code_size()
            search_space_point.set_code_lines()
            if (search_space_point.code_size <= max_code):
                vp.vprint(f"The flag -Os saved {search_space_point.variant_name} from being pruned")
            else:
                vp.vprint(f"Pruning {search_space_point.variant_name} due to code size")
    return pruned_list

def prune_search_space_runtime(search_space):
    runtime_lst = []
    for search_space_point in search_space:
        code_gen_point = ns.Ntt_Source(search_space_point)
        # Call code gen
        code_gen_point.generate_target()
        search_space_point.set_runtime()
        runtime_lst.append(search_space_point.runtime)

    smallest_runtime = min(runtime_lst)
    min_idx = runtime_lst.index(smallest_runtime)
    return search_space[min_idx]
