#include "ntt.h" 

// TODO this is useless -> memory is reported in pages which is huge for this
// use-case
#if DO_HEAP == 1

#include <unistd.h>
#include <string.h>

size_t g_start_heap;
size_t g_peak_heap;

void get_heap() {
    FILE *fp;

    // Open the /proc/self/statm file for reading
    fp = fopen("/proc/self/statm", "r");

    if (fp == NULL) {
        perror("Error opening /proc/self/statm");
    }

    // Read the contents of the file
    char buffer[256];  // Adjust the buffer size as needed
    long page_size = sysconf(_SC_PAGESIZE);
    if (fgets(buffer, sizeof(buffer), fp) != NULL) {
        // Split the content into fields based on spaces
        char *token;
        token = strtok(buffer, " ");

        // The second field (index 1) represents the RSS, which includes the heap size
        if (token != NULL) {
            token = strtok(NULL, " "); // Move to the second field
            if (token != NULL) {
                // Convert the RSS value to an integer (heap size in pages)
                int rss = atoi(token);

                // Calculate the heap size in bytes
                size_t heapSizeBytes = rss * page_size;

                printf("Heap Size: %lu bytes\n", heapSizeBytes);
            }
        }
    } else {
        perror("Error reading /proc/self/statm");
    }

    // Close the file
    fclose(fp);
}

#endif

// Comparison function for qsort
int compare(const void *a, const void *b) {
    // Cast the void pointers to the correct data type (int*)
    int int_a = *((int*)a);
    int int_b = *((int*)b);

    // Compare the integers
    return int_b - int_a;
}

// Function to sort an array using qsort
void sort(int *x, size_t size) {
    qsort(x, size, sizeof(int), compare);
}

int clog2(long int in) {
    int count = 0;
    in--; // For powers of 2
    while (in > 0) {
        in >>= 1;
        count++;
    }
    return count;
}

int a_pow_b_mod_m(int a, int b, int m) {
    int abm = 1;
    for (int i = 0; i < b; i++) {
        abm = (abm * a) % m;
    }
    return abm;
}

int is_prime(int n) {
    if ((n & 1) == 0) {
        return 0;
    }
    int d = 3;
    while (d * d <= n) {
        if (n % d == 0)
            return 0;
        d = d + 2;
    }
    return n == 1 ? 0 : 1;
}

int * get_prime_factors(int n, int *prime_factor_size) {
    // Max number of prime factors is 2^^clog2(n)
    int ret_idx = 0;
    int *ret = calloc(clog2(n), sizeof(int));
    int fact = 2;
    while (n > 1) {
        if (n % fact == 0) {
            ret[ret_idx] = fact;
            n /= fact;
            fact = 2; // Reset factor
            ret_idx++;
        } else {
            fact++;
        }
    }
    *prime_factor_size = ret_idx;
    // Sort the prime largest to smallest
    sort(ret, (size_t) ret_idx);
    return ret;
}

void get_ntt_params(int n, int * mod, int * g) {
    int k = 2;
    while (1) {
        *mod = n*k + 1;
        if (is_prime(*mod)) {
            break;
        } else {
            k++;
        }
    }
    int good_pow;
    int running_pow;
    for (int i = 2; i < *mod; i++) {
        good_pow = 1;
        running_pow = i;
        for (int j = 2; j <= n; j++) {
            running_pow = (running_pow * i) % *mod;
            if (running_pow == 1 && j != n) {
                good_pow = 0;
                break;
            }
        }
        if (running_pow == 1 && good_pow) {
            *g = i;
            break;
        }
    }
}

int modinv(int a, int m) {
    int q, t, r, newt, newr, tempt, tempr;
    t = 0;
    newt = 1;
    r = m;
    newr = a;
    while (newr != 0) {
        q = r / newr;
        tempt = newt;
        tempr = newr;
        newt = t - q*newt;
        newr = r - q*newr;
        t = tempt;
        r = tempr;
    }
    if (t < 0) {
        t += m;
    }
    return t;
}

int barrett_reduce(int a, ntt_ctx *ctx) {
  long int q, t;
  q = ((long int) a*ctx->barrett_r) >> ctx->barrett_k;
  t = (long int) a - (q * ctx->mod);
  t = t >= (long int) ctx->mod ? t - (long int) ctx->mod : t;
  return (int) t;
}

