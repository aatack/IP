import modules.reusablenet as rnet
import tensorflow as tf
import numpy as np


class ExportedParametricGenerator:
    def __init__(self, generator, session):
        """
        ParametricGenerator -> tf.Session -> ExportedParametricGenerator
        Export a parametric generator that has been trained for easy querying
        in typical use cases.
        """
        self.sample_for_constraint = self._make_sample_for_constraint(
            generator, session
        )
        self.map_to_solution = self._make_map_to_solution(generator, session)

        self.constraint_optimiser = self._make_constraint_optimiser(generator, session)
        self.satisfaction_probability = self._make_satisfaction_probability(
            generator, session
        )

    def _make_sample_for_constraint(self, parametric_generator, session):
        """
        ParametricGenerator -> tf.Session -> (np.array -> Int -> [Dict])
        From a generator, create a function that takes a constraint and a number
        of samples, and creates that number of GeneratorSample instances.  Each
        contains a latent sample, solution, and satisfaction probability.
        """
        sample_size = tf.placeholder(tf.int32, shape=(), name="sample_size")
        constraint_input = rnet.make_input_node(
            [parametric_generator.constraint_dimension]
        )

        multiples = tf.stack([sample_size, tf.constant(1)])
        tiled_constraints = tf.tile(tf.expand_dims(constraint_input, 0), multiples)

        latent_samples = tf.random.uniform(
            tf.stack([sample_size, tf.constant(parametric_generator.latent_dimension)]),
            minval=parametric_generator.latent_lower_bound,
            maxval=parametric_generator.latent_upper_bound,
        )

        weights, biases = parametric_generator.build_embedder(tiled_constraints)
        generator = parametric_generator.build_generator(
            latent_samples, weights, biases
        )
        discriminator = parametric_generator.build_discriminator(
            generator["output"], tiled_constraints
        )

        def sample_for_constraint(constraint, samples):
            """
            np.array -> Int -> [Dict]
            Given a constraint and a requested number of samples, return that
            number of dictionaries, where each dictionary represents a sample from
            the latent space for that constraint.  They contain keys for 
            `latent`, `solution`, and `satisfaction_probability`.
            """
            latent_samples, solutions, satisfaction_probabilities = session.run(
                [generator["input"], generator["output"], discriminator["output"]],
                feed_dict={constraint_input: constraint, sample_size: samples},
            )

            zipped_samples = [
                ExportedParametricGenerator.GeneratorSample(l, s, p)
                for l, s, p in zip(
                    latent_samples, solutions, satisfaction_probabilities
                )
            ]

            return zipped_samples

        return sample_for_constraint

    def _make_map_to_solution(self, parametric_generator, session):
        """
        ParametricGenerator -> tf.Session -> (np.array -> (np.array -> np.array))
        Generate a function that maps from the latent space to the solution space.
        """
        latent_placeholder = rnet.make_input_node(
            [None, parametric_generator.latent_dimension]
        )
        constraint_placeholder = rnet.make_input_node(
            [parametric_generator.constraint_dimension]
        )
        replicated_constraint = tf.tile(
            tf.expand_dims(constraint_placeholder, axis=0),
            [tf.shape(latent_placeholder)[0], 1],
        )

        weights, biases = parametric_generator.build_embedder(replicated_constraint)
        generator = parametric_generator.build_generator(
            latent_placeholder, weights, biases
        )

        def map_to_solution(constraint):
            """
            np.array -> (np.array -> np.array)
            Given a constraint, return a function that maps a list of latent
            coordinates into the solution space.
            """
            np_constraint = np.array(constraint)

            def map_to_solution_inner(latent_points):
                wrapped = False

                np_latent_points = np.array(latent_points)
                if len(np_latent_points.shape) == 1:
                    np_latent_points = np.array([np_latent_points])
                    wrapped = True

                output = session.run(
                    generator["output"],
                    feed_dict={
                        constraint_placeholder: np_constraint,
                        latent_placeholder: np_latent_points,
                    },
                )

                return output if not wrapped else output[0]

            return map_to_solution_inner

        return map_to_solution

    def _make_constraint_optimiser(self, parametric_generator, session):
        """
        ParametricGenerator -> tf.Session -> (np.array -> (np.array -> GeneratorSample))
        Create a function that can be used to optimise the position in the latent
        space for a specific constraint.        
        """
        constraint_placeholder = rnet.make_input_node(
            [parametric_generator.constraint_dimension]
        )
        latent_placeholder = rnet.make_input_node(
            [parametric_generator.latent_dimension]
        )

        constraint_input = tf.expand_dims(constraint_placeholder, 0)
        latent_input = tf.expand_dims(latent_placeholder, 0)

        weights, biases = parametric_generator.build_embedder(constraint_input)
        generator = parametric_generator.build_generator(latent_input, weights, biases)
        discriminator = parametric_generator.build_discriminator(
            generator["output"], constraint_input
        )

        solution_output = tf.squeeze(generator["output"])
        satisfaction_output = tf.squeeze(discriminator["output"])

        def constraint_optimiser(constraint):
            """
            np.array -> (np.array -> GeneratorSample)
            Take a constraint and produce a function which, given a position in the
            latent space, calculates the corresponding solution and satisfaction
            probability.  Useful for interfacing with external optimisation algorithms.
            """

            def evaluate(latent):
                l, s, p = session.run(
                    [latent_placeholder, solution_output, satisfaction_output],
                    feed_dict={
                        constraint_placeholder: constraint,
                        latent_placeholder: latent,
                    },
                )
                return ExportedParametricGenerator.GeneratorSample(l, s, p)

            return evaluate

        return constraint_optimiser

    def _make_satisfaction_probability(self, generator, session):
        """
        ParametricGenerator -> tf.Session -> (np.array -> Float)
        Return a curried function that takes the constraint vector and solution
        vectors as input and returns the estimated probability of the solution
        satisfying the constraint.
        """
        discriminator = generator.build_discriminator(
            generator.solution_input, generator.constraint_input
        )

        def satisfaction_probability_function(constraint, zero_outside_bounds=True):
            """
            np.array -> Bool? -> Float
            Return a function that calculates the probability of a solution vector
            satisfying the given constraint.
            """
            l, u = generator.solution_lower_bound, generator.solution_upper_bound
            return (
                lambda s: 0.0
                if any([not l <= si < u for si in s])
                else session.run(
                    discriminator["output"],
                    feed_dict={
                        generator.constraint_input: [constraint],
                        generator.solution_input: [s],
                    },
                )
            )

        return satisfaction_probability_function

    class GeneratorSample:
        def __init__(self, latent, solution, satisfaction_probability):
            """
            np.array -> np.array -> Float -> GeneratorSample
            Data class for easily representing samples of the generator.
            """
            self.latent = latent
            self.solution = solution
            self.satisfaction_probability = satisfaction_probability

        def __str__(self):
            """
            () -> String
            Return a string representation of the sample.
            """
            return "(\n  latent: {}\n  solution: {}\n  satisfaction_probability: {}\n)".format(
                list(self.latent), list(self.solution), self.satisfaction_probability
            )

        def to_json(self):
            """
            () -> Dict
            Return a JSON-like representation of the generator sample.
            """
            return {
                "latent": self.latent.tolist(),
                "solution": self.solution.tolist(),
                "satisfactionProbability": self.satisfaction_probability.item(),
            }
