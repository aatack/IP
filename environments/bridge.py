from environments.environment \
    import ContinuousEnvironment, DrawableEnvironment
from maths.activations import identity
from random import uniform


class Bridge(ContinuousEnvironment, DrawableEnvironment):
    """
    An environment consisting of a bridge, drawn in pixels in a 2D plane,
    over an obstacle.  The bridge is defined by having each pixel turned on
    to varying intensities: darker pixels (values closer to 1) have higher
    intensity - and therefore higher strength - but also greater mass.  The
    constraint is defined in terms of a pixel matrix of the same size,
    each pixel in the constraint denoting the maximum intensity of the same
    pixel in the solution.

    Note that the pixels are stored as a list of rows.
    """

    WIDTH = 3
    HEIGHT = 2

    # Number of members to either side of a block which are able to support
    # it, not including the one directly beneath it
    SUPPORTING_MEMBERS = 1

    SELF_LOAD_FACTOR = 0.25
    LOAD_PROPAGATION_FACTOR = 1.0

    def constraint_shape():
        """
        () -> [Int]
        Return the shape of a valid constraint tensor.
        """
        return [Bridge.HEIGHT, Bridge.WIDTH]

    def solution_shape():
        """
        () -> [Int]
        Return the shape of a valid solution tensor.
        """
        return Bridge.constraint_shape()

    def solve(constraint, solution):
        """
        [Float] -> [Float] -> Bool
        Test whether the parameters of the given solution satisfy the parameters
        of the constraint.
        """
        raise NotImplementedError()

    def _is_structurally_stable(solution):
        """
        [[Float]] -> Bool
        Determines whether or not the given solution can hold its own weight
        according to some set of rules.
        """
        return Bridge._elementwise_predicate(lambda s, l: s < l, solution,
            Bridge._create_load_map(solution))

    def _create_load_map(solution):
        """
        [[Float]] -> [[Float]]
        Calculate the load of each block.
        """
        loads = [[cell * Bridge.SELF_LOAD_FACTOR for cell in row] for row in solution]

        for row in range(Bridge.HEIGHT - 1):
            for column in range(Bridge.WIDTH):
                supporting_indices, supporting_weights = \
                    Bridge._get_supporting_indices_and_strengths(solution, row, column)
                propagated_loads = Bridge._calculate_propagated_loads(
                    solution[row][column], supporting_weights)
                for index, additional_load in zip(supporting_indices, propagated_loads):
                    loads[row + 1][index] += additional_load
        
        return loads
                
    def _get_supporting_indices_and_strengths(solution, row, column):
        """
        [[Float]] -> Int -> Int -> Range -> [Float]
        Given a solution and a row and column specifying a block in the solution,
        return a range of column indices and a list of their corresponding weights.
        """
        columns = range(max([0, column - Bridge.SUPPORTING_MEMBERS]),
            min([column + Bridge.SUPPORTING_MEMBERS + 1, Bridge.WIDTH]))
        weights = [solution[row + 1][c] for c in columns]
        return columns, weights

    def _calculate_propagated_loads(source, targets):
        """
        Float -> [Float] -> [Float]
        Calculate the amount of load that is propagated from the source block to the
        target blocks, assuming that the amount of load transferred is equal to the
        strength of the source block multiplied by the global load propagation
        factor.
        """
        propagated_load = source * Bridge.LOAD_PROPAGATION_FACTOR
        total_distribution_weight = sum(targets)
        if total_distribution_weight == 0.0:
            even_share = propagated_load / len(targets)
            return [even_share] * len(targets)
        return [propagated_load * (weight / total_distribution_weight) \
            for weight in targets]

    def _avoids_disallowed_areas(solution, constraint):
        """
        [[Float]] -> [[Float]] -> Bool
        Determine whether the solution avoids the disallowed areas as specified
        by the constraint.  Each block in the constraint gives the maximum strength
        allowed in the corresponding block in the solution.
        """
        return Bridge._elementwise_predicate(lambda s, c: s < c, solution, constraint)

    def _elementwise_predicate(predicate, solution, constraint):
        """
        (Float -> Float -> Bool) -> [[Float]] -> [[Float]] -> Bool
        Determine whether or not the given solution and constraint satisfy the
        predicate in all blocks, where the predicate is applied one by one to
        each pair of corresponding blocks.
        """
        for i in range(Bride.HEIGHT):
            for j in range(Bridge.WIDTH):
                if not predicate(solution[i][j], constraint[i][j]):
                    return False
        return True

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

    def uniform_solution():
        """
        () -> [[Float]]
        Return a solution whose weights are all sampled independently from a
        uniform distribution on [0, 1).
        """
        return [[uniform(0, 1) for _ in range(Bridge.WIDTH)] \
            for _ in range(Bridge.HEIGHT)]

    def image_shape(fidelity=None):
        """
        () -> [Int]
        Return the shape of images output by this environment with the given
        fidelity settings.
        """
        return [2 * Bridge.HEIGHT, Bridge.WIDTH]

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
