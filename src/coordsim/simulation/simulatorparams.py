"""

Flow Simulator parameters.
- Allows for clean and quick access to parameters from the flow simulator.
- Facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""
import numpy as np
import random


class SimulatorParams:
    def __init__(self, network, ing_nodes, eg_nodes, sfc_list, sf_list, config, metrics, prediction=False,
                 schedule=None, sf_placement=None):
        # Bool to store if simulator is called in warmup
        self.warmup = True
        # NetworkX network object: DiGraph
        self.network = network
        # Ingress nodes of the network (nodes at which flows arrive): list
        self.ing_nodes = ing_nodes
        # Egress nodes of the network (nodes at which flows may leave the network): list
        self.eg_nodes = eg_nodes
        # List of available SFCs and their child SFs: defaultdict(None)
        self.sfc_list = sfc_list
        # List of every SF and it's properties (e.g. processing_delay): defaultdict(None)
        self.sf_list = sf_list
        self.metrics = metrics
        self.use_trace = False
        if 'trace_path' in config:
            self.use_trace = True

        self.prediction = prediction  # bool
        self.predicted_inter_arr_mean = {node_id: config['inter_arrival_mean'] for node_id in self.network.nodes}

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

        # list of generated inter-arrival times, flow sizes, and data rates for the entire episode
        # dict: ingress_id --> list of arrival times, sizes, drs
        self.flow_arrival_list = None
        self.flow_size_list = None
        self.flow_dr_list = None
        # index in these lists: is initialized and reset when generating the lists
        # dict: ingress_id --> list index
        self.flow_list_idx = None

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

    def update_single_predicted_inter_arr_mean(self, new_mean):
        self.predicted_inter_arr_mean = {node_id: new_mean for node_id in self.network.nodes}

    def reset_flow_lists(self):
        """Reset and re-init flow data lists and index. Called at the beginning of each new episode."""
        # list of generated inter-arrival times, flow sizes, and data rates for the entire episode
        # dict: ingress_id --> list of arrival times, sizes, drs
        self.flow_arrival_list = {ing[0]: [] for ing in self.ing_nodes}
        self.flow_size_list = {ing[0]: [] for ing in self.ing_nodes}
        self.flow_dr_list = {ing[0]: [] for ing in self.ing_nodes}
        self.flow_list_idx = {ing[0]: 0 for ing in self.ing_nodes}
        self.last_arrival_sum = {ing[0]: 0 for ing in self.ing_nodes}

    def generate_flow_lists(self, now=0):
        """Generate and append dicts of lists of flow arrival, size, dr for the run duration"""
        # generate flow inter-arrival times for each ingress
        ingress_ids = [ing[0] for ing in self.ing_nodes]
        for ing in ingress_ids:
            flow_arrival = []
            flow_sizes = []
            flow_drs = []
            # generate flows for time frame of num_steps
            run_end = now + self.run_duration
            # Check to see if next flow arrival is before end of run
            while self.last_arrival_sum[ing] < run_end:
                # extension for det, and MMPP
                if self.deterministic_arrival:
                    inter_arr_time = self.inter_arr_mean[ing]
                else:
                    inter_arr_time = random.expovariate(lambd=1.0/self.inter_arr_mean[ing])
                # Generate flow dr
                flow_dr = np.random.normal(self.flow_dr_mean, self.flow_dr_stdev)
                # generate flow sizes
                if self.deterministic_size:
                    flow_size = self.flow_size_shape
                else:
                    # heavy-tail flow size
                    flow_size = np.random.pareto(self.flow_size_shape) + 1
                # Skip flows with negative flow_dr or flow_size values
                if flow_dr <= 0.00 or flow_size <= 0.00:
                    continue

                flow_arrival.append(inter_arr_time)
                flow_sizes.append(flow_size)
                flow_drs.append(flow_dr)
                self.last_arrival_sum[ing] += inter_arr_time

            # append to existing flow list. it continues to grow across runs within an episode
            self.flow_arrival_list[ing].extend(flow_arrival)
            self.flow_dr_list[ing].extend(flow_drs)
            self.flow_size_list[ing].extend(flow_sizes)
            self.generated_flows = flow_drs

    def get_next_flow_data(self, ing):
        """Return next flow data for given ingress from list of generated arrival times."""
        idx = self.flow_list_idx[ing]
        assert idx < len(self.flow_arrival_list[ing])
        inter_arrival_time = self.flow_arrival_list[ing][idx]
        flow_dr = self.flow_dr_list[ing][idx]
        flow_size = self.flow_size_list[ing][idx]
        # important: increment index!
        self.flow_list_idx[ing] += 1
        return inter_arrival_time, flow_dr, flow_size
