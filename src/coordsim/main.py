import argparse
import simpy
from coordsim.simulation import flowsimulator


def main():
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration")
    parser.add_argument('-r', '--rate', required=False, default=None, dest="rate")
    args = parser.parse_args()
    env = simpy.Environment()
    nodes = [{"id": 1, "name": "NY", "type": "ingress"}, {"id": 1, "name": "DC", "type": "ingress"},
             {"id": 1, "name": "PH", "type": "normal"}]
    flowsimulator.start_simulation(env, nodes)
    env.run(until=args.duration)


if __name__ == '__main__':
    main()
