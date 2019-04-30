import argparse
import simpy
import random
from coordsim.simulation import flowsimulator
from coordsim.reader import networkreader
import logging


def main():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

    args = parse_args()

    # Initialize environment (random seed and simpy.)
    random.seed(args.seed)
    env = simpy.Environment()

    network = networkreader.read_network(args.network, node_cap=10, link_cap=10)
    log.info("Coordination-Simulation")
    log.info("Using seed {} and using inter arrival mean {}\n".format(args.seed, args.inter_arr_mean))

    # Getting current placement of VNF's
    sf_placement, sfc_list, sf_list = networkreader.network_update(args.placement, network)
    log.info("Total of {} nodes have VNF's placed in them\n".format(len(sf_placement)))

    # Obtain flow datarate and size params
    flow_dr_mean = float(args.flow_dr_mean)
    flow_dr_stdev = float(args.flow_dr_stdev)
    flow_size_shape = float(args.flow_size_shape)
    vnf_delay_mean = float(args.vnf_delay_mean)
    vnf_delay_stdev = float(args.vnf_delay_stdev)

    # Obtain flow inter arrival mean
    inter_arr_mean = float(args.inter_arr_mean)

    # Begin simulation
    flowsimulator.start_simulation(env, network, sf_placement, sfc_list, sf_list, inter_arr_mean,
                                   flow_dr_mean, flow_dr_stdev, flow_size_shape, vnf_delay_mean,
                                   vnf_delay_stdev)
    env.run(until=args.duration)


def parse_args():
    default_seed = 9999
    # Read CLI arguments
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration")
    parser.add_argument('-r', '--rate', required=False, default=None, dest="rate")
    parser.add_argument('-s', '--seed', required=False, default=default_seed, dest="seed")
    parser.add_argument('-n', '--network', required=True, dest='network')
    parser.add_argument('-iam', '--inter_arr_mean', required=False, default=1.0, dest="inter_arr_mean")
    parser.add_argument('-p', '--placement', required=True, default=None, dest="placement")
    parser.add_argument('-fdm', '--flow_dr_mean', required=False, default=10.0, dest="flow_dr_mean")
    parser.add_argument('-fds', '--flow_dr_stdev', required=False, default=1.0, dest="flow_dr_stdev")
    parser.add_argument('-fss', '--flow_size_shape', required=False, default=1.0, dest="flow_size_shape")
    parser.add_argument('-vdm', '--vnf_delay_mean', required=False, default=5.0, dest="vnf_delay_mean")
    parser.add_argument('-vds', '--vnf_delay_stdev', required=False, default=1.0, dest="vnf_delay_stdev")
    return parser.parse_args()


if __name__ == '__main__':
    main()
