import logging
import random
import time

import coordsim.metrics.metrics as metrics
import coordsim.reader.reader as reader
from coordsim.simulation.flowsimulator import FlowSimulator
from coordsim.simulation.simulatorparams import SimulatorParams
import numpy
import simpy
from spinterface import SimulatorAction, SimulatorInterface, SimulatorState
from coordsim.writer.writer import ResultWriter
import copy
import networkx
logger = logging.getLogger(__name__)


class ExtendedSimulatorAction(SimulatorAction):
    def __init__(self,
                 placement: dict,
                 scheduling: dict,
                 flow_forwarding_rules: dict,
                 flow_processing_rules: dict):
        SimulatorAction.__init__(self, placement, scheduling)
        self.flow_forwarding_rules = flow_forwarding_rules
        self.flow_processing_rules = flow_processing_rules

    @staticmethod
    def convert(actions: SimulatorAction, flow_forwarding_rules={}, flow_processing_rules={}):
        return ExtendedSimulatorAction(actions.placement,
                                       actions.scheduling,
                                       flow_forwarding_rules,
                                       flow_processing_rules)


class ExtendedSimulatorState(SimulatorState):
    def __init__(self,
                 network,
                 placement,
                 sfcs,
                 service_functions,
                 traffic,
                 network_stats,
                 flow_forwarding_rules: dict,
                 flow_processing_rules: dict):
        SimulatorState.__init__(self, network, placement, sfcs, service_functions, traffic, network_stats)
        self.flow_forwarding_rules = flow_forwarding_rules
        self.flow_processing_rules = flow_processing_rules

    @staticmethod
    def convert(state: SimulatorState, flow_forwarding_rules={}, flow_processing_rules={}):
        return ExtendedSimulatorState(state.network,
                                      state.placement,
                                      state.sfcs,
                                      state.service_functions,
                                      state.traffic,
                                      state.network_stats,
                                      flow_forwarding_rules,
                                      flow_processing_rules)


