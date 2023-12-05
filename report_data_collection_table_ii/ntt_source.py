# This file is to be used to build out the NTT implementation with
# Common blocks for each piece of the transform
# This will do pure code generation without many build flags in C
# Using as few build flags as possible to keep static code generation for
# the mixed radix implementation

import ntt_params as nt
import search_space as ss
import math
import pdb
import vprint as vp

# This class should be able to build out the source code given a set of NTT
# parameters and a search space object defining the point in the space
class Ntt_Source:
    c_test_name = "main.c"
    c_target_name = "ntt_target.c"
    h_target_name = "ntt_target.h"
    sub_pc = "#"
    sub_while = "while"
    sub_oc = "{"
    sub_cc = "}"
    sub_co = "//"
    sub_oco = "/*"
    sub_cco = "*/"
    sub_tab = "\t"
    sub_nl = "\\n"
    c_stack_check_call = \
"""
#if CHECK_STACK
    profile_stack();
#endif
"""


    def generate_target(self):
        # Use search space point to create code

        # Write header file constants
        with open(self.h_target_name, "w") as file:
            file.write("#ifndef NTT_H\n#define NTT_H\n")
            # TODO stdlib not needed?
            file.write("#include <stdlib.h>\n")
            file.write("#include <stdint.h>\n")
            file.write("#if CHECK_STACK\nvoid profile_stack();\n#endif\n")
            if self.search_space_point.is_omp:
                file.write("#include <omp.h>\n")
            if self.search_space_point.is_pthread:
                file.write("#include <pthread.h>\n")
                file.write(f"#define NUM_THREADS {self.search_space_point.max_threads}\n")
            if self.search_space_point.is_avx:
                file.write("#include <immintrin.h>\n")
            temp_str = \
"""
// Constants
#define FAIL_PRINT_INFO 1
"""
            # For recursive implementations we need to pass the size
            self.recursive_str = ""
            self.recursive_call_str = ""
            if (self.search_space_point.is_recursive):
                self.recursive_str += f"{self.ntt_parameters.n_type} n, {self.ntt_parameters.n_type} n0,"
                self.recursive_call_str = f"{self.ntt_parameters.n}, {self.ntt_parameters.n},"
            file.write(temp_str)
            # Inv flag only matters when we share an implementation between forward
            # and inverse transforms
            file.write(f"void ntt_impl({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.recursive_str} uint8_t inv);\n")
            file.write(f"void ntt_impl_inv({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.recursive_str} uint8_t inv);\n")
            file.write(f"#endif {self.sub_co} NTT_H \n")


        # Write test file
        with open(self.c_test_name, "w") as file:
            file.write("#include \"ntt_target.h\"\n")
            file.write("#include <string.h>\n")

            temp_str = \
f"""
{self.sub_pc}include <stdlib.h>
{self.sub_pc}include <sys/time.h>
{self.sub_pc}include <stdio.h>
"""
            file.write(temp_str)
            temp_str = \
f"""
{self.ntt_parameters.mod_type} modinv({self.ntt_parameters.mod_type} a, {self.ntt_parameters.mod_type} m) {self.sub_oc}
    {self.sub_co} Usage here doesn't count since it's a test-only feauture. Make signed to handle signed comparisons in the loop 
    int64_t q, t, r, newt, newr, tempt, tempr;
    t = 0;
    newt = 1;
    r = m;
    newr = a;
    {self.sub_while} (newr != 0) {self.sub_oc}
        q = r / newr;
        tempt = newt;
        tempr = newr;
        newt = t - q*newt;
        newr = r - q*newr;
        t = tempt;
        r = tempr;
    {self.sub_cc}
    if (t < 0) {self.sub_oc}
        t += m;
    {self.sub_cc}
    return t;
{self.sub_cc}
"""
            file.write(temp_str)
            temp_str = \
f"""
uint8_t ntt_check({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.ntt_parameters.mod_type} *x_inv, {self.ntt_parameters.mod_type} *y_inv) {self.sub_oc}
    ntt_impl(x, y, {self.recursive_call_str} 0);
    ntt_impl_inv(y, y_inv, {self.recursive_call_str} 1);
    x_inv = y;
    {self.ntt_parameters.mod_type} *orig_arr = x;
    {self.ntt_parameters.mod_type} *final_arr = y_inv;
    {self.ntt_parameters.mod_type} inv_n = modinv({self.ntt_parameters.n}, {self.ntt_parameters.mod});
    for ({self.ntt_parameters.n_type} i = 0; i < {self.ntt_parameters.n}; i++) {self.sub_oc}
        final_arr[i] = (final_arr[i] * inv_n) % {self.ntt_parameters.mod};
        if (final_arr[i] != orig_arr[i]) {self.sub_oc}
            {self.sub_co} TODO Temp skip FAST comparison
{self.sub_pc}if {int(self.search_space_point.type_str != "TYPE_FAST")}
            return 0;
{self.sub_pc}endif
        {self.sub_cc}
    {self.sub_cc}
    return 1;
{self.sub_cc}
"""
            file.write(temp_str)
            file.write("\n\nint main() {\n")
            temp_str = \
f"""
    srand(time(NULL));
"""
            file.write(temp_str)
            temp_str = \
f"""
    printf("Running NTT N = %d, mod = %d, g = %d, ginv = %d{self.sub_nl}", {self.ntt_parameters.n}, {self.ntt_parameters.mod}, {self.ntt_parameters.g}, {self.ntt_parameters.g_inv});
"""
            file.write(temp_str)

            # TODO how aggressive to go with threading here?
            if self.search_space_point.is_omp:
                temp_str = f"\tomp_set_num_threads({self.search_space_point.max_threads});\n"
                file.write(temp_str)

            temp_str = \
