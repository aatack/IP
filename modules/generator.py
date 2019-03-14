from wise.util.tensors import placeholder_node
import modules.reusablenet as rnet
import tensorflow as tf


class ParametricGenerator:
    def __init__(
        self,
        name,
        solution_dimension,
        latent_dimension,
        constraint_dimension,
        embedding_dimension,
    ):
        """
        Int -> Int -> Int -> Int -> ParametricGenerator
        Create a parametric generator by specifying the dimensions
        of all relevant spaces.
        """
        self.name = name
        self.extend_name = rnet.name_extender(self.name)

        self.solution_dimension = solution_dimension
        self.latent_dimension = latent_dimension
        self.constraint_dimension = constraint_dimension
        self.embedding_dimension = embedding_dimension

        # NOTE: if strange errors about non-matching dimensions are observed,
        #       it is likely because the batch size fed into the constraint node
        #       did not match this value
        self.generator_training_batch_size = 64

    def set_generator_architecture(
        self, internal_layers, internal_activation, output_activation
    ):
        """
        [(Int, String)] -> String -> String -> ()
        Provide an architecture to use when building the generator.
        """
        self.generator_architecture = rnet.feedforward_network_input_dict(
            self.extend_name("generator"),
            self.latent_dimension,
            internal_layers + [(self.embedding_dimension, internal_activation)],
        )
        self.generator_architecture["layers"].append(
            {
                "axes": 2,
                "activation": output_activation,
                "name": "solution_embedding_layer",
            }
        )

    def set_embedder_architecture(
        self,
        weights_internal_layers,
        weights_activation,
        biases_internal_layers,
        biases_activation,
    ):
        """
        [(Int, String)] -> String -> [(Int, String)] -> String -> ()
        Provide architectures to use when building the constraint
        embedders.
        """
        self.embedder_weights_architecture = rnet.feedforward_network_input_dict(
            self.extend_name("embedder_weights"),
            self.constraint_dimension,
            weights_internal_layers
            + [
                (self.embedding_dimension * self.solution_dimension, weights_activation)
            ],
        )

        self.embedder_biases_architecture = rnet.feedforward_network_input_dict(
            self.extend_name("embedder_biases"),
            self.constraint_dimension,
            biases_internal_layers + [(self.solution_dimension, biases_activation)],
        )

    def set_discriminator_architecture(self, internal_layers):
        """
        Dict -> ()
        Provide an architecture to use when building the discriminator.
        """
        self.discriminator_architecture = rnet.feedforward_network_input_dict(
            self.extend_name("discriminator"),
            self.solution_dimension + self.constraint_dimension,
            internal_layers + [(1, "sigmoid")],
        )

    def build_input_nodes(self):
        """
        () -> ()
        Construct input placeholder nodes for the tensorflow graph.
        """
        self.solution_input = placeholder_node(
            self.extend_name("solution_input"),
            [self.solution_dimension],
            dynamic_dimensions=1,
        )
        self.latent_input = placeholder_node(
            self.extend_name("latent_input"),
            [self.latent_dimension],
            dynamic_dimensions=1,
        )
        self.constraint_input = placeholder_node(
            self.extend_name("constraint_input"),
            [self.constraint_dimension],
            dynamic_dimensions=1,
        )

    def build_sample_nodes(self):
        """
        () -> ()
        Construct sample nodes for training the generator.
        """
        self.latent_sample = tf.random.uniform(
            [self.generator_training_batch_size, self.latent_dimension],
            name=self.extend_name("latent_sample"),
        )
        self.constraint_sample = tf.random.uniform(
            [self.generator_training_batch_size, self.constraint_dimension],
            name=self.extend_name("constraint_sample"),
        )

    def build_embedder(self, constraint_input):
        """
        tf.Node -> (Dict, Dict)
        Build the constraint embedder.  The output of the penultimate layer
        of the generator is assumed to have a dimensionality consistent with
        this object's `embedding_dimension` parameter.  The return values
        are separated into two networks, for the weights and biases of the
        final layer respectively.
        """
        embedder_weights_architecture = rnet.deep_copy(
            self.embedder_weights_architecture
        )
        embedder_weights_architecture["input"] = constraint_input
        weights_embedder = rnet.feedforward_network(embedder_weights_architecture)
        weights_embedder["output"] = tf.reshape(
            weights_embedder["output"],
            [
                self.embedding_dimension,
                tf.shape(weights_embedder["output"])[0],
                self.solution_dimension,
            ],
            name=self.extend_name("reshaped_constraint_embedding"),
        )

        embedder_biases_architecture = rnet.deep_copy(self.embedder_biases_architecture)
        embedder_biases_architecture["input"] = constraint_input
        biases_embedder = rnet.feedforward_network(embedder_biases_architecture)

        return weights_embedder, biases_embedder

    def build_generator(self, latent_input, weights_embedder, biases_embedder):
        """
        tf.Node -> Dict -> Dict -> Dict
        Build the generator given an input node and the weights and biases
        produced by the constraint embedder.
        """
        architecture = rnet.deep_copy(self.generator_architecture)
        print(architecture["name"])
        architecture["input"] = latent_input
        output_layer = architecture["layers"][-1]
        output_layer["weights"] = weights_embedder["output"]
        output_layer["biases"] = biases_embedder["output"]
        return rnet.feedforward_network(architecture)

    def build_discriminator(self, solution_input, constraint_input):
        """
        tf.Node -> tf.Node -> Dict
        Build the discriminator, given nodes containing batches of
        solutions and constraints respectively.
        """
        architecture = rnet.deep_copy(self.discriminator_architecture)
        architecture["input"] = rnet.join_inputs(solution_input, constraint_input)
        discriminator = rnet.feedforward_network(architecture)
        discriminator["output"] = tf.reshape(
            discriminator["output"], [tf.shape(discriminator["output"])[0]]
        )
        return discriminator

    def discriminator_training_nodes(self, discriminator):
        """
        Dict -> (tf.Node, tf.Node)
        Return a target node and loss node useful for training the discriminator.
        """
        target = placeholder_node(
            self.extend_name("discriminator_target"), [], dynamic_dimensions=1
        )
        loss = tf.losses.mean_squared_error(target, discriminator["output"])
        return target, loss

    def generator_pretraining_nodes(self, generator):
        """
        Dict -> tf.Node
        Return a loss node that measures the distance of the generator from
        the identity function in the function space.  Only defined when the
        latent dimension is equal to the solution dimension.
        """
        if self.latent_dimension != self.solution_dimension:
            raise ValueError(
                "latent and solution dimensions must be equal "
                + "for linearity loss to be well defined"
            )
        return tf.reduce_mean(
            tf.squared_difference(
                2 * (generator["input"] - 1),
                generator["output"],
                name=self.extend_name("linearity_squared_difference"),
            ),
            name=self.extend_name("linearity_loss"),
        )
