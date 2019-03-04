import argparse
import simpy
import random
from coordsim.simulation import flowsimulator


def main():
    default_seed = 9999

    # Read CLI arguments 
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration")
    parser.add_argument('-r', '--rate', required=False, default=None, dest="rate")
    parser.add_argument('-s', '--seed', required=False, default=default_seed, dest="seed")
    parser.add_argument('-rm', '--randmean', required=False, default=1.0, dest="rand_mean")
    args = parser.parse_args()

    # Initialize environment (random seed and simpy.)
    random.seed(args.seed)
    env = simpy.Environment()

    # For now this is a dummy list of node. Will be replaced by a NetworkX representation (Future)
    nodes = [{"id": 1, "name": "NY", "type": "ingress"}, {"id": 2, "name": "DC", "type": "ingress"},
             {"id": 3, "name": "PH", "type": "normal"}]
    print("Coordination-Simulation")
    print("Using seed {} and using mean {}\n".format(args.seed, args.rand_mean))

    # Begin simulation
    flowsimulator.start_simulation(env, nodes, float(args.rand_mean))
    env.run(until=args.duration)


if __name__ == '__main__':
    main()