f"""
    {self.ntt_parameters.mod_type} *x = malloc({self.ntt_parameters.n} * sizeof({self.ntt_parameters.mod_type}));
    {self.ntt_parameters.mod_type} *y = malloc({self.ntt_parameters.n} * sizeof({self.ntt_parameters.mod_type}));
    {self.ntt_parameters.mod_type} *x_inv = malloc({self.ntt_parameters.n} * sizeof({self.ntt_parameters.mod_type}));
    {self.ntt_parameters.mod_type} *y_inv = malloc({self.ntt_parameters.n} * sizeof({self.ntt_parameters.mod_type}));
    for ({self.ntt_parameters.n_type} i = 0; i < {self.ntt_parameters.n}; i++) {self.sub_oc}
        {self.sub_co} x[i] = rand() % {self.ntt_parameters.mod};
        x[i] = i;
    {self.sub_cc}
{self.sub_pc}if DO_TIME
    struct timeval start, end;
    double elapsed_time;
    gettimeofday(&start, NULL);
{self.sub_pc}endif
    uint8_t check_res = ntt_check(x, y, x_inv, y_inv);
{self.sub_pc}if DO_TIME
    gettimeofday(&end, NULL);
    elapsed_time = (end.tv_sec - start.tv_sec)*1e6 + (end.tv_usec - start.tv_usec);
    printf("TIME: %0.0f us{self.sub_nl}", elapsed_time);
{self.sub_pc}endif
    if (!check_res) {self.sub_oc}
        {self.sub_pc}if FAIL_PRINT_INFO
        printf("FWD IN:{self.sub_nl}");
        for ({self.ntt_parameters.n_type} i = 0; i < {self.ntt_parameters.n}; i++) {self.sub_oc}
            printf("%d, ", x[i]);
        {self.sub_cc}
        printf("{self.sub_nl}FWD OUT:{self.sub_nl}");
        for ({self.ntt_parameters.n_type} i = 0; i < {self.ntt_parameters.n}; i++) {self.sub_oc}
            printf("%d, ", y[i]);
        {self.sub_cc}
        printf("{self.sub_nl}INV(FWD):{self.sub_nl}");
        for ({self.ntt_parameters.n_type} i = 0; i < {self.ntt_parameters.n}; i++) {self.sub_oc}
            printf("%d, ", y_inv[i]);
        {self.sub_cc}
        printf("{self.sub_nl} FAIL{self.sub_nl}");
        {self.sub_pc}else
        printf("FAIL{self.sub_nl}");
        {self.sub_pc}endif
    {self.sub_cc} else {self.sub_oc}
        printf("PASS{self.sub_nl}");
    {self.sub_cc}
{self.sub_cc}
"""
            file.write(temp_str)
        # End of Write test file

        # This seems to be unreliable due to how the OS moves the stack around.
        # Can instead set stack size in bash with "ulimit -s" to view the
        # inital stack size then can use "ulimit -s <#>" to change the stack
        # size.
        c_stack_check = \
f"""
#if CHECK_STACK
#include <stdio.h>
static void *g_stack_top = NULL;
static int g_stack_grows_up = 0;
static int g_stack_grows_up_init_done = 0;
static void *g_stack_ptr_r = NULL;
static void *g_stack_init = NULL;
static long int g_peak_stack_size = 0;

void profile_stack() {self.sub_oc}
    {self.sub_co} Dynamic memory allocation within function gets placed on
    stack
    char stack_top;
    if (g_stack_init == NULL) {self.sub_oc}
        g_stack_init = &stack_top;
        g_stack_top = &stack_top;
    {self.sub_cc}
    if (g_stack_ptr_r != NULL) {self.sub_oc}
        if (g_stack_ptr_r < &stack_top && !g_stack_grows_up_init_done) {self.sub_oc}
            g_stack_grows_up = 1;
            g_stack_grows_up_init_done = 1;
        {self.sub_cc} else if (!g_stack_grows_up_init_done) {self.sub_oc}
            g_stack_grows_up = 0;
            g_stack_grows_up_init_done = 1;
        {self.sub_cc}
        if (g_stack_grows_up && g_stack_top < &stack_top ||
           !g_stack_grows_up && g_stack_top > &stack_top) {self.sub_oc}
            g_stack_top = &stack_top;
            if (g_stack_grows_up) {self.sub_oc}
                g_peak_stack_size = g_stack_top - g_stack_init;
            {self.sub_cc} else {self.sub_oc}
                g_peak_stack_size = g_stack_init - g_stack_top;
            {self.sub_cc}
            printf("New stack height: %ld{self.sub_nl}", g_peak_stack_size);
            printf("Current stack pointer: %p{self.sub_nl}", &stack_top);
        {self.sub_cc}
    {self.sub_cc}
    g_stack_ptr_r = &stack_top;
{self.sub_cc}
#endif
"""

        # Always defined
        c_barrett_reduction = \
f"""
{self.ntt_parameters.mod_type} barrett_reduce({self.ntt_parameters.mod_prod_type} a) {self.sub_oc}
  {self.ntt_parameters.barrett_q_type} q;
  {self.ntt_parameters.barrett_q_type} t;
  q = (a*({self.ntt_parameters.barrett_q_type}){self.ntt_parameters.barrett_r}) >> {self.ntt_parameters.barrett_k};
  t = a - (q * {self.ntt_parameters.mod});
  t = t >= {self.ntt_parameters.mod} ? t - {self.ntt_parameters.mod} : t;
  return ({self.ntt_parameters.mod_type}) t;
{self.sub_cc}
"""

        c_barrett_reduction_avx = ""
        if self.search_space_point.is_avx:
# TODO what to do about type extension here if we go from int to long int?? With a big modulus
            c_barrett_reduction_avx = \
f"""
__m{self.avx_width_str}i barrett_reduce_avx(__m{self.avx_width_str}i a) {self.sub_oc}
  __m{self.avx_width_str}i barrett_r_avx = _mm{self.avx_width_str}_set1_epi{self.ntt_parameters.mod_prod_trunc}({self.ntt_parameters.barrett_r});
  __m{self.avx_width_str}i mod_avx = _mm{self.avx_width_str}_set1_epi{self.ntt_parameters.mod_prod_trunc}({self.ntt_parameters.mod});
  __m{self.avx_width_str}i q, t;

  {self.sub_co} Calculate q = (a * barrett_r) >> barrett_k;
  q = _mm{self.avx_width_str}_mullo_epi{self.ntt_parameters.mod_prod_trunc}(a, barrett_r_avx);
  q = _mm{self.avx_width_str}_srli_epi{self.ntt_parameters.mod_prod_trunc}(q, {self.ntt_parameters.barrett_k});

  {self.sub_co} Calculate t = a - (q * mod);
  t = _mm{self.avx_width_str}_mullo_epi{self.ntt_parameters.mod_prod_trunc}(q, mod_avx);
  t = _mm{self.avx_width_str}_sub_epi{self.ntt_parameters.mod_prod_trunc}(a, t);

  {self.sub_co} Check if t is greater than or equal to mod
  __m{self.avx_width_str}i cmp = _mm{self.avx_width_str}_cmpgt_epi{self.ntt_parameters.mod_prod_trunc}(t, mod_avx);
  t = _mm{self.avx_width_str}_sub_epi{self.ntt_parameters.mod_prod_trunc}(t, _mm{self.avx_width_str}_and_si{self.avx_width_str}(cmp, mod_avx));
  return t;
{self.sub_cc}
"""

        # Reduces the LUT mapping i*j instead of doing the mod operation
        c_power_barrett_reduction = \
