#ifndef NTT_H
#define NTT_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>

// TODO defined via makefile
// #define NTT_TYPE FAST
// #define DIM 512

#define FAIL_PRINT_INFO 1

#define DO_TIME 1

// Constants
#define TYPE_N2 0
#define TYPE_FAST 1

// Mutually exclusive
// #define FAST_FIXED 1
// #define FAST_MIXED 0

// Use OMP
// #define PARALLEL 1

// Only matters if FAST_MIXED == 1
// #define MAX_RADIX 5

// #define LUT_BASED 0

typedef struct {
    int mod;
    int qinv;
    int size;
    int barrett_k;
    int barrett_r;
    int w;
    int is_fwd;
    int prime_factor_size;
    int * prime_factors;
    int * in_seq;
    int * out_seq;
} ntt_ctx;

int ntt_check(ntt_ctx *, ntt_ctx *);
int fqmul(int, int, ntt_ctx *);
int barrett_reduce(int a, ntt_ctx *ctx);
int modinv(int a, int m);
int is_prime(int n);
void get_ntt_params(int n, int * mod, int * g);
int * get_prime_factors(int n, int *prime_factor_size);
int clog2(long int in);
void sort(int *x, size_t size);
void populate_pows_lut(ntt_ctx *, ntt_ctx *);
void init_cache(void);

#endif // NTT_H
