from qibo.config import BACKEND_NAME
if BACKEND_NAME == "tensorflow":
    from qibo.tensorflow.callbacks import *
else:
    raise NotImplementedError("Only Tensorflow backend is implemented.")
