from numpy.random import normal
from random import uniform


def standard_gaussian_generator(n):
    """
    Int -> (() -> [Float])
    Create a function which, when called, returns a list of
    n floats sampled from a standard Gaussian.
    """
    def generate():
        return normal(size=n)
    return generate


def gaussian_about(x):
    """
    [Float] -> [Float]
    Return a sample from a multivariate Gaussian distribution with a standard
    deviation of 1, centred on the input point.
    """
    return normal(loc=x, size=len(x))


def metropolis_hastings(iterations, f, x, Q=gaussian_about):
    """
    Int -> ([Float] -> Float) -> [Float] -> ([Float] -> [Float])? -> [Float]
    Iterate the Metropolis-Hastings algorithm n times on the given starting
    point for the objective function f.
    """
    _x = x
    for _ in range(iterations):
        _x = iterate_metropolis_hastings(f, Q, x)
    return _x


def iterate_metropolis_hastings(f, Q, x):
    """
    ([Float] -> Float) -> ([Float] -> [Float]) -> [Float] -> [Float]
    Use the Metroplis-Hastings algorithm to sample the next point in a MCMC chain
    of f given the current point x and the proposal distribution Q, which returns
    a candidate for x' given x and which is assumed to be symmetric.
    """
    x_dash = Q(x)
    acceptance_ratio = f(x_dash) / f(x)
    u = uniform(0, 1)
    return x if u > acceptance_ratio else x_dash
