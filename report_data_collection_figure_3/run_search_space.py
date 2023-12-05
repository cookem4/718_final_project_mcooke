 
import subprocess 
import pdb
import re
 
# Data container 
class Ntt_Data: 
    dim_build_str = "DIM"
    type_build_str = "NTT_TYPE"
    is_lut_build_str = "LUT_BASED"
    fixed_radix_build_str = "FAST_FIXED"
    mixed_radix_build_str = "FAST_MIXED"
    max_mixed_radix_build_str = "FAST_MIXED"
    max_mixed_radix_build_str = "MAX_RADIX"
    is_parallel_build_str = "PARALLEL"
    def __init__(self, type_str, is_lut, fixed_radix, max_mixed_radix, is_parallel): 
        self.type_str = type_str 
        self.is_lut = is_lut 
        self.fixed_radix = fixed_radix 
        self.mixed_radix = 1 if fixed_radix == 0 else 0
        self.max_mixed_radix = max_mixed_radix 
        self.is_parallel = is_parallel 
        self.dim_data_x = [] 
        self.runtime_y = [] 
        self.heap_y = [] 
        self.ir_cnt_y = [] 
        self.stack_height_y = [] 
        self.code_size_B_y = [] 
        self.func_size_B_y = [] 
        self.prog_output = [] 
        self.exec_status_y = [] # Pass/fail 
        self.fname = str(self.type_str) + "_LUT" + str(self.is_lut)  + "_F" + str(self.fixed_radix) + "_MR" + str(self.max_mixed_radix) + "_P" + str(self.is_parallel) + "_data_sweep.csv"
        with open(self.fname, "a") as file:
            file.write("Dim,Status,Runtime,Heap,IR Cnt,Code Size B,Func Size B\n")
 
 
def run_bash_cmd(bash_command): 
    try: 
        # Run the command and capture the output and error 
        output = subprocess.check_output(bash_command, shell=True, universal_newlines=True, stderr=subprocess.STDOUT) 
         
        # Print the output 
        # print(output) 
        return output 
    except subprocess.CalledProcessError as e: 
        # If the command returns a non-zero exit code, it will raise a CalledProcessError 
        print(f"Command failed with exit code {e.returncode}:") 
        print(e.output) 
 
