import coordsim.reader.networkreader as networkreader
from coordsim.simulation.flowsimulator import FlowSimulator
import coordsim.metrics.metrics as metrics
from coordsim.network.scheduler import Scheduler
import time
from coordsim.simulation.simulatorparams import SimulatorParams
from siminterface.interface.siminterface import SimulatorAction, SimulatorInterface, SimulatorState
import simpy
import random

DURATION = int(100)


class Simulator(SimulatorInterface):
    def __init__(self):
        # Number of time the simulator has run. Necessary to correctly calculate env run time of apply function
        self.run_times = int(1)

    def init(self, network_file, service_functions_file, seed):

        # Initialize metrics, record start time
        metrics.reset()
        self.start_time = time.time()

        # Parse network (GraphML): Get NetworkX object and ingress nodes list
        self.network, self.ing_nodes = networkreader.read_network(network_file, node_cap=10, link_cap=10)
        # Parse placement (YAML): Get placement, sfc, and sf lists.
        self.sf_placement, self.sfc_list, self.sf_list = networkreader.network_update(service_functions_file,
                                                                                      self.network)

        # Generate SimPy simulation environment
        self.env = simpy.Environment()

        # Get the initial flow schedule
        self.schedule = Scheduler().flow_schedule
        # Get and plant random seed
        self.seed = seed
        random.seed(self.seed)

        # Instantiate the parameter object for the simulator.
        self.params = SimulatorParams(self.network, self.ing_nodes, self.sf_placement, self.sfc_list, self.sf_list,
                                      self.seed, self.schedule)

        # Instantiate a simulator object, pass the environment and params
        self.simulator = FlowSimulator(self.env, self.params)

        # Start the simulator
        self.simulator.start()

        # Run the environment for one step to get initial stats.
        self.env.step()

        # Parse the network stats. Prepares network stats in SimulatorState format.
        self.parse_network()
        self.network_metrics()

        # Increment the run times variable to indicate the simulator has run an additional time.
        self.run_times += 1

        # Record end time and running time metrics
        self.end_time = time.time()
        metrics.running_time(self.start_time, self.end_time)
        simulator_state = SimulatorState(self.network_dict, self.sfc_list, self.sf_list, self.traffic,
                                         self.network_stats)
        return simulator_state

    def apply(self, actions: SimulatorAction):
        self.simulator.params.sf_placement = actions.placement
        self.simulator.params.schedule = actions.scheduling
        self.env.run(until=(DURATION * self.run_times))
        self.parse_network()
        self.network_metrics()
        self.run_times += 1
        self.end_time = time.time()
        metrics.running_time(self.start_time, self.end_time)
        simulator_state = SimulatorState(self.network_dict, self.sfc_list, self.sf_list, self.traffic,
                                         self.network_stats)
        return simulator_state

    def parse_network(self) -> dict:
        self.network_dict = {'nodes': [], 'edges': []}
        for node in self.network.nodes(data=True):
            # Reset network_dict nodes array
            node_cap = node[1]['cap']
            used_node_cap = node[1]['cap'] - node[1]['remaining_cap']
            self.network_dict['nodes'].append({'id': node[0], 'resource': node_cap, 'used_resources': used_node_cap})
        for edge in self.network.edges(data=True):
            edge_src = edge[0]
            edge_dest = edge[1]
            edge_delay = edge[2]['delay']
            edge_dr = edge[2]['cap']
            edge_used_dr = 0
            self.network_dict['edges'] = {
                'src': edge_src,
                'dst': edge_dest,
                'delay': edge_delay,
                'data_rate': edge_dr,
                'used_data_rate': edge_used_dr
            }

    def network_metrics(self):
        stats = metrics.get_metrics()
        self.traffic = stats['current_traffic']
        self.network_stats = {
            'total_flows': stats['generated_flows'],
            'successful_flows': stats['processed_flows'],
            'dropped_flows': stats['dropped_flows'],
            'in_network_flows': stats['total_active_flows'],
            'avg_end_2_end_delay': stats['avg_end2end_delay']
        }