f"""
{self.ntt_parameters.n_type} barrett_reduce_pow({self.ntt_parameters.n_prod_type} a) {self.sub_oc}
  {self.ntt_parameters.barrett_q_pow_type} q;
  {self.ntt_parameters.n_type} t;
  q = (a*({self.ntt_parameters.barrett_q_pow_type}){self.ntt_parameters.barrett_r_pow}) >> {self.ntt_parameters.barrett_k_pow};
  t = a - ({self.ntt_parameters.n_type}) (q * {self.ntt_parameters.n});
  t = t >= {self.ntt_parameters.n} ? t - {self.ntt_parameters.n} : t;
  return t;
{self.sub_cc}
"""
        c_a_pow_b_mod_m = \
f"""
{self.ntt_parameters.mod_type} a_pow_b_mod_m({self.ntt_parameters.mod_type} a, {self.ntt_parameters.mod_type} b) {self.sub_oc}
    {self.ntt_parameters.mod_type} abm = 1;
    for ({self.ntt_parameters.mod_type} i = 0; i < b; i++) {self.sub_oc}
        abm = barrett_reduce(abm * a);
    {self.sub_cc}
    return abm;
{self.sub_cc}
"""
        # Populated and used by FAST MR
        if self.search_space_point.type_str == "TYPE_FAST" and self.search_space_point.mixed_radix:
            c_prime_fact_lut = \
f"""
static const {self.ntt_parameters.mod_type} g_stat_prime_factors[{len(self.ntt_parameters.prime_factorization)}] = {self.sub_oc}
"""
            for i in range(len(self.ntt_parameters.prime_factorization)-1):
                c_prime_fact_lut += f"\t{self.ntt_parameters.prime_factorization[i]}, \n"
            c_prime_fact_lut += f"\t{self.ntt_parameters.prime_factorization[len(self.ntt_parameters.prime_factorization)-1]}\n"
            c_prime_fact_lut += \
f"""
{self.sub_cc};
"""
        else:
            # Not defined for non-mixed
            c_prime_fact_lut = ""

        if self.search_space_point.is_lut:
            # Defined and populated if LUT approach used
            c_static_pow_lut = \
f"""
static const {self.ntt_parameters.mod_type} g_stat_twiddle_pows[{self.ntt_parameters.n}] = {self.sub_oc}
"""
            # Power lut entries
            running_pow = 1
            for i in range(self.ntt_parameters.n-1):
                c_static_pow_lut += f"\t{running_pow}, \n"
                running_pow = (running_pow * self.ntt_parameters.g) % self.ntt_parameters.mod
            c_static_pow_lut += f"\t{running_pow} \n"
            c_static_pow_lut += \
f"""
{self.sub_cc};
"""
            c_static_inv_pow_lut = \
f"""
static const {self.ntt_parameters.mod_type} g_stat_inv_twiddle_pows[{self.ntt_parameters.n}] = {self.sub_oc}
"""
            # Power lut entries
            running_pow = 1
            for i in range(self.ntt_parameters.n-1):
                c_static_inv_pow_lut += f"\t{running_pow}, \n"
                running_pow = (running_pow * nt.modinv(self.ntt_parameters.g, self.ntt_parameters.mod)) % self.ntt_parameters.mod
            c_static_inv_pow_lut += f"\t{running_pow} \n"
            c_static_inv_pow_lut += \
f"""
{self.sub_cc};
"""
        else:
            c_static_pow_lut = ""
            c_static_inv_pow_lut = ""

        c_ntt_impl_tot_str = c_barrett_reduction + \
                             c_barrett_reduction_avx + \
                             c_power_barrett_reduction + \
                             c_a_pow_b_mod_m + \
                             c_prime_fact_lut + \
                             c_static_pow_lut + \
                             c_static_inv_pow_lut

        c_ntt_str = ""
        if self.search_space_point.is_pthread:
            c_ntt_str += \
f"""
typedef struct {self.sub_oc}
    int thread_id;
    int start_row;
    int end_row;
    {self.ntt_parameters.mod_type} *x;
    {self.ntt_parameters.mod_type} *y;
{self.sub_cc} thread_data_t;
"""
        c_ntt_str += self.generate_ntt_func(self.ntt_parameters, True)
        # Always at least a forward implemenation
        # Build flags will insert ternary if needed
        if (self.search_space_point.separate_inv_impl):
            inv_ntt_parameters = self.ntt_parameters
            # Obtain inverted generator
            inv_ntt_parameters.g = nt.modinv(self.ntt_parameters.g, self.ntt_parameters.mod)
            c_ntt_str += self.generate_ntt_func(inv_ntt_parameters, False)
        else:
            # If no separate inv impl then build a function wrapper for ntt_inv that goes to ntt_fwd
            c_ntt_str += \
f"""
void ntt_impl_inv({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.recursive_str} uint8_t inv) {self.sub_oc}
    {self.sub_co} The illusion of choice
    ntt_impl(x, y, {self.recursive_call_str} 1);
{self.sub_cc}
"""
        c_ntt_impl_tot_str += c_ntt_str
        with open(self.c_target_name, "w") as file:
            file.write("#include \"ntt_target.h\"\n")
            file.write(c_ntt_impl_tot_str)

    # May be used to generate either 1 or 2 NTT functions based on
    # if we decide to do one function with switch statements or two entirely
    # different functions
    # RETURN: Ntt function implementation string
    def generate_ntt_func(self, ntt_parameters, forward_impl):
        # Build a big ol string
        ntt_impl_string = ""

        c_ntt_impl_func_proto =  ""
        if (forward_impl):
            c_ntt_impl_func_proto = \
f"""ntt_impl({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.recursive_str} uint8_t inv)"""
        else:
            c_ntt_impl_func_proto = \
f"""ntt_impl_inv({self.ntt_parameters.mod_type} *x, {self.ntt_parameters.mod_type} *y, {self.recursive_str} uint8_t inv)"""
        c_ntt_common_func_header = "void " + c_ntt_impl_func_proto + " {\n"

        ############################################################
        # String substitutions into general loop structure for N2
        ############################################################
        c_N2_omp_pragma = ""
        if self.search_space_point.is_omp:
            c_N2_omp_pragma = \
