import sys
import logging
import os

from siminterface.simulator import Simulator
from algorithms.greedy.gpasp import GPASPAlgo
from algorithms.tour.spr1 import SPR1Algo
from algorithms.tour.spr2 import SPR2Algo

log = logging.getLogger(__name__)


def main():
    version = sys.argv[1]
    scenario = sys.argv[2]
    run = sys.argv[3]
    network_path = sys.argv[4]
    network = os.path.basename(network_path)
    ingress = sys.argv[5]
    algo_id = sys.argv[6]

    args = {
        'network': network_path,
        'service_functions': '../../../../params/services/3sfcs.yaml',
        'resource_functions': '../../../../params/services/resource_functions',
        'config': f'configurations/{scenario}_{ingress}.yaml',
        'seed': int(run),
        'output_path': f'scenarios/{version}/{scenario}/{run}/{network}/{ingress}/{algo_id}'
    }

    os.makedirs(args['output_path'], exist_ok=True)

    logging.getLogger('coordsim').setLevel(logging.CRITICAL)
    logging.getLogger('coordsim.reader').setLevel(logging.CRITICAL)

    simulator = Simulator(test_mode=True)

    # Setup algorithm
    algo = None
    if algo_id == 'gpasp':
        algo = GPASPAlgo(simulator)
    elif algo_id == 'spr1':
        algo = SPR1Algo(simulator)
    elif algo_id == 'spr2':
        algo = SPR2Algo(simulator)

    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'],
              args['output_path'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()
    print(f'{scenario}-{run}-{os.path.basename(network)}-{ingress}-{algo_id}')


if __name__ == "__main__":
    main()