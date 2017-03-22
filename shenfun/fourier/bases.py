import numpy as np
import pyfftw
from mpiFFT4py import rfft, fft, irfft, ifft
from shenfun.spectralbase import SpectralBase
from shenfun.utilities import inheritdocstrings

__all__ = ['FourierBase', 'R2CBasis', 'C2CBasis']


@inheritdocstrings
class FourierBase(SpectralBase):
    """Fourier base class
    """

    def __init__(self, N, threads=1):
        SpectralBase.__init__(self, N, '')
        self.N = N

    def points_and_weights(self):
        """Return points and weights of quadrature"""
        points = np.arange(self.N, dtype=np.float)*2*np.pi/self.N
        return points, np.array([2*np.pi/self.N])

    def vandermonde(self, x):
        """Return Vandermonde matrix

        args:
            x               points for evaluation

        """
        k = self.wavenumbers(self.N, 0)
        return np.exp(1j*x[:, np.newaxis]*k[np.newaxis, :])

    def get_vandermonde_basis_derivative(self, V, d=0):
        """Return k'th derivative of basis as a Vandermonde matrix

        args:
            V               Chebyshev Vandermonde matrix

        kwargs:
            k    integer    k'th derivative

        """
        if d > 0:
            k = self.wavenumbers(self.N, 0)
            V = V*((1j*k)**d)[np.newaxis, :]
        return V

    def get_mass_matrix(self):
        from .matrices import mat
        return mat[(self.__class__, 0), (self.__class__, 0)]

    def apply_inverse_mass(self, array):
        """Apply inverse mass, which is identity for Fourier basis

        args:
            array   (input/output)    Expansion coefficients

        """
        assert array is self.xfftn_fwd.output_array
        array *= (0.5/np.pi)
        return array

    def evaluate_expansion_all(self, input_array, output_array):
        self.xfftn_bck()
        output_array *= self.N
        return output_array

    def scalar_product(self, input_array=None, output_array=None, fast_transform=True):
        if input_array is not None:
            self.xfftn_fwd.input_array[...] = input_array

        if fast_transform:
            output = self.xfftn_fwd()
            output *= (2*np.pi/self.N)

        else:
            self.vandermonde_scalar_product(self.xfftn_fwd.input_array,
                                            self.xfftn_fwd.output_array)

        if output_array is not None:
            output_array[...] = self.xfftn_fwd.output_array
            return output_array
        else:
            return self.xfftn_fwd.output_array


class R2CBasis(FourierBase):
    """Fourier basis class for real to complex transforms
    """

    def __init__(self, N, plan=False):
        FourierBase.__init__(self, N, '')
        self.N = N
        self._xfftn_fwd = pyfftw.builders.rfft
        self._xfftn_bck = pyfftw.builders.irfft
        if plan:
            self.plan((N,), 0, np.float, {})

    def wavenumbers(self, N, axis=0):
        """Return the wavenumbermesh

        All dimensions, except axis, are obtained through broadcasting.

        """
        N = list(N) if np.ndim(N) else [N]
        assert self.N == N[axis]
        k = np.fft.rfftfreq(N[axis], 1./N[axis])
        K = self.broadcast_to_ndims(k, len(N), axis)
        return K

    def eval(self, x, fk):
        V = self.vandermonde(x)
        return np.dot(V, fk) + np.conj(np.dot(V[:, 1:-1], fk[1:-1]))

    def slice(self):
        return slice(0, self.N//2+1)

    def vandermonde_evaluate_expansion_all(self, input_array, output_array):
        """Naive implementation of evaluate_expansion_all

        args:
            input_array    (input)    Expansion coefficients
            output_array   (output)   Function values on quadrature mesh

        """
        assert self.N == output_array.shape[self.axis]
        points = self.points_and_weights()[0]
        P = self.vandermonde(points)
        if output_array.ndim == 1:
            output_array[:] = np.dot(P, input_array).real
            output_array += np.dot(P[:, 1:-1], np.conj(input_array[1:-1])).real
        else:
            fc = np.moveaxis(input_array, self.axis, -2)
            array = np.dot(P, fc).real
            s = [slice(None)]*fc.ndim
            s[-2] = slice(1, -1)
            array += np.conj(np.dot(P[:, 1:-1], fc[s])).real
            output_array[:] = np.moveaxis(array, 0, self.axis)

        assert output_array is self.backward.output_array
        assert input_array is self.backward.input_array
        return output_array


class C2CBasis(FourierBase):
    """Fourier basis class for complex to complex transforms
    """

    def __init__(self, N):
        FourierBase.__init__(self, N, '')
        self.N = N
        self._xfftn_fwd = pyfftw.builders.fft
        self._xfftn_bck = pyfftw.builders.ifft

    def wavenumbers(self, N, axis=0):
        """Return the wavenumbermesh

        All dimensions, except axis, are obtained through broadcasting.

        """
        N = list(N) if np.ndim(N) else [N]
        assert self.N == N[axis]
        k = np.fft.fftfreq(N[axis], 1./N[axis])
        K = self.broadcast_to_ndims(k, len(N), axis)
        return K

    def eval(self, x, fk):
        V = self.vandermonde(x)
        return np.dot(V, fk)

    def slice(self):
        return slice(0, self.N)

    def vandermonde_evaluate_expansion_all(self, input_array, output_array):
        """Naive implementation of evaluate_expansion_all

        args:
            input_array    (input)    Expansion coefficients
            output_array   (output)   Function values on quadrature mesh

        """
        assert self.N == output_array.shape[self.axis]
        points = self.points_and_weights()[0]
        V = self.vandermonde(points)
        P = self.get_vandermonde_basis(V)
        if output_array.ndim == 1:
            output_array = np.dot(P, input_array, out=output_array)
        else:
            fc = np.moveaxis(input_array, self.axis, -2)
            array = np.dot(P, fc)
            output_array[:] = np.moveaxis(array, 0, self.axis)

        assert output_array is self.backward.output_array
        assert input_array is self.backward.input_array
        return output_array
