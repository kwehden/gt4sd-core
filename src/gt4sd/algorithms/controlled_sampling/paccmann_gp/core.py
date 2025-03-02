"""PaccMann\\ :superscript:`GP` Algorithm.

PaccMann\\ :superscript:`GP` generation is conditioned via gaussian processes.
"""

import logging
from dataclasses import field
from typing import Any, Callable, ClassVar, Dict, Iterable, Optional, TypeVar

from typing_extensions import Protocol, runtime_checkable

from ....domains.materials import SmallMolecule, validate_molecules
from ....exceptions import InvalidItem
from ...core import AlgorithmConfiguration, GeneratorAlgorithm
from ...registry import ApplicationsRegistry
from .implementation import GPConditionalGenerator

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

T = TypeVar("T", bound=Any)
S = TypeVar("S", bound=SmallMolecule)
Targeted = Callable[[T], Iterable[Any]]


class PaccMannGP(GeneratorAlgorithm[S, T]):
    """PaccMann\\ :superscript:`GP` Algorithm."""

    def __init__(
        self,
        configuration: AlgorithmConfiguration[S, T],
        target: Optional[T],
    ):
        """Instantiate PaccMannGP ready to generate items.

        Args:
            configuration: domain and application
                specification defining parameters, types and validations.
            target: a target for which to generate items.

        Example:
            An example for generating small molecules (SMILES) with high affinity
            for a target protein::

                configuration = PaccMannGPGenerator()
                target = {
                    "qed": {"weight": 1.0},
                    "molwt": {"target": 200},
                    "sa": {"weight": 2.0},
                    "affinity": {"protein": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTT"}
                }
                paccmann_gp = PaccMannGP(configuration=configuration, target=target)
                items = list(paccmann_gp.sample(10))
                print(items)
        """

        configuration = self.validate_configuration(configuration)
        # TODO there might also be a validation/check on the target input

        super().__init__(
            configuration=configuration,  # type:ignore
            target=target,  # type:ignore
        )

    def get_generator(
        self,
        configuration: AlgorithmConfiguration[S, T],
        target: Optional[T],
    ) -> Targeted[T]:
        """Get the function to sample batches via PaccMannGP's GPConditionalGenerator.

        Args:
            configuration: helps to set up specific application of PaccMannGP.
            target: context or condition for the generation.

        Returns:
            callable with target generating a batch of items.
        """
        logger.info("ensure artifacts for the application are present.")
        self.local_artifacts = configuration.ensure_artifacts()
        implementation: GPConditionalGenerator = configuration.get_conditional_generator(  # type: ignore
            self.local_artifacts
        )
        return implementation.generate_batch

    def validate_configuration(
        self, configuration: AlgorithmConfiguration[S, T]
    ) -> AlgorithmConfiguration[S, T]:
        @runtime_checkable
        class AnyPaccMannGPConfiguration(Protocol):
            """Protocol for PaccMannGP configurations."""

            def get_conditional_generator(
                self, resources_path: str
            ) -> GPConditionalGenerator:
                ...

            def validate_item(self, item: Any) -> S:
                ...

        # TODO raise InvalidAlgorithmConfiguration
        assert isinstance(configuration, AnyPaccMannGPConfiguration)
        assert isinstance(configuration, AlgorithmConfiguration)
        return configuration


@ApplicationsRegistry.register_algorithm_application(PaccMannGP)
class PaccMannGPGenerator(AlgorithmConfiguration[SmallMolecule, Any]):
    """
    Configuration to generate compounds controlling molecules properties.

    Implementation from the paper: https://doi.org/10.1021/acs.jcim.1c00889.
    """

    algorithm_type: ClassVar[str] = "controlled_sampling"
    domain: ClassVar[str] = "materials"
    algorithm_version: str = "v0"

    batch_size: int = field(
        default=32,
        metadata=dict(description="Batch size used for the generative model sampling."),
    )
    temperature: float = field(
        default=1.4,
        metadata=dict(
            description="Temperature parameter for the softmax sampling in decoding."
        ),
    )
    generated_length: int = field(
        default=100,
        metadata=dict(
            description="Maximum length in tokens of the generated molcules (relates to the SMILES length)."
        ),
    )
    limit: float = field(
        default=5.0,
        metadata=dict(description="Hypercube limits in the latent space."),
    )
    acquisition_function: str = field(
        default="EI",
        metadata=dict(
            description=(
                "Acquisition function used in the Gaussian process. "
                "More details in https://scikit-optimize.github.io/stable/modules/generated/skopt.gp_minimize.html."
            )
        ),
    )
    number_of_steps: int = field(
        default=32,
        metadata=dict(description="Number of steps for an optmization round."),
    )
    number_of_initial_points: int = field(
        default=16,
        metadata=dict(description="Number of initial points evaluated."),
    )
    initial_point_generator: str = field(
        default="random",
        metadata=dict(
            description=(
                "Scheme to generate initial points. "
                "More details in https://scikit-optimize.github.io/stable/modules/generated/skopt.gp_minimize.html."
            )
        ),
    )
    seed: int = field(
        default=42,
        metadata=dict(
            description="Seed used for random number generation in the optimizer."
        ),
    )
    number_of_optimization_rounds: int = field(
        default=1,
        metadata=dict(description="Maximum number of optimization rounds."),
    )
    sampling_variance: float = field(
        default=0.1,
        metadata=dict(
            description="Variance of the Gaussian noise applied during sampling from the optimal point."
        ),
    )
    samples_for_evaluation: int = field(
        default=4,
        metadata=dict(
            description="Number of samples averaged for each minimization function evaluation."
        ),
    )
    maximum_number_of_sampling_steps: int = field(
        default=32,
        metadata=dict(
            description="Maximum number of sampling steps in an optimization round."
        ),
    )

    def get_target_description(self) -> Dict[str, str]:
        """Get description of the target for generation.

        Returns:
            target description.
        """
        return {
            "title": "Scoring functions with parameters",
            "description": "Scoring functions will be used to generate a score for the generated molecules.",
            "type": "object",
        }

    def get_conditional_generator(self, resources_path: str) -> GPConditionalGenerator:
        """Instantiate the actual generator implementation.

        Args:
            resources_path: local path to model files.

        Returns:
            instance with :meth:`generate_batch<gt4sd.algorithms.controlled_sampling.paccmann_rl.implementation.GPConditionalGenerator.generate_batch>` method for targeted generation.
        """
        return GPConditionalGenerator(
            resources_path=resources_path,
            temperature=self.temperature,
            generated_length=self.generated_length,
            batch_size=self.batch_size,
            limit=self.limit,
            acquisition_function=self.acquisition_function,
            number_of_steps=self.number_of_steps,
            number_of_initial_points=self.number_of_initial_points,
            initial_point_generator=self.initial_point_generator,
            seed=self.seed,
            number_of_optimization_rounds=self.number_of_optimization_rounds,
            sampling_variance=self.sampling_variance,
            samples_for_evaluation=self.samples_for_evaluation,
            maximum_number_of_sampling_steps=self.maximum_number_of_sampling_steps,
        )

    def validate_item(self, item: str) -> SmallMolecule:
        """Check that item is a valid SMILES.

        Args:
            item: a generated item that is possibly not valid.

        Raises:
            InvalidItem: in case the item can not be validated.

        Returns:
            the validated SMILES.
        """
        (
            molecules,
            _,
        ) = validate_molecules([item])
        if molecules[0] is None:
            raise InvalidItem(
                title="InvalidSMILES",
                detail=f'rdkit.Chem.MolFromSmiles returned None for "{item}"',
            )
        return SmallMolecule(item)