f"""
{self.sub_pc}pragma omp parallel for
"""

        # Initialize AVX sums fo rthe inner loop
        c_N2_avx_init = ""
        c_N2_inner_loop_structure = ""
        c_N2_avx_reg_accum = ""
        c_N2_avx_parallel_init = ""
        if self.search_space_point.is_avx:
            if self.search_space_point.is_omp:
                c_N2_avx_parallel_init = \
f"""
        __m{self.avx_width_str}i avx_result, avx_reduction, vec_a, vec_b;
        {self.ntt_parameters.mod_prod_type} avx_twiddle_arr[{self.avx_reg_width}];
        {self.ntt_parameters.mod_prod_type} hsum[{self.avx_reg_width}];
        {self.ntt_parameters.mod_prod_type} temp_sum;
        uint8_t avx_load_cntr = 0;
"""
            else:
                c_N2_avx_init = \
f"""
    __m{self.avx_width_str}i avx_result, avx_reduction, vec_a, vec_b;
    {self.ntt_parameters.mod_prod_type} avx_twiddle_arr[{self.avx_reg_width}];
    {self.ntt_parameters.mod_prod_type} hsum[{self.avx_reg_width}];
    {self.ntt_parameters.mod_prod_type} temp_sum;
    uint8_t avx_load_cntr = 0;
"""
            c_N2_avx_reg_accum = \
f"""
            {self.sub_co} If on last of a block of 8 or if on last iteration of loop for non multiple of 8 dimension
            if (avx_load_cntr == {self.avx_reg_width}) {self.sub_oc}
                // Load AVX
                vec_a = _mm{self.avx_width_str}_loadu_si{self.avx_width_str}((__m{self.avx_width_str}i*)avx_twiddle_arr);
                vec_b = _mm{self.avx_width_str}_loadu_si{self.avx_width_str}((__m{self.avx_width_str}i*)&x[j - {self.avx_reg_width-1}]);
                // Perform AVX operation
                avx_result = _mm{self.avx_width_str}_mullo_epi{self.ntt_parameters.mod_prod_trunc}(vec_a, vec_b);
                // Perform AVX reduction
                avx_result = barrett_reduce_avx(avx_result);
                _mm{self.avx_width_str}_storeu_si{self.avx_width_str}((__m{self.avx_width_str}i*)hsum, avx_result);
                temp_sum = 0;
                for (uint8_t i = 0; i < {self.avx_reg_width}; i++) {self.sub_oc}
                    temp_sum += hsum[i];
                {self.sub_cc}
                y[i] = y[i] + temp_sum;
                // Reduce vector component-wise sum
                y[i] = barrett_reduce(y[i]);
                avx_load_cntr = 0;
            {self.sub_cc}
"""
        else:
            c_N2_inner_loop_structure = \
f"""
"""

        c_N2_no_lut_twiddle_def = ""
        c_N2_inner_twiddle_init = ""
        c_N2_inner_impl = ""
        c_N2_outer_twiddle_incr = ""

        if not self.search_space_point.is_lut:
            c_N2_inner_twiddle_init = \
f"""
        twiddle = 1;
"""
            c_N2_no_lut_twiddle_def = \
f"""
    {ntt_parameters.mod_type} twiddle = 1;
    {ntt_parameters.mod_type} twiddle_fact = 1; {self.sub_co} Geometrically increasing factor in each loop iteration
    {ntt_parameters.mod_type} temp;
"""
            if self.search_space_point.is_avx:
                c_N2_inner_impl = \
f"""
            twiddle = j == 0 ? 1 : barrett_reduce(twiddle * twiddle_fact);
            avx_twiddle_arr[avx_load_cntr++] = twiddle;
"""
            else:
                c_N2_inner_impl = \
f"""
            twiddle = j == 0 ? 1 : barrett_reduce(twiddle * twiddle_fact);
            temp = barrett_reduce(x[j] * twiddle);
            y[i] = y[i] + temp >= {ntt_parameters.mod} ? y[i] + temp - {ntt_parameters.mod} : y[i] + temp;
"""
            if self.search_space_point.separate_inv_impl:
                c_N2_outer_twiddle_incr = \
f"""
        twiddle_fact = barrett_reduce(twiddle_fact * {ntt_parameters.g});
"""
                
            else:
                c_N2_outer_twiddle_incr = \
f"""
        twiddle_fact = barrett_reduce(twiddle_fact * (inv ? {ntt_parameters.g_inv} : {ntt_parameters.g}));
"""
        # LUT BASED
        else:
            if self.search_space_point.separate_inv_impl:
                if forward_impl:
                    if self.search_space_point.is_avx:
                        c_N2_inner_impl = \
f"""
            avx_twiddle_arr[avx_load_cntr++] = g_stat_twiddle_pows[barrett_reduce_pow(i*j)];
"""
                    else:
                        c_N2_inner_impl = \
f"""
            {ntt_parameters.mod_type} temp = barrett_reduce(x[j] * g_stat_twiddle_pows[barrett_reduce_pow(i*j)]);
            y[i] = y[i] + temp >= {ntt_parameters.mod} ? y[i] + temp - {ntt_parameters.mod} : y[i] + temp;
"""
                else:
                    if self.search_space_point.is_avx:
                        c_N2_inner_impl = \
f"""
            avx_twiddle_arr[avx_load_cntr++] = g_stat_inv_twiddle_pows[barrett_reduce_pow(i*j)];
"""
                    else:
                        c_N2_inner_impl = \
f"""
            {ntt_parameters.mod_type} temp = barrett_reduce(x[j] * g_stat_inv_twiddle_pows[barrett_reduce_pow(i*j)]);
            y[i] = y[i] + temp >= {ntt_parameters.mod} ? y[i] + temp - {ntt_parameters.mod} : y[i] + temp;
"""
            else:
                if self.search_space_point.is_avx:
                    c_N2_inner_impl = \
f"""
            avx_twiddle_arr[avx_load_cntr++] = inv ? g_stat_inv_twiddle_pows[barrett_reduce_pow(i*j)] : g_stat_twiddle_pows[barrett_reduce_pow(i*j)];
"""
                else:
                    c_N2_inner_impl = \
f"""
            {ntt_parameters.mod_type} temp = barrett_reduce(x[j] * (inv ? g_stat_inv_twiddle_pows[barrett_reduce_pow(i*j)] : g_stat_twiddle_pows[barrett_reduce_pow(i*j)]));
            y[i] = y[i] + temp >= {ntt_parameters.mod} ? y[i] + temp - {ntt_parameters.mod} : y[i] + temp;
"""

        c_N2_pthread_impl = ""
        c_N2_pthread_manage = ""
        if self.search_space_point.is_pthread:
            c_N2_pthread_impl = \
