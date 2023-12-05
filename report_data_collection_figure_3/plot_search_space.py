import pandas as pd
import matplotlib.pyplot as plt
import subprocess

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

# Function to plot the given array together on same set of figs
def plot_set(dir_name, legend):
    # Define the columns to plot against "Dim"
    columns_to_plot = ["Runtime", "Heap", "IR Cnt", "Code Size B", "Func Size B"]
    for column in columns_to_plot:
        folder_path = dir_name + "_FIGS/"
        bash_cmd = "[ ! -d " + folder_path + " ] && mkdir " + folder_path + " || echo"
        run_bash_cmd(bash_cmd)

        plt.figure(figsize=(8, 6))  # Set the figure size
        plt.xlabel("Dim")
        plt.ylabel(column)
        plt.title(f" {column} vs. Dim")
        plt.grid(True)
        for ntt_type in legend:

            df = pd.read_csv(ntt_type.fname)
            plt.plot(df["Dim"], df[column], linestyle='-', label=ntt_type)
        plt.legend()
        plt.savefig(folder_path + dir_name + "_" + column.replace(" ","") + ".png", dpi=300, bbox_inches='tight')
        plt.close()

# Define the columns to plot against "Dim"
columns_to_plot = ["Runtime", "Heap", "IR Cnt", "Code Size B", "Func Size B"]

# Build the same NTT object list as in the run script
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

for ntt_type in ntt_objs:
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(ntt_type.fname)
    ntt_name = ntt_type.fname.replace("_data_sweep.csv", "")
    folder_path = ntt_name + "_FIGS/"
    bash_cmd = "[ ! -d " + folder_path + " ] && mkdir " + folder_path + " || echo"
    run_bash_cmd(bash_cmd)

    # Create a line graph for each column
    for column in columns_to_plot:
        plt.figure(figsize=(8, 6))  # Set the figure size
        plt.plot(df["Dim"].astype(int), df[column].astype(int), linestyle='-', label=column)
        plt.xlabel("Dim")
        plt.ylabel(column)
        plt.title(ntt_name + f" {column} vs. Dim")
        plt.grid(True)
        plt.legend()
        plt.savefig(folder_path + ntt_name + "_" + column.replace(" ","") + ".png", dpi=300, bbox_inches='tight')
        plt.close()


# plot_set("ALL", ntt_objs)
