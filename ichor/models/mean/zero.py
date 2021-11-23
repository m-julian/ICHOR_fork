import numpy as np
from typing import IO

from ichor.models.mean.mean import Mean


class ZeroMean(Mean):
    """Implements a zero mean for the Gaussian Process. When covariance between training points and a test point is low, this means the GP will return the
    mean of the GP (in this case it is set to 0)."""

    def value(self, x: np.ndarray) -> np.ndarray:
        """Return 0 as this is a Zero Mean Gaussian Process"""
        return np.zeros((x.shape[0]))

    def write(self, f: IO):
        f.write("[mean]\n")
        f.write("type zero\n")
