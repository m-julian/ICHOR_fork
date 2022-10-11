import json
from typing import Dict

import numpy as np
import numpy.linalg as la
import pandas as pd
from ichor.core.atoms import ListOfAtoms
from ichor.core.common.functools import classproperty
from ichor.core.models import Model, Models
from ichor.hpc.active_learning.active_learning_method import (
    ActiveLearningMethod,
)
from scipy.spatial.distance import cdist
from ichor.core.common.io import mkdir
from ichor.core.common.np import ensure_array

"""
    Implementation of the Maximum Expected Prediction Error (MEPE) method
    
    Liu, H., Cai, J., Ong, Y.-S., 2017.
    An adaptive sampling approach for Kriging metamodeling by maximizing expected prediction error.
    Computers & Chemical Engineering 106, 171–182..
    doi:10.1016/j.compchemeng.2017.05.025
    
    Equation numbers provided above relevant code
"""


def B(model: Model) -> float:
    """Eq. 6"""
    return np.matmul(
        (
            la.inv(
                np.matmul(
                    np.matmul(np.ones((1, model.ntrain)), model.invR),
                    np.ones((model.ntrain, 1)),
                )
            )
        ),
        np.matmul(np.matmul(np.ones((1, model.ntrain)), model.invR), model.y),
    ).item()


def H(ntrain: int) -> np.ndarray:
    """Eq. 19"""
    return np.matmul(
        np.ones((ntrain, 1)),
        la.inv(np.matmul(np.ones((1, ntrain)), np.ones((ntrain, 1)))).item()
        * np.ones((1, ntrain)),
    )


def cross_validation(model: Model) -> np.ndarray:
    """Eq. 18"""
    d = (model.y - B(model)).reshape((-1, 1))
    h = H(model.ntrain)

    """Eq. 17"""
    cross_validation_error = np.empty(model.ntrain)
    for i in range(model.ntrain):
        cross_validation_error[i] = (
            np.matmul(
                model.invR[i, :],
                (d + (d[i] / h[i][i]) * h[:][i].reshape((-1, 1))),
            )
            / model.invR[i][i]
        ).item() ** 2
    return cross_validation_error


class MEPE(ActiveLearningMethod):

    """Maximum Expected Prediction Errorr implementation for selecting new training data out of sample pool."""

    def __init__(self, models: Models):
        super().__init__(models)

    @classproperty
    def name(self) -> str:
        return "epe"

    def cv_error(self, x: Dict[str, np.ndarray]) -> pd.DataFrame:
        """Eq. 20. Calculate cross validation error."""
        cv_errors = {}
        for atom in self.models.atom_names:
            atom_cv_errors = {}
            for model in self.models[atom]:
                cv = cross_validation(model)
                distances = cdist(x[model.atom_name], model.x)
                atom_cv_errors[model.type] = cv[
                    distances.argmin(
                        axis=-1,
                    )
                ]
            cv_errors[atom] = atom_cv_errors
        return pd.DataFrame(cv_errors)

    @property
    def alpha(self) -> float:
        """alpha value is a balance factor which varies based on how well the cv error
        approximated the prediction error of the points added in the previous iteration.

        For the first iteration there are no previously added points therefore alpha defaults
        to 0.5, for each subsequent iteration, equation 24 of the above cited paper is used.
        """
        from ichor.hpc import FILE_STRUCTURE

        cv_errors_file = FILE_STRUCTURE["cv_errors"]
        if not cv_errors_file.exists():
            return 0.5  # if the cv_errors_file doesn't exist, there was no previous iteration and we can default to 0.5

        try:
            with open(
                cv_errors_file, 'r'
            ) as f:  # the previous iterations data is stored as json in cv_errors_file
                obj = json.load(f)
                npoints = obj["added_points"]
                cv_errors = obj["cv_errors"]
                predictions = obj["predictions"]
        except json.JSONDecodeError:
            return 0.5

        for atom, pred in predictions.items():
            for prop in pred.keys():
                predictions[atom][prop] = np.array(predictions[atom][prop])
                cv_errors[atom][prop] = np.array(cv_errors[atom][prop])

        alpha_sum = 0.0
        nalpha = 0
        for atom, data in predictions.items():
            for property, predicted_values in data.items():
                true_values = self.models[atom][property].y[-npoints:]
                true_error = (true_values - predicted_values) ** 2
                """Eq. 24"""
                alpha_sum += np.sum(
                    0.99
                    * np.clip(
                        0.5 * true_error / np.array(cv_errors[atom][property]),
                        0.0,
                        1.0,
                    )
                )
                nalpha += len(true_values)
        return alpha_sum / nalpha

    def get_points(self, points: ListOfAtoms, npoints: int) -> np.ndarray:
        """Gets the indeces of the points to add from the sample pool to the training set based on the maximum prediction
        error criteria

        :param points: An instance of ListOfAtoms (note than PointsDirectory inherits from ListOfAtoms)
        :param npoints: The number of points to add to the training set from the sample pool based on the EPE criteria.
        """

        epe = np.array([])
        for batched_points in self.batch_points(points):
            features_dict = self.models.get_features_dict(batched_points)
            cv_errors = self.cv_error(features_dict)
            variance = self.models.variance(features_dict)
            alpha = self.alpha
            """Eq. 23"""
            # todo: get max (and max indices) from batch
            epe = np.hstack(
                (
                    epe,
                    (alpha * cv_errors - (1.0 - alpha) * variance).sum().sum(),
                )
            )

        """Eq. 25"""
        mepe = np.flip(np.argsort(epe), axis=-1)[:npoints]

        mepe_points = points[mepe]

        features_dict = self.models.get_features_dict(mepe_points)
        cv_errors = self.cv_error(features_dict).to_dict()
        predictions = self.models.predict(features_dict).to_dict()

        for atom, pred in predictions.items():
            for prop in pred.keys():
                predictions[atom][prop] = list(predictions[atom][prop])
                cv_errors[atom][prop] = list(cv_errors[atom][prop])

        from ichor.hpc import FILE_STRUCTURE
        cv_file = FILE_STRUCTURE["cv_errors"]
        mkdir(cv_file.parent)
        if cv_file.exists():
            cv_file.unlink()  # delete previous cv_errors to prevent bug where extra closing brackets were present
        with open(cv_file, 'w') as f:  # store data as json for next iterations alpha calculation
            json.dump(
                {
                    "added_points": npoints,
                    "cv_errors": cv_errors,
                    "predictions": predictions,
                },
                f,
            )

        return mepe
