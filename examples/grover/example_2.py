from qibo import gates
from qibo.models.grover import Grover
from qibo.models import Circuit
import numpy as np
from scipy.special import binom

qubits = 10
num_1 = 2

def one_sum(sum_qubits):
    c = Circuit(sum_qubits + 1)

    for q in range(sum_qubits, 0, -1):
        c.add(gates.X(q).controlled_by(*range(0, q)))

    return c

def sum_circuit(qubits):
    sum_qubits = int(np.ceil(np.log2(qubits))) + 1
    sum_circuit = Circuit(qubits + sum_qubits)
    sum_circuit.add(gates.X(qubits).controlled_by(0))
    sum_circuit.add(gates.X(qubits).controlled_by(1))
    sum_circuit.add(gates.X(qubits + 1).controlled_by(*[0,1]))

    for qub in range(2, qubits):
        sum_circuit.add(one_sum(sum_qubits).on_qubits(*([qub] + list(range(qubits, qubits + sum_qubits)))))

    return sum_circuit

def oracle(qubits, num_1):
    sum = sum_circuit(qubits)
    oracle=Circuit(sum.nqubits + 1)
    oracle.add(sum.on_qubits(*range(sum.nqubits)))

    booleans = np.binary_repr(num_1, int(np.ceil(np.log2(qubits)) + 1))

    for i, b in enumerate(booleans[::-1]):
        if b=='0': oracle.add(gates.X(qubits + i))

    oracle.add(gates.X(sum.nqubits).controlled_by(*range(qubits, sum.nqubits)))

    for i, b in enumerate(booleans[::-1]):
        if b=='0': oracle.add(gates.X(qubits + i))

    oracle.add(sum.invert().on_qubits(*range(sum.nqubits)))

    return oracle

def check(instance, num_1):
    res = instance.count('1') == num_1
    return res


oracle = oracle(qubits, num_1)

#################################################################
###################### NON ITERATIVE MODEL ######################
#################################################################

grover = Grover(oracle, superposition_qubits=qubits, number_solutions=int(binom(qubits, num_1)))


solution, iterations = grover()

print('NON ITERATIVE MODEL: \n\n')

print('The solution is', solution)
print('Number of iterations needed:', iterations)
print('\nFound number of solutions: ',len(solution),'\nTheoretical number of solutions:', int(binom(qubits, num_1)))

#################################################################
######################## ITERATIVE MODEL ########################
#################################################################

print('ITERATIVE MODEL: \n\n')


grover = Grover(oracle, superposition_qubits=qubits, check=check, check_args=(num_1,))
solution, iterations = grover()

print('Found solution:', solution)
