import logging
import numpy as np
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.controller import BaseController
from spinterface import SimulatorAction, SimulatorState
log = logging.getLogger(__name__)


class DurationController(BaseController):
    """
    This is the default decision maker class. It makes flow decisions based on the scheduling table
    """

    def __init__(self, env, params):
        super().__init__(env, params)
        self.episode = 0
        self.duration = self.params.run_duration

    def get_init_state(self):
        # Run the environment for one step to get initial stats.
        self.env.step()

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()
        if self.prediction:
            requested_traffic = self.get_current_ingress_traffic()
            self.predictor.predict_traffic(self.env.now, current_traffic=requested_traffic)
            stats = self.params.metrics.get_metrics()
            self.traffic = stats['run_total_requested_traffic']
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        return simulator_state

    def get_next_state(self, action: SimulatorAction) -> SimulatorState:
        """ Apply a decision and run until a specified duration has finished
        If init, create initial state
        """

        # self.writer.write_action_result(self.episode, self.env.now, action)

        # Get the new placement from the action passed by the RL agent
        # Modify and set the placement parameter of the instantiated simulator object.
        self.simulator.params.sf_placement = action.placement
        # Update which sf is available at which node
        for node_id, placed_sf_list in action.placement.items():
            available = {}
            # Keep only SFs which still process
            for sf, sf_data in self.simulator.params.network.nodes[node_id]['available_sf'].items():
                if sf_data['load'] != 0:
                    available[sf] = sf_data
            # Add all SFs which are in the placement
            for sf in placed_sf_list:
                if sf not in available.keys():
                    available[sf] = available.get(sf, {
                        'load': 0.0,
                        'last_active': self.env.now,
                        'startup_time': self.env.now
                    })
            self.simulator.params.network.nodes[node_id]['available_sf'] = available

        # Get the new schedule from the SimulatorAction
        # Set it in the params of the instantiated simulator object.
        self.simulator.params.schedule = action.scheduling

        runtime_steps = self.duration * self.run_times
        self.params.logger.debug("Running simulator until time step %s", runtime_steps)
        self.env.run(until=runtime_steps)

        # Check to see if traffic prediction is enabled to provide future traffic not current traffic
        if self.prediction:
            requested_traffic = self.get_current_ingress_traffic()
            self.predictor.predict_traffic(self.env.now, current_traffic=requested_traffic)
            stats = self.params.metrics.get_metrics()
            self.traffic = stats['run_total_requested_traffic']
        # Create a new SimulatorState object to pass to the RL Agent
        simulator_state = SimulatorState(self.network_dict, self.simulator.params.sf_placement, self.sfc_list,
                                         self.sf_list, self.traffic, self.network_stats)
        return simulator_state

    def parse_network(self) -> dict:
        """
        Converts the NetworkX network in the simulator to a dict in a format specified in the SimulatorState class.
        """
        max_node_usage = self.params.metrics.get_metrics()['run_max_node_usage']
        self.network_dict = {'nodes': [], 'edges': []}
        for node in self.params.network.nodes(data=True):
            node_cap = node[1]['cap']
            run_max_node_usage = max_node_usage[node[0]]
            # 'used_resources' here is the max usage for the run.
            self.network_dict['nodes'].append({'id': node[0], 'resource': node_cap,
                                               'used_resources': run_max_node_usage})
        for edge in self.network.edges(data=True):
            edge_src = edge[0]
            edge_dest = edge[1]
            edge_delay = edge[2]['delay']
            edge_dr = edge[2]['cap']
            # We use a fixed user data rate for the edges here as the functionality is not yet incorporated in the
            # simulator.
            # TODO: Implement used edge data rates in the simulator.
            edge_used_dr = 0
            self.network_dict['edges'].append({
                'src': edge_src,
                'dst': edge_dest,
                'delay': edge_delay,
                'data_rate': edge_dr,
                'used_data_rate': edge_used_dr
            })

    def get_current_ingress_traffic(self) -> float:
        """
        Get current ingress traffic for the LSTM module
        Current limitation: works for 1 SFC and 1 ingress node
        """
        # Get name of ingress SF from first SFC
        first_sfc = list(self.sfc_list.keys())[0]
        ingress_sf = self.params.sfc_list[first_sfc][0]
        ingress_node = self.params.ing_nodes[0][0]
        ingress_traffic = self.metrics.metrics['run_total_requested_traffic'][ingress_node][first_sfc][ingress_sf]
        return ingress_traffic

    def network_metrics(self):
        """
        Processes the metrics and parses them in a format specified in the SimulatorState class.
        """
        stats = self.params.metrics.get_metrics()
        self.traffic = stats['run_total_requested_traffic']
        self.network_stats = {
            'processed_traffic': stats['run_total_processed_traffic'],
            'total_flows': stats['generated_flows'],
            'successful_flows': stats['processed_flows'],
            'dropped_flows': stats['dropped_flows'],
            'run_successful_flows': stats['run_processed_flows'],
            'run_dropped_flows': stats['run_dropped_flows'],
            'run_dropped_flows_per_node': stats['run_dropped_flows_per_node'],
            'in_network_flows': stats['total_active_flows'],
            'avg_end2end_delay': stats['avg_end2end_delay'],
            'run_avg_end2end_delay': stats['run_avg_end2end_delay'],
            'run_max_end2end_delay': stats['run_max_end2end_delay'],
            'run_avg_path_delay': stats['run_avg_path_delay'],
            'run_total_processed_traffic': stats['run_total_processed_traffic']
        }
