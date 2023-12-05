import math
import copy

class NTT_Params:
    prime_factorization = []
    # Word size constants
    c_uint8 = "uint8_t"
    c_uint16 = "uint16_t"
    c_uint32 = "uint32_t"
    c_uint64 = "uint64_t"

    # Setters
    def set_prime_factorization(self):
        fact = 2;
        n = self.n
        while (n > 1):
            if (n % fact == 0):
                self.prime_factorization.append(fact)
                n //= fact
                fact = 2
            else:
                fact += 1
        self.prime_factorization = sorted(self.prime_factorization)

    # Truncate to type widths
    def set_type_trunc(self, width):
        if width <= 8:
            return 8
        elif width > 8 and width <= 16:
            return 16
        elif width > 16 and width <= 32:
            return 32
        elif width > 32:
            return 64

    def set_type_str(self, width):
        if width <= 8:
            return self.c_uint8
        elif width > 8 and width <= 16:
            return self.c_uint16
        elif width > 16 and width <= 32:
            return self.c_uint32
        elif width > 32:
            return self.c_uint64

    def __init__(self, dimension):
        self.n = dimension
        self.g, self.mod = get_ntt_params(self.n)
        self.g_inv = modinv(self.g, self.mod)
        self.prime_factorization = []
        self.set_prime_factorization()
        self.barrett_k = 2*math.ceil(math.log2(self.mod))
        self.barrett_r = ((1 << self.barrett_k) // self.mod)
        # For power reduction in the case of LUT
        self.barrett_k_pow = 2*math.ceil(math.log2(self.n))
        self.barrett_r_pow = ((1 << self.barrett_k_pow) // self.n)
        # For word size propagation
        self.mod_width = math.ceil(math.log2(self.mod + 1))
        self.mod_prod_width = math.ceil(math.log2(self.mod*self.mod + 1))
        self.g_width = math.ceil(math.log2(self.mod + 1))
        self.g_inv_width = math.ceil(math.log2(self.mod + 1))
        self.barrett_k_width = math.ceil(math.log2(self.barrett_k + 1))
        self.barrett_r_width = math.ceil(math.log2(self.barrett_r + 1))
        self.n_width = math.ceil(math.log2(self.n + 1))
        self.n_prod_width = math.ceil(math.log2(self.n*self.n + 1))
        self.barrett_k_pow_width = math.ceil(math.log2(self.barrett_k_pow + 1))
        self.barrett_r_pow_width = math.ceil(math.log2(self.barrett_r_pow + 1))
        # Assign int type strings to each parameter and the operations between parameters
        self.mod_type = self.set_type_str(self.mod_width)
        self.mod_prod_type = self.set_type_str(self.mod_prod_width)
        self.g_type = self.set_type_str(self.g_width)
        self.g_inv_type = self.set_type_str(self.g_inv_width)
        self.barrett_k_type = self.set_type_str(self.barrett_k_width)
        self.barrett_r_type = self.set_type_str(self.barrett_r_width)
        self.n_type = self.set_type_str(self.n_width)
        self.n_prod_type = self.set_type_str(self.n_prod_width)
        self.barrett_q_type  = self.set_type_str(self.mod_prod_width + self.barrett_r_width)
        self.barrett_q_pow_type  = self.set_type_str(self.n_prod_width + self.barrett_r_pow_width)
        # Assign integer widths based on truncating widths to nearest word size
        self.mod_trunc = self.set_type_trunc(self.mod_width)
        self.mod_prod_trunc = self.set_type_trunc(self.mod_prod_width)

def is_prime(n):
    if (n & 1 == 0):
        return 0
    else:
        d = 3
        while (d*d <= n):
            if (n % d == 0):
                return 0
            d = d + 2
        return 0 if n == 1 else 1

def get_ntt_params(n):
    k = 2
    while True:
        mod = n*k + 1
        if (is_prime(mod)):
            break
        else:
            k += 1
    for i in range(2, mod):
        good_pow = True
        running_pow = i
        for j in range(2, n+1):
            running_pow = (running_pow * i) % mod
            if (running_pow == 1 and j != n):
                good_pow = False
                break
        if (running_pow == 1 and good_pow):
            return (i, mod)

    # Raise exception if no generator
    assert True, "No generator for the given dimension"

def modinv(a, m):
    t = 0
    newt = 1
    r = m
    newr = a
    while (newr != 0):
        q = int(math.floor(r / newr))
        tempt = copy.copy(newt)
        tempr = copy.copy(newr)
        newt = t - q*newt
        newr = r - q*newr
        t = copy.copy(tempt)
        r = copy.copy(tempr)
    if (t < 0):
        t += m
    return t

def a_pow_b_mod_m(a, b, m):
    abm = 1
    for i in range(b):
        abm = (abm * a) % m
    return abm