#if LUT_BASED == 1
static int * g_gen_pows;
static int * g_inv_gen_pows;

void populate_pows_lut(ntt_ctx * fwd_ctx, ntt_ctx * inv_ctx) {
    g_gen_pows = malloc(DIM * sizeof(int));
    g_inv_gen_pows = malloc(DIM * sizeof(int));
    int cur_g = 1;
    int cur_g_inv = 1;
    for (int i = 0; i < DIM; i++) {
        g_gen_pows[i] = cur_g;
        g_inv_gen_pows[i] = cur_g_inv;
        cur_g = barrett_reduce(cur_g * fwd_ctx->w, fwd_ctx);
        cur_g_inv = barrett_reduce(cur_g_inv * inv_ctx->w, inv_ctx);
    }
}
#endif

#if CACHE_BASED == 1

static int * g_gen_pows_cache;
static char * g_cache_pow_idx; // Small Tag

// Place cache on heap based on DIM
void init_cache() {
    g_gen_pows_cache = malloc((DIM/CACHE_RATIO) * sizeof(int));
    g_cache_pow_idx = malloc((DIM/CACHE_RATIO) * sizeof(char));
    // Init tags to -1
    for (int i = 0; i < DIM/CACHE_RATIO; i++) {
        g_cache_pow_idx[i] = -1;
    }
}

#endif

// Use barrett reduction instead of mod
#if NTT_TYPE == TYPE_N2 && LUT_BASED == 0 && CACHE_BASED == 0
void ntt_impl(ntt_ctx * ctx) {
  int *s  = malloc(ctx->size * sizeof(int));
  int twiddle = 1;
  int twiddle_fact = 1; // Geometrically increasing factor in each loop iteration
  for (int i = 0; i < ctx->size; i++) {
      s[i] = 0;
  }
  #if PARALLEL == 1
  #pragma omp parallel for
  #endif
  for (int i = 0; i < ctx->size; i++) {
      twiddle = 1;
      for (int j = 0; j < ctx->size; j++) {
          twiddle = j == 0 ? 1 : barrett_reduce(twiddle * twiddle_fact, ctx);
          int temp = barrett_reduce(ctx->in_seq[j] * twiddle, ctx);
          s[i] = s[i] + temp > ctx->mod ? s[i] + temp - ctx->mod : s[i] + temp;
      }
      // Increase twiddle factor
      twiddle_fact = barrett_reduce(twiddle_fact * ctx->w, ctx);
  }
  ctx->out_seq = s;
}
#endif

// Lookup powers instead of using a_pow_b_mod_m
#if NTT_TYPE == TYPE_N2 && LUT_BASED == 1
void ntt_impl(ntt_ctx * ctx) {
  int *s  = malloc(ctx->size * sizeof(int));
  for (int i = 0; i < ctx->size; i++) {
      s[i] = 0;
  }
  #if PARALLEL == 1
  #pragma omp parallel for
  #endif
  for (int i = 0; i < ctx->size; i++) {
      for (int j = 0; j < ctx->size; j++) {
          s[i] = barrett_reduce(s[i] + ctx->in_seq[j] * (ctx->is_fwd ? g_gen_pows[i*j % ctx->size] : g_inv_gen_pows[i*j % ctx->size]), ctx);
      }
  }
  ctx->out_seq = s;
}
#endif

// Use associative cache
#if NTT_TYPE == TYPE_N2 && CACHE_BASED == 1
void ntt_impl(ntt_ctx * ctx) {
  int *s  = malloc(ctx->size * sizeof(int));
  int twiddle = 1;
  int twiddle_fact = 1; // Geometrically increasing factor in each loop iteration
  int tag = 0;
  int hit = 0;
  for (int i = 0; i < ctx->size; i++) {
      s[i] = 0;
  }
  #if PARALLEL == 1
  #pragma omp parallel for
  #endif
  for (int i = 0; i < ctx->size; i++) {
      twiddle = 1;
      for (int j = 0; j < ctx->size; j++) {
          tag = (i*j % DIM/CACHE_RATIO);
          hit = g_cache_pow_idx[tag] == (i*j % DIM);
          if (!hit) {
              // TODO check for a hit on neighbour below?
              // TODO check hits from all neighbours then get shortest distance?
              g_gen_pows_cache[tag] = a_pow_b_mod_m(ctx->w, i*j % DIM, ctx->mod);
              g_cache_pow_idx[tag] = i*j % DIM;
          }
          int temp = barrett_reduce(ctx->in_seq[j] * g_gen_pows_cache[tag], ctx);
          s[i] = s[i] + temp > ctx->mod ? s[i] + temp - ctx->mod : s[i] + temp;
      }
      // Increase twiddle factor
      twiddle_fact = barrett_reduce(twiddle_fact * ctx->w, ctx);
  }
  ctx->out_seq = s;
}
#endif

