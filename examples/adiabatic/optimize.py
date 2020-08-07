"""Adiabatic evolution scheduling optimization for the Ising Hamiltonian."""
import argparse
import numpy as np
from qibo import callbacks, hamiltonians, models


parser = argparse.ArgumentParser()
parser.add_argument("--nqubits", default=4, type=int)
parser.add_argument("--hfield", default=1, type=float)
parser.add_argument("--T", default=1, type=float)
parser.add_argument("--dt", default=1e-2, type=float)
parser.add_argument("--solver", default="exp", type=str)
parser.add_argument("--method", default="BFGS", type=str)
parser.add_argument("--maxiter", default=None, type=int)
parser.add_argument("--save", action="store_true")


def main(nqubits, hfield, T, dt, solver, method, maxiter, save):
    """Optimizes the scheduling of the adiabatic evolution.

    Args:
        nqubits (int): Number of qubits in the system.
        hfield (float): TFIM transverse field h value.
        T (float): Total time of the adiabatic evolution.
        dt (float): Time step used for integration.
        solver (str): Solver used for integration.
        method (str): Optimization method.
        maxiter (int): Maximum iterations for scipy solvers.
        save (bool): Whether to save optimization history.
    """
    h0 = hamiltonians.X(nqubits)
    h1 = hamiltonians.TFIM(nqubits, h=hfield)

    # Calculate target values (H1 ground state)
    target_state = h1.eigenvectors()[:, 0]
    target_energy = h1.eigenvalues()[0].numpy().real

    # Check ground state
    state_energy = (target_state.numpy().conj() *
                    (h1 @ target_state).numpy()).sum()
    np.testing.assert_allclose(state_energy.real, target_energy)

    #s = lambda t, p: p[0] * t ** 3 + p[1] * t ** 2 + p[2] * t + (1 - p.sum()) * np.sqrt(t)
    s = lambda t: t
    evolution = models.AdiabaticEvolution(h0, h1, s, dt=dt, solver=solver)
    options = {"maxiter": maxiter}
    energy, parameters = evolution.minimize([T], method=method, options=options,
                                            messages=True)

    print("\nBest energy found:", energy)
    print("Final parameters:", parameters)

    final_state = evolution(parameters[-1])
    overlap = np.abs((target_state.numpy().conj() * final_state.numpy()).sum())
    print("Target energy:", target_energy)
    print("Overlap:", overlap)

    if save:
        evolution.opt_history["loss"].append(target_energy)
        np.save(f"optparams/linears_opt_n{nqubits}_loss.npy",
                evolution.opt_history["loss"])
        np.save(f"optparams/linears_opt_n{nqubits}_params.npy",
                evolution.opt_history["params"])


if __name__ == "__main__":
    args = vars(parser.parse_args())
    main(**args)