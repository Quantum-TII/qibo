from qibo import gates
from qibo.models import Circuit
import numpy as np
from scipy.special import binom as binomial
import itertools
from qibo.models import Grover

qubits = 10
num_1 = 9

def set_ancillas_to_num(ancillas, num):
    '''Set a quantum register to a specific number.

    '''
    ind = 0
    for i in reversed(bin(num)[2:]):
        if int(i) == 1:
            yield gates.X(ancillas[ind])
        ind += 1


def add_negates_for_check(ancillas, num):
    '''Adds the negates needed for control-on-zero.

    '''
    ind = 0
    for i in reversed(bin(num)[2:]):
        if int(i) == 0:
            yield gates.X(ancillas[ind])
        ind += 1
    for i in range(len(bin(num)[2:]), len(ancillas)):
        yield gates.X(ancillas[i])


def sub_one(ancillas, controls):
    '''Subtract 1 bit by bit.

    '''
    a = ancillas
    yield gates.X(a[0]).controlled_by(*controls)
    for i in range(1, len(a)):
        controls.append(a[i - 1])
        yield gates.X(a[i]).controlled_by(*controls)


def superposition_probabilities(n, r):
    '''Computes the probabilities to set the initial superposition.

    '''

    def split_weights(n, r):
        '''
        Auxiliary function that gets the required binomials.

        '''
        v0 = binomial(n - 1, r)
        v1 = binomial(n - 1, r - 1)
        return v0 / (v0 + v1), v1 / (v0 + v1)

    L = []
    for i in range(n):
        for j in range(min(i, r - 1), -1, -1):
            if n - i >= r - j:
                L.append([n - i, r - j, split_weights(n - i, r - j)])
    return L


def superposition_circuit(n, r):
    '''Creates an equal quantum superposition over the column choices.

    '''
    n_anc = int(np.ceil(np.log2(r + 1)))
    ancillas = [i for i in range(n, n + n_anc)]
    c = Circuit(n + n_anc)
    c.add(set_ancillas_to_num(ancillas, r))
    tmp = n
    L = superposition_probabilities(n, r)
    for i in L:
        if tmp != i[0]:
            c.add(sub_one(ancillas, [n - tmp]))
            tmp = i[0]

        if (i[2] == (0, 1)):
            c.add(add_negates_for_check(ancillas, i[1]))
            c.add(gates.X(n - i[0]).controlled_by(*ancillas))
            c.add(add_negates_for_check(ancillas, i[1]))
        else:
            if i[0] != n:
                c.add(add_negates_for_check(ancillas, i[1]))
                c.add(gates.RY(n - i[0], float(2 * np.arccos(np.sqrt(i[2][0])))).controlled_by(*ancillas))
                c.add(add_negates_for_check(ancillas, i[1]))
            else:
                c.add(gates.RY(0, float(2 * np.arccos(np.sqrt(i[2][0])))))
    c.add(sub_one(ancillas, [n - 1]))
    return c


def check_superposition(n, r, nshots=10000):
    '''Checks that the superposition has been created correctly.

    '''
    n_anc = int(np.ceil(np.log2(r + 1)))
    c = Circuit(n + n_anc)
    c += superposition_circuit(n, r)
    c.add(gates.M(*range(n)))
    result = c(nshots=nshots)
    print('-' * 37)
    print('| Column choices  | Probability     |')
    print('-' * 37)
    for i in result.frequencies():
        print('|', i, ' ' * (14 - n), '|', result.frequencies()[i] / nshots,
              ' ' * (14 - len(str(result.frequencies()[i] / nshots))), '|')
        print('-' * 37)
    print('\n')


def oracle(n, s):
    """
    Oracle checks whether the first s terms are 1
    :param n:
    :param r:
    :return:
    """
    if s > 2:
        n_anc = s - 2
        oracle = Circuit(n + n_anc + 1)
        oracle_1 = Circuit(n + n_anc + 1)
        oracle_1.add(gates.X(n + 1).controlled_by(*(0, 1)))
        for q in range(2, s-1):
            oracle_1.add(gates.X(n + q).controlled_by(*(q , n + q - 1)))


        oracle.add(oracle_1.on_qubits(*(range(n + n_anc + 1))))
        oracle.add(gates.X(n).controlled_by(*(s - 1, n + n_anc)))
        oracle.add(oracle_1.invert().on_qubits(*(range(n + n_anc + 1))))

        return oracle

    else:
        oracle = Circuit(n + int(np.ceil(np.log2(s + 1))) + 1)
        oracle.add(gates.X(n).controlled_by(*range(s)))

        return oracle

oracle = oracle(qubits, num_1)

or_circuit = Circuit(oracle.nqubits)

or_circuit.add(oracle.on_qubits(*(list(range(qubits)) + [oracle.nqubits - 1] + list(range(qubits, oracle.nqubits - 1)))))

superposition = superposition_circuit(qubits, num_1)

superposition.add(gates.M(*range(superposition.nqubits)))

grover = Grover(or_circuit, superposition_circuit=superposition, superposition_qubits=qubits, number_solutions=1,
                superposition_size=int(binomial(qubits, num_1)))

'''for i in range(26):
    print(grover.circuit(i).execute(nshots=10000).frequencies())'''

'''print(grover.oracle.draw())
print(grover.superposition.draw())'''
solution, iterations = grover()

print('The solution is', solution)
print('Number of iterations needed:', iterations)