// Fixed radix only
// TODO worth doing a base-case N2 expansion? Could be parallelized
#if NTT_TYPE == TYPE_FAST && FAST_FIXED == 1
void ntt_impl(ntt_ctx * ctx) {
    int *x = ctx->in_seq;
    int t1, t2;
    int twiddle1, twiddle2;
    int cur_size;
    int cur_idx;
#if LUT_BASED == 0
    int half_rot = a_pow_b_mod_m(ctx->w, ctx->size/2, ctx->mod);
    int stride_twiddle;
    int running_twiddle_1;
#else
    int half_rot = ctx->is_fwd ? g_gen_pows[ctx->size/2] : g_inv_gen_pows[ctx->size/2];
#endif
    for (int stride = ctx->size>>1; stride >= 1; stride >>= 1) { // log n
        cur_size = stride<<1;
#if LUT_BASED == 0
        stride_twiddle = a_pow_b_mod_m(ctx->w, stride, ctx->mod);
        running_twiddle_1 = 1;
#endif
        // For each of the "sub-transforms" in the CT butterfly
        for (int sub_trans_idx = 0; sub_trans_idx < ctx->size/cur_size; sub_trans_idx++) {
            // We take steps within our sub transform
            for (int step = 0; step < stride; step++) {
                cur_idx = sub_trans_idx*cur_size + step;
#if LUT_BASED == 0
                twiddle1 = running_twiddle_1;
                running_twiddle_1 = barrett_reduce(stride_twiddle * running_twiddle_1, ctx);
                // Twiddle 2 is offset half a rotation from twiddle 1
                twiddle2 = barrett_reduce(twiddle1 * half_rot, ctx);
#else // LUT
                twiddle1 = ctx->is_fwd ? g_gen_pows[(sub_trans_idx*stride) % ctx->size] : g_inv_gen_pows[(sub_trans_idx*stride) % ctx->size];
                twiddle2 = ctx->is_fwd ? g_gen_pows[(sub_trans_idx*stride + ctx->size/2) % ctx->size] : g_inv_gen_pows[(sub_trans_idx*stride + ctx->size/2) % ctx->size];
#endif
                x[cur_idx + stride] = barrett_reduce(x[cur_idx] + x[cur_idx + stride] * twiddle2, ctx);
                x[cur_idx] = barrett_reduce(x[cur_idx] + x[cur_idx + stride] * twiddle1, ctx);
            }
        }
    }
    ctx->out_seq = x;
}
#endif

