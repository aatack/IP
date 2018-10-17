from maths.activations import identity


class ContinuousEnvironment:
    """
    Base class for an environment in which the solution space and
    constraint space are both continuous.
    """

    def constraint_shape():
        """
        () -> [Int]
        Return the shape of a valid constraint tensor.
        """
        raise NotImplementedError()

    def solution_shape():
        """
        () -> [Int]
        Return the shape of a valid solution tensor.
        """
        raise NotImplementedError()

    def solve(constraint, solution):
        """
        [Float] -> [Float] -> Bool
        Test whether the parameters of the given solution satisfy the parameters
        of the constraint.
        """
        raise NotImplementedError()

    def environment_sampler(constraint_input='constraint', solution_input='solution',
            satisfaction_input='satisfaction', sampler_transform=identity):
        """
        Object? -> Object? -> Object? -> (Sampler a -> Sampler a)?
            -> FeedDictSampler ([Float], [Float], [Float])
        Return a sampler that generates random constraint/solution pairs and
        matches them with the satisfaction of the constraint.  The raw sampler is
        mapped through a user-provided transform, optionally producing a mapped
        sampler, before being extracted into a FeedDictSampler.
        """
        raise NotImplementedError()


class DrawableEnvironment:
    """
    Base class for an environment in which the solution space and
    constraint space can both be represented by a 2D greyscale image.
    """

    def image_shape(fidelity=None):
        """
        () -> [Int]
        Return the shape of images output by this environment with the given
        fidelity settings.
        """
        raise NotImplementedError()

    def as_image(constraint, solution, fidelity=None):
        """
        [Float] -> [Float] -> Object? -> [[Float]]
        Produce a greyscale image of the environment from the given environment
        parameters, and optionally some measure of fidelity.  Pixel values
        should be in the interval [0, 1], where 0 represents fully off and 1
        represents fully on.
        """
        raise NotImplementedError()

    def pixel_environment_sampler(pixels_input='pixels', satisfaction_input='satisfaction',
            fidelity=None, sampler_transform=identity):
        """
        Object? -> Object? -> Object? -> (Sampler a -> Sampler a)?
            -> FeedDictSampler ([[Float]], [Float])
        Sample from the space of environments, returning them as the output of
        a FeedDictSampler in pixel format, grouped with their satisfaction.
        The raw sampler is mapped through a user-provided transform, optionally producing
        a mapped sampler, before being extracted into a FeedDictSampler.
        """
        raise NotImplementedError()