f"""

void *{"thread_loop" if forward_impl else "thread_loop_inv"}(void *arg) {self.sub_oc}
    thread_data_t * thread_params = (thread_data_t *)arg;
    {self.ntt_parameters.mod_type} * x = thread_params->x;
    {self.ntt_parameters.mod_type} * y = thread_params->y;
    for ({self.ntt_parameters.n_type} i = thread_params->start_row; i < thread_params->end_row; i++) {self.sub_oc}
        {c_N2_avx_parallel_init}
        for ({self.ntt_parameters.n_type} j = 0; j < {ntt_parameters.n}; j++) {self.sub_oc}
            {c_N2_inner_impl}
            {c_N2_avx_reg_accum}
        {self.sub_cc}
    {self.sub_cc}
    pthread_exit(NULL);
{self.sub_cc}
"""
            c_N2_pthread_manage = \
f"""
    pthread_t threads[NUM_THREADS];
    thread_data_t thread_data[NUM_THREADS];
    for (uint8_t i = 0; i < NUM_THREADS; i++) {self.sub_oc}
        thread_data[i].thread_id = i;
        thread_data[i].start_row = i * {ntt_parameters.n}/NUM_THREADS;
        thread_data[i].end_row = (i == NUM_THREADS - 1) ? {ntt_parameters.n} : (i + 1) * ({ntt_parameters.n} / NUM_THREADS);
        thread_data[i].x = x;
        thread_data[i].y = y;
        pthread_create(&threads[i], NULL, {"thread_loop" if forward_impl else "thread_loop_inv""thread_loop" if forward_impl else "thread_loop_inv"}, &thread_data[i]);
    {self.sub_cc}
    {self.sub_co} Wait for threads to finish
    for (uint8_t i = 0; i < NUM_THREADS; i++) {self.sub_oc}
        pthread_join(threads[i], NULL);
    {self.sub_cc}
"""
        ############################################################

        c_N2 = ""
        if self.search_space_point.is_pthread:
            c_N2 = \
f"""
{c_N2_pthread_impl}
{c_ntt_common_func_header}
    {c_N2_pthread_manage}
"""
        else:
            c_N2 = \
f"""
{c_ntt_common_func_header}
    for ({ntt_parameters.n_type} i = 0; i < {ntt_parameters.n}; i++) {self.sub_oc}
        y[i] = 0;
    {self.sub_cc}
    {c_N2_no_lut_twiddle_def}
    {c_N2_avx_init}
    {c_N2_omp_pragma}
    for ({ntt_parameters.n_type} i = 0; i < {ntt_parameters.n}; i++) {self.sub_oc}
        {c_N2_avx_parallel_init}
        {c_N2_inner_twiddle_init}
        for ({ntt_parameters.n_type} j = 0; j < {ntt_parameters.n}; j++) {self.sub_oc}
            {c_N2_inner_impl}
            {c_N2_avx_reg_accum}
        {self.sub_cc}
        {c_N2_outer_twiddle_incr}
    {self.sub_cc}
"""
        ############################################################
        # String substitutions into general loop structure for N2
        ############################################################
        c_R2_half_rot_init = ""
        c_R2_stride_twiddle = ""
        c_R2_running_twiddle_1_init = ""
        c_R2_twiddle1_twiddle2_assign = ""

        if not self.search_space_point.is_lut:
            c_R2_running_twiddle_1_init = \
f"""
        running_twiddle_1 = 1;
"""
            c_R2_twiddle1_twiddle2_assign = \
f"""
                twiddle1 = running_twiddle_1;
                running_twiddle_1 = barrett_reduce(stride_twiddle * running_twiddle_1);
                {self.sub_co} Twiddle 2 is offset half a rotation from twiddle 1
                twiddle2 = barrett_reduce(twiddle1 * half_rot);
"""
            if self.search_space_point.separate_inv_impl:
                c_R2_half_rot_init = \
f"""
    {ntt_parameters.mod_type} half_rot = {nt.a_pow_b_mod_m(ntt_parameters.g, ntt_parameters.n>>1, ntt_parameters.mod)};
    {ntt_parameters.mod_type} stride_twiddle;
    {ntt_parameters.mod_type} running_twiddle_1;
"""
                c_R2_stride_twiddle = \
f"""
        stride_twiddle = a_pow_b_mod_m({ntt_parameters.g}, stride);
"""
            else:
                c_R2_half_rot_init = \
f"""
    {ntt_parameters.mod_type} half_rot = inv ? {nt.a_pow_b_mod_m(ntt_parameters.g_inv, ntt_parameters.n>>1, ntt_parameters.mod)} : {nt.a_pow_b_mod_m(ntt_parameters.g, ntt_parameters.n>>1, ntt_parameters.mod)};
    {ntt_parameters.mod_type} stride_twiddle;
    {ntt_parameters.mod_type} running_twiddle_1;
"""
                c_R2_stride_twiddle = \
f"""
        stride_twiddle = a_pow_b_mod_m((inv ? {ntt_parameters.g_inv} : {ntt_parameters.g}), stride);
"""

        else:
            if self.search_space_point.separate_inv_impl:
                if forward_impl:
                    c_R2_half_rot_init = \
f"""
    {ntt_parameters.mod_type} half_rot = g_stat_twiddle_pows[{ntt_parameters.n}>>1];
"""
                    c_R2_twiddle1_twiddle2_assign = \
f"""
                twiddle1 = g_stat_twiddle_pows[barrett_reduce_pow(sub_trans_idx*stride)];
                {ntt_parameters.n_type} temp = barrett_reduce_pow(sub_trans_idx*stride);
                twiddle2 = g_stat_twiddle_pows[temp + {ntt_parameters.n}>>1 > {ntt_parameters.n} ? temp + {ntt_parameters.n}>>1 - {ntt_parameters.n} : temp + {ntt_parameters.n}>>1];
"""

                else:
                    c_R2_half_rot_init = \
f"""
    {ntt_parameters.mod_type} half_rot = g_stat_inv_twiddle_pows[{ntt_parameters.n}>>1];
"""
                    c_R2_twiddle1_twiddle2_assign = \