#if NTT_TYPE == TYPE_FAST && FAST_MIXED == 1
void ntt_impl(ntt_ctx * ctx) {
    int *x = ctx->in_seq;
    int t;
    int twiddle;
    int n_cur = ctx->size;
    int orig_size = ctx->size;
    int fact_cnt = 0;
    int n2 = n_cur/ctx->prime_factors[fact_cnt];
    int dst_idx;
#if LUT_BASED == 0
    int base_j_1; // With n_cur/ctx->size
    int running_pow_j_2; // With above ^ni
    int running_pow_j_3; // With above ^butterfly_j
    int base_i_1; // With ctx->size/ctx->prime_factors[fact_cnt]
    int running_pow_i_2; // With above ^butterfly_i
#endif
    // for (int n2 = n_cur/ctx->prime_factors[fact_cnt]; n2 >= 1; n2 /= (ctx->prime_factors[fact_cnt])) { // log n
    while (1) { // Iterates over prime factors. Termination at bottom of loop
        // For each of the "sub-transforms" in the CT butterfly
        for (int n1 = 0; n1 < orig_size/n_cur; n1++) {
#if LUT_BASED == 0
            base_j_1 = a_pow_b_mod_m(ctx->w, n_cur/ctx->size, ctx->mod);
            base_i_1 = a_pow_b_mod_m(ctx->w, n_cur/ctx->prime_factors[fact_cnt], ctx->mod);
            running_pow_j_2 = 1;
#endif
            // We take steps within our sub transform
            for (int ni = 0; ni < n2; ni++) {
                int *x_t = calloc(ctx->prime_factors[fact_cnt], sizeof(int));
                for (int butterfly_i = 0; butterfly_i < ctx->prime_factors[fact_cnt]; butterfly_i++) {
                    dst_idx = n1*n_cur + ni + butterfly_i*n2;
                    x_t[butterfly_i] = x[dst_idx]; // Temp save
                }
                // We have N^2 terms to add where N is the prime factor
                // Since N sums into each N node of the sub transform
#if LUT_BASED == 0
                running_pow_i_2 = 1;
#endif
                for (int butterfly_i = 0; butterfly_i < ctx->prime_factors[fact_cnt]; butterfly_i++) {
#if LUT_BASED == 0
                    running_pow_j_3 = 1;
#endif
                    for (int butterfly_j = 0; butterfly_j < ctx->prime_factors[fact_cnt]; butterfly_j++) {
                        dst_idx = n1*n_cur + ni + butterfly_i*n2;
#if LUT_BASED == 0
                        /*
                        x[dst_idx] =  barrett_reduce(x[dst_idx] + x_t[butterfly_j] *
                                      a_pow_b_mod_m(ctx->w, ((n_cur/ctx->size)*ni*butterfly_j + (butterfly_i * ctx->size/ctx->prime_factors[fact_cnt]))
                                      % ctx->size, ctx->mod), ctx);
                                      */
                        int red1 = barrett_reduce(running_pow_j_3 * running_pow_i_2, ctx);
                        int red2 = barrett_reduce(red2 * x_t[butterfly_j], ctx);
                        x[dst_idx] =  barrett_reduce(x[dst_idx] + red2, ctx);
                        running_pow_j_3 = barrett_reduce(running_pow_j_3 * running_pow_j_2, ctx);
#else // LUT
                        x[dst_idx] =  barrett_reduce(x[dst_idx] + x_t[butterfly_j] *
                                      (ctx->is_fwd ?     g_gen_pows[((n_cur/ctx->size)*ni*butterfly_j + (butterfly_i * ctx->size/ctx->prime_factors[fact_cnt])) % ctx->size]
                                                  : g_inv_gen_pows[((n_cur/ctx->size)*ni*butterfly_j + (butterfly_i * ctx->size/ctx->prime_factors[fact_cnt])) % ctx->size]),
                                      ctx);
#endif
                    }
#if LUT_BASED == 0
                    running_pow_i_2 = barrett_reduce(running_pow_i_2 * base_i_1, ctx);
#endif
                }
                free(x_t);
            }
#if LUT_BASED == 0
            running_pow_j_2 = barrett_reduce(running_pow_j_2 * base_j_1, ctx);
#endif
        }
        // Size for next iter
        n_cur = n2;
        fact_cnt++;
        if (fact_cnt >= ctx->prime_factor_size) {
            break;
        }
        n2 /= (ctx->prime_factors[fact_cnt]); // Logn
    }
    ctx->out_seq = x;
}
#endif


int ntt_check(ntt_ctx *fwd_ctx, ntt_ctx *inv_ctx) {

    ntt_impl(fwd_ctx);
    // Reset tags
#if CACHE_BASED == 1
    for (int i = 0; i < DIM/CACHE_RATIO; i++) {
        g_cache_pow_idx[i] = -1;
    }
#endif
    inv_ctx->in_seq = fwd_ctx->out_seq;
    ntt_impl(inv_ctx);
        
    int *orig_arr = fwd_ctx->in_seq;
    int *final_arr = inv_ctx->out_seq;
    int inv_n = modinv(fwd_ctx->size, fwd_ctx->mod);
    for (int i = 0; i < fwd_ctx->size; i++) {
        final_arr[i] = (final_arr[i] * inv_n) % fwd_ctx->mod;
        if (final_arr[i] != orig_arr[i]) {
            return 0;
        }
    }
    return 1;
}
