import math

import numpy as np
from ichor.core.models.kernels.kernel import Kernel


class MixedKernelWithDerivatives(Kernel):
    r"""
    Implementation of the mixed kernel, where the rbf dimensions are used for non-cyclic dimensions
    and the periodic kernel is used for cyclic dimensions (phi dimensions).

    Also adds first and second derivatives of the mixed kernel which are used to train on the total
    system energy with gradient information.
    """

    def __init__(
        self,
        name: str,
        rbf_thetas: np.ndarray,
        periodic_thetas: np.ndarray,
        periodic_period_lengths: np.ndarray,
        rbf_dimensions: np.ndarray,
        periodic_dimensions: np.ndarray,
    ):

        ndims = len(rbf_dimensions + periodic_dimensions)
        active_dims = np.arange(ndims)

        super().__init__(name, active_dims)
        self._rbf_thetas = rbf_thetas
        self._periodic_thetas = periodic_thetas
        self.period_length = periodic_period_lengths

        self.rbf_dimensions = rbf_dimensions
        self.periodic_dimensions = periodic_dimensions

    @property
    def rbf_lengthscales(self):
        return np.sqrt(1.0 / (2 * self._rbf_thetas))

    @property
    def periodic_lengthscales(self):
        """Note that the lengthscales are already squared for the periodic kernel. But still,
        thetas are defined to be 1/(2l). (where l here is the already squared true lengthscale)"""
        return 1.0 / (2.0 * self._periodic_thetas)

    @property
    def lengthscale(self) -> np.ndarray:
        """Returns a 1D array of lengtshcales for both RBF and periodic which
        are ordered correctly (i.e. first 3 lengthscales are RBF ones, then it repeats RBF RBF Periodic)
        """
        l = []
        iter_rbf_dims = iter(self.rbf_lengthscales)
        iter_periodic_lengthscales = iter(self.periodic_lengthscales)

        for i in range(self.active_dims):
            if (i + 1) % 3 == 0 and i != 2:
                l.append(next(iter_periodic_lengthscales))
            else:
                l.append(next(iter_rbf_dims))

        return np.array(l)

    def k(self, x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
        """
        Calculates RBF covariance matrix from two sets of points

        Args:
            :param: `x1` np.ndarray of shape n x ndimensions:
                First matrix of n points
            :param: `x2` np.ndarray of shape m x ndimensions:
                Second matrix of m points, can be identical to the first matrix `x1`

        Returns:
            :type: `np.ndarray`
                The RBF covariance matrix of shape (n, m)
        """
        # Get lengthscale
        lengthscale = self.lengthscale

        batch_shape = x1.shape[:-2]
        n_batch_dims = len(batch_shape)
        n1, d = x1.shape[-2:]
        n2 = x2.shape[-2]

        # this is the full matrix
        K = np.zeros(*batch_shape, n1 * (d + 1), n2 * (d + 1), dtype=x1.dtype)

        # shape of n1 x n2 x d
        diffs = x1.view(*batch_shape, n1, 1, d) - x2.view(*batch_shape, 1, n2, d)

        # rbf part of matrix
        # shape is n1 x n2 x nrbfdims
        rbf_part = diffs[..., self.rbf_dimensions] ** 2
        rbf_part = rbf_part / lengthscale[..., self.rbf_dimensions].unsqueeze(-2)
        # sum over nrbfdims
        rbf_part = rbf_part.sum(-1).mul(-0.5)

        # # shape is n1 x n2 x nperiodic
        periodic_part = diffs[..., self.periodic_dimensions].mul(
            math.pi / self.period_length[..., self.periodic_dimensions].unsqueeze(-2)
        )
        periodic_part = periodic_part.sin().pow(2.0)
        periodic_part = (
            periodic_part.div(lengthscale[..., self.periodic_dimensions].unsqueeze(-2))
            .sum(-1)
            .mul(-2.0)
        )

        # # 1) Kernel block
        # # directly use the already implemented RBF and PeriodicKernel methods
        K[..., :n1, :n2] = np.exp(rbf_part + periodic_part)

        # Form all possible rank-1 products for the gradient and Hessian blocks
        # rbf dx_i^n first

        periodic_dims_zeros_ones_tensor = np.array(
            [[1 if i in self.periodic_dimensions else 0 for i in range(d)]],
            dtype=x1.dtype,
        )
        rbf_dims_zeros_ones_tensor = np.array(
            [[1 if i in self.rbf_dimensions else 0 for i in range(d)]], dtype=x1.dtype
        )
        # possibly transform this kron back into a n1 x n2 x d matrix
        periodic_mask_dx_i_n = np.kron(
            periodic_dims_zeros_ones_tensor,
            np.ones(*batch_shape, n1, n2, dtype=x1.dtype),
        )
        rbf_mask_dx_i_n = np.kron(
            rbf_dims_zeros_ones_tensor, np.ones(*batch_shape, n1, n2, dtype=x1.dtype)
        )

        # outer1 here is the rbf part, but name as the final variable, and use inplace operations to save memory
        # divide each dimension by the lengthscale
        outer1 = diffs / self.lengthscale.unsqueeze(-2)
        # get n1 x n2 x d tensor
        outer1 = np.transpose(outer1, -1, -2).contiguous()
        # get n1 x n2 * d tensor
        outer1 = outer1.reshape(*batch_shape, n1, n2 * d)
        # multiply by mask so that periodic dimensions are 0
        outer1 = outer1.mul_(rbf_mask_dx_i_n.to_dense())

        outer_topright_periodic = diffs * (
            ((2 * math.pi) / self.period_length.unsqueeze(-2))
        )
        outer_topright_periodic = np.sin(outer_topright_periodic) * (
            2
            * math.pi
            / (self.lengthscale.unsqueeze(-2) * self.period_length.unsqueeze(-2))
        )
        outer_topright_periodic = np.transpose(
            outer_topright_periodic, -1, -2
        ).contiguous()
        outer_topright_periodic = outer_topright_periodic.view(*batch_shape, n1, n2 * d)
        outer_topright_periodic = (
            outer_topright_periodic * periodic_mask_dx_i_n.to_dense()
        )

        outer1.add_(outer_topright_periodic)

        K[..., :n1, n2:] = outer1 * K[..., :n1, :n2].repeat(
            [*([1] * (n_batch_dims + 1)), d]
        )

        # todo: implemt this as n1 x n2 x d directly and to work on the distance matrix, that will save some space
        periodic_mask_dx_j_m = np.kron(
            periodic_dims_zeros_ones_tensor,
            np.ones(*batch_shape, n2, n1, dtype=x1.dtype),
        ).transpose(-2, -1)
        rbf_mask_dx_j_m = np.kron(
            rbf_dims_zeros_ones_tensor, np.ones(*batch_shape, n2, n1, dtype=x1.dtype)
        ).transpose(-2, -1)

        # save some memory by naming outer_bottomleft_rbf as outer2
        # and use inplace operations
        outer2 = diffs / self.lengthscale.unsqueeze(-2)  # n1 x n2 x d
        outer2 = np.transpose(outer2, -1, -2).contiguous()  # n1 x d x n2
        outer2 = outer2.transpose(-3, -1)  # n2 x d x n1
        outer2 = outer2.reshape(*batch_shape, n2, n1 * d)  # n2 x n1 * d
        outer2 = outer2.transpose(-1, -2)  # n1 * d x n2
        outer2.mul_(rbf_mask_dx_j_m.to_dense())  # n1 * d x n2

        outer_bottomleft_periodic = diffs * (
            ((2 * math.pi) / self.period_length.unsqueeze(-2))
        )  # n1 x n2 x d
        outer_bottomleft_periodic = np.sin(outer_bottomleft_periodic) * (
            2
            * math.pi
            / (self.lengthscale.unsqueeze(-2) * self.period_length.unsqueeze(-2))
        )
        outer_bottomleft_periodic = np.transpose(
            outer_bottomleft_periodic, -1, -2
        ).contiguous()  # n1 x d x n2
        outer_bottomleft_periodic = outer_bottomleft_periodic.transpose(
            -3, -1
        )  # n2 x d x n1
        outer_bottomleft_periodic = outer_bottomleft_periodic.reshape(
            *batch_shape, n2, n1 * d
        )
        outer_bottomleft_periodic = outer_bottomleft_periodic.transpose(-2, -1)
        outer_bottomleft_periodic = (
            outer_bottomleft_periodic * periodic_mask_dx_j_m.to_dense()
        )

        outer2.add_(outer_bottomleft_periodic)

        K[..., n1:, :n2] = -outer2 * K[..., :n1, :n2].repeat(
            [*([1] * n_batch_dims), d, 1]
        )

        # make mask arrays for dxjm_dxin part of matrix.
        rbf_mask_dxjm_dxin = rbf_mask_dx_i_n.to_dense().repeat(
            [*([1] * n_batch_dims), d, 1]
        ) * rbf_mask_dx_j_m.to_dense().repeat([*([1] * (n_batch_dims + 1)), d])
        periodic_mask_dxjm_dxin = periodic_mask_dx_i_n.to_dense().repeat(
            [*([1] * n_batch_dims), d, 1]
        ) * periodic_mask_dx_j_m.to_dense().repeat([*([1] * (n_batch_dims + 1)), d])

        # make mask for elements where both rbf and periodic derivatives are needed
        mask_i_P_j_R = rbf_mask_dx_i_n.to_dense().repeat(
            [*([1] * n_batch_dims), d, 1]
        ) * periodic_mask_dx_j_m.to_dense().repeat(
            [*([1] * (n_batch_dims + 1)), d]
        ) + periodic_mask_dx_i_n.to_dense().repeat(
            [*([1] * n_batch_dims), d, 1]
        ) * rbf_mask_dx_j_m.to_dense().repeat(
            [*([1] * (n_batch_dims + 1)), d]
        )

        outer3 = outer1.repeat([*([1] * n_batch_dims), d, 1]) * -outer2.repeat(
            [*([1] * (n_batch_dims + 1)), d]
        )

        # # 4) Hessian block kronecker for rbf part
        kp_rbf = np.kron(
            np.eye(d, d, dtype=x1.dtype).repeat(*batch_shape, 1, 1) / self.lengthscale,
            np.ones(n1, n2, dtype=x1.dtype).repeat(*batch_shape, 1, 1),
        )

        # # 4) Hessian block for periodic part
        kp_periodic = np.kron(
            np.eye(d, d, dtype=x1.dtype).repeat(*batch_shape, 1, 1)
            / self.period_length,
            np.ones(n1, n2, dtype=x1.dtype).repeat(*batch_shape, 1, 1),
        )

        periodic_kp_outer3 = diffs * (
            (2 * math.pi) / (self.period_length.unsqueeze(-2))
        )
        periodic_kp_outer3 = (
            (4 * math.pi**2)
            / (self.period_length.unsqueeze(-2) * self.lengthscale.unsqueeze(-2))
        ) * np.cos(periodic_kp_outer3)
        periodic_kp_outer3 = np.transpose(periodic_kp_outer3, -1, -2).contiguous()
        periodic_kp_outer3 = kp_periodic.to_dense() * periodic_kp_outer3.view(
            *batch_shape, n1, n2 * d
        ).repeat([*([1] * n_batch_dims), d, 1])

        # from matplotlib import pyplot as plt
        # plt.matshow(mask_i_P_j_R.detach().numpy())
        # plt.show()

        mixed_part3 = outer3 * mask_i_P_j_R
        mixed_part3.add_((kp_rbf.to_dense() + outer3) * rbf_mask_dxjm_dxin)
        mixed_part3.add_((periodic_kp_outer3 + outer3) * periodic_mask_dxjm_dxin)

        K[..., n1:, n2:] = mixed_part3 * K[..., :n1, :n2].repeat(
            [*([1] * n_batch_dims), d, d]
        )

        # Symmetrize for stability
        if n1 == n2 and np.eq(x1, x2).all():
            K = 0.5 * (K.transpose(-1, -2) + K)

        # do not need to shuffle here like in gpytorch because the ordering in the model files
        # should not need reordering because the weights are split into alpha (energy weights)
        # and beta (gradient weights)

        # Apply a perfect shuffle permutation to match the MutiTask ordering
        # pi1 = np.arange(n1 * (d + 1)).view(d + 1, n1).t().reshape((n1 * (d + 1)))
        # pi2 = np.arange(n2 * (d + 1)).view(d + 1, n2).t().reshape((n2 * (d + 1)))
        # K = K[..., pi1, :][..., :, pi2]

        return K

    def write_str(self) -> str:

        str_to_write = ""

        str_to_write += f"[kernel.{self.name}]\n"
        str_to_write += "type constant\n"
        str_to_write += f"number_of_dimensions {len(self.active_dims)}\n"
        str_to_write += f"active_dimensions {' '.join(map(str, self.active_dims+1))}\n"
        str_to_write += f"thetas {' '.join(map(str, self._thetas))}\n"

        return str_to_write

    def __repr__(self):

        lengthscales = self.lengthscales

        return f"{self.__class__.__name__}: lengthscales: {lengthscales}"
