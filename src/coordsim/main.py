import argparse
import simpy
import random
from coordsim.simulation import flowsimulator
from coordsim.reader import networkreader
import logging


def main():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

    default_seed = 9999

    # Read CLI arguments
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration")
    parser.add_argument('-r', '--rate', required=False, default=None, dest="rate")
    parser.add_argument('-s', '--seed', required=False, default=default_seed, dest="seed")
    parser.add_argument('-n', '--network', required=True, dest='network')
    parser.add_argument('-rm', '--randmean', required=False, default=1.0, dest="rand_mean")
    parser.add_argument('-p', '--placement', required=True, default=None, dest="placement")
    args = parser.parse_args()

    # Initialize environment (random seed and simpy.)
    random.seed(args.seed)
    env = simpy.Environment()

    nodes, links = networkreader.read_network(args.network, node_cap=10, link_cap=10)
    log.info("Coordination-Simulation")
    log.info("Using seed {} and using mean {}\n".format(args.seed, args.rand_mean))

    # Getting current placement of VNF's
    sf_placement, sfc_list = networkreader.network_update(args.placement)
    log.info("Total of {} nodes have VNF's placed in them\n".format(len(sf_placement)))

    # Begin simulation
    flowsimulator.start_simulation(env, nodes, float(args.rand_mean))
    env.run(until=args.duration)


if __name__ == '__main__':
    main()
