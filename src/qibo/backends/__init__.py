import os
from qibo import config
from qibo.config import raise_error, log, warnings


class Backend:

    def __init__(self):
        self.available_backends = {}
        active_backend = "numpy"

        # check if numpy is installed
        if self.check_availability("numpy"):
            from qibo.backends.numpy import NumpyDefaultEinsumBackend, NumpyMatmulEinsumBackend
            self.available_backends["numpy"] = NumpyDefaultEinsumBackend
            self.available_backends["numpy_defaulteinsum"] = NumpyDefaultEinsumBackend
            self.available_backends["numpy_matmuleinsum"] = NumpyMatmulEinsumBackend
        else:  # pragma: no cover
            raise_error(ModuleNotFoundError, "Numpy is not installed.")

        # check if tensorflow is installed and use it as default backend.
        if self.check_availability("tensorflow"):
            from qibo.backends.tensorflow import TensorflowDefaultEinsumBackend, TensorflowMatmulEinsumBackend
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = str(config.LOG_LEVEL)
            import tensorflow as tf
            self.available_backends["defaulteinsum"] = TensorflowDefaultEinsumBackend
            self.available_backends["matmuleinsum"] = TensorflowMatmulEinsumBackend
            self.available_backends["tensorflow_defaulteinsum"] = TensorflowDefaultEinsumBackend
            self.available_backends["tensorflow_matmuleinsum"] = TensorflowMatmulEinsumBackend
            import qibo.tensorflow.custom_operators as op
            if not op._custom_operators_loaded: # pragma: no cover
                log.warning("Einsum will be used to apply gates with Tensorflow. "
                            "Removing custom operators from available backends.")
                self.available_backends["tensorflow"] = TensorflowDefaultEinsumBackend
            else:
                from qibo.backends.tensorflow import TensorflowCustomBackend
                self.available_backends["custom"] = TensorflowCustomBackend
                self.available_backends["tensorflow"] = TensorflowCustomBackend
            active_backend = "tensorflow"
        else:  # pragma: no cover
            # case not tested because CI has tf installed
            log.warning("Tensorflow is not installed. Falling back to numpy. "
                        "Numpy does not support Qibo custom operators and GPU. "
                        "Einsum will be used to apply gates on CPU.")
            # use numpy for defaulteinsum and matmuleinsum backends
            self.available_backends["defaulteinsum"] = NumpyDefaultEinsumBackend
            self.available_backends["matmuleinsum"] = NumpyMatmulEinsumBackend

        self.constructed_backends = {}
        self._active_backend = None
        self.qnp = self.construct_backend("numpy_defaulteinsum")
        # Create the default active backend
        if "QIBO_BACKEND" in os.environ: # pragma: no cover
            self.active_backend = os.environ.get("QIBO_BACKEND")
        self.active_backend = active_backend

    @property
    def active_backend(self):
        return self._active_backend

    @active_backend.setter
    def active_backend(self, name):
        self._active_backend = self.construct_backend(name)

    def construct_backend(self, name):
        """Constructs and returns a backend.

        If the backend already exists in previously constructed backends then
        the existing object is returned.

        Args:
            name (str): Name of the backend to construct.
                See ``available_backends`` for the list of supported names.

        Returns:
            Backend object.
        """
        if name not in self.constructed_backends:
            if name not in self.available_backends:
                available = [" - {}: {}".format(n, b.description)
                             for n, b in self.available_backends.items()]
                available = "\n".join(available)
                raise_error(ValueError, "Unknown backend {}. Please select one of "
                                        "the available backends:\n{}."
                                        "".format(name, available))
            new_backend = self.available_backends.get(name)()
            if self.active_backend is not None:
                new_backend.set_precision(self.active_backend.precision)
                if self.active_backend.device is not None:
                    new_backend.set_device(self.active_backend.default_device)
            self.constructed_backends[name] = new_backend
        return self.constructed_backends.get(name)

    def __getattr__(self, x):
        return getattr(self.active_backend, x)

    def __str__(self):
        return self.active_backend.name

    def __repr__(self):
        return str(self)

    @staticmethod
    def check_availability(module_name):
        """Check if module is installed.

        Args:
            module_name (str): module name.

        Returns:
            True if the module is installed, False otherwise.
        """
        from pkgutil import iter_modules
        return module_name in (name for _, name, _ in iter_modules())


K = Backend()
numpy_matrices = K.qnp.matrices


def set_backend(backend="custom"):
    """Sets backend used for mathematical operations and applying gates.

    The following backends are available:
    'custom': Tensorflow backend with custom operators for applying gates,
    'defaulteinsum': Tensorflow backend that applies gates using ``tf.einsum``,
    'matmuleinsum': Tensorflow backend that applies gates using ``tf.matmul``,
    'numpy_defaulteinsum': Numpy backend that applies gates using ``np.einsum``,
    'numpy_matmuleinsum': Numpy backend that applies gates using ``np.matmul``,

    Args:
        backend (str): A backend from the above options.
    """
    if not config.ALLOW_SWITCHERS and backend != K.name:
        warnings.warn("Backend should not be changed after allocating gates.",
                      category=RuntimeWarning)
    K.active_backend = backend


def get_backend():
    """Get backend used to implement gates.

    Returns:
        A string with the backend name.
    """
    return K.name


def set_precision(dtype='double'):
    """Set precision for states and gates simulation.

    Args:
        dtype (str): possible options are 'single' for single precision
            (complex64) and 'double' for double precision (complex128).
    """
    if not config.ALLOW_SWITCHERS and dtype != K.precision:
        warnings.warn("Precision should not be changed after allocating gates.",
                      category=RuntimeWarning)
    for bk in K.constructed_backends.values():
        bk.set_precision(dtype)
        bk.matrices.allocate_matrices()


def get_precision():
    """Get precision for states and gates simulation.

    Returns:
        A string with the precision name ('single', 'double').
    """
    return K.precision


def set_device(name):
    """Set default execution device.

    Args:
        name (str): Device name. Should follow the pattern
            '/{device type}:{device number}' where device type is one of
            CPU or GPU.
    """
    if not config.ALLOW_SWITCHERS and name != K.default_device:
        warnings.warn("Device should not be changed after allocating gates.",
                      category=RuntimeWarning)
    for bk in K.constructed_backends.values():
        bk.set_device(name)
        with bk.device(bk.default_device):
            bk.matrices.allocate_matrices()


def get_device():
    return K.default_device
