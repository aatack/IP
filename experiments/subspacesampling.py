from wise.networks.deterministic.feedforwardnetwork import FeedforwardNetwork
from wise.networks.activation import Activation
from wise.util.training import default_adam_optimiser
from wise.training.routines import fit
from numpy import linspace
import matplotlib.pyplot as plt
import tensorflow as tf


class Args:

    n = 1
    batch_size = 32
    session = tf.Session()
    g_hidden = [[8]]
    w = 5


def uniform_node():
    """
    () -> tf.Node
    Create a node that represents a list of samples from an n-dimensional
    unit hypercube.
    """
    return tf.random.uniform([Args.batch_size, Args.n])


def g(y):
    """
    tf.Node -> tf.Node
    Create a function that maps from the latent space S_L to the
    generated space S_G.
    """
    return FeedforwardNetwork(
        'g', Args.session, [Args.n], Args.g_hidden + [[1]],
        activations=Activation.all_except_last(
            Activation.LEAKY_RELU, Activation.TANH),
        input_node=y).output_node


def f(x):
    """
    tf.Node -> tf.Node
    Create a Tensorflow graph representing the objective function, which
    is expected to output values between 0 and 1.
    """
    return sigmoid_bump(x, width=Args.w, offset=0.5)


def sigmoid_bump(x, width=4, offset=0., fatness=0.05, y_scale=1.):
    """
    tf.Node -> Float -> Float? -> Float? -> Float? -> tf.Node
    Create a Tensorflow graph representing a sigmoid bump.
    """
    after_offset = (x - offset) / fatness
    return y_scale * (tf.sigmoid(after_offset + width) -
        tf.sigmoid(after_offset - width))


def p_loss(gamma):
    """
    tf.Node -> tf.Node
    Create a node that estimates the a proxy loss for maximising the
    precision of the generator network.
    """
    return tf.reduce_mean(-tf.log(gamma))


def plot_histogram(node, lower=None, upper=None, steps=50):
    """
    tf.Node -> ()
    Plot a histogram of the given node, where the node is assumed to be
    a list of vectors, and the first component of each vector is used.
    """
    values = sorted([v[0] for v in Args.session.run(node)])
    l = lower if lower is not None else values[0]
    u = upper if upper is not None else values[-1]
    plt.hist(values, bins=steps, range=(l, u))
    plt.show()


def f_plotter(lower, upper, steps=50):
    """
    () -> (() -> ())
    Return a function which, when called, plots the objective function
    for the specified range.
    """
    xs = linspace(lower, upper, steps)
    fs = Args.session.run(f(tf.constant(xs)))
    def plot():
        plt.plot(xs, fs)
        plt.show()
    return plot


def run():
    """
    () -> ()
    Attempt to learn a function which maps samples from a unit hypercube
    to another space defined as the values of x for which f(x) > 0.5.
    """
    y_sample = uniform_node()
    x_sample = g(y_sample)
    gamma_sample = f(x_sample)
    l = p_loss(gamma_sample)
    opt = default_adam_optimiser(l, 'optimiser')

    plot_f = f_plotter(-1, 1)
    plot_f()

    def plot_x_histogram():
        plot_histogram(x_sample, lower=-1, upper=1)

    def plot_gamma_histogram():
        plot_histogram(gamma_sample, lower=0, upper=1)

    Args.session.run(tf.global_variables_initializer())

    plot_x_histogram()
    plot_gamma_histogram()

    for i in range(1000):
        epoch_loss, _ = Args.session.run([l, opt])
        if i % 10 == 0:
            print(epoch_loss)
            
    plot_x_histogram()
    plot_gamma_histogram()
