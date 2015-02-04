import random, math

def rndvow():
    """
    Return a random vowel. Only really necessary for the vowel filter included in Dirt.
    """
    return random.choice(['a', 'e', 'i', 'o', 'u'])

def stepvow(step):
    """
    Return a vowel accorind to a step. Only really necessary for the vowel filter included in Dirt.
    """
    vowels = ['a', 'e', 'i', 'o', 'u']
    return vowels[step % 5]

def mod(i, j):
    return i % j

def add(i, j):
    return i + j

def sub(i, j):
    return i - j  

def mul(i, j):
    return i * j  

def div(i, j):
    return i / j 

def stra(s, step):
    return s + ":" + str(step)

# value, incrementing param, steps for one cycle, range 
def sinstretch(val, inc, cyc, min_bound, max_bound):
    """
    Sinusoidal stretching of values between specified bounds
    """
    degree_increment = 360 / cyc
    degree = ((inc % cyc) * degree_increment) % 360
    abs_sin = abs(math.sin(math.radians(degree)))
    stretch_range = max_bound - min_bound
    return (abs_sin * stretch_range) + min_bound 
    

def brownian(val, inc, min_bound, max_bound):
    """
    Simplified Wiener Process between certain bounds.

    Only works as permalay.
    
    """
    random.seed()
    val = val + random.choice([inc, -inc])
    if val < min_bound:
        return min_bound
    elif val > max_bound:
        return max_bound
    else:
        return val
