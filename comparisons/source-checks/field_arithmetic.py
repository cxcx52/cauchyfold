"""Arithmetic for the declared quartic extension field."""
Q=2**48-59

def em(a, b):
    c = [0]*7
    for i in range(4):
        for j in range(4):
            c[i+j] += a[i]*b[j]
    for j in range(6, 3, -1):
        c[j-2] += 4*c[j]
        c[j-4] -= 2*c[j]
    return tuple(x % Q for x in c[:4])


def ea(a, b):
    return tuple((x+y) % Q for x, y in zip(a, b))


def es(a, b):
    return tuple((x-y) % Q for x, y in zip(a, b))


ZERO, ONE = (0, 0, 0, 0), (1, 0, 0, 0)


def quadratic(z):
    out = []
    for j in range(4):
        acc = ZERO
        for l in range(8):
            t = 5+16*j+2*l
            acc = ea(acc, em(z[t], z[t+1]))
        out.append(es(acc, em(z[0], z[1+j])))
    return out
