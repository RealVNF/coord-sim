import argparse
import simpy
import random
from coordsim.simulation.flowsimulator import FlowSimulator
from coordsim.reader import networkreader
from coordsim.metrics import metrics
from coordsim.simulation.simulatorparams import SimulatorParams
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
    seed = args.seed
    random.seed(seed)

    # Parse network and get NetworkX object and ingress network list
    network, ing_nodes = networkreader.read_network(args.network, node_cap=10, link_cap=10)

    # Getting current SFC list, and the SF list of each SFC.
    sf_placement, sfc_list, sf_list = networkreader.network_update(args.sf, network)
    log.info("Total of {} nodes have VNF's placed in them\n".format(len(sf_placement)))

    # Obtain flow datarate and size params (mean and standard deviation)
    flow_dr_mean = args.flow_dr_mean
    flow_dr_stdev = args.flow_dr_stdev
    flow_size_shape = args.flow_size_shape

    # Obtain flow inter-arrival mean
    inter_arr_mean = args.inter_arr_mean

    # Dummy initial placement
    sf_placement = {
        'pop0': ['a', 'b', 'c'],
        'pop1': ['a', 'b', 'c'],
        'pop2': ['a', 'b']
    }
    # Dummy initial schedule
    schedule = {
        'pop0': {
            'sfc_1': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_2': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_3': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
        },
        'pop1': {
            'sfc_1': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_2': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_3': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
        },
        'pop2': {
            'sfc_1': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_2': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
            'sfc_3': {
                'a': {
                    'pop0': 0.4,
                    'pop1': 0.6,
                    'pop2': 0
                },
                'b': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                },
                'c': {
                    'pop0': 0.6,
                    'pop1': 0.2,
                    'pop2': 0.2
                }
            },
        },
    }

    # Get simulation duration
    duration = args.duration

    # Create the simulator parameters object
    params = SimulatorParams(network, ing_nodes, sfc_list, sf_list, seed, sf_placement=sf_placement, schedule=schedule,
                             inter_arr_mean=inter_arr_mean, flow_dr_mean=flow_dr_mean, flow_dr_stdev=flow_dr_stdev,
                             flow_size_shape=flow_size_shape)

    # Create a FlowSimulator object, pass the SimPy environment and params objects
    simulator = FlowSimulator(env, params)

    # Start the simulation
    simulator.start()

    # Run the simpy environment for the specified duration
    env.run(until=duration)

    # Record endtime and running_time metrics
    end_time = time.time()
    metrics.running_time(start_time, end_time)


def parse_args():
    default_seed = 9999
    # Read CLI arguments

    # TODO: Research a valid defaults for these arguments. Also update defaults in SimulatorParams.
    parser = argparse.ArgumentParser(description="Coordination-Simulation tool")
    parser.add_argument('-d', '--duration', required=True, default=None, dest="duration", type=int,
                        help="The duration of the simulation (simulates milliseconds).")
    parser.add_argument('-sf', '--sf', required=True, dest="sf",
                        help="VNF file which contains the SFCs and their respective SFs and their properties.")
    parser.add_argument('-n', '--network', required=True, dest='network',
                        help="The GraphML network file that specifies the nodes and edges of the network.")
    parser.add_argument('-s', '--seed', required=False, default=default_seed, dest="seed", type=int,
                        help="The seed to use for the random number generator.")
    parser.add_argument('-iam', '--inter_arr_mean', required=False, default=1.0, dest="inter_arr_mean", type=float,
                        help="Inter arrival mean of the flows' arrival at ingress nodes.")
    parser.add_argument('-fdm', '--flow_dr_mean', required=False, default=5.0, dest="flow_dr_mean", type=float,
                        help="The mean value for the generation of data rate values for each flow.")
    parser.add_argument('-fds', '--flow_dr_stdev', required=False, default=1.0, dest="flow_dr_stdev", type=float,
                        help="The standard deviation value for the generation of data rate values for each flow.")
    parser.add_argument('-fss', '--flow_size_shape', required=False, default=1.0, dest="flow_size_shape", type=float,
                        help="The shape of the Pareto distribution for the generation of the flow size values.")
    return parser.parse_args()


if __name__ == '__main__':
    main()
