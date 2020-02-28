# -*- coding: utf-8 -*-
# @authors: S. Carrazza and A. Garcia
from abc import ABCMeta, abstractmethod


class BaseCircuit(object):
    """This class implements the circuit object which holds all gates.

    Args:
        nqubits (int): number of quantum bits.

    Example:
        ::

            from qibo.models import Circuit
            c = Circuit(3) # initialized circuit with 3 qubits
    """

    __metaclass__ = ABCMeta

    def __init__(self, nqubits):
        """Initialize properties."""
        self.nqubits = nqubits
        self.queue = []

    def __add__(self, circuit):
        """Add circuits.

        Args:
            circuit: Circuit to be added to the current one.
        Return:
            The resulting circuit from the addition.
        """
        return BaseCircuit._circuit_addition(self, circuit)

    @classmethod
    def _circuit_addition(cls, c1, c2):
        if c1.nqubits != c2.nqubits:
            raise ValueError("Circuits of different size.")
        newcircuit = cls(c1.nqubits)
        for gate in c1.queue:
            newcircuit.add(gate)
        for gate in c2.queue:
            newcircuit.add(gate)
        return newcircuit

    def add(self, gate):
        """Add a gate to a given queue.

        Args:
            gate (qibo.gates): the specific gate (see :ref:`Gates`).
        """
        gate.nqubits = self.nqubits
        self.queue.append(gate)

    @property
    def size(self):
        """
        Return:
            number of qubits in the circuit
        """
        return self.nqubits

    @property
    def depth(self):
        """
        Return:
            number of gates/operations in the circuit
        """
        return len(self.queue)

    @abstractmethod
    def execute(self):
        """Executes the circuit on a given backend.

        Args:
            model: (qibo.models.Circuit): The circuit to be executed.
        Returns:
            The final wave function.
        """
        raise NotImplementedError