f"""
                twiddle1 = g_stat_inv_twiddle_pows[barrett_reduce_pow(sub_trans_idx*stride)];
                {ntt_parameters.n_type} temp = barrett_reduce_pow(sub_trans_idx*stride);
                twiddle2 = g_stat_inv_twiddle_pows[temp + {ntt_parameters.n}>>1 > {ntt_parameters.n} ? temp + {ntt_parameters.n}>>1 - {ntt_parameters.n} : temp + {ntt_parameters.n}>>1];
"""

            else:
                c_R2_half_rot_init = \
f"""
    {ntt_parameters.mod_type} half_rot = inv ? g_stat_inv_twiddle_pows[{ntt_parameters.n}>>1] : g_stat_twiddle_pows[{ntt_parameters.n}>>1];
"""
                c_R2_twiddle1_twiddle2_assign = \
f"""
                twiddle1 = inv ? g_stat_inv_twiddle_pows[barrett_reduce_pow(sub_trans_idx*stride)] : g_stat_twiddle_pows[barrett_reduce_pow(sub_trans_idx*stride)];
                {ntt_parameters.n_type} temp = barrett_reduce_pow(sub_trans_idx*stride);
                {ntt_parameters.n_type} reduced_pow = temp + {ntt_parameters.n}>>1 > {ntt_parameters.n} ? temp + {ntt_parameters.n}>>1 - {ntt_parameters.n} : temp + {ntt_parameters.n}>>1;
                twiddle2 = inv ? g_stat_inv_twiddle_pows[reduced_pow] : g_stat_twiddle_pows[reduced_pow];
"""

        ############################################################

        c_fast_fixed_r2 = \
f"""
{c_ntt_common_func_header}
    {ntt_parameters.mod_type} t1, t2;
    {ntt_parameters.mod_type} twiddle1, twiddle2;
    {ntt_parameters.n_type} cur_size;
    {ntt_parameters.n_type} cur_idx;
    {self.sub_co} Copy x to y then do inplace
    for ({ntt_parameters.n_type} i = 0; i < {ntt_parameters.n}; i++) {self.sub_oc}
        y[i] = x[i];
    {self.sub_cc}
    {c_R2_half_rot_init}
    for ({ntt_parameters.n_type} stride = {ntt_parameters.n}>>1; stride >= 1; stride >>= 1) {self.sub_oc}
        cur_size = stride<<1;
        {c_R2_stride_twiddle}
        {c_R2_running_twiddle_1_init}
        {self.sub_co} For each of the "sub-transforms" in the CT butterfly
        for ({ntt_parameters.n_type} sub_trans_idx = 0; sub_trans_idx < {ntt_parameters.n}/cur_size; sub_trans_idx++) {self.sub_oc}
            {self.sub_co} We take steps within our sub transform
            {ntt_parameters.mod_type} temp;
            for ({ntt_parameters.n_type} step = 0; step < stride; step++) {self.sub_oc}
                cur_idx = sub_trans_idx*cur_size + step;
                {c_R2_twiddle1_twiddle2_assign}
                temp = barrett_reduce(y[cur_idx + stride] * twiddle2);
                y[cur_idx + stride] = y[cur_idx] + temp >= {ntt_parameters.mod} ? y[cur_idx] + temp - {ntt_parameters.mod} : y[cur_idx] + temp;
                temp = barrett_reduce(y[cur_idx + stride] * twiddle1);
                y[cur_idx] = y[cur_idx] + temp >= {ntt_parameters.mod} ? y[cur_idx] + temp - {ntt_parameters.mod} : y[cur_idx] + temp;
            {self.sub_cc}
        {self.sub_cc}
    {self.sub_cc}
"""

        ############################################################
        # String substitutions into general loop structure for 
        ############################################################

	    # Doesn't make sense to do mixed-radix recursive, since by definition
	    # Recursive is more memory intensive and thus

        c_r2_rec_func_call_0 = ""
        c_r2_rec_func_call_1 = ""
        if (forward_impl):
            c_r2_rec_func_call_0 = \
f"""ntt_impl(x_e, y_e, n>>1, n0, inv)"""
            c_r2_rec_func_call_1 = \
f"""ntt_impl(x_o, y_o, n>>1, n0, inv)"""
        else:
            c_r2_rec_func_call_0 = \
f"""ntt_impl_inv(x_e, y_e, n>>1, n0, inv)"""
            c_r2_rec_func_call_1 = \
f"""ntt_impl_inv(x_o, y_o, n>>1, n0, inv)"""

        c_r2_rec_butterfly_twiddle_1 = ""
        c_r2_rec_butterfly_twiddle_1_init = ""
        c_r2_rec_butterfly_twiddle_1_post_mult = ""

        if not self.search_space_point.is_lut:

            c_r2_rec_butterfly_twiddle_1_init = \
f"""
        {ntt_parameters.mod_type} twiddle = 1;
        {ntt_parameters.mod_type} adjusted_gen = a_pow_b_mod_m({ntt_parameters.g}, n0/n);
"""
            c_r2_rec_butterfly_twiddle_1 = \
f"twiddle"
            c_r2_rec_butterfly_twiddle_1_post_mult = \
f"""
            twiddle = barrett_reduce(twiddle * adjusted_gen);
"""

        else:
            if self.search_space_point.separate_inv_impl:
                if forward_impl:
                    c_r2_rec_butterfly_twiddle_1 = \
f"g_stat_twiddle_pows[barrett_reduce_pow((n0/n)*i)]"
                else:
                    c_r2_rec_butterfly_twiddle_1 = \
f"g_stat_inv_twiddle_pows[barrett_reduce_pow((n0/n)*i)]"
            else:
                c_r2_rec_butterfly_twiddle_1 = \
f"(inv ? g_stat_twiddle_pows[barrett_reduce_pow((n0/n)*i)] : g_stat_inv_twiddle_pows[barrett_reduce_pow((n0/n)*i)])"

        c_fast_fixed_r2_recursive = \