def main(): 
    PROG_NAME = "./ntt_test" 
    DIM_LST = list(range(32, 255))
    mixed_radix_range = [3, 5, 7, 11, 13]
    ntt_objs = [] 
    # Cross product of search space creates a set of NTT objects with certain
    # attributes
    NTT_TYPE = "TYPE_N2"
    for is_lut in [0, 1]:
        # TODO temp skip non-lut parallelization for failures
        if is_lut == 1:
            for is_parallel in [0, 1]:
                new_data_obj = Ntt_Data(NTT_TYPE, is_lut, 0, 1, is_parallel) 
                ntt_objs.append(new_data_obj) 
        else:
            new_data_obj = Ntt_Data(NTT_TYPE, is_lut, 0, 1, 0) 
            ntt_objs.append(new_data_obj) 
    NTT_TYPE = "TYPE_FAST"
    for is_lut in [0, 1]:
        for is_fixed_radix in [0, 1]:
            # Skip if is N2
            if (is_fixed_radix == 1):
                new_data_obj = Ntt_Data(NTT_TYPE, is_lut, 1, 2, 0) 
                ntt_objs.append(new_data_obj) 
            else:
                for max_mixed_radix in mixed_radix_range:
                    new_data_obj = Ntt_Data(NTT_TYPE, is_lut, 0, max_mixed_radix, 0) 
                    ntt_objs.append(new_data_obj) 

    bash_command_base = "make clean && make CFLAGS=\"-O2" 
    for dim in DIM_LST: 
        for ntt_obj in ntt_objs: 
            ntt_obj.dim_data_x.append(dim) 
            bash_command_build = bash_command_base  + " -D" + ntt_obj.dim_build_str             + "=" + str(dim)
            bash_command_build = bash_command_build + " -D" + ntt_obj.type_build_str            + "=" + str(ntt_obj.type_str)
            bash_command_build = bash_command_build + " -D" + ntt_obj.is_lut_build_str          + "=" + str(ntt_obj.is_lut)
            bash_command_build = bash_command_build + " -D" + ntt_obj.fixed_radix_build_str     + "=" + str(ntt_obj.fixed_radix)
            bash_command_build = bash_command_build + " -D" + ntt_obj.fixed_radix_build_str     + "=" + str(ntt_obj.fixed_radix)
            bash_command_build = bash_command_build + " -D" + ntt_obj.mixed_radix_build_str     + "=" + str(ntt_obj.mixed_radix)
            bash_command_build = bash_command_build + " -D" + ntt_obj.max_mixed_radix_build_str + "=" + str(ntt_obj.max_mixed_radix)
            bash_command_build = bash_command_build + " -D" + ntt_obj.is_parallel_build_str     + "=" + str(ntt_obj.is_parallel)
            if (ntt_obj.is_parallel == 1):
                bash_command_build = bash_command_build + " -fopenmp "
            bash_command = bash_command_build + "\"" 
            print(bash_command)
            # Compile the program 
            output = run_bash_cmd(bash_command) 
            # Run the program 
            output = run_bash_cmd(PROG_NAME) 
            ntt_obj.prog_output.append(output) 
            if (output.find("PASS") != -1): 
                ntt_obj.exec_status_y.append("PASS") 
                print("N = " + str(dim) + " PASSED for NTT: " + ntt_obj.fname) 
            else: 
                ntt_obj.exec_status_y.append("FAIL") 
                print("N = " + str(dim) + " FAILED for NTT: " + ntt_obj.fname) 
 
            # Tools: 
            # valgrind --tool=cachegrind,massif,callgrind 
            # Can then run callgrind_annotate or ms_print for the given callgrind log 
 
            bash_command = "valgrind --tool=massif " + PROG_NAME 
            output = run_bash_cmd(bash_command) 
            # Parse the massif output 
            bash_command = "ls massif* | xargs -I {} ms_print {}" 
            output = run_bash_cmd(bash_command) 
            massif_pattern = r"(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)"
            # The last line looks like this:
            '''
            --------------------------------------------------------------------------------
              n        time(i)         total(B)   useful-heap(B) extra-heap(B)    stacks(B)
            --------------------------------------------------------------------------------
             10        206,103            2,376            2,320            56            0
            '''
            # We want the total(B) argument
            matches = re.findall(massif_pattern, output)
            # We care about third match, but want the max across the snapshots
            # peak_match = re.findall("([\d,]+)B.*ntt_impl", output)
            # ntt_obj.heap_y.append(peak_match[0])
            peak_match = re.findall("(\d+)\s+\(peak\)", output)
            # ntt_obj.heap_y.append(int(matches[int(peak_match[0])][2].replace(",","")))
            # Find max manually 
            this_max = int(matches[0][2].replace(",","")) 
            for i in matches[1:-1]: 
                if int(i[2].replace(",","")) > this_max: 
                    this_max = int(i[2].replace(",","")) 
            ntt_obj.heap_y.append(this_max)
            bash_command = "rm massif*" 
            output = run_bash_cmd(bash_command) 
 
            # Skip callgrind if openMP
            if (ntt_obj.is_parallel == 0):
                bash_command = "valgrind --tool=callgrind " + PROG_NAME 
                output = run_bash_cmd(bash_command) 
                # Parse the massif output 
                bash_command = "ls callgrind* | xargs -I {} callgrind_annotate {}" 
                output = run_bash_cmd(bash_command) 
                matches = re.findall(r"([\d,]+).*ntt_impl", output)
                ntt_obj.ir_cnt_y.append(int(matches[0].replace(",","")))
                bash_command = "rm callgrind*" 
                output = run_bash_cmd(bash_command) 
            else:
                ntt_obj.ir_cnt_y.append(int(0))
 
            # Check code size in B 
            bash_command = "size ntt.o" 
            output = run_bash_cmd(bash_command) 
            matches = re.findall(r"\d+\s+\d+\s+\d+\s+(\d+)", output)
            ntt_obj.code_size_B_y.append(int(matches[0]))
 
            # Check code size in Assembly lines 
            bash_command = "objdump -d -t ntt.o" 
            output = run_bash_cmd(bash_command) 
            matches1 = re.findall(r"([0-9A-Fa-f]+)\s+\<ntt_impl\>\:", output)
            matches2 = re.findall(r"([0-9A-Fa-f]+)\s+\<ntt_check\>\:", output)
            func_size = int(matches2[0], 16) - int(matches1[0], 16)
            ntt_obj.func_size_B_y.append(func_size)
 
            # Check runtime with flag 
            NUM_TIME_RERUN = 10
            running_sum = 0;
            bash_command_build = bash_command_build + " -DDO_TIME=1 \"" 
            # Compile with timing 
            output = run_bash_cmd(bash_command_build) 
            for i in range(NUM_TIME_RERUN):
                # Execute 
                output = run_bash_cmd(PROG_NAME) 
                matches = re.findall(r"TIME\:\s+(\d+)\s+us", output)
                running_sum = running_sum + int(matches[0])
            ntt_obj.runtime_y.append(running_sum / NUM_TIME_RERUN)

            # Write collected data to the CSV file so we don't lose it if
            # there's a runtime error
            with open(ntt_obj.fname, "a") as file:
                file.write(str(ntt_obj.dim_data_x[-1]) + "," + \
                           str(ntt_obj.exec_status_y[-1]) + "," + \
                           str(ntt_obj.runtime_y[-1]) + "," + \
                           str(ntt_obj.heap_y[-1]) + "," + \
                           str(ntt_obj.ir_cnt_y[-1]) + "," + \
                           str(ntt_obj.code_size_B_y[-1]) + "," + \
                           str(ntt_obj.func_size_B_y[-1]) + "\n");
 
if __name__ == "__main__": 
    main() 