class Simulator(SimulatorInterface):
    def __init__(self, test_mode=False):
        # Number of time the simulator has run. Necessary to correctly calculate env run time of apply function
        self.run_times = int(1)
        self.test_mode = test_mode
        # Create CSV writer
        self.writer = ResultWriter(self.test_mode)

    def init(self, network_file, service_functions_file, config_file, seed, resource_functions_path="",
             interception_callbacks={}) -> ExtendedSimulatorState:

        # Initialize metrics, record start time
        metrics.reset()
        self.run_times = int(1)
        self.start_time = time.time()

        # Parse network and SFC + SF file
        self.network, self.ing_nodes = reader.read_network(network_file, node_cap=10, link_cap=10)
        self.sfc_list = reader.get_sfc(service_functions_file)
        self.sf_list = reader.get_sf(service_functions_file, resource_functions_path)
        self.config = reader.get_config(config_file)
        self.interception_callbacks = interception_callbacks

        # Generate SimPy simulation environment
        self.env = simpy.Environment()

        # Instantiate the parameter object for the simulator.
        self.params = SimulatorParams(self.network, self.ing_nodes, self.sfc_list, self.sf_list, self.config, seed,
                                      interception_callbacks=self.interception_callbacks)
        self.duration = self.params.run_duration
        # Get and plant random seed
        self.seed = seed
        random.seed(self.seed)
        numpy.random.seed(self.seed)

        # Instantiate a simulator object, pass the environment and params
        self.simulator = FlowSimulator(self.env, self.params)

        # Start the simulator
        self.simulator.start()

        # Run the environment for one step to get initial stats.
        self.env.step()

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()

        # Record end time and running time metrics
        self.end_time = time.time()
        metrics.running_time(self.start_time, self.end_time)
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        # self.writer.write_state_results(self.env, simulator_state)
        extended_simulator_state = ExtendedSimulatorState.convert(simulator_state, self.params.flow_forwarding_rules,
                                                                  self.params.flow_processing_rules)
        return extended_simulator_state

    def init_inter(self, network_file, service_functions_file, config_file, seed, resource_functions_path="",
                   interception_callbacks={}):
        # Initialize metrics, record start time
        metrics.reset()
        self.run_times = int(1)
        self.start_time = time.time()

        # Parse network and SFC + SF file
        self.network, self.ing_nodes = reader.read_network(network_file, node_cap=10, link_cap=10)
        self.sfc_list = reader.get_sfc(service_functions_file)
        self.sf_list = reader.get_sf(service_functions_file, resource_functions_path)
        self.config = reader.get_config(config_file)
        self.interception_callbacks = interception_callbacks

        # Generate SimPy simulation environment
        self.env = simpy.Environment()

        # Instantiate the parameter object for the simulator.
        self.params = SimulatorParams(self.network, self.ing_nodes, self.sfc_list, self.sf_list, self.config, seed,
                                      interception_callbacks=self.interception_callbacks)
        self.duration = self.params.run_duration
        # Get and plant random seed
        self.seed = seed
        random.seed(self.seed)
        numpy.random.seed(self.seed)

        # Instantiate a simulator object, pass the environment and params
        self.simulator = FlowSimulator(self.env, self.params)

        # Start the simulator
        self.simulator.start()

        # Run the environment for one step to get initial stats.
        self.env.step()

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()

        # Record end time and running time metrics
        self.end_time = time.time()
        metrics.running_time(self.start_time, self.end_time)
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        # self.writer.write_state_results(self.env, simulator_state)
        extended_simulator_state = ExtendedSimulatorState.convert(simulator_state, self.params.flow_forwarding_rules,
                                                                  self.params.flow_processing_rules)
        return extended_simulator_state

    def apply(self, actions: ExtendedSimulatorAction) -> ExtendedSimulatorState:
        # self.writer.write_action_result(self.env, actions)
        # increase performance when debug logging is disabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"SimulatorAction: %s", repr(actions))

        # Get the new placement from the action passed by the RL agent
        # Modify and set the placement parameter of the instantiated simulator object.
        self.simulator.params.sf_placement = actions.placement
        # Update which sf is available at which node
        for node_id, placed_sf_list in actions.placement.items():
            available_sf = {}
            for sf in placed_sf_list:
                available_sf[sf] = self.simulator.params.network.nodes[node_id]['available_sf'].get(sf, {'load': 0.0})
            self.simulator.params.network.nodes[node_id]['available_sf'] = available_sf

        # Get the new schedule from the SimulatorAction
        # Set it in the params of the instantiated simulator object.
        self.simulator.params.schedule = actions.scheduling
        # Set forwarding rules
        self.params.flow_forwarding_rules = actions.flow_forwarding_rules
        # Set processing rules
        self.params.flow_processing_rules = actions.flow_processing_rules

        # reset metrics for steps
        metrics.reset_run()

        # Run the simulation again with the new params for the set duration.
        # Due to SimPy restraints, we multiply the duration by the run times because SimPy does not reset when run()
        # stops and we must increase the value of "until=" to accomodate for this. e.g.: 1st run call runs for 100 time
        # uniits (1 run time), 2nd run call will also run for 100 more time units but value of "until=" is now 200.
        runtime_steps = self.duration * self.run_times
        logger.debug("Running simulator until time step %s", runtime_steps)
        self.env.run(until=runtime_steps)

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()

        # Increment the run times variable
        self.run_times += 1

        # Record end time of the apply round, doesn't change start time to show the running time of the entire
        # simulation at the end of the simulation.
        self.end_time = time.time()
        metrics.running_time(self.start_time, self.end_time)

        # Create a new SimulatorState object to pass to the RL Agent
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        extended_simulator_state = ExtendedSimulatorState.convert(simulator_state, self.params.flow_forwarding_rules,
                                                                  self.params.flow_processing_rules)
        self.writer.write_state_results(self.env, simulator_state)
        return extended_simulator_state

    def apply_inter(self, actions: ExtendedSimulatorAction):
        # increase performance when debug logging is disabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"SimulatorAction: %s", repr(actions))

        # Get the new placement from the action passed by the RL agent
        # Modify and set the placement parameter of the instantiated simulator object.
        self.simulator.params.sf_placement = actions.placement
        # Update which sf is available at which node
        for node_id, placed_sf_list in actions.placement.items():
            available_sf = {}
            for sf in placed_sf_list:
                available_sf[sf] = self.simulator.params.network.nodes[node_id]['available_sf'].get(sf, {'load': 0.0})
            self.simulator.params.network.nodes[node_id]['available_sf'] = available_sf

        # Get the new schedule from the SimulatorAction
        # Set it in the params of the instantiated simulator object.
        self.simulator.params.schedule = actions.scheduling
        # Set forwarding rules
        self.params.flow_forwarding_rules = actions.flow_forwarding_rules
        # Set processing rules
        self.params.flow_processing_rules = actions.flow_processing_rules

    def get_simulator_state(self) -> ExtendedSimulatorState:
        self.parse_network()
        self.network_metrics()
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        extended_simulator_state = ExtendedSimulatorState.convert(simulator_state, self.params.flow_forwarding_rules,
                                                                  self.params.flow_processing_rules)
        return extended_simulator_state

    def write_simulator_state(self):
        # reset metrics for steps
        metrics.reset_run()

        extended = self.get_simulator_state()
        self.writer.write_state_results(self.env, extended)

    def get_network_copy(self) -> networkx.Graph:
        """
        Returns a deepcopy of the network topology and its current state. The returned network can be used by external
        algorithms for e.g. calculating shortest path based on their restricted knowledge, without altering the internal
        simulator state.
        """
        copy_network = copy.deepcopy(self.params.network)
        return copy_network

    def parse_network(self) -> dict:
        """
        Converts the NetworkX network in the simulator to a dict in a format specified in the SimulatorState class.
        """
        self.network_dict = {'nodes': [], 'edges': []}
        for node in self.params.network.nodes(data=True):
            node_cap = node[1]['cap']
            used_node_cap = node[1]['cap'] - node[1]['remaining_cap']
            self.network_dict['nodes'].append({'id': node[0], 'resource': node_cap, 'used_resources': used_node_cap})
        for edge in self.network.edges(data=True):
            edge_src = edge[0]
            edge_dest = edge[1]
            edge_delay = edge[2]['delay']
            edge_dr = edge[2]['cap']
            # We use a fixed user data rate for the edges here as the functionality is not yet incorporated in the
            # simulator.
            edge_used_dr = edge[2]['cap'] - edge[2]['remaining_cap']
            self.network_dict['edges'].append({
                'src': edge_src,
                'dst': edge_dest,
                'delay': edge_delay,
                'data_rate': edge_dr,
                'used_data_rate': edge_used_dr
            })

    def network_metrics(self):
        """
        Processes the metrics and parses them in a format specified in the SimulatorState class.
        """
        stats = metrics.get_metrics()
        self.traffic = stats['current_traffic']
        self.network_stats = {
            'total_flows': stats['generated_flows'],
            'successful_flows': stats['processed_flows'],
            'dropped_flows': stats['dropped_flows'],
            'in_network_flows': stats['total_active_flows'],
            'avg_end_2_end_delay': stats['avg_end2end_delay'],
            'run_avg_end2end_delay': stats['run_avg_end2end_delay'],
            'run_max_end2end_delay': stats['run_max_end2end_delay']
        }