f"""
{c_ntt_common_func_header}
    if (n <= {self.search_space_point.recursive_base_case}) {self.sub_oc}
        {self.sub_co} Assume y allocated by caller
        {c_N2_no_lut_twiddle_def}
        {c_N2_avx_init}
        {c_N2_omp_pragma}
        for ({self.ntt_parameters.n_type} i = 0; i < n; i++) {self.sub_oc}
            {c_N2_avx_parallel_init}
            {c_N2_inner_twiddle_init}
            for ({self.ntt_parameters.n_type} j = 0; j < n; j++) {self.sub_oc}
                {self.sub_co} TODO below should have n0/n generator ratio
                {c_N2_inner_impl}
                {c_N2_avx_reg_accum}
            {self.sub_cc}
            {c_N2_outer_twiddle_incr}
        {self.sub_cc}
    {self.sub_cc} else {self.sub_oc}
        {self.ntt_parameters.mod_type} * x_e = malloc(n>>1 * sizeof({self.ntt_parameters.mod_type}));
        {self.ntt_parameters.mod_type} * x_o = malloc(n>>1 * sizeof({self.ntt_parameters.mod_type}));
        {self.ntt_parameters.mod_type} * y_e = calloc(n>>1 , sizeof({self.ntt_parameters.mod_type}));
        {self.ntt_parameters.mod_type} * y_o = calloc(n>>1 , sizeof({self.ntt_parameters.mod_type}));
        for ({self.ntt_parameters.n_type} j = 0; j < n>>1; j++) {self.sub_oc}
            x_e[j] = x[j<<1 + 0];
            x_o[j] = x[j<<1 + 1];
        {self.sub_cc}
        {self.sub_co} Recursive calls followed by twiddles
	    {c_r2_rec_func_call_0};
	    {c_r2_rec_func_call_1};
        {c_r2_rec_butterfly_twiddle_1_init}
        {self.sub_co} TODO should this be pragma'd?
        {c_N2_omp_pragma}
        for ({self.ntt_parameters.n_type} i = 0; i < n>>1; i++) {self.sub_oc}
            {self.ntt_parameters.mod_type} sum_0 = y_e[i] + y_o[i];
            {self.ntt_parameters.mod_type} sum_1 = y_e[i] + barrett_reduce({c_r2_rec_butterfly_twiddle_1}*y_o[i]);
            y[i]        = sum_0 >= {ntt_parameters.mod} ? sum_0 - {ntt_parameters.mod} : sum_0;
            y[i + n>>1] = sum_1 >= {ntt_parameters.mod} ? sum_1 - {ntt_parameters.mod} : sum_1;
            {c_r2_rec_butterfly_twiddle_1_post_mult}
        {self.sub_cc}
        {self.sub_co} free(x_e);
        {self.sub_co} free(x_o);
        {self.sub_co} free(y_e);
        {self.sub_co} free(y_o);
    {self.sub_cc}
"""

        ############################################################
        # String substitutions into general loop structure for 
        ############################################################

        c_MR_pow_defs = ""
        c_MR_base_ij_set = ""
        c_MR_common_pow_j_2_init = ""
        c_MR_common_pow_j_2_assn = ""
        c_MR_common_pow_i_2_init = ""
        c_MR_common_pow_i_2_assn = ""
        c_MR_common_pow_j_3_init = ""
        c_MR_assn_y = ""

        if not self.search_space_point.is_lut:
            c_MR_common_pow_j_2_init = \
f"""
            running_pow_j_2 = 1;
"""
            c_MR_common_pow_j_2_assn = \
f"""
            running_pow_j_2 = barrett_reduce(running_pow_j_2 * base_j_1);
"""
            c_MR_common_pow_i_2_init = \
f"""
                running_pow_i_2 = 1;
"""
            c_MR_common_pow_i_2_assn = \
f"""
                    running_pow_i_2 = barrett_reduce(running_pow_i_2 * base_i_1);
"""
            c_MR_common_pow_j_3_init = \
f"""
                    running_pow_j_3 = 1;
"""
            c_MR_pow_defs = \
f"""
    {ntt_parameters.mod_type} base_j_1; {self.sub_co} With n_cur/DIM
    {ntt_parameters.mod_type} running_pow_j_2; {self.sub_co} With above ^ni
    {ntt_parameters.mod_type} running_pow_j_3; {self.sub_co} With above ^butterfly_j
    {ntt_parameters.mod_type} base_i_1; {self.sub_co} With dim/g_stat_prime_factors[fact_cnt]
    {ntt_parameters.mod_type} running_pow_i_2; {self.sub_co} With above ^butterfly_i
"""
            c_MR_assn_y = \
f"""
                        {ntt_parameters.mod_type} red1 = barrett_reduce(running_pow_j_3 * running_pow_i_2);
                        {ntt_parameters.mod_type} red2 = barrett_reduce(red2 * y_t[butterfly_j]);
                        y[dst_idx] =  (y[dst_idx] + red2) > {ntt_parameters.mod} ? (y[dst_idx] + red2) - {ntt_parameters.mod} : (y[dst_idx] + red2);
                        running_pow_j_3 = barrett_reduce(running_pow_j_3 * running_pow_j_2);
"""
            if self.search_space_point.separate_inv_impl:
                c_MR_base_ij_set = \
f"""
            base_j_1 = a_pow_b_mod_m({ntt_parameters.g}, n_cur/{ntt_parameters.n});
            base_i_1 = a_pow_b_mod_m({ntt_parameters.g}, n_cur/g_stat_prime_factors[fact_cnt]);
"""
            else:
                c_MR_base_ij_set = \
f"""
            base_j_1 = a_pow_b_mod_m((inv ? {ntt_parameters.g_inv} : {ntt_parameters.g}), n_cur/{ntt_parameters.n});
            base_i_1 = a_pow_b_mod_m((inv ? {ntt_parameters.g_inv} : {ntt_parameters.g}), n_cur/g_stat_prime_factors[fact_cnt]);
"""
        else:
            if self.search_space_point.separate_inv_impl:
                if forward_impl:
                    c_MR_assn_y = \
f"""
                        y[dst_idx] =  barrett_reduce(y[dst_idx] + y_t[butterfly_j] * g_stat_twiddle_pows[barrett_reduce_pow((n_cur/{ntt_parameters.n})*ni*butterfly_j + (butterfly_i * {ntt_parameters.n}/g_stat_prime_factors[fact_cnt]))]);
"""
                else:
                    c_MR_assn_y = \
f"""
                        y[dst_idx] =  barrett_reduce(y[dst_idx] + y_t[butterfly_j] * g_stat_inv_twiddle_pows[barrett_reduce_pow((n_cur/{ntt_parameters.n})*ni*butterfly_j + (butterfly_i * {ntt_parameters.n}/g_stat_prime_factors[fact_cnt]))]);
"""
            else:
                c_MR_assn_y = \
f"""
                        y[dst_idx] =  barrett_reduce(y[dst_idx] + y_t[butterfly_j] * (inv ? g_stat_inv_twiddle_pows[barrett_reduce_pow((n_cur/{ntt_parameters.n})*ni*butterfly_j + (butterfly_i * {ntt_parameters.n}/g_stat_prime_factors[fact_cnt]))] : g_stat_twiddle_pows[barrett_reduce_pow((n_cur/{ntt_parameters.n})*ni*butterfly_j + (butterfly_i * {ntt_parameters.n}/g_stat_prime_factors[fact_cnt]))]));
"""

        ############################################################
        # TODO how to avoid non-constant iterator over prime factors?
        # Is a static const sufficient?
        c_fast_mr = \
