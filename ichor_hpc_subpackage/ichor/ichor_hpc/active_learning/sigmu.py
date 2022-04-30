import numpy as np

from ichor.active_learning.active_learning_method import ActiveLearningMethod
from ichor.atoms import ListOfAtoms
from ichor.ichor_lib.common.functools import classproperty
from ichor.models import Models


# todo: update docstrings
class SigMu(ActiveLearningMethod):
    """Active learning method which calculates the variance of the sample pool points (given the models) and adds
    points with the highest variance to the training set.

    .. note::
        Only one point, the one with the highest variance in the sample pool, is added by default.
    """

    def __init__(self, models: Models):
        super().__init__(models)

    @classproperty
    def name(self) -> str:
        return "sigmu"

    def get_points(self, points: ListOfAtoms, npoints: int) -> np.ndarray:
        """Gets points with the highest calculated variance and adds to the training set.

        :param points: A ListOfAtoms instance for which to calculate the variance
        :param npoints: The number of points with highest variance to add to the training set
        :return: The indices of the points which should be added to the training set.
        """

        sigmu = np.array([])
        for batched_points in self.batch_points(points):
            features_dict = self.models.get_features_dict(batched_points)
            sigmu = np.hstack(
                (
                    sigmu,
                    self.models.variance(features_dict).reduce(-1)
                    * np.abs(self.models.predict(features_dict).reduce(-1)),
                )
            )

        # sort the array from smallest to largest, but give only the indeces back. Then flip the indeces, so that
        # the point index with the largest variance is first. Finally, get the desired number of points
        return np.flip(np.argsort(sigmu), axis=-1)[:npoints]