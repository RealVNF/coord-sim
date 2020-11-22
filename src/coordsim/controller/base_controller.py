from simpy import Environment
from coordsim.network.flow import Flow
from coordsim.simulation.flowsimulator import FlowSimulator
from coordsim.simulation.simulatorparams import SimulatorParams
from typing import Union


class BaseController:
    """
    BaseController class
    Controls the duration between decisions and returns a simulator state to be passed
    to the controlling algorithm
    """
    def __init__(self, env: Environment, params: SimulatorParams, simulator: FlowSimulator):
        self.env = env
        self.params = params
        self.simulator = simulator

    def get_init_state(self):
        """ Return the init state """
        raise NotImplementedError

    def get_next_state(self, action=None):
        """
        Apply the action from the control algorithm
        Returns:
            - SimulatorState or a child class
        """
        raise NotImplementedError

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

    def get_current_ingress_traffic(self) -> float:
        """
        Get current ingress traffic for the LSTM module
        Current limitation: works for 1 SFC and 1 ingress node
        """
        # Get name of ingress SF from first SFC
        first_sfc = list(self.params.sfc_list.keys())[0]
        ingress_sf = self.params.sfc_list[first_sfc][0]
        ingress_node = self.params.ing_nodes[0][0]
        ingress_traffic = self.metrics.metrics['run_total_requested_traffic'][ingress_node][first_sfc][ingress_sf]
        return ingress_traffic

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
        for edge in self.params.network.edges(data=True):
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

    def update_prediction(self):
        requested_traffic = self.get_current_ingress_traffic()
        self.predictor.predict_traffic(self.env.now, current_traffic=requested_traffic)
        stats = self.params.metrics.get_metrics()
        self.traffic = stats['run_total_requested_traffic']