f"""
{c_ntt_common_func_header}
    {ntt_parameters.mod_type} t;
    {ntt_parameters.mod_type} twiddle;
    {ntt_parameters.n_type} n_cur = {ntt_parameters.n};
    {ntt_parameters.n_type} orig_size = {ntt_parameters.n};
    uint8_t fact_cnt = 0;
    {ntt_parameters.n_type} n2 = n_cur/g_stat_prime_factors[fact_cnt];
    {ntt_parameters.n_type} dst_idx;
    {self.sub_co} Copy x to y then do inplace
    for ({ntt_parameters.n_type} i = 0; i < {ntt_parameters.n}; i++) {self.sub_oc}
        y[i] = x[i];
    {self.sub_cc}
    {c_MR_pow_defs}
    {self.sub_co} for ({ntt_parameters.n_type} n2 = n_cur/g_stat_prime_factors[fact_cnt]; n2 >= 1; n2 /= (g_stat_prime_factors[fact_cnt])) {self.sub_oc}
    {self.sub_co} Iterates over prime factors. Termination at bottom of loop
    {self.sub_while} (1) {self.sub_oc}
        {self.sub_co} For each of the "sub-transforms" in the CT butterfly
        for ({ntt_parameters.n_type} n1 = 0; n1 < orig_size/n_cur; n1++) {self.sub_oc}
            {c_MR_common_pow_j_2_init}
            {c_MR_base_ij_set}
            {self.sub_co} We take steps within our self.sub transform
            for ({ntt_parameters.n_type} ni = 0; ni < n2; ni++) {self.sub_oc}
                {self.sub_co} TODO any way around this dynamic memory allocation?
                {ntt_parameters.mod_type} *y_t = calloc(g_stat_prime_factors[fact_cnt], sizeof({self.ntt_parameters.mod_type}));
                for ({ntt_parameters.n_type} butterfly_i = 0; butterfly_i < g_stat_prime_factors[fact_cnt]; butterfly_i++) {self.sub_oc}
                    dst_idx = n1*n_cur + ni + butterfly_i*n2;
                    y_t[butterfly_i] = y[dst_idx]; {self.sub_co} Temp save
                {self.sub_cc}
                {self.sub_co} We have N^2 terms to add where N is the prime factor
                {self.sub_co} Since N sums into each N node of the self.sub transform
                {c_MR_common_pow_i_2_init}
                for ({ntt_parameters.n_type} butterfly_i = 0; butterfly_i < g_stat_prime_factors[fact_cnt]; butterfly_i++) {self.sub_oc}
                    {c_MR_common_pow_j_3_init}
                    for ({ntt_parameters.n_type} butterfly_j = 0; butterfly_j < g_stat_prime_factors[fact_cnt]; butterfly_j++) {self.sub_oc}
                        dst_idx = n1*n_cur + ni + butterfly_i*n2;
                        {c_MR_assn_y}
                    {self.sub_cc}
                    {c_MR_common_pow_i_2_assn}
                {self.sub_cc}
                free(y_t);
            {self.sub_cc}
            {c_MR_common_pow_j_2_assn}
        {self.sub_cc}
        {self.sub_co} Size for next iter
        n_cur = n2;
        fact_cnt++;
        if (fact_cnt >= {len(ntt_parameters.prime_factorization)}) {self.sub_oc}
            break;
        {self.sub_cc}
        n2 /= (g_stat_prime_factors[fact_cnt]);
    {self.sub_cc}
"""

        if self.search_space_point.type_str == "TYPE_N2":
            ntt_impl_string += c_N2
        else: # TYPE_FAST
            if self.search_space_point.fixed_radix:
                if self.search_space_point.is_recursive:
                    ntt_impl_string += c_fast_fixed_r2_recursive
                else:
                    ntt_impl_string += c_fast_fixed_r2
            else:
                ntt_impl_string += c_fast_mr


        c_ntt_impl_func_end = \
f"""
{self.sub_cc} {self.sub_co} End ntt_impl
"""
        ntt_impl_string += c_ntt_impl_func_end
        return ntt_impl_string

    def __init__(self, search_space_point):
        self.search_space_point = search_space_point
        self.ntt_parameters = search_space_point.ntt_parameters
        # For FAST implemenations, check the prime factorizaiton and
        # expand the dimension as needed
        if (self.search_space_point.type_str == "TYPE_FAST"):
            dimension = self.ntt_parameters.n
            vp.vprint("Original dimension of " +  str(dimension))
            while max(self.ntt_parameters.prime_factorization) > self.search_space_point.max_mixed_radix:
                dimension += 1
                self.ntt_parameters = nt.NTT_Params(dimension)
            vp.vprint("Dimension expanded to " + str(dimension))
        self.avx_width_str = ""
        avx_temp = 256
        if self.search_space_point.is_avx2:
            avx_temp = 256
            self.avx_width_str = str(avx_temp)
        if self.search_space_point.is_avx512:
            avx_temp = 512
            self.avx_width_str = str(avx_temp)
        if self.ntt_parameters.mod_prod_type == "uint8_t":
            self.avx_reg_width = int(avx_temp/8)
        elif self.ntt_parameters.mod_prod_type == "uint16_t":
            self.avx_reg_width = int(avx_temp/16)
        elif self.ntt_parameters.mod_prod_type == "uint32_t":
            self.avx_reg_width = int(avx_temp/32)

        if (self.search_space_point.type_str == "TYPE_N2" and self.search_space_point.is_avx):
            # For AVX, expand to multiple of avx reg width
            vp.vprint("Original dimension of " + str(self.ntt_parameters.n))
            self.ntt_parameters = nt.NTT_Params(self.avx_reg_width * int(math.ceil(self.ntt_parameters.n / self.avx_reg_width)))
            vp.vprint("Dimension expanded to " + str(self.ntt_parameters.n))
            # For AVX, we also need to use the X and Y variables on the same
            # width as the product - i.e. the width gets doubled. This prevents
            # overflow when doing AVX mulitplication
            self.ntt_parameters.mod_type = self.ntt_parameters.mod_prod_type
            self.ntt_parameters.mod_trunc = self.ntt_parameters.mod_prod_trunc
            self.ntt_parameters.mod_width = self.ntt_parameters.mod_prod_width

