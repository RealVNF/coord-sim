import argparse
import simpy
import random
from coordsim.simulation.flowsimulator import FlowSimulator
from coordsim.reader import networkreader
from coordsim.metrics import metrics
from coordsim.simulation.simulatorparams import SimulatorParams
import coordsim.network.dummy_data as dummy_data
import logging
import time


log = logging.getLogger(__name__)


def main():

    # Parse arge, initialize metrics, record start time and configure logging level
    args = parse_args()
    metrics.reset()
    start_time = time.time()
    logging.basicConfig(level=logging.INFO)

    # Create a SimPy environment
    env = simpy.Environment()
    # Seed the random generator
    random.seed(args.seed)

    # Parse network and get NetworkX object and ingress network list
    network, ing_nodes = networkreader.read_network(args.network, node_cap=10, link_cap=10)

    # Getting current SFC list, and the SF list of each SFC.
    sf_placement, sfc_list, sf_list = networkreader.network_update(args.sf, network)

    # use dummy placement and schedule for running simulator without algorithm
    sf_placement = dummy_data.triangle_placement
    schedule = dummy_data.triangle_schedule

    # Create the simulator parameters object with the provided args
    params = SimulatorParams(network, ing_nodes, sfc_list, sf_list, args.seed, sf_placement=sf_placement,
                             schedule=schedule, inter_arr_mean=args.inter_arr_mean, flow_dr_mean=args.flow_dr_mean,
                             flow_dr_stdev=args.flow_dr_stdev, flow_size_shape=args.flow_size_shape)
    log.info(params)

    # Create a FlowSimulator object, pass the SimPy environment and params objects
    simulator = FlowSimulator(env, params)

    # Start the simulation
    simulator.start()

    # Run the simpy environment for the specified duration
    env.run(until=args.duration)

    # Record endtime and running_time metrics
    end_time = time.time()
    metrics.running_time(start_time, end_time)


# parse CLI args
def parse_args():
    # TODO: Research a valid defaults for these arguments. Also update defaults in SimulatorParams.
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration", type=int,
                        help="The duration of the simulation (simulates milliseconds).")
    parser.add_argument('-sf', '--sf', required=True, dest="sf",
                        help="VNF file which contains the SFCs and their respective SFs and their properties.")
    parser.add_argument('-n', '--network', required=True, dest='network',
                        help="The GraphML network file that specifies the nodes and edges of the network.")
    parser.add_argument('-s', '--seed', required=False, default=random.randint(0, 9999), dest="seed", type=int,
                        help="The seed to use for the random number generator.")
    parser.add_argument('-iam', '--inter_arr_mean', required=False, default=10.0, dest="inter_arr_mean", type=float,
                        help="Inter arrival mean of the flows' arrival at ingress nodes.")
    parser.add_argument('-fdm', '--flow_dr_mean', required=False, default=1.0, dest="flow_dr_mean", type=float,
                        help="The mean value for the generation of data rate values for each flow.")
    parser.add_argument('-fds', '--flow_dr_stdev', required=False, default=0.0, dest="flow_dr_stdev", type=float,
                        help="The standard deviation value for the generation of data rate values for each flow.")
    parser.add_argument('-fss', '--flow_size_shape', required=False, default=0.001, dest="flow_size_shape", type=float,
                        help="The shape of the Pareto distribution for the generation of the flow size values.")
    return parser.parse_args()


if __name__ == '__main__':
    main()
