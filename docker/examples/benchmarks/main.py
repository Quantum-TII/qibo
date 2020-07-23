"""
Generic benchmark script that runs circuits defined in `benchmark_models.py`.

The type of the circuit is selected using the ``--type`` flag.
"""
import argparse
import os
import time
from typing import Dict, List, Optional

_PARAM_NAMES = {"theta", "phi"}
parser = argparse.ArgumentParser()
parser.add_argument("--nqubits", default="20", type=str)
parser.add_argument("--backend", default="custom", type=str)
parser.add_argument("--type", default="qft", type=str)
parser.add_argument("--fuse", action="store_true")
parser.add_argument("--nlayers", default=None, type=int)
parser.add_argument("--gate-type", default=None, type=str)
parser.add_argument("--nshots", default=None, type=int)
parser.add_argument("--device", default="/CPU:0", type=str)
parser.add_argument("--accelerators", default=None, type=str)
parser.add_argument("--memory", default=None, type=int)
parser.add_argument("--directory", default=None, type=str)
parser.add_argument("--name", default=None, type=str)
parser.add_argument("--compile", action="store_true")
parser.add_argument("--precision", default="double", type=str)
# params
parser.add_argument("--theta", default=None, type=float)
parser.add_argument("--phi", default=None, type=float)
args = vars(parser.parse_args())


import tensorflow as tf
def limit_gpu_memory(memory_limit=None):
    """Limits GPU memory that is available to Tensorflow.

    Args:
        memory_limit: Memory limit in MBs.
    """
    if memory_limit is None:
        print("\nNo GPU memory limiter used.\n")
        return

    print("\nAttempting to limit GPU memory to {}.\n".format(memory_limit))
    gpus = tf.config.list_physical_devices("GPU")
    for gpu in tf.config.list_physical_devices("GPU"):
        config = tf.config.experimental.VirtualDeviceConfiguration(
                      memory_limit=memory_limit)
        tf.config.experimental.set_virtual_device_configuration(gpu, [config])
        print("Limiting memory of {} to {}.".format(gpu.name, memory_limit))
    print()

limit_gpu_memory(args.pop("memory"))

import qibo
qibo.set_backend(args.pop("backend"))
qibo.set_precision(args.pop("precision"))
import circuits
import utils


def main(nqubits_list: List[int],
         type: str,
         device: Optional[str] = "/CPU:0",
         accelerators: Optional[Dict[str, int]] = None,
         fuse: bool = False,
         nlayers: Optional[int] = None,
         gate_type: Optional[str] = None,
         params: Dict[str, float] = {},
         nshots: Optional[int] = None,
         directory: Optional[str] = None,
         name: Optional[str] = None,
         compile: bool = False):
    """Runs benchmarks for the Quantum Fourier Transform.

    If `directory` is specified this saves an `.h5` file that contains the
    following keys:
        * nqubits: List with the number of qubits that were simulated.
        * simulation_time: List with simulation times for each number of qubits.
        * compile_time (optional): List with compile times for each number of
            qubits. This is saved only if `compile` is `True`.

    Args:
        nqubits_list: List with the number of qubits to run for.
        type: Type of Circuit to use.
            See ``benchmark_models.py`` for available types.
        device: Tensorflow logical device to use for the benchmark.
            If ``None`` the first available device is used.
        nlayers: Number of layers for supremacy-like or gate circuits.
            If a different circuit is used ``nlayers`` is ignored.
        gate_type: Type of gate for gate circuits.
            If a different circuit is used ``gate_type`` is ignored.
        params: Gate parameter for gate circuits.
            If a non-parametrized circuit is used then ``params`` is ignored.
        nshots: Number of measurement shots.
        directory: Directory to save the log files.
            If ``None`` then logs are not saved.
        name: Name of the run to be used when saving logs.
            This should be specified if a directory in given. Otherwise it
            is ignored.
        compile: If ``True`` then the Tensorflow graph is compiled using
            ``circuit.compile()``. In this case the compile time is also logged.

    Raises:
        FileExistsError if the file with the `name` specified exists in the
        given `directory`.
    """
    if device is None:
        device = tf.config.list_logical_devices()[0].name

    if directory is not None:
        if name is None:
            raise ValueError("A run name should be given in order to save logs.")

        # Generate log file name
        log_name = [name]
        if compile:
            log_name.append("compiled")
        log_name = "{}.h5".format("_".join(log_name))
        # Generate log file path
        file_path = os.path.join(directory, log_name)
        if os.path.exists(file_path):
            raise FileExistsError("File {} already exists in {}."
                                  "".format(log_name, directory))

        print("Saving logs in {}.".format(file_path))

    # Create log dict
    logs = {"nqubits": [], "simulation_time": [], "creation_time": []}
    if compile:
        logs["compile_time"] = []

    # Set circuit type
    print("Running {} benchmarks.".format(type))

    for nqubits in nqubits_list:
        kwargs = {"nqubits": nqubits, "circuit_type": type}
        params = {k: v for k, v in params.items() if v is not None}
        if params: kwargs["params"] = params
        if nlayers is not None: kwargs["nlayers"] = nlayers
        if gate_type is not None: kwargs["gate_type"] = gate_type
        if accelerators is not None:
            kwargs["accelerators"] = accelerators
            kwargs["memory_device"] = device

        start_time = time.time()
        circuit = circuits.CircuitFactory(**kwargs)
        if fuse:
            circuit = circuit.fuse()
        logs["creation_time"].append(time.time() - start_time)

        try:
            actual_backend = circuit.queue[0].einsum.__class__.__name__
        except AttributeError:
            actual_backend = "Custom"

        print("\nBenchmark parameters:", kwargs)
        print("Actual backend:", actual_backend)
        with tf.device(device):
            if compile:
                start_time = time.time()
                circuit.compile()
                # Try executing here so that compile time is not included
                # in the simulation time
                final_state = circuit.execute(nshots=nshots)
                logs["compile_time"].append(time.time() - start_time)

            start_time = time.time()
            final_state = circuit.execute(nshots=nshots)
            logs["simulation_time"].append(time.time() - start_time)

        logs["nqubits"].append(nqubits)

        # Write updated logs in file
        if directory is not None:
            utils.update_file(file_path, logs)

        # Print results during run
        print("Creation time:", logs["creation_time"][-1])
        if compile:
            print("Compile time:", logs["compile_time"][-1])
        print("Simulation time:", logs["simulation_time"][-1])
        print("Final dtype:", final_state.dtype)


if __name__ == "__main__":
    args["nqubits_list"] = utils.parse_nqubits(args.pop("nqubits"))
    args["accelerators"] = utils.parse_accelerators(args.pop("accelerators"))
    args["params"] = {k: args.pop(k) for k in _PARAM_NAMES}
    main(**args)
