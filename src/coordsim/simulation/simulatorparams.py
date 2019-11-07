"""

Flow Simulator parameters.
- Allows for clean and quick access to parameters from the flow simulator.
- Facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""
import numpy as np


class SimulatorParams:
    def __init__(self, network, ing_nodes, sfc_list, sf_list, config, schedule=None, sf_placement=None):
        # NetworkX network object: DiGraph
        self.network = network
        # Ingress nodes of the network (nodes at which flows arrive): list
        self.ing_nodes = ing_nodes
        # List of available SFCs and their child SFs: defaultdict(None)
        self.sfc_list = sfc_list
        # List of every SF and it's properties (e.g. processing_delay): defaultdict(None)
        self.sf_list = sf_list

        self.use_trace = False
        if 'trace_path' in config:
            self.use_trace = True

        if schedule is None:
            schedule = {}
        if sf_placement is None:
            sf_placement = {}
        # read dummy placement and schedule if specified
        # Flow forwarding schedule: dict
        self.schedule = schedule
        # Placement of SFs in each node: defaultdict(list)
        self.sf_placement = sf_placement
        # Update which sf is available at which node
        for node_id, placed_sf_list in sf_placement.items():
            for sf in placed_sf_list:
                self.network.nodes[node_id]['available_sf'][sf] = self.network.nodes[node_id]['available_sf'].get(sf, {
                    'load': 0.0})

        # Flow data rate normal distribution mean: float
        self.flow_dr_mean = config['flow_dr_mean']
        # Flow data rate normal distribution standard deviation: float
        self.flow_dr_stdev = config['flow_dr_stdev']
        # Flow size Pareto heavy-tail distribtution shape: float
        self.flow_size_shape = config['flow_size_shape']
        # if deterministic = True, the simulator reinterprets and uses inter_arrival_mean and flow_size_shape as fixed
        # deterministic values rather than means of a random distribution
        self.deterministic_arrival = None
        self.deterministic_size = None
        if 'deterministic' in config:
            self.deterministic_arrival = config['deterministic']
            self.deterministic_size = config['deterministic']
        # deterministic_arrival/size override 'deterministic'
        if 'deterministic_arrival' in config:
            self.deterministic_arrival = config['deterministic_arrival']
        if 'deterministic_size' in config:
            self.deterministic_size = config['deterministic_size']
        if self.deterministic_arrival is None or self.deterministic_size is None:
            raise ValueError("'deterministic_arrival' or 'deterministic_size' are not set in simulator config.")

        # also allow to set determinism for inter-arrival times and flow size separately
        # The duration of a run in the simulator's interface
        self.run_duration = config['run_duration']

        self.use_states = False
        self.states = {}
        self.in_init_state = True

        if 'use_states' in config and config['use_states']:
            self.use_states = True
            self.init_state = config['init_state']
            self.states = config['states']
            if self.in_init_state:
                self.current_state = self.init_state
            state_inter_arr_mean = self.states[self.current_state]['inter_arr_mean']
            self.update_single_inter_arr_mean(state_inter_arr_mean)
        else:
            inter_arr_mean = config['inter_arrival_mean']
            self.update_single_inter_arr_mean(inter_arr_mean)

    def update_state(self):
        switch = [False, True]
        change_prob = self.states[self.current_state]['switch_p']
        remain_prob = 1 - change_prob
        switch_decision = np.random.choice(switch, p=[remain_prob, change_prob])
        if switch_decision:
            state_names = list(self.states.keys())
            if self.current_state == state_names[0]:
                self.current_state = state_names[1]
            else:
                self.current_state = state_names[0]
        state_inter_arr_mean = self.states[self.current_state]['inter_arr_mean']
        self.update_single_inter_arr_mean(state_inter_arr_mean)

    def update_single_inter_arr_mean(self, new_mean):
        self.inter_arr_mean = {node_id: new_mean for node_id in self.network.nodes}

    # string representation for logging
    def __str__(self):
        params_str = "Simulator parameters: \n"
        params_str += "inter_arr_mean: {}\n".format(self.inter_arr_mean)
        params_str += f"deterministic_arrival: {self.deterministic_arrival}\n"
        params_str += "flow_dr_mean: {}\n".format(self.flow_dr_mean)
        params_str += "flow_dr_stdv: {}\n".format(self.flow_dr_stdev)
        params_str += "flow_size_shape: {}\n".format(self.flow_size_shape)
        params_str += f"deterministic_size: {self.deterministic_size}\n"
        return params_str
