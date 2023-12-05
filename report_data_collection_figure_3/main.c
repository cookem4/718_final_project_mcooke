#include <time.h>
#include "ntt.h"

#if DO_TIME
#include <sys/time.h>
#endif

int main() {
    // init_ntt();
    // Seed RND
    srand(time(NULL));

    ntt_ctx fwd_ctx, inv_ctx;
    fwd_ctx.is_fwd = 1;
    inv_ctx.is_fwd = 0;
    // Expand dimension via padding for non-power-of-2 for fast
    // ntt with fixed radix of 2
#if FAST_FIXED == 1
    fwd_ctx.size = 1<<clog2(DIM);
    inv_ctx.size = 1<<clog2(DIM);
#else
    fwd_ctx.size = DIM;
    inv_ctx.size = DIM;
#endif
    // Get the prime factors for this dimension
    fwd_ctx.prime_factors = get_prime_factors(fwd_ctx.size, &fwd_ctx.prime_factor_size);
#if NTT_TYPE == TYPE_FAST && FAST_MIXED == 1
    // Pad sequence until largest factor is less than or equal to 5
    int largest_prime_fact;
    do {
        largest_prime_fact = fwd_ctx.prime_factors[0];
        for (int i = 1; i < fwd_ctx.prime_factor_size; i++) {
            if (largest_prime_fact < fwd_ctx.prime_factors[i]) {
                largest_prime_fact = fwd_ctx.prime_factors[i];
            }
        }
        if (largest_prime_fact > MAX_RADIX) {
            free(fwd_ctx.prime_factors);
            fwd_ctx.size++;
            inv_ctx.size++;
            fwd_ctx.prime_factors = get_prime_factors(fwd_ctx.size, &fwd_ctx.prime_factor_size);
        }
    } while (largest_prime_fact > MAX_RADIX);
#endif
    inv_ctx.prime_factors = fwd_ctx.prime_factors;
    inv_ctx.prime_factor_size = fwd_ctx.prime_factor_size;
    get_ntt_params(fwd_ctx.size, &fwd_ctx.mod, &fwd_ctx.w);
    inv_ctx.mod = fwd_ctx.mod;
    inv_ctx.w = modinv(fwd_ctx.w, fwd_ctx.mod);
    printf("Running NTT type %d, N = %d, mod = %d, g = %d, ginv = %d\n", NTT_TYPE, fwd_ctx.size, fwd_ctx.mod, fwd_ctx.w, inv_ctx.w);
    printf("Prime factors: ");
    for (int i = 0; i < fwd_ctx.prime_factor_size-1; i++) {
        printf("%d, ", fwd_ctx.prime_factors[i]);
    }
    printf("%d\n", fwd_ctx.prime_factors[fwd_ctx.prime_factor_size-1]);
    fwd_ctx.barrett_k = 2*clog2(fwd_ctx.mod);
    fwd_ctx.barrett_r = ((1 << fwd_ctx.barrett_k)/fwd_ctx.mod);
    inv_ctx.barrett_k = fwd_ctx.barrett_k;
    inv_ctx.barrett_r = fwd_ctx.barrett_r;
#if LUT_BASED == 1
    populate_pows_lut(&fwd_ctx, &inv_ctx);
#elif CACHE_BASED == 1
    init_cache();
#endif
    int in_seq_fwd[fwd_ctx.size];
    for (int i = 0; i < fwd_ctx.size; i++) {
        // in_seq_fwd[i] = rand() % fwd_ctx.mod;
        in_seq_fwd[i] = i;
    }
    fwd_ctx.in_seq = in_seq_fwd;
#if DO_TIME
    struct timeval start, end;
    double elapsed_time;
    gettimeofday(&start, NULL);
    int check_res = ntt_check(&fwd_ctx, &inv_ctx);
    gettimeofday(&end, NULL);
    elapsed_time = (end.tv_sec - start.tv_sec)*1e6 + (end.tv_usec - start.tv_usec);
    printf("TIME: %0.0f us\n", elapsed_time);
#else
    int check_res = ntt_check(&fwd_ctx, &inv_ctx);
#endif
    if (!check_res) {
        #if FAIL_PRINT_INFO
        printf("FWD IN:\n");
        for (int i = 0; i < fwd_ctx.size; i++) {
            printf("%d, ", fwd_ctx.in_seq[i]);
        }
        printf("\nFWD OUT:\n");
        for (int i = 0; i < fwd_ctx.size; i++) {
            printf("%d, ", fwd_ctx.out_seq[i]);
        }
        printf("\nINV(FWD):\n");
        for (int i = 0; i < fwd_ctx.size; i++) {
            printf("%d, ", inv_ctx.out_seq[i]);
        }
        printf("\n FAIL\n");
        #else
        printf("FAIL\n");
        #endif
    } else {
        printf("PASS\n");
    }
    return 0;
}